"""API handler functions that can be tested without FastAPI installed."""

from __future__ import annotations

from typing import Any

from projectbrain_runtime.git_diff import GitDiffSelection
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


def git_diff_impact_handler(
    runtime: ProjectBrainRuntime,
    project_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_payload_keys(payload, ["task", "selection"])
    selection = _parse_git_diff_selection(payload["selection"])
    return runtime.analyze_git_diff_impact(
        project_id=project_id,
        task=payload["task"],
        selection=selection,
        changed_symbols=payload.get("changed_symbols") or [],
        max_items_per_section=int(payload.get("max_items_per_section", 12)),
    )


def policy_inspect_handler(runtime: ProjectBrainRuntime, project_id: str) -> dict[str, Any]:
    return runtime.inspect_policy(project_id=project_id)


def list_claims_handler(
    runtime: ProjectBrainRuntime,
    project_id: str,
    include_archived: bool = False,
) -> dict[str, Any]:
    return runtime.list_experience_claims(
        project_id=project_id,
        include_archived=bool(include_archived),
    )


def add_claim_handler(
    runtime: ProjectBrainRuntime,
    project_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_payload_keys(payload, ["statement"])
    return runtime.add_experience_claim(
        project_id=project_id,
        statement=payload["statement"],
        applies_to=payload.get("applies_to"),
        risk_level=payload.get("risk_level", "normal"),
        review_state=payload.get("review_state", "draft"),
        claim_type=payload.get("claim_type", "HUMAN_REVIEW_REQUIRED"),
        confidence=float(payload.get("confidence", 0.8)),
        source=payload.get("source"),
        claim_id=payload.get("claim_id"),
    )


def review_claim_handler(
    runtime: ProjectBrainRuntime,
    project_id: str,
    claim_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    confidence = payload.get("confidence")
    return runtime.review_experience_claim(
        project_id=project_id,
        claim_id=claim_id,
        review_state=payload.get("review_state"),
        risk_level=payload.get("risk_level"),
        claim_type=payload.get("claim_type"),
        confidence=float(confidence) if confidence is not None else None,
        statement=payload.get("statement"),
        applies_to=payload.get("applies_to"),
        source=payload.get("source"),
    )


def archive_claim_handler(
    runtime: ProjectBrainRuntime,
    project_id: str,
    claim_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    return runtime.archive_experience_claim(
        project_id=project_id,
        claim_id=claim_id,
        reason=reason,
    )


def brain_summary_handler(runtime: ProjectBrainRuntime, project_id: str) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).summary()


def brain_knowledge_list_handler(runtime: ProjectBrainRuntime, project_id: str, query: dict[str, Any]) -> dict[str, Any]:
    q = query.get("q")
    service = runtime.brain_for_project(project_id)
    if q:
        return service.search(str(q), limit=int(query.get("limit", 20)))
    return service.list_knowledge(
        type=query.get("type"),
        review_state=query.get("review_state"),
        staleness=query.get("staleness"),
        tag=query.get("tag"),
        include_archived=bool(query.get("include_archived", False)),
    )


def brain_knowledge_create_handler(runtime: ProjectBrainRuntime, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require_payload_keys(payload, ["type", "statement"])
    return runtime.brain_for_project(project_id).remember(
        type=payload["type"],
        statement=payload["statement"],
        title=payload.get("title"),
        summary=payload.get("summary", ""),
        tags=payload.get("tags", []),
        applies_to=payload.get("applies_to", []),
        review_state=payload.get("review_state", "human_review_required"),
        confidence=float(payload.get("confidence", 0.8)),
        risk_level=payload.get("risk_level", "normal"),
    )


def brain_candidates_handler(runtime: ProjectBrainRuntime, project_id: str, query: dict[str, Any]) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).list_candidates(review_state=query.get("review_state"))


def brain_candidate_confirm_handler(runtime: ProjectBrainRuntime, project_id: str, candidate_id: str) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).confirm_candidate(candidate_id)


def brain_candidate_reject_handler(runtime: ProjectBrainRuntime, project_id: str, candidate_id: str) -> dict[str, Any]:
    return runtime.brain_for_project(project_id).reject_candidate(candidate_id)


def _parse_git_diff_selection(selection: dict[str, Any]) -> GitDiffSelection:
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    kind = selection.get("kind")
    if kind == "staged":
        return GitDiffSelection(staged=True)
    if kind == "last-commit" or kind == "last_commit":
        return GitDiffSelection(last_commit=True)
    if kind == "branch":
        from_ref = selection.get("from") or selection.get("from_ref")
        to_ref = selection.get("to") or selection.get("to_ref")
        if not from_ref and not to_ref:
            raise ValueError("branch selection requires 'from' or 'to' ref")
        return GitDiffSelection(from_ref=from_ref, to_ref=to_ref)
    raise ValueError(
        "selection.kind must be one of: staged, last-commit, branch"
    )


def _require_payload_keys(payload: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in payload or payload[key] in (None, "")]
    if missing:
        raise ValueError(f"Missing required payload keys: {', '.join(missing)}")
