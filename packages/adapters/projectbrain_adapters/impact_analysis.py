"""Build a minimal ProjectBrain impact analysis from CodeGraph adapter exports."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from projectbrain_adapters.context_pack import BUSINESS_CONCEPT_PATTERNS, HIGH_RISK_TERMS
from projectbrain_adapters.experience import has_human_confirmed_claim, match_experience_claims


DEPENDENCY_RELATIONS = {"IMPLEMENTS_INTERFACE", "IMPORTS", "REFERENCES", "INSTANTIATES", "EXTENDS"}


@dataclass(frozen=True)
class ImpactAnalysisBuilder:
    """Analyze changed files/symbols against exported CodeGraph facts."""

    task: str
    export: dict[str, Any]
    changed_files: list[str]
    changed_symbols: list[str]
    experience_claims: list[dict[str, Any]] | None = None
    max_items_per_section: int = 12

    def build(self) -> dict[str, Any]:
        entities = self.export.get("entities", [])
        relations = self.export.get("relations", [])
        entity_by_key = {entity["stable_key"]: entity for entity in entities}
        changed_entities = self._changed_entities(entities)
        changed_keys = {entity["stable_key"] for entity in changed_entities}
        affected_relations = self._affected_relations(relations, changed_keys)
        affected_entities = self._affected_entities(affected_relations, changed_keys, entity_by_key)
        risk_entities = [*changed_entities, *[item["entity"] for item in affected_entities if item.get("entity")]]
        matched_experience_claims = match_experience_claims(
            self.experience_claims or [],
            risk_entities,
            self._entity_text,
            limit=self.max_items_per_section,
        )

        return {
            "impact_analysis_id": self._impact_analysis_id(),
            "project_id": self.export.get("project_id"),
            "task": self.task,
            "change": {
                "changed_files": self.changed_files,
                "changed_symbols": self.changed_symbols,
            },
            "summary": self._summary(changed_entities, affected_entities, affected_relations),
            "sections": [
                self._changed_entities_section(changed_entities),
                self._affected_relations_section("affected_calls", affected_relations, {"CALLS"}, entity_by_key),
                self._affected_relations_section("affected_dependencies", affected_relations, DEPENDENCY_RELATIONS, entity_by_key),
                self._affected_entities_section(affected_entities),
                self._candidate_business_concepts(risk_entities),
                self._experience_claims(matched_experience_claims),
                self._risk_warnings(risk_entities, affected_relations, matched_experience_claims),
                self._unknowns(),
            ],
            "recommended_files": self._recommended_files(changed_entities, affected_entities),
            "recommended_tests": self._recommended_tests(changed_entities, affected_entities, affected_relations),
            "review_recommendation": self._review_recommendation(risk_entities, affected_relations, matched_experience_claims),
            "omissions": self._omissions(),
        }

    def _impact_analysis_id(self) -> str:
        project_id = self.export.get("project_id", "unknown")
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in self.task).strip("-")
        slug = "-".join(part for part in slug.split("-") if part)[:48] or "impact"
        return f"impact_{project_id}_{slug}"

    def _changed_entities(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        changed_files = [self._normalize_path(path) for path in self.changed_files]
        changed_symbols = [symbol.lower() for symbol in self.changed_symbols]
        matched = []
        for entity in entities:
            file_path = self._normalize_path(entity.get("properties", {}).get("file_path") or "")
            qualified_name = entity.get("qualified_name", "").lower()
            name = entity.get("name", "").lower()
            file_match = any(file_path == changed_file or file_path.endswith(changed_file) for changed_file in changed_files)
            symbol_match = any(symbol in qualified_name or symbol == name for symbol in changed_symbols)
            if file_match or symbol_match or (not changed_files and not changed_symbols):
                matched.append(dict(entity))
        matched.sort(key=lambda entity: (entity.get("properties", {}).get("file_path") or "", entity["qualified_name"]))
        return matched

    def _affected_relations(
        self,
        relations: list[dict[str, Any]],
        changed_keys: set[str],
    ) -> list[dict[str, Any]]:
        affected = []
        for relation in relations:
            from_changed = relation["from_stable_key"] in changed_keys
            to_changed = relation["to_stable_key"] in changed_keys
            if not from_changed and not to_changed:
                continue
            item = dict(relation)
            if from_changed and to_changed:
                item["_direction"] = "internal"
            elif from_changed:
                item["_direction"] = "outgoing"
            else:
                item["_direction"] = "incoming"
            affected.append(item)
        affected.sort(
            key=lambda relation: (
                relation["relation_type"] != "CALLS",
                relation.get("_direction", ""),
                relation["from_stable_key"],
                relation["to_stable_key"],
            )
        )
        return affected

    def _affected_entities(
        self,
        affected_relations: list[dict[str, Any]],
        changed_keys: set[str],
        entity_by_key: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        directions: dict[str, set[str]] = {}
        relation_types: dict[str, set[str]] = {}
        for relation in affected_relations:
            for key in (relation["from_stable_key"], relation["to_stable_key"]):
                if key in changed_keys:
                    continue
                counts[key] += 1
                directions.setdefault(key, set()).add(relation["_direction"])
                relation_types.setdefault(key, set()).add(relation["relation_type"])

        items = []
        for key, count in counts.most_common(self.max_items_per_section):
            entity = entity_by_key.get(key)
            items.append(
                {
                    "stable_key": key,
                    "entity": entity,
                    "label": self._entity_label(entity, key),
                    "relation_count": count,
                    "directions": sorted(directions.get(key, set())),
                    "relation_types": sorted(relation_types.get(key, set())),
                    "sources": entity.get("source_refs", []) if entity else [],
                }
            )
        return items

    def _summary(
        self,
        changed_entities: list[dict[str, Any]],
        affected_entities: list[dict[str, Any]],
        affected_relations: list[dict[str, Any]],
    ) -> str:
        relation_counts = Counter(relation["relation_type"] for relation in affected_relations)
        return (
            f"Impact analysis matched {len(changed_entities)} changed entities, "
            f"{len(affected_entities)} affected neighbor entities, and {len(affected_relations)} touching relations. "
            f"Relation mix: {self._format_counter(relation_counts)}."
        )

    def _changed_entities_section(self, changed_entities: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "changed_entities",
            "items": [
                {
                    "entity_type": entity["entity_type"],
                    "name": entity["name"],
                    "qualified_name": entity["qualified_name"],
                    "file": entity.get("properties", {}).get("file_path"),
                    "signature": entity.get("properties", {}).get("signature"),
                    "confidence": 1.0,
                    "sources": entity.get("source_refs", []),
                }
                for entity in changed_entities[: self.max_items_per_section]
            ],
        }

    def _affected_relations_section(
        self,
        section_type: str,
        affected_relations: list[dict[str, Any]],
        relation_types: set[str],
        entity_by_key: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        items = []
        for relation in affected_relations:
            if relation["relation_type"] not in relation_types:
                continue
            from_entity = entity_by_key.get(relation["from_stable_key"])
            to_entity = entity_by_key.get(relation["to_stable_key"])
            items.append(
                {
                    "relation_type": relation["relation_type"],
                    "direction": relation["_direction"],
                    "from": self._entity_label(from_entity, relation["from_stable_key"]),
                    "to": self._entity_label(to_entity, relation["to_stable_key"]),
                    "confidence": relation.get("confidence", 0.8),
                    "properties": relation.get("properties", {}),
                    "sources": relation.get("source_refs", []),
                }
            )
            if len(items) >= self.max_items_per_section:
                break
        return {"type": section_type, "items": items}

    def _affected_entities_section(self, affected_entities: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "affected_entities",
            "items": [
                {
                    "stable_key": item["stable_key"],
                    "label": item["label"],
                    "relation_count": item["relation_count"],
                    "directions": item["directions"],
                    "relation_types": item["relation_types"],
                    "sources": item["sources"],
                }
                for item in affected_entities[: self.max_items_per_section]
            ],
        }

    def _candidate_business_concepts(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        items = []
        for concept, patterns in BUSINESS_CONCEPT_PATTERNS.items():
            matched = [
                entity
                for entity in entities
                if self._matches_concept(self._entity_text(entity).lower(), patterns)
            ]
            if matched:
                items.append(
                    {
                        "concept": concept,
                        "claim_type": "AI_INFERENCE",
                        "statement": f"{concept} may be affected because changed or neighboring symbols match its naming pattern.",
                        "confidence": min(0.35 + 0.08 * len(matched), 0.75),
                        "evidence_count": len(matched),
                        "sources": self._entity_sources(matched[:3]),
                    }
                )
        items.sort(key=lambda item: (-item["confidence"], item["concept"]))
        return {"type": "affected_candidate_business_concepts", "items": items[: self.max_items_per_section]}

    def _risk_warnings(
        self,
        entities: list[dict[str, Any]],
        affected_relations: list[dict[str, Any]],
        experience_claims: list[dict[str, Any]],
    ) -> dict[str, Any]:
        items = []
        high_risk_entities = [
            entity
            for entity in entities
            if any(term in self._entity_text(entity).lower() for term in HIGH_RISK_TERMS)
        ]
        if high_risk_entities:
            items.append(
                {
                    "code": "payment_domain_change",
                    "claim_type": "AI_INFERENCE",
                    "statement": "Changed or neighboring symbols use payment-domain names; review external API behavior, callback compatibility, accounting, and reconciliation assumptions.",
                    "confidence": 0.65,
                    "sources": self._entity_sources(high_risk_entities[:5]),
                }
            )
        incoming_call_count = sum(
            1
            for relation in affected_relations
            if relation["relation_type"] == "CALLS" and relation["_direction"] == "incoming"
        )
        if incoming_call_count:
            items.append(
                {
                    "code": "incoming_callers",
                    "claim_type": "FACT",
                    "statement": f"CodeGraph reports {incoming_call_count} incoming CALLS relations into changed entities.",
                    "confidence": 1.0,
                    "sources": self._relation_sources(affected_relations),
                }
            )
        if not items:
            items.append(
                {
                    "code": "bounded_fact_only",
                    "claim_type": "FACT",
                    "statement": "No high-risk naming pattern was detected in the bounded export.",
                    "confidence": 1.0,
                    "sources": self._relation_sources(affected_relations),
                }
            )
        if not has_human_confirmed_claim(experience_claims):
            items.append(
                {
                    "code": "no_human_confirmed_claims",
                    "claim_type": "AI_INFERENCE",
                    "statement": "No HUMAN_CONFIRMED constraints are loaded; impact severity is based only on names and CodeGraph relations.",
                    "confidence": 1.0,
                    "sources": [],
                }
            )
        return {"type": "risk_warnings", "items": items}

    def _experience_claims(self, claims: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "experience_claims",
            "items": [
                {
                    "id": claim["id"],
                    "claim_type": claim["claim_type"],
                    "review_state": claim["review_state"],
                    "risk_level": claim["risk_level"],
                    "statement": claim["statement"],
                    "confidence": claim["confidence"],
                    "matched_entity_count": claim["matched_entity_count"],
                    "sources": [*claim.get("sources", []), *claim.get("matched_sources", [])],
                }
                for claim in claims
            ],
        }

    def _unknowns(self) -> dict[str, Any]:
        return {
            "type": "unknowns_for_human_review",
            "items": [
                "Do changed service contracts have external consumers or compatibility commitments?",
                "Are affected async messages idempotent and backward-compatible?",
                "Which integration tests or sandbox callbacks validate this flow?",
                "Are any database tables, amount units, or audit requirements involved outside this CodeGraph export?",
            ],
        }

    def _recommended_files(
        self,
        changed_entities: list[dict[str, Any]],
        affected_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen = set()
        files = []
        for entity in [*changed_entities, *[item["entity"] for item in affected_entities if item.get("entity")]]:
            file_path = entity.get("properties", {}).get("file_path")
            if not file_path or file_path in seen:
                continue
            seen.add(file_path)
            files.append(
                {
                    "file": file_path,
                    "reason": f"Review because {entity['entity_type']} {entity['name']} is changed or adjacent to changed code.",
                    "sources": entity.get("source_refs", []),
                }
            )
            if len(files) >= self.max_items_per_section:
                break
        return files

    def _recommended_tests(
        self,
        changed_entities: list[dict[str, Any]],
        affected_entities: list[dict[str, Any]],
        affected_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        test_entities = [
            entity
            for entity in [*changed_entities, *[item["entity"] for item in affected_entities if item.get("entity")]]
            if self._is_test_like(entity)
        ]
        items = [
            {
                "qualified_name": entity["qualified_name"],
                "file": entity.get("properties", {}).get("file_path"),
                "reason": "Test-like entity appears in changed or affected scope.",
                "sources": entity.get("source_refs", []),
            }
            for entity in test_entities[: self.max_items_per_section]
        ]
        if items:
            return items

        test_relation_keys = []
        for relation in affected_relations:
            for key in (relation["from_stable_key"], relation["to_stable_key"]):
                if "test" in key.lower():
                    test_relation_keys.append(key)
        return [
            {
                "qualified_name": key,
                "file": None,
                "reason": "CodeGraph relation references a test-like symbol outside the exported entity set.",
                "sources": [],
            }
            for key in dict.fromkeys(test_relation_keys).keys()
        ][: self.max_items_per_section]

    def _review_recommendation(
        self,
        entities: list[dict[str, Any]],
        affected_relations: list[dict[str, Any]],
        experience_claims: list[dict[str, Any]],
    ) -> dict[str, Any]:
        high_risk = any(any(term in self._entity_text(entity).lower() for term in HIGH_RISK_TERMS) for entity in entities)
        incoming_calls = any(
            relation["relation_type"] == "CALLS" and relation["_direction"] == "incoming"
            for relation in affected_relations
        )
        confirmed_high_risk = any(
            claim.get("review_state") == "approved" and claim.get("risk_level") in {"critical", "high"}
            for claim in experience_claims
        )
        if confirmed_high_risk:
            level = "critical"
            action = "manual_review_required"
        elif high_risk and incoming_calls:
            level = "high"
            action = "manual_review_required"
        elif high_risk:
            level = "medium"
            action = "manual_review_recommended"
        else:
            level = "normal"
            action = "review_optional"
        return {
            "risk_level": level,
            "action": action,
            "reason": "Based on payment-domain naming, incoming callers, and matched experience constraints.",
        }

    def _omissions(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "bounded_export",
                "message": "Only relations present in the selected CodeGraph export can be analyzed.",
            },
            {
                "code": "no_diff_parser",
                "message": "This MVP uses changed files/symbols as input; it does not parse git diff hunks yet.",
            },
            {
                "code": "no_human_experience",
                "message": "Human-confirmed constraints, incidents, and ownership data are not loaded yet.",
            },
        ]

    def _normalize_path(self, path: str) -> str:
        return path.strip().replace("\\", "/")

    def _entity_text(self, entity: dict[str, Any]) -> str:
        props = entity.get("properties", {})
        return " ".join(
            str(value)
            for value in (
                entity.get("name"),
                entity.get("qualified_name"),
                props.get("file_path"),
                props.get("signature"),
                props.get("module"),
            )
            if value
        )

    def _entity_label(self, entity: dict[str, Any] | None, fallback: str) -> str:
        if not entity:
            return fallback
        return f"{entity['entity_type']}:{entity['qualified_name']}"

    def _entity_sources(self, entities: list[dict[str, Any]]) -> list[str]:
        refs = []
        for entity in entities:
            refs.extend(entity.get("source_refs", []))
        return refs

    def _relation_sources(self, relations: list[dict[str, Any]]) -> list[str]:
        refs = []
        for relation in relations:
            refs.extend(relation.get("source_refs", []))
            if len(refs) >= 5:
                break
        return refs[:5]

    def _matches_concept(self, text: str, patterns: tuple[tuple[str, ...], ...]) -> bool:
        return all(any(term in text for term in alternatives) for alternatives in patterns)

    def _is_test_like(self, entity: dict[str, Any]) -> bool:
        file_path = entity.get("properties", {}).get("file_path") or ""
        return "/test/" in file_path or entity["name"].lower().startswith("test") or "test" in entity["qualified_name"].lower()

    def _format_counter(self, counter: Counter[str]) -> str:
        return ", ".join(f"{name}={count}" for name, count in counter.most_common(4)) or "none"
