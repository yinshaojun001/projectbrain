"""codex-brain command: run Codex CLI with ProjectBrain session support."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from uuid import uuid4

from projectbrain_cli.codex_session import (
    ManagedSessionResult,
    conversation_transcript,
    extract_session_memories,
    persist_session_result,
    run_codex_command,
    run_codex_command_captured,
    write_transcript,
)
from projectbrain_runtime.agent_output import format_output
from projectbrain_runtime.brain.repository import BrainRepository
from projectbrain_runtime.brain.service import BrainService
from projectbrain_runtime.repository import JsonProjectBrainRepository
from projectbrain_runtime.service import ProjectBrainRuntime

_EMPTY_EXTRACTION_OUTPUT = '{"session_summary":"","candidates":[]}'
_CODEX_PROMPTLESS_SUBCOMMANDS = {
    "app",
    "app-server",
    "apply",
    "archive",
    "cloud",
    "completion",
    "debug",
    "delete",
    "doctor",
    "exec-server",
    "features",
    "fork",
    "help",
    "login",
    "logout",
    "mcp",
    "mcp-server",
    "plugin",
    "remote-control",
    "review",
    "resume",
    "sandbox",
    "unarchive",
    "update",
}
_CODEX_EXEC_PROMPTLESS_SUBCOMMANDS = {"help", "resume", "review"}
_CODEX_EXEC_OPTIONS_WITH_VALUE = {
    "-C",
    "-c",
    "-m",
    "-o",
    "--ask-for-approval",
    "--cd",
    "--config",
    "--config-profile",
    "--model",
    "--output-last-message",
    "--profile",
    "--sandbox",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-brain", description="Run Codex CLI with ProjectBrain memory capture")
    parser.add_argument("--project", default=".", help="Project path. Defaults to current directory.")
    parser.add_argument("--no-ui", action="store_true", help="Do not open Brain Explorer UI")
    parser.add_argument("--no-extract", action="store_true", help="Do not extract memories on exit")
    parser.add_argument("--codex-command", default="codex", help="Codex command to run")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    command_runner: Callable[..., Any] | None = None,
    browser_opener: Callable[[str], Any] | None = None,
    extraction_runner: Callable[..., str] | None = None,
    session_id_factory: Callable[[], str] | None = None,
    ui_server_starter: Callable[..., Any] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    requested_path = Path(args.project).expanduser().resolve()
    if not requested_path.exists():
        raise SystemExit(f"Project path does not exist: {requested_path}")
    project_path = _project_root(requested_path)
    if not args.no_ui:
        starter = ui_server_starter or _ensure_ui_server
        starter(cwd=project_path)
        opener = browser_opener or _open_url
        opener(_brain_url(project_path))
    command = _codex_command_from_arg(args.codex_command)
    if not command:
        raise SystemExit("--codex-command must not be empty")
    command = _inject_task_bundle_context(command, project_path)
    if args.no_extract:
        runner = command_runner or run_codex_command
        result = runner(command, cwd=project_path)
        return result[0] if isinstance(result, tuple) else result

    runner = command_runner or run_codex_command_captured
    result = runner(command, cwd=project_path)
    if isinstance(result, tuple):
        return_code, transcript = result
    else:
        return_code, transcript = result, ""
    turns = _conversation_turns(command, transcript)
    if not _has_memory_pair(turns):
        return return_code
    session_id = (session_id_factory or _session_id)()
    paired_transcript = conversation_transcript(turns)
    transcript_path = write_transcript(project_path, session_id, paired_transcript)
    if paired_transcript.strip():
        brain_service = BrainService(BrainRepository(project_path))
        extraction_output = _extract_or_empty(paired_transcript, project_path, extraction_runner)
        _persist_session_result(
            brain_service,
            session_result=ManagedSessionResult(
                session_id=session_id,
                project_id=project_path.name or "local_project",
                task="codex-brain session",
                transcript_path=str(transcript_path),
                extraction_output=extraction_output,
                changed_files=[],
                turns=turns,
                stores_full_transcript=True,
            ),
        )
    return return_code


def _codex_command_from_arg(value: str) -> list[str]:
    command = shlex.split(value)
    if not command:
        return []
    if command[0] == "codex":
        return command
    if len(command) == 1 and _looks_like_shell_command(command[0]):
        return command
    return ["codex", "exec", value.strip()]


def _looks_like_shell_command(value: str) -> bool:
    return value in {"true", "false"} or shutil.which(value) is not None


def _extract_or_empty(
    transcript: str,
    project_path: Path,
    extraction_runner: Callable[..., str] | None,
) -> str:
    try:
        return extract_session_memories(transcript, cwd=project_path, extractor_runner=extraction_runner)
    except Exception as exc:
        print(f"ProjectBrain memory extraction failed: {exc}", file=sys.stderr)
        return _EMPTY_EXTRACTION_OUTPUT


def _persist_session_result(
    brain_service: BrainService,
    *,
    session_result: ManagedSessionResult,
) -> None:
    try:
        persist_session_result(brain_service, session_result)
    except Exception as exc:
        print(f"ProjectBrain memory persistence failed: {exc}", file=sys.stderr)
        if session_result.extraction_output == _EMPTY_EXTRACTION_OUTPUT:
            return
        try:
            persist_session_result(
                brain_service,
                ManagedSessionResult(
                    session_id=session_result.session_id,
                    project_id=session_result.project_id,
                    task=session_result.task,
                    transcript_path=session_result.transcript_path,
                    extraction_output=_EMPTY_EXTRACTION_OUTPUT,
                    changed_files=session_result.changed_files,
                    turns=session_result.turns,
                    stores_full_transcript=session_result.stores_full_transcript,
                ),
            )
        except Exception as fallback_exc:
            print(f"ProjectBrain memory fallback persistence failed: {fallback_exc}", file=sys.stderr)


def _conversation_turns(command: list[str], transcript: str) -> list[dict[str, str]]:
    prompt = _user_prompt_from_command(command)
    assistant = transcript.strip()
    turns: list[dict[str, str]] = []
    if prompt:
        turns.append({"role": "user", "content": prompt})
    if assistant:
        turns.append({"role": "assistant", "content": assistant})
    return turns


def _has_memory_pair(turns: list[dict[str, str]]) -> bool:
    roles = {turn.get("role") for turn in turns if turn.get("content")}
    return "user" in roles and "assistant" in roles


def _user_prompt_from_command(command: list[str]) -> str:
    if command == ["codex"]:
        return ""
    if len(command) >= 2 and command[0] == "codex" and command[1] == "exec":
        return _user_prompt_from_codex_exec(command[2:])
    if len(command) >= 2 and command[0] == "codex" and command[1].startswith("-"):
        return ""
    if len(command) >= 2 and command[0] == "codex" and command[1] in _CODEX_PROMPTLESS_SUBCOMMANDS:
        return ""
    if len(command) >= 2 and command[0] == "codex":
        return " ".join(command[1:]).strip()
    return " ".join(command).strip()


def _user_prompt_from_codex_exec(args: list[str]) -> str:
    prompt_tokens = _strip_codex_exec_options(args)
    if not prompt_tokens or prompt_tokens[0] in _CODEX_EXEC_PROMPTLESS_SUBCOMMANDS:
        return ""
    return " ".join(prompt_tokens).strip()


def _strip_codex_exec_options(args: list[str]) -> list[str]:
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            return args[index + 1 :]
        if token.startswith("--") and "=" in token:
            index += 1
            continue
        if token in _CODEX_EXEC_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return args[index:]
    return []


def _session_id() -> str:
    return "session_" + uuid4().hex


def _inject_task_bundle_context(command: list[str], project_path: Path) -> list[str]:
    if len(command) != 3 or command[0] != "codex" or command[1] != "exec":
        return command

    task = command[2].strip()
    if not task:
        return command

    try:
        repository = JsonProjectBrainRepository(project_path / ".projectbrain")
        runtime = ProjectBrainRuntime(repository)
        bundle_data = runtime.build_task_understanding_bundle(
            project_id=project_path.name or "local_project",
            task=task,
        )
    except Exception:
        return command

    preloaded_prompt = _render_preloaded_prompt(task, bundle_data)
    return ["codex", "exec", preloaded_prompt]


def _render_preloaded_prompt(task: str, bundle_data: dict[str, Any]) -> str:
    bundle = format_output(bundle_data, "agent")["agent_output"]
    lines = [
        "ProjectBrain Task Understanding Bundle",
        f"Summary: {bundle.get('summary') or ''}",
    ]

    must_read_files = bundle.get("must_read_files", [])[:3]
    if must_read_files:
        lines.append("Must-read files:")
        for item in must_read_files:
            lines.append(f"- {item.get('file')}: {item.get('reason')}")

    risk_warnings = bundle.get("risk_warnings", [])[:3]
    if risk_warnings:
        lines.append("Risk warnings:")
        for item in risk_warnings:
            lines.append(f"- {item.get('message')}")

    lines.extend(
        [
            "",
            "Original task:",
            task,
        ]
    )
    return "\n".join(lines).strip()


def _open_url(
    url: str,
    *,
    platform: str | None = None,
    command_runner: Callable[..., Any] | None = None,
) -> None:
    current_platform = platform or sys.platform
    if current_platform == "darwin":
        runner = command_runner or subprocess.run
        runner(["open", url], check=False)
        return
    webbrowser.open(url)


def _ensure_ui_server(
    *,
    cwd: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    process_starter: Callable[..., Any] | None = None,
) -> None:
    if _ui_server_is_ready(host=host, port=port):
        return
    starter = process_starter or subprocess.Popen
    starter(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "projectbrain_api.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=cwd,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        if _ui_server_is_ready(host=host, port=port):
            return
        time.sleep(0.1)


def _ui_server_is_ready(*, host: str, port: int) -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=0.2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _project_root(path: Path) -> Path:
    current = path if path.is_dir() else path.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def _brain_url(project_path: Path) -> str:
    encoded_project_path = quote(str(project_path), safe="")
    return f"http://127.0.0.1:8000/ui/projects?project_path={encoded_project_path}"


if __name__ == "__main__":
    raise SystemExit(main())
