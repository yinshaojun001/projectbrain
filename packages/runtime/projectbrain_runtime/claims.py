"""Experience claim authoring helpers for the local runtime."""

from __future__ import annotations

import hashlib
from typing import Any


CLAIM_TYPES = ("HUMAN_REVIEW_REQUIRED", "HUMAN_CONFIRMED", "AI_INFERENCE", "FACT")
REVIEW_STATES = ("draft", "pending", "approved", "needs_review")
RISK_LEVELS = ("normal", "low", "medium", "high", "critical")


def build_experience_claim(
    *,
    existing_claims: list[dict[str, Any]],
    statement: str,
    applies_to: list[str] | str | None = None,
    risk_level: str = "normal",
    review_state: str = "draft",
    claim_type: str = "HUMAN_REVIEW_REQUIRED",
    confidence: float = 0.8,
    source: str | list[str] | None = None,
    claim_id: str | None = None,
) -> dict[str, Any]:
    normalized_statement = statement.strip()
    if not normalized_statement:
        raise ValueError("Claim statement is required")

    normalized_claim_type = _validate_choice("claim_type", claim_type, CLAIM_TYPES)
    normalized_review_state = _validate_choice("review_state", review_state, REVIEW_STATES)
    normalized_risk_level = _validate_choice("risk_level", risk_level, RISK_LEVELS)
    normalized_confidence = float(confidence)
    if normalized_confidence < 0 or normalized_confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    applies_to_tokens = _split_tokens(applies_to)
    source_tokens = _split_tokens(source)
    generated_id = claim_id.strip() if claim_id else _generate_claim_id(normalized_statement, existing_claims)
    if not generated_id:
        raise ValueError("claim id is required")
    if any(claim.get("id") == generated_id for claim in existing_claims):
        raise ValueError(f"Experience claim already exists: {generated_id}")

    return {
        "id": generated_id,
        "claim_type": normalized_claim_type,
        "review_state": normalized_review_state,
        "risk_level": normalized_risk_level,
        "applies_to": applies_to_tokens,
        "statement": normalized_statement,
        "confidence": normalized_confidence,
        "sources": source_tokens or [f"projectbrain://experience-claims/{generated_id}"],
    }


def _validate_choice(name: str, value: str, choices: tuple[str, ...]) -> str:
    normalized = value.strip()
    if normalized not in choices:
        raise ValueError(f"{name} must be one of: {', '.join(choices)}")
    return normalized


def _split_tokens(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    tokens = []
    for raw_value in raw_values:
        for part in str(raw_value).replace(",", ";").replace("<br>", ";").split(";"):
            token = part.strip()
            if token:
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def _generate_claim_id(statement: str, existing_claims: list[dict[str, Any]]) -> str:
    digest = hashlib.sha1(statement.encode("utf-8")).hexdigest()[:10]
    base = f"exp_{digest}"
    if not any(claim.get("id") == base for claim in existing_claims):
        return base
    suffix = 2
    while any(claim.get("id") == f"{base}_{suffix}" for claim in existing_claims):
        suffix += 1
    return f"{base}_{suffix}"
