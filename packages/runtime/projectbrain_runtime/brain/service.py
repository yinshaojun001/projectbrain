"""Business operations for project-local Brain memory."""

from __future__ import annotations

from typing import Any

from projectbrain_runtime.brain.models import ConversationSession, KnowledgeUnit, MemoryCandidate, make_brain_id, now_iso
from projectbrain_runtime.brain.repository import BrainRepository
from projectbrain_runtime.brain.search import filter_items, search_knowledge


class BrainService:
    def __init__(self, repository: BrainRepository) -> None:
        self.repository = repository
        self.repository.ensure()

    def remember(
        self,
        *,
        type: str,
        statement: str,
        title: str | None = None,
        summary: str = "",
        tags: list[str] | None = None,
        applies_to: list[str] | None = None,
        review_state: str = "human_review_required",
        confidence: float = 0.8,
        risk_level: str = "normal",
        source: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        unit_id: str | None = None,
    ) -> dict[str, Any]:
        generated_id = unit_id or make_brain_id("ku", title or statement)
        unit = KnowledgeUnit(
            id=generated_id,
            type=type,
            title=title or statement[:80],
            statement=statement,
            summary=summary,
            tags=tags or [],
            applies_to=applies_to or [],
            review_state=review_state,
            confidence=confidence,
            risk_level=risk_level,
            source=source or {},
            evidence=evidence or [],
        )
        if unit_id is None:
            unit = self.repository.create_knowledge_unit_with_available_id(unit)
        else:
            self.repository.save_knowledge_unit(unit)
        return {"knowledge_unit": unit.to_dict()}

    def list_knowledge(
        self,
        *,
        type: str | None = None,
        review_state: str | None = None,
        staleness: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        units = [unit.to_dict() for unit in self.repository.list_knowledge_units()]
        selected = filter_items(
            units,
            type=type,
            review_state=review_state,
            staleness=staleness,
            tag=tag,
            include_archived=include_archived,
        )
        return {"knowledge_units": selected, "knowledge_unit_count": len(selected)}

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        type: str | None = None,
        review_state: str | None = None,
        staleness: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        units = [unit.to_dict() for unit in self.repository.list_knowledge_units()]
        selected = filter_items(
            units,
            type=type,
            review_state=review_state,
            staleness=staleness,
            tag=tag,
            include_archived=include_archived,
        )
        return {"query": query, "matches": search_knowledge(selected, query, limit=limit)}

    def propose_memories(
        self,
        *,
        project_id: str,
        session_id: str | None,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        saved = []
        for candidate_data in candidates:
            statement = candidate_data["statement"]
            candidate = MemoryCandidate(
                candidate_id=make_brain_id("mc", candidate_data.get("title") or statement),
                project_id=project_id,
                session_id=session_id,
                proposed_unit=dict(candidate_data),
                evidence=candidate_data.get("evidence", []),
                possible_duplicates=self._possible_duplicates(candidate_data),
            )
            candidate = self.repository.create_memory_candidate_with_available_id(candidate)
            saved.append(candidate.to_dict())
        return {"candidates": saved, "candidate_count": len(saved)}

    def list_candidates(self, *, review_state: str | None = None) -> dict[str, Any]:
        candidates = [candidate.to_dict() for candidate in self.repository.list_memory_candidates()]
        if review_state:
            candidates = [candidate for candidate in candidates if candidate.get("review_state") == review_state]
        return {"candidates": candidates, "candidate_count": len(candidates)}

    def confirm_candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate, unit = self.repository.confirm_memory_candidate(candidate_id)
        return {"candidate": candidate.to_dict(), "knowledge_unit": unit.to_dict()}

    def reject_candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.repository.get_memory_candidate(candidate_id)
        if candidate.review_state == "human_confirmed":
            raise ValueError(f"Cannot reject confirmed candidate: {candidate_id}")
        if candidate.review_state == "rejected":
            return {"candidate": candidate.to_dict()}
        if candidate.review_state != "human_review_required":
            raise ValueError(f"Cannot reject candidate in state {candidate.review_state}: {candidate_id}")
        updated_candidate = MemoryCandidate.from_dict({**candidate.to_dict(), "review_state": "rejected", "updated_at": now_iso()})
        self.repository.save_memory_candidate(updated_candidate)
        return {"candidate": updated_candidate.to_dict()}

    def save_session(self, session: ConversationSession) -> dict[str, Any]:
        self.repository.save_conversation_session(session)
        return {"session": session.to_dict()}

    def list_sessions(self) -> dict[str, Any]:
        sessions = [session.to_dict() for session in self.repository.list_conversation_sessions()]
        return {"sessions": sessions, "session_count": len(sessions)}

    def summary(self) -> dict[str, Any]:
        units = self.list_knowledge(include_archived=True)["knowledge_units"]
        candidates = self.list_candidates(review_state="human_review_required")["candidates"]
        by_type: dict[str, int] = {}
        by_review_state: dict[str, int] = {}
        for unit in units:
            by_type[unit["type"]] = by_type.get(unit["type"], 0) + 1
            state = unit.get("review_state", "human_review_required")
            by_review_state[state] = by_review_state.get(state, 0) + 1
        return {
            "knowledge_unit_count": len(units),
            "candidate_count": len(candidates),
            "by_type": by_type,
            "by_review_state": by_review_state,
        }

    def _possible_duplicates(self, candidate_data: dict[str, Any]) -> list[dict[str, Any]]:
        candidate_terms = set(_tokens(candidate_data.get("statement", ""))) | set(candidate_data.get("tags", []))
        duplicates = []
        for unit in self.repository.list_knowledge_units():
            unit_terms = set(_tokens(unit.statement)) | set(unit.tags)
            if not candidate_terms or not unit_terms:
                continue
            overlap = len(candidate_terms & unit_terms) / max(len(candidate_terms | unit_terms), 1)
            if overlap >= 0.45:
                duplicates.append({"knowledge_unit_id": unit.id, "similarity": round(overlap, 2), "statement": unit.statement})
        return duplicates


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in value.replace(".", " ").replace(",", " ").split() if token.strip()]
