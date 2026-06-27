"""Task Understanding Bundle schema for ProjectBrain V1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TaskUnderstandingBundle:
    bundle_id: str
    project_id: str
    task: str
    task_type: str
    summary: str
    bundle_type: str = "task_understanding"
    relevant_files: list[dict[str, Any]] = field(default_factory=list)
    relevant_symbols: list[dict[str, Any]] = field(default_factory=list)
    entry_flows: list[dict[str, Any]] = field(default_factory=list)
    impact_hints: list[dict[str, Any]] = field(default_factory=list)
    risk_warnings: list[dict[str, Any]] = field(default_factory=list)
    human_claims: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {"verified": [], "likely_relevant": [], "needs_review": []}
    )
    linked_evidence: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {"verified": [], "likely_relevant": [], "needs_review": []}
    )
    test_suggestions: list[dict[str, Any]] = field(default_factory=list)
    unknowns: list[dict[str, Any]] = field(default_factory=list)
    quality_notes: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
