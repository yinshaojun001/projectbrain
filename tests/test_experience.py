import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))

from projectbrain_adapters.experience import load_experience_seed, match_experience_claims


class ExperienceSeedTest(unittest.TestCase):
    def test_load_and_match_markdown_seed(self):
        content = """# Seed

| id | claim_type | review_state | risk_level | applies_to | statement | confidence | source |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| exp_lg | HUMAN_REVIEW_REQUIRED | pending | high | lg; settlement | Review LG settlement compatibility. | 0.7 | codegraph |
"""
        with tempfile.TemporaryDirectory() as tmp:
            seed_path = Path(tmp) / "experience-seed.md"
            seed_path.write_text(content, encoding="utf-8")

            claims = load_experience_seed(seed_path)
            matched = match_experience_claims(
                claims,
                [
                    {
                        "qualified_name": "payment.lg::SettlementService",
                        "name": "SettlementService",
                        "properties": {"file_path": "contract/payment/lg/SettlementService.java"},
                        "source_refs": ["codegraph://payment/node/1"],
                    }
                ],
                lambda entity: " ".join(
                    [
                        entity["qualified_name"],
                        entity["name"],
                        entity["properties"]["file_path"],
                    ]
                ),
                limit=5,
            )

        self.assertEqual(claims[0]["id"], "exp_lg")
        self.assertEqual(claims[0]["confidence"], 0.7)
        self.assertEqual(matched[0]["matched_entity_count"], 1)
        self.assertIn("codegraph://payment/node/1", matched[0]["matched_sources"])


if __name__ == "__main__":
    unittest.main()
