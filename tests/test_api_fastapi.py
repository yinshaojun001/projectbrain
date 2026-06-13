import os
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

try:
    from fastapi.testclient import TestClient  # noqa: E402
    from projectbrain_api.main import app  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - tested in .venv with api extra installed.
    TestClient = None
    app = None


class FastApiTest(unittest.TestCase):
    def test_http_routes_run_against_runtime(self):
        if TestClient is None or app is None:
            self.skipTest("FastAPI is not installed in this interpreter")
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            previous = os.environ.get("PROJECTBRAIN_STORE_ROOT")
            os.environ["PROJECTBRAIN_STORE_ROOT"] = tmp
            try:
                client = TestClient(app)
                self.assertEqual(client.get("/health").json(), {"status": "ok"})

                import_response = client.post(
                    "/api/v1/projects/import",
                    json={
                        "project_id": "payment_mini_http_test",
                        "project_path": str(fixture["project_path"]),
                        "name": "Payment Mini HTTP Test",
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
                self.assertEqual(import_response.status_code, 200)
                self.assertEqual(import_response.json()["project"]["project_id"], "payment_mini_http_test")

                projects_response = client.get("/api/v1/projects")
                self.assertEqual(projects_response.status_code, 200)
                self.assertEqual(len(projects_response.json()["projects"]), 1)

                context_response = client.post(
                    "/api/v1/projects/payment_mini_http_test/context-pack",
                    json={"task": "Explain settlement", "max_items_per_section": 5},
                )
                self.assertEqual(context_response.status_code, 200)
                self.assertIn("context_pack", context_response.json())

                impact_response = client.post(
                    "/api/v1/projects/payment_mini_http_test/impact-analysis",
                    json={
                        "task": "Change settlement contract",
                        "changed_files": [
                            "contract/src/main/java/example/payment/settlement/SettlementService.java"
                        ],
                        "changed_symbols": [],
                        "max_items_per_section": 5,
                    },
                )
                self.assertEqual(impact_response.status_code, 200)
                self.assertEqual(
                    impact_response.json()["impact_analysis"]["review_recommendation"]["action"],
                    "manual_review_required",
                )
            finally:
                if previous is None:
                    os.environ.pop("PROJECTBRAIN_STORE_ROOT", None)
                else:
                    os.environ["PROJECTBRAIN_STORE_ROOT"] = previous


if __name__ == "__main__":
    unittest.main()
