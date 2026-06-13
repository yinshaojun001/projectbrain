"""API handler functions that can be tested without FastAPI installed."""

from __future__ import annotations

from typing import Any

from projectbrain_runtime.models import ImportOptions
from projectbrain_runtime.service import ProjectBrainRuntime


def health_response() -> dict[str, str]:
    return {"status": "ok"}


def import_project_handler(runtime: ProjectBrainRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    required = ["project_id", "project_path"]
    _require_payload_keys(payload, required)
    return runtime.import_project(
        project_id=payload["project_id"],
        project_path=payload["project_path"],
        name=payload.get("name"),
        experience_seed=payload.get("experience_seed"),
        options=ImportOptions(
            path_prefixes=payload.get("path_prefixes", []),
            kinds=payload.get("kinds", []),
            node_limit=int(payload.get("node_limit", 200)),
            edge_limit=int(payload.get("edge_limit", 300)),
        ),
    )


def list_projects_handler(runtime: ProjectBrainRuntime) -> dict[str, Any]:
    return {"projects": [project.to_dict() for project in runtime.repository.list_projects()]}


def context_pack_handler(runtime: ProjectBrainRuntime, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require_payload_keys(payload, ["task"])
    return runtime.build_context_pack(
        project_id=project_id,
        task=payload["task"],
        max_items_per_section=int(payload.get("max_items_per_section", 12)),
    )


def impact_analysis_handler(runtime: ProjectBrainRuntime, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require_payload_keys(payload, ["task"])
    return runtime.analyze_impact(
        project_id=project_id,
        task=payload["task"],
        changed_files=payload.get("changed_files", []),
        changed_symbols=payload.get("changed_symbols", []),
        max_items_per_section=int(payload.get("max_items_per_section", 12)),
    )


def _require_payload_keys(payload: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in payload or payload[key] in (None, "")]
    if missing:
        raise ValueError(f"Missing required payload keys: {', '.join(missing)}")
