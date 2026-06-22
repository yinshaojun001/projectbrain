"""Parse Codex memory extraction output."""

from __future__ import annotations

import json
import re
from typing import Any


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
    raise ValueError("Could not parse extraction JSON: " + "; ".join(errors or ["no JSON object found"]))


def _candidate_json_strings(text: str) -> list[str]:
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    values = [block.strip() for block in blocks]
    if text.startswith("{") and text.endswith("}"):
        values.insert(0, text)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        values.append(text[first:last + 1])
    return values


def _normalize_extraction(data: dict[str, Any]) -> dict[str, Any]:
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    normalized = []
    for item in candidates:
        if not isinstance(item, dict) or not item.get("type") or not item.get("statement"):
            continue
        normalized_item = {
            "type": item["type"],
            "statement": item["statement"],
            "summary": item.get("summary", ""),
            "tags": item.get("tags", []),
            "applies_to": item.get("applies_to", []),
            "confidence": float(item.get("confidence", 0.8)),
            "risk_level": item.get("risk_level", "normal"),
            "review_state": item.get("review_state", "human_review_required"),
            "evidence": [{"type": "conversation_summary", "summary": item.get("evidence_summary", "Extracted from codex-brain session.")}],
        }
        if item.get("title"):
            normalized_item["title"] = item["title"]
        normalized.append(normalized_item)
    return {"session_summary": data.get("session_summary", ""), "candidates": normalized}
