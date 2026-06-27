# ProjectBrain V1 First Four Microbranches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first V1 vertical slice of ProjectBrain by introducing a stable Task Understanding Bundle, a minimal bundle builder, a unified `understand` CLI entrypoint, and the first SQLite knowledge store bootstrap.

**Architecture:** Keep the existing JSON facts/runtime flow intact, then add a thin bundle layer above `context` and `impact`, plus a parallel SQLite store that initially coexists with the JSON repository. The first four branches intentionally avoid large refactors and only add seams that later branches can extend.

**Tech Stack:** Python 3.11, dataclasses, argparse CLI, sqlite3 standard library, unittest

---

## File Structure

**Existing files to modify early**
- `packages/runtime/projectbrain_runtime/models.py`
- `packages/runtime/projectbrain_runtime/service.py`
- `packages/runtime/projectbrain_cli/main.py`
- `packages/runtime/projectbrain_runtime/repository.py`
- `tests/test_cli.py`
- `tests/test_repository.py`

**New files to create in the first four branches**
- `packages/runtime/projectbrain_runtime/bundle.py`
- `packages/runtime/projectbrain_runtime/knowledge_store.py`
- `tests/test_bundle.py`
- `tests/test_knowledge_store.py`

**Responsibility boundaries**
- `bundle.py` owns the public V1 bundle schema and bundle builder helpers.
- `service.py` owns orchestration and should call bundle helpers rather than embed bundle formatting logic.
- `main.py` owns CLI argument parsing and command dispatch.
- `knowledge_store.py` owns SQLite creation and low-level schema bootstrap only; it should not yet replace the JSON runtime repository.

---

### Task 1: `feat/v1-01-bundle-schema`

**Files:**
- Create: `packages/runtime/projectbrain_runtime/bundle.py`
- Test: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing test for bundle defaults**

```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.bundle import TaskUnderstandingBundle  # noqa: E402


class TaskUnderstandingBundleTest(unittest.TestCase):
    def test_to_dict_includes_required_v1_fields(self):
        bundle = TaskUnderstandingBundle(
            bundle_id="tub_test",
            project_id="demo_project",
            task="Explain checkout flow",
            task_type="explain",
            summary="Checkout starts in CheckoutController.",
        )

        data = bundle.to_dict()

        self.assertEqual(data["bundle_type"], "task_understanding")
        self.assertEqual(data["bundle_id"], "tub_test")
        self.assertEqual(data["project_id"], "demo_project")
        self.assertEqual(data["task"], "Explain checkout flow")
        self.assertEqual(data["task_type"], "explain")
        self.assertEqual(data["summary"], "Checkout starts in CheckoutController.")
        self.assertEqual(data["relevant_files"], [])
        self.assertEqual(data["relevant_symbols"], [])
        self.assertEqual(data["entry_flows"], [])
        self.assertEqual(data["impact_hints"], [])
        self.assertEqual(data["risk_warnings"], [])
        self.assertEqual(data["human_claims"]["verified"], [])
        self.assertEqual(data["linked_evidence"]["verified"], [])
        self.assertEqual(data["test_suggestions"], [])
        self.assertEqual(data["unknowns"], [])
        self.assertEqual(data["quality_notes"], [])
        self.assertIn("generated_at", data)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_bundle -v
```

Expected: FAIL with `ModuleNotFoundError` for `projectbrain_runtime.bundle`.

- [ ] **Step 3: Write the minimal bundle schema**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_bundle -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/runtime/projectbrain_runtime/bundle.py tests/test_bundle.py
git commit -m "feat(bundle): add task understanding bundle schema"
```

---

### Task 2: `feat/v1-02-bundle-builder`

**Files:**
- Modify: `packages/runtime/projectbrain_runtime/service.py`
- Create: `packages/runtime/projectbrain_runtime/bundle.py`
- Test: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing test for runtime bundle generation**

```python
def test_runtime_build_task_understanding_bundle_uses_context_pack_summary(self):
    from projectbrain_runtime.models import ProjectRecord
    from projectbrain_runtime.repository import JsonProjectBrainRepository
    from projectbrain_runtime.service import ProjectBrainRuntime

    with tempfile.TemporaryDirectory() as tmp:
        repository = JsonProjectBrainRepository(tmp)
        runtime = ProjectBrainRuntime(repository)
        repository.save_project(
            ProjectRecord(
                project_id="payment_demo",
                name="Payment Demo",
                source_path="/repo/payment",
                codegraph_db_path="/repo/payment/.codegraph/codegraph.db",
            )
        )
        repository.save_facts(
            "payment_demo",
            {
                "project_id": "payment_demo",
                "entities": [],
                "relations": [],
                "sources": [],
                "stats": {},
            },
        )
        repository.save_experience_claims("payment_demo", [])

        data = runtime.build_task_understanding_bundle(
            project_id="payment_demo",
            task="Explain payment flow",
        )

        self.assertEqual(data["bundle"]["project_id"], "payment_demo")
        self.assertEqual(data["bundle"]["task"], "Explain payment flow")
        self.assertEqual(data["bundle"]["task_type"], "general")
        self.assertIn("summary", data["bundle"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_bundle -v
```

Expected: FAIL with `AttributeError: 'ProjectBrainRuntime' object has no attribute 'build_task_understanding_bundle'`.

- [ ] **Step 3: Add minimal bundle builder logic**

```python
from projectbrain_runtime.bundle import TaskUnderstandingBundle


def _infer_task_type(task: str) -> str:
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


def _bundle_summary(context_pack: dict[str, Any]) -> str:
    recommended = context_pack.get("recommended_files") or []
    if recommended:
        first_item = recommended[0]
        path = first_item.get("path") or first_item.get("file") or "unknown file"
        return f"Start with {path}."
    return "No relevant files were identified yet."


class ProjectBrainRuntime:
    ...

    def build_task_understanding_bundle(
        self,
        *,
        project_id: str,
        task: str,
        max_items_per_section: int = 12,
    ) -> dict[str, Any]:
        context_data = self.build_context_pack(
            project_id=project_id,
            task=task,
            max_items_per_section=max_items_per_section,
        )
        context_pack = context_data["context_pack"]
        bundle = TaskUnderstandingBundle(
            bundle_id=f"{project_id}:{task}",
            project_id=project_id,
            task=task,
            task_type=_infer_task_type(task),
            summary=_bundle_summary(context_pack),
            relevant_files=[
                {
                    "path": item.get("path", ""),
                    "reason": item.get("reason", ""),
                    "confidence": item.get("confidence", 0.0),
                }
                for item in context_pack.get("recommended_files", [])
            ],
            relevant_symbols=[
                {
                    "symbol": item.get("name", ""),
                    "reason": item.get("reason", ""),
                    "confidence": item.get("confidence", 0.0),
                }
                for item in context_pack.get("recommended_symbols", [])
            ],
        )
        artifact_path = self.repository.save_run_artifact(
            project_id,
            "task-understanding-bundle-latest.json",
            bundle.to_dict(),
        )
        return {
            "artifact_path": artifact_path,
            "bundle": bundle.to_dict(),
            "context_pack_artifact_path": context_data["artifact_path"],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_bundle tests.test_repository -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/runtime/projectbrain_runtime/bundle.py packages/runtime/projectbrain_runtime/service.py tests/test_bundle.py
git commit -m "feat(bundle): add runtime task understanding bundle builder"
```

---

### Task 3: `feat/v1-05-cli-understand`

**Files:**
- Modify: `packages/runtime/projectbrain_cli/main.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `docs/projectbrain/local-runtime.md`

- [ ] **Step 1: Write the failing CLI test**

```python
    def test_understand_returns_task_understanding_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_understand_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "understand",
                    "payment_understand_cli",
                    "Explain settlement flow",
                ]
            )

            self.assertEqual(output["bundle"]["bundle_type"], "task_understanding")
            self.assertEqual(output["bundle"]["project_id"], "payment_understand_cli")
            self.assertEqual(output["bundle"]["task"], "Explain settlement flow")
            self.assertIn("summary", output["bundle"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_cli.ProjectBrainCliTest.test_understand_returns_task_understanding_bundle -v
```

Expected: FAIL with argparse error for unknown command `understand`.

- [ ] **Step 3: Add the `understand` CLI command**

```python
    understand = subcommands.add_parser("understand", help="Build a task understanding bundle from imported facts")
    understand.add_argument("project_id")
    understand.add_argument("task")
    understand.add_argument("--max-items-per-section", type=int, default=12)
    understand.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")
```

```python
    if args.command == "understand":
        data = runtime.build_task_understanding_bundle(
            project_id=args.project_id,
            task=args.task,
            max_items_per_section=args.max_items_per_section,
        )
        if args.format == "json":
            print_json(data)
        else:
            print_json({"agent_output": data["bundle"]})
        return 0
```

```markdown
生成 Task Understanding Bundle：

```bash
projectbrain understand my_project "解释结算主流程"
```
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_cli -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/runtime/projectbrain_cli/main.py tests/test_cli.py README.md docs/projectbrain/local-runtime.md
git commit -m "feat(cli): add understand command for task bundles"
```

---

### Task 4: `feat/v1-08-knowledge-db-bootstrap`

**Files:**
- Create: `packages/runtime/projectbrain_runtime/knowledge_store.py`
- Modify: `packages/runtime/projectbrain_runtime/repository.py`
- Create: `tests/test_knowledge_store.py`
- Modify: `README.md`
- Modify: `docs/projectbrain/local-runtime.md`

- [ ] **Step 1: Write the failing SQLite bootstrap test**

```python
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.knowledge_store import SQLiteKnowledgeStore  # noqa: E402


class SQLiteKnowledgeStoreTest(unittest.TestCase):
    def test_ensure_creates_v1_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "knowledge.db"
            store = SQLiteKnowledgeStore(db_path)

            store.ensure()

            connection = sqlite3.connect(db_path)
            try:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
            finally:
                connection.close()

            self.assertIn("knowledge_units", table_names)
            self.assertIn("claims", table_names)
            self.assertIn("evidence_items", table_names)
            self.assertIn("entity_links", table_names)
            self.assertIn("review_events", table_names)
            self.assertIn("quality_flags", table_names)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_knowledge_store -v
```

Expected: FAIL with `ModuleNotFoundError` for `projectbrain_runtime.knowledge_store`.

- [ ] **Step 3: Add the minimal SQLite bootstrap implementation**

```python
"""SQLite knowledge store bootstrap for ProjectBrain V1."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteKnowledgeStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def ensure(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_units (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  knowledge_type TEXT NOT NULL,
                  title TEXT NOT NULL,
                  statement TEXT NOT NULL,
                  summary TEXT,
                  status TEXT NOT NULL,
                  review_state TEXT NOT NULL,
                  confidence REAL NOT NULL DEFAULT 0.5,
                  risk_level TEXT,
                  source_type TEXT NOT NULL,
                  last_verified_at TEXT,
                  created_by TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS claims (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  knowledge_unit_id TEXT,
                  claim_type TEXT NOT NULL,
                  statement TEXT NOT NULL,
                  scope_type TEXT,
                  scope_key TEXT,
                  review_state TEXT NOT NULL,
                  confidence REAL NOT NULL DEFAULT 0.5,
                  risk_level TEXT,
                  source_type TEXT NOT NULL,
                  last_verified_at TEXT,
                  created_by TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence_items (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  evidence_type TEXT NOT NULL,
                  title TEXT NOT NULL,
                  uri TEXT,
                  content_hash TEXT,
                  version_ref TEXT,
                  source_root TEXT,
                  retrieval_status TEXT NOT NULL,
                  last_checked_at TEXT,
                  created_by TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS entity_links (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id TEXT NOT NULL,
                  entity_type TEXT NOT NULL,
                  entity_key TEXT NOT NULL,
                  link_type TEXT NOT NULL,
                  strength REAL NOT NULL DEFAULT 1.0,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_events (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  actor TEXT,
                  before_state_json TEXT,
                  after_state_json TEXT,
                  note TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quality_flags (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id TEXT NOT NULL,
                  flag_type TEXT NOT NULL,
                  severity TEXT NOT NULL,
                  status TEXT NOT NULL,
                  reason TEXT,
                  detected_by TEXT,
                  created_at TEXT NOT NULL,
                  resolved_at TEXT
                );
                """
            )
            connection.commit()
        finally:
            connection.close()
```

```python
from projectbrain_runtime.knowledge_store import SQLiteKnowledgeStore


class JsonProjectBrainRepository(ProjectBrainRepository):
    def __init__(
        self,
        root: str | Path = ".projectbrain",
        *,
        knowledge_db_path: str | Path | None = None,
    ) -> None:
        self.store = ProjectBrainStore(root)
        default_db_path = Path(root) / "knowledge.db"
        self.knowledge_store = SQLiteKnowledgeStore(knowledge_db_path or default_db_path)

    def ensure(self) -> None:
        self.store.ensure()
        self.knowledge_store.ensure()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_knowledge_store tests.test_repository -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/runtime/projectbrain_runtime/knowledge_store.py packages/runtime/projectbrain_runtime/repository.py tests/test_knowledge_store.py README.md docs/projectbrain/local-runtime.md
git commit -m "feat(store): bootstrap sqlite knowledge database"
```

---

## Validation Matrix

**Per microbranch default verification**
- `feat/v1-01-bundle-schema`
  - `python3 -m unittest tests.test_bundle -v`
- `feat/v1-02-bundle-builder`
  - `python3 -m unittest tests.test_bundle tests.test_repository -v`
- `feat/v1-05-cli-understand`
  - `python3 -m unittest tests.test_cli.ProjectBrainCliTest.test_understand_returns_task_understanding_bundle -v`
  - `python3 -m unittest tests.test_cli -v`
- `feat/v1-08-knowledge-db-bootstrap`
  - `python3 -m unittest tests.test_knowledge_store tests.test_repository -v`

**Integration checkpoint on `feat/v1-product` after all four merge**

```bash
python3 -m unittest \
  tests.test_bundle \
  tests.test_repository \
  tests.test_cli \
  tests.test_codex_brain -v
```

Expected: PASS.

---

## Branching Sequence

- Start from `feat/v1-product`
- Create and complete branches in order:
  1. `feat/v1-01-bundle-schema`
  2. `feat/v1-02-bundle-builder`
  3. `feat/v1-05-cli-understand`
  4. `feat/v1-08-knowledge-db-bootstrap`
- After each branch:
  - run the branch-specific verification commands
  - push the branch
  - merge back into `feat/v1-product`
- After the fourth branch:
  - run the integration checkpoint
  - continue to the next batch only if the checkpoint passes

---

## Spec Coverage Check

- V1 unified object: covered by Task 1 and Task 2.
- V1 unified CLI entrypoint: covered by Task 3.
- SQLite knowledge bootstrap: covered by Task 4.
- Small-step, test-after-each-step workflow: covered by all tasks and validation matrix.

## Placeholder Scan

- No `TODO`, `TBD`, or deferred implementation markers remain in the first four branch tasks.
- All code-bearing steps include concrete code or commands.

## Type Consistency Check

- Bundle output consistently uses `bundle`, `bundle_type`, `project_id`, `task`, and `task_type`.
- SQLite bootstrap consistently uses `SQLiteKnowledgeStore` and the six initial tables across code and tests.

