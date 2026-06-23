import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_cli.codex_session import (  # noqa: E402
    ManagedSessionResult,
    build_extraction_prompt,
    persist_session_result,
    run_codex_command_captured,
    sanitize_terminal_transcript,
)
from projectbrain_runtime.brain.extraction import parse_extraction_output  # noqa: E402
from projectbrain_runtime.brain.repository import BrainRepository  # noqa: E402
from projectbrain_runtime.brain.service import BrainService  # noqa: E402


class CodexBrainTest(unittest.TestCase):
    def test_sanitize_terminal_transcript_strips_ansi_controls_and_applies_backspaces(self):
        raw = "\x1b[31mHellp\bo\x1b[0m from Codex\x07\r\nNext\tline\x00"

        cleaned = sanitize_terminal_transcript(raw)

        self.assertEqual(cleaned, "Hello from Codex\nNext\tline")

    def test_run_codex_command_captured_uses_macos_script_without_capture_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                raw_transcript = Path(command[2])
                raw_transcript.write_text("\x1b[32mAssistant\b says hi\x1b[0m\x07", encoding="utf-8")
                return SimpleNamespace(returncode=3)

            return_code, transcript = run_codex_command_captured(
                ["codex", "exec", "remember this"],
                cwd=Path(tmp),
                platform="darwin",
                subprocess_runner=fake_runner,
            )

            self.assertEqual(return_code, 3)
            self.assertEqual(transcript, "Assistan says hi")
            self.assertEqual(calls[0][0][0:2], ["/usr/bin/script", "-q"])
            self.assertEqual(calls[0][0][3:], ["codex", "exec", "remember this"])
            self.assertEqual(calls[0][1], {"cwd": Path(tmp), "check": False})

    def test_run_codex_command_captured_non_macos_preserves_interactive_commands_without_capture_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return SimpleNamespace(returncode=0)

            return_code, transcript = run_codex_command_captured(
                ["codex"],
                cwd=Path(tmp),
                platform="linux",
                subprocess_runner=fake_runner,
            )

            self.assertEqual(return_code, 0)
            self.assertEqual(transcript, "")
            self.assertEqual(calls, [(["codex"], {"cwd": Path(tmp), "check": False})])

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


from projectbrain_cli.codex_brain import _open_url, main as codex_brain_main  # noqa: E402


class CodexBrainMainTest(unittest.TestCase):
    def test_codex_brain_extracts_child_output_into_memory_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, *, cwd):
                calls.append(("codex", command, cwd))
                return (0, "Assistant: Homebrew package is projectbrain but startup command is codex-brain.\n")

            def fake_extractor(prompt, *, cwd):
                calls.append(("extract", prompt, cwd))
                self.assertIn("Homebrew package is projectbrain", prompt)
                return '{"session_summary":"Packaging decision.","candidates":[{"type":"decision","statement":"Homebrew package is projectbrain but the startup command is codex-brain.","tags":["brew","codex-brain"]}]}'

            return_code = codex_brain_main(
                ["--project", tmp, "--no-ui", "--codex-command", "codex exec test"],
                command_runner=fake_runner,
                extraction_runner=fake_extractor,
                session_id_factory=lambda: "session_test",
            )

            self.assertEqual(return_code, 0)
            service = BrainService(BrainRepository(Path(tmp)))
            candidates = service.list_candidates()
            self.assertEqual(candidates["candidate_count"], 1)
            self.assertEqual(
                candidates["candidates"][0]["proposed_unit"]["statement"],
                "Homebrew package is projectbrain but the startup command is codex-brain.",
            )
            sessions = service.list_sessions()
            self.assertEqual(sessions["session_count"], 1)
            self.assertEqual(sessions["sessions"][0]["session_id"], "session_test")
            self.assertEqual(
                sessions["sessions"][0]["turns"],
                [
                    {"role": "user", "content": "test"},
                    {"role": "assistant", "content": "Assistant: Homebrew package is projectbrain but startup command is codex-brain."},
                ],
            )
            transcript_path = Path(tmp).resolve() / ".projectbrain" / "brain" / "transcripts" / "session_test.txt"
            self.assertTrue(sessions["sessions"][0]["privacy"]["stores_full_transcript"])
            self.assertEqual(sessions["sessions"][0]["privacy"]["transcript_path"], str(transcript_path))
            self.assertEqual(
                transcript_path.read_text(encoding="utf-8"),
                "user: test\n\nassistant: Assistant: Homebrew package is projectbrain but startup command is codex-brain.",
            )

    def test_codex_brain_strips_codex_exec_options_from_user_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_runner(command, *, cwd):
                return (0, "Assistant: Run focused tests first.\n")

            return_code = codex_brain_main(
                [
                    "--project",
                    tmp,
                    "--no-ui",
                    "--codex-command",
                    "codex exec -C /repo -m gpt-5 fix tests",
                ],
                command_runner=fake_runner,
                extraction_runner=lambda prompt, *, cwd: '{"session_summary":"","candidates":[]}',
                session_id_factory=lambda: "session_options",
            )

            self.assertEqual(return_code, 0)
            service = BrainService(BrainRepository(Path(tmp)))
            self.assertEqual(
                service.list_sessions()["sessions"][0]["turns"][0],
                {"role": "user", "content": "fix tests"},
            )

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
            brain_root = Path(tmp) / ".projectbrain" / "brain"
            self.assertFalse((brain_root / "conversations.jsonl").exists())
            self.assertFalse((brain_root / "memory_candidates.jsonl").exists())
            self.assertFalse((brain_root / "transcripts").exists())

    def test_codex_brain_codex_exec_subcommand_does_not_persist_as_prompt_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            return_code = codex_brain_main(
                ["--project", tmp, "--no-ui", "--codex-command", "codex exec resume --last"],
                command_runner=lambda command, *, cwd: (0, "Resumed session output.\n"),
                extraction_runner=lambda prompt, *, cwd: self.fail("resume subcommand should not be extracted"),
                session_id_factory=lambda: "session_resume",
            )

            self.assertEqual(return_code, 0)
            brain_root = Path(tmp).resolve() / ".projectbrain" / "brain"
            self.assertFalse((brain_root / "conversations.jsonl").exists())
            self.assertFalse((brain_root / "memory_candidates.jsonl").exists())
            self.assertFalse((brain_root / "transcripts").exists())

    def test_codex_brain_top_level_codex_subcommand_does_not_persist_as_prompt_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            for subcommand in ("doctor", "update"):
                with self.subTest(subcommand=subcommand):
                    return_code = codex_brain_main(
                        ["--project", tmp, "--no-ui", "--codex-command", f"codex {subcommand}"],
                        command_runner=lambda command, *, cwd: (0, f"Codex {subcommand} output.\n"),
                        extraction_runner=lambda prompt, *, cwd: self.fail(f"{subcommand} subcommand should not be extracted"),
                        session_id_factory=lambda: f"session_{subcommand}",
                    )

                    self.assertEqual(return_code, 0)
                    brain_root = Path(tmp).resolve() / ".projectbrain" / "brain"
                    self.assertFalse((brain_root / "conversations.jsonl").exists())
                    self.assertFalse((brain_root / "memory_candidates.jsonl").exists())
                    self.assertFalse((brain_root / "transcripts").exists())

    def test_codex_brain_without_extractable_prompt_does_not_persist_assistant_only_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_runner(command, *, cwd):
                calls.append(("codex", command, cwd))
                return (0, "Assistant output captured from an interactive TUI.\n")

            def fake_extractor(prompt, *, cwd):
                self.fail("assistant-only transcript should not be extracted as a memory pair")

            return_code = codex_brain_main(
                ["--project", tmp, "--no-ui", "--codex-command", "codex"],
                command_runner=fake_runner,
                extraction_runner=fake_extractor,
                session_id_factory=lambda: "session_interactive",
            )

            self.assertEqual(return_code, 0)
            self.assertEqual(calls[0][0], "codex")
            brain_root = Path(tmp).resolve() / ".projectbrain" / "brain"
            self.assertFalse((brain_root / "conversations.jsonl").exists())
            self.assertFalse((brain_root / "memory_candidates.jsonl").exists())
            self.assertFalse((brain_root / "transcripts").exists())

    def test_codex_brain_extraction_failure_still_saves_paired_session_and_returns_child_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()

            def fake_runner(command, *, cwd):
                return (0, "Assistant: Keep brew package naming documented.\n")

            def failing_extractor(prompt, *, cwd):
                raise RuntimeError("extractor unavailable")

            with contextlib.redirect_stderr(stderr):
                return_code = codex_brain_main(
                    ["--project", tmp, "--no-ui", "--codex-command", "codex exec Document brew package naming"],
                    command_runner=fake_runner,
                    extraction_runner=failing_extractor,
                    session_id_factory=lambda: "session_extract_failure",
                )

            self.assertEqual(return_code, 0)
            self.assertIn("ProjectBrain memory extraction failed", stderr.getvalue())
            service = BrainService(BrainRepository(Path(tmp)))
            sessions = service.list_sessions()
            self.assertEqual(sessions["session_count"], 1)
            self.assertEqual(sessions["sessions"][0]["candidate_ids"], [])
            self.assertEqual(
                sessions["sessions"][0]["turns"],
                [
                    {"role": "user", "content": "Document brew package naming"},
                    {"role": "assistant", "content": "Assistant: Keep brew package naming documented."},
                ],
            )
            self.assertEqual(service.list_candidates()["candidate_count"], 0)
            self.assertTrue(
                (
                    Path(tmp).resolve()
                    / ".projectbrain"
                    / "brain"
                    / "transcripts"
                    / "session_extract_failure.txt"
                ).exists()
            )

    def test_codex_brain_invalid_extraction_output_falls_back_to_empty_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()

            def fake_runner(command, *, cwd):
                return (0, "Assistant: Keep the startup command as codex-brain.\n")

            with contextlib.redirect_stderr(stderr):
                return_code = codex_brain_main(
                    ["--project", tmp, "--no-ui", "--codex-command", "codex exec What is the startup command?"],
                    command_runner=fake_runner,
                    extraction_runner=lambda prompt, *, cwd: "not json",
                    session_id_factory=lambda: "session_invalid_extraction",
                )

            self.assertEqual(return_code, 0)
            self.assertIn("ProjectBrain memory persistence failed", stderr.getvalue())
            service = BrainService(BrainRepository(Path(tmp)))
            sessions = service.list_sessions()
            self.assertEqual(sessions["session_count"], 1)
            self.assertEqual(sessions["sessions"][0]["candidate_ids"], [])
            self.assertEqual(service.list_candidates()["candidate_count"], 0)

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

    def test_codex_brain_opens_existing_brain_explorer_projects_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            opened = []

            return_code = codex_brain_main(
                ["--project", tmp, "--no-extract", "--codex-command", "true"],
                command_runner=lambda command, *, cwd: 0,
                browser_opener=opened.append,
            )

            self.assertEqual(return_code, 0)
            self.assertEqual(len(opened), 1)
            self.assertIn("/ui/projects", opened[0])
            self.assertNotIn("/ui/app/projects", opened[0])
            self.assertIn("project_path=", opened[0])

    def test_open_url_uses_macos_open_command_without_shell(self):
        calls = []

        _open_url(
            "http://127.0.0.1:8000/ui/projects?project_path=%2Ftmp%2Frepo",
            platform="darwin",
            command_runner=lambda command, **kwargs: calls.append((command, kwargs)),
        )

        self.assertEqual(
            calls,
            [(["open", "http://127.0.0.1:8000/ui/projects?project_path=%2Ftmp%2Frepo"], {"check": False})],
        )

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
