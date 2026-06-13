"""FastAPI entrypoint for ProjectBrain local runtime."""

from __future__ import annotations

from typing import Any

from projectbrain_api.dependencies import build_runtime
from projectbrain_api.handlers import (
    context_pack_handler,
    health_response,
    impact_analysis_handler,
    import_project_handler,
    list_projects_handler,
)

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without api extra.
    raise ModuleNotFoundError(
        "FastAPI is not installed. Install the API extra with: pip install -e '.[api]'"
    ) from exc


app = FastAPI(title="ProjectBrain Local Runtime API", version="0.1.0")


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
