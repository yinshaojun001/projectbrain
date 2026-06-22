"""codex-brain command: run Codex CLI with ProjectBrain session support."""

from __future__ import annotations

import argparse
import shlex
import webbrowser
from pathlib import Path
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
    project_path = _project_root(Path(args.project).expanduser().resolve())
    BrainService(BrainRepository(project_path))
    if not args.no_ui:
        (browser_opener or webbrowser.open)(_brain_url(project_path))
    command = shlex.split(args.codex_command)
    runner = command_runner or run_codex_command
    return runner(command, cwd=project_path)


def _project_root(path: Path) -> Path:
    current = path if path.is_dir() else path.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def _brain_url(project_path: Path) -> str:
    return f"http://127.0.0.1:8000/ui/app/projects?project_path={project_path}"


if __name__ == "__main__":
    raise SystemExit(main())
