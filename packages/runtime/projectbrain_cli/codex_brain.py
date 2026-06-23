"""codex-brain command: run Codex CLI with ProjectBrain session support."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote
from typing import Any, Callable

from projectbrain_cli.codex_session import run_codex_command
from projectbrain_runtime.brain.repository import BrainRepository
from projectbrain_runtime.brain.service import BrainService


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
    command_runner: Callable[..., int] | None = None,
    browser_opener: Callable[[str], Any] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    requested_path = Path(args.project).expanduser().resolve()
    if not requested_path.exists():
        raise SystemExit(f"Project path does not exist: {requested_path}")
    project_path = _project_root(requested_path)
    BrainService(BrainRepository(project_path))
    if not args.no_ui:
        opener = browser_opener or _open_url
        opener(_brain_url(project_path))
    command = shlex.split(args.codex_command)
    if not command:
        raise SystemExit("--codex-command must not be empty")
    runner = command_runner or run_codex_command
    return runner(command, cwd=project_path)


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
