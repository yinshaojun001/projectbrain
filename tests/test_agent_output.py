import json
import subprocess
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
from projectbrain_cli.main import main  # noqa: E402
from projectbrain_cli.mcp_server import ProjectBrainMcpServer  # noqa: E402
from projectbrain_runtime.agent_output import format_agent_output, format_output  # noqa: E402


class ProjectBaselineAgentOutputTest(unittest.TestCase):
    def test_format_output_returns_project_baseline_agent_view(self):
        output = format_output(
            {
                "baseline": {
                    "bundle_type": "project_baseline",
                    "project_id": "payment_demo",
                    "project_summary": "支付项目基线",
                    "project_goal": "负责支付回调和结算处理。",
                    "primary_users": ["财务结算", "支付运营"],
                    "core_modules": ["结算编排模块", "支付回调模块"],
                    "key_flows": ["支付回调 -> 状态校验 -> 结算编排"],
                    "third_party_integrations": ["微信支付", "支付宝"],
                    "high_risk_areas": ["支付回调幂等处理", "结算状态机"],
                    "constraints": ["必须兼容历史账单", "不能改第三方回调协议"],
                    "validation_strategy": ["补充单元测试", "跑支付回调联调"],
                    "priority_evidence": ["支付链路告警历史"],
                    "unknowns": ["退款边界"],
                    "quality_notes": ["需人工确认"],
                }
            },
            "agent",
        )

        self.assertNotIn("baseline", output)
        self.assertEqual(output["agent_output"]["artifact_type"], "project_baseline")
        self.assertEqual(output["agent_output"]["project_id"], "payment_demo")
        self.assertEqual(output["agent_output"]["project_goal"], "负责支付回调和结算处理。")
        self.assertEqual(output["agent_output"]["primary_users"], ["财务结算", "支付运营"])
        self.assertEqual(output["agent_output"]["core_modules"], ["结算编排模块", "支付回调模块"])
        self.assertEqual(output["agent_output"]["quality_notes"], ["需人工确认"])

    def test_format_output_returns_empty_lists_for_sparse_project_baseline(self):
        output = format_output(
            {
                "baseline": {
                    "bundle_type": "project_baseline",
                    "project_id": "legacy_demo",
                    "project_goal": "兼容历史制品。",
                }
            },
            "agent",
        )

        self.assertEqual(output["agent_output"]["artifact_type"], "project_baseline")
        self.assertEqual(output["agent_output"]["project_id"], "legacy_demo")
        self.assertEqual(output["agent_output"]["primary_users"], [])
        self.assertEqual(output["agent_output"]["core_modules"], [])
        self.assertEqual(output["agent_output"]["quality_notes"], [])

class AgentOutputTest(unittest.TestCase):
    def test_cli_context_agent_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str(Path(tmp) / "store")
            _import_payment_mini(store_root, fixture, "payment_mini_agent_context")

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "context",
                    "payment_mini_agent_context",
                    "Explain settlement",
                    "--format",
                    "agent",
                ]
            )

            agent_output = output["agent_output"]
            self.assertEqual(agent_output["artifact_type"], "context_pack")
            self.assertTrue(agent_output["must_read_files"])
            self.assertIn("manual_review", agent_output)
            self.assertNotIn("context_pack", output)

    def test_cli_impact_agent_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str(Path(tmp) / "store")
            _import_payment_mini(store_root, fixture, "payment_mini_agent_impact")

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact",
                    "payment_mini_agent_impact",
                    "Change settlement contract",
                    "--changed-file",
                    "contract/src/main/java/example/payment/settlement/SettlementService.java",
                    "--format",
                    "agent",
                ]
            )

            agent_output = output["agent_output"]
            self.assertEqual(agent_output["artifact_type"], "impact_analysis")
            self.assertEqual(agent_output["review_recommendation"]["action"], "manual_review_required")
            self.assertTrue(agent_output["matched_entities"])
            self.assertNotIn("impact_analysis", output)

    def test_cli_impact_diff_agent_format_keeps_git_diff_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            store_root = str(Path(tmp) / "store")
            _import_payment_mini(store_root, fixture, "payment_mini_agent_diff")
            _change_and_stage_settlement_contract(fixture["project_path"])

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact-diff",
                    "payment_mini_agent_diff",
                    "Review staged settlement contract change",
                    "--staged",
                    "--format",
                    "agent",
                ]
            )

            agent_output = output["agent_output"]
            self.assertEqual(agent_output["artifact_type"], "impact_analysis")
            self.assertEqual(agent_output["git_diff"]["selection"], "staged")
            self.assertEqual(
                agent_output["changed_files"],
                ["contract/src/main/java/example/payment/settlement/SettlementService.java"],
            )

    def test_mcp_context_and_impact_agent_output_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
            _call_tool(
                server,
                "projectbrain_import_project",
                {
                    "project_id": "payment_mini_agent_mcp",
                    "project_path": str(fixture["project_path"]),
                    "experience_seed": str(fixture["experience_seed"]),
                    "path_prefixes": [
                        "contract/src/main/java/example/payment/settlement/",
                        "service/src/main/java/example/payment/settlement/",
                    ],
                    "kinds": ["class", "interface", "method"],
                },
            )

            context_output = _call_tool(
                server,
                "projectbrain_context_pack",
                {
                    "project_id": "payment_mini_agent_mcp",
                    "task": "Explain settlement",
                    "output_format": "agent",
                },
            )
            self.assertEqual(context_output["agent_output"]["artifact_type"], "context_pack")

            impact_output = _call_tool(
                server,
                "projectbrain_impact_analysis",
                {
                    "project_id": "payment_mini_agent_mcp",
                    "task": "Change settlement contract",
                    "changed_files": [
                        "contract/src/main/java/example/payment/settlement/SettlementService.java"
                    ],
                    "output_format": "agent",
                },
            )
            self.assertEqual(impact_output["agent_output"]["artifact_type"], "impact_analysis")

    def test_mcp_git_diff_agent_output_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
            _call_tool(
                server,
                "projectbrain_import_project",
                {
                    "project_id": "payment_mini_agent_mcp_diff",
                    "project_path": str(fixture["project_path"]),
                    "experience_seed": str(fixture["experience_seed"]),
                    "path_prefixes": [
                        "contract/src/main/java/example/payment/settlement/",
                        "service/src/main/java/example/payment/settlement/",
                    ],
                    "kinds": ["class", "interface", "method"],
                },
            )
            _change_and_stage_settlement_contract(fixture["project_path"])

            output = _call_tool(
                server,
                "projectbrain_review_git_diff",
                {
                    "project_id": "payment_mini_agent_mcp_diff",
                    "task": "Review staged settlement contract change",
                    "staged": True,
                    "output_format": "agent",
                },
            )

            self.assertEqual(output["agent_output"]["artifact_type"], "impact_analysis")
            self.assertEqual(output["agent_output"]["git_diff"]["selection"], "staged")

    def test_format_agent_output_rejects_source_body_like_sections(self):
        output = format_agent_output(
            {
                "context_pack": {
                    "project_id": "demo",
                    "task": "Explain",
                    "summary": "Summary",
                    "sections": [],
                    "recommended_files": [{"file": "src/App.java", "reason": "Read it", "body": "private"}],
                    "recommended_symbols": [],
                    "recommended_tests": [],
                    "warnings": [],
                    "omissions": [],
                }
            }
        )

        self.assertEqual(output["must_read_files"], [{"file": "src/App.java", "reason": "Read it"}])

    def test_runtime_policy_filters_denied_paths_and_caps_read_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            (fixture["project_path"] / ".projectbrain-policy.json").write_text(
                json.dumps(
                    {
                        "deny_paths": ["service/src/test/**"],
                        "max_items_per_section": 1,
                        "max_recommended_files": 1,
                        "max_recommended_tests": 0,
                        "include_source_snippets": False,
                    }
                ),
                encoding="utf-8",
            )
            store_root = str(Path(tmp) / "store")
            _import_payment_mini(store_root, fixture, "payment_mini_policy")

            context = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "context",
                    "payment_mini_policy",
                    "Explain settlement",
                    "--max-items-per-section",
                    "5",
                ]
            )["context_pack"]
            impact = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact",
                    "payment_mini_policy",
                    "Change settlement contract",
                    "--changed-file",
                    "contract/src/main/java/example/payment/settlement/SettlementService.java",
                    "--max-items-per-section",
                    "5",
                ]
            )["impact_analysis"]

            self.assertLessEqual(len(context["recommended_files"]), 1)
            self.assertEqual(context["recommended_tests"], [])
            self.assertEqual(impact["recommended_tests"], [])
            self.assertFalse(_contains_path(context, "service/src/test/"))
            self.assertFalse(_contains_path(impact, "service/src/test/"))

    def test_cli_policy_inspect_reports_loaded_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            policy_path = fixture["project_path"] / ".projectbrain-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "deny_paths": ["service/src/test/**"],
                        "max_recommended_tests": 0,
                    }
                ),
                encoding="utf-8",
            )
            store_root = str(Path(tmp) / "store")
            _import_payment_mini(store_root, fixture, "payment_mini_policy_inspect")

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "policy",
                    "inspect",
                    "payment_mini_policy_inspect",
                ]
            )

            self.assertEqual(output["project_id"], "payment_mini_policy_inspect")
            self.assertTrue(output["policy_found"])
            self.assertEqual(output["source_path"], str(policy_path))
            self.assertEqual(output["summary"]["deny_path_count"], 1)
            self.assertTrue(output["summary"]["has_output_caps"])


def _import_payment_mini(store_root: str, fixture: dict[str, Path], project_id: str) -> None:
    _run_cli(
        [
            "--store-root",
            store_root,
            "import",
            str(fixture["project_path"]),
            "--id",
            project_id,
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


def _init_git_repo(path: Path) -> None:
    _run_git(path, "init")
    _run_git(path, "config", "user.email", "projectbrain@example.com")
    _run_git(path, "config", "user.name", "ProjectBrain Test")
    _run_git(path, "add", ".")
    _run_git(path, "commit", "-m", "initial")


def _change_and_stage_settlement_contract(path: Path) -> None:
    target = path / "contract/src/main/java/example/payment/settlement/SettlementService.java"
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "SettlementResult requestSettlement(SettlementRequest request);",
            "SettlementResult requestSettlement(SettlementRequest request, String requestId);",
        ),
        encoding="utf-8",
    )
    _run_git(path, "add", "contract/src/main/java/example/payment/settlement/SettlementService.java")


def _run_git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)


def _run_cli(argv: list[str]) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        result = main(argv)
    if result != 0:
        raise AssertionError(f"CLI returned {result}")
    return json.loads(output.getvalue())


def _call_tool(server: ProjectBrainMcpServer, name: str, arguments: dict) -> dict:
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    if response["result"].get("isError"):
        raise AssertionError(response["result"]["content"][0]["text"])
    return json.loads(response["result"]["content"][0]["text"])


def _contains_path(value: object, path_fragment: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_path(item, path_fragment) for item in value.values())
    if isinstance(value, list):
        return any(_contains_path(item, path_fragment) for item in value)
    return isinstance(value, str) and path_fragment in value


if __name__ == "__main__":
    unittest.main()
