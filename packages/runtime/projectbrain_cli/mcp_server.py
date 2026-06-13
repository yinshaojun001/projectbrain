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

            if name == "projectbrain_context_pack":
                data = self.runtime.build_context_pack(
                    project_id=_required(arguments, "project_id"),
                    task=_required(arguments, "task"),
                    max_items_per_section=int(arguments.get("max_items_per_section", 12)),
                )
                return self._tool_result(request_id, data)

            if name == "projectbrain_impact_analysis":
                data = self.runtime.analyze_impact(
                    project_id=_required(arguments, "project_id"),
                    task=_required(arguments, "task"),
                    changed_files=arguments.get("changed_files", []),
                    changed_symbols=arguments.get("changed_symbols", []),
                    max_items_per_section=int(arguments.get("max_items_per_section", 12)),
                )
                return self._tool_result(request_id, data)

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
                return self._tool_result(request_id, data)

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
                "name": "projectbrain_context_pack",
                "description": "Build a task-scoped Context Pack from local ProjectBrain facts.",
                "inputSchema": {
                    "type": "object",
                    "required": ["project_id", "task"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "task": {"type": "string"},
                        "max_items_per_section": {"type": "integer", "default": 12},
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
