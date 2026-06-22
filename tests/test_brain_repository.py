import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate  # noqa: E402
from projectbrain_runtime.brain.repository import BrainRepository  # noqa: E402


class BrainRepositoryTest(unittest.TestCase):
    def make_knowledge_unit(self, unit_id="ku_refund", statement="Refund fee must be booked separately."):
        return KnowledgeUnit(
            id=unit_id,
            type="constraint",
            title="Refund constraint",
            statement=statement,
        )

    def make_memory_candidate(self, candidate_id="mc_refund", review_state="human_review_required"):
        return MemoryCandidate(
            candidate_id=candidate_id,
            project_id="payment",
            session_id="session1",
            proposed_unit={"type": "constraint", "statement": "Refund fee rule"},
            review_state=review_state,
        )

    def make_conversation_session(self, session_id="session1", summary="Captured refund discussion."):
        return ConversationSession(
            session_id=session_id,
            project_id="payment",
            summary=summary,
        )

    def test_repository_creates_project_brain_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()

            self.assertTrue((Path(tmp) / ".projectbrain/brain/manifest.json").exists())
            self.assertTrue((Path(tmp) / ".projectbrain/brain/knowledge_units.jsonl").exists())
            self.assertTrue((Path(tmp) / ".projectbrain/brain/memory_candidates.jsonl").exists())
            self.assertTrue((Path(tmp) / ".projectbrain/brain/conversations.jsonl").exists())

    def test_repository_creates_all_brain_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()

            for relative_path in (
                ".projectbrain/brain/manifest.json",
                ".projectbrain/brain/knowledge_units.jsonl",
                ".projectbrain/brain/memory_candidates.jsonl",
                ".projectbrain/brain/conversations.jsonl",
                ".projectbrain/brain/concepts.jsonl",
                ".projectbrain/brain/links.jsonl",
            ):
                self.assertTrue((Path(tmp) / relative_path).exists(), relative_path)

    def test_missing_get_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()

            with self.assertRaises(FileNotFoundError):
                repo.get_knowledge_unit("missing_ku")
            with self.assertRaises(FileNotFoundError):
                repo.get_memory_candidate("missing_mc")
            with self.assertRaises(FileNotFoundError):
                repo.get_conversation_session("missing_session")

    def test_save_and_list_knowledge_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_knowledge_unit(self.make_knowledge_unit())

            units = repo.list_knowledge_units()

            self.assertEqual([unit.id for unit in units], ["ku_refund"])

    def test_get_and_list_each_record_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_knowledge_unit(self.make_knowledge_unit())
            repo.save_memory_candidate(self.make_memory_candidate())
            repo.save_conversation_session(self.make_conversation_session())

            units = repo.list_knowledge_units()
            candidates = repo.list_memory_candidates()
            sessions = repo.list_conversation_sessions()

            self.assertEqual([unit.id for unit in units], ["ku_refund"])
            self.assertEqual([candidate.candidate_id for candidate in candidates], ["mc_refund"])
            self.assertEqual([session.session_id for session in sessions], ["session1"])
            self.assertEqual(repo.get_knowledge_unit("ku_refund").statement, "Refund fee must be booked separately.")
            self.assertEqual(repo.get_memory_candidate("mc_refund").review_state, "human_review_required")
            self.assertEqual(repo.get_conversation_session("session1").summary, "Captured refund discussion.")

    def test_update_candidate_replaces_existing_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_memory_candidate(self.make_memory_candidate())
            repo.save_memory_candidate(self.make_memory_candidate(review_state="rejected"))

            candidates = repo.list_memory_candidates()

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].review_state, "rejected")

    def test_upsert_replaces_existing_record_for_each_record_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_knowledge_unit(self.make_knowledge_unit(statement="Original rule."))
            repo.save_knowledge_unit(self.make_knowledge_unit(statement="Updated rule."))
            repo.save_memory_candidate(self.make_memory_candidate())
            repo.save_memory_candidate(self.make_memory_candidate(review_state="rejected"))
            repo.save_conversation_session(self.make_conversation_session(summary="Original summary."))
            repo.save_conversation_session(self.make_conversation_session(summary="Updated summary."))

            self.assertEqual(len(repo.list_knowledge_units()), 1)
            self.assertEqual(repo.get_knowledge_unit("ku_refund").statement, "Updated rule.")
            self.assertEqual(len(repo.list_memory_candidates()), 1)
            self.assertEqual(repo.get_memory_candidate("mc_refund").review_state, "rejected")
            self.assertEqual(len(repo.list_conversation_sessions()), 1)
            self.assertEqual(repo.get_conversation_session("session1").summary, "Updated summary.")

    def test_repository_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_repo = BrainRepository(Path(tmp))
            first_repo.ensure()
            first_repo.save_knowledge_unit(self.make_knowledge_unit())
            first_repo.save_memory_candidate(self.make_memory_candidate())
            first_repo.save_conversation_session(self.make_conversation_session())

            second_repo = BrainRepository(Path(tmp))

            self.assertEqual(second_repo.get_knowledge_unit("ku_refund").title, "Refund constraint")
            self.assertEqual(second_repo.get_memory_candidate("mc_refund").project_id, "payment")
            self.assertEqual(second_repo.get_conversation_session("session1").summary, "Captured refund discussion.")

    def test_upsert_collapses_duplicate_existing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            first = self.make_knowledge_unit(statement="First duplicate.").to_dict()
            second = self.make_knowledge_unit(statement="Second duplicate.").to_dict()
            other = self.make_knowledge_unit(unit_id="ku_other", statement="Unrelated rule.").to_dict()
            repo.knowledge_path.write_text(
                "".join(json.dumps(item, sort_keys=True) + "\n" for item in (first, second, other)),
                encoding="utf-8",
            )

            repo.save_knowledge_unit(self.make_knowledge_unit(statement="Updated canonical record."))

            units = repo.list_knowledge_units()
            matching_units = [unit for unit in units if unit.id == "ku_refund"]
            self.assertEqual([unit.id for unit in units], ["ku_refund", "ku_other"])
            self.assertEqual(len(matching_units), 1)
            self.assertEqual(matching_units[0].statement, "Updated canonical record.")

    def test_save_and_get_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_conversation_session(self.make_conversation_session())

            session = repo.get_conversation_session("session1")

            self.assertEqual(session.summary, "Captured refund discussion.")

    def test_normal_writes_do_not_leave_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            repo.ensure()
            repo.save_knowledge_unit(self.make_knowledge_unit())

            temp_files = list(repo.root.glob("*.tmp")) + list(repo.root.glob(".*.tmp"))
            self.assertEqual(temp_files, [])


if __name__ == "__main__":
    unittest.main()
