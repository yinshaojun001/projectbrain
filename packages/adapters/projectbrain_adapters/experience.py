"""Load and match lightweight ProjectBrain experience seed claims."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def load_experience_seed(path: str | Path | None) -> list[dict[str, Any]]:
    """Load experience claims from a markdown table.

    The first markdown table with an ``id`` and ``statement`` column is treated
    as the seed table. This keeps the pilot editable without adding YAML or DB
    dependencies.
    """

    if not path:
        return []
    seed_path = Path(path)
    if not seed_path.exists():
        raise FileNotFoundError(f"Experience seed not found: {seed_path}")
    lines = seed_path.read_text(encoding="utf-8").splitlines()
    rows = _parse_markdown_table(lines)
    claims = []
    for row in rows:
        claim_id = row.get("id", "").strip()
        statement = row.get("statement", "").strip()
        if not claim_id or not statement:
            continue
        claims.append(
            {
                "id": claim_id,
                "claim_type": row.get("claim_type", "HUMAN_REVIEW_REQUIRED").strip()
                or "HUMAN_REVIEW_REQUIRED",
                "review_state": row.get("review_state", "pending").strip() or "pending",
                "risk_level": row.get("risk_level", "normal").strip() or "normal",
                "applies_to": _split_tokens(row.get("applies_to", "")),
                "statement": statement,
                "confidence": _parse_float(row.get("confidence", ""), default=0.8),
                "sources": [
                    f"experience-seed://{seed_path.name}#{claim_id}",
                    *[source for source in _split_tokens(row.get("source", "")) if source],
                ],
            }
        )
    return claims


def match_experience_claims(
    claims: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    entity_text: Callable[[dict[str, Any]], str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Return seed claims that match the selected entity scope."""

    entity_texts = [(entity, entity_text(entity).lower()) for entity in entities]
    matched_claims = []
    for claim in claims:
        applies_to = [token.lower() for token in claim.get("applies_to", []) if token]
        matched_entities = []
        if applies_to:
            for entity, text in entity_texts:
                if any(token in text for token in applies_to):
                    matched_entities.append(entity)
        else:
            matched_entities = [entity for entity, _text in entity_texts]

        if not matched_entities and applies_to:
            continue

        matched_claim = dict(claim)
        matched_claim["matched_entity_count"] = len(matched_entities)
        matched_claim["matched_sources"] = _entity_sources(matched_entities[:3])
        matched_claims.append(matched_claim)

    matched_claims.sort(
        key=lambda claim: (
            claim.get("review_state") != "approved",
            claim.get("risk_level") not in {"critical", "high"},
            -claim.get("matched_entity_count", 0),
            claim.get("id", ""),
        )
    )
    return matched_claims[:limit]


def has_human_confirmed_claim(claims: list[dict[str, Any]]) -> bool:
    return any(
        claim.get("claim_type") == "HUMAN_CONFIRMED" or claim.get("review_state") == "approved"
        for claim in claims
    )


def _parse_markdown_table(lines: list[str]) -> list[dict[str, str]]:
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        if "|" not in line:
            if header and rows:
                break
            continue
        cells = _split_row(line)
        if not cells:
            continue
        normalized = [_normalize_header(cell) for cell in cells]
        if "id" in normalized and "statement" in normalized:
            header = normalized
            continue
        if header and _is_separator(cells):
            continue
        if header:
            padded = [*cells, *([""] * (len(header) - len(cells)))]
            rows.append({key: value.strip() for key, value in zip(header, padded)})
    return rows


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _is_separator(cells: list[str]) -> bool:
    return all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in cells)


def _split_tokens(value: str) -> list[str]:
    return [part.strip() for part in value.replace("<br>", ";").split(";") if part.strip()]


def _parse_float(value: str, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _entity_sources(entities: list[dict[str, Any]]) -> list[str]:
    refs = []
    for entity in entities:
        refs.extend(entity.get("source_refs", []))
    return refs
