import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures import create_payment_mini_codegraph_project  # noqa: E402
from projectbrain_api.handlers import (  # noqa: E402
    context_pack_handler,
    health_response,
    impact_analysis_handler,
    import_project_handler,
    list_projects_handler,
)
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


class ApiHandlersTest(unittest.TestCase):
    def test_runtime_handlers_work_without_fastapi(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(tmp))

            self.assertEqual(health_response(), {"status": "ok"})
            import_result = import_project_handler(
                runtime,
                {
                    "project_id": "payment_mini_api_test",
                    "project_path": str(fixture["project_path"]),
                    "name": "Payment Mini API Test",
                    "experience_seed": str(fixture["experience_seed"]),
                    "path_prefixes": [
                        "contract/src/main/java/example/payment/settlement/",
                        "service/src/main/java/example/payment/settlement/",
                    ],
                    "kinds": ["class", "interface", "method"],
                    "node_limit": 50,
                    "edge_limit": 80,
                },
            )
            self.assertEqual(import_result["project"]["project_id"], "payment_mini_api_test")
            self.assertEqual(len(list_projects_handler(runtime)["projects"]), 1)

            context_result = context_pack_handler(
                runtime,
                "payment_mini_api_test",
                {"task": "Explain settlement", "max_items_per_section": 5},
            )
            self.assertIn("context_pack", context_result)

            impact_result = impact_analysis_handler(
                runtime,
                "payment_mini_api_test",
                {
                    "task": "Change settlement contract",
                    "changed_files": [
                        "contract/src/main/java/example/payment/settlement/SettlementService.java"
                    ],
                    "changed_symbols": [],
                    "max_items_per_section": 5,
                },
            )
            self.assertEqual(impact_result["impact_analysis"]["review_recommendation"]["action"], "manual_review_required")


if __name__ == "__main__":
    unittest.main()
