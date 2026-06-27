"""Minimal intake session helpers for ProjectBrain V1."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from projectbrain_runtime.models import now_iso


PROJECT_INTAKE_QUESTIONS = [
    {
        "question_id": "project_goal_01",
        "slot_key": "project_goal",
        "question": "这个项目最核心是干什么的？",
    },
    {
        "question_id": "primary_users_01",
        "slot_key": "primary_users",
        "question": "这个项目主要服务谁？最常使用它的是哪些角色？",
    },
    {
        "question_id": "core_modules_01",
        "slot_key": "core_modules",
        "question": "这个项目当前最关键的核心模块有哪些？",
    },
    {
        "question_id": "key_flows_01",
        "slot_key": "key_flows",
        "question": "这个项目最关键的流程有哪些？请优先描述关键流程或调用流程。",
    },
]


def build_project_intake_session(*, project_id: str) -> dict[str, Any]:
    now = now_iso()
    return {
        "session_id": f"intake_{uuid4().hex}",
        "project_id": project_id,
        "intake_type": "project",
        "status": "asking",
        "initiated_by": "user",
        "summary": "Project intake session created. The first onboarding question is ready.",
        "next_question": dict(PROJECT_INTAKE_QUESTIONS[0]),
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

    current_question = session.get("next_question")
    if not current_question:
        raise ValueError(f"Intake session already completed: {session_id}")

    slot_key = current_question.get("slot_key")
    updated = dict(session)
    captured_fields = {
        **updated.get("captured_fields", {}),
        slot_key: answer,
    }
    next_question = _next_project_intake_question(current_question.get("question_id"))
    updated["status"] = "answered" if next_question is None else "asking"
    updated["captured_fields"] = {
        **captured_fields,
    }
    updated["answers"] = [
        *updated.get("answers", []),
        {
            "question_id": current_question.get("question_id"),
            "slot_key": slot_key,
            "answer": answer,
        },
    ]
    updated["next_question"] = next_question
    updated["updated_at"] = now_iso()
    updated["summary"] = _project_intake_summary(next_question)
    updated["baseline_draft"] = _build_project_baseline_draft(
        project_id=updated.get("project_id"),
        captured_fields=captured_fields,
    )
    return updated


def _next_project_intake_question(current_question_id: str | None) -> dict[str, Any] | None:
    for index, question in enumerate(PROJECT_INTAKE_QUESTIONS):
        if question["question_id"] == current_question_id:
            if index + 1 < len(PROJECT_INTAKE_QUESTIONS):
                return dict(PROJECT_INTAKE_QUESTIONS[index + 1])
            return None
    return None


def _project_intake_summary(next_question: dict[str, Any] | None) -> str:
    if next_question is None:
        return "Project intake captured the current onboarding answers."
    return "Project intake captured the latest answer and queued the next onboarding question."


def _build_project_baseline_draft(*, project_id: str | None, captured_fields: dict[str, Any]) -> dict[str, Any]:
    project_goal = captured_fields.get("project_goal", "")
    primary_users = captured_fields.get("primary_users")
    primary_user_list = [primary_users] if primary_users else []
    core_modules = _split_list_answer(captured_fields.get("core_modules"))
    key_flows = _split_list_answer(captured_fields.get("key_flows"))
    return {
        "bundle_type": "project_baseline",
        "project_id": project_id,
        "project_summary": project_goal,
        "project_goal": project_goal,
        "primary_users": primary_user_list,
        "core_modules": core_modules,
        "key_flows": key_flows,
        "third_party_integrations": [],
        "high_risk_areas": [],
        "constraints": [],
        "validation_strategy": [],
        "priority_evidence": [],
        "unknowns": [],
        "quality_notes": [],
    }


def _split_list_answer(answer: Any) -> list[str]:
    if not isinstance(answer, str):
        return []
    normalized = answer.replace("，", ",").replace("、", ",").replace("；", ",").replace(";", ",")
    items = [item.strip().strip("。") for item in normalized.split(",")]
    return [item for item in items if item]
