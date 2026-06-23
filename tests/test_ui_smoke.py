"""Lightweight UI smoke tests.

These tests do not import a project fixture. They only verify that the /ui/*
HTML surface renders, that static assets are mounted, that the empty-state
landing pages are reachable, and that the unknown-project error path returns
the expected status code. Heavier end-to-end coverage (real import, context,
impact, policy) lives in `test_api_fastapi.py::test_ui_wave3_pages`.
"""

from __future__ import annotations

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

from projectbrain_runtime.models import ProjectRecord  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


try:
    from fastapi.testclient import TestClient  # noqa: E402
    from projectbrain_api.main import app  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - tested in .venv with api extra installed.
    TestClient = None
    app = None


class UiSmokeTest(unittest.TestCase):
    """Verifies every /ui/* page renders without depending on a real project."""

    def setUp(self) -> None:
        if TestClient is None or app is None:
            self.skipTest("FastAPI is not installed in this interpreter")
        self._tmp = tempfile.TemporaryDirectory()
        self._previous_root = os.environ.get("PROJECTBRAIN_STORE_ROOT")
        os.environ["PROJECTBRAIN_STORE_ROOT"] = self._tmp.name
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._previous_root is None:
            os.environ.pop("PROJECTBRAIN_STORE_ROOT", None)
        else:
            os.environ["PROJECTBRAIN_STORE_ROOT"] = self._previous_root
        self._tmp.cleanup()

    def test_index_page_includes_observability_banner(self) -> None:
        for path in ("/ui", "/ui/"):
            response = self.client.get(path, follow_redirects=True)
            self.assertEqual(response.status_code, 200, path)
            body = response.text
            self.assertIn("ProjectBrain 观察台", body)
            self.assertIn("AI 智能体看到的上下文", body)
            # Banner explicitly clarifies this is not a code editor (STATE.md L11).
            self.assertIn("不是代码搜索", body)

    def test_static_css_is_mounted(self) -> None:
        response = self.client.get("/ui/static/app.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("pb-header", response.text)
        # Wave 3 styles are present so impact tabs render correctly.
        self.assertIn("pb-tabs", response.text)
        self.assertIn("pb-callout", response.text)

    def test_projects_with_project_path_auto_opens_brain_for_git_project(self) -> None:
        project_path = Path(self._tmp.name) / "My Project"
        project_path.mkdir()
        (project_path / ".git").mkdir()

        response = self.client.get(
            "/ui/projects",
            params={"project_path": str(project_path)},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/ui/projects/my_project/brain")
        self.assertTrue((project_path / ".projectbrain" / "brain" / "manifest.json").exists())

        brain_response = self.client.get(response.headers["location"])
        self.assertEqual(brain_response.status_code, 200)
        self.assertIn("Project Brain", brain_response.text)
        self.assertNotIn("导入项目", brain_response.text)

    def _create_brain_candidate(self, *, project_id: str = "ui_candidate_project", statement: str = "UI candidate should be confirmable.") -> str:
        project_path = Path(self._tmp.name) / f"{project_id}_repo"
        project_path.mkdir()
        runtime = ProjectBrainRuntime(JsonProjectBrainRepository(Path(self._tmp.name)))
        runtime.repository.save_project(ProjectRecord(
            project_id=project_id,
            name="UI Candidate Project",
            source_path=str(project_path),
            codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
        ))
        created = runtime.brain_for_project(project_id).propose_memories(
            project_id=project_id,
            session_id="ui-session",
            candidates=[{"type": "decision", "statement": statement}],
        )["candidates"]
        return created[0]["candidate_id"]

    def test_brain_page_renders_candidate_confirm_and_reject_buttons(self) -> None:
        candidate_id = self._create_brain_candidate()

        response = self.client.get("/ui/projects/ui_candidate_project/brain")

        self.assertEqual(response.status_code, 200)
        self.assertIn("确认加入知识库", response.text)
        self.assertIn("拒绝", response.text)
        self.assertIn(
            f'action="/ui/projects/ui_candidate_project/brain/candidates/{candidate_id}/confirm"',
            response.text,
        )
        self.assertIn(
            f'action="/ui/projects/ui_candidate_project/brain/candidates/{candidate_id}/reject"',
            response.text,
        )

    def test_brain_candidate_confirm_button_promotes_candidate_and_returns_to_brain_page(self) -> None:
        candidate_id = self._create_brain_candidate(
            project_id="ui_confirm_project",
            statement="Confirmed UI candidate becomes knowledge.",
        )

        response = self.client.post(
            f"/ui/projects/ui_confirm_project/brain/candidates/{candidate_id}/confirm",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/ui/projects/ui_confirm_project/brain")
        refreshed = self.client.get(response.headers["location"])
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("Confirmed UI candidate becomes knowledge.", refreshed.text)
        self.assertIn("暂无待确认知识。", refreshed.text)

    def test_brain_candidate_reject_button_removes_candidate_from_pending_list(self) -> None:
        candidate_id = self._create_brain_candidate(
            project_id="ui_reject_project",
            statement="Rejected UI candidate leaves pending list.",
        )

        response = self.client.post(
            f"/ui/projects/ui_reject_project/brain/candidates/{candidate_id}/reject",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/ui/projects/ui_reject_project/brain")
        refreshed = self.client.get(response.headers["location"])
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("暂无待确认知识。", refreshed.text)
        self.assertNotIn("Rejected UI candidate leaves pending list.", refreshed.text)

    def test_empty_project_list_renders(self) -> None:
        response = self.client.get("/ui/projects")
        self.assertEqual(response.status_code, 200)
        self.assertIn("项目列表", response.text)
        self.assertIn("导入项目", response.text)
        self.assertIn("尚未导入任何项目", response.text)

    def test_unknown_project_context_returns_404(self) -> None:
        response = self.client.get("/ui/projects/__does_not_exist__/context")
        self.assertEqual(response.status_code, 404)
        self.assertIn("未找到", response.text)
        self.assertIn("pb-error", response.text)

    def test_unknown_project_impact_returns_404(self) -> None:
        response = self.client.get("/ui/projects/__does_not_exist__/impact")
        self.assertEqual(response.status_code, 404)

    def test_unknown_project_policy_returns_404(self) -> None:
        response = self.client.get("/ui/projects/__does_not_exist__/policy")
        self.assertEqual(response.status_code, 404)

    def test_last_run_partial_returns_404_without_artifact(self) -> None:
        response = self.client.get(
            "/ui/projects/__does_not_exist__/impact/last-run"
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("impact-analysis-latest.json", response.text)

    def test_project_redirect_to_context(self) -> None:
        response = self.client.get(
            "/ui/projects/anything", follow_redirects=False
        )
        # Always redirects, even for unknown projects; 404 surfaces on /context.
        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            response.headers["location"],
            "/ui/projects/anything/context",
        )


if __name__ == "__main__":
    unittest.main()
