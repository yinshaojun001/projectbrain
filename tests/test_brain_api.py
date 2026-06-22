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
    brain_candidate_reject_handler,
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

    def test_search_applies_type_filter(self):
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
            service = runtime.brain_for_project("payment")
            constraint = service.remember(
                type="constraint",
                statement="Refund flow must preserve settlement ordering.",
                tags=["refund"],
            )["knowledge_unit"]
            service.remember(
                type="gotcha",
                statement="Refund flow has a gotcha for legacy retries.",
                tags=["refund"],
            )

            results = brain_knowledge_list_handler(
                runtime,
                "payment",
                {"q": "refund", "type": "constraint"},
            )

            self.assertEqual([match["id"] for match in results["matches"]], [constraint["id"]])
            self.assertEqual([match["type"] for match in results["matches"]], ["constraint"])

    def test_search_treats_string_false_include_archived_as_false(self):
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
            service = runtime.brain_for_project("payment")
            active = service.remember(
                type="constraint",
                statement="Refund active rule.",
                tags=["refund"],
            )["knowledge_unit"]
            service.remember(
                type="constraint",
                statement="Refund archived rule.",
                tags=["refund"],
                review_state="archived",
            )

            results = brain_knowledge_list_handler(
                runtime,
                "payment",
                {"q": "refund", "include_archived": "false"},
            )

            self.assertEqual([match["id"] for match in results["matches"]], [active["id"]])

    def test_reject_candidate_handler_marks_candidate_rejected(self):
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
            candidate = runtime.brain_for_project("payment").propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "gotcha", "statement": "Refund rejection candidate."}],
            )["candidates"][0]

            rejected = brain_candidate_reject_handler(runtime, "payment", candidate["candidate_id"])

            self.assertEqual(rejected["candidate"]["review_state"], "rejected")
            candidates = brain_candidates_handler(runtime, "payment", {"review_state": "rejected"})
            self.assertEqual([item["candidate_id"] for item in candidates["candidates"]], [candidate["candidate_id"]])


if __name__ == "__main__":
    unittest.main()
