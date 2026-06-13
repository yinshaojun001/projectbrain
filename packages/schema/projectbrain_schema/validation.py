"""Lightweight validation for ProjectBrain V0.1 JSON artifacts."""

from __future__ import annotations

from typing import Any

from projectbrain_schema.models import ContextPack, ImpactAnalysis, KnowledgeEntity, KnowledgeRelation, SourceRef


class SchemaValidationError(ValueError):
    """Raised when a ProjectBrain artifact violates the V0.1 schema contract."""


def validate_facts_export(data: dict[str, Any]) -> None:
    _require_keys(data, ["project_id", "entities", "relations", "sources"], "facts_export")
    if not isinstance(data["entities"], list):
        raise SchemaValidationError("facts_export.entities must be a list")
    if not isinstance(data["relations"], list):
        raise SchemaValidationError("facts_export.relations must be a list")
    if not isinstance(data["sources"], list):
        raise SchemaValidationError("facts_export.sources must be a list")

    source_uris = set()
    for index, source_data in enumerate(data["sources"]):
        source = SourceRef.from_dict(source_data)
        _require_non_empty(source.uri, f"sources[{index}].uri")
        source_uris.add(source.uri)

    entity_keys = set()
    for index, entity_data in enumerate(data["entities"]):
        entity = KnowledgeEntity.from_dict(entity_data)
        _require_non_empty(entity.stable_key, f"entities[{index}].stable_key")
        _require_non_empty(entity.entity_type, f"entities[{index}].entity_type")
        _require_non_empty(entity.qualified_name, f"entities[{index}].qualified_name")
        if not entity.source_refs:
            raise SchemaValidationError(f"entities[{index}] must have at least one source_ref")
        entity_keys.add(entity.stable_key)

    for index, relation_data in enumerate(data["relations"]):
        relation = KnowledgeRelation.from_dict(relation_data)
        _require_non_empty(relation.relation_type, f"relations[{index}].relation_type")
        _require_non_empty(relation.from_stable_key, f"relations[{index}].from_stable_key")
        _require_non_empty(relation.to_stable_key, f"relations[{index}].to_stable_key")
        _validate_confidence(relation.confidence, f"relations[{index}].confidence")
        if not relation.source_refs:
            raise SchemaValidationError(f"relations[{index}] must have at least one source_ref")


def validate_context_pack(data: dict[str, Any]) -> None:
    pack = ContextPack.from_dict(data)
    _require_non_empty(pack.context_pack_id, "context_pack_id")
    _require_non_empty(pack.project_id, "project_id")
    _require_non_empty(pack.task, "task")
    _require_non_empty(pack.summary, "summary")
    _validate_sections(pack.sections, "context_pack.sections")
    _validate_sources_in_items(pack.sections, "context_pack.sections")


def validate_impact_analysis(data: dict[str, Any]) -> None:
    analysis = ImpactAnalysis.from_dict(data)
    _require_non_empty(analysis.impact_analysis_id, "impact_analysis_id")
    _require_non_empty(analysis.project_id, "project_id")
    _require_non_empty(analysis.task, "task")
    _require_keys(analysis.change, ["changed_files", "changed_symbols"], "impact_analysis.change")
    _require_non_empty(analysis.summary, "summary")
    _validate_sections(analysis.sections, "impact_analysis.sections")
    _validate_review_recommendation(analysis.review_recommendation)


def _require_keys(data: dict[str, Any], keys: list[str], label: str) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise SchemaValidationError(f"{label} missing required keys: {', '.join(missing)}")


def _require_non_empty(value: Any, label: str) -> None:
    if value is None or value == "":
        raise SchemaValidationError(f"{label} must not be empty")


def _validate_confidence(value: float, label: str) -> None:
    if value < 0 or value > 1:
        raise SchemaValidationError(f"{label} must be between 0 and 1")


def _validate_sections(sections: list[dict[str, Any]], label: str) -> None:
    if not isinstance(sections, list):
        raise SchemaValidationError(f"{label} must be a list")
    if not sections:
        raise SchemaValidationError(f"{label} must not be empty")
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise SchemaValidationError(f"{label}[{index}] must be an object")
        _require_non_empty(section.get("type"), f"{label}[{index}].type")
        if "items" in section and not isinstance(section["items"], list):
            raise SchemaValidationError(f"{label}[{index}].items must be a list")


def _validate_sources_in_items(sections: list[dict[str, Any]], label: str) -> None:
    for section_index, section in enumerate(sections):
        for item_index, item in enumerate(section.get("items", [])):
            if isinstance(item, dict) and "confidence" in item:
                _validate_confidence(float(item["confidence"]), f"{label}[{section_index}].items[{item_index}].confidence")
            if isinstance(item, dict) and "sources" in item and not isinstance(item["sources"], list):
                raise SchemaValidationError(f"{label}[{section_index}].items[{item_index}].sources must be a list")


def _validate_review_recommendation(data: dict[str, Any]) -> None:
    _require_keys(data, ["risk_level", "action", "reason"], "impact_analysis.review_recommendation")
    if data["risk_level"] not in {"normal", "medium", "high", "critical"}:
        raise SchemaValidationError("impact_analysis.review_recommendation.risk_level is invalid")
    if data["action"] not in {"review_optional", "manual_review_recommended", "manual_review_required"}:
        raise SchemaValidationError("impact_analysis.review_recommendation.action is invalid")
