"""FastAPI entrypoint for ProjectBrain local runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from projectbrain_api.dependencies import build_runtime
from projectbrain_api.handlers import (
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

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without api extra.
    raise ModuleNotFoundError(
        "FastAPI is not installed. Install the API extra with: pip install -e '.[api]'"
    ) from exc

from projectbrain_api.ui.router import router as ui_router


app = FastAPI(title="ProjectBrain Local Runtime API", version="0.1.0")

# Observability UI (HTMX) — local-only, mounted under /ui.
app.include_router(ui_router)
_UI_STATIC_DIR = Path(__file__).resolve().parent / "ui" / "static"
app.mount(
    "/ui/static",
    StaticFiles(directory=str(_UI_STATIC_DIR)),
    name="ui-static",
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    # 根路径直接跳到 UI，方便浏览器直接访问 127.0.0.1:8765。
    return RedirectResponse(url="/ui", status_code=307)


@app.get("/health")
def health() -> dict[str, str]:
    return health_response()


@app.post("/api/v1/projects/import")
def import_project(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return import_project_handler(build_runtime(), payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/projects")
def list_projects() -> dict[str, Any]:
    return list_projects_handler(build_runtime())


@app.post("/api/v1/projects/{project_id}/context-pack")
def context_pack(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return context_pack_handler(build_runtime(), project_id, payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/impact-analysis")
def impact_analysis(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return impact_analysis_handler(build_runtime(), project_id, payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/impact-analysis/git-diff")
def impact_analysis_git_diff(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return git_diff_impact_handler(build_runtime(), project_id, payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/projects/{project_id}/policy")
def inspect_policy(project_id: str) -> dict[str, Any]:
    try:
        return policy_inspect_handler(build_runtime(), project_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/projects/{project_id}/claims")
def list_claims(project_id: str, include_archived: bool = False) -> dict[str, Any]:
    try:
        return list_claims_handler(build_runtime(), project_id, include_archived=include_archived)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/claims")
def add_claim(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return add_claim_handler(build_runtime(), project_id, payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/v1/projects/{project_id}/claims/{claim_id}")
def review_claim(project_id: str, claim_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return review_claim_handler(build_runtime(), project_id, claim_id, payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/projects/{project_id}/claims/{claim_id}")
def archive_claim(project_id: str, claim_id: str, reason: str | None = None) -> dict[str, Any]:
    try:
        return archive_claim_handler(build_runtime(), project_id, claim_id, reason=reason)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
