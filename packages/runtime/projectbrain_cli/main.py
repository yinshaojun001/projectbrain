"""Installable ProjectBrain CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projectbrain_adapters.codegraph import CodeGraphAdapter
from projectbrain_adapters.context_pack import ContextPackBuilder
from projectbrain_adapters.experience import load_experience_seed
from projectbrain_adapters.impact_analysis import ImpactAnalysisBuilder
from projectbrain_cli.mcp_server import serve_stdio
from projectbrain_runtime.models import ImportOptions
from projectbrain_runtime.repository import JsonProjectBrainRepository
from projectbrain_runtime.service import ProjectBrainRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projectbrain",
        description="ProjectBrain local project cognition CLI",
    )
    parser.add_argument("--store-root", default=".projectbrain", help="Runtime store root directory")

    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("doctor", help="Check local ProjectBrain CLI health")

    mcp = subcommands.add_parser("mcp", help="Run ProjectBrain MCP server commands")
    mcp_subcommands = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_subcommands.add_parser("serve", help="Run local-only stdio MCP server")

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

    context = subcommands.add_parser("context", help="Build context pack from imported facts")
    context.add_argument("project_id")
    context.add_argument("task")
    context.add_argument("--max-items-per-section", type=int, default=12)

    impact = subcommands.add_parser("impact", help="Build impact analysis from imported facts")
    impact.add_argument("project_id")
    impact.add_argument("task")
    impact.add_argument("--changed-file", action="append", default=[])
    impact.add_argument("--changed-symbol", action="append", default=[])
    impact.add_argument("--max-items-per-section", type=int, default=12)

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


def main(argv: list[str] | None = None) -> int:
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

    if args.command == "context":
        data = runtime.build_context_pack(
            project_id=args.project_id,
            task=args.task,
            max_items_per_section=args.max_items_per_section,
        )
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
        print_json(data)
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
