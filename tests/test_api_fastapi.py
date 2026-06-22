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
from projectbrain_runtime.brain.models import KnowledgeUnit  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402
from projectbrain_runtime.models import ProjectRecord  # noqa: E402

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

                policy_response = client.get(
                    "/api/v1/projects/payment_mini_http_test/policy"
                )
                self.assertEqual(policy_response.status_code, 200)
                self.assertEqual(
                    policy_response.json()["project_id"], "payment_mini_http_test"
                )

                add_claim_response = client.post(
                    "/api/v1/projects/payment_mini_http_test/claims",
                    json={
                        "claim_id": "exp_http_test",
                        "statement": "HTTP claim added via UI API.",
                        "applies_to": "settlement",
                        "risk_level": "medium",
                        "review_state": "pending",
                    },
                )
                self.assertEqual(add_claim_response.status_code, 200)
                self.assertEqual(
                    add_claim_response.json()["claim"]["id"], "exp_http_test"
                )

                review_response = client.patch(
                    "/api/v1/projects/payment_mini_http_test/claims/exp_http_test",
                    json={"review_state": "approved"},
                )
                self.assertEqual(review_response.status_code, 200)
                self.assertEqual(
                    review_response.json()["claim"]["review_state"], "approved"
                )

                list_response = client.get(
                    "/api/v1/projects/payment_mini_http_test/claims"
                )
                self.assertEqual(list_response.status_code, 200)
                claim_ids = [c["id"] for c in list_response.json()["claims"]]
                self.assertIn("exp_http_test", claim_ids)

                archive_response = client.delete(
                    "/api/v1/projects/payment_mini_http_test/claims/exp_http_test",
                    params={"reason": "Cleanup after smoke test."},
                )
                self.assertEqual(archive_response.status_code, 200)
                self.assertEqual(
                    archive_response.json()["claim"]["lifecycle_state"], "archived"
                )

                active_after_archive = client.get(
                    "/api/v1/projects/payment_mini_http_test/claims"
                ).json()
                with_archived = client.get(
                    "/api/v1/projects/payment_mini_http_test/claims",
                    params={"include_archived": "true"},
                ).json()
                self.assertNotIn(
                    "exp_http_test",
                    [c["id"] for c in active_after_archive["claims"]],
                )
                self.assertIn(
                    "exp_http_test",
                    [c["id"] for c in with_archived["claims"]],
                )

                bad_git_diff = client.post(
                    "/api/v1/projects/payment_mini_http_test/impact-analysis/git-diff",
                    json={
                        "task": "Review diff",
                        "selection": {"kind": "unknown"},
                    },
                )
                self.assertEqual(bad_git_diff.status_code, 400)
            finally:
                if previous is None:
                    os.environ.pop("PROJECTBRAIN_STORE_ROOT", None)
                else:
                    os.environ["PROJECTBRAIN_STORE_ROOT"] = previous



    def test_brain_routes_exercise_knowledge_summary_and_candidates(self):
        if TestClient is None or app is None:
            self.skipTest("FastAPI is not installed in this interpreter")
        with tempfile.TemporaryDirectory() as tmp:
            store_root = Path(tmp) / "store"
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            runtime = ProjectBrainRuntime(JsonProjectBrainRepository(store_root))
            runtime.repository.save_project(ProjectRecord(
                project_id="payment_brain_http_test",
                name="Payment Brain HTTP Test",
                source_path=str(project_path),
                codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
            ))

            previous = os.environ.get("PROJECTBRAIN_STORE_ROOT")
            os.environ["PROJECTBRAIN_STORE_ROOT"] = str(store_root)
            try:
                client = TestClient(app)

                constraint_response = client.post(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge",
                    json={
                        "type": "constraint",
                        "statement": "Refund API must preserve settlement ordering.",
                        "tags": ["refund"],
                    },
                )
                self.assertEqual(constraint_response.status_code, 200)
                constraint = constraint_response.json()["knowledge_unit"]

                gotcha_response = client.post(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge",
                    json={
                        "type": "gotcha",
                        "statement": "Refund API has a gotcha around retry headers.",
                        "tags": ["refund"],
                    },
                )
                self.assertEqual(gotcha_response.status_code, 200)

                search_response = client.get(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge",
                    params={"q": "refund", "type": "constraint"},
                )
                self.assertEqual(search_response.status_code, 200)
                self.assertEqual(
                    [match["id"] for match in search_response.json()["matches"]],
                    [constraint["id"]],
                )

                brain_repo = runtime.brain_for_project("payment_brain_http_test").repository
                brain_repo.save_knowledge_unit(KnowledgeUnit(
                    id="ku_stale_refund_route",
                    type="workflow",
                    title="Stale refund workflow",
                    statement="Refund stale route workflow.",
                    tags=["refund"],
                    staleness={"state": "stale", "reason": "old route test"},
                ))
                stale_response = client.get(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge",
                    params={"staleness": "stale"},
                )
                self.assertEqual(stale_response.status_code, 200)
                self.assertEqual(
                    [unit["id"] for unit in stale_response.json()["knowledge_units"]],
                    ["ku_stale_refund_route"],
                )

                archived_response = client.post(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge",
                    json={
                        "type": "risk",
                        "statement": "Refund archived route risk.",
                        "tags": ["refund"],
                        "review_state": "archived",
                    },
                )
                self.assertEqual(archived_response.status_code, 200)
                archived_id = archived_response.json()["knowledge_unit"]["id"]
                default_ids = [unit["id"] for unit in client.get(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge"
                ).json()["knowledge_units"]]
                archived_ids = [unit["id"] for unit in client.get(
                    "/api/v1/projects/payment_brain_http_test/brain/knowledge",
                    params={"include_archived": "true"},
                ).json()["knowledge_units"]]
                self.assertNotIn(archived_id, default_ids)
                self.assertIn(archived_id, archived_ids)

                summary_response = client.get(
                    "/api/v1/projects/payment_brain_http_test/brain/summary"
                )
                self.assertEqual(summary_response.status_code, 200)
                self.assertGreaterEqual(summary_response.json()["knowledge_unit_count"], 4)

                service = runtime.brain_for_project("payment_brain_http_test")
                created_candidates = service.propose_memories(
                    project_id="payment_brain_http_test",
                    session_id="route-session",
                    candidates=[
                        {"type": "risk", "statement": "Confirm route candidate."},
                        {"type": "gotcha", "statement": "Reject route candidate."},
                    ],
                )["candidates"]

                candidates_response = client.get(
                    "/api/v1/projects/payment_brain_http_test/brain/candidates",
                    params={"review_state": "human_review_required"},
                )
                self.assertEqual(candidates_response.status_code, 200)
                self.assertEqual(candidates_response.json()["candidate_count"], 2)

                confirm_response = client.post(
                    f"/api/v1/projects/payment_brain_http_test/brain/candidates/{created_candidates[0]['candidate_id']}/confirm"
                )
                self.assertEqual(confirm_response.status_code, 200)
                self.assertEqual(
                    confirm_response.json()["candidate"]["review_state"],
                    "human_confirmed",
                )

                reject_response = client.post(
                    f"/api/v1/projects/payment_brain_http_test/brain/candidates/{created_candidates[1]['candidate_id']}/reject"
                )
                self.assertEqual(reject_response.status_code, 200)
                self.assertEqual(reject_response.json()["candidate"]["review_state"], "rejected")
            finally:
                if previous is None:
                    os.environ.pop("PROJECTBRAIN_STORE_ROOT", None)
                else:
                    os.environ["PROJECTBRAIN_STORE_ROOT"] = previous

    def test_ui_scaffold_renders(self):
        if TestClient is None or app is None:
            self.skipTest("FastAPI is not installed in this interpreter")
        client = TestClient(app)

        # Index page is reachable both with and without trailing slash and
        # carries the observability banner that warns this is not a code editor.
        for path in ("/ui", "/ui/"):
            response = client.get(path, follow_redirects=True)
            self.assertEqual(response.status_code, 200, path)
            body = response.text
            self.assertIn("ProjectBrain 观察台", body)
            self.assertIn("AI 智能体看到的上下文", body)
            self.assertIn('href="/ui/static/app.css"', body)
            self.assertIn("htmx", body)

        # Static assets are served from the mounted directory.
        css_response = client.get("/ui/static/app.css")
        self.assertEqual(css_response.status_code, 200)
        self.assertIn("pb-header", css_response.text)
        self.assertIn("pb-tabs", css_response.text)

    def test_ui_wave3_pages(self):
        if TestClient is None or app is None:
            self.skipTest("FastAPI is not installed in this interpreter")
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            previous = os.environ.get("PROJECTBRAIN_STORE_ROOT")
            os.environ["PROJECTBRAIN_STORE_ROOT"] = tmp
            try:
                client = TestClient(app)

                # Empty project list page renders even with no projects.
                empty_list = client.get("/ui/projects")
                self.assertEqual(empty_list.status_code, 200)
                self.assertIn("尚未导入任何项目", empty_list.text)

                # Import via the UI form (multipart) drives the same runtime
                # path as the JSON API and triggers an HX-Redirect.
                import_response = client.post(
                    "/ui/projects/import",
                    data={
                        "project_id": "payment_mini_ui_test",
                        "project_path": str(fixture["project_path"]),
                        "name": "Payment Mini UI Test",
                        "experience_seed": str(fixture["experience_seed"]),
                        "path_prefixes": (
                            "contract/src/main/java/example/payment/settlement/\n"
                            "service/src/main/java/example/payment/settlement/\n"
                        ),
                        "kinds": "class, interface, method",
                        "node_limit": "50",
                        "edge_limit": "80",
                    },
                    headers={"HX-Request": "true"},
                )
                self.assertEqual(import_response.status_code, 200)
                self.assertEqual(
                    import_response.headers.get("hx-redirect"),
                    "/ui/projects/payment_mini_ui_test/context",
                )

                # Project list now shows the imported row.
                list_response = client.get("/ui/projects")
                self.assertEqual(list_response.status_code, 200)
                self.assertIn("payment_mini_ui_test", list_response.text)
                self.assertIn("Payment Mini UI Test", list_response.text)
                self.assertIn(
                    '/ui/projects/payment_mini_ui_test/context', list_response.text
                )

                # /ui/projects/{id} redirects to the context page.
                redirect_response = client.get(
                    "/ui/projects/payment_mini_ui_test", follow_redirects=False
                )
                self.assertEqual(redirect_response.status_code, 303)
                self.assertEqual(
                    redirect_response.headers["location"],
                    "/ui/projects/payment_mini_ui_test/context",
                )

                # Context page renders with policy sidebar.
                context_page = client.get(
                    "/ui/projects/payment_mini_ui_test/context"
                )
                self.assertEqual(context_page.status_code, 200)
                self.assertIn("构建 Context Pack", context_page.text)
                self.assertIn("pb-sidebar", context_page.text)
                self.assertIn("deny_paths", context_page.text)

                # POST /context/run returns an HTML partial containing the pack.
                context_run = client.post(
                    "/ui/projects/payment_mini_ui_test/context/run",
                    data={"task": "Explain settlement", "max_items_per_section": "5"},
                    headers={"HX-Request": "true"},
                )
                self.assertEqual(context_run.status_code, 200)
                self.assertIn("Context Pack", context_run.text)
                self.assertIn("pb-section", context_run.text)

                # Impact page exposes the three tabs.
                impact_page = client.get(
                    "/ui/projects/payment_mini_ui_test/impact"
                )
                self.assertEqual(impact_page.status_code, 200)
                self.assertIn('data-tab="manual"', impact_page.text)
                self.assertIn('data-tab="git"', impact_page.text)
                self.assertIn('data-tab="last"', impact_page.text)

                # Manual tab POST returns review_recommendation in the partial.
                impact_manual = client.post(
                    "/ui/projects/payment_mini_ui_test/impact/manual",
                    data={
                        "task": "Change settlement contract",
                        "changed_files": (
                            "contract/src/main/java/example/payment/settlement/"
                            "SettlementService.java\n"
                        ),
                        "changed_symbols": "",
                        "max_items_per_section": "5",
                    },
                    headers={"HX-Request": "true"},
                )
                self.assertEqual(impact_manual.status_code, 200)
                self.assertIn("review_recommendation", impact_manual.text)
                self.assertIn("manual_review_required", impact_manual.text)

                # Last-run tab now succeeds because manual tab persisted the
                # impact-analysis-latest.json artifact.
                last_run = client.get(
                    "/ui/projects/payment_mini_ui_test/impact/last-run"
                )
                self.assertEqual(last_run.status_code, 200)
                self.assertIn("Impact Analysis", last_run.text)
                self.assertIn("last-run", last_run.text)

                # Bad git-diff selection_kind surfaces an inline error partial.
                bad_diff = client.post(
                    "/ui/projects/payment_mini_ui_test/impact/git-diff",
                    data={
                        "task": "Review diff",
                        "selection_kind": "unknown",
                    },
                    headers={"HX-Request": "true"},
                )
                self.assertEqual(bad_diff.status_code, 400)
                self.assertIn("pb-error", bad_diff.text)

                # Policy page renders the full policy view.
                policy_page = client.get(
                    "/ui/projects/payment_mini_ui_test/policy"
                )
                self.assertEqual(policy_page.status_code, 200)
                self.assertIn("当前生效策略", policy_page.text)
                self.assertIn("deny_paths", policy_page.text)
                self.assertIn("include_source_snippets", policy_page.text)

                # Unknown project returns a 404 inline error.
                unknown = client.get("/ui/projects/does_not_exist/context")
                self.assertEqual(unknown.status_code, 404)
                self.assertIn("未找到", unknown.text)
            finally:
                if previous is None:
                    os.environ.pop("PROJECTBRAIN_STORE_ROOT", None)
                else:
                    os.environ["PROJECTBRAIN_STORE_ROOT"] = previous


if __name__ == "__main__":
    unittest.main()
