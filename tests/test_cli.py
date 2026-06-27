import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures import create_payment_mini_codegraph_project  # noqa: E402
from projectbrain_cli import main as cli_main  # noqa: E402
from projectbrain_cli.main import main  # noqa: E402


class ProjectBrainCliTest(unittest.TestCase):
    def test_doctor_reports_ok(self):
        output = _run_cli(["doctor"])

        self.assertEqual(output["status"], "ok")
        self.assertIn("python", output)

    def test_facts_context_from_export_json(self):
        output = _run_cli(
            [
                "facts",
                "context",
                "--export-json",
                str(ROOT / "examples/payment-mini/projectbrain-codegraph-export.json"),
                "--experience-seed",
                str(ROOT / "examples/payment-mini/experience-seed.md"),
                "--task",
                "Explain settlement",
            ]
        )

        self.assertEqual(output["project_id"], "payment_mini")
        self.assertTrue(output["recommended_files"])

    def test_runtime_import_context_and_impact(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            import_output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_mini_cli_test",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                    "--path-prefix",
                    "contract/src/main/java/example/payment/settlement/",
                    "--path-prefix",
                    "service/src/main/java/example/payment/settlement/",
                    "--kind",
                    "class",
                    "--kind",
                    "interface",
                    "--kind",
                    "method",
                ]
            )
            self.assertEqual(import_output["project"]["project_id"], "payment_mini_cli_test")

            context_output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "context",
                    "payment_mini_cli_test",
                    "Explain settlement",
                ]
            )
            self.assertIn("context_pack", context_output)

            impact_output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact",
                    "payment_mini_cli_test",
                    "Change settlement contract",
                    "--changed-file",
                    "contract/src/main/java/example/payment/settlement/SettlementService.java",
                ]
            )
            self.assertEqual(
                impact_output["impact_analysis"]["review_recommendation"]["action"],
                "manual_review_required",
            )

    def test_understand_returns_task_understanding_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_understand_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "understand",
                    "payment_understand_cli",
                    "Explain settlement flow",
                ]
            )

            self.assertEqual(output["bundle"]["bundle_type"], "task_understanding")
            self.assertEqual(output["bundle"]["project_id"], "payment_understand_cli")
            self.assertEqual(output["bundle"]["task"], "Explain settlement flow")
            self.assertEqual(output["bundle"]["task_type"], "explain")
            self.assertIn("summary", output["bundle"])

    def test_project_intake_creates_session_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_intake_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_intake_cli",
                ]
            )

            self.assertEqual(output["intake"]["intake_type"], "project")
            self.assertEqual(output["intake"]["project_id"], "payment_intake_cli")
            self.assertEqual(output["intake"]["status"], "asking")
            self.assertEqual(output["intake"]["next_question"]["slot_key"], "project_goal")
            self.assertIn("最核心是干什么的", output["intake"]["next_question"]["question"])
            self.assertTrue(output["artifact_path"].endswith(".json"))

    def test_project_intake_first_answer_advances_to_second_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_intake_answer_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            started = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_intake_answer_cli",
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_answer_cli",
                    started["intake"]["session_id"],
                    "--answer",
                    "这个项目主要负责支付回调和结算处理。",
                ]
            )

            self.assertEqual(output["intake"]["status"], "asking")
            self.assertEqual(
                output["intake"]["captured_fields"]["project_goal"],
                "这个项目主要负责支付回调和结算处理。",
            )
            self.assertEqual(output["intake"]["next_question"]["slot_key"], "primary_users")
            self.assertIn("主要服务谁", output["intake"]["next_question"]["question"])
            self.assertEqual(output["intake"]["baseline_draft"]["bundle_type"], "project_baseline")
            self.assertEqual(
                output["intake"]["baseline_draft"]["project_summary"],
                "这个项目主要负责支付回调和结算处理。",
            )

    def test_project_intake_second_answer_advances_to_core_modules_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_intake_second_answer_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            started = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_intake_second_answer_cli",
                ]
            )

            first_answer = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_second_answer_cli",
                    started["intake"]["session_id"],
                    "--answer",
                    "这个项目主要负责支付回调和结算处理。",
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_second_answer_cli",
                    first_answer["intake"]["session_id"],
                    "--answer",
                    "主要服务财务结算和支付运营同学。",
                ]
            )

            self.assertEqual(output["intake"]["status"], "asking")
            self.assertEqual(output["intake"]["next_question"]["slot_key"], "core_modules")
            self.assertIn("核心模块", output["intake"]["next_question"]["question"])
            self.assertEqual(
                output["intake"]["captured_fields"]["primary_users"],
                "主要服务财务结算和支付运营同学。",
            )
            self.assertEqual(
                output["intake"]["baseline_draft"]["primary_users"],
                ["主要服务财务结算和支付运营同学。"],
            )

    def test_project_intake_third_answer_advances_to_key_flows_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_intake_third_answer_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            started = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_intake_third_answer_cli",
                ]
            )

            first_answer = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_third_answer_cli",
                    started["intake"]["session_id"],
                    "--answer",
                    "这个项目主要负责支付回调和结算处理。",
                ]
            )

            second_answer = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_third_answer_cli",
                    first_answer["intake"]["session_id"],
                    "--answer",
                    "主要服务财务结算和支付运营同学。",
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_third_answer_cli",
                    second_answer["intake"]["session_id"],
                    "--answer",
                    "结算编排模块、支付回调模块、对账模块。",
                ]
            )

            self.assertEqual(output["intake"]["status"], "asking")
            self.assertEqual(output["intake"]["next_question"]["slot_key"], "key_flows")
            self.assertIn("关键流程", output["intake"]["next_question"]["question"])
            self.assertEqual(
                output["intake"]["captured_fields"]["core_modules"],
                "结算编排模块、支付回调模块、对账模块。",
            )
            self.assertEqual(
                output["intake"]["baseline_draft"]["core_modules"],
                ["结算编排模块", "支付回调模块", "对账模块"],
            )

    def test_project_intake_fourth_answer_completes_baseline_key_flows(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_intake_fourth_answer_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            started = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_intake_fourth_answer_cli",
                ]
            )

            first_answer = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_fourth_answer_cli",
                    started["intake"]["session_id"],
                    "--answer",
                    "这个项目主要负责支付回调和结算处理。",
                ]
            )

            second_answer = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_fourth_answer_cli",
                    first_answer["intake"]["session_id"],
                    "--answer",
                    "主要服务财务结算和支付运营同学。",
                ]
            )

            third_answer = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_fourth_answer_cli",
                    second_answer["intake"]["session_id"],
                    "--answer",
                    "结算编排模块、支付回调模块、对账模块。",
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_intake_fourth_answer_cli",
                    third_answer["intake"]["session_id"],
                    "--answer",
                    "支付回调 -> 状态校验 -> 结算编排 -> 对账出账。",
                ]
            )

            self.assertEqual(output["intake"]["status"], "answered")
            self.assertIsNone(output["intake"]["next_question"])
            self.assertEqual(
                output["intake"]["captured_fields"]["key_flows"],
                "支付回调 -> 状态校验 -> 结算编排 -> 对账出账。",
            )
            self.assertEqual(
                output["intake"]["baseline_draft"]["key_flows"],
                ["支付回调 -> 状态校验 -> 结算编排 -> 对账出账"],
            )

    def test_setup_indexes_imports_smoke_tests_and_prints_mcp_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            project_path = Path(fixture["project_path"]).resolve()
            store_root = str((Path(tmp) / "store").resolve())
            calls = []

            def fake_run(command, *, cwd=None):
                calls.append((command, cwd))
                return cli_main.CommandResult(returncode=0, stdout="", stderr="")

            def fake_agent_detector(_command):
                return None

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "setup",
                    str(project_path),
                    "--id",
                    "payment_mini_setup",
                    "--task",
                    "Explain settlement",
                    "--mcp-command",
                    sys.argv[0],
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                    "--path-prefix",
                    "contract/src/main/java/example/payment/settlement/",
                    "--kind",
                    "class",
                    "--kind",
                    "method",
                ],
                command_runner=fake_run,
                agent_detector=fake_agent_detector,
            )

            self.assertEqual(
                calls,
                [
                    (["codegraph", "init", str(project_path)], project_path),
                    (["codegraph", "index", str(project_path)], project_path),
                ],
            )
            self.assertEqual(output["status"], "ok")
            self.assertEqual(output["project"]["project_id"], "payment_mini_setup")
            self.assertEqual(output["smoke_test"]["artifact_type"], "context_pack")
            self.assertEqual(output["mcp_config"]["mcpServers"]["projectbrain"]["command"], sys.argv[0])
            self.assertEqual(
                output["mcp_config"]["mcpServers"]["projectbrain"]["args"],
                ["--store-root", store_root, "mcp", "serve"],
            )

    def test_setup_can_install_codex_mcp_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            project_path = Path(fixture["project_path"]).resolve()
            store_root = str((Path(tmp) / "store").resolve())
            calls = []

            def fake_run(command, *, cwd=None):
                calls.append((command, cwd))
                return cli_main.CommandResult(returncode=0, stdout="", stderr="")

            def fake_agent_detector(command):
                return {
                    "codex": "/opt/homebrew/bin/codex",
                    "claude": "/Users/a58/.local/bin/claude",
                    "cursor": "/usr/local/bin/cursor",
                    "trae": "/usr/local/bin/trae",
                }.get(command)

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "setup",
                    str(project_path),
                    "--id",
                    "payment_mini_setup_agents",
                    "--skip-codegraph",
                    "--agent",
                    "codex",
                    "--mcp-command",
                    "/opt/homebrew/bin/projectbrain",
                ],
                command_runner=fake_run,
                agent_detector=fake_agent_detector,
            )

            self.assertEqual(
                calls,
                [
                    (
                        [
                            "/opt/homebrew/bin/codex",
                            "mcp",
                            "add",
                            "projectbrain",
                            "--",
                            "/opt/homebrew/bin/projectbrain",
                            "--store-root",
                            store_root,
                            "mcp",
                            "serve",
                        ],
                        None,
                    )
                ],
            )
            self.assertEqual(output["agents"]["requested"], ["codex"])
            self.assertEqual(output["agents"]["install_results"][0]["agent"], "codex")
            self.assertEqual(output["agents"]["install_results"][0]["status"], "installed")
            detected = {agent["agent"]: agent for agent in output["agents"]["detected"]}
            self.assertTrue(detected["codex"]["installed"])
            self.assertEqual(detected["cursor"]["status"], "auto_install_available")

    def test_setup_can_install_claude_cursor_and_trae_mcp_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            project_path = Path(fixture["project_path"]).resolve()
            store_root = str((Path(tmp) / "store").resolve())
            calls = []

            def fake_run(command, *, cwd=None):
                calls.append((command, cwd))
                return cli_main.CommandResult(returncode=0, stdout="", stderr="")

            def fake_agent_detector(command):
                return {
                    "claude": "/Users/a58/.local/bin/claude",
                    "cursor": "/usr/local/bin/cursor",
                    "trae": "/usr/local/bin/trae",
                }.get(command)

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "setup",
                    str(project_path),
                    "--id",
                    "payment_mini_setup_more_agents",
                    "--skip-codegraph",
                    "--agent",
                    "claude",
                    "--agent",
                    "cursor",
                    "--agent",
                    "trae",
                    "--mcp-command",
                    "/opt/homebrew/bin/projectbrain",
                ],
                command_runner=fake_run,
                agent_detector=fake_agent_detector,
            )

            mcp_json = json.dumps(
                {
                    "name": "projectbrain",
                    "command": "/opt/homebrew/bin/projectbrain",
                    "args": ["--store-root", store_root, "mcp", "serve"],
                },
                ensure_ascii=False,
            )
            self.assertEqual(
                calls,
                [
                    (
                        [
                            "/Users/a58/.local/bin/claude",
                            "mcp",
                            "add",
                            "projectbrain",
                            "--",
                            "/opt/homebrew/bin/projectbrain",
                            "--store-root",
                            store_root,
                            "mcp",
                            "serve",
                        ],
                        None,
                    ),
                    (["/usr/local/bin/cursor", "--add-mcp", mcp_json], None),
                    (["/usr/local/bin/trae", "--add-mcp", mcp_json], None),
                ],
            )
            self.assertEqual(output["agents"]["requested"], ["claude", "cursor", "trae"])
            self.assertEqual([result["status"] for result in output["agents"]["install_results"]], ["installed", "installed", "installed"])

    def test_setup_prompts_for_agents_when_not_provided(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            project_path = Path(fixture["project_path"]).resolve()
            store_root = str((Path(tmp) / "store").resolve())
            calls = []
            prompts = []

            def fake_run(command, *, cwd=None):
                calls.append((command, cwd))
                return cli_main.CommandResult(returncode=0, stdout="", stderr="")

            def fake_agent_detector(command):
                return {
                    "codex": "/opt/homebrew/bin/codex",
                    "claude": "/Users/a58/.local/bin/claude",
                }.get(command)

            def fake_input(prompt):
                prompts.append(prompt)
                return "1"

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "setup",
                    str(project_path),
                    "--id",
                    "payment_mini_setup_prompt",
                    "--skip-codegraph",
                    "--mcp-command",
                    "/opt/homebrew/bin/projectbrain",
                ],
                command_runner=fake_run,
                agent_detector=fake_agent_detector,
                input_reader=fake_input,
            )

            self.assertTrue(prompts)
            self.assertEqual(output["agents"]["requested"], ["codex"])
            self.assertEqual(output["agents"]["install_results"][0]["status"], "installed")


def _run_cli(argv: list[str], **kwargs) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        result = main(argv, **kwargs)
    if result != 0:
        raise AssertionError(f"CLI returned {result}")
    return json.loads(output.getvalue())


if __name__ == "__main__":
    unittest.main()
