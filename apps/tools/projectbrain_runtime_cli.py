#!/usr/bin/env python3
"""CLI for the local ProjectBrain runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))

from projectbrain_runtime.models import ImportOptions  # noqa: E402
from projectbrain_runtime.repository import JsonProjectBrainRepository  # noqa: E402
from projectbrain_runtime.service import ProjectBrainRuntime  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProjectBrain local runtime CLI")
    parser.add_argument("--store-root", default=".projectbrain", help="Runtime store root directory")

    subcommands = parser.add_subparsers(dest="command", required=True)

    import_project = subcommands.add_parser("import-project", help="Import CodeGraph facts into local runtime")
    import_project.add_argument("--project-id", required=True)
    import_project.add_argument("--project-path", required=True)
    import_project.add_argument("--name")
    import_project.add_argument("--experience-seed")
    import_project.add_argument("--path-prefix", action="append", default=[])
    import_project.add_argument("--kind", action="append", default=[])
    import_project.add_argument("--node-limit", type=int, default=200)
    import_project.add_argument("--edge-limit", type=int, default=300)

    subcommands.add_parser("list-projects", help="List imported projects")

    context_pack = subcommands.add_parser("context-pack", help="Build context pack from imported facts")
    context_pack.add_argument("--project-id", required=True)
    context_pack.add_argument("--task", required=True)
    context_pack.add_argument("--max-items-per-section", type=int, default=12)

    impact = subcommands.add_parser("impact-analysis", help="Build impact analysis from imported facts")
    impact.add_argument("--project-id", required=True)
    impact.add_argument("--task", required=True)
    impact.add_argument("--changed-file", action="append", default=[])
    impact.add_argument("--changed-symbol", action="append", default=[])
    impact.add_argument("--max-items-per-section", type=int, default=12)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = JsonProjectBrainRepository(args.store_root)
    runtime = ProjectBrainRuntime(repository)

    if args.command == "import-project":
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

    if args.command == "list-projects":
        print_json({"projects": [project.to_dict() for project in repository.list_projects()]})
        return 0

    if args.command == "context-pack":
        data = runtime.build_context_pack(
            project_id=args.project_id,
            task=args.task,
            max_items_per_section=args.max_items_per_section,
        )
        print_json(data)
        return 0

    if args.command == "impact-analysis":
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


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
