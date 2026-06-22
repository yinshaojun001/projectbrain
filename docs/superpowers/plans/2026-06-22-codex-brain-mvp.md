# codex-brain MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first codex-brain MVP: a ProjectBrain-backed local project memory store, candidate review queue, Brain Explorer UI, and a `codex-brain` command that can run a managed Codex CLI session and persist extracted memory candidates.

**Architecture:** Add a focused `projectbrain_runtime.brain` module that owns durable project-brain models, JSONL storage, search, candidates, and session records. Expose this through CLI commands, API handlers, HTMX UI pages, MCP tools, and a new `codex-brain` script that uses injectable process/session components so tests do not need a real Codex binary.

**Tech Stack:** Python 3.11+ standard library, unittest, FastAPI/Jinja/HTMX existing UI stack, existing JSON runtime storage, local filesystem only.

---

## Scope

This plan implements Phase 1 from the accepted spec:

- `KnowledgeUnit`, `MemoryCandidate`, and `ConversationSession` data models.
- Project-local `.projectbrain/brain/` JSONL store under each imported/opened project.
- Brain service operations: remember, search, list, propose candidates, confirm/reject candidates, record sessions.
- CLI commands under `projectbrain brain ...`.
- First Brain API endpoints and HTMX Brain Explorer pages.
- MCP tools for memory and candidates.
- `codex-brain` entrypoint with a testable managed-session runner.

This plan does not implement desktop packaging, Claude Code support, vector search, relationship graph visualization, or automatic background capture of ordinary `codex` sessions.

---

## File Structure

### New runtime brain package

- Create: `packages/runtime/projectbrain_runtime/brain/__init__.py`
  - Re-export public brain models and service functions.
- Create: `packages/runtime/projectbrain_runtime/brain/models.py`
  - Dataclasses and constants for `KnowledgeUnit`, `MemoryCandidate`, `ConversationSession`, review states, knowledge types, staleness states, risk levels.
- Create: `packages/runtime/projectbrain_runtime/brain/repository.py`
  - JSONL repository rooted at a project source path: `<project>/.projectbrain/brain/`.
- Create: `packages/runtime/projectbrain_runtime/brain/service.py`
  - Business operations: remember, search, list, propose candidates, confirm/reject, sessions.
- Create: `packages/runtime/projectbrain_runtime/brain/search.py`
  - Local lexical scoring and filtering.
- Create: `packages/runtime/projectbrain_runtime/brain/extraction.py`
  - Robust parser for Codex extraction JSON output.

### New codex-brain CLI package

- Create: `packages/runtime/projectbrain_cli/codex_brain.py`
  - Entry point for `codex-brain`, argument parsing, project detection, app launch hook, managed Codex session orchestration.
- Create: `packages/runtime/projectbrain_cli/codex_session.py`
  - Testable session runner abstractions: `CommandResult`, `ManagedSessionResult`, `run_codex_session`, extraction prompt builder.

### Modify existing runtime and CLI

- Modify: `pyproject.toml`
  - Add script entry point `codex-brain = "projectbrain_cli.codex_brain:main"`.
- Modify: `packages/runtime/projectbrain_cli/main.py`
  - Add `brain` subcommands.
- Modify: `packages/runtime/projectbrain_runtime/service.py`
  - Add wrapper methods that locate a project and delegate to `BrainService`.
- Modify: `packages/runtime/projectbrain_cli/mcp_server.py`
  - Add memory/candidate tools.

### API and UI

- Modify: `apps/api/projectbrain_api/handlers.py`
  - Add brain API handler functions.
- Modify: `apps/api/projectbrain_api/main.py`
  - Add brain API routes.
- Modify: `apps/api/projectbrain_api/ui/router.py`
  - Add Brain Explorer UI routes.
- Create: `apps/api/projectbrain_api/ui/templates/projects/brain.html`
  - Brain Explorer page.
- Create: `apps/api/projectbrain_api/ui/templates/_partials/brain_knowledge_list.html`
  - HTMX partial for knowledge search results.
- Create: `apps/api/projectbrain_api/ui/templates/_partials/brain_candidate_list.html`
  - HTMX partial for candidates.
- Modify: `apps/api/projectbrain_api/ui/templates/projects/index.html`
  - Add Brain links in project table.
- Modify: `apps/api/projectbrain_api/ui/templates/projects/context.html`, `impact.html`, `policy.html`
  - Add Brain subnav link.

### Tests

- Create: `tests/test_brain_models.py`
- Create: `tests/test_brain_repository.py`
- Create: `tests/test_brain_service.py`
- Create: `tests/test_brain_cli.py`
- Create: `tests/test_codex_brain.py`
- Create: `tests/test_brain_api.py`
- Create: `tests/test_brain_ui.py`
- Modify: `tests/test_mcp_server.py`

---

## Task 1: Brain Models

**Files:**
- Create: `packages/runtime/projectbrain_runtime/brain/__init__.py`
- Create: `packages/runtime/projectbrain_runtime/brain/models.py`
- Create: `tests/test_brain_models.py`

- [ ] **Step 1: Write failing tests for brain model defaults and serialization**

Create `tests/test_brain_models.py`:

```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.brain.models import (  # noqa: E402
    ConversationSession,
    KnowledgeUnit,
    MemoryCandidate,
    make_brain_id,
)


class BrainModelsTest(unittest.TestCase):
    def test_knowledge_unit_round_trips_with_defaults(self):
        unit = KnowledgeUnit(
            id="ku_refund_fee",
            type="constraint",
            title="退款手续费不能影响结算本金",
            statement="Refund handling fee must not change settlement principal amount.",
            tags=["refund", "settlement"],
            applies_to=["RefundService"],
        )

        data = unit.to_dict()
        restored = KnowledgeUnit.from_dict(data)

        self.assertEqual(restored.id, "ku_refund_fee")
        self.assertEqual(restored.review_state, "human_review_required")
        self.assertEqual(restored.staleness["state"], "fresh")
        self.assertEqual(restored.tags, ["refund", "settlement"])
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_memory_candidate_confirm_source_fields_exist(self):
        candidate = MemoryCandidate(
            candidate_id="mc_refund_fee",
            project_id="payment",
            session_id="session_codex",
            proposed_unit={
                "type": "constraint",
                "title": "退款手续费不能影响结算本金",
                "statement": "Refund fee must be booked separately.",
                "tags": ["refund"],
                "applies_to": ["RefundService"],
                "confidence": 0.9,
            },
        )

        data = candidate.to_dict()
        restored = MemoryCandidate.from_dict(data)

        self.assertEqual(restored.review_state, "human_review_required")
        self.assertEqual(restored.extraction["method"], "codex_brain_exit_extraction")
        self.assertEqual(restored.proposed_unit["type"], "constraint")

    def test_conversation_session_round_trips(self):
        session = ConversationSession(
            session_id="session_20260622_codex",
            project_id="payment",
            task="Add refund fee",
            summary="Clarified refund fee settlement constraints.",
            changed_files=["service/refund/RefundService.java"],
        )

        restored = ConversationSession.from_dict(session.to_dict())

        self.assertEqual(restored.client, "codex-brain")
        self.assertFalse(restored.privacy["stores_full_transcript"])
        self.assertEqual(restored.changed_files, ["service/refund/RefundService.java"])

    def test_make_brain_id_is_stable_and_safe(self):
        self.assertEqual(
            make_brain_id("ku", "Refund fee must not change settlement principal!"),
            "ku_refund_fee_must_not_change_settlement_principal",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run model tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_brain_models -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'projectbrain_runtime.brain'`.

- [ ] **Step 3: Implement brain models**

Create `packages/runtime/projectbrain_runtime/brain/__init__.py`:

```python
"""ProjectBrain durable project-brain storage and memory models."""

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate

__all__ = ["ConversationSession", "KnowledgeUnit", "MemoryCandidate"]
```

Create `packages/runtime/projectbrain_runtime/brain/models.py`:

```python
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
```

- [ ] **Step 4: Run model tests**

Run:

```bash
python3 -m unittest tests.test_brain_models -v
```

Expected: PASS.

- [ ] **Step 5: Commit brain models**

```bash
git add packages/runtime/projectbrain_runtime/brain/__init__.py packages/runtime/projectbrain_runtime/brain/models.py tests/test_brain_models.py
git commit -m "feat: add project brain memory models"
```

---

## Task 2: JSONL Brain Repository

**Files:**
- Create: `packages/runtime/projectbrain_runtime/brain/repository.py`
- Create: `tests/test_brain_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/test_brain_repository.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate  # noqa: E402
from projectbrain_runtime.brain.repository import BrainRepository  # noqa: E402


class BrainRepositoryTest(unittest.TestCase):
    def test_repository_creates_project_brain_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()

            self.assertTrue((Path(tmp) / ".projectbrain/brain/manifest.json").exists())
            self.assertTrue((Path(tmp) / ".projectbrain/brain/knowledge_units.jsonl").exists())
            self.assertTrue((Path(tmp) / ".projectbrain/brain/memory_candidates.jsonl").exists())
            self.assertTrue((Path(tmp) / ".projectbrain/brain/conversations.jsonl").exists())

    def test_save_and_list_knowledge_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_knowledge_unit(KnowledgeUnit(
                id="ku_refund",
                type="constraint",
                title="Refund constraint",
                statement="Refund fee must be booked separately.",
            ))

            units = repo.list_knowledge_units()

            self.assertEqual([unit.id for unit in units], ["ku_refund"])

    def test_update_candidate_replaces_existing_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_memory_candidate(MemoryCandidate(
                candidate_id="mc_refund",
                project_id="payment",
                session_id="session1",
                proposed_unit={"type": "constraint", "statement": "Refund fee rule"},
            ))
            repo.save_memory_candidate(MemoryCandidate(
                candidate_id="mc_refund",
                project_id="payment",
                session_id="session1",
                proposed_unit={"type": "constraint", "statement": "Refund fee rule"},
                review_state="rejected",
            ))

            candidates = repo.list_memory_candidates()

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].review_state, "rejected")

    def test_save_and_get_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_conversation_session(ConversationSession(
                session_id="session1",
                project_id="payment",
                summary="Captured refund discussion.",
            ))

            session = repo.get_conversation_session("session1")

            self.assertEqual(session.summary, "Captured refund discussion.")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run repository tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_brain_repository -v
```

Expected: FAIL with `ModuleNotFoundError` for `projectbrain_runtime.brain.repository`.

- [ ] **Step 3: Implement JSONL repository**

Create `packages/runtime/projectbrain_runtime/brain/repository.py`:

```python
"""JSONL-backed project-local Brain repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

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
```

- [ ] **Step 4: Run repository tests**

Run:

```bash
python3 -m unittest tests.test_brain_repository -v
```

Expected: PASS.

- [ ] **Step 5: Commit repository**

```bash
git add packages/runtime/projectbrain_runtime/brain/repository.py tests/test_brain_repository.py
git commit -m "feat: add project-local brain repository"
```

---

## Task 3: Brain Search and Service

**Files:**
- Create: `packages/runtime/projectbrain_runtime/brain/search.py`
- Create: `packages/runtime/projectbrain_runtime/brain/service.py`
- Create: `tests/test_brain_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_brain_service.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.brain.repository import BrainRepository  # noqa: E402
from projectbrain_runtime.brain.service import BrainService  # noqa: E402


class BrainServiceTest(unittest.TestCase):
    def test_remember_creates_searchable_knowledge_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            result = service.remember(
                type="constraint",
                statement="Refund handling fee must not change settlement principal amount.",
                title="退款手续费不能影响结算本金",
                tags=["refund", "settlement"],
                applies_to=["RefundService"],
                review_state="human_confirmed",
            )

            search = service.search("refund settlement")

            self.assertEqual(result["knowledge_unit"]["review_state"], "human_confirmed")
            self.assertEqual(search["matches"][0]["id"], result["knowledge_unit"]["id"])

    def test_propose_memories_creates_candidates_with_duplicate_hints(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            service.remember(
                type="constraint",
                statement="Refund fee must not affect settlement principal.",
                tags=["refund", "settlement"],
                applies_to=["RefundService"],
            )
            result = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[
                    {
                        "type": "constraint",
                        "statement": "Refund fee must not affect settlement principal.",
                        "tags": ["refund", "settlement"],
                        "applies_to": ["RefundService"],
                        "confidence": 0.9,
                    }
                ],
            )

            candidate = result["candidates"][0]

            self.assertEqual(candidate["review_state"], "human_review_required")
            self.assertTrue(candidate["possible_duplicates"])

    def test_confirm_candidate_creates_knowledge_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            candidate = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[
                    {
                        "type": "gotcha",
                        "statement": "account_record is append-only.",
                        "tags": ["account"],
                    }
                ],
            )["candidates"][0]

            result = service.confirm_candidate(candidate["candidate_id"])

            self.assertEqual(result["candidate"]["review_state"], "human_confirmed")
            self.assertEqual(result["knowledge_unit"]["type"], "gotcha")
            self.assertEqual(service.list_knowledge()["knowledge_units"][0]["statement"], "account_record is append-only.")

    def test_reject_candidate_updates_state_without_creating_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            candidate = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "risk", "statement": "Temporary speculation."}],
            )["candidates"][0]

            service.reject_candidate(candidate["candidate_id"])

            self.assertEqual(service.list_candidates(review_state="rejected")["candidates"][0]["review_state"], "rejected")
            self.assertEqual(service.list_knowledge()["knowledge_units"], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run service tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_brain_service -v
```

Expected: FAIL with `ModuleNotFoundError` for `projectbrain_runtime.brain.service`.

- [ ] **Step 3: Implement lexical search**

Create `packages/runtime/projectbrain_runtime/brain/search.py`:

```python
"""Local lexical search for ProjectBrain memory."""

from __future__ import annotations

import re
from typing import Any


def search_knowledge(units: list[dict[str, Any]], query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    terms = _terms(query)
    scored = []
    for unit in units:
        score = _score_unit(unit, terms)
        if score > 0 or not terms:
            item = dict(unit)
            item["search_score"] = score
            scored.append(item)
    scored.sort(key=lambda item: (-item["search_score"], item.get("updated_at", ""), item.get("id", "")))
    return scored[:limit]


def filter_items(
    items: list[dict[str, Any]],
    *,
    type: str | None = None,
    review_state: str | None = None,
    staleness: str | None = None,
    tag: str | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    selected = []
    for item in items:
        if not include_archived and item.get("review_state") == "archived":
            continue
        if type and item.get("type") != type:
            continue
        if review_state and item.get("review_state") != review_state:
            continue
        if staleness and item.get("staleness", {}).get("state") != staleness:
            continue
        if tag and tag not in item.get("tags", []):
            continue
        selected.append(item)
    return selected


def _score_unit(unit: dict[str, Any], terms: list[str]) -> int:
    text = " ".join(
        [
            str(unit.get("title", "")),
            str(unit.get("statement", "")),
            str(unit.get("summary", "")),
            " ".join(unit.get("tags", [])),
            " ".join(unit.get("applies_to", [])),
            " ".join(str(code.get("file", "")) + " " + str(code.get("symbol", "")) for code in unit.get("related_code", [])),
        ]
    ).lower()
    score = 0
    for term in terms:
        if term in unit.get("tags", []):
            score += 8
        if term in " ".join(unit.get("applies_to", [])).lower():
            score += 6
        if term in text:
            score += 3
    if unit.get("review_state") == "human_confirmed":
        score += 2
    if unit.get("risk_level") == "high":
        score += 2
    return score


def _terms(query: str) -> list[str]:
    return [term for term in re.split(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", query.lower()) if term]
```

- [ ] **Step 4: Implement brain service**

Create `packages/runtime/projectbrain_runtime/brain/service.py`:

```python
"""Business operations for project-local Brain memory."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate, make_brain_id, now_iso
from projectbrain_runtime.brain.repository import BrainRepository
from projectbrain_runtime.brain.search import filter_items, search_knowledge


class BrainService:
    def __init__(self, repository: BrainRepository) -> None:
        self.repository = repository
        self.repository.ensure()

    def remember(
        self,
        *,
        type: str,
        statement: str,
        title: str | None = None,
        summary: str = "",
        tags: list[str] | None = None,
        applies_to: list[str] | None = None,
        review_state: str = "human_review_required",
        confidence: float = 0.8,
        risk_level: str = "normal",
        source: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        unit_id: str | None = None,
    ) -> dict[str, Any]:
        unit = KnowledgeUnit(
            id=unit_id or make_brain_id("ku", title or statement),
            type=type,
            title=title or statement[:80],
            statement=statement,
            summary=summary,
            tags=tags or [],
            applies_to=applies_to or [],
            review_state=review_state,
            confidence=confidence,
            risk_level=risk_level,
            source=source or {},
            evidence=evidence or [],
        )
        self.repository.save_knowledge_unit(unit)
        return {"knowledge_unit": unit.to_dict()}

    def list_knowledge(
        self,
        *,
        type: str | None = None,
        review_state: str | None = None,
        staleness: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        units = [unit.to_dict() for unit in self.repository.list_knowledge_units()]
        selected = filter_items(
            units,
            type=type,
            review_state=review_state,
            staleness=staleness,
            tag=tag,
            include_archived=include_archived,
        )
        return {"knowledge_units": selected, "knowledge_unit_count": len(selected)}

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        units = [unit.to_dict() for unit in self.repository.list_knowledge_units()]
        return {"query": query, "matches": search_knowledge(units, query, limit=limit)}

    def propose_memories(
        self,
        *,
        project_id: str,
        session_id: str | None,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        saved = []
        for candidate_data in candidates:
            statement = candidate_data["statement"]
            candidate = MemoryCandidate(
                candidate_id=make_brain_id("mc", candidate_data.get("title") or statement),
                project_id=project_id,
                session_id=session_id,
                proposed_unit=dict(candidate_data),
                evidence=candidate_data.get("evidence", []),
                possible_duplicates=self._possible_duplicates(candidate_data),
            )
            self.repository.save_memory_candidate(candidate)
            saved.append(candidate.to_dict())
        return {"candidates": saved, "candidate_count": len(saved)}

    def list_candidates(self, *, review_state: str | None = None) -> dict[str, Any]:
        candidates = [candidate.to_dict() for candidate in self.repository.list_memory_candidates()]
        if review_state:
            candidates = [candidate for candidate in candidates if candidate.get("review_state") == review_state]
        return {"candidates": candidates, "candidate_count": len(candidates)}

    def confirm_candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.repository.get_memory_candidate(candidate_id)
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
            source={"kind": "conversation", "session_id": candidate.session_id, "candidate_id": candidate.candidate_id, "client": "codex-brain"},
            evidence=candidate.evidence,
        )
        updated_candidate = replace(candidate, review_state="human_confirmed", updated_at=now_iso())
        self.repository.save_memory_candidate(updated_candidate)
        self.repository.save_knowledge_unit(unit)
        return {"candidate": updated_candidate.to_dict(), "knowledge_unit": unit.to_dict()}

    def reject_candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.repository.get_memory_candidate(candidate_id)
        updated_candidate = replace(candidate, review_state="rejected", updated_at=now_iso())
        self.repository.save_memory_candidate(updated_candidate)
        return {"candidate": updated_candidate.to_dict()}

    def save_session(self, session: ConversationSession) -> dict[str, Any]:
        self.repository.save_conversation_session(session)
        return {"session": session.to_dict()}

    def list_sessions(self) -> dict[str, Any]:
        sessions = [session.to_dict() for session in self.repository.list_conversation_sessions()]
        return {"sessions": sessions, "session_count": len(sessions)}

    def summary(self) -> dict[str, Any]:
        units = self.list_knowledge(include_archived=True)["knowledge_units"]
        candidates = self.list_candidates(review_state="human_review_required")["candidates"]
        by_type: dict[str, int] = {}
        by_review_state: dict[str, int] = {}
        for unit in units:
            by_type[unit["type"]] = by_type.get(unit["type"], 0) + 1
            state = unit.get("review_state", "human_review_required")
            by_review_state[state] = by_review_state.get(state, 0) + 1
        return {
            "knowledge_unit_count": len(units),
            "candidate_count": len(candidates),
            "by_type": by_type,
            "by_review_state": by_review_state,
        }

    def _possible_duplicates(self, candidate_data: dict[str, Any]) -> list[dict[str, Any]]:
        candidate_terms = set(_tokens(candidate_data.get("statement", ""))) | set(candidate_data.get("tags", []))
        duplicates = []
        for unit in self.repository.list_knowledge_units():
            unit_terms = set(_tokens(unit.statement)) | set(unit.tags)
            if not candidate_terms or not unit_terms:
                continue
            overlap = len(candidate_terms & unit_terms) / max(len(candidate_terms | unit_terms), 1)
            if overlap >= 0.45:
                duplicates.append({"knowledge_unit_id": unit.id, "similarity": round(overlap, 2), "statement": unit.statement})
        return duplicates


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in value.replace(".", " ").replace(",", " ").split() if token.strip()]
```

- [ ] **Step 5: Run service tests**

Run:

```bash
python3 -m unittest tests.test_brain_service -v
```

Expected: PASS.

- [ ] **Step 6: Run all brain tests so far**

Run:

```bash
python3 -m unittest tests.test_brain_models tests.test_brain_repository tests.test_brain_service -v
```

Expected: PASS.

- [ ] **Step 7: Commit brain service**

```bash
git add packages/runtime/projectbrain_runtime/brain/search.py packages/runtime/projectbrain_runtime/brain/service.py tests/test_brain_service.py
git commit -m "feat: add brain memory service"
```

---

## Task 4: Runtime Integration and Brain CLI Commands

**Files:**
- Modify: `packages/runtime/projectbrain_runtime/service.py`
- Modify: `packages/runtime/projectbrain_cli/main.py`
- Create: `tests/test_brain_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_brain_cli.py`:

```python
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))

from projectbrain_cli.main import main  # noqa: E402


class BrainCliTest(unittest.TestCase):
    def test_brain_remember_list_search_and_confirm_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            store_root = str(Path(tmp) / "store")

            remember = _run_cli([
                "--store-root", store_root,
                "brain", "remember", str(project_path),
                "--id", "payment",
                "--type", "constraint",
                "--statement", "Refund fee must not affect settlement principal.",
                "--tag", "refund",
                "--applies-to", "RefundService",
                "--review-state", "human_confirmed",
            ])
            self.assertEqual(remember["knowledge_unit"]["review_state"], "human_confirmed")

            listed = _run_cli(["--store-root", store_root, "brain", "list", str(project_path)])
            self.assertEqual(listed["knowledge_unit_count"], 1)

            search = _run_cli(["--store-root", store_root, "brain", "search", str(project_path), "refund"])
            self.assertEqual(search["matches"][0]["review_state"], "human_confirmed")

            proposed = _run_cli([
                "--store-root", store_root,
                "brain", "propose", str(project_path),
                "--id", "payment",
                "--type", "gotcha",
                "--statement", "account_record is append-only.",
                "--tag", "account",
            ])
            candidate_id = proposed["candidates"][0]["candidate_id"]

            confirmed = _run_cli([
                "--store-root", store_root,
                "brain", "confirm-candidate", str(project_path), candidate_id,
            ])
            self.assertEqual(confirmed["knowledge_unit"]["type"], "gotcha")


def _run_cli(args):
    stdout = StringIO()
    with redirect_stdout(stdout):
        return_code = main(args)
    if return_code != 0:
        raise AssertionError(f"CLI returned {return_code}")
    return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run CLI brain test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_brain_cli -v
```

Expected: FAIL because `brain` subcommand is not registered.

- [ ] **Step 3: Add runtime BrainService helpers**

Modify `packages/runtime/projectbrain_runtime/service.py` imports:

```python
from projectbrain_runtime.brain.repository import BrainRepository
from projectbrain_runtime.brain.service import BrainService
```

Add methods inside `ProjectBrainRuntime`:

```python
    def brain_for_path(self, project_path: str | Path) -> BrainService:
        return BrainService(BrainRepository(project_path))

    def brain_for_project(self, project_id: str) -> BrainService:
        project = self.repository.get_project(project_id)
        return self.brain_for_path(project.source_path)
```

- [ ] **Step 4: Add brain parser commands**

Modify `packages/runtime/projectbrain_cli/main.py` in `build_parser()` after claim parser setup and before context parser:

```python
    brain = subcommands.add_parser("brain", help="Work with project-local Brain memory")
    brain_subcommands = brain.add_subparsers(dest="brain_command", required=True)

    brain_remember = brain_subcommands.add_parser("remember", help="Write a knowledge unit into a project Brain")
    brain_remember.add_argument("project_path", help="Path to the local project containing .projectbrain/brain")
    brain_remember.add_argument("--id", dest="project_id", default="local_project")
    brain_remember.add_argument("--type", required=True)
    brain_remember.add_argument("--statement", required=True)
    brain_remember.add_argument("--title")
    brain_remember.add_argument("--summary", default="")
    brain_remember.add_argument("--tag", action="append", default=[])
    brain_remember.add_argument("--applies-to", action="append", default=[])
    brain_remember.add_argument("--review-state", default="human_review_required")
    brain_remember.add_argument("--confidence", type=float, default=0.8)
    brain_remember.add_argument("--risk-level", default="normal")

    brain_list = brain_subcommands.add_parser("list", help="List project Brain knowledge")
    brain_list.add_argument("project_path")
    brain_list.add_argument("--type")
    brain_list.add_argument("--review-state")
    brain_list.add_argument("--tag")
    brain_list.add_argument("--include-archived", action="store_true")

    brain_search = brain_subcommands.add_parser("search", help="Search project Brain knowledge")
    brain_search.add_argument("project_path")
    brain_search.add_argument("query")
    brain_search.add_argument("--limit", type=int, default=20)

    brain_propose = brain_subcommands.add_parser("propose", help="Propose a memory candidate")
    brain_propose.add_argument("project_path")
    brain_propose.add_argument("--id", dest="project_id", default="local_project")
    brain_propose.add_argument("--session-id")
    brain_propose.add_argument("--type", required=True)
    brain_propose.add_argument("--statement", required=True)
    brain_propose.add_argument("--title")
    brain_propose.add_argument("--summary", default="")
    brain_propose.add_argument("--tag", action="append", default=[])
    brain_propose.add_argument("--applies-to", action="append", default=[])
    brain_propose.add_argument("--confidence", type=float, default=0.8)
    brain_propose.add_argument("--risk-level", default="normal")

    brain_candidates = brain_subcommands.add_parser("candidates", help="List memory candidates")
    brain_candidates.add_argument("project_path")
    brain_candidates.add_argument("--review-state")

    brain_confirm = brain_subcommands.add_parser("confirm-candidate", help="Confirm a memory candidate")
    brain_confirm.add_argument("project_path")
    brain_confirm.add_argument("candidate_id")

    brain_reject = brain_subcommands.add_parser("reject-candidate", help="Reject a memory candidate")
    brain_reject.add_argument("project_path")
    brain_reject.add_argument("candidate_id")
```

- [ ] **Step 5: Handle brain commands in main()**

Modify `packages/runtime/projectbrain_cli/main.py` after runtime is created and before `setup` handling:

```python
    if args.command == "brain":
        brain_service = runtime.brain_for_path(args.project_path)
        if args.brain_command == "remember":
            print_json(brain_service.remember(
                type=args.type,
                statement=args.statement,
                title=args.title,
                summary=args.summary,
                tags=args.tag,
                applies_to=args.applies_to,
                review_state=args.review_state,
                confidence=args.confidence,
                risk_level=args.risk_level,
            ))
            return 0
        if args.brain_command == "list":
            print_json(brain_service.list_knowledge(
                type=args.type,
                review_state=args.review_state,
                tag=args.tag,
                include_archived=args.include_archived,
            ))
            return 0
        if args.brain_command == "search":
            print_json(brain_service.search(args.query, limit=args.limit))
            return 0
        if args.brain_command == "propose":
            print_json(brain_service.propose_memories(
                project_id=args.project_id,
                session_id=args.session_id,
                candidates=[{
                    "type": args.type,
                    "title": args.title,
                    "statement": args.statement,
                    "summary": args.summary,
                    "tags": args.tag,
                    "applies_to": args.applies_to,
                    "confidence": args.confidence,
                    "risk_level": args.risk_level,
                }],
            ))
            return 0
        if args.brain_command == "candidates":
            print_json(brain_service.list_candidates(review_state=args.review_state))
            return 0
        if args.brain_command == "confirm-candidate":
            print_json(brain_service.confirm_candidate(args.candidate_id))
            return 0
        if args.brain_command == "reject-candidate":
            print_json(brain_service.reject_candidate(args.candidate_id))
            return 0
        raise ValueError(f"Unsupported brain command: {args.brain_command}")
```

- [ ] **Step 6: Run brain CLI tests**

Run:

```bash
python3 -m unittest tests.test_brain_cli -v
```

Expected: PASS.

- [ ] **Step 7: Run existing CLI tests**

Run:

```bash
python3 -m unittest tests.test_cli -v
```

Expected: PASS.

- [ ] **Step 8: Commit brain CLI**

```bash
git add packages/runtime/projectbrain_runtime/service.py packages/runtime/projectbrain_cli/main.py tests/test_brain_cli.py
git commit -m "feat: add brain memory cli commands"
```

---

## Task 5: Extraction Parser and codex-brain Session Runner

**Files:**
- Create: `packages/runtime/projectbrain_runtime/brain/extraction.py`
- Create: `packages/runtime/projectbrain_cli/codex_session.py`
- Create: `tests/test_codex_brain.py`

- [ ] **Step 1: Write failing extraction and session tests**

Create `tests/test_codex_brain.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_cli.codex_session import ManagedSessionResult, build_extraction_prompt, persist_session_result  # noqa: E402
from projectbrain_runtime.brain.extraction import parse_extraction_output  # noqa: E402
from projectbrain_runtime.brain.repository import BrainRepository  # noqa: E402
from projectbrain_runtime.brain.service import BrainService  # noqa: E402


class CodexBrainTest(unittest.TestCase):
    def test_parse_extraction_output_accepts_json_code_block(self):
        output = '''Here is the result:\n```json\n{"session_summary":"Refund fee discussion.","candidates":[{"type":"constraint","statement":"Refund fee must be booked separately.","tags":["refund"],"applies_to":["RefundService"],"confidence":0.9,"review_state":"human_review_required"}]}\n```'''

        parsed = parse_extraction_output(output)

        self.assertEqual(parsed["session_summary"], "Refund fee discussion.")
        self.assertEqual(parsed["candidates"][0]["type"], "constraint")

    def test_build_extraction_prompt_contains_safety_rules(self):
        prompt = build_extraction_prompt()

        self.assertIn("Return ONLY JSON", prompt)
        self.assertIn("Do NOT include", prompt)
        self.assertIn("secrets or credentials", prompt)

    def test_persist_session_result_writes_session_and_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            result = ManagedSessionResult(
                session_id="session_test",
                project_id="payment",
                task="Refund fee",
                transcript_path=str(Path(tmp) / "session.log"),
                extraction_output='{"session_summary":"Refund fee discussion.","candidates":[{"type":"constraint","statement":"Refund fee must be booked separately.","tags":["refund"]}]}',
                changed_files=["service/refund/RefundService.java"],
            )

            persisted = persist_session_result(service, result)

            self.assertEqual(persisted["session"]["session_id"], "session_test")
            self.assertEqual(persisted["candidate_count"], 1)
            self.assertEqual(service.list_candidates()["candidates"][0]["proposed_unit"]["type"], "constraint")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run codex-brain tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_codex_brain -v
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement extraction parser**

Create `packages/runtime/projectbrain_runtime/brain/extraction.py`:

```python
"""Parse Codex memory extraction output."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_extraction_output(output: str) -> dict[str, Any]:
    text = output.strip()
    candidates = _candidate_json_strings(text)
    errors = []
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            return _normalize_extraction(data)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
    raise ValueError("Could not parse extraction JSON: " + "; ".join(errors or ["no JSON object found"]))


def _candidate_json_strings(text: str) -> list[str]:
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    values = [block.strip() for block in blocks]
    if text.startswith("{") and text.endswith("}"):
        values.insert(0, text)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        values.append(text[first:last + 1])
    return values


def _normalize_extraction(data: dict[str, Any]) -> dict[str, Any]:
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    normalized = []
    for item in candidates:
        if not isinstance(item, dict) or not item.get("type") or not item.get("statement"):
            continue
        normalized.append({
            "type": item["type"],
            "title": item.get("title"),
            "statement": item["statement"],
            "summary": item.get("summary", ""),
            "tags": item.get("tags", []),
            "applies_to": item.get("applies_to", []),
            "confidence": float(item.get("confidence", 0.8)),
            "risk_level": item.get("risk_level", "normal"),
            "review_state": item.get("review_state", "human_review_required"),
            "evidence": [{"type": "conversation_summary", "summary": item.get("evidence_summary", "Extracted from codex-brain session.")}],
        })
    return {"session_summary": data.get("session_summary", ""), "candidates": normalized}
```

- [ ] **Step 4: Implement codex session helpers**

Create `packages/runtime/projectbrain_cli/codex_session.py`:

```python
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
    session = ConversationSession(
        session_id=result.session_id,
        project_id=result.project_id,
        task=result.task,
        summary=parsed.get("session_summary", ""),
        ended_at=now_iso(),
        changed_files=result.changed_files,
    )
    service.save_session(session)
    proposed = service.propose_memories(
        project_id=result.project_id,
        session_id=result.session_id,
        candidates=parsed.get("candidates", []),
    )
    return {"session": session.to_dict(), "candidate_count": proposed["candidate_count"], "candidates": proposed["candidates"]}
```

- [ ] **Step 5: Run codex-brain tests**

Run:

```bash
python3 -m unittest tests.test_codex_brain -v
```

Expected: PASS.

- [ ] **Step 6: Commit extraction and session helpers**

```bash
git add packages/runtime/projectbrain_runtime/brain/extraction.py packages/runtime/projectbrain_cli/codex_session.py tests/test_codex_brain.py
git commit -m "feat: add codex-brain extraction helpers"
```

---

## Task 6: codex-brain Entrypoint

**Files:**
- Create: `packages/runtime/projectbrain_cli/codex_brain.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_codex_brain.py`

- [ ] **Step 1: Extend failing tests for codex-brain main**

Append to `tests/test_codex_brain.py` before `if __name__ == "__main__"`:

```python
from projectbrain_cli.codex_brain import main as codex_brain_main  # noqa: E402


class CodexBrainMainTest(unittest.TestCase):
    def test_codex_brain_no_extract_runs_injected_command_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, *, cwd):
                calls.append((command, cwd))
                return 0

            return_code = codex_brain_main(
                ["--project", tmp, "--no-ui", "--no-extract", "--codex-command", "codex --version"],
                command_runner=fake_runner,
                browser_opener=lambda url: None,
            )

            self.assertEqual(return_code, 0)
            self.assertEqual(calls[0][0], ["codex", "--version"])
            self.assertEqual(calls[0][1], Path(tmp).resolve())
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_codex_brain.CodexBrainMainTest -v
```

Expected: FAIL with missing `projectbrain_cli.codex_brain`.

- [ ] **Step 3: Implement codex-brain main**

Create `packages/runtime/projectbrain_cli/codex_brain.py`:

```python
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
```

- [ ] **Step 4: Add script entrypoint**

Modify `pyproject.toml` `[project.scripts]` section:

```toml
projectbrain = "projectbrain_cli.main:main"
codex-brain = "projectbrain_cli.codex_brain:main"
```

- [ ] **Step 5: Run codex-brain main tests**

Run:

```bash
python3 -m unittest tests.test_codex_brain.CodexBrainMainTest -v
```

Expected: PASS.

- [ ] **Step 6: Run all codex-brain tests**

Run:

```bash
python3 -m unittest tests.test_codex_brain -v
```

Expected: PASS.

- [ ] **Step 7: Commit codex-brain entrypoint**

```bash
git add packages/runtime/projectbrain_cli/codex_brain.py pyproject.toml tests/test_codex_brain.py
git commit -m "feat: add codex-brain entrypoint"
```

---

## Task 7: Brain API Handlers and Routes

**Files:**
- Modify: `apps/api/projectbrain_api/handlers.py`
- Modify: `apps/api/projectbrain_api/main.py`
- Create: `tests/test_brain_api.py`

- [ ] **Step 1: Write failing API handler tests**

Create `tests/test_brain_api.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from projectbrain_api.handlers import (  # noqa: E402
    brain_candidate_confirm_handler,
    brain_candidates_handler,
    brain_knowledge_create_handler,
    brain_knowledge_list_handler,
    brain_summary_handler,
)
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402
from projectbrain_runtime.models import ProjectRecord  # noqa: E402


class BrainApiHandlerTest(unittest.TestCase):
    def test_brain_handlers_create_list_and_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(Path(tmp) / "store"))
            runtime.repository.save_project(ProjectRecord(
                project_id="payment",
                name="Payment",
                source_path=str(project_path),
                codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
            ))

            created = brain_knowledge_create_handler(runtime, "payment", {
                "type": "constraint",
                "statement": "Refund fee must be booked separately.",
                "tags": ["refund"],
            })
            self.assertEqual(created["knowledge_unit"]["type"], "constraint")

            listed = brain_knowledge_list_handler(runtime, "payment", {"q": "refund"})
            self.assertEqual(listed["matches"][0]["type"], "constraint")

            runtime.brain_for_project("payment").propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "gotcha", "statement": "account_record is append-only."}],
            )
            candidates = brain_candidates_handler(runtime, "payment", {"review_state": "human_review_required"})
            confirmed = brain_candidate_confirm_handler(runtime, "payment", candidates["candidates"][0]["candidate_id"])

            self.assertEqual(confirmed["knowledge_unit"]["type"], "gotcha")
            self.assertEqual(brain_summary_handler(runtime, "payment")["knowledge_unit_count"], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run API handler tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_brain_api -v
```

Expected: FAIL with missing handler imports.

- [ ] **Step 3: Add brain handlers**

Append to `apps/api/projectbrain_api/handlers.py`:

```python

def brain_summary_handler(runtime: ProjectBrainRuntime, project_id: str) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).summary()


def brain_knowledge_list_handler(runtime: ProjectBrainRuntime, project_id: str, query: dict[str, Any]) -> dict[str, Any]:
    q = query.get("q")
    service = runtime.brain_for_project(project_id)
    if q:
        return service.search(str(q), limit=int(query.get("limit", 20)))
    return service.list_knowledge(
        type=query.get("type"),
        review_state=query.get("review_state"),
        staleness=query.get("staleness"),
        tag=query.get("tag"),
        include_archived=bool(query.get("include_archived", False)),
    )


def brain_knowledge_create_handler(runtime: ProjectBrainRuntime, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require_payload_keys(payload, ["type", "statement"])
    return runtime.brain_for_project(project_id).remember(
        type=payload["type"],
        statement=payload["statement"],
        title=payload.get("title"),
        summary=payload.get("summary", ""),
        tags=payload.get("tags", []),
        applies_to=payload.get("applies_to", []),
        review_state=payload.get("review_state", "human_review_required"),
        confidence=float(payload.get("confidence", 0.8)),
        risk_level=payload.get("risk_level", "normal"),
    )


def brain_candidates_handler(runtime: ProjectBrainRuntime, project_id: str, query: dict[str, Any]) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).list_candidates(review_state=query.get("review_state"))


def brain_candidate_confirm_handler(runtime: ProjectBrainRuntime, project_id: str, candidate_id: str) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).confirm_candidate(candidate_id)


def brain_candidate_reject_handler(runtime: ProjectBrainRuntime, project_id: str, candidate_id: str) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).reject_candidate(candidate_id)
```

- [ ] **Step 4: Add FastAPI routes**

Modify imports in `apps/api/projectbrain_api/main.py` to include new handlers:

```python
    brain_candidate_confirm_handler,
    brain_candidate_reject_handler,
    brain_candidates_handler,
    brain_knowledge_create_handler,
    brain_knowledge_list_handler,
    brain_summary_handler,
```

Append routes after claim routes:

```python
@app.get("/api/v1/projects/{project_id}/brain/summary")
def brain_summary(project_id: str) -> dict[str, Any]:
    try:
        return brain_summary_handler(build_runtime(), project_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/projects/{project_id}/brain/knowledge")
def brain_knowledge(project_id: str, q: str | None = None, type: str | None = None, review_state: str | None = None, tag: str | None = None, limit: int = 20) -> dict[str, Any]:
    try:
        return brain_knowledge_list_handler(build_runtime(), project_id, {"q": q, "type": type, "review_state": review_state, "tag": tag, "limit": limit})
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/brain/knowledge")
def brain_create_knowledge(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return brain_knowledge_create_handler(build_runtime(), project_id, payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/projects/{project_id}/brain/candidates")
def brain_candidates(project_id: str, review_state: str | None = None) -> dict[str, Any]:
    try:
        return brain_candidates_handler(build_runtime(), project_id, {"review_state": review_state})
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/brain/candidates/{candidate_id}/confirm")
def brain_confirm_candidate(project_id: str, candidate_id: str) -> dict[str, Any]:
    try:
        return brain_candidate_confirm_handler(build_runtime(), project_id, candidate_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/brain/candidates/{candidate_id}/reject")
def brain_reject_candidate(project_id: str, candidate_id: str) -> dict[str, Any]:
    try:
        return brain_candidate_reject_handler(build_runtime(), project_id, candidate_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 5: Run API tests**

Run:

```bash
python3 -m unittest tests.test_brain_api -v
```

Expected: PASS.

- [ ] **Step 6: Run existing API handler tests**

Run:

```bash
python3 -m unittest tests.test_api_handlers -v
```

Expected: PASS.

- [ ] **Step 7: Commit brain API**

```bash
git add apps/api/projectbrain_api/handlers.py apps/api/projectbrain_api/main.py tests/test_brain_api.py
git commit -m "feat: add brain memory api handlers"
```

---

## Task 8: Brain Explorer UI

**Files:**
- Modify: `apps/api/projectbrain_api/ui/router.py`
- Create: `apps/api/projectbrain_api/ui/templates/projects/brain.html`
- Create: `apps/api/projectbrain_api/ui/templates/_partials/brain_knowledge_list.html`
- Create: `apps/api/projectbrain_api/ui/templates/_partials/brain_candidate_list.html`
- Modify: `apps/api/projectbrain_api/ui/templates/projects/index.html`
- Modify: `apps/api/projectbrain_api/ui/templates/projects/context.html`
- Modify: `apps/api/projectbrain_api/ui/templates/projects/impact.html`
- Modify: `apps/api/projectbrain_api/ui/templates/projects/policy.html`
- Create: `tests/test_brain_ui.py`

- [ ] **Step 1: Write failing UI tests**

Create `tests/test_brain_ui.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from projectbrain_api.ui.router import brain_page_context  # noqa: E402
from projectbrain_runtime.models import ProjectRecord  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


class BrainUiTest(unittest.TestCase):
    def test_brain_page_context_contains_summary_candidates_and_knowledge(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(Path(tmp) / "store"))
            runtime.repository.save_project(ProjectRecord(
                project_id="payment",
                name="Payment",
                source_path=str(project_path),
                codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
            ))
            brain = runtime.brain_for_project("payment")
            brain.remember(type="constraint", statement="Refund fee rule.", tags=["refund"])
            brain.propose_memories(project_id="payment", session_id="session1", candidates=[{"type": "gotcha", "statement": "account_record is append-only."}])

            context = brain_page_context(runtime, "payment", q="refund")

            self.assertEqual(context["project"].project_id, "payment")
            self.assertEqual(context["summary"]["knowledge_unit_count"], 1)
            self.assertEqual(context["candidates"]["candidate_count"], 1)
            self.assertEqual(context["knowledge"]["matches"][0]["statement"], "Refund fee rule.")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run UI tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_brain_ui -v
```

Expected: FAIL with missing `brain_page_context`.

- [ ] **Step 3: Add UI context helper and route**

Modify `apps/api/projectbrain_api/ui/router.py` imports to include `Any` if not present and append:

```python

def brain_page_context(runtime: Any, project_id: str, q: str | None = None) -> dict[str, Any]:
    project = runtime.repository.get_project(project_id)
    brain = runtime.brain_for_project(project_id)
    knowledge = brain.search(q) if q else brain.list_knowledge()
    candidates = brain.list_candidates(review_state="human_review_required")
    return {
        "title": f"{project.name} · Brain",
        "heading": "Project Brain",
        "project": project,
        "summary": brain.summary(),
        "knowledge": knowledge,
        "candidates": candidates,
        "query": q or "",
    }


@router.get("/projects/{project_id}/brain")
def project_brain(project_id: str, q: str | None = None, request: Request = None):
    runtime = build_runtime()
    return templates.TemplateResponse(
        "projects/brain.html",
        {"request": request, **brain_page_context(runtime, project_id, q=q)},
    )
```

If `Request`, `build_runtime`, `templates`, or `router` names differ in the existing file, use the existing names already used by context/impact routes. Keep the helper signature exactly as tested.

- [ ] **Step 4: Create Brain Explorer template**

Create `apps/api/projectbrain_api/ui/templates/projects/brain.html`:

```html
{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<div class="pb-grid">
  <section class="pb-card">
    <div class="pb-card-head">
      <h1>{{ heading }}</h1>
      <nav class="pb-subnav">
        <a href="/ui/projects">← 项目列表</a>
        <a href="/ui/projects/{{ project.project_id }}/context">Context</a>
        <a href="/ui/projects/{{ project.project_id }}/impact">Impact</a>
        <a href="/ui/projects/{{ project.project_id }}/policy">策略</a>
      </nav>
    </div>
    <p class="pb-muted"><code>{{ project.source_path }}</code></p>

    <div class="pb-callout">
      <strong>Brain Summary</strong>：{{ summary.knowledge_unit_count }} 条知识，{{ summary.candidate_count }} 条待确认。
    </div>

    <form class="pb-form" method="get" action="/ui/projects/{{ project.project_id }}/brain">
      <label>
        <span>搜索项目大脑</span>
        <input type="text" name="q" value="{{ query }}" aria-label="搜索项目大脑" value="{{ query }}" />
      </label>
      <div class="pb-form-actions"><button type="submit">搜索</button></div>
    </form>

    <h2>待确认知识</h2>
    {% with candidates = candidates.candidates %}
      {% include "_partials/brain_candidate_list.html" %}
    {% endwith %}

    <h2>知识库</h2>
    {% if knowledge.matches is defined %}
      {% with units = knowledge.matches %}
        {% include "_partials/brain_knowledge_list.html" %}
      {% endwith %}
    {% else %}
      {% with units = knowledge.knowledge_units %}
        {% include "_partials/brain_knowledge_list.html" %}
      {% endwith %}
    {% endif %}
  </section>
</div>
{% endblock %}
```

- [ ] **Step 5: Create knowledge partial**

Create `apps/api/projectbrain_api/ui/templates/_partials/brain_knowledge_list.html`:

```html
{% if units %}
<ul class="pb-section-items">
  {% for unit in units %}
  <li>
    <strong>{{ unit.title or unit.statement }}</strong>
    <div class="pb-muted">
      <code>{{ unit.type }}</code> · <code>{{ unit.review_state }}</code>
      {% if unit.risk_level %} · risk: <code>{{ unit.risk_level }}</code>{% endif %}
    </div>
    <p>{{ unit.statement }}</p>
    {% if unit.tags %}<p class="pb-muted">tags: {{ unit.tags | join(", ") }}</p>{% endif %}
    {% if unit.applies_to %}<p class="pb-muted">applies_to: {{ unit.applies_to | join(", ") }}</p>{% endif %}
  </li>
  {% endfor %}
</ul>
{% else %}
<p class="pb-muted">暂无知识。</p>
{% endif %}
```

- [ ] **Step 6: Create candidate partial**

Create `apps/api/projectbrain_api/ui/templates/_partials/brain_candidate_list.html`:

```html
{% if candidates %}
<ul class="pb-section-items">
  {% for candidate in candidates %}
  <li>
    <strong>{{ candidate.proposed_unit.title or candidate.proposed_unit.statement }}</strong>
    <div class="pb-muted">
      <code>{{ candidate.proposed_unit.type }}</code> · <code>{{ candidate.review_state }}</code>
      · confidence: <code>{{ candidate.proposed_unit.confidence or "0.8" }}</code>
    </div>
    <p>{{ candidate.proposed_unit.statement }}</p>
    {% if candidate.possible_duplicates %}
      <p class="pb-muted">可能重复：{{ candidate.possible_duplicates | length }} 条</p>
    {% endif %}
  </li>
  {% endfor %}
</ul>
{% else %}
<p class="pb-muted">暂无待确认知识。</p>
{% endif %}
```

- [ ] **Step 7: Add Brain links to existing project pages**

In `apps/api/projectbrain_api/ui/templates/projects/index.html`, add this link inside the existing project actions list:

```html
<a href="/ui/projects/{{ project.project_id }}/brain">Brain</a>
```

In `context.html`, `impact.html`, and `policy.html`, add this subnav link where project subnav links are rendered:

```html
<a href="/ui/projects/{{ project.project_id }}/brain">Brain</a>
```

- [ ] **Step 8: Run UI tests**

Run:

```bash
python3 -m unittest tests.test_brain_ui -v
```

Expected: PASS.

- [ ] **Step 9: Run existing UI smoke tests**

Run:

```bash
python3 -m unittest tests.test_ui_smoke -v
```

Expected: PASS.

- [ ] **Step 10: Commit Brain Explorer UI**

```bash
git add apps/api/projectbrain_api/ui/router.py apps/api/projectbrain_api/ui/templates/projects/brain.html apps/api/projectbrain_api/ui/templates/_partials/brain_knowledge_list.html apps/api/projectbrain_api/ui/templates/_partials/brain_candidate_list.html apps/api/projectbrain_api/ui/templates/projects/index.html apps/api/projectbrain_api/ui/templates/projects/context.html apps/api/projectbrain_api/ui/templates/projects/impact.html apps/api/projectbrain_api/ui/templates/projects/policy.html tests/test_brain_ui.py
git commit -m "feat: add brain explorer ui"
```

---

## Task 9: MCP Memory Tools

**Files:**
- Modify: `packages/runtime/projectbrain_cli/mcp_server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Add failing MCP test**

Append to `tests/test_mcp_server.py`:

```python
    def test_mcp_can_propose_search_and_confirm_brain_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
            server.repository.save_project(ProjectRecord(
                project_id="payment",
                name="Payment",
                source_path=str(project_path),
                codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
            ))

            proposed = server.handle_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_propose_memories",
                    "arguments": {
                        "project_id": "payment",
                        "session_id": "session1",
                        "candidates": [
                            {"type": "constraint", "statement": "Refund fee must be booked separately.", "tags": ["refund"]}
                        ],
                    },
                },
            })
            proposed_data = json.loads(proposed["result"]["content"][0]["text"])
            candidate_id = proposed_data["candidates"][0]["candidate_id"]

            confirmed = server.handle_message({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_review_memory_candidate",
                    "arguments": {"project_id": "payment", "candidate_id": candidate_id, "action": "confirm"},
                },
            })
            confirmed_data = json.loads(confirmed["result"]["content"][0]["text"])
            self.assertEqual(confirmed_data["knowledge_unit"]["type"], "constraint")

            search = server.handle_message({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_search_brain",
                    "arguments": {"project_id": "payment", "query": "refund"},
                },
            })
            search_data = json.loads(search["result"]["content"][0]["text"])
            self.assertEqual(search_data["matches"][0]["type"], "constraint")
```

If `ProjectRecord`, `Path`, `tempfile`, or `json` are not already imported in `tests/test_mcp_server.py`, add imports:

```python
import json
import tempfile
from pathlib import Path
from projectbrain_runtime.models import ProjectRecord
```

- [ ] **Step 2: Run MCP test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_mcp_server.ProjectBrainMcpServerTest.test_mcp_can_propose_search_and_confirm_brain_memory -v
```

Expected: FAIL with unknown tool.

- [ ] **Step 3: Add MCP tool handlers**

Modify `packages/runtime/projectbrain_cli/mcp_server.py` inside `_handle_tool_call()` before unknown tool error:

```python
            if name == "projectbrain_remember":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).remember(
                    type=_required(arguments, "type"),
                    statement=_required(arguments, "statement"),
                    title=arguments.get("title"),
                    summary=arguments.get("summary", ""),
                    tags=arguments.get("tags", []),
                    applies_to=arguments.get("applies_to", []),
                    review_state=arguments.get("review_state", "human_review_required"),
                    confidence=float(arguments.get("confidence", 0.8)),
                    risk_level=arguments.get("risk_level", "normal"),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_propose_memories":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).propose_memories(
                    project_id=_required(arguments, "project_id"),
                    session_id=arguments.get("session_id"),
                    candidates=arguments.get("candidates", []),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_search_brain":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).search(
                    _required(arguments, "query"),
                    limit=int(arguments.get("limit", 20)),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_list_memory_candidates":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).list_candidates(
                    review_state=arguments.get("review_state")
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_review_memory_candidate":
                service = self.runtime.brain_for_project(_required(arguments, "project_id"))
                action = arguments.get("action", "confirm")
                if action == "confirm":
                    data = service.confirm_candidate(_required(arguments, "candidate_id"))
                elif action == "reject":
                    data = service.reject_candidate(_required(arguments, "candidate_id"))
                else:
                    raise ValueError("action must be confirm or reject")
                return self._tool_result(request_id, data)
```

- [ ] **Step 4: Add MCP tool schemas**

Modify `_tools()` and append these tool definitions before context/impact tools:

```python
            {
                "name": "projectbrain_remember",
                "description": "Write durable project knowledge into the local project Brain.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "type", "statement"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "type": {"type": "string"},
                        "statement": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "applies_to": {"type": "array", "items": {"type": "string"}},
                        "review_state": {"type": "string"},
                        "confidence": {"type": "number"},
                        "risk_level": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_propose_memories",
                "description": "Submit memory candidates extracted from a Codex session for human review.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "candidates"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "session_id": {"type": "string"},
                        "candidates": {"type": "array", "items": {"type": "object"}},
                    },
                },
            },
            {
                "name": "projectbrain_search_brain",
                "description": "Search durable local project Brain knowledge.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "query"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "projectbrain_list_memory_candidates",
                "description": "List memory candidates awaiting review.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "review_state": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_review_memory_candidate",
                "description": "Confirm or reject a memory candidate.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "candidate_id", "action"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "candidate_id": {"type": "string"},
                        "action": {"type": "string", "enum": ["confirm", "reject"]},
                    },
                },
            },
```

- [ ] **Step 5: Run MCP test**

Run:

```bash
python3 -m unittest tests.test_mcp_server.ProjectBrainMcpServerTest.test_mcp_can_propose_search_and_confirm_brain_memory -v
```

Expected: PASS.

- [ ] **Step 6: Run full MCP tests**

Run:

```bash
python3 -m unittest tests.test_mcp_server -v
```

Expected: PASS.

- [ ] **Step 7: Commit MCP tools**

```bash
git add packages/runtime/projectbrain_cli/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: expose project brain memory tools over mcp"
```

---

## Task 10: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/mcp-usage.md`
- Modify: `docs/quickstart.md`

- [ ] **Step 1: Add README codex-brain section**

Add after the existing “Local MCP Server” section in `README.md`:

```markdown
## codex-brain: Run Codex With Project Memory

`codex-brain` starts a managed Codex CLI session for a local project. It initializes the project Brain store, opens the local Brain Explorer, runs Codex as a child process, and can save extracted memory candidates for human review.

```bash
cd /path/to/my/project
codex-brain
```

The first MVP only captures sessions explicitly started by `codex-brain`. It does not monitor ordinary `codex` sessions, other terminals, the clipboard, or background activity.

Memory candidates are written under the project-local Brain store:

```text
<project>/.projectbrain/brain/
  knowledge_units.jsonl
  memory_candidates.jsonl
  conversations.jsonl
```

Use the Brain Explorer or CLI to review candidates:

```bash
projectbrain brain candidates /path/to/my/project
projectbrain brain confirm-candidate /path/to/my/project <candidate_id>
```
```

- [ ] **Step 2: Add MCP docs for memory tools**

Add to `docs/mcp-usage.md` under “Exposed Tools” table:

```markdown
| `projectbrain_remember` | Write durable project knowledge into the local project Brain. |
| `projectbrain_propose_memories` | Submit memory candidates extracted from a Codex session for review. |
| `projectbrain_search_brain` | Search durable project Brain knowledge. |
| `projectbrain_list_memory_candidates` | List memory candidates awaiting review. |
| `projectbrain_review_memory_candidate` | Confirm or reject a memory candidate. |
```

Add a short privacy note:

```markdown
### codex-brain Privacy Boundary

`codex-brain` captures only the Codex CLI process it explicitly starts. It does not monitor ordinary `codex` sessions, other shells, system clipboard contents, or background applications. Full transcripts are not part of the durable Brain by default; durable Brain records store concise summaries, candidates, and reviewed knowledge units.
```

- [ ] **Step 3: Add quickstart snippet**

Add to `docs/quickstart.md` after “Use Your Own Project”:

```markdown
## Run Codex With ProjectBrain Memory

From a local project directory:

```bash
codex-brain
```

Review extracted memory candidates:

```bash
projectbrain brain candidates .
projectbrain brain confirm-candidate . <candidate_id>
```
```

- [ ] **Step 4: Run documentation grep for incomplete-marker terms**

Run:

```bash
rg -n "T[B]D|T[O]DO|fill[ ]in" README.md docs/mcp-usage.md docs/quickstart.md docs/superpowers/specs docs/superpowers/plans
```

Expected: No output.

- [ ] **Step 5: Run focused test suite**

Run:

```bash
python3 -m unittest \
  tests.test_brain_models \
  tests.test_brain_repository \
  tests.test_brain_service \
  tests.test_brain_cli \
  tests.test_codex_brain \
  tests.test_brain_api \
  tests.test_brain_ui \
  tests.test_mcp_server \
  -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: PASS.

- [ ] **Step 7: Commit docs and final verification**

```bash
git add README.md docs/mcp-usage.md docs/quickstart.md
git commit -m "docs: document codex-brain memory workflow"
```

---

## Self-Review Notes

- Spec coverage: This plan covers `codex-brain`, Brain Core models, project-local JSONL persistence, MemoryCandidate queue, Brain Explorer Needs Review UI, API, CLI, MCP, and privacy documentation. Brain-aware Context/Impact is intentionally left for the next phase after candidates can be captured and reviewed.
- Placeholder scan: The plan uses concrete file paths, test code, implementation snippets, commands, and expected outcomes. It avoids incomplete implementation markers.
- Type consistency: The plan consistently uses `KnowledgeUnit.id`, `MemoryCandidate.candidate_id`, `ConversationSession.session_id`, `review_state`, `proposed_unit`, and `BrainService` method names across tests, service, CLI, API, UI, and MCP.
