import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))

from projectbrain_adapters.context_pack import ContextPackBuilder


class ContextPackBuilderTest(unittest.TestCase):
    def test_context_pack_builder_groups_facts_and_warnings(self):
        export = {
            "project_id": "payment_demo",
            "entities": [
                {
                    "entity_type": "Interface",
                    "stable_key": "codegraph:interface:payment.lg::SettlementService",
                    "name": "SettlementService",
                    "qualified_name": "payment.lg::SettlementService",
                    "properties": {
                        "language": "java",
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
                        "language": "java",
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
                        "language": "java",
                        "file_path": "service/src/main/java/payment/lg/SettlementServiceImpl.java",
                        "module": "service",
                        "signature": None,
                    },
                    "source_refs": ["codegraph://payment_demo/node/class:1"],
                },
            ],
            "relations": [
                {
                    "relation_type": "CALLS",
                    "from_stable_key": "codegraph:method:payment.lg::SettlementService::settlement",
                    "to_stable_key": "codegraph:class:payment.lg::SettlementServiceImpl",
                    "confidence": 0.75,
                    "properties": {"source_edge_kind": "calls"},
                    "source_refs": ["codegraph://payment_demo/edge/1"],
                }
            ],
            "sources": [
                {
                    "source_type": "code_location",
                    "uri": "codegraph://payment_demo/node/interface:1",
                    "locator": {
                        "file": "contract/src/main/java/payment/lg/SettlementService.java",
                        "symbol": "payment.lg::SettlementService",
                    },
                },
                {
                    "source_type": "code_location",
                    "uri": "codegraph://payment_demo/node/method:1",
                    "locator": {
                        "file": "contract/src/main/java/payment/lg/SettlementService.java",
                        "symbol": "payment.lg::SettlementService::settlement",
                    },
                },
                {
                    "source_type": "code_location",
                    "uri": "codegraph://payment_demo/node/class:1",
                    "locator": {
                        "file": "service/src/main/java/payment/lg/SettlementServiceImpl.java",
                        "symbol": "payment.lg::SettlementServiceImpl",
                    },
                },
            ],
        }

        pack = ContextPackBuilder(task="explain settlement flow", export=export).build()

        self.assertEqual(pack["project_id"], "payment_demo")
        recommended_files = {item["file"] for item in pack["recommended_files"]}
        self.assertIn("contract/src/main/java/payment/lg/SettlementService.java", recommended_files)
        self.assertTrue(any(section["type"] == "entrypoint_flows" for section in pack["sections"]))
        self.assertTrue(
            any(
                item["concept"] == "Settlement Flow"
                for section in pack["sections"]
                if section["type"] == "candidate_business_concepts"
                for item in section["items"]
            )
        )
        self.assertTrue(any(warning["code"] == "no_human_confirmed_claims" for warning in pack["warnings"]))


if __name__ == "__main__":
    unittest.main()
