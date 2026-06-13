"""Minimal CodeGraph SQLite adapter for ProjectBrain.

This module intentionally uses only Python's standard library so the first
ProjectBrain pilot can run without dependency installation.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NODE_KIND_TO_ENTITY_TYPE = {
    "file": "CodeFile",
    "namespace": "Namespace",
    "class": "Class",
    "interface": "Interface",
    "enum": "Enum",
    "method": "Method",
    "function": "Function",
    "field": "Field",
    "constant": "Constant",
    "enum_member": "EnumMember",
    "import": "Import",
    "route": "API",
    "component": "Component",
}

EDGE_KIND_TO_RELATION_TYPE = {
    "contains": "CONTAINS",
    "calls": "CALLS",
    "imports": "IMPORTS",
    "references": "REFERENCES",
    "instantiates": "INSTANTIATES",
    "implements": "IMPLEMENTS_INTERFACE",
    "extends": "EXTENDS",
}


@dataclass(frozen=True)
class CodeGraphAdapter:
    """Read CodeGraph facts and map them to ProjectBrain-shaped JSON."""

    db_path: Path
    project_id: str
    source_name: str = "codegraph"

    @classmethod
    def from_project_path(cls, project_path: str | Path, project_id: str) -> "CodeGraphAdapter":
        root = Path(project_path)
        db_path = root / ".codegraph" / "codegraph.db"
        return cls(db_path=db_path, project_id=project_id)

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"CodeGraph DB not found: {self.db_path}")
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def inventory(self) -> dict[str, Any]:
        with closing(self.connect()) as conn:
            return {
                "project_id": self.project_id,
                "db_path": str(self.db_path),
                "tables": self._tables(conn),
                "files_by_language": self._files_by_language(conn),
                "nodes_by_kind": self._counts(conn, "nodes", "kind"),
                "edges_by_kind": self._counts(conn, "edges", "kind"),
                "files_by_top_dir": self._files_by_top_dir(conn),
            }

    def export_sample(
        self,
        *,
        path_prefixes: list[str] | None = None,
        kinds: list[str] | None = None,
        node_limit: int = 200,
        edge_limit: int = 300,
    ) -> dict[str, Any]:
        with closing(self.connect()) as conn:
            nodes = self._select_nodes(conn, path_prefixes=path_prefixes, kinds=kinds, limit=node_limit)
            node_ids = [node["id"] for node in nodes]
            edges = self._select_edges(conn, node_ids=node_ids, limit=edge_limit)
            entities = [self.map_node_to_entity(dict(node)) for node in nodes]
            relations = [self.map_edge_to_relation(dict(edge)) for edge in edges]
            sources = [self.map_node_to_source(dict(node)) for node in nodes]
            return {
                "project_id": self.project_id,
                "source": {
                    "type": self.source_name,
                    "db_path": str(self.db_path),
                },
                "stats": {
                    "nodes_exported": len(nodes),
                    "edges_exported": len(edges),
                    "sources_exported": len(sources),
                },
                "entities": entities,
                "relations": relations,
                "sources": sources,
            }

    def map_node_to_entity(self, node: dict[str, Any]) -> dict[str, Any]:
        entity_type = NODE_KIND_TO_ENTITY_TYPE.get(node["kind"], "CodeEntity")
        return {
            "entity_type": entity_type,
            "stable_key": self._node_stable_key(node),
            "name": node["name"],
            "qualified_name": node["qualified_name"],
            "properties": {
                "source": self.source_name,
                "source_node_id": node["id"],
                "source_kind": node["kind"],
                "language": node["language"],
                "file_path": node["file_path"],
                "signature": node["signature"],
                "visibility": node["visibility"],
                "module": self._module_from_path(node["file_path"]),
            },
            "source_refs": [self._source_uri(node["id"])],
        }

    def map_node_to_source(self, node: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": "code_location",
            "uri": self._source_uri(node["id"]),
            "locator": {
                "file": node["file_path"],
                "start_line": node["start_line"],
                "end_line": node["end_line"],
                "start_column": node["start_column"],
                "end_column": node["end_column"],
                "symbol": node["qualified_name"],
            },
            "metadata": {
                "codegraph_node_id": node["id"],
                "language": node["language"],
                "kind": node["kind"],
            },
        }

    def map_edge_to_relation(self, edge: dict[str, Any]) -> dict[str, Any]:
        relation_type = EDGE_KIND_TO_RELATION_TYPE.get(edge["kind"], edge["kind"].upper())
        confidence = self._edge_confidence(edge)
        return {
            "relation_type": relation_type,
            "from_stable_key": self._node_stable_key(
                {
                    "kind": edge["source_kind"],
                    "qualified_name": edge["source_qualified_name"],
                }
            ),
            "to_stable_key": self._node_stable_key(
                {
                    "kind": edge["target_kind"],
                    "qualified_name": edge["target_qualified_name"],
                }
            ),
            "confidence": confidence,
            "properties": {
                "source": self.source_name,
                "source_edge_id": edge["id"],
                "source_edge_kind": edge["kind"],
                "provenance": edge["provenance"],
                "line": edge["line"],
                "col": edge["col"],
            },
            "source_refs": [f"{self._source_prefix()}/edge/{edge['id']}"],
        }

    def _tables(self, conn: sqlite3.Connection) -> list[str]:
        rows = conn.execute("select name from sqlite_master where type='table' order by name").fetchall()
        return [row["name"] for row in rows]

    def _files_by_language(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            select language,
                   count(*) as files,
                   coalesce(sum(node_count), 0) as nodes,
                   coalesce(sum(size), 0) as bytes
            from files
            group by language
            order by files desc
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _counts(self, conn: sqlite3.Connection, table: str, column: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            f"select {column} as name, count(*) as count from {table} group by {column} order by count desc"
        ).fetchall()
        return [dict(row) for row in rows]

    def _files_by_top_dir(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            select substr(path, 1, instr(path || '/', '/') - 1) as top_dir,
                   count(*) as files,
                   coalesce(sum(node_count), 0) as nodes
            from files
            group by top_dir
            order by files desc
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _select_nodes(
        self,
        conn: sqlite3.Connection,
        *,
        path_prefixes: list[str] | None,
        kinds: list[str] | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[Any] = []
        if path_prefixes:
            path_clauses = []
            for prefix in path_prefixes:
                path_clauses.append("file_path like ?")
                params.append(f"{prefix}%")
            clauses.append("(" + " or ".join(path_clauses) + ")")
        if kinds:
            kind_placeholders = ",".join("?" for _ in kinds)
            clauses.append(f"kind in ({kind_placeholders})")
            params.extend(kinds)
        where = "where " + " and ".join(clauses) if clauses else ""
        params.append(limit)
        return conn.execute(
            f"""
            select id, kind, name, qualified_name, file_path, language,
                   start_line, end_line, start_column, end_column,
                   signature, visibility
            from nodes
            {where}
            order by file_path, start_line, kind, name
            limit ?
            """,
            params,
        ).fetchall()

    def _select_edges(
        self,
        conn: sqlite3.Connection,
        *,
        node_ids: list[str],
        limit: int,
    ) -> list[sqlite3.Row]:
        if not node_ids:
            return []
        placeholders = ",".join("?" for _ in node_ids)
        params: list[Any] = [*node_ids, *node_ids, limit]
        return conn.execute(
            f"""
            select e.id, e.kind, e.metadata, e.line, e.col, e.provenance,
                   s.id as source_id,
                   s.kind as source_kind,
                   s.name as source_name,
                   s.qualified_name as source_qualified_name,
                   s.file_path as source_file_path,
                   t.id as target_id,
                   t.kind as target_kind,
                   t.name as target_name,
                   t.qualified_name as target_qualified_name,
                   t.file_path as target_file_path
            from edges e
            join nodes s on s.id = e.source
            join nodes t on t.id = e.target
            where e.source in ({placeholders}) or e.target in ({placeholders})
            order by e.kind, s.file_path, e.line
            limit ?
            """,
            params,
        ).fetchall()

    def _node_stable_key(self, node: dict[str, Any]) -> str:
        return f"codegraph:{node['kind']}:{node['qualified_name']}"

    def _source_uri(self, node_id: str) -> str:
        return f"{self._source_prefix()}/node/{node_id}"

    def _source_prefix(self) -> str:
        return f"codegraph://{self.project_id}"

    def _module_from_path(self, file_path: str) -> str | None:
        first = file_path.split("/", 1)[0]
        return first if first else None

    def _edge_confidence(self, edge: dict[str, Any]) -> float:
        if edge["kind"] in {"contains", "imports", "extends", "implements", "references"}:
            return 1.0
        if edge["provenance"] == "heuristic":
            return 0.75
        if edge["kind"] == "calls":
            return 0.9
        return 0.8


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
