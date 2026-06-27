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


def infer_task_type(task: str) -> str:
    lowered = task.lower()
    if "review" in lowered or "审查" in task:
        return "review"
    if "debug" in lowered or "排查" in task:
        return "debug"
    if "change" in lowered or "修改" in task:
        return "modify"
    if "explain" in lowered or "解释" in task:
        return "explain"
    return "general"


def bundle_summary(context_pack: dict[str, Any]) -> str:
    recommended_files = context_pack.get("recommended_files", [])
    if recommended_files:
        first_item = recommended_files[0]
        file_name = first_item.get("file") or "unknown file"
        reason = first_item.get("reason")
        if reason:
            return f"Start with {file_name}: {reason}"
        return f"Start with {file_name}."
    return context_pack.get("summary") or "No relevant files were identified yet."


def bundle_from_context_pack(
    *,
    project_id: str,
    task: str,
    context_pack: dict[str, Any],
) -> TaskUnderstandingBundle:
    return TaskUnderstandingBundle(
        bundle_id=f"{project_id}:{task}",
        project_id=project_id,
        task=task,
        task_type=infer_task_type(task),
        summary=bundle_summary(context_pack),
        relevant_files=[
            {
                "path": item.get("file", ""),
                "reason": item.get("reason", ""),
                "confidence": item.get("confidence", 0.0),
            }
            for item in context_pack.get("recommended_files", [])
        ],
        relevant_symbols=[
            {
                "symbol": item.get("qualified_name", ""),
                "kind": item.get("entity_type", ""),
                "path": item.get("file", ""),
                "reason": item.get("reason", ""),
                "confidence": item.get("confidence", 0.0),
            }
            for item in context_pack.get("recommended_symbols", [])
        ],
        risk_warnings=[
            {
                "message": warning if isinstance(warning, str) else warning.get("message", ""),
                "confidence": warning.get("confidence") if isinstance(warning, dict) else None,
            }
            for warning in context_pack.get("warnings", [])
        ],
        test_suggestions=[
            {
                "symbol": item.get("qualified_name", ""),
                "path": item.get("file", ""),
                "reason": item.get("reason", ""),
            }
            for item in context_pack.get("recommended_tests", [])
        ],
        quality_notes=[
            {
                "message": omission if isinstance(omission, str) else omission.get("message", ""),
                "confidence": omission.get("confidence") if isinstance(omission, dict) else None,
            }
            for omission in context_pack.get("omissions", [])
        ],
    )
