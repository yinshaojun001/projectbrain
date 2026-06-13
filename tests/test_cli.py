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
            store_root = str(Path(tmp) / "store")

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


def _run_cli(argv: list[str]) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        result = main(argv)
    if result != 0:
        raise AssertionError(f"CLI returned {result}")
    return json.loads(output.getvalue())


if __name__ == "__main__":
    unittest.main()
