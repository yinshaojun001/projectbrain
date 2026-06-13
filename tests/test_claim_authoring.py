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
from projectbrain_cli.main import main  # noqa: E402
from projectbrain_cli.mcp_server import ProjectBrainMcpServer  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


class ClaimAuthoringTest(unittest.TestCase):
    def test_runtime_add_experience_claim_and_context_matches_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(str(Path(tmp) / "store")))
            _import_payment_mini_runtime(runtime, fixture, "payment_mini_claim_runtime")

            output = runtime.add_experience_claim(
                project_id="payment_mini_claim_runtime",
                statement="Settlement contract changes require compatibility review.",
                applies_to=["SettlementService"],
                risk_level="high",
                review_state="approved",
                claim_type="HUMAN_CONFIRMED",
                source="demo://claim",
                claim_id="exp_runtime_settlement_contract",
            )
            context = runtime.build_context_pack(
                project_id="payment_mini_claim_runtime",
                task="Explain settlement contract",
            )["context_pack"]

            self.assertEqual(output["claim"]["id"], "exp_runtime_settlement_contract")
            self.assertEqual(output["experience_claims"], 2)
            claim_sections = [section for section in context["sections"] if section["type"] == "experience_claims"]
            statements = [item["statement"] for section in claim_sections for item in section["items"]]
            self.assertIn("Settlement contract changes require compatibility review.", statements)

    def test_runtime_add_experience_claim_validates_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(str(Path(tmp) / "store")))
            _import_payment_mini_runtime(runtime, fixture, "payment_mini_claim_validation")

            with self.assertRaisesRegex(ValueError, "risk_level must be one of"):
                runtime.add_experience_claim(
                    project_id="payment_mini_claim_validation",
                    statement="Invalid risk claim.",
                    risk_level="severe",
                )

            with self.assertRaisesRegex(ValueError, "confidence must be between 0 and 1"):
                runtime.add_experience_claim(
                    project_id="payment_mini_claim_validation",
                    statement="Invalid confidence claim.",
                    confidence=1.2,
                )

    def test_cli_claim_add_persists_claim_for_impact(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str(Path(tmp) / "store")
            _import_payment_mini_cli(store_root, fixture, "payment_mini_claim_cli")

            claim_output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "claim",
                    "add",
                    "payment_mini_claim_cli",
                    "--id",
                    "exp_cli_settlement_contract",
                    "--statement",
                    "Settlement interface compatibility must be reviewed.",
                    "--applies-to",
                    "SettlementService",
                    "--risk",
                    "high",
                    "--review-state",
                    "approved",
                    "--claim-type",
                    "HUMAN_CONFIRMED",
                    "--source",
                    "demo://cli",
                ]
            )
            impact = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact",
                    "payment_mini_claim_cli",
                    "Change settlement contract",
                    "--changed-file",
                    "contract/src/main/java/example/payment/settlement/SettlementService.java",
                ]
            )

            self.assertEqual(claim_output["claim"]["id"], "exp_cli_settlement_contract")
            self.assertEqual(
                impact["impact_analysis"]["review_recommendation"]["risk_level"],
                "critical",
            )

    def test_mcp_add_experience_claim_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
            _call_tool(
                server,
                "projectbrain_import_project",
                {
                    "project_id": "payment_mini_claim_mcp",
                    "project_path": str(fixture["project_path"]),
                    "experience_seed": str(fixture["experience_seed"]),
                    "path_prefixes": [
                        "contract/src/main/java/example/payment/settlement/",
                        "service/src/main/java/example/payment/settlement/",
                    ],
                    "kinds": ["class", "interface", "method"],
                },
            )

            output = _call_tool(
                server,
                "projectbrain_add_experience_claim",
                {
                    "project_id": "payment_mini_claim_mcp",
                    "claim_id": "exp_mcp_settlement_contract",
                    "statement": "Settlement service claims require manual review.",
                    "applies_to": ["SettlementService"],
                    "risk_level": "high",
                    "review_state": "approved",
                    "claim_type": "HUMAN_CONFIRMED",
                    "source": ["demo://mcp"],
                },
            )
            context = _call_tool(
                server,
                "projectbrain_context_pack",
                {
                    "project_id": "payment_mini_claim_mcp",
                    "task": "Explain settlement",
                    "output_format": "agent",
                },
            )

            self.assertEqual(output["claim"]["id"], "exp_mcp_settlement_contract")
            self.assertEqual(output["experience_claims"], 2)
            risk_messages = context["agent_output"]["risk_warnings"]
            self.assertTrue(any("HUMAN_CONFIRMED" in item["message"] for item in risk_messages))


def _import_payment_mini_runtime(runtime: ProjectBrainRuntime, fixture: dict[str, Path], project_id: str) -> None:
    runtime.import_project(
        project_id=project_id,
        project_path=fixture["project_path"],
        experience_seed=fixture["experience_seed"],
    )


def _import_payment_mini_cli(store_root: str, fixture: dict[str, Path], project_id: str) -> None:
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


if __name__ == "__main__":
    unittest.main()
