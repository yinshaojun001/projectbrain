"""Managed Codex session helpers for codex-brain."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

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
    )
    service.save_session(session)
    return {"session": session.to_dict(), "candidate_count": proposed["candidate_count"], "candidates": proposed["candidates"]}
