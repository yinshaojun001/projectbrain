"""Build a first ProjectBrain context pack from CodeGraph adapter exports."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from projectbrain_adapters.experience import has_human_confirmed_claim, match_experience_claims


HIGH_RISK_TERMS = (
    "refund",
    "settle",
    "settlement",
    "bill",
    "compensate",
    "callback",
    "payment",
    "audit",
    "account",
    "register",
)

BUSINESS_CONCEPT_PATTERNS = {
    "Settlement Flow": (("settle", "settlement"),),
    "Payment Flow": (("payment",),),
    "Refund Flow": (("refund",),),
    "Callback Flow": (("callback", "notify", "notification"),),
    "Registration Flow": (("register", "registration"),),
    "Third-Party Interaction": (("thirdparty", "third-party", "tripartite"), ("interaction",)),
    "Compensation": (("compensate", "compensation"),),
    "Async Messaging": (("async", "message", "producer", "consumer"),),
    "Settlement Notification": (("settle", "settlement"), ("notify",)),
}


@dataclass(frozen=True)
class ContextPackBuilder:
    """Create task-scoped context from ProjectBrain-shaped code facts."""

    task: str
    export: dict[str, Any]
    experience_claims: list[dict[str, Any]] | None = None
    max_items_per_section: int = 12

    def build(self) -> dict[str, Any]:
        entities = self.export.get("entities", [])
        relations = self.export.get("relations", [])
        sources = self.export.get("sources", [])
        entity_by_key = {entity["stable_key"]: entity for entity in entities}

        related_entities = self._rank_entities(entities, relations)
        relation_sections = self._relation_sections(relations, entity_by_key)
        source_by_uri = {source["uri"]: source for source in sources}
        matched_experience_claims = match_experience_claims(
            self.experience_claims or [],
            related_entities,
            self._entity_text,
            limit=self.max_items_per_section,
        )

        return {
            "context_pack_id": self._context_pack_id(),
            "project_id": self.export.get("project_id"),
            "task": self.task,
            "summary": self._summary(entities, relations),
            "sections": [
                self._project_overview(entities, relations, sources),
                self._module_overview(entities),
                self._important_entities(related_entities),
                relation_sections["entrypoint_flows"],
                relation_sections["dependency_facts"],
                self._experience_claims(matched_experience_claims),
                self._candidate_business_concepts(related_entities),
                self._risk_hypotheses(related_entities, relations, matched_experience_claims),
                self._unknowns(),
            ],
            "recommended_files": self._recommended_files(related_entities, source_by_uri),
            "recommended_symbols": self._recommended_symbols(related_entities),
            "recommended_tests": self._recommended_tests(related_entities),
            "warnings": self._warnings(sources, matched_experience_claims),
            "omissions": self._omissions(),
        }

    def _context_pack_id(self) -> str:
        project_id = self.export.get("project_id", "unknown")
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in self.task).strip("-")
        slug = "-".join(part for part in slug.split("-") if part)[:48] or "context"
        return f"ctx_{project_id}_{slug}"

    def _summary(self, entities: list[dict[str, Any]], relations: list[dict[str, Any]]) -> str:
        modules = sorted({entity.get("properties", {}).get("module") for entity in entities if entity.get("properties", {}).get("module")})
        kinds = Counter(entity["entity_type"] for entity in entities)
        relation_types = Counter(relation["relation_type"] for relation in relations)
        return (
            f"Context pack built from {len(entities)} CodeGraph entities and {len(relations)} relations"
            f" across modules {', '.join(modules) if modules else 'unknown'}."
            f" Dominant entity types: {self._format_counter(kinds)}."
            f" Dominant relation types: {self._format_counter(relation_types)}."
        )

    def _project_overview(
        self,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        languages = sorted(
            {
                entity.get("properties", {}).get("language")
                for entity in entities
                if entity.get("properties", {}).get("language")
            }
        )
        return {
            "type": "project_overview",
            "items": [
                {
                    "statement": "The pack is generated from CodeGraph code-location facts, not human-confirmed business knowledge.",
                    "confidence": 1.0,
                    "sources": self._first_source_refs(sources),
                },
                {
                    "statement": (
                        f"Selected scope contains {len(entities)} entities, {len(relations)} relations, "
                        f"{len(sources)} source locations, and languages {', '.join(languages) if languages else 'unknown'}."
                    ),
                    "confidence": 1.0,
                    "sources": self._first_source_refs(sources),
                },
            ],
        }

    def _module_overview(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, Counter[str]] = defaultdict(Counter)
        for entity in entities:
            module = entity.get("properties", {}).get("module") or "unknown"
            counts[module][entity["entity_type"]] += 1
        items = []
        for module, counter in sorted(counts.items(), key=lambda item: (-sum(item[1].values()), item[0])):
            items.append(
                {
                    "module": module,
                    "entity_count": sum(counter.values()),
                    "entity_types": dict(counter.most_common()),
                    "confidence": 1.0,
                }
            )
        return {"type": "modules", "items": items}

    def _important_entities(self, ranked_entities: list[dict[str, Any]]) -> dict[str, Any]:
        items = []
        for entity in ranked_entities[: self.max_items_per_section]:
            props = entity.get("properties", {})
            items.append(
                {
                    "entity_type": entity["entity_type"],
                    "name": entity["name"],
                    "qualified_name": entity["qualified_name"],
                    "file": props.get("file_path"),
                    "signature": props.get("signature"),
                    "score": entity["_context_score"],
                    "confidence": 1.0,
                    "sources": entity.get("source_refs", []),
                }
            )
        return {"type": "important_entities", "items": items}

    def _relation_sections(
        self,
        relations: list[dict[str, Any]],
        entity_by_key: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        call_items = []
        dependency_items = []
        for relation in relations:
            from_entity = entity_by_key.get(relation["from_stable_key"])
            to_entity = entity_by_key.get(relation["to_stable_key"])
            item = {
                "relation_type": relation["relation_type"],
                "from": self._entity_label(from_entity, relation["from_stable_key"]),
                "to": self._entity_label(to_entity, relation["to_stable_key"]),
                "confidence": relation.get("confidence", 0.8),
                "properties": relation.get("properties", {}),
                "sources": relation.get("source_refs", []),
            }
            if relation["relation_type"] == "CALLS":
                call_items.append(item)
            elif relation["relation_type"] in {"IMPLEMENTS_INTERFACE", "IMPORTS", "REFERENCES", "INSTANTIATES", "EXTENDS"}:
                dependency_items.append(item)

        call_items.sort(key=lambda item: (-item["confidence"], item["from"], item["to"]))
        dependency_items.sort(key=lambda item: (item["relation_type"], item["from"], item["to"]))
        return {
            "entrypoint_flows": {
                "type": "entrypoint_flows",
                "items": call_items[: self.max_items_per_section],
            },
            "dependency_facts": {
                "type": "dependency_facts",
                "items": dependency_items[: self.max_items_per_section],
            },
        }

    def _candidate_business_concepts(self, ranked_entities: list[dict[str, Any]]) -> dict[str, Any]:
        evidence_texts = [self._entity_text(entity).lower() for entity in ranked_entities]
        items = []
        for concept, patterns in BUSINESS_CONCEPT_PATTERNS.items():
            matched = [
                entity
                for entity in ranked_entities
                if self._matches_concept(self._entity_text(entity).lower(), patterns)
            ]
            if matched:
                items.append(
                    {
                        "concept": concept,
                        "claim_type": "AI_INFERENCE",
                        "statement": f"{concept} appears relevant because selected code symbols or paths match its naming pattern.",
                        "confidence": min(0.35 + 0.08 * len(matched), 0.75),
                        "evidence_count": len(matched),
                        "sources": self._entity_sources(matched[:3]),
                    }
                )
        if not items and evidence_texts:
            items.append(
                {
                    "concept": "Unclassified Payment Context",
                    "claim_type": "AI_INFERENCE",
                    "statement": "Selected symbols are code facts only; no stable business concept could be inferred from names.",
                    "confidence": 0.3,
                    "evidence_count": len(evidence_texts),
                    "sources": self._entity_sources(ranked_entities[:3]),
                }
            )
        items.sort(key=lambda item: (-item["confidence"], item["concept"]))
        return {"type": "candidate_business_concepts", "items": items[: self.max_items_per_section]}

    def _risk_hypotheses(
        self,
        ranked_entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        experience_claims: list[dict[str, Any]],
    ) -> dict[str, Any]:
        high_risk_entities = [
            entity
            for entity in ranked_entities
            if any(term in self._entity_text(entity).lower() for term in HIGH_RISK_TERMS)
        ]
        call_count = sum(1 for relation in relations if relation["relation_type"] == "CALLS")
        items = []
        if high_risk_entities:
            items.append(
                {
                    "claim_type": "AI_INFERENCE",
                    "statement": "Selected scope touches payment/settlement/refund-like names; changes should be reviewed for external API, accounting, callback, and reconciliation effects.",
                    "confidence": 0.65,
                    "sources": self._entity_sources(high_risk_entities[:5]),
                }
            )
        if call_count:
            items.append(
                {
                    "claim_type": "FACT",
                    "statement": f"CodeGraph reports {call_count} CALLS relations in this selected scope.",
                    "confidence": 1.0,
                    "sources": self._first_relation_refs(relations),
                }
            )
        if has_human_confirmed_claim(experience_claims):
            items.append(
                {
                    "claim_type": "FACT",
                    "statement": "At least one approved or HUMAN_CONFIRMED experience claim is loaded for this scope.",
                    "confidence": 1.0,
                    "sources": self._claim_sources(experience_claims),
                }
            )
        else:
            items.append(
                {
                    "claim_type": "AI_INFERENCE",
                    "statement": "No HUMAN_CONFIRMED operational constraints are loaded yet; do not treat inferred business concepts as policy.",
                    "confidence": 1.0,
                    "sources": [],
                }
            )
        return {"type": "risk_hypotheses", "items": items}

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
                "Which payment-domain invariants are human-confirmed, such as amount units, immutable records, or callback compatibility?",
                "Which external consumers depend on the selected service contracts?",
                "Which integration or regression tests are authoritative for the selected business flow?",
                "Which configuration values are sensitive and must remain excluded from memory chunks?",
            ],
        }

    def _recommended_files(
        self,
        ranked_entities: list[dict[str, Any]],
        source_by_uri: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen = set()
        files = []
        for entity in ranked_entities:
            file_path = entity.get("properties", {}).get("file_path")
            if not file_path or file_path in seen:
                continue
            seen.add(file_path)
            sources = [
                source_by_uri[source_ref]
                for source_ref in entity.get("source_refs", [])
                if source_ref in source_by_uri
            ]
            files.append(
                {
                    "file": file_path,
                    "reason": f"Contains selected {entity['entity_type']} {entity['name']}.",
                    "sources": sources[:1],
                }
            )
            if len(files) >= self.max_items_per_section:
                break
        return files

    def _recommended_symbols(self, ranked_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        symbols = []
        for entity in ranked_entities[: self.max_items_per_section]:
            symbols.append(
                {
                    "qualified_name": entity["qualified_name"],
                    "entity_type": entity["entity_type"],
                    "file": entity.get("properties", {}).get("file_path"),
                    "sources": entity.get("source_refs", []),
                }
            )
        return symbols

    def _recommended_tests(self, ranked_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        test_candidates = [
            entity
            for entity in ranked_entities
            if "/test/" in (entity.get("properties", {}).get("file_path") or "")
            or entity["name"].lower().startswith("test")
            or "test" in entity["qualified_name"].lower()
        ]
        return [
            {
                "qualified_name": entity["qualified_name"],
                "file": entity.get("properties", {}).get("file_path"),
                "reason": "CodeGraph export contains this test-like symbol in the selected scope.",
                "sources": entity.get("source_refs", []),
            }
            for entity in test_candidates[: self.max_items_per_section]
        ]

    def _warnings(self, sources: list[dict[str, Any]], experience_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
        warnings = []
        if not has_human_confirmed_claim(experience_claims):
            warnings.append(
                {
                    "code": "no_human_confirmed_claims",
                    "message": "This context pack contains no approved HUMAN_CONFIRMED constraints for the selected scope.",
                }
            )
        sensitive_paths = [
            source
            for source in sources
            if any(
                token in (source.get("locator", {}).get("file") or "").lower()
                for token in ("key", "secret", "password", "config_online", "config_sandbox", "config_stable")
            )
        ]
        if sensitive_paths:
            warnings.append(
                {
                    "code": "sensitive_config_scope",
                    "message": "Selected sources include sensitive-looking config paths; do not persist secret values in ProjectBrain memory.",
                    "sources": sensitive_paths[:3],
                }
            )
        return warnings

    def _omissions(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "no_runtime_data",
                "message": "Runtime traffic, database schema, incidents, and human experience are not loaded in this V0.1 pack.",
            },
            {
                "code": "bounded_export",
                "message": "The pack is limited by the export scope and node/edge limits used before generation.",
            },
        ]

    def _rank_entities(
        self,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        task_terms = [term for term in self._tokenize(self.task) if len(term) > 2]
        degree = Counter()
        for relation in relations:
            degree[relation["from_stable_key"]] += 1
            degree[relation["to_stable_key"]] += 1

        ranked = []
        for entity in entities:
            text = self._entity_text(entity).lower()
            score = degree[entity["stable_key"]]
            score += sum(5 for term in task_terms if term in text)
            if entity["entity_type"] in {"Interface", "Class", "API"}:
                score += 4
            elif entity["entity_type"] == "Method":
                score += 2
            if any(term in text for term in HIGH_RISK_TERMS):
                score += 3
            ranked_entity = dict(entity)
            ranked_entity["_context_score"] = score
            ranked.append(ranked_entity)
        ranked.sort(key=lambda entity: (-entity["_context_score"], entity["entity_type"], entity["qualified_name"]))
        return ranked

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

    def _first_source_refs(self, sources: list[dict[str, Any]]) -> list[str]:
        return [source["uri"] for source in sources[:3] if source.get("uri")]

    def _first_relation_refs(self, relations: list[dict[str, Any]]) -> list[str]:
        refs = []
        for relation in relations:
            refs.extend(relation.get("source_refs", []))
            if len(refs) >= 3:
                break
        return refs[:3]

    def _claim_sources(self, claims: list[dict[str, Any]]) -> list[str]:
        refs = []
        for claim in claims:
            refs.extend(claim.get("sources", []))
            if len(refs) >= 3:
                break
        return refs[:3]

    def _format_counter(self, counter: Counter[str]) -> str:
        return ", ".join(f"{name}={count}" for name, count in counter.most_common(4)) or "none"

    def _tokenize(self, text: str) -> list[str]:
        token = []
        tokens = []
        for char in text.lower():
            if char.isalnum():
                token.append(char)
            elif token:
                tokens.append("".join(token))
                token = []
        if token:
            tokens.append("".join(token))
        return tokens

    def _matches_concept(self, text: str, patterns: tuple[tuple[str, ...], ...]) -> bool:
        return all(any(term in text for term in alternatives) for alternatives in patterns)
