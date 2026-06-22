"""Local lexical search for ProjectBrain memory."""

from __future__ import annotations

import re
from typing import Any


def search_knowledge(units: list[dict[str, Any]], query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    terms = _terms(query)
    scored = []
    for unit in units:
        score = _score_unit(unit, terms)
        if score > 0 or not terms:
            item = dict(unit)
            item["search_score"] = score
            scored.append(item)
    scored.sort(key=lambda item: (-item["search_score"], item.get("updated_at", ""), item.get("id", "")))
    return scored[:limit]


def filter_items(
    items: list[dict[str, Any]],
    *,
    type: str | None = None,
    review_state: str | None = None,
    staleness: str | None = None,
    tag: str | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    selected = []
    for item in items:
        if not include_archived and item.get("review_state") == "archived":
            continue
        if type and item.get("type") != type:
            continue
        if review_state and item.get("review_state") != review_state:
            continue
        if staleness and item.get("staleness", {}).get("state") != staleness:
            continue
        if tag and tag not in item.get("tags", []):
            continue
        selected.append(item)
    return selected


def _score_unit(unit: dict[str, Any], terms: list[str]) -> int:
    text = " ".join(
        [
            str(unit.get("title", "")),
            str(unit.get("statement", "")),
            str(unit.get("summary", "")),
            " ".join(unit.get("tags", [])),
            " ".join(unit.get("applies_to", [])),
            " ".join(str(code.get("file", "")) + " " + str(code.get("symbol", "")) for code in unit.get("related_code", [])),
        ]
    ).lower()
    score = 0
    for term in terms:
        if term in unit.get("tags", []):
            score += 8
        if term in " ".join(unit.get("applies_to", [])).lower():
            score += 6
        if term in text:
            score += 3
    if unit.get("review_state") == "human_confirmed":
        score += 2
    if unit.get("risk_level") == "high":
        score += 2
    return score


def _terms(query: str) -> list[str]:
    return [term for term in re.split(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", query.lower()) if term]
