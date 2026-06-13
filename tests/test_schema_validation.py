import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schema"))

from projectbrain_schema.validation import (  # noqa: E402
    SchemaValidationError,
    validate_context_pack,
    validate_facts_export,
    validate_impact_analysis,
)


class SchemaValidationTest(unittest.TestCase):
    def test_validate_facts_export_requires_entity_sources(self):
        facts = {
            "project_id": "payment_demo",
            "entities": [
                {
                    "entity_type": "Class",
                    "stable_key": "codegraph:class:Payment",
                    "name": "Payment",
                    "qualified_name": "payment::Payment",
                    "source_refs": ["codegraph://payment/node/1"],
                }
            ],
            "relations": [
                {
                    "relation_type": "CALLS",
                    "from_stable_key": "codegraph:class:Payment",
                    "to_stable_key": "codegraph:class:Payment",
                    "confidence": 0.9,
                    "source_refs": ["codegraph://payment/edge/1"],
                }
            ],
            "sources": [
                {
                    "source_type": "code_location",
                    "uri": "codegraph://payment/node/1",
                    "locator": {"file": "Payment.java"},
                }
            ],
        }

        validate_facts_export(facts)
        facts["entities"][0]["source_refs"] = []
        with self.assertRaises(SchemaValidationError):
            validate_facts_export(facts)

    def test_validate_context_pack_and_impact_analysis(self):
        validate_context_pack(
            {
                "context_pack_id": "ctx_payment",
                "project_id": "payment_demo",
                "task": "explain",
                "summary": "summary",
                "sections": [{"type": "project_overview", "items": []}],
            }
        )
        validate_impact_analysis(
            {
                "impact_analysis_id": "impact_payment",
                "project_id": "payment_demo",
                "task": "change",
                "change": {"changed_files": [], "changed_symbols": []},
                "summary": "summary",
                "sections": [{"type": "changed_entities", "items": []}],
                "review_recommendation": {
                    "risk_level": "normal",
                    "action": "review_optional",
                    "reason": "test",
                },
            }
        )


if __name__ == "__main__":
    unittest.main()
