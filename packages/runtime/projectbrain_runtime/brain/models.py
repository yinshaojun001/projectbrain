"""Data models for durable ProjectBrain project memory."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from math import isfinite
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


# These wrappers prevent accidental public mutation of frozen dataclass fields.
# They are not intended as a security boundary against deliberate base-class bypasses.
class _ImmutableList(list):
    def _readonly(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("brain model containers are immutable")

    append = _readonly
    clear = _readonly
    extend = _readonly
    insert = _readonly
    pop = _readonly
    remove = _readonly
    reverse = _readonly
    sort = _readonly
    __delitem__ = _readonly
    __iadd__ = _readonly
    __imul__ = _readonly
    __setitem__ = _readonly


class _ImmutableDict(dict):
    def _readonly(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("brain model containers are immutable")

    clear = _readonly
    pop = _readonly
    popitem = _readonly
    setdefault = _readonly
    update = _readonly
    __delitem__ = _readonly
    __ior__ = _readonly
    __setitem__ = _readonly


def make_brain_id(prefix: str, text: str, *, max_slug_length: int = 64) -> str:
    # Stable readable ID helper; callers still own global uniqueness.
    safe_prefix = re.sub(r"[^a-zA-Z0-9]+", "_", str(prefix).strip().lower()).strip("_")
    safe_prefix = re.sub(r"_+", "_", safe_prefix) or "memory"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(text).strip().lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if slug and len(slug) <= max_slug_length:
        return f"{safe_prefix}_{slug}"
    base_slug = slug[:max_slug_length].strip("_") or "memory"
    digest = sha256(str(text).encode("utf-8")).hexdigest()[:12]
    return f"{safe_prefix}_{base_slug}_{digest}"


def _required_string(name: str, value: Any) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _confidence(value: Any) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be between 0 and 1") from exc
    if not isfinite(normalized) or normalized < 0 or normalized > 1:
        raise ValueError("confidence must be between 0 and 1")
    return normalized


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [deepcopy(item) for item in value if isinstance(item, dict)]


def _dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return {}
    return deepcopy(value)


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return _ImmutableDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return _ImmutableList(_freeze(item) for item in value)
    return deepcopy(value)


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return deepcopy(value)


def _review_state(value: str | None) -> str:
    normalized = str(value).strip() if value is not None else ""
    normalized = normalized or "human_review_required"
    if normalized not in REVIEW_STATES:
        raise ValueError(f"Unsupported review_state: {normalized}")
    return normalized


def _knowledge_type(value: str) -> str:
    if value not in KNOWLEDGE_TYPES:
        raise ValueError(f"Unsupported knowledge type: {value}")
    return value


def _proposed_unit(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise ValueError("proposed_unit must be a non-empty dict")
    normalized = deepcopy(value)
    normalized["type"] = _required_string("proposed_unit.type", normalized.get("type"))
    _knowledge_type(normalized["type"])
    normalized["statement"] = _required_string("proposed_unit.statement", normalized.get("statement"))
    if "title" in normalized:
        normalized["title"] = _required_string("proposed_unit.title", normalized.get("title"))
    if "confidence" in normalized:
        normalized["confidence"] = _confidence(normalized["confidence"])
    if "tags" in normalized:
        normalized["tags"] = _string_list(normalized["tags"])
    if "applies_to" in normalized:
        normalized["applies_to"] = _string_list(normalized["applies_to"])
    return normalized


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
        object.__setattr__(self, "id", _required_string("id", self.id))
        object.__setattr__(self, "type", _required_string("type", self.type))
        object.__setattr__(self, "title", _required_string("title", self.title))
        object.__setattr__(self, "statement", _required_string("statement", self.statement))
        object.__setattr__(self, "summary", str(self.summary or ""))
        object.__setattr__(self, "tags", _freeze(_string_list(self.tags)))
        object.__setattr__(self, "applies_to", _freeze(_string_list(self.applies_to)))
        object.__setattr__(self, "related_code", _freeze(_dict_list(self.related_code)))
        object.__setattr__(self, "source", _freeze(_dict(self.source)))
        object.__setattr__(self, "evidence", _freeze(_dict_list(self.evidence)))
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        object.__setattr__(self, "staleness", _freeze(_dict(self.staleness) or {"state": "fresh", "reason": None}))
        _knowledge_type(self.type)
        object.__setattr__(self, "review_state", _review_state(self.review_state))
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"Unsupported risk_level: {self.risk_level}")
        state = self.staleness.get("state", "fresh")
        if state not in STALENESS_STATES:
            raise ValueError(f"Unsupported staleness state: {state}")

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))

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
            source=_dict(data.get("source")),
            evidence=_dict_list(data.get("evidence", [])),
            confidence=_confidence(data.get("confidence", 0.8)),
            risk_level=data.get("risk_level", "normal"),
            review_state=data.get("review_state", "human_review_required"),
            staleness=_dict(data.get("staleness")) or {"state": "fresh", "reason": None},
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
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
        object.__setattr__(self, "candidate_id", _required_string("candidate_id", self.candidate_id))
        object.__setattr__(self, "project_id", _required_string("project_id", self.project_id))
        if self.session_id is not None:
            object.__setattr__(self, "session_id", _required_string("session_id", self.session_id))
        object.__setattr__(self, "proposed_unit", _freeze(_proposed_unit(self.proposed_unit)))
        object.__setattr__(self, "evidence", _freeze(_dict_list(self.evidence)))
        object.__setattr__(self, "extraction", _freeze(_dict(self.extraction)))
        object.__setattr__(self, "possible_duplicates", _freeze(_dict_list(self.possible_duplicates)))
        object.__setattr__(self, "conflicts_with", _freeze(_dict_list(self.conflicts_with)))
        object.__setattr__(self, "review_state", _review_state(self.review_state))

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryCandidate":
        return cls(
            candidate_id=data["candidate_id"],
            project_id=data["project_id"],
            session_id=data.get("session_id"),
            proposed_unit=_dict(data.get("proposed_unit")),
            evidence=_dict_list(data.get("evidence", [])),
            extraction=dict(data.get("extraction") or {
                "method": "codex_brain_exit_extraction",
                "client": "codex-brain",
                "created_at": now_iso(),
            }),
            review_state=data.get("review_state", "human_review_required"),
            possible_duplicates=_dict_list(data.get("possible_duplicates", [])),
            conflicts_with=_dict_list(data.get("conflicts_with", [])),
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _required_string("session_id", self.session_id))
        object.__setattr__(self, "project_id", _required_string("project_id", self.project_id))
        object.__setattr__(self, "task", str(self.task or ""))
        object.__setattr__(self, "summary", str(self.summary or ""))
        object.__setattr__(self, "client", str(self.client or "codex-brain"))
        object.__setattr__(self, "changed_files", _freeze(_string_list(self.changed_files)))
        object.__setattr__(self, "candidate_ids", _freeze(_string_list(self.candidate_ids)))
        object.__setattr__(self, "knowledge_unit_ids", _freeze(_string_list(self.knowledge_unit_ids)))
        object.__setattr__(self, "privacy", _freeze(_dict(self.privacy) or {
            "stores_full_transcript": False,
            "stores_excerpts": True,
        }))

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationSession":
        return cls(
            session_id=data["session_id"],
            project_id=data["project_id"],
            task=data.get("task", ""),
            summary=data.get("summary", ""),
            client=data.get("client", "codex-brain"),
            started_at=data.get("started_at") or now_iso(),
            ended_at=data.get("ended_at"),
            changed_files=_string_list(data.get("changed_files", [])),
            candidate_ids=_string_list(data.get("candidate_ids", [])),
            knowledge_unit_ids=_string_list(data.get("knowledge_unit_ids", [])),
            privacy=dict(data.get("privacy") or {"stores_full_transcript": False, "stores_excerpts": True}),
        )
