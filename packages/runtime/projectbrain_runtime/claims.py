"""Experience claim authoring and lifecycle helpers for the local runtime."""

from __future__ import annotations

import hashlib
from typing import Any

from projectbrain_runtime.models import now_iso


CLAIM_TYPES = ("HUMAN_REVIEW_REQUIRED", "HUMAN_CONFIRMED", "AI_INFERENCE", "FACT")
REVIEW_STATES = ("draft", "pending", "approved", "needs_review")
RISK_LEVELS = ("normal", "low", "medium", "high", "critical")
ARCHIVED_LIFECYCLE_STATE = "archived"


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


def active_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return claims that should participate in context and impact matching."""

    return [claim for claim in claims if not is_archived_claim(claim)]


def is_archived_claim(claim: dict[str, Any]) -> bool:
    return bool(claim.get("archived_at")) or claim.get("lifecycle_state") == ARCHIVED_LIFECYCLE_STATE


def update_experience_claim(
    claims: list[dict[str, Any]],
    *,
    claim_id: str,
    review_state: str | None = None,
    risk_level: str | None = None,
    claim_type: str | None = None,
    confidence: float | None = None,
    statement: str | None = None,
    applies_to: list[str] | str | None = None,
    source: str | list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Update review metadata for one experience claim."""

    updates: dict[str, Any] = {}
    if review_state is not None:
        updates["review_state"] = _validate_choice("review_state", review_state, REVIEW_STATES)
    if risk_level is not None:
        updates["risk_level"] = _validate_choice("risk_level", risk_level, RISK_LEVELS)
    if claim_type is not None:
        updates["claim_type"] = _validate_choice("claim_type", claim_type, CLAIM_TYPES)
    if confidence is not None:
        normalized_confidence = float(confidence)
        if normalized_confidence < 0 or normalized_confidence > 1:
            raise ValueError("confidence must be between 0 and 1")
        updates["confidence"] = normalized_confidence
    if statement is not None:
        normalized_statement = statement.strip()
        if not normalized_statement:
            raise ValueError("Claim statement is required")
        updates["statement"] = normalized_statement
    if applies_to is not None:
        updates["applies_to"] = _split_tokens(applies_to)
    if source is not None:
        updates["sources"] = _split_tokens(source)

    if not updates:
        raise ValueError("At least one claim update field is required")

    updated_claims, updated_claim = _replace_claim(
        claims,
        claim_id=claim_id,
        updates={
            **updates,
            "reviewed_at": now_iso(),
        },
    )
    return updated_claims, updated_claim


def archive_experience_claim(
    claims: list[dict[str, Any]],
    *,
    claim_id: str,
    reason: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Archive one claim while preserving it in storage."""

    archive_updates = {
        "lifecycle_state": ARCHIVED_LIFECYCLE_STATE,
        "archived_at": now_iso(),
    }
    normalized_reason = (reason or "").strip()
    if normalized_reason:
        archive_updates["archive_reason"] = normalized_reason
    return _replace_claim(claims, claim_id=claim_id, updates=archive_updates)


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


def _replace_claim(
    claims: list[dict[str, Any]],
    *,
    claim_id: str,
    updates: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_id = claim_id.strip()
    if not normalized_id:
        raise ValueError("claim id is required")

    updated_claims = []
    updated_claim: dict[str, Any] | None = None
    for claim in claims:
        if claim.get("id") != normalized_id:
            updated_claims.append(claim)
            continue
        updated_claim = {
            **claim,
            **updates,
        }
        updated_claims.append(updated_claim)

    if updated_claim is None:
        raise ValueError(f"Experience claim not found: {normalized_id}")
    return updated_claims, updated_claim
