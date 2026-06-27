import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures import create_payment_mini_codegraph_project  # noqa: E402
from projectbrain_runtime.bundle import TaskUnderstandingBundle  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


class TaskUnderstandingBundleTest(unittest.TestCase):
    def test_to_dict_includes_required_v1_fields(self):
        bundle = TaskUnderstandingBundle(
            bundle_id="tub_test",
            project_id="demo_project",
            task="Explain checkout flow",
            task_type="explain",
            summary="Checkout starts in CheckoutController.",
        )

        data = bundle.to_dict()

        self.assertEqual(data["bundle_type"], "task_understanding")
        self.assertEqual(data["bundle_id"], "tub_test")
        self.assertEqual(data["project_id"], "demo_project")
        self.assertEqual(data["task"], "Explain checkout flow")
        self.assertEqual(data["task_type"], "explain")
        self.assertEqual(data["summary"], "Checkout starts in CheckoutController.")
        self.assertEqual(data["relevant_files"], [])
        self.assertEqual(data["relevant_symbols"], [])
        self.assertEqual(data["entry_flows"], [])
        self.assertEqual(data["impact_hints"], [])
        self.assertEqual(data["risk_warnings"], [])
        self.assertEqual(data["human_claims"]["verified"], [])
        self.assertEqual(data["linked_evidence"]["verified"], [])
        self.assertEqual(data["test_suggestions"], [])
        self.assertEqual(data["unknowns"], [])
        self.assertEqual(data["quality_notes"], [])
        self.assertIn("generated_at", data)

    def test_runtime_build_task_understanding_bundle_uses_context_pack_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            repository = JsonProjectBrainRepository(Path(tmp) / "store")
            runtime = ProjectBrainRuntime(repository)
            runtime.import_project(
                project_id="payment_demo",
                project_path=fixture["project_path"],
                name="Payment Demo",
                experience_seed=fixture["experience_seed"],
            )

            data = runtime.build_task_understanding_bundle(
                project_id="payment_demo",
                task="Explain payment flow",
            )

            self.assertEqual(data["bundle"]["project_id"], "payment_demo")
            self.assertEqual(data["bundle"]["task"], "Explain payment flow")
            self.assertEqual(data["bundle"]["task_type"], "explain")
            self.assertIn("summary", data["bundle"])
            self.assertTrue(data["bundle"]["relevant_files"])
            self.assertTrue(Path(data["artifact_path"]).exists())

    def test_runtime_build_task_understanding_bundle_includes_approved_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            repository = JsonProjectBrainRepository(Path(tmp) / "store")
            runtime = ProjectBrainRuntime(repository)
            runtime.import_project(
                project_id="payment_demo",
                project_path=fixture["project_path"],
                name="Payment Demo",
                experience_seed=fixture["experience_seed"],
            )
            runtime.add_experience_claim(
                project_id="payment_demo",
                claim_id="exp_callback_idempotency",
                statement="Payment callback changes require idempotency verification.",
                applies_to=["payment", "callback"],
                risk_level="high",
                review_state="approved",
                claim_type="HUMAN_CONFIRMED",
                confidence=0.95,
                source=["projectbrain://tests/approved-claim"],
            )

            data = runtime.build_task_understanding_bundle(
                project_id="payment_demo",
                task="Explain payment callback flow",
            )

            verified_claims = data["bundle"]["human_claims"]["verified"]
            self.assertEqual(len(verified_claims), 1)
            self.assertEqual(verified_claims[0]["id"], "exp_callback_idempotency")
            self.assertEqual(verified_claims[0]["review_state"], "approved")
            self.assertEqual(verified_claims[0]["risk_level"], "high")


if __name__ == "__main__":
    unittest.main()
