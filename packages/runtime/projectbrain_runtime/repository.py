"""Repository interfaces for ProjectBrain runtime storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from projectbrain_runtime.knowledge_store import SQLiteKnowledgeStore
from projectbrain_runtime.models import ProjectRecord
from projectbrain_runtime.store import ProjectBrainStore


class ProjectBrainRepository(ABC):
    """Storage abstraction used by ProjectBrainRuntime."""

    @abstractmethod
    def ensure(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_project(self, project: ProjectRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_project(self, project_id: str) -> ProjectRecord:
        raise NotImplementedError

    @abstractmethod
    def list_projects(self) -> list[ProjectRecord]:
        raise NotImplementedError

    @abstractmethod
    def save_inventory(self, project_id: str, inventory: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_inventory(self, project_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_facts(self, project_id: str, facts: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_facts(self, project_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_experience_claims(self, project_id: str, claims: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_experience_claims(self, project_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_run_artifact(self, project_id: str, artifact_name: str, data: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_run_artifact(self, project_id: str, artifact_name: str) -> dict[str, Any]:
        raise NotImplementedError


class JsonProjectBrainRepository(ProjectBrainRepository):
    """ProjectBrainRepository backed by JSON files."""

    def __init__(
        self,
        root: str | Path = ".projectbrain",
        *,
        knowledge_db_path: str | Path | None = None,
    ) -> None:
        self.store = ProjectBrainStore(root)
        default_db_path = Path(root) / "knowledge.db"
        self.knowledge_store = SQLiteKnowledgeStore(knowledge_db_path or default_db_path)

    def ensure(self) -> None:
        self.store.ensure()
        self.knowledge_store.ensure()

    def save_project(self, project: ProjectRecord) -> None:
        self.store.write_project(project)

    def get_project(self, project_id: str) -> ProjectRecord:
        return self.store.read_project(project_id)

    def list_projects(self) -> list[ProjectRecord]:
        return self.store.list_projects()

    def save_inventory(self, project_id: str, inventory: dict[str, Any]) -> None:
        self.store.write_inventory(project_id, inventory)

    def get_inventory(self, project_id: str) -> dict[str, Any]:
        return self.store.read_inventory(project_id)

    def save_facts(self, project_id: str, facts: dict[str, Any]) -> None:
        self.store.write_facts(project_id, facts)

    def get_facts(self, project_id: str) -> dict[str, Any]:
        return self.store.read_facts(project_id)

    def save_experience_claims(self, project_id: str, claims: list[dict[str, Any]]) -> None:
        self.store.write_experience_claims(project_id, claims)

    def get_experience_claims(self, project_id: str) -> list[dict[str, Any]]:
        return self.store.read_experience_claims(project_id)

    def save_run_artifact(self, project_id: str, artifact_name: str, data: dict[str, Any]) -> str:
        return str(self.store.write_run_artifact(project_id, artifact_name, data))

    def get_run_artifact(self, project_id: str, artifact_name: str) -> dict[str, Any]:
        return self.store.read_run_artifact(project_id, artifact_name)
