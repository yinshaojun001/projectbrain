import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit  # noqa: E402
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



    def test_repository_create_with_available_id_is_atomic_for_same_base_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            first = repo.create_knowledge_unit_with_available_id(
                KnowledgeUnit(id="ku_collision", type="constraint", title="Collision", statement="First record.")
            )
            second = repo.create_knowledge_unit_with_available_id(
                KnowledgeUnit(id="ku_collision", type="constraint", title="Collision", statement="Second record.")
            )

            units = repo.list_knowledge_units()

            self.assertEqual(first.id, "ku_collision")
            self.assertEqual(second.id, "ku_collision_2")
            self.assertEqual([unit.statement for unit in units], ["First record.", "Second record."])


    def test_concurrent_confirm_candidate_is_atomic_and_idempotent(self):
        class RacingConfirmRepository(BrainRepository):
            def __init__(self, project_path: Path) -> None:
                super().__init__(project_path)
                self.confirm_barrier = Barrier(2)
                self.raced_candidate_id: str | None = None

            def get_memory_candidate(self, candidate_id: str):  # type: ignore[no-untyped-def]
                candidate = super().get_memory_candidate(candidate_id)
                if candidate_id == self.raced_candidate_id and candidate.review_state == "human_review_required":
                    self.confirm_barrier.wait(timeout=5)
                return candidate

        with tempfile.TemporaryDirectory() as tmp:
            repo = RacingConfirmRepository(Path(tmp))
            service = BrainService(repo)
            candidate = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "decision", "statement": "Concurrent confirmation creates one unit."}],
            )["candidates"][0]
            repo.raced_candidate_id = candidate["candidate_id"]
            start_barrier = Barrier(2)

            def confirm_after_both_threads_are_ready() -> dict:
                start_barrier.wait(timeout=5)
                return service.confirm_candidate(candidate["candidate_id"])

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: confirm_after_both_threads_are_ready(), range(2)))

            units = service.list_knowledge()["knowledge_units"]
            linked_candidate = service.list_candidates(review_state="human_confirmed")["candidates"][0]
            returned_unit_ids = {result["knowledge_unit"]["id"] for result in results}

            self.assertEqual(len(returned_unit_ids), 1)
            self.assertEqual(len(units), 1)
            self.assertEqual(linked_candidate["extraction"]["confirmed_knowledge_unit_id"], units[0]["id"])
            self.assertEqual(returned_unit_ids, {units[0]["id"]})

    def test_confirm_candidate_twice_is_idempotent_and_does_not_duplicate_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            candidate = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "decision", "statement": "Use settlement v2 for refunds."}],
            )["candidates"][0]

            first = service.confirm_candidate(candidate["candidate_id"])
            second = service.confirm_candidate(candidate["candidate_id"])

            self.assertEqual(first["knowledge_unit"]["id"], second["knowledge_unit"]["id"])
            self.assertEqual(service.list_knowledge()["knowledge_unit_count"], 1)

    def test_candidate_invalid_state_transitions_raise_clear_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            confirmed = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "gotcha", "statement": "Confirmed candidate."}],
            )["candidates"][0]
            rejected = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "risk", "statement": "Rejected candidate."}],
            )["candidates"][0]

            service.confirm_candidate(confirmed["candidate_id"])
            service.reject_candidate(rejected["candidate_id"])

            with self.assertRaisesRegex(ValueError, "Cannot reject confirmed candidate"):
                service.reject_candidate(confirmed["candidate_id"])
            with self.assertRaisesRegex(ValueError, "Cannot confirm rejected candidate"):
                service.confirm_candidate(rejected["candidate_id"])

    def test_search_excludes_archived_by_default_and_can_include_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            active = service.remember(type="constraint", statement="Refund active rule.", tags=["refund"])["knowledge_unit"]
            archived = service.remember(
                type="constraint",
                statement="Refund archived rule.",
                tags=["refund"],
                review_state="archived",
            )["knowledge_unit"]

            default_search = service.search("refund")
            archived_search = service.search("refund", include_archived=True)

            self.assertEqual([match["id"] for match in default_search["matches"]], [active["id"]])
            self.assertEqual({match["id"] for match in archived_search["matches"]}, {active["id"], archived["id"]})

    def test_list_knowledge_filters_and_archived_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = BrainRepository(Path(tmp))
            service = BrainService(repo)
            constraint = service.remember(
                type="constraint",
                statement="Refund settlement constraint.",
                tags=["refund"],
                review_state="human_confirmed",
            )["knowledge_unit"]
            repo.save_knowledge_unit(
                KnowledgeUnit(
                    id="ku_stale_workflow",
                    type="workflow",
                    title="Stale workflow",
                    statement="Old account workflow.",
                    tags=["account"],
                    review_state="human_review_required",
                    staleness={"state": "stale", "reason": "old docs"},
                )
            )
            service.remember(type="risk", statement="Archived refund risk.", tags=["refund"], review_state="archived")

            self.assertEqual([unit["id"] for unit in service.list_knowledge(type="constraint")["knowledge_units"]], [constraint["id"]])
            self.assertEqual([unit["id"] for unit in service.list_knowledge(review_state="human_confirmed")["knowledge_units"]], [constraint["id"]])
            self.assertEqual([unit["id"] for unit in service.list_knowledge(tag="refund")["knowledge_units"]], [constraint["id"]])
            self.assertEqual([unit["id"] for unit in service.list_knowledge(staleness="stale")["knowledge_units"]], ["ku_stale_workflow"])
            self.assertEqual(service.list_knowledge()["knowledge_unit_count"], 2)
            self.assertEqual(service.list_knowledge(include_archived=True)["knowledge_unit_count"], 3)

    def test_list_candidates_filters_pending_rejected_and_confirmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            pending, rejected, confirmed = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[
                    {"type": "risk", "statement": "Pending candidate."},
                    {"type": "risk", "statement": "Rejected candidate."},
                    {"type": "risk", "statement": "Confirmed candidate."},
                ],
            )["candidates"]

            service.reject_candidate(rejected["candidate_id"])
            service.confirm_candidate(confirmed["candidate_id"])

            self.assertEqual([candidate["candidate_id"] for candidate in service.list_candidates(review_state="human_review_required")["candidates"]], [pending["candidate_id"]])
            self.assertEqual([candidate["candidate_id"] for candidate in service.list_candidates(review_state="rejected")["candidates"]], [rejected["candidate_id"]])
            self.assertEqual([candidate["candidate_id"] for candidate in service.list_candidates(review_state="human_confirmed")["candidates"]], [confirmed["candidate_id"]])

    def test_save_session_and_list_sessions_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            session = ConversationSession(
                session_id="session1",
                project_id="payment",
                task="Capture memories",
                summary="Remembered refund rules.",
                changed_files=["RefundService.py"],
            )

            result = service.save_session(session)
            sessions = service.list_sessions()

            self.assertEqual(result["session"]["session_id"], "session1")
            self.assertEqual(sessions["session_count"], 1)
            self.assertEqual(sessions["sessions"][0]["summary"], "Remembered refund rules.")
            self.assertEqual(sessions["sessions"][0]["changed_files"], ["RefundService.py"])

    def test_summary_counts_and_groups_units_and_pending_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            service.remember(type="constraint", statement="Confirmed rule.", review_state="human_confirmed")
            service.remember(type="risk", statement="Pending risk.")
            service.remember(type="risk", statement="Archived risk.", review_state="archived")
            candidates = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[
                    {"type": "gotcha", "statement": "Pending candidate."},
                    {"type": "gotcha", "statement": "Rejected candidate."},
                ],
            )["candidates"]
            service.reject_candidate(candidates[1]["candidate_id"])

            summary = service.summary()

            self.assertEqual(summary["knowledge_unit_count"], 3)
            self.assertEqual(summary["candidate_count"], 1)
            self.assertEqual(summary["by_type"], {"constraint": 1, "risk": 2})
            self.assertEqual(summary["by_review_state"], {"human_confirmed": 1, "human_review_required": 1, "archived": 1})

    def test_generated_candidate_ids_do_not_overwrite_unrelated_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            result = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[
                    {"type": "risk", "title": "Collision", "statement": "First candidate."},
                    {"type": "risk", "title": "Collision", "statement": "Second candidate."},
                ],
            )

            candidates = service.list_candidates()["candidates"]

            self.assertNotEqual(result["candidates"][0]["candidate_id"], result["candidates"][1]["candidate_id"])
            self.assertEqual([candidate["proposed_unit"]["statement"] for candidate in candidates], ["First candidate.", "Second candidate."])

    def test_confirm_candidate_generated_unit_id_collision_does_not_overwrite_existing_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            existing = service.remember(type="constraint", title="Collision", statement="Existing unit.")["knowledge_unit"]
            candidate = service.propose_memories(
                project_id="payment",
                session_id="session1",
                candidates=[{"type": "constraint", "title": "Collision", "statement": "Confirmed unit."}],
            )["candidates"][0]

            confirmed = service.confirm_candidate(candidate["candidate_id"])["knowledge_unit"]
            units = service.list_knowledge()["knowledge_units"]

            self.assertNotEqual(existing["id"], confirmed["id"])
            self.assertEqual([unit["statement"] for unit in units], ["Existing unit.", "Confirmed unit."])



if __name__ == "__main__":
    unittest.main()
