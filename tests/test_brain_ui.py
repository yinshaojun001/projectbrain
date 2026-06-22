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
