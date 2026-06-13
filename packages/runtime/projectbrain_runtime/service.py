"""Local ProjectBrain runtime service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from projectbrain_adapters.codegraph import CodeGraphAdapter
from projectbrain_adapters.context_pack import ContextPackBuilder
from projectbrain_adapters.experience import load_experience_seed
from projectbrain_adapters.impact_analysis import ImpactAnalysisBuilder
from projectbrain_schema.validation import validate_context_pack, validate_facts_export, validate_impact_analysis
from projectbrain_runtime.claims import build_experience_claim
from projectbrain_runtime.git_diff import GitDiffSelection, changed_files_for_selection
from projectbrain_runtime.models import ImportOptions, ProjectRecord, now_iso
from projectbrain_runtime.repository import ProjectBrainRepository


class ProjectBrainRuntime:
    """Coordinate CodeGraph import, local storage, and query artifacts."""

    def __init__(self, repository: ProjectBrainRepository) -> None:
        self.repository = repository
        self.repository.ensure()

    def import_project(
        self,
        *,
        project_id: str,
        project_path: str | Path,
        name: str | None = None,
        options: ImportOptions | None = None,
        experience_seed: str | Path | None = None,
    ) -> dict[str, Any]:
        import_options = options or ImportOptions()
        adapter = CodeGraphAdapter.from_project_path(project_path, project_id)
        inventory = adapter.inventory()
        facts = adapter.export_sample(
            path_prefixes=import_options.path_prefixes or None,
            kinds=import_options.kinds or None,
            node_limit=import_options.node_limit,
            edge_limit=import_options.edge_limit,
        )
        claims = load_experience_seed(experience_seed)
        validate_facts_export(facts)
        project = ProjectRecord(
            project_id=project_id,
            name=name or project_id,
            source_path=str(project_path),
            codegraph_db_path=str(adapter.db_path),
            metadata={
                "import_options": import_options.to_dict(),
                "imported_at": now_iso(),
                "experience_seed": str(experience_seed) if experience_seed else None,
            },
        )
        self.repository.save_project(project)
        self.repository.save_inventory(project_id, inventory)
        self.repository.save_facts(project_id, facts)
        self.repository.save_experience_claims(project_id, claims)
        return {
            "project": project.to_dict(),
            "inventory_summary": {
                "files_by_language": inventory.get("files_by_language", []),
                "nodes_by_kind": inventory.get("nodes_by_kind", [])[:8],
                "edges_by_kind": inventory.get("edges_by_kind", [])[:8],
            },
            "facts_summary": facts.get("stats", {}),
            "experience_claims": len(claims),
        }

    def build_context_pack(
        self,
        *,
        project_id: str,
        task: str,
        max_items_per_section: int = 12,
    ) -> dict[str, Any]:
        facts = self.repository.get_facts(project_id)
        claims = self.repository.get_experience_claims(project_id)
        pack = ContextPackBuilder(
            task=task,
            export=facts,
            experience_claims=claims,
            max_items_per_section=max_items_per_section,
        ).build()
        validate_context_pack(pack)
        artifact_path = self.repository.save_run_artifact(project_id, "context-pack-latest.json", pack)
        return {"artifact_path": artifact_path, "context_pack": pack}

    def analyze_impact(
        self,
        *,
        project_id: str,
        task: str,
        changed_files: list[str],
        changed_symbols: list[str],
        max_items_per_section: int = 12,
    ) -> dict[str, Any]:
        facts = self.repository.get_facts(project_id)
        claims = self.repository.get_experience_claims(project_id)
        analysis = ImpactAnalysisBuilder(
            task=task,
            export=facts,
            changed_files=changed_files,
            changed_symbols=changed_symbols,
            experience_claims=claims,
            max_items_per_section=max_items_per_section,
        ).build()
        validate_impact_analysis(analysis)
        artifact_path = self.repository.save_run_artifact(project_id, "impact-analysis-latest.json", analysis)
        return {"artifact_path": artifact_path, "impact_analysis": analysis}

    def analyze_git_diff_impact(
        self,
        *,
        project_id: str,
        task: str,
        selection: GitDiffSelection,
        changed_symbols: list[str] | None = None,
        max_items_per_section: int = 12,
    ) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        changed_files = changed_files_for_selection(project.source_path, selection)
        data = self.analyze_impact(
            project_id=project_id,
            task=task,
            changed_files=changed_files,
            changed_symbols=changed_symbols or [],
            max_items_per_section=max_items_per_section,
        )
        data["git_diff"] = {
            "selection": selection.label(),
            "repo_path": project.source_path,
            "changed_files": changed_files,
        }
        return data

    def add_experience_claim(
        self,
        *,
        project_id: str,
        statement: str,
        applies_to: list[str] | str | None = None,
        risk_level: str = "normal",
        review_state: str = "draft",
        claim_type: str = "HUMAN_REVIEW_REQUIRED",
        confidence: float = 0.8,
        source: str | list[str] | None = None,
        claim_id: str | None = None,
    ) -> dict[str, Any]:
        self.repository.get_project(project_id)
        claims = self.repository.get_experience_claims(project_id)
        claim = build_experience_claim(
            existing_claims=claims,
            statement=statement,
            applies_to=applies_to,
            risk_level=risk_level,
            review_state=review_state,
            claim_type=claim_type,
            confidence=confidence,
            source=source,
            claim_id=claim_id,
        )
        updated_claims = [*claims, claim]
        self.repository.save_experience_claims(project_id, updated_claims)
        return {
            "project_id": project_id,
            "claim": claim,
            "experience_claims": len(updated_claims),
        }
