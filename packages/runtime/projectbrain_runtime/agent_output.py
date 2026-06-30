"""Compact ProjectBrain output for AI coding agents."""

from __future__ import annotations

from typing import Any


OUTPUT_FORMATS = ("json", "agent")


def format_agent_output(data: dict[str, Any]) -> dict[str, Any]:
    """Return compact, action-oriented output for an existing runtime result."""

    if "context_pack" in data:
        return _context_pack_output(data["context_pack"])
    if "impact_analysis" in data:
        output = _impact_analysis_output(data["impact_analysis"])
        if "git_diff" in data:
            output["git_diff"] = data["git_diff"]
        return output
    if "baseline" in data:
        return _project_baseline_output(data["baseline"])
    return data


def format_output(data: dict[str, Any], output_format: str = "json") -> dict[str, Any]:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output_format: {output_format}")
    if output_format == "agent":
        return {"agent_output": format_agent_output(data)}
    return data


def _context_pack_output(pack: dict[str, Any]) -> dict[str, Any]:
    sections = _sections_by_type(pack)
    return {
        "artifact_type": "context_pack",
        "project_id": pack.get("project_id"),
        "task": pack.get("task"),
        "summary": pack.get("summary"),
        "must_read_files": _files(pack.get("recommended_files", [])),
        "important_symbols": _symbols(pack.get("recommended_symbols", [])),
        "risk_warnings": _messages([*pack.get("warnings", []), *_section_items(sections, "risk_hypotheses")]),
        "recommended_tests": _tests(pack.get("recommended_tests", [])),
        "manual_review": _manual_review_from_context(pack, sections),
        "omissions": _messages(pack.get("omissions", [])),
    }


def _impact_analysis_output(analysis: dict[str, Any]) -> dict[str, Any]:
    sections = _sections_by_type(analysis)
    recommendation = analysis.get("review_recommendation", {})
    return {
        "artifact_type": "impact_analysis",
        "project_id": analysis.get("project_id"),
        "task": analysis.get("task"),
        "summary": analysis.get("summary"),
        "changed_files": analysis.get("change", {}).get("changed_files", []),
        "matched_entities": _matched_entities(_section_items(sections, "changed_entities")),
        "affected_relations": _relations(
            [
                *_section_items(sections, "affected_calls"),
                *_section_items(sections, "affected_dependencies"),
            ]
        ),
        "risk_warnings": _messages(_section_items(sections, "risk_warnings")),
        "recommended_tests": _tests(analysis.get("recommended_tests", [])),
        "manual_review": {
            "required": recommendation.get("action") == "manual_review_required",
            "recommended": recommendation.get("action") in {"manual_review_required", "manual_review_recommended"},
            "risk_level": recommendation.get("risk_level"),
            "reason": recommendation.get("reason"),
        },
        "review_recommendation": recommendation,
        "omissions": _messages(analysis.get("omissions", [])),
    }


def _project_baseline_output(baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "project_baseline",
        "project_id": baseline.get("project_id"),
        "project_summary": baseline.get("project_summary"),
        "project_goal": baseline.get("project_goal"),
        "primary_users": baseline.get("primary_users"),
        "core_modules": baseline.get("core_modules"),
        "key_flows": baseline.get("key_flows"),
        "third_party_integrations": baseline.get("third_party_integrations"),
        "high_risk_areas": baseline.get("high_risk_areas"),
        "constraints": baseline.get("constraints"),
        "validation_strategy": baseline.get("validation_strategy"),
        "priority_evidence": baseline.get("priority_evidence"),
        "unknowns": baseline.get("unknowns"),
        "quality_notes": baseline.get("quality_notes"),
    }


def _sections_by_type(artifact: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    sections: dict[str, list[dict[str, Any]]] = {}
    for section in artifact.get("sections", []):
        section_type = section.get("type")
        if section_type:
            sections.setdefault(section_type, []).append(section)
    return sections


def _section_items(sections: dict[str, list[dict[str, Any]]], section_type: str) -> list[Any]:
    items = []
    for section in sections.get(section_type, []):
        items.extend(section.get("items", []))
    return items


def _files(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "file": item.get("file"),
            "reason": item.get("reason"),
        }
        for item in items
    ]


def _symbols(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "qualified_name": item.get("qualified_name"),
            "entity_type": item.get("entity_type"),
            "file": item.get("file"),
        }
        for item in items
    ]


def _matched_entities(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "qualified_name": item.get("qualified_name"),
            "entity_type": item.get("entity_type"),
            "file": item.get("file"),
        }
        for item in items
    ]


def _relations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "relation_type": item.get("relation_type"),
            "direction": item.get("direction"),
            "from": item.get("from"),
            "to": item.get("to"),
        }
        for item in items
    ]


def _tests(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "qualified_name": item.get("qualified_name"),
            "file": item.get("file"),
            "reason": item.get("reason"),
        }
        for item in items
    ]


def _messages(items: list[Any]) -> list[dict[str, Any]]:
    messages = []
    for item in items:
        if isinstance(item, str):
            messages.append({"message": item})
        elif isinstance(item, dict):
            messages.append(
                {
                    "code": item.get("code"),
                    "message": item.get("message") or item.get("statement"),
                    "confidence": item.get("confidence"),
                }
            )
    return messages


def _string_list(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, str)]


def _manual_review_from_context(pack: dict[str, Any], sections: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    warnings = pack.get("warnings", [])
    risk_items = _section_items(sections, "risk_hypotheses")
    return {
        "recommended": bool(warnings or risk_items),
        "reason": "Review risk warnings and unknowns before editing.",
    }
