"""Runtime data models for the local ProjectBrain prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    source_path: str
    codegraph_db_path: str
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectRecord":
        return cls(
            project_id=data["project_id"],
            name=data["name"],
            source_path=data["source_path"],
            codegraph_db_path=data["codegraph_db_path"],
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class ImportOptions:
    path_prefixes: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    node_limit: int = 200
    edge_limit: int = 300

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
