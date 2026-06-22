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
