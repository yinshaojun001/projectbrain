"""Data models for durable ProjectBrain project memory."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from projectbrain_runtime.models import now_iso

KNOWLEDGE_TYPES = (
    "constraint",
    "decision",
    "gotcha",
    "workflow",
    "risk",
    "test_guidance",
    "open_question",
    "concept_note",
    "incident",
)

REVIEW_STATES = (
    "draft",
    "ai_inferred",
    "human_review_required",
    "human_confirmed",
    "rejected",
    "archived",
)

STALENESS_STATES = ("fresh", "maybe_stale", "stale", "source_missing")
RISK_LEVELS = ("low", "normal", "medium", "high")


def make_brain_id(prefix: str, text: str, *, max_slug_length: int = 64) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)[:max_slug_length].strip("_")
    return f"{prefix}_{slug or 'memory'}"


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _review_state(value: str | None) -> str:
    normalized = value or "human_review_required"
    if normalized not in REVIEW_STATES:
        raise ValueError(f"Unsupported review_state: {normalized}")
    return normalized


def _knowledge_type(value: str) -> str:
    if value not in KNOWLEDGE_TYPES:
        raise ValueError(f"Unsupported knowledge type: {value}")
    return value


@dataclass(frozen=True)
class KnowledgeUnit:
    id: str
    type: str
    title: str
    statement: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    related_code: list[dict[str, Any]] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.8
    risk_level: str = "normal"
    review_state: str = "human_review_required"
    staleness: dict[str, Any] = field(default_factory=lambda: {"state": "fresh", "reason": None})
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        _knowledge_type(self.type)
        _review_state(self.review_state)
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"Unsupported risk_level: {self.risk_level}")
        state = self.staleness.get("state", "fresh")
        if state not in STALENESS_STATES:
            raise ValueError(f"Unsupported staleness state: {state}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeUnit":
        return cls(
            id=data["id"],
            type=data["type"],
            title=data.get("title") or data["statement"][:80],
            statement=data["statement"],
            summary=data.get("summary", ""),
            tags=_string_list(data.get("tags", [])),
            applies_to=_string_list(data.get("applies_to", [])),
            related_code=_dict_list(data.get("related_code", [])),
            source=dict(data.get("source", {})),
            evidence=_dict_list(data.get("evidence", [])),
            confidence=float(data.get("confidence", 0.8)),
            risk_level=data.get("risk_level", "normal"),
            review_state=data.get("review_state", "human_review_required"),
            staleness=dict(data.get("staleness", {"state": "fresh", "reason": None})),
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
        )


@dataclass(frozen=True)
class MemoryCandidate:
    candidate_id: str
    project_id: str
    session_id: str | None
    proposed_unit: dict[str, Any]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    extraction: dict[str, Any] = field(default_factory=lambda: {
        "method": "codex_brain_exit_extraction",
        "client": "codex-brain",
        "created_at": now_iso(),
    })
    review_state: str = "human_review_required"
    possible_duplicates: list[dict[str, Any]] = field(default_factory=list)
    conflicts_with: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        _review_state(self.review_state)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryCandidate":
        return cls(
            candidate_id=data["candidate_id"],
            project_id=data["project_id"],
            session_id=data.get("session_id"),
            proposed_unit=dict(data["proposed_unit"]),
            evidence=_dict_list(data.get("evidence", [])),
            extraction=dict(data.get("extraction", {
                "method": "codex_brain_exit_extraction",
                "client": "codex-brain",
                "created_at": now_iso(),
            })),
            review_state=data.get("review_state", "human_review_required"),
            possible_duplicates=_dict_list(data.get("possible_duplicates", [])),
            conflicts_with=_dict_list(data.get("conflicts_with", [])),
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
        )


@dataclass(frozen=True)
class ConversationSession:
    session_id: str
    project_id: str
    task: str = ""
    summary: str = ""
    client: str = "codex-brain"
    started_at: str = field(default_factory=now_iso)
    ended_at: str | None = None
    changed_files: list[str] = field(default_factory=list)
    candidate_ids: list[str] = field(default_factory=list)
    knowledge_unit_ids: list[str] = field(default_factory=list)
    privacy: dict[str, Any] = field(default_factory=lambda: {
        "stores_full_transcript": False,
        "stores_excerpts": True,
    })

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationSession":
        return cls(
            session_id=data["session_id"],
            project_id=data["project_id"],
            task=data.get("task", ""),
            summary=data.get("summary", ""),
            client=data.get("client", "codex-brain"),
            started_at=data.get("started_at", now_iso()),
            ended_at=data.get("ended_at"),
            changed_files=_string_list(data.get("changed_files", [])),
            candidate_ids=_string_list(data.get("candidate_ids", [])),
            knowledge_unit_ids=_string_list(data.get("knowledge_unit_ids", [])),
            privacy=dict(data.get("privacy", {"stores_full_transcript": False, "stores_excerpts": True})),
        )
