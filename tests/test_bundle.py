import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.bundle import TaskUnderstandingBundle  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
