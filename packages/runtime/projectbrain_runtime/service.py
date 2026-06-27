"""Local ProjectBrain runtime service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from projectbrain_adapters.codegraph import CodeGraphAdapter
from projectbrain_adapters.context_pack import ContextPackBuilder
from projectbrain_adapters.experience import load_experience_seed
from projectbrain_adapters.impact_analysis import ImpactAnalysisBuilder
from projectbrain_schema.validation import validate_context_pack, validate_facts_export, validate_impact_analysis
from projectbrain_runtime.bundle import bundle_from_context_pack
from projectbrain_runtime.brain.repository import BrainRepository
from projectbrain_runtime.brain.service import BrainService
from projectbrain_runtime.claims import active_claims, archive_experience_claim, build_experience_claim, update_experience_claim
from projectbrain_runtime.git_diff import GitDiffSelection, changed_files_for_selection
from projectbrain_runtime.models import ImportOptions, ProjectRecord, now_iso
from projectbrain_runtime.policy import ProjectBrainPolicy, apply_output_policy, inspect_policy_for_project, load_policy_for_project
from projectbrain_runtime.repository import ProjectBrainRepository


class ProjectBrainRuntime:
    """Coordinate CodeGraph import, local storage, and query artifacts."""

    def __init__(self, repository: ProjectBrainRepository) -> None:
        self.repository = repository
        self.repository.ensure()

    def brain_for_path(self, project_path: str | Path) -> BrainService:
        return BrainService(BrainRepository(project_path))

    def brain_for_project(self, project_id: str) -> BrainService:
        project = self.repository.get_project(project_id)
        return self.brain_for_path(project.source_path)

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
        project = self.repository.get_project(project_id)
        policy = load_policy_for_project(project.source_path)
        facts = self.repository.get_facts(project_id)
        claims = active_claims(self.repository.get_experience_claims(project_id))
        pack = ContextPackBuilder(
            task=task,
            export=facts,
            experience_claims=claims,
            max_items_per_section=self._effective_section_limit(max_items_per_section, policy),
        ).build()
        pack = apply_output_policy(pack, policy)
        validate_context_pack(pack)
        artifact_path = self.repository.save_run_artifact(project_id, "context-pack-latest.json", pack)
        return {"artifact_path": artifact_path, "context_pack": pack}

    def build_task_understanding_bundle(
        self,
        *,
        project_id: str,
        task: str,
        max_items_per_section: int = 12,
    ) -> dict[str, Any]:
        context_data = self.build_context_pack(
            project_id=project_id,
            task=task,
            max_items_per_section=max_items_per_section,
        )
        bundle = bundle_from_context_pack(
            project_id=project_id,
            task=task,
            context_pack=context_data["context_pack"],
        )
        artifact_path = self.repository.save_run_artifact(
            project_id,
            "task-understanding-bundle-latest.json",
            bundle.to_dict(),
        )
        return {
            "artifact_path": artifact_path,
            "bundle": bundle.to_dict(),
            "context_pack_artifact_path": context_data["artifact_path"],
        }

    def analyze_impact(
        self,
        *,
        project_id: str,
        task: str,
        changed_files: list[str],
        changed_symbols: list[str],
        max_items_per_section: int = 12,
    ) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        policy = load_policy_for_project(project.source_path)
        facts = self.repository.get_facts(project_id)
        claims = active_claims(self.repository.get_experience_claims(project_id))
        analysis = ImpactAnalysisBuilder(
            task=task,
            export=facts,
            changed_files=changed_files,
            changed_symbols=changed_symbols,
            experience_claims=claims,
            max_items_per_section=self._effective_section_limit(max_items_per_section, policy),
        ).build()
        analysis = apply_output_policy(analysis, policy)
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

    def inspect_policy(self, *, project_id: str) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        return {
            "project_id": project_id,
            "project_source_path": project.source_path,
            **inspect_policy_for_project(project.source_path),
        }

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

    def list_experience_claims(
        self,
        *,
        project_id: str,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        self.repository.get_project(project_id)
        claims = self.repository.get_experience_claims(project_id)
        selected_claims = claims if include_archived else active_claims(claims)
        return {
            "project_id": project_id,
            "claims": selected_claims,
            "experience_claims": len(selected_claims),
            "total_experience_claims": len(claims),
        }

    def review_experience_claim(
        self,
        *,
        project_id: str,
        claim_id: str,
        review_state: str | None = None,
        risk_level: str | None = None,
        claim_type: str | None = None,
        confidence: float | None = None,
        statement: str | None = None,
        applies_to: list[str] | str | None = None,
        source: str | list[str] | None = None,
    ) -> dict[str, Any]:
        self.repository.get_project(project_id)
        claims = self.repository.get_experience_claims(project_id)
        updated_claims, claim = update_experience_claim(
            claims,
            claim_id=claim_id,
            review_state=review_state,
            risk_level=risk_level,
            claim_type=claim_type,
            confidence=confidence,
            statement=statement,
            applies_to=applies_to,
            source=source,
        )
        self.repository.save_experience_claims(project_id, updated_claims)
        return {
            "project_id": project_id,
            "claim": claim,
            "experience_claims": len(updated_claims),
        }

    def archive_experience_claim(
        self,
        *,
        project_id: str,
        claim_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self.repository.get_project(project_id)
        claims = self.repository.get_experience_claims(project_id)
        updated_claims, claim = archive_experience_claim(
            claims,
            claim_id=claim_id,
            reason=reason,
        )
        self.repository.save_experience_claims(project_id, updated_claims)
        return {
            "project_id": project_id,
            "claim": claim,
            "experience_claims": len(updated_claims),
            "active_experience_claims": len(active_claims(updated_claims)),
        }

    def _effective_section_limit(self, requested_limit: int, policy: ProjectBrainPolicy) -> int:
        if policy.max_items_per_section is None:
            return requested_limit
        return min(requested_limit, policy.max_items_per_section)
