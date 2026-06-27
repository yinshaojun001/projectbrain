"""JSON-file storage for the ProjectBrain local runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from projectbrain_runtime.models import ProjectRecord


class ProjectBrainStore:
    """Persist local runtime state under ``.projectbrain/projects``."""

    def __init__(self, root: str | Path = ".projectbrain") -> None:
        self.root = Path(root)
        self.projects_dir = self.root / "projects"

    def ensure(self) -> None:
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def runs_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "runs"

    def write_project(self, project: ProjectRecord) -> None:
        project_dir = self.project_dir(project.project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(project_dir / "project.json", project.to_dict())

    def read_project(self, project_id: str) -> ProjectRecord:
        data = self._read_json(self.project_dir(project_id) / "project.json")
        return ProjectRecord.from_dict(data)

    def list_projects(self) -> list[ProjectRecord]:
        if not self.projects_dir.exists():
            return []
        projects = []
        for path in sorted(self.projects_dir.glob("*/project.json")):
            projects.append(ProjectRecord.from_dict(self._read_json(path)))
        return projects

    def write_inventory(self, project_id: str, inventory: dict[str, Any]) -> None:
        self._write_json(self.project_dir(project_id) / "inventory.json", inventory)

    def read_inventory(self, project_id: str) -> dict[str, Any]:
        return self._read_json(self.project_dir(project_id) / "inventory.json")

    def write_facts(self, project_id: str, facts: dict[str, Any]) -> None:
        self._write_json(self.project_dir(project_id) / "facts.json", facts)

    def read_facts(self, project_id: str) -> dict[str, Any]:
        return self._read_json(self.project_dir(project_id) / "facts.json")

    def write_experience_claims(self, project_id: str, claims: list[dict[str, Any]]) -> None:
        self._write_json(self.project_dir(project_id) / "experience_claims.json", claims)

    def read_experience_claims(self, project_id: str) -> list[dict[str, Any]]:
        path = self.project_dir(project_id) / "experience_claims.json"
        if not path.exists():
            return []
        return self._read_json(path)

    def write_run_artifact(self, project_id: str, artifact_name: str, data: dict[str, Any]) -> Path:
        runs_dir = self.runs_dir(project_id)
        runs_dir.mkdir(parents=True, exist_ok=True)
        path = runs_dir / artifact_name
        self._write_json(path, data)
        return path

    def read_run_artifact(self, project_id: str, artifact_name: str) -> dict[str, Any]:
        return self._read_json(self.runs_dir(project_id) / artifact_name)

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"ProjectBrain runtime file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
