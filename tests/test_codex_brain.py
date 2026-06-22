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

    def test_parse_extraction_output_defaults_invalid_confidence_and_keeps_valid_candidate(self):
        parsed = parse_extraction_output(
            '{"session_summary":"Confidence cleanup.",'
            '"candidates":[{"type":"constraint","statement":"Use durable project-local storage.",'
            '"confidence":"high"}]}'
        )

        self.assertEqual(len(parsed["candidates"]), 1)
        self.assertEqual(parsed["candidates"][0]["statement"], "Use durable project-local storage.")
        self.assertEqual(parsed["candidates"][0]["confidence"], 0.8)

    def test_persist_session_result_skips_unsupported_type_without_partial_session_or_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = BrainService(BrainRepository(Path(tmp)))
            result = ManagedSessionResult(
                session_id="session_bad_type",
                project_id="payment",
                task="Unsupported extraction type",
                transcript_path=str(Path(tmp) / "session.log"),
                extraction_output='{"session_summary":"Invalid candidate.","candidates":[{"type":"unsupported","statement":"This should be skipped."}]}',
                changed_files=[],
            )

            persisted = persist_session_result(service, result)

            self.assertEqual(persisted["candidate_count"], 0)
            self.assertEqual(service.list_candidates()["candidate_count"], 0)
            sessions = service.list_sessions()
            self.assertEqual(sessions["session_count"], 1)
            self.assertEqual(sessions["sessions"][0]["candidate_ids"], [])

    def test_parse_extraction_output_rejects_non_object_json_with_clear_value_error(self):
        with self.assertRaisesRegex(ValueError, "Extraction JSON must be an object"):
            parse_extraction_output("[]")

    def test_parse_extraction_output_skips_malformed_candidate_and_keeps_valid_candidate(self):
        parsed = parse_extraction_output(
            '{"session_summary":"Mixed candidates.",'
            '"candidates":['
            '{"type":"constraint","statement":["not","scalar"]},'
            '{"type":"decision","statement":"Candidate normalization is defensive.",'
            '"risk_level":"extreme","review_state":"maybe","tags":"parser","applies_to":null}'
            ']}'
        )

        self.assertEqual(len(parsed["candidates"]), 1)
        candidate = parsed["candidates"][0]
        self.assertEqual(candidate["type"], "decision")
        self.assertEqual(candidate["statement"], "Candidate normalization is defensive.")
        self.assertEqual(candidate["risk_level"], "normal")
        self.assertEqual(candidate["review_state"], "human_review_required")
        self.assertEqual(candidate["tags"], ["parser"])
        self.assertEqual(candidate["applies_to"], [])


from projectbrain_cli.codex_brain import main as codex_brain_main  # noqa: E402


class CodexBrainMainTest(unittest.TestCase):
    def test_codex_brain_no_extract_runs_injected_command_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, *, cwd):
                calls.append((command, cwd))
                return 0

            return_code = codex_brain_main(
                ["--project", tmp, "--no-ui", "--no-extract", "--codex-command", "codex --version"],
                command_runner=fake_runner,
                browser_opener=lambda url: None,
            )

            self.assertEqual(return_code, 0)
            self.assertEqual(calls[0][0], ["codex", "--version"])
            self.assertEqual(calls[0][1], Path(tmp).resolve())

    def test_codex_brain_invalid_project_raises_clear_system_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_project = Path(tmp) / "misspelled-subdir"

            with self.assertRaises(SystemExit) as caught:
                codex_brain_main(
                    ["--project", str(missing_project), "--no-ui", "--no-extract", "--codex-command", "codex --version"],
                    command_runner=lambda command, *, cwd: 0,
                    browser_opener=lambda url: None,
                )

            self.assertEqual(str(caught.exception), f"Project path does not exist: {missing_project.resolve()}")

    def test_codex_brain_invalid_project_does_not_invoke_command_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_project = Path(tmp) / "misspelled-subdir"
            calls = []

            def fake_runner(command, *, cwd):
                calls.append((command, cwd))
                return 0

            with self.assertRaises(SystemExit):
                codex_brain_main(
                    ["--project", str(missing_project), "--no-ui", "--no-extract", "--codex-command", "codex --version"],
                    command_runner=fake_runner,
                    browser_opener=lambda url: None,
                )

            self.assertEqual(calls, [])

    def test_codex_brain_empty_codex_command_raises_clear_system_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, *, cwd):
                calls.append((command, cwd))
                return 0

            with self.assertRaisesRegex(SystemExit, "--codex-command must not be empty"):
                codex_brain_main(
                    ["--project", tmp, "--no-ui", "--no-extract", "--codex-command", ""],
                    command_runner=fake_runner,
                    browser_opener=lambda url: None,
                )

            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
