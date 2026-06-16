"""UI router that serves HTMX-driven observability pages.

Routes (all local-only, mounted under /ui):

* GET  /ui                                       — landing page
* GET  /ui/projects                              — project list + import form
* POST /ui/projects/import                       — import handler (HX-Redirect)
* GET  /ui/projects/{id}                         — redirect to context page
* GET  /ui/projects/{id}/context                 — Context Pack browser
* POST /ui/projects/{id}/context/run             — HTMX partial: context result
* GET  /ui/projects/{id}/impact                  — Impact Analysis viewer
* POST /ui/projects/{id}/impact/manual           — HTMX partial: manual impact
* POST /ui/projects/{id}/impact/git-diff         — HTMX partial: git-diff impact
* GET  /ui/projects/{id}/impact/last-run         — HTMX partial: last run
* GET  /ui/projects/{id}/policy                  — Policy details page

This module renders HTML only. JSON API consumers continue to use /api/v1/*.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, Form, Request
    from fastapi.responses import HTMLResponse, RedirectResponse, Response
    from fastapi.templating import Jinja2Templates
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without api extra.
    raise ModuleNotFoundError(
        "FastAPI is not installed. Install the API extra with: pip install -e '.[api]'"
    ) from exc

from projectbrain_api.dependencies import build_runtime
from projectbrain_api.handlers import _parse_git_diff_selection
from projectbrain_runtime.models import ImportOptions
from projectbrain_runtime.service import ProjectBrainRuntime


_UI_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _UI_DIR / "templates"
_VENDOR_HTMX = _UI_DIR / "static" / "vendor" / "htmx.min.js"

# Pinned version. If you upgrade, also update vendor/README.md.
_HTMX_CDN_URL = "https://cdn.jsdelivr.net/npm/htmx.org@1.9.12/dist/htmx.min.js"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(prefix="/ui", tags=["ui"])


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _htmx_asset_url() -> str:
    """Prefer the vendored copy; fall back to a pinned CDN version."""
    if _VENDOR_HTMX.is_file():
        return "/ui/static/vendor/htmx.min.js"
    return _HTMX_CDN_URL


def _base_context(**extra: Any) -> dict[str, Any]:
    context: dict[str, Any] = {
        "htmx_url": _htmx_asset_url(),
        "banner_text": (
            "This UI observes AI agent context. "
            "It is not a code search or code editor."
        ),
    }
    context.update(extra)
    return context


def _runtime() -> ProjectBrainRuntime:
    return build_runtime()


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _split_csv(value: str) -> list[str]:
    return [piece.strip() for piece in value.split(",") if piece.strip()]


def _load_policy_summary(
    runtime: ProjectBrainRuntime, project_id: str
) -> dict[str, Any] | None:
    try:
        return runtime.inspect_policy(project_id=project_id)
    except (FileNotFoundError, ValueError):
        return None


def _read_latest_run(
    runtime: ProjectBrainRuntime, project_id: str, name: str
) -> dict[str, Any] | None:
    try:
        runtime.repository.get_project(project_id)
    except (FileNotFoundError, ValueError):
        return None
    runs_dir = runtime.repository.store.runs_dir(project_id)
    path = runs_dir / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _error_partial(request: Request, message: str, *, status_code: int = 400) -> HTMLResponse:
    body = templates.TemplateResponse(
        request,
        "_partials/error.html",
        {"message": message},
    ).body
    return HTMLResponse(body, status_code=status_code)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        _base_context(
            title="ProjectBrain Observability",
            heading="ProjectBrain Observability",
        ),
    )


@router.get("/projects", response_class=HTMLResponse, include_in_schema=False)
def ui_projects_list(request: Request) -> HTMLResponse:
    runtime = _runtime()
    projects = [project.to_dict() for project in runtime.repository.list_projects()]
    return templates.TemplateResponse(
        request,
        "projects/list.html",
        _base_context(
            title="Projects · ProjectBrain",
            heading="Projects",
            projects=projects,
        ),
    )


@router.post("/projects/import", include_in_schema=False)
def ui_projects_import(
    request: Request,
    project_id: str = Form(...),
    project_path: str = Form(...),
    name: str = Form(""),
    experience_seed: str = Form(""),
    path_prefixes: str = Form(""),
    kinds: str = Form(""),
    node_limit: int = Form(200),
    edge_limit: int = Form(300),
) -> Response:
    runtime = _runtime()
    options = ImportOptions(
        path_prefixes=_split_lines(path_prefixes),
        kinds=_split_csv(kinds),
        node_limit=int(node_limit),
        edge_limit=int(edge_limit),
    )
    try:
        runtime.import_project(
            project_id=project_id,
            project_path=project_path,
            name=name or None,
            experience_seed=experience_seed or None,
            options=options,
        )
    except (FileNotFoundError, ValueError) as exc:
        return _error_partial(request, f"Import failed: {exc}")

    target = f"/ui/projects/{project_id}/context"
    if request.headers.get("hx-request") == "true":
        return HTMLResponse("", headers={"HX-Redirect": target})
    return RedirectResponse(url=target, status_code=303)


@router.get("/projects/{project_id}", include_in_schema=False)
def ui_project_detail(project_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/ui/projects/{project_id}/context", status_code=303)


# ---------- Context Pack ---------- #


@router.get(
    "/projects/{project_id}/context",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_context_page(request: Request, project_id: str) -> HTMLResponse:
    runtime = _runtime()
    try:
        project = runtime.repository.get_project(project_id).to_dict()
    except (FileNotFoundError, ValueError):
        return _error_partial(
            request, f"Project '{project_id}' not found", status_code=404
        )
    last_run = _read_latest_run(runtime, project_id, "context-pack-latest.json")
    return templates.TemplateResponse(
        request,
        "projects/context.html",
        _base_context(
            title=f"Context · {project_id}",
            heading=f"Context Pack — {project_id}",
            project=project,
            policy=_load_policy_summary(runtime, project_id),
            last_run=last_run,
        ),
    )


@router.post(
    "/projects/{project_id}/context/run",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_context_run(
    request: Request,
    project_id: str,
    task: str = Form(...),
    max_items_per_section: int = Form(12),
) -> HTMLResponse:
    runtime = _runtime()
    try:
        result = runtime.build_context_pack(
            project_id=project_id,
            task=task,
            max_items_per_section=int(max_items_per_section),
        )
    except (FileNotFoundError, ValueError) as exc:
        return _error_partial(request, f"Context pack failed: {exc}")
    return templates.TemplateResponse(
        request,
        "_partials/context_result.html",
        {
            "context_pack": result["context_pack"],
            "artifact_path": result.get("artifact_path"),
        },
    )


# ---------- Impact Analysis ---------- #


@router.get(
    "/projects/{project_id}/impact",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_impact_page(request: Request, project_id: str) -> HTMLResponse:
    runtime = _runtime()
    try:
        project = runtime.repository.get_project(project_id).to_dict()
    except (FileNotFoundError, ValueError):
        return _error_partial(
            request, f"Project '{project_id}' not found", status_code=404
        )
    return templates.TemplateResponse(
        request,
        "projects/impact.html",
        _base_context(
            title=f"Impact · {project_id}",
            heading=f"Impact Analysis — {project_id}",
            project=project,
            policy=_load_policy_summary(runtime, project_id),
        ),
    )


@router.post(
    "/projects/{project_id}/impact/manual",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_impact_manual(
    request: Request,
    project_id: str,
    task: str = Form(...),
    changed_files: str = Form(""),
    changed_symbols: str = Form(""),
    max_items_per_section: int = Form(12),
) -> HTMLResponse:
    runtime = _runtime()
    try:
        result = runtime.analyze_impact(
            project_id=project_id,
            task=task,
            changed_files=_split_lines(changed_files),
            changed_symbols=_split_csv(changed_symbols),
            max_items_per_section=int(max_items_per_section),
        )
    except (FileNotFoundError, ValueError) as exc:
        return _error_partial(request, f"Impact analysis failed: {exc}")
    return templates.TemplateResponse(
        request,
        "_partials/impact_result.html",
        {
            "impact_analysis": result["impact_analysis"],
            "artifact_path": result.get("artifact_path"),
            "git_diff": None,
            "source_label": "manual",
        },
    )


@router.post(
    "/projects/{project_id}/impact/git-diff",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_impact_git_diff(
    request: Request,
    project_id: str,
    task: str = Form(...),
    selection_kind: str = Form(...),
    from_ref: str = Form(""),
    to_ref: str = Form(""),
    changed_symbols: str = Form(""),
    max_items_per_section: int = Form(12),
) -> HTMLResponse:
    runtime = _runtime()
    selection_payload: dict[str, Any] = {"kind": selection_kind}
    if selection_kind == "branch":
        selection_payload["from"] = from_ref or None
        selection_payload["to"] = to_ref or None
    try:
        selection = _parse_git_diff_selection(selection_payload)
        result = runtime.analyze_git_diff_impact(
            project_id=project_id,
            task=task,
            selection=selection,
            changed_symbols=_split_csv(changed_symbols),
            max_items_per_section=int(max_items_per_section),
        )
    except (FileNotFoundError, ValueError) as exc:
        return _error_partial(request, f"Git diff impact failed: {exc}")
    return templates.TemplateResponse(
        request,
        "_partials/impact_result.html",
        {
            "impact_analysis": result["impact_analysis"],
            "artifact_path": result.get("artifact_path"),
            "git_diff": result.get("git_diff"),
            "source_label": "git-diff",
        },
    )


@router.get(
    "/projects/{project_id}/impact/last-run",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_impact_last_run(request: Request, project_id: str) -> HTMLResponse:
    runtime = _runtime()
    payload = _read_latest_run(runtime, project_id, "impact-analysis-latest.json")
    if payload is None:
        return _error_partial(
            request,
            "No impact-analysis-latest.json found for this project. "
            "Run an analysis first via the Manual or Git-diff tab.",
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "_partials/impact_result.html",
        {
            "impact_analysis": payload,
            "artifact_path": None,
            "git_diff": None,
            "source_label": "last-run",
        },
    )


# ---------- Policy ---------- #


@router.get(
    "/projects/{project_id}/policy",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def ui_policy_page(request: Request, project_id: str) -> HTMLResponse:
    runtime = _runtime()
    try:
        project = runtime.repository.get_project(project_id).to_dict()
    except (FileNotFoundError, ValueError):
        return _error_partial(
            request, f"Project '{project_id}' not found", status_code=404
        )
    policy = _load_policy_summary(runtime, project_id)
    return templates.TemplateResponse(
        request,
        "projects/policy.html",
        _base_context(
            title=f"Policy · {project_id}",
            heading=f"Policy — {project_id}",
            project=project,
            policy=policy,
        ),
    )
