"""Minimal intake session helpers for ProjectBrain V1."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from projectbrain_runtime.models import now_iso


def build_project_intake_session(*, project_id: str) -> dict[str, Any]:
    now = now_iso()
    return {
        "session_id": f"intake_{uuid4().hex}",
        "project_id": project_id,
        "intake_type": "project",
        "status": "asking",
        "initiated_by": "user",
        "summary": "Project intake session created. The first onboarding question is ready.",
        "next_question": {
            "question_id": "project_goal_01",
            "slot_key": "project_goal",
            "question": "这个项目最核心是干什么的？主要服务谁？",
        },
        "started_at": now,
        "updated_at": now,
    }


def submit_project_intake_answer(
    *,
    session: dict[str, Any],
    session_id: str,
    answer: str,
) -> dict[str, Any]:
    if session.get("session_id") != session_id:
        raise ValueError(f"Unknown intake session: {session_id}")

    updated = dict(session)
    updated["status"] = "answered"
    updated["captured_fields"] = {
        **updated.get("captured_fields", {}),
        "project_goal": answer,
    }
    updated["answers"] = [
        *updated.get("answers", []),
        {
            "question_id": updated.get("next_question", {}).get("question_id"),
            "slot_key": "project_goal",
            "answer": answer,
        },
    ]
    updated["next_question"] = None
    updated["updated_at"] = now_iso()
    updated["summary"] = "Project intake captured the first onboarding answer."
    return updated
