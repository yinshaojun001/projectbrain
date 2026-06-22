import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_cli.codex_session import ManagedSessionResult, build_extraction_prompt, persist_session_result  # noqa: E402
from projectbrain_runtime.brain.extraction import parse_extraction_output  # noqa: E402
from projectbrain_runtime.brain.repository import BrainRepository  # noqa: E402
from projectbrain_runtime.brain.service import BrainService  # noqa: E402


class CodexBrainTest(unittest.TestCase):
    def test_parse_extraction_output_accepts_json_code_block(self):
        output = '''Here is the result:\n```json\n{"session_summary":"Refund fee discussion.","candidates":[{"type":"constraint","statement":"Refund fee must be booked separately.","tags":["refund"],"applies_to":["RefundService"],"confidence":0.9,"review_state":"human_review_required"}]}\n```'''

        parsed = parse_extraction_output(output)

        self.assertEqual(parsed["session_summary"], "Refund fee discussion.")
        self.assertEqual(parsed["candidates"][0]["type"], "constraint")

    def test_build_extraction_prompt_contains_safety_rules(self):
        prompt = build_extraction_prompt()

        self.assertIn("Return ONLY JSON", prompt)
        self.assertIn("Do NOT include", prompt)
        self.assertIn("secrets or credentials", prompt)

    def test_persist_session_result_writes_session_and_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            result = ManagedSessionResult(
                session_id="session_test",
                project_id="payment",
                task="Refund fee",
                transcript_path=str(Path(tmp) / "session.log"),
                extraction_output='{"session_summary":"Refund fee discussion.","candidates":[{"type":"constraint","statement":"Refund fee must be booked separately.","tags":["refund"]}]}',
                changed_files=["service/refund/RefundService.java"],
            )

            persisted = persist_session_result(service, result)

            self.assertEqual(persisted["session"]["session_id"], "session_test")
            self.assertEqual(persisted["candidate_count"], 1)
            self.assertEqual(service.list_candidates()["candidates"][0]["proposed_unit"]["type"], "constraint")


if __name__ == "__main__":
    unittest.main()
