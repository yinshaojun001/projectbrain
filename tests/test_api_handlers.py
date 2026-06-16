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
    add_claim_handler,
    archive_claim_handler,
    context_pack_handler,
    git_diff_impact_handler,
    health_response,
    impact_analysis_handler,
    import_project_handler,
    list_claims_handler,
    list_projects_handler,
    policy_inspect_handler,
    review_claim_handler,
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

    def test_policy_inspect_handler(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(tmp))
            import_project_handler(
                runtime,
                {
                    "project_id": "payment_mini_policy",
                    "project_path": str(fixture["project_path"]),
                },
            )
            policy = policy_inspect_handler(runtime, "payment_mini_policy")
            self.assertEqual(policy["project_id"], "payment_mini_policy")
            self.assertIn("policy", policy)
            self.assertIn("deny_paths", policy["policy"])

    def test_claims_lifecycle_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(tmp))
            import_project_handler(
                runtime,
                {
                    "project_id": "payment_mini_claims",
                    "project_path": str(fixture["project_path"]),
                    "experience_seed": str(fixture["experience_seed"]),
                },
            )

            initial = list_claims_handler(runtime, "payment_mini_claims")
            initial_count = initial["experience_claims"]

            add_result = add_claim_handler(
                runtime,
                "payment_mini_claims",
                {
                    "claim_id": "exp_ui_test",
                    "statement": "UI dashboard observability test claim.",
                    "applies_to": "settlement",
                    "risk_level": "medium",
                    "review_state": "pending",
                    "claim_type": "HUMAN_REVIEW_REQUIRED",
                    "confidence": 0.7,
                },
            )
            self.assertEqual(add_result["claim"]["id"], "exp_ui_test")
            self.assertEqual(add_result["experience_claims"], initial_count + 1)

            reviewed = review_claim_handler(
                runtime,
                "payment_mini_claims",
                "exp_ui_test",
                {"review_state": "approved", "risk_level": "high"},
            )
            self.assertEqual(reviewed["claim"]["review_state"], "approved")
            self.assertEqual(reviewed["claim"]["risk_level"], "high")

            archived = archive_claim_handler(
                runtime,
                "payment_mini_claims",
                "exp_ui_test",
                reason="Superseded by Phase 6 plan.",
            )
            self.assertEqual(archived["claim"]["lifecycle_state"], "archived")
            self.assertEqual(archived["claim"]["archive_reason"], "Superseded by Phase 6 plan.")

            active_only = list_claims_handler(runtime, "payment_mini_claims")
            include_archived = list_claims_handler(
                runtime, "payment_mini_claims", include_archived=True
            )
            self.assertEqual(active_only["experience_claims"], initial_count)
            self.assertEqual(include_archived["experience_claims"], initial_count + 1)

    def test_git_diff_impact_handler_rejects_bad_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(tmp))
            import_project_handler(
                runtime,
                {
                    "project_id": "payment_mini_gitdiff",
                    "project_path": str(fixture["project_path"]),
                },
            )
            with self.assertRaises(ValueError):
                git_diff_impact_handler(
                    runtime,
                    "payment_mini_gitdiff",
                    {"task": "Review diff", "selection": {"kind": "unknown"}},
                )
            with self.assertRaises(ValueError):
                git_diff_impact_handler(
                    runtime,
                    "payment_mini_gitdiff",
                    {"task": "Review diff", "selection": {"kind": "branch"}},
                )


if __name__ == "__main__":
    unittest.main()
