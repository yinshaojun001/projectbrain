"""Parse Codex memory extraction output."""

from __future__ import annotations

import json
import re
from math import isfinite
from typing import Any

from projectbrain_runtime.brain.models import KNOWLEDGE_TYPES, REVIEW_STATES, RISK_LEVELS

DEFAULT_CONFIDENCE = 0.8
DEFAULT_REVIEW_STATE = "human_review_required"
DEFAULT_RISK_LEVEL = "normal"


def parse_extraction_output(output: str) -> dict[str, Any]:
    text = output.strip()
    candidates = _candidate_json_strings(text)
    errors = []
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            return _normalize_extraction(data)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
        except ValueError:
            raise
    raise ValueError("Could not parse extraction JSON: " + "; ".join(errors or ["no JSON object found"]))


def _candidate_json_strings(text: str) -> list[str]:
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    values = [block.strip() for block in blocks]
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        values.insert(0, text)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        values.append(text[first:last + 1])
    return values


def _normalize_extraction(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Extraction JSON must be an object")
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    normalized = []
    for item in candidates:
        normalized_item = _normalize_candidate(item)
        if normalized_item is None:
            continue
        normalized.append(normalized_item)
    return {"session_summary": _string_or_default(data.get("session_summary"), ""), "candidates": normalized}


def _normalize_candidate(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    knowledge_type = _required_scalar_string(item.get("type"))
    statement = _required_scalar_string(item.get("statement"))
    if knowledge_type is None or statement is None or knowledge_type not in KNOWLEDGE_TYPES:
        return None

    normalized_item: dict[str, Any] = {
        "type": knowledge_type,
        "statement": statement,
        "summary": _string_or_default(item.get("summary"), ""),
        "tags": _string_list(item.get("tags")),
        "applies_to": _string_list(item.get("applies_to")),
        "confidence": _confidence_or_default(item.get("confidence", DEFAULT_CONFIDENCE)),
        "risk_level": _risk_level_or_default(item.get("risk_level")),
        "review_state": _review_state_or_default(item.get("review_state")),
        "evidence": [{
            "type": "conversation_summary",
            "summary": _string_or_default(item.get("evidence_summary"), "Extracted from codex-brain session."),
        }],
    }
    title = _optional_string(item.get("title"))
    if title is not None:
        normalized_item["title"] = title
    return normalized_item


def _required_scalar_string(value: Any) -> str | None:
    if _is_container(value) or value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _string_or_default(value: Any, default: str) -> str:
    if _is_container(value) or value is None:
        return default
    return str(value).strip()


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in raw_values if not _is_container(item) and str(item).strip()]


def _confidence_or_default(value: Any) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return DEFAULT_CONFIDENCE
    if not isfinite(normalized) or normalized < 0 or normalized > 1:
        return DEFAULT_CONFIDENCE
    return normalized


def _risk_level_or_default(value: Any) -> str:
    normalized = _required_scalar_string(value)
    if normalized in RISK_LEVELS:
        return normalized
    return DEFAULT_RISK_LEVEL


def _review_state_or_default(value: Any) -> str:
    normalized = _required_scalar_string(value)
    if normalized in REVIEW_STATES:
        return normalized
    return DEFAULT_REVIEW_STATE


def _is_container(value: Any) -> bool:
    return isinstance(value, (dict, list, tuple, set))
