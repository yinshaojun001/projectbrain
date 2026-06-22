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
