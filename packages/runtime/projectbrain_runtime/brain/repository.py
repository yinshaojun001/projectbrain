"""JSONL-backed project-local Brain repository."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from typing import TypeVar

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate, make_brain_id, now_iso

T = TypeVar("T")

_REPOSITORY_LOCKS_GUARD = threading.Lock()
_REPOSITORY_LOCKS: dict[str, threading.RLock] = {}


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
        self.mutation_lock_path = self.root / "transaction.jsonl.lock"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            _write_text_atomic(
                self.manifest_path,
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
        with self._mutation_lock():
            _upsert_jsonl_unlocked(self.knowledge_path, unit.to_dict(), key="id")

    def create_knowledge_unit_with_available_id(self, unit: KnowledgeUnit) -> KnowledgeUnit:
        self.ensure()
        with self._mutation_lock():
            item = _create_jsonl_with_available_key_unlocked(self.knowledge_path, unit.to_dict(), key="id")
        return KnowledgeUnit.from_dict(item)

    def list_knowledge_units(self) -> list[KnowledgeUnit]:
        self.ensure()
        return [KnowledgeUnit.from_dict(item) for item in _read_jsonl(self.knowledge_path)]

    def get_knowledge_unit(self, unit_id: str) -> KnowledgeUnit:
        return _get_by_key(self.list_knowledge_units(), "id", unit_id)

    def save_memory_candidate(self, candidate: MemoryCandidate) -> None:
        self.ensure()
        with self._mutation_lock():
            _upsert_jsonl_unlocked(self.candidates_path, candidate.to_dict(), key="candidate_id")

    def create_memory_candidate_with_available_id(self, candidate: MemoryCandidate) -> MemoryCandidate:
        self.ensure()
        with self._mutation_lock():
            item = _create_jsonl_with_available_key_unlocked(self.candidates_path, candidate.to_dict(), key="candidate_id")
        return MemoryCandidate.from_dict(item)

    def list_memory_candidates(self) -> list[MemoryCandidate]:
        self.ensure()
        return [MemoryCandidate.from_dict(item) for item in _read_jsonl(self.candidates_path)]

    def get_memory_candidate(self, candidate_id: str) -> MemoryCandidate:
        return _get_by_key(self.list_memory_candidates(), "candidate_id", candidate_id)

    def confirm_memory_candidate(self, candidate_id: str) -> tuple[MemoryCandidate, KnowledgeUnit]:
        self.ensure()
        with self._mutation_lock():
            candidate_items = _read_jsonl(self.candidates_path)
            candidate_data = _get_dict_by_key(candidate_items, "candidate_id", candidate_id)
            candidate = MemoryCandidate.from_dict(candidate_data)

            if candidate.review_state == "human_confirmed":
                unit_id = candidate.extraction.get("confirmed_knowledge_unit_id")
                if not unit_id:
                    raise ValueError(f"Confirmed candidate has no linked knowledge unit: {candidate_id}")
                unit_data = _get_dict_by_key(_read_jsonl(self.knowledge_path), "id", str(unit_id))
                return candidate, KnowledgeUnit.from_dict(unit_data)
            if candidate.review_state == "rejected":
                raise ValueError(f"Cannot confirm rejected candidate: {candidate_id}")
            if candidate.review_state != "human_review_required":
                raise ValueError(f"Cannot confirm candidate in state {candidate.review_state}: {candidate_id}")

            proposed = candidate.proposed_unit
            unit = KnowledgeUnit(
                id=make_brain_id("ku", proposed.get("title") or proposed["statement"]),
                type=proposed["type"],
                title=proposed.get("title") or proposed["statement"][:80],
                statement=proposed["statement"],
                summary=proposed.get("summary", ""),
                tags=proposed.get("tags", []),
                applies_to=proposed.get("applies_to", []),
                confidence=float(proposed.get("confidence", 0.8)),
                risk_level=proposed.get("risk_level", "normal"),
                review_state="human_confirmed",
                source={
                    "kind": "conversation",
                    "session_id": candidate.session_id,
                    "candidate_id": candidate.candidate_id,
                    "client": "codex-brain",
                },
                evidence=candidate.evidence,
            )

            knowledge_items = _read_jsonl(self.knowledge_path)
            unit_data = unit.to_dict()
            unit_data["id"] = _available_key(str(unit_data["id"]), {str(existing.get("id")) for existing in knowledge_items})

            extraction = {**candidate.to_dict().get("extraction", {}), "confirmed_knowledge_unit_id": unit_data["id"]}
            updated_candidate = MemoryCandidate.from_dict({
                **candidate.to_dict(),
                "extraction": extraction,
                "review_state": "human_confirmed",
                "updated_at": now_iso(),
            })

            _write_jsonl(self.knowledge_path, [*knowledge_items, unit_data])
            _write_jsonl(self.candidates_path, _replace_by_key(candidate_items, updated_candidate.to_dict(), key="candidate_id"))
            return updated_candidate, KnowledgeUnit.from_dict(unit_data)

    def reject_memory_candidate(self, candidate_id: str) -> MemoryCandidate:
        self.ensure()
        with self._mutation_lock():
            candidate_items = _read_jsonl(self.candidates_path)
            candidate_data = _get_dict_by_key(candidate_items, "candidate_id", candidate_id)
            candidate = MemoryCandidate.from_dict(candidate_data)
            if candidate.review_state == "human_confirmed":
                raise ValueError(f"Cannot reject confirmed candidate: {candidate_id}")
            if candidate.review_state == "rejected":
                return candidate
            if candidate.review_state != "human_review_required":
                raise ValueError(f"Cannot reject candidate in state {candidate.review_state}: {candidate_id}")
            updated_candidate = MemoryCandidate.from_dict({**candidate.to_dict(), "review_state": "rejected", "updated_at": now_iso()})
            _write_jsonl(self.candidates_path, _replace_by_key(candidate_items, updated_candidate.to_dict(), key="candidate_id"))
            return updated_candidate

    def save_conversation_session(self, session: ConversationSession) -> None:
        self.ensure()
        with self._mutation_lock():
            _upsert_jsonl_unlocked(self.sessions_path, session.to_dict(), key="session_id")

    def list_conversation_sessions(self) -> list[ConversationSession]:
        self.ensure()
        return [ConversationSession.from_dict(item) for item in _read_jsonl(self.sessions_path)]

    def get_conversation_session(self, session_id: str) -> ConversationSession:
        return _get_by_key(self.list_conversation_sessions(), "session_id", session_id)

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        with _locked_path(self.mutation_lock_path):
            yield


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
    _write_text_atomic(path, text)


def _upsert_jsonl(path: Path, item: dict, *, key: str) -> None:
    with _locked_jsonl(path):
        _upsert_jsonl_unlocked(path, item, key=key)


def _upsert_jsonl_unlocked(path: Path, item: dict, *, key: str) -> None:
    items = _read_jsonl(path)
    _write_jsonl(path, _replace_by_key(items, item, key=key))


def _create_jsonl_with_available_key(path: Path, item: dict, *, key: str) -> dict:
    with _locked_jsonl(path):
        return _create_jsonl_with_available_key_unlocked(path, item, key=key)


def _create_jsonl_with_available_key_unlocked(path: Path, item: dict, *, key: str) -> dict:
    items = _read_jsonl(path)
    created = dict(item)
    created[key] = _available_key(str(created[key]), {str(existing.get(key)) for existing in items})
    _write_jsonl(path, [*items, created])
    return created


def _replace_by_key(items: list[dict], item: dict, *, key: str) -> list[dict]:
    item_key = item[key]
    replaced = False
    updated = []
    for existing in items:
        if existing.get(key) == item_key:
            if not replaced:
                updated.append(item)
                replaced = True
            continue
        updated.append(existing)
    if not replaced:
        updated.append(item)
    return updated


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
        try:
            temp_file.write(text)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            os.replace(temp_path, path)
            temp_path = None
            _fsync_directory(path.parent)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass


def _fsync_directory(path: Path) -> None:
    try:
        directory_fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


@contextmanager
def _locked_jsonl(path: Path) -> Iterator[None]:
    with _locked_path(path.with_suffix(path.suffix + ".lock")):
        yield


@contextmanager
def _locked_path(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    process_lock = _process_lock_for(lock_path)
    with process_lock:
        with lock_path.open("a", encoding="utf-8") as lock_file:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _process_lock_for(lock_path: Path) -> threading.RLock:
    lock_key = str(lock_path.expanduser().resolve())
    with _REPOSITORY_LOCKS_GUARD:
        lock = _REPOSITORY_LOCKS.get(lock_key)
        if lock is None:
            lock = threading.RLock()
            _REPOSITORY_LOCKS[lock_key] = lock
        return lock


def _available_key(desired_key: str, existing_keys: set[str]) -> str:
    if desired_key not in existing_keys:
        return desired_key
    suffix = 2
    while f"{desired_key}_{suffix}" in existing_keys:
        suffix += 1
    return f"{desired_key}_{suffix}"


def _get_dict_by_key(items: list[dict], key: str, value: str) -> dict:
    for item in items:
        if item.get(key) == value:
            return item
    raise FileNotFoundError(f"Brain record not found: {key}={value}")


def _get_by_key(items: list[T], attr: str, value: str) -> T:
    for item in items:
        if getattr(item, attr) == value:
            return item
    raise FileNotFoundError(f"Brain record not found: {attr}={value}")
