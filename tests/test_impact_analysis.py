import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))

from projectbrain_adapters.impact_analysis import ImpactAnalysisBuilder


class ImpactAnalysisBuilderTest(unittest.TestCase):
    def test_impact_analysis_marks_changed_and_incoming_callers(self):
        export = {
            "project_id": "payment_demo",
            "entities": [
                {
                    "entity_type": "Interface",
                    "stable_key": "codegraph:interface:payment.lg::SettlementService",
                    "name": "SettlementService",
                    "qualified_name": "payment.lg::SettlementService",
                    "properties": {
                        "file_path": "contract/src/main/java/payment/lg/SettlementService.java",
                        "module": "contract",
                        "signature": None,
                    },
                    "source_refs": ["codegraph://payment_demo/node/interface:1"],
                },
                {
                    "entity_type": "Method",
                    "stable_key": "codegraph:method:payment.lg::SettlementService::settlement",
                    "name": "settlement",
                    "qualified_name": "payment.lg::SettlementService::settlement",
                    "properties": {
                        "file_path": "contract/src/main/java/payment/lg/SettlementService.java",
                        "module": "contract",
                        "signature": "Result (SettlementDTO dto)",
                    },
                    "source_refs": ["codegraph://payment_demo/node/method:1"],
                },
                {
                    "entity_type": "Class",
                    "stable_key": "codegraph:class:payment.lg::SettlementServiceImpl",
                    "name": "SettlementServiceImpl",
                    "qualified_name": "payment.lg::SettlementServiceImpl",
                    "properties": {
                        "file_path": "service/src/main/java/payment/lg/SettlementServiceImpl.java",
                        "module": "service",
                        "signature": None,
                    },
                    "source_refs": ["codegraph://payment_demo/node/class:1"],
                },
                {
                    "entity_type": "Method",
                    "stable_key": "codegraph:method:payment.lg::SettlementServiceImpl::settlement",
                    "name": "settlement",
                    "qualified_name": "payment.lg::SettlementServiceImpl::settlement",
                    "properties": {
                        "file_path": "service/src/main/java/payment/lg/SettlementServiceImpl.java",
                        "module": "service",
                        "signature": "Result (SettlementDTO dto)",
                    },
                    "source_refs": ["codegraph://payment_demo/node/method:2"],
                },
                {
                    "entity_type": "Method",
                    "stable_key": "codegraph:method:payment.lg::SettlementFlowTest::settlement",
                    "name": "settlement",
                    "qualified_name": "payment.lg::SettlementFlowTest::settlement",
                    "properties": {
                        "file_path": "service/src/test/java/payment/lg/SettlementFlowTest.java",
                        "module": "service",
                        "signature": "void ()",
                    },
                    "source_refs": ["codegraph://payment_demo/node/test:1"],
                },
            ],
            "relations": [
                {
                    "relation_type": "CALLS",
                    "from_stable_key": "codegraph:method:payment.lg::SettlementService::settlement",
                    "to_stable_key": "codegraph:method:payment.lg::SettlementServiceImpl::settlement",
                    "confidence": 0.75,
                    "properties": {"source_edge_kind": "calls"},
                    "source_refs": ["codegraph://payment_demo/edge/1"],
                },
                {
                    "relation_type": "CALLS",
                    "from_stable_key": "codegraph:method:payment.lg::SettlementFlowTest::settlement",
                    "to_stable_key": "codegraph:method:payment.lg::SettlementService::settlement",
                    "confidence": 0.9,
                    "properties": {"source_edge_kind": "calls"},
                    "source_refs": ["codegraph://payment_demo/edge/2"],
                },
                {
                    "relation_type": "IMPLEMENTS_INTERFACE",
                    "from_stable_key": "codegraph:class:payment.lg::SettlementServiceImpl",
                    "to_stable_key": "codegraph:interface:payment.lg::SettlementService",
                    "confidence": 1.0,
                    "properties": {"source_edge_kind": "implements"},
                    "source_refs": ["codegraph://payment_demo/edge/3"],
                },
            ],
            "sources": [],
        }

        analysis = ImpactAnalysisBuilder(
            task="modify settlement API",
            export=export,
            changed_files=["contract/src/main/java/payment/lg/SettlementService.java"],
            changed_symbols=[],
        ).build()

        changed_section = next(section for section in analysis["sections"] if section["type"] == "changed_entities")
        affected_calls = next(section for section in analysis["sections"] if section["type"] == "affected_calls")
        concepts = next(
            section for section in analysis["sections"] if section["type"] == "affected_candidate_business_concepts"
        )

        self.assertEqual(len(changed_section["items"]), 2)
        self.assertTrue(any(item["direction"] == "incoming" for item in affected_calls["items"]))
        self.assertTrue(any(item["concept"] == "Settlement Flow" for item in concepts["items"]))
        self.assertEqual(analysis["review_recommendation"]["action"], "manual_review_required")
        self.assertTrue(analysis["recommended_tests"])


if __name__ == "__main__":
    unittest.main()
