"""Installable ProjectBrain CLI."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from projectbrain_adapters.codegraph import CodeGraphAdapter
from projectbrain_adapters.context_pack import ContextPackBuilder
from projectbrain_adapters.experience import load_experience_seed
from projectbrain_adapters.impact_analysis import ImpactAnalysisBuilder
from projectbrain_cli.mcp_server import serve_stdio
from projectbrain_runtime.agent_output import OUTPUT_FORMATS, format_output
from projectbrain_runtime.claims import CLAIM_TYPES, REVIEW_STATES, RISK_LEVELS
from projectbrain_runtime.git_diff import GitDiffSelection
from projectbrain_runtime.models import ImportOptions
from projectbrain_runtime.repository import JsonProjectBrainRepository
from projectbrain_runtime.service import ProjectBrainRuntime


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projectbrain",
        description="ProjectBrain local project cognition CLI",
    )
    parser.add_argument("--store-root", default=".projectbrain", help="Runtime store root directory")

    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("doctor", help="Check local ProjectBrain CLI health")

    setup = subcommands.add_parser("setup", help="Set up a local project for agent use")
    setup.add_argument("project_path", help="Path to the local repository")
    setup.add_argument("--id", dest="project_id", help="ProjectBrain project id")
    setup.add_argument("--name", help="Human-readable project name")
    setup.add_argument("--task", default="Explain the main flow", help="Smoke-test task for the first Context Pack")
    setup.add_argument("--experience-seed", help="Markdown experience seed table")
    setup.add_argument("--path-prefix", action="append", default=[], help="Only import nodes under this prefix")
    setup.add_argument("--kind", action="append", default=[], help="Only import CodeGraph nodes of this kind")
    setup.add_argument("--node-limit", type=int, default=800)
    setup.add_argument("--edge-limit", type=int, default=1200)
    setup.add_argument("--skip-codegraph", action="store_true", help="Skip CodeGraph init/index and import existing facts only")
    setup.add_argument("--mcp-command", help="Command path to use in the printed MCP config")
    setup.add_argument(
        "--agent",
        action="append",
        choices=["codex", "claude", "cursor", "trae"],
        default=[],
        help="Install ProjectBrain MCP into a detected agent. Repeat to install multiple agents.",
    )

    mcp = subcommands.add_parser("mcp", help="Run ProjectBrain MCP server commands")
    mcp_subcommands = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_subcommands.add_parser("serve", help="Run local-only stdio MCP server")

    policy = subcommands.add_parser("policy", help="Inspect local ProjectBrain privacy policy")
    policy_subcommands = policy.add_subparsers(dest="policy_command", required=True)
    policy_inspect = policy_subcommands.add_parser("inspect", help="Inspect the policy for an imported project")
    policy_inspect.add_argument("project_id")

    import_project = subcommands.add_parser("import", help="Import CodeGraph facts into local runtime")
    import_project.add_argument("project_path", help="Path to repository containing .codegraph/codegraph.db")
    import_project.add_argument("--id", dest="project_id", required=True, help="ProjectBrain project id")
    import_project.add_argument("--name", help="Human-readable project name")
    import_project.add_argument("--experience-seed", help="Markdown experience seed table")
    import_project.add_argument("--path-prefix", action="append", default=[], help="Only import nodes under this prefix")
    import_project.add_argument("--kind", action="append", default=[], help="Only import CodeGraph nodes of this kind")
    import_project.add_argument("--node-limit", type=int, default=200)
    import_project.add_argument("--edge-limit", type=int, default=300)

    subcommands.add_parser("list", help="List imported projects")

    baseline = subcommands.add_parser("baseline", help="Work with project baseline artifacts")
    baseline_subcommands = baseline.add_subparsers(dest="baseline_command", required=True)
    baseline_show = baseline_subcommands.add_parser("show", help="Show the latest project baseline artifact")
    baseline_show.add_argument("project_id")

    intake = subcommands.add_parser("intake", help="Start ProjectBrain intake workflows")
    intake_subcommands = intake.add_subparsers(dest="intake_command", required=True)
    intake_project = intake_subcommands.add_parser("project", help="Start project onboarding intake")
    intake_project.add_argument("project_id")
    intake_answer = intake_subcommands.add_parser("answer", help="Submit an answer for the current project intake session")
    intake_answer.add_argument("project_id")
    intake_answer.add_argument("session_id")
    intake_answer.add_argument("--answer", required=True)

    claim = subcommands.add_parser("claim", help="Work with local experience claims")
    claim_subcommands = claim.add_subparsers(dest="claim_command", required=True)
    claim_add = claim_subcommands.add_parser("add", help="Add a local experience claim")
    claim_add.add_argument("project_id")
    claim_add.add_argument("--statement", required=True)
    claim_add.add_argument("--applies-to", action="append", default=[])
    claim_add.add_argument("--risk", dest="risk_level", choices=RISK_LEVELS, default="normal")
    claim_add.add_argument("--review-state", choices=REVIEW_STATES, default="draft")
    claim_add.add_argument("--claim-type", choices=CLAIM_TYPES, default="HUMAN_REVIEW_REQUIRED")
    claim_add.add_argument("--confidence", type=float, default=0.8)
    claim_add.add_argument("--source", action="append", default=[])
    claim_add.add_argument("--id", dest="claim_id")
    claim_list = claim_subcommands.add_parser("list", help="List local experience claims")
    claim_list.add_argument("project_id")
    claim_list.add_argument("--include-archived", action="store_true")
    claim_review = claim_subcommands.add_parser("review", help="Update experience claim review metadata")
    claim_review.add_argument("project_id")
    claim_review.add_argument("claim_id")
    claim_review.add_argument("--statement")
    claim_review.add_argument("--applies-to", action="append")
    claim_review.add_argument("--risk", dest="risk_level", choices=RISK_LEVELS)
    claim_review.add_argument("--review-state", choices=REVIEW_STATES)
    claim_review.add_argument("--claim-type", choices=CLAIM_TYPES)
    claim_review.add_argument("--confidence", type=float)
    claim_review.add_argument("--source", action="append")
    claim_archive = claim_subcommands.add_parser("archive", help="Archive a local experience claim")
    claim_archive.add_argument("project_id")
    claim_archive.add_argument("claim_id")
    claim_archive.add_argument("--reason")

    brain = subcommands.add_parser("brain", help="Work with project-local Brain memory")
    brain_subcommands = brain.add_subparsers(dest="brain_command", required=True)

    brain_remember = brain_subcommands.add_parser("remember", help="Remember a durable project knowledge unit")
    brain_remember.add_argument("project_path")
    brain_remember.add_argument("--id", dest="project_id", default="local_project")
    brain_remember.add_argument("--type", required=True)
    brain_remember.add_argument("--statement", required=True)
    brain_remember.add_argument("--title")
    brain_remember.add_argument("--summary", default="")
    brain_remember.add_argument("--tag", action="append", default=[])
    brain_remember.add_argument("--applies-to", action="append", default=[])
    brain_remember.add_argument("--review-state", default="human_review_required")
    brain_remember.add_argument("--confidence", type=float, default=0.8)
    brain_remember.add_argument("--risk-level", default="normal")
    brain_remember.add_argument("--unit-id")

    brain_list = brain_subcommands.add_parser("list", help="List project Brain knowledge units")
    brain_list.add_argument("project_path")
    brain_list.add_argument("--type")
    brain_list.add_argument("--review-state")
    brain_list.add_argument("--staleness")
    brain_list.add_argument("--tag")
    brain_list.add_argument("--include-archived", action="store_true")

    brain_search = brain_subcommands.add_parser("search", help="Search project Brain knowledge units")
    brain_search.add_argument("project_path")
    brain_search.add_argument("query")
    brain_search.add_argument("--limit", type=int, default=20)
    brain_search.add_argument("--type")
    brain_search.add_argument("--review-state")
    brain_search.add_argument("--staleness")
    brain_search.add_argument("--tag")
    brain_search.add_argument("--include-archived", action="store_true")

    brain_propose = brain_subcommands.add_parser("propose", help="Propose a Brain memory candidate")
    brain_propose.add_argument("project_path")
    brain_propose.add_argument("--id", dest="project_id", default="local_project")
    brain_propose.add_argument("--session-id")
    brain_propose.add_argument("--type", required=True)
    brain_propose.add_argument("--statement", required=True)
    brain_propose.add_argument("--title")
    brain_propose.add_argument("--summary", default="")
    brain_propose.add_argument("--tag", action="append", default=[])
    brain_propose.add_argument("--applies-to", action="append", default=[])
    brain_propose.add_argument("--confidence", type=float, default=0.8)
    brain_propose.add_argument("--risk-level", default="normal")

    brain_candidates = brain_subcommands.add_parser("candidates", help="List Brain memory candidates")
    brain_candidates.add_argument("project_path")
    brain_candidates.add_argument("--review-state")

    brain_confirm = brain_subcommands.add_parser("confirm-candidate", help="Confirm a Brain memory candidate")
    brain_confirm.add_argument("project_path")
    brain_confirm.add_argument("candidate_id")

    brain_reject = brain_subcommands.add_parser("reject-candidate", help="Reject a Brain memory candidate")
    brain_reject.add_argument("project_path")
    brain_reject.add_argument("candidate_id")

    context = subcommands.add_parser("context", help="Build context pack from imported facts")
    context.add_argument("project_id")
    context.add_argument("task")
    context.add_argument("--max-items-per-section", type=int, default=12)
    context.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")

    understand = subcommands.add_parser("understand", help="Build a task understanding bundle from imported facts")
    understand.add_argument("project_id")
    understand.add_argument("task")
    understand.add_argument("--max-items-per-section", type=int, default=12)
    understand.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")

    impact = subcommands.add_parser("impact", help="Build impact analysis from imported facts")
    impact.add_argument("project_id")
    impact.add_argument("task")
    impact.add_argument("--changed-file", action="append", default=[])
    impact.add_argument("--changed-symbol", action="append", default=[])
    impact.add_argument("--max-items-per-section", type=int, default=12)
    impact.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")

    impact_diff = subcommands.add_parser("impact-diff", help="Build impact analysis from local Git diff")
    impact_diff.add_argument("project_id")
    impact_diff.add_argument("task")
    diff_group = impact_diff.add_mutually_exclusive_group()
    diff_group.add_argument("--staged", action="store_true", help="Analyze staged changes")
    diff_group.add_argument("--last-commit", action="store_true", help="Analyze HEAD~1..HEAD")
    impact_diff.add_argument("--from", dest="from_ref", help="Git base ref")
    impact_diff.add_argument("--to", dest="to_ref", help="Git target ref")
    impact_diff.add_argument("--changed-symbol", action="append", default=[])
    impact_diff.add_argument("--max-items-per-section", type=int, default=12)
    impact_diff.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")

    facts = subcommands.add_parser("facts", help="Work directly with CodeGraph facts or exported facts")
    facts_subcommands = facts.add_subparsers(dest="facts_command", required=True)

    inventory = facts_subcommands.add_parser("inventory", help="Print CodeGraph inventory JSON")
    _add_fact_source_arguments(inventory)

    export = facts_subcommands.add_parser("export", help="Export ProjectBrain-shaped facts from CodeGraph")
    _add_fact_source_arguments(export)
    _add_fact_filter_arguments(export)

    facts_context = facts_subcommands.add_parser("context", help="Build context pack from exported facts")
    _add_export_or_project_arguments(facts_context)
    _add_fact_filter_arguments(facts_context)
    facts_context.add_argument("--task", required=True)
    facts_context.add_argument("--experience-seed")
    facts_context.add_argument("--max-items-per-section", type=int, default=12)

    facts_impact = facts_subcommands.add_parser("impact", help="Build impact analysis from exported facts")
    _add_export_or_project_arguments(facts_impact)
    _add_fact_filter_arguments(facts_impact)
    facts_impact.add_argument("--task", required=True)
    facts_impact.add_argument("--experience-seed")
    facts_impact.add_argument("--changed-file", action="append", default=[])
    facts_impact.add_argument("--changed-symbol", action="append", default=[])
    facts_impact.add_argument("--max-items-per-section", type=int, default=12)

    return parser


def main(
    argv: list[str] | None = None,
    *,
    command_runner: Any | None = None,
    agent_detector: Any | None = None,
    input_reader: Any | None = None,
) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "doctor":
        print_json(
            {
                "status": "ok",
                "python": sys.version.split()[0],
                "store_root": args.store_root,
            }
        )
        return 0

    if args.command == "facts":
        return _handle_facts(args)

    if args.command == "mcp":
        if args.mcp_command == "serve":
            return serve_stdio(store_root=args.store_root)
        raise ValueError(f"Unsupported mcp command: {args.mcp_command}")

    repository = JsonProjectBrainRepository(args.store_root)
    runtime = ProjectBrainRuntime(repository)

    if args.command == "brain":
        brain_service = runtime.brain_for_path(args.project_path)
        if args.brain_command == "remember":
            data = brain_service.remember(
                type=args.type,
                statement=args.statement,
                title=args.title,
                summary=args.summary,
                tags=args.tag,
                applies_to=args.applies_to,
                review_state=args.review_state,
                confidence=args.confidence,
                risk_level=args.risk_level,
                source={"project_id": args.project_id, "client": "projectbrain-cli"},
                unit_id=args.unit_id,
            )
            print_json(data)
            return 0
        if args.brain_command == "list":
            data = brain_service.list_knowledge(
                type=args.type,
                review_state=args.review_state,
                staleness=args.staleness,
                tag=args.tag,
                include_archived=args.include_archived,
            )
            print_json(data)
            return 0
        if args.brain_command == "search":
            data = brain_service.search(
                args.query,
                limit=args.limit,
                type=args.type,
                review_state=args.review_state,
                staleness=args.staleness,
                tag=args.tag,
                include_archived=args.include_archived,
            )
            print_json(data)
            return 0
        if args.brain_command == "propose":
            data = brain_service.propose_memories(
                project_id=args.project_id,
                session_id=args.session_id,
                candidates=[
                    {
                        key: value
                        for key, value in {
                            "type": args.type,
                            "statement": args.statement,
                            "title": args.title,
                            "summary": args.summary,
                            "tags": args.tag,
                            "applies_to": args.applies_to,
                            "confidence": args.confidence,
                            "risk_level": args.risk_level,
                        }.items()
                        if value is not None
                    }
                ],
            )
            print_json(data)
            return 0
        if args.brain_command == "candidates":
            print_json(brain_service.list_candidates(review_state=args.review_state))
            return 0
        if args.brain_command == "confirm-candidate":
            print_json(brain_service.confirm_candidate(args.candidate_id))
            return 0
        if args.brain_command == "reject-candidate":
            print_json(brain_service.reject_candidate(args.candidate_id))
            return 0
        raise ValueError(f"Unsupported brain command: {args.brain_command}")

    if args.command == "setup":
        data = _setup_project(
            args,
            runtime=runtime,
            command_runner=command_runner or _run_command,
            agent_detector=agent_detector or shutil.which,
            input_reader=input_reader or _read_interactive_input,
        )
        print_json(data)
        return 0

    if args.command == "import":
        data = runtime.import_project(
            project_id=args.project_id,
            project_path=args.project_path,
            name=args.name,
            options=ImportOptions(
                path_prefixes=args.path_prefix,
                kinds=args.kind,
                node_limit=args.node_limit,
                edge_limit=args.edge_limit,
            ),
            experience_seed=args.experience_seed,
        )
        print_json(data)
        return 0

    if args.command == "list":
        print_json({"projects": [project.to_dict() for project in repository.list_projects()]})
        return 0

    if args.command == "baseline":
        if args.baseline_command == "show":
            print_json(
                {
                    "artifact_path": str(
                        Path(args.store_root)
                        / "projects"
                        / args.project_id
                        / "runs"
                        / "project-baseline-latest.json"
                    ),
                    "baseline": repository.get_run_artifact(args.project_id, "project-baseline-latest.json"),
                }
            )
            return 0
        raise ValueError(f"Unsupported baseline command: {args.baseline_command}")

    if args.command == "intake":
        if args.intake_command == "project":
            print_json(runtime.start_project_intake(project_id=args.project_id))
            return 0
        if args.intake_command == "answer":
            print_json(
                runtime.answer_project_intake(
                    project_id=args.project_id,
                    session_id=args.session_id,
                    answer=args.answer,
                )
            )
            return 0
        raise ValueError(f"Unsupported intake command: {args.intake_command}")

    if args.command == "policy":
        if args.policy_command == "inspect":
            print_json(runtime.inspect_policy(project_id=args.project_id))
            return 0
        raise ValueError(f"Unsupported policy command: {args.policy_command}")

    if args.command == "claim":
        if args.claim_command == "add":
            data = runtime.add_experience_claim(
                project_id=args.project_id,
                statement=args.statement,
                applies_to=args.applies_to,
                risk_level=args.risk_level,
                review_state=args.review_state,
                claim_type=args.claim_type,
                confidence=args.confidence,
                source=args.source,
                claim_id=args.claim_id,
            )
            print_json(data)
            return 0
        if args.claim_command == "list":
            data = runtime.list_experience_claims(
                project_id=args.project_id,
                include_archived=args.include_archived,
            )
            print_json(data)
            return 0
        if args.claim_command == "review":
            data = runtime.review_experience_claim(
                project_id=args.project_id,
                claim_id=args.claim_id,
                statement=args.statement,
                applies_to=args.applies_to,
                risk_level=args.risk_level,
                review_state=args.review_state,
                claim_type=args.claim_type,
                confidence=args.confidence,
                source=args.source,
            )
            print_json(data)
            return 0
        if args.claim_command == "archive":
            data = runtime.archive_experience_claim(
                project_id=args.project_id,
                claim_id=args.claim_id,
                reason=args.reason,
            )
            print_json(data)
            return 0
        raise ValueError(f"Unsupported claim command: {args.claim_command}")

    if args.command == "context":
        data = runtime.build_context_pack(
            project_id=args.project_id,
            task=args.task,
            max_items_per_section=args.max_items_per_section,
        )
        print_json(format_output(data, args.format))
        return 0

    if args.command == "understand":
        data = runtime.build_task_understanding_bundle(
            project_id=args.project_id,
            task=args.task,
            max_items_per_section=args.max_items_per_section,
        )
        if args.format == "agent":
            print_json({"agent_output": data["bundle"]})
        else:
            print_json(data)
        return 0

    if args.command == "impact":
        data = runtime.analyze_impact(
            project_id=args.project_id,
            task=args.task,
            changed_files=args.changed_file,
            changed_symbols=args.changed_symbol,
            max_items_per_section=args.max_items_per_section,
        )
        print_json(format_output(data, args.format))
        return 0

    if args.command == "impact-diff":
        data = runtime.analyze_git_diff_impact(
            project_id=args.project_id,
            task=args.task,
            selection=GitDiffSelection(
                staged=args.staged,
                from_ref=args.from_ref,
                to_ref=args.to_ref,
                last_commit=args.last_commit,
            ),
            changed_symbols=args.changed_symbol,
            max_items_per_section=args.max_items_per_section,
        )
        print_json(format_output(data, args.format))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def _handle_facts(args: argparse.Namespace) -> int:
    if args.facts_command == "inventory":
        adapter = CodeGraphAdapter.from_project_path(args.project_path, args.project_id)
        print_json(adapter.inventory())
        return 0

    if args.facts_command == "export":
        adapter = CodeGraphAdapter.from_project_path(args.project_path, args.project_id)
        print_json(_export_from_adapter(adapter, args))
        return 0

    if args.facts_command == "context":
        export_data = _load_export(args)
        data = ContextPackBuilder(
            task=args.task,
            export=export_data,
            experience_claims=load_experience_seed(args.experience_seed),
            max_items_per_section=args.max_items_per_section,
        ).build()
        print_json(data)
        return 0

    if args.facts_command == "impact":
        export_data = _load_export(args)
        data = ImpactAnalysisBuilder(
            task=args.task,
            export=export_data,
            changed_files=args.changed_file,
            changed_symbols=args.changed_symbol,
            experience_claims=load_experience_seed(args.experience_seed),
            max_items_per_section=args.max_items_per_section,
        ).build()
        print_json(data)
        return 0

    raise ValueError(f"Unsupported facts command: {args.facts_command}")


def _setup_project(
    args: argparse.Namespace,
    *,
    runtime: ProjectBrainRuntime,
    command_runner: Any,
    agent_detector: Any,
    input_reader: Any,
) -> dict[str, Any]:
    project_path = Path(args.project_path).expanduser().resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"Project path not found: {project_path}")
    if not project_path.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {project_path}")

    codegraph_steps: list[dict[str, Any]] = []
    codegraph_db = project_path / ".codegraph" / "codegraph.db"
    if not args.skip_codegraph:
        codegraph_steps.append(_run_setup_command(["codegraph", "init", str(project_path)], project_path, command_runner))
        codegraph_steps.append(_run_setup_command(["codegraph", "index", str(project_path)], project_path, command_runner))
    if not codegraph_db.exists():
        raise FileNotFoundError(
            "CodeGraph database not found after setup. Expected "
            f"{codegraph_db}. Run codegraph init/index or use an existing .codegraph/codegraph.db."
        )

    project_id = args.project_id or _default_project_id(project_path)
    import_data = runtime.import_project(
        project_id=project_id,
        project_path=project_path,
        name=args.name or project_path.name,
        options=ImportOptions(
            path_prefixes=args.path_prefix,
            kinds=args.kind or ["class", "interface", "method", "function"],
            node_limit=args.node_limit,
            edge_limit=args.edge_limit,
        ),
        experience_seed=args.experience_seed,
    )
    context_data = runtime.build_context_pack(project_id=project_id, task=args.task)
    smoke_test = format_output(context_data, "agent")["agent_output"]

    store_root = str(Path(args.store_root).expanduser().resolve())
    mcp_command = args.mcp_command or _default_mcp_command()
    mcp_config = _mcp_config(command=mcp_command, store_root=store_root)
    agents = _setup_agents(
        requested_agents=args.agent,
        mcp_command=mcp_command,
        store_root=store_root,
        command_runner=command_runner,
        agent_detector=agent_detector,
        input_reader=input_reader,
    )
    return {
        "status": "ok",
        "project": import_data["project"],
        "inventory_summary": import_data["inventory_summary"],
        "facts_summary": import_data["facts_summary"],
        "experience_claims": import_data["experience_claims"],
        "codegraph": {
            "database": str(codegraph_db),
            "steps": codegraph_steps,
        },
        "smoke_test": smoke_test,
        "mcp_config": mcp_config,
        "agents": agents,
        "next_agent_prompt": (
            f"Use ProjectBrain MCP project_id '{project_id}'. "
            "Before editing, call projectbrain_context_pack with output_format='agent'. "
            "After editing, call projectbrain_review_git_diff with output_format='agent'."
        ),
    }


def _setup_agents(
    *,
    requested_agents: list[str],
    mcp_command: str,
    store_root: str,
    command_runner: Any,
    agent_detector: Any,
    input_reader: Any,
) -> dict[str, Any]:
    detected = [_agent_status(agent, agent_detector(agent), mcp_command, store_root) for agent in AGENTS]
    selected_agents = requested_agents or _prompt_for_agents(detected, input_reader)
    install_results = [
        _install_agent(agent, detected, mcp_command, store_root, command_runner)
        for agent in selected_agents
    ]
    return {
        "requested": selected_agents,
        "detected": detected,
        "install_results": install_results,
    }


AGENTS = ("codex", "claude", "cursor", "trae")


def _prompt_for_agents(detected: list[dict[str, Any]], input_reader: Any) -> list[str]:
    choices = [agent for agent in detected if agent["installed"] and agent["status"] in {"auto_install_available", "manual_config_available"}]
    if not choices:
        return []
    lines = ["Detected agents:"]
    for index, agent in enumerate(choices, start=1):
        install_note = "auto install" if agent["status"] == "auto_install_available" else "manual config"
        lines.append(f"[{index}] {agent['agent']} ({install_note})")
    lines.append("Install ProjectBrain MCP into which agents? Enter numbers like 1,2 or press Enter to skip: ")
    try:
        answer = input_reader("\n".join(lines))
    except EOFError:
        return []
    return _parse_agent_selection(answer, choices)


def _read_interactive_input(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise EOFError
    print(prompt, file=sys.stderr)
    return input()


def _parse_agent_selection(answer: str, choices: list[dict[str, Any]]) -> list[str]:
    selected: list[str] = []
    for part in answer.split(","):
        value = part.strip()
        if not value:
            continue
        if not value.isdigit():
            continue
        index = int(value)
        if 1 <= index <= len(choices):
            agent = choices[index - 1]["agent"]
            if agent not in selected:
                selected.append(agent)
    return selected


def _agent_status(agent: str, executable: str | None, mcp_command: str, store_root: str) -> dict[str, Any]:
    manual_config = _mcp_config(command=mcp_command, store_root=store_root)
    if agent in {"codex", "claude", "cursor", "trae"}:
        return {
            "agent": agent,
            "installed": bool(executable),
            "executable": executable,
            "status": "auto_install_available" if executable else "not_detected",
            "install_command": _agent_install_command(agent, executable or agent, mcp_command, store_root),
            "manual_config": manual_config,
        }
    return {
        "agent": agent,
        "installed": bool(executable),
        "executable": executable,
        "status": "manual_config_available" if executable else "not_detected",
        "manual_config": manual_config,
    }


def _install_agent(
    agent: str,
    detected: list[dict[str, Any]],
    mcp_command: str,
    store_root: str,
    command_runner: Any,
) -> dict[str, Any]:
    status_by_agent = {item["agent"]: item for item in detected}
    agent_status = status_by_agent[agent]
    if not agent_status["installed"]:
        return {"agent": agent, "status": "not_detected"}
    command = _agent_install_command(agent, agent_status["executable"], mcp_command, store_root)
    result = command_runner(command, cwd=None)
    if result.returncode != 0:
        return {
            "agent": agent,
            "status": "failed",
            "command": command,
            "returncode": result.returncode,
            "stderr": result.stderr,
        }
    return {
        "agent": agent,
        "status": "installed",
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _agent_install_command(agent: str, agent_command: str, mcp_command: str, store_root: str) -> list[str]:
    if agent in {"codex", "claude"}:
        return [
            agent_command,
            "mcp",
            "add",
            "projectbrain",
            "--",
            mcp_command,
            "--store-root",
            store_root,
            "mcp",
            "serve",
        ]
    if agent in {"cursor", "trae"}:
        return [
            agent_command,
            "--add-mcp",
            json.dumps(_vscode_style_mcp_definition(mcp_command, store_root), ensure_ascii=False),
        ]
    raise ValueError(f"Unsupported agent: {agent}")


def _vscode_style_mcp_definition(mcp_command: str, store_root: str) -> dict[str, Any]:
    return {
        "name": "projectbrain",
        "command": mcp_command,
        "args": ["--store-root", store_root, "mcp", "serve"],
    }


def _run_setup_command(command: list[str], cwd: Path, command_runner: Any) -> dict[str, Any]:
    result = command_runner(command, cwd=cwd)
    step = {
        "command": command,
        "cwd": str(cwd),
        "returncode": result.returncode,
    }
    if result.stdout:
        step["stdout"] = result.stdout
    if result.stderr:
        step["stderr"] = result.stderr
    if result.returncode != 0:
        raise RuntimeError(
            f"Setup command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{result.stderr}" if result.stderr else "")
        )
    return step


def _run_command(command: list[str], *, cwd: Path | None = None) -> CommandResult:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return CommandResult(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def _default_project_id(project_path: Path) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", project_path.name.strip()).strip("_").lower()
    return value or "local_project"


def _default_mcp_command() -> str:
    return shutil.which("projectbrain") or sys.argv[0]


def _mcp_config(*, command: str, store_root: str) -> dict[str, Any]:
    return {
        "mcpServers": {
            "projectbrain": {
                "command": command,
                "args": ["--store-root", store_root, "mcp", "serve"],
            }
        }
    }


def _add_fact_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-path", required=True, help="Path to repository containing .codegraph/codegraph.db")
    parser.add_argument("--project-id", required=True, help="ProjectBrain project id")


def _add_export_or_project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--export-json", help="Existing ProjectBrain-shaped export JSON")
    parser.add_argument("--project-path", help="Path to repository containing .codegraph/codegraph.db")
    parser.add_argument("--project-id", default="local_project", help="ProjectBrain project id")


def _add_fact_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path-prefix", action="append", default=[], help="Only export nodes under this path prefix")
    parser.add_argument("--kind", action="append", default=[], help="Only export nodes of this CodeGraph kind")
    parser.add_argument("--node-limit", type=int, default=200)
    parser.add_argument("--edge-limit", type=int, default=300)


def _load_export(args: argparse.Namespace) -> dict[str, Any]:
    if args.export_json:
        with Path(args.export_json).open(encoding="utf-8") as file:
            return json.load(file)
    if not args.project_path:
        raise ValueError("Either --export-json or --project-path is required")
    adapter = CodeGraphAdapter.from_project_path(args.project_path, args.project_id)
    return _export_from_adapter(adapter, args)


def _export_from_adapter(adapter: CodeGraphAdapter, args: argparse.Namespace) -> dict[str, Any]:
    return adapter.export_sample(
        path_prefixes=args.path_prefix or None,
        kinds=args.kind or None,
        node_limit=args.node_limit,
        edge_limit=args.edge_limit,
    )


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
