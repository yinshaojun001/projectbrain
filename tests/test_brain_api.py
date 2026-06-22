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
