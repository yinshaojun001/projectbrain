"""JSONL-backed project-local Brain repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate, now_iso

T = TypeVar("T")


class BrainRepository:
    """Store project brain data under <project>/.projectbrain/brain/."""

    def __init__(self, project_path: str | Path) -> None:
        self.project_path = Path(project_path).expanduser().resolve()
        self.root = self.project_path / ".projectbrain" / "brain"
        self.manifest_path = self.root / "manifest.json"
        self.knowledge_path = self.root / "knowledge_units.jsonl"
        self.candidates_path = self.root / "memory_candidates.jsonl"
        self.sessions_path = self.root / "conversations.jsonl"
        self.concepts_path = self.root / "concepts.jsonl"
        self.links_path = self.root / "links.jsonl"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            self.manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "projectbrain.brain.v1",
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        for path in (
            self.knowledge_path,
            self.candidates_path,
            self.sessions_path,
            self.concepts_path,
            self.links_path,
        ):
            path.touch(exist_ok=True)

    def save_knowledge_unit(self, unit: KnowledgeUnit) -> None:
        self.ensure()
        _upsert_jsonl(self.knowledge_path, unit.to_dict(), key="id")

    def list_knowledge_units(self) -> list[KnowledgeUnit]:
        self.ensure()
        return [KnowledgeUnit.from_dict(item) for item in _read_jsonl(self.knowledge_path)]

    def get_knowledge_unit(self, unit_id: str) -> KnowledgeUnit:
        return _get_by_key(self.list_knowledge_units(), "id", unit_id)

    def save_memory_candidate(self, candidate: MemoryCandidate) -> None:
        self.ensure()
        _upsert_jsonl(self.candidates_path, candidate.to_dict(), key="candidate_id")

    def list_memory_candidates(self) -> list[MemoryCandidate]:
        self.ensure()
        return [MemoryCandidate.from_dict(item) for item in _read_jsonl(self.candidates_path)]

    def get_memory_candidate(self, candidate_id: str) -> MemoryCandidate:
        return _get_by_key(self.list_memory_candidates(), "candidate_id", candidate_id)

    def save_conversation_session(self, session: ConversationSession) -> None:
        self.ensure()
        _upsert_jsonl(self.sessions_path, session.to_dict(), key="session_id")

    def list_conversation_sessions(self) -> list[ConversationSession]:
        self.ensure()
        return [ConversationSession.from_dict(item) for item in _read_jsonl(self.sessions_path)]

    def get_conversation_session(self, session_id: str) -> ConversationSession:
        return _get_by_key(self.list_conversation_sessions(), "session_id", session_id)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items)
    path.write_text(text, encoding="utf-8")


def _upsert_jsonl(path: Path, item: dict, *, key: str) -> None:
    items = _read_jsonl(path)
    item_key = item[key]
    replaced = False
    updated = []
    for existing in items:
        if existing.get(key) == item_key:
            updated.append(item)
            replaced = True
        else:
            updated.append(existing)
    if not replaced:
        updated.append(item)
    _write_jsonl(path, updated)


def _get_by_key(items: list[T], attr: str, value: str) -> T:
    for item in items:
        if getattr(item, attr) == value:
            return item
    raise FileNotFoundError(f"Brain record not found: {attr}={value}")
