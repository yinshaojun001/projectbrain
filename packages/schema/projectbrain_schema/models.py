"""Dataclass schema models for ProjectBrain V0.1 artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    source_type: str
    uri: str
    locator: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRef":
        return cls(
            source_type=data["source_type"],
            uri=data["uri"],
            locator=data.get("locator", {}),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeEntity:
    entity_type: str
    stable_key: str
    name: str
    qualified_name: str
    properties: dict[str, Any] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeEntity":
        return cls(
            entity_type=data["entity_type"],
            stable_key=data["stable_key"],
            name=data["name"],
            qualified_name=data["qualified_name"],
            properties=data.get("properties", {}),
            source_refs=data.get("source_refs", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeRelation:
    relation_type: str
    from_stable_key: str
    to_stable_key: str
    confidence: float
    properties: dict[str, Any] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeRelation":
        return cls(
            relation_type=data["relation_type"],
            from_stable_key=data["from_stable_key"],
            to_stable_key=data["to_stable_key"],
            confidence=float(data["confidence"]),
            properties=data.get("properties", {}),
            source_refs=data.get("source_refs", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperienceClaim:
    id: str
    claim_type: str
    review_state: str
    risk_level: str
    statement: str
    confidence: float
    applies_to: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperienceClaim":
        return cls(
            id=data["id"],
            claim_type=data["claim_type"],
            review_state=data["review_state"],
            risk_level=data["risk_level"],
            statement=data["statement"],
            confidence=float(data["confidence"]),
            applies_to=data.get("applies_to", []),
            sources=data.get("sources", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextPack:
    context_pack_id: str
    project_id: str
    task: str
    summary: str
    sections: list[dict[str, Any]]
    recommended_files: list[dict[str, Any]] = field(default_factory=list)
    recommended_symbols: list[dict[str, Any]] = field(default_factory=list)
    recommended_tests: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    omissions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextPack":
        return cls(
            context_pack_id=data["context_pack_id"],
            project_id=data["project_id"],
            task=data["task"],
            summary=data["summary"],
            sections=data["sections"],
            recommended_files=data.get("recommended_files", []),
            recommended_symbols=data.get("recommended_symbols", []),
            recommended_tests=data.get("recommended_tests", []),
            warnings=data.get("warnings", []),
            omissions=data.get("omissions", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactAnalysis:
    impact_analysis_id: str
    project_id: str
    task: str
    change: dict[str, Any]
    summary: str
    sections: list[dict[str, Any]]
    recommended_files: list[dict[str, Any]] = field(default_factory=list)
    recommended_tests: list[dict[str, Any]] = field(default_factory=list)
    review_recommendation: dict[str, Any] = field(default_factory=dict)
    omissions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImpactAnalysis":
        return cls(
            impact_analysis_id=data["impact_analysis_id"],
            project_id=data["project_id"],
            task=data["task"],
            change=data["change"],
            summary=data["summary"],
            sections=data["sections"],
            recommended_files=data.get("recommended_files", []),
            recommended_tests=data.get("recommended_tests", []),
            review_recommendation=data.get("review_recommendation", {}),
            omissions=data.get("omissions", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
