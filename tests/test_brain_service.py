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


    def test_remember_avoids_generated_id_collision_for_unrelated_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            first = service.remember(
                type="constraint",
                title="Shared title",
                statement="First unrelated memory.",
            )["knowledge_unit"]
            second = service.remember(
                type="constraint",
                title="Shared title",
                statement="Second unrelated memory.",
            )["knowledge_unit"]

            units = service.list_knowledge()["knowledge_units"]

            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(len(units), 2)
            self.assertEqual([unit["statement"] for unit in units], ["First unrelated memory.", "Second unrelated memory."])



if __name__ == "__main__":
    unittest.main()
