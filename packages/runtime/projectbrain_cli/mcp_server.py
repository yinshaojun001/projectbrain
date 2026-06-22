"""Local-only stdio MCP server for ProjectBrain.

The server intentionally uses only the Python standard library. It does not
open network sockets, call remote APIs, or upload code. MCP clients start it as
a local child process and communicate over stdin/stdout JSON-RPC messages.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, TextIO

from projectbrain_runtime.agent_output import OUTPUT_FORMATS, format_output
from projectbrain_runtime.brain.models import (
    KNOWLEDGE_TYPES,
    REVIEW_STATES as BRAIN_REVIEW_STATES,
    RISK_LEVELS as BRAIN_RISK_LEVELS,
)
from projectbrain_runtime.claims import CLAIM_TYPES, REVIEW_STATES, RISK_LEVELS
from projectbrain_runtime.git_diff import GitDiffSelection
from projectbrain_runtime.models import ImportOptions
from projectbrain_runtime.repository import JsonProjectBrainRepository
from projectbrain_runtime.service import ProjectBrainRuntime


JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-06-18"


@dataclass(frozen=True)
class ProjectBrainMcpServer:
    """Handle ProjectBrain MCP JSON-RPC requests."""

    store_root: str = ".projectbrain"

    def __post_init__(self) -> None:
        repository = JsonProjectBrainRepository(self.store_root)
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "runtime", ProjectBrainRuntime(repository))

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "projectbrain", "version": "0.1.0"},
                },
            )

        if method == "ping":
            return self._result(request_id, {})

        if method == "tools/list":
            return self._result(request_id, {"tools": self._tools()})

        if method == "tools/call":
            return self._handle_tool_call(request_id, params)

        return self._error(request_id, -32601, f"Method not found: {method}")

    def _handle_tool_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return self._error(request_id, -32602, "Tool arguments must be an object")

        try:
            if name == "projectbrain_import_project":
                data = self.runtime.import_project(
                    project_id=_required(arguments, "project_id"),
                    project_path=_required(arguments, "project_path"),
                    name=arguments.get("name"),
                    options=ImportOptions(
                        path_prefixes=arguments.get("path_prefixes", []),
                        kinds=arguments.get("kinds", []),
                        node_limit=int(arguments.get("node_limit", 200)),
                        edge_limit=int(arguments.get("edge_limit", 300)),
                    ),
                    experience_seed=arguments.get("experience_seed"),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_list_projects":
                data = {"projects": [project.to_dict() for project in self.repository.list_projects()]}
                return self._tool_result(request_id, data)

            if name == "projectbrain_inspect_policy":
                data = self.runtime.inspect_policy(project_id=_required(arguments, "project_id"))
                return self._tool_result(request_id, data)

            if name == "projectbrain_add_experience_claim":
                data = self.runtime.add_experience_claim(
                    project_id=_required(arguments, "project_id"),
                    statement=_required(arguments, "statement"),
                    applies_to=arguments.get("applies_to", []),
                    risk_level=arguments.get("risk_level", "normal"),
                    review_state=arguments.get("review_state", "draft"),
                    claim_type=arguments.get("claim_type", "HUMAN_REVIEW_REQUIRED"),
                    confidence=float(arguments.get("confidence", 0.8)),
                    source=arguments.get("source", []),
                    claim_id=arguments.get("claim_id"),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_list_experience_claims":
                data = self.runtime.list_experience_claims(
                    project_id=_required(arguments, "project_id"),
                    include_archived=bool(arguments.get("include_archived", False)),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_review_experience_claim":
                data = self.runtime.review_experience_claim(
                    project_id=_required(arguments, "project_id"),
                    claim_id=_required(arguments, "claim_id"),
                    statement=arguments.get("statement"),
                    applies_to=arguments.get("applies_to") if "applies_to" in arguments else None,
                    risk_level=arguments.get("risk_level"),
                    review_state=arguments.get("review_state"),
                    claim_type=arguments.get("claim_type"),
                    confidence=float(arguments["confidence"]) if "confidence" in arguments else None,
                    source=arguments.get("source") if "source" in arguments else None,
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_archive_experience_claim":
                data = self.runtime.archive_experience_claim(
                    project_id=_required(arguments, "project_id"),
                    claim_id=_required(arguments, "claim_id"),
                    reason=arguments.get("reason"),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_remember":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).remember(
                    type=_required(arguments, "type"),
                    statement=_required(arguments, "statement"),
                    title=arguments.get("title"),
                    summary=arguments.get("summary", ""),
                    tags=arguments.get("tags", []),
                    applies_to=arguments.get("applies_to", []),
                    review_state=arguments.get("review_state", "human_review_required"),
                    confidence=float(arguments.get("confidence", 0.8)),
                    risk_level=arguments.get("risk_level", "normal"),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_propose_memories":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).propose_memories(
                    project_id=_required(arguments, "project_id"),
                    session_id=arguments.get("session_id"),
                    candidates=_validate_memory_candidates(_required(arguments, "candidates")),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_search_brain":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).search(
                    _required(arguments, "query"),
                    limit=int(arguments.get("limit", 20)),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_list_memory_candidates":
                data = self.runtime.brain_for_project(_required(arguments, "project_id")).list_candidates(
                    review_state=arguments.get("review_state")
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_review_memory_candidate":
                service = self.runtime.brain_for_project(_required(arguments, "project_id"))
                action = _required(arguments, "action")
                if action == "confirm":
                    data = service.confirm_candidate(_required(arguments, "candidate_id"))
                elif action == "reject":
                    data = service.reject_candidate(_required(arguments, "candidate_id"))
                else:
                    raise ValueError("action must be confirm or reject")
                return self._tool_result(request_id, data)

            if name == "projectbrain_context_pack":
                data = self.runtime.build_context_pack(
                    project_id=_required(arguments, "project_id"),
                    task=_required(arguments, "task"),
                    max_items_per_section=int(arguments.get("max_items_per_section", 12)),
                )
                return self._tool_result(request_id, _format_tool_output(data, arguments))

            if name == "projectbrain_impact_analysis":
                data = self.runtime.analyze_impact(
                    project_id=_required(arguments, "project_id"),
                    task=_required(arguments, "task"),
                    changed_files=arguments.get("changed_files", []),
                    changed_symbols=arguments.get("changed_symbols", []),
                    max_items_per_section=int(arguments.get("max_items_per_section", 12)),
                )
                return self._tool_result(request_id, _format_tool_output(data, arguments))

            if name == "projectbrain_review_git_diff":
                data = self.runtime.analyze_git_diff_impact(
                    project_id=_required(arguments, "project_id"),
                    task=_required(arguments, "task"),
                    selection=GitDiffSelection(
                        staged=bool(arguments.get("staged", False)),
                        from_ref=arguments.get("from_ref"),
                        to_ref=arguments.get("to_ref"),
                        last_commit=bool(arguments.get("last_commit", False)),
                    ),
                    changed_symbols=arguments.get("changed_symbols", []),
                    max_items_per_section=int(arguments.get("max_items_per_section", 12)),
                )
                return self._tool_result(request_id, _format_tool_output(data, arguments))

            return self._error(request_id, -32602, f"Unknown tool: {name}")
        except Exception as exc:  # pragma: no cover - exercised through integration failures.
            return self._tool_result(request_id, {"error": str(exc)}, is_error=True)

    def _tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "projectbrain_import_project",
                "description": (
                    "Import CodeGraph facts from a local repository into the local ProjectBrain store. "
                    "Runs only on local files and does not upload source code."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "project_path"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "project_path": {"type": "string"},
                        "name": {"type": "string"},
                        "experience_seed": {"type": "string"},
                        "path_prefixes": {"type": "array", "items": {"type": "string"}},
                        "kinds": {"type": "array", "items": {"type": "string"}},
                        "node_limit": {"type": "integer", "default": 200},
                        "edge_limit": {"type": "integer", "default": 300},
                    },
                },
            },
            {
                "name": "projectbrain_list_projects",
                "description": "List projects imported into the local ProjectBrain store.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "projectbrain_inspect_policy",
                "description": "Inspect the local output policy loaded for an imported project.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_add_experience_claim",
                "description": (
                    "Add a local human experience claim to an imported project. "
                    "Writes only to local ProjectBrain storage and does not read source bodies."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "statement"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "statement": {"type": "string"},
                        "applies_to": {"type": "array", "items": {"type": "string"}},
                        "risk_level": {"type": "string", "enum": list(RISK_LEVELS), "default": "normal"},
                        "review_state": {"type": "string", "enum": list(REVIEW_STATES), "default": "draft"},
                        "claim_type": {"type": "string", "enum": list(CLAIM_TYPES), "default": "HUMAN_REVIEW_REQUIRED"},
                        "confidence": {"type": "number", "default": 0.8},
                        "source": {"type": "array", "items": {"type": "string"}},
                        "claim_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_list_experience_claims",
                "description": "List local experience claims for an imported project. Archived claims are hidden by default.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "include_archived": {"type": "boolean", "default": False},
                    },
                },
            },
            {
                "name": "projectbrain_review_experience_claim",
                "description": "Update local review metadata for an experience claim.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "claim_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "claim_id": {"type": "string"},
                        "statement": {"type": "string"},
                        "applies_to": {"type": "array", "items": {"type": "string"}},
                        "risk_level": {"type": "string", "enum": list(RISK_LEVELS)},
                        "review_state": {"type": "string", "enum": list(REVIEW_STATES)},
                        "claim_type": {"type": "string", "enum": list(CLAIM_TYPES)},
                        "confidence": {"type": "number"},
                        "source": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            {
                "name": "projectbrain_archive_experience_claim",
                "description": "Archive a local experience claim while keeping it in ProjectBrain storage.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "claim_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "claim_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_remember",
                "description": "Write durable project knowledge into the local project Brain.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "type", "statement"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "type": {"type": "string"},
                        "statement": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "applies_to": {"type": "array", "items": {"type": "string"}},
                        "review_state": {"type": "string"},
                        "confidence": {"type": "number"},
                        "risk_level": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_propose_memories",
                "description": "Submit memory candidates extracted from a Codex session for human review.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "candidates"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "session_id": {"type": "string"},
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["type", "statement"],
                                "additionalProperties": False,
                                "properties": {
                                    "type": {"type": "string", "enum": list(KNOWLEDGE_TYPES)},
                                    "title": {"type": "string"},
                                    "statement": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                    "applies_to": {"type": "array", "items": {"type": "string"}},
                                    "confidence": {"type": "number"},
                                    "risk_level": {"type": "string", "enum": list(BRAIN_RISK_LEVELS)},
                                    "evidence_summary": {"type": "string"},
                                    "review_state": {"type": "string", "enum": list(BRAIN_REVIEW_STATES)},
                                },
                            },
                        },
                    },
                },
            },
            {
                "name": "projectbrain_search_brain",
                "description": "Search durable local project Brain knowledge.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "query"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "projectbrain_list_memory_candidates",
                "description": "List memory candidates awaiting review.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "review_state": {"type": "string"},
                    },
                },
            },
            {
                "name": "projectbrain_review_memory_candidate",
                "description": "Confirm or reject a memory candidate.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "candidate_id", "action"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "candidate_id": {"type": "string"},
                        "action": {"type": "string", "enum": ["confirm", "reject"]},
                    },
                },
            },
            {
                "name": "projectbrain_context_pack",
                "description": "Build a task-scoped Context Pack from local ProjectBrain facts.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "task"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "task": {"type": "string"},
                        "max_items_per_section": {"type": "integer", "default": 12},
                        "output_format": {"type": "string", "enum": list(OUTPUT_FORMATS), "default": "json"},
                    },
                },
            },
            {
                "name": "projectbrain_impact_analysis",
                "description": "Analyze likely local project impact for changed files or symbols.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "task"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "task": {"type": "string"},
                        "changed_files": {"type": "array", "items": {"type": "string"}},
                        "changed_symbols": {"type": "array", "items": {"type": "string"}},
                        "max_items_per_section": {"type": "integer", "default": 12},
                        "output_format": {"type": "string", "enum": list(OUTPUT_FORMATS), "default": "json"},
                    },
                },
            },
            {
                "name": "projectbrain_review_git_diff",
                "description": (
                    "Analyze impact for local Git changes in an imported project. "
                    "Reads changed file names from local git only; does not read or upload source bodies."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "task"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "task": {"type": "string"},
                        "staged": {"type": "boolean", "default": False},
                        "from_ref": {"type": "string"},
                        "to_ref": {"type": "string"},
                        "last_commit": {"type": "boolean", "default": False},
                        "changed_symbols": {"type": "array", "items": {"type": "string"}},
                        "max_items_per_section": {"type": "integer", "default": 12},
                        "output_format": {"type": "string", "enum": list(OUTPUT_FORMATS), "default": "json"},
                    },
                },
            },
        ]

    def _tool_result(self, request_id: Any, data: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
        return self._result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(data, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": is_error,
            },
        )

    def _result(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": code, "message": message}}


def serve_stdio(
    *,
    store_root: str = ".projectbrain",
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    server = ProjectBrainMcpServer(store_root=store_root)
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = server.handle_message(message)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc.msg}"},
            }
        except Exception as exc:  # pragma: no cover - defensive stdio boundary.
            print(f"ProjectBrain MCP internal error: {exc}", file=stderr, flush=True)
            response = {
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {"code": -32603, "message": "Internal error"},
            }
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            stdout.flush()
    return 0


def _required(arguments: dict[str, Any], key: str) -> Any:
    value = arguments.get(key)
    if value in (None, ""):
        raise ValueError(f"Missing required argument: {key}")
    return value


MEMORY_CANDIDATE_ALLOWED_FIELDS = {
    "type",
    "title",
    "statement",
    "summary",
    "tags",
    "applies_to",
    "confidence",
    "risk_level",
    "evidence_summary",
    "review_state",
}


def _validate_memory_candidates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("candidates must be an array")
    validated = []
    for index, candidate in enumerate(value):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidates[{index}] must be an object")
        extra_fields = sorted(set(candidate) - MEMORY_CANDIDATE_ALLOWED_FIELDS)
        if extra_fields:
            raise ValueError(f"Unsupported candidate field: {extra_fields[0]}")
        for field in ("type", "statement"):
            if candidate.get(field) in (None, ""):
                raise ValueError(f"Missing required candidate field: {field}")
        validated.append(dict(candidate))
    return validated


def _format_tool_output(data: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    return format_output(data, str(arguments.get("output_format", "json")))
