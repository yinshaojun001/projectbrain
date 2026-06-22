import json
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

    def test_make_brain_id_disambiguates_cjk_only_text(self):
        first = make_brain_id("ku", "退款手续费不能影响结算本金")
        second = make_brain_id("ku", "订单状态必须同步")

        self.assertNotEqual(first, "ku_memory")
        self.assertNotEqual(second, "ku_memory")
        self.assertNotEqual(first, second)

    def test_make_brain_id_disambiguates_truncated_long_text(self):
        shared_prefix = " ".join(["refund"] * 20)
        first = make_brain_id("ku", f"{shared_prefix} settlement")
        second = make_brain_id("ku", f"{shared_prefix} principal")

        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first.removeprefix("ku_")), 64 + 1 + 12)
        self.assertLessEqual(len(second.removeprefix("ku_")), 64 + 1 + 12)

    def test_knowledge_unit_defensively_copies_mutable_inputs(self):
        tags = ["refund"]
        source = {"file": "RefundService.java"}
        evidence = [{"kind": "test"}]

        unit = KnowledgeUnit(
            id="ku_defensive_copy",
            type="constraint",
            title="Defensive copy",
            statement="Mutable constructor inputs must not mutate the model.",
            tags=tags,
            source=source,
            evidence=evidence,
        )

        tags.append("settlement")
        source["file"] = "Other.java"
        evidence[0]["kind"] = "review"

        self.assertEqual(unit.tags, ["refund"])
        self.assertEqual(unit.source, {"file": "RefundService.java"})
        self.assertEqual(unit.evidence, [{"kind": "test"}])

    def test_knowledge_unit_rejects_direct_container_mutation(self):
        unit = KnowledgeUnit(
            id="ku_immutable",
            type="constraint",
            title="Immutable containers",
            statement="Public containers should not be directly mutable.",
            tags=["refund"],
            source={"file": "RefundService.java"},
        )

        with self.assertRaises(TypeError):
            unit.tags.append("settlement")
        with self.assertRaises(TypeError):
            unit.source["line"] = 42

        self.assertEqual(unit.tags, ["refund"])
        self.assertEqual(unit.source, {"file": "RefundService.java"})
        self.assertEqual(unit.to_dict()["tags"], ["refund"])
        self.assertEqual(unit.to_dict()["source"], {"file": "RefundService.java"})

    def test_memory_candidate_rejects_direct_proposed_unit_mutation(self):
        candidate = MemoryCandidate(
            candidate_id="mc_immutable",
            project_id="payment",
            session_id=None,
            proposed_unit={
                "type": "constraint",
                "title": "Immutable proposed unit",
                "statement": "Proposed units should not be directly mutable.",
                "tags": ["refund"],
            },
        )

        with self.assertRaises(TypeError):
            candidate.proposed_unit["title"] = "Changed"
        with self.assertRaises(TypeError):
            candidate.proposed_unit["tags"].append("settlement")

        self.assertEqual(candidate.proposed_unit["title"], "Immutable proposed unit")
        self.assertEqual(candidate.proposed_unit["tags"], ["refund"])
        self.assertEqual(candidate.to_dict()["proposed_unit"]["tags"], ["refund"])

    def test_conversation_session_rejects_direct_changed_files_mutation(self):
        session = ConversationSession(
            session_id="session_immutable",
            project_id="payment",
            changed_files=["service/refund/RefundService.java"],
        )

        with self.assertRaises(TypeError):
            session.changed_files.append("service/refund/Other.java")

        self.assertEqual(session.changed_files, ["service/refund/RefundService.java"])
        self.assertEqual(session.to_dict()["changed_files"], ["service/refund/RefundService.java"])

    def test_to_dict_returns_builtin_json_serializable_containers(self):
        candidate = MemoryCandidate(
            candidate_id="mc_plain_to_dict",
            project_id="payment",
            session_id=None,
            proposed_unit={
                "type": "constraint",
                "title": "Plain containers",
                "statement": "Serialized data should use builtin containers.",
                "tags": ["refund"],
            },
            evidence=[{"snippets": ["refund fee"]}],
        )

        data = candidate.to_dict()

        self.assertIs(type(data), dict)
        self.assertIs(type(data["proposed_unit"]), dict)
        self.assertIs(type(data["proposed_unit"]["tags"]), list)
        self.assertIs(type(data["evidence"]), list)
        self.assertIs(type(data["evidence"][0]), dict)
        self.assertIs(type(data["evidence"][0]["snippets"]), list)
        json.dumps(data)

    def test_knowledge_unit_normalizes_falsey_review_state(self):
        unit = KnowledgeUnit(
            id="ku_review_state_default",
            type="constraint",
            title="Review state default",
            statement="Falsey review state should be normalized.",
            review_state=None,
        )

        self.assertEqual(unit.to_dict()["review_state"], "human_review_required")

    def test_memory_candidate_normalizes_falsey_review_state(self):
        candidate = MemoryCandidate(
            candidate_id="mc_review_state_default",
            project_id="payment",
            session_id=None,
            proposed_unit={
                "type": "constraint",
                "title": "Review state default",
                "statement": "Falsey review state should be normalized.",
            },
            review_state="",
        )

        self.assertEqual(candidate.to_dict()["review_state"], "human_review_required")

    def test_knowledge_unit_rejects_invalid_confidence(self):
        for value in (-0.1, 1.1, "nan"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    KnowledgeUnit(
                        id="ku_invalid_confidence",
                        type="constraint",
                        title="Invalid confidence",
                        statement="Confidence must be finite and between zero and one.",
                        confidence=value,
                    )

    def test_memory_candidate_validates_proposed_unit_confidence(self):
        with self.assertRaises(ValueError):
            MemoryCandidate(
                candidate_id="mc_invalid_confidence",
                project_id="payment",
                session_id=None,
                proposed_unit={
                    "type": "constraint",
                    "title": "Invalid confidence",
                    "statement": "Candidate confidence must be validated.",
                    "confidence": 2,
                },
            )

        candidate = MemoryCandidate(
            candidate_id="mc_confidence_normalized",
            project_id="payment",
            session_id=None,
            proposed_unit={
                "type": "constraint",
                "title": "Confidence normalized",
                "statement": "Candidate confidence should be normalized to float.",
                "confidence": "0.7",
            },
        )
        self.assertEqual(candidate.proposed_unit["confidence"], 0.7)

    def test_memory_candidate_rejects_invalid_proposed_unit_shape(self):
        invalid_units = (
            {"statement": "Refund fee rule"},
            {"type": "unsupported", "statement": "Refund fee rule"},
            {"type": "constraint"},
            {"type": "constraint", "statement": "   "},
            {"type": "constraint", "statement": "Refund fee rule", "title": "   "},
        )

        for proposed_unit in invalid_units:
            with self.subTest(proposed_unit=proposed_unit):
                with self.assertRaises(ValueError):
                    MemoryCandidate(
                        candidate_id="mc_invalid_shape",
                        project_id="payment",
                        session_id=None,
                        proposed_unit=proposed_unit,
                    )

    def test_memory_candidate_accepts_plan_compatible_proposed_unit_without_title(self):
        candidate = MemoryCandidate(
            candidate_id="mc_plan_compatible",
            project_id="payment",
            session_id=None,
            proposed_unit={"type": "constraint", "statement": "Refund fee rule"},
        )

        self.assertEqual(
            candidate.to_dict()["proposed_unit"],
            {"type": "constraint", "statement": "Refund fee rule"},
        )

    def test_memory_candidate_normalizes_proposed_unit_string_lists(self):
        candidate = MemoryCandidate(
            candidate_id="mc_normalized_lists",
            project_id="payment",
            session_id=None,
            proposed_unit={
                "type": "constraint",
                "statement": "Refund fee rule",
                "tags": " refund ",
                "applies_to": [" RefundService ", "", "SettlementService"],
            },
        )

        self.assertEqual(candidate.proposed_unit["tags"], ["refund"])
        self.assertEqual(candidate.proposed_unit["applies_to"], ["RefundService", "SettlementService"])

    def test_review_state_strips_whitespace_and_defaults_blank(self):
        unit = KnowledgeUnit(
            id="ku_review_state_strip",
            type="constraint",
            title="Review state strip",
            statement="Whitespace review states should be normalized.",
            review_state=" human_confirmed ",
        )
        candidate = MemoryCandidate(
            candidate_id="mc_review_state_blank",
            project_id="payment",
            session_id=None,
            proposed_unit={"type": "constraint", "statement": "Refund fee rule"},
            review_state="   ",
        )

        self.assertEqual(unit.review_state, "human_confirmed")
        self.assertEqual(candidate.review_state, "human_review_required")

    def test_required_knowledge_unit_fields_reject_empty_strings(self):
        with self.assertRaises(ValueError):
            KnowledgeUnit(
                id=" ",
                type="constraint",
                title="Invalid id",
                statement="Statement is present.",
            )

        with self.assertRaises(ValueError):
            KnowledgeUnit(
                id="ku_empty_statement",
                type="constraint",
                title="Invalid statement",
                statement=" ",
            )

    def test_conversation_session_rejects_empty_project_id(self):
        with self.assertRaises(ValueError):
            ConversationSession(session_id="session_1", project_id=" ")


if __name__ == "__main__":
    unittest.main()
