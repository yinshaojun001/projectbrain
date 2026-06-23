"""Managed Codex session helpers for codex-brain."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from projectbrain_runtime.brain.extraction import parse_extraction_output
from projectbrain_runtime.brain.models import ConversationSession, now_iso
from projectbrain_runtime.brain.service import BrainService


@dataclass(frozen=True)
class ManagedSessionResult:
    session_id: str
    project_id: str
    task: str
    transcript_path: str
    extraction_output: str
    changed_files: list[str]
    turns: list[dict[str, str]] | None = None
    stores_full_transcript: bool = False


def build_extraction_prompt() -> str:
    return """You are helping ProjectBrain extract durable project knowledge from this coding session.

Return ONLY JSON.

Extract facts that will remain useful in future work on this project:
- business constraints
- architecture decisions
- gotchas
- workflows
- risks
- test guidance
- domain concepts
- incident/root-cause lessons

Do NOT include:
- secrets or credentials
- temporary task steps
- unverified speculation as confirmed fact
- source code bodies
- private URLs
- generic programming advice

For each candidate include:
type, title, statement, summary, tags, applies_to, confidence, evidence_summary, review_state.

Rules:
- If the user explicitly confirmed it, review_state can be human_confirmed.
- If it is inferred by the assistant, review_state must be human_review_required.
- Prefer concise, durable statements.
"""


def run_codex_command(command: list[str], *, cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


_ANSI_ESCAPE_RE = re.compile(
    r"""
    \x1B
    (?:
        \[[0-?]*[ -/]*[@-~]
        |\][^\x07]*(?:\x07|\x1B\\)
        |[PX^_].*?\x1B\\
        |[@-Z\\-_]
    )
    """,
    re.VERBOSE | re.DOTALL,
)


def run_codex_command_captured(
    command: list[str],
    *,
    cwd: Path,
    platform: str | None = None,
    subprocess_runner: Callable[..., Any] | None = None,
) -> tuple[int, str]:
    runner = subprocess_runner or subprocess.run
    if (platform or sys.platform) == "darwin":
        with tempfile.TemporaryDirectory(prefix="projectbrain-codex-") as tmp:
            raw_transcript_path = Path(tmp) / "terminal-transcript.txt"
            completed = runner(["/usr/bin/script", "-q", str(raw_transcript_path), *command], cwd=cwd, check=False)
            raw_transcript = raw_transcript_path.read_text(encoding="utf-8", errors="replace") if raw_transcript_path.exists() else ""
        return completed.returncode, sanitize_terminal_transcript(raw_transcript)

    if not _is_non_interactive_codex_exec(command):
        completed = runner(command, cwd=cwd, check=False)
        return completed.returncode, ""

    completed = runner(command, cwd=cwd, check=False, capture_output=True, text=True)
    transcript = (completed.stdout or "")
    if completed.stderr:
        transcript += ("\n" if transcript else "") + completed.stderr
    print(transcript, end="")
    return completed.returncode, sanitize_terminal_transcript(transcript)


def _is_non_interactive_codex_exec(command: list[str]) -> bool:
    return len(command) >= 2 and command[0] == "codex" and command[1] == "exec"


def sanitize_terminal_transcript(raw: str) -> str:
    text = _ANSI_ESCAPE_RE.sub("", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned: list[str] = []
    for char in text:
        if char in ("\b", "\x7f"):
            if cleaned:
                cleaned.pop()
            continue
        if char == "\n" or char == "\t" or (ord(char) >= 32 and char != "\x7f"):
            cleaned.append(char)
    return "".join(cleaned).strip()


def conversation_transcript(turns: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{turn['role']}: {turn['content']}" for turn in turns if turn.get("content"))


def extract_session_memories(
    transcript: str,
    *,
    cwd: Path,
    extractor_runner: Callable[..., str] | None = None,
) -> str:
    prompt = build_extraction_prompt() + "\n\nTranscript:\n" + transcript
    if extractor_runner is not None:
        return extractor_runner(prompt, cwd=cwd)
    completed = subprocess.run(
        ["codex", "exec", "--output-last-message", "-", prompt],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or "codex extraction failed")
    return completed.stdout


def write_transcript(project_path: Path, session_id: str, transcript: str) -> Path:
    path = project_path / ".projectbrain" / "brain" / "transcripts" / f"{session_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(transcript, encoding="utf-8")
    return path


def persist_session_result(service: BrainService, result: ManagedSessionResult) -> dict:
    parsed = parse_extraction_output(result.extraction_output)
    proposed = service.propose_memories(
        project_id=result.project_id,
        session_id=result.session_id,
        candidates=parsed.get("candidates", []),
    )
    session = ConversationSession(
        session_id=result.session_id,
        project_id=result.project_id,
        task=result.task,
        summary=parsed.get("session_summary", ""),
        ended_at=now_iso(),
        changed_files=result.changed_files,
        candidate_ids=[candidate["candidate_id"] for candidate in proposed["candidates"]],
        turns=result.turns or [],
        privacy={
            "stores_full_transcript": result.stores_full_transcript,
            "stores_excerpts": True,
            "transcript_path": result.transcript_path,
        },
    )
    service.save_session(session)
    return {"session": session.to_dict(), "candidate_count": proposed["candidate_count"], "candidates": proposed["candidates"]}
