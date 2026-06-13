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
from projectbrain_runtime.git_diff import GitDiffSelection, changed_files_for_selection  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


class GitDiffImpactTest(unittest.TestCase):
    def test_changed_files_for_staged_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            _change_and_stage_settlement_contract(fixture["project_path"])

            changed_files = changed_files_for_selection(fixture["project_path"], GitDiffSelection(staged=True))

            self.assertEqual(
                changed_files,
                ["contract/src/main/java/example/payment/settlement/SettlementService.java"],
            )

    def test_changed_files_for_explicit_ref_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            base_ref = _git_revision(fixture["project_path"], "HEAD")
            _change_and_stage_settlement_contract(fixture["project_path"])
            _run_git(fixture["project_path"], "commit", "-m", "change settlement contract")

            changed_files = changed_files_for_selection(
                fixture["project_path"],
                GitDiffSelection(from_ref=base_ref, to_ref="HEAD"),
            )

            self.assertEqual(
                changed_files,
                ["contract/src/main/java/example/payment/settlement/SettlementService.java"],
            )

    def test_git_diff_selection_rejects_multiple_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])

            with self.assertRaisesRegex(ValueError, "Choose only one Git diff selection mode"):
                changed_files_for_selection(
                    fixture["project_path"],
                    GitDiffSelection(staged=True, from_ref="main", to_ref="HEAD"),
                )

    def test_runtime_analyzes_staged_git_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            store_root = str(Path(tmp) / "store")
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(store_root))
            _import_payment_mini(runtime, fixture)
            _change_and_stage_settlement_contract(fixture["project_path"])

            output = runtime.analyze_git_diff_impact(
                project_id="payment_mini_git_test",
                task="Review staged settlement contract change",
                selection=GitDiffSelection(staged=True),
            )

            self.assertEqual(output["git_diff"]["selection"], "staged")
            self.assertEqual(
                output["git_diff"]["changed_files"],
                ["contract/src/main/java/example/payment/settlement/SettlementService.java"],
            )
            self.assertEqual(
                output["impact_analysis"]["review_recommendation"]["action"],
                "manual_review_required",
            )

    def test_cli_impact_diff_uses_imported_project_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            store_root = str(Path(tmp) / "store")
            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_mini_git_cli_test",
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
            _change_and_stage_settlement_contract(fixture["project_path"])

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact-diff",
                    "payment_mini_git_cli_test",
                    "Review staged settlement contract change",
                    "--staged",
                ]
            )

            self.assertEqual(output["git_diff"]["selection"], "staged")
            self.assertTrue(output["impact_analysis"]["recommended_tests"])

    def test_cli_impact_diff_supports_explicit_ref_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            base_ref = _git_revision(fixture["project_path"], "HEAD")
            store_root = str(Path(tmp) / "store")
            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_mini_git_range_cli_test",
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
            _change_and_stage_settlement_contract(fixture["project_path"])
            _run_git(fixture["project_path"], "commit", "-m", "change settlement contract")

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "impact-diff",
                    "payment_mini_git_range_cli_test",
                    "Review branch settlement contract change",
                    "--from",
                    base_ref,
                    "--to",
                    "HEAD",
                ]
            )

            self.assertEqual(output["git_diff"]["selection"], f"{base_ref}..HEAD")
            self.assertEqual(
                output["git_diff"]["changed_files"],
                ["contract/src/main/java/example/payment/settlement/SettlementService.java"],
            )

    def test_mcp_review_git_diff_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            _init_git_repo(fixture["project_path"])
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
            _call_tool(
                server,
                "projectbrain_import_project",
                {
                    "project_id": "payment_mini_git_mcp_test",
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
                    "project_id": "payment_mini_git_mcp_test",
                    "task": "Review staged settlement contract change",
                    "staged": True,
                },
            )

            self.assertEqual(output["git_diff"]["selection"], "staged")
            self.assertEqual(
                output["impact_analysis"]["review_recommendation"]["action"],
                "manual_review_required",
            )


def _import_payment_mini(runtime: ProjectBrainRuntime, fixture: dict[str, Path]) -> None:
    runtime.import_project(
        project_id="payment_mini_git_test",
        project_path=fixture["project_path"],
        experience_seed=fixture["experience_seed"],
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


def _git_revision(path: Path, ref: str) -> str:
    result = subprocess.run(["git", "-C", str(path), "rev-parse", ref], check=True, capture_output=True, text=True)
    return result.stdout.strip()


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
