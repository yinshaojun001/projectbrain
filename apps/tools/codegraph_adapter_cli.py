#!/usr/bin/env python3
"""CLI for the minimal ProjectBrain CodeGraph adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))

from projectbrain_adapters.context_pack import ContextPackBuilder  # noqa: E402
from projectbrain_adapters.codegraph import CodeGraphAdapter, dump_json  # noqa: E402
from projectbrain_adapters.experience import load_experience_seed  # noqa: E402
from projectbrain_adapters.impact_analysis import ImpactAnalysisBuilder  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProjectBrain CodeGraph adapter CLI")
    parser.add_argument("--project-path", required=True, help="Path to repository containing .codegraph/codegraph.db")
    parser.add_argument("--project-id", required=True, help="ProjectBrain project id")

    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("inventory", help="Print CodeGraph inventory JSON")

    export = subcommands.add_parser("export-sample", help="Export ProjectBrain-shaped sample JSON")
    export.add_argument("--path-prefix", action="append", default=[], help="Only export nodes under this path prefix")
    export.add_argument("--kind", action="append", default=[], help="Only export nodes of this CodeGraph kind")
    export.add_argument("--node-limit", type=int, default=200)
    export.add_argument("--edge-limit", type=int, default=300)

    context_pack = subcommands.add_parser("context-pack", help="Build a first ProjectBrain context pack")
    context_pack.add_argument("--task", required=True, help="Task or question the context pack should answer")
    context_pack.add_argument("--export-json", help="Existing ProjectBrain-shaped export JSON")
    context_pack.add_argument("--experience-seed", help="Markdown experience seed table")
    context_pack.add_argument("--path-prefix", action="append", default=[], help="Only export nodes under this path prefix")
    context_pack.add_argument("--kind", action="append", default=[], help="Only export nodes of this CodeGraph kind")
    context_pack.add_argument("--node-limit", type=int, default=200)
    context_pack.add_argument("--edge-limit", type=int, default=300)
    context_pack.add_argument("--max-items-per-section", type=int, default=12)

    impact = subcommands.add_parser("impact-analysis", help="Build a first ProjectBrain impact analysis")
    impact.add_argument("--task", required=True, help="Task or change the impact analysis should evaluate")
    impact.add_argument("--export-json", help="Existing ProjectBrain-shaped export JSON")
    impact.add_argument("--experience-seed", help="Markdown experience seed table")
    impact.add_argument("--changed-file", action="append", default=[], help="Changed file path")
    impact.add_argument("--changed-symbol", action="append", default=[], help="Changed symbol name or qualified name")
    impact.add_argument("--path-prefix", action="append", default=[], help="Only export nodes under this path prefix")
    impact.add_argument("--kind", action="append", default=[], help="Only export nodes of this CodeGraph kind")
    impact.add_argument("--node-limit", type=int, default=200)
    impact.add_argument("--edge-limit", type=int, default=300)
    impact.add_argument("--max-items-per-section", type=int, default=12)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter = CodeGraphAdapter.from_project_path(args.project_path, args.project_id)

    if args.command == "inventory":
        print(dump_json(adapter.inventory()), end="")
        return 0

    if args.command == "export-sample":
        data = adapter.export_sample(
            path_prefixes=args.path_prefix or None,
            kinds=args.kind or None,
            node_limit=args.node_limit,
            edge_limit=args.edge_limit,
        )
        print(dump_json(data), end="")
        return 0

    if args.command == "context-pack":
        if args.export_json:
            with Path(args.export_json).open(encoding="utf-8") as file:
                export_data = json.load(file)
        else:
            export_data = adapter.export_sample(
                path_prefixes=args.path_prefix or None,
                kinds=args.kind or None,
                node_limit=args.node_limit,
                edge_limit=args.edge_limit,
            )
        data = ContextPackBuilder(
            task=args.task,
            export=export_data,
            experience_claims=load_experience_seed(args.experience_seed),
            max_items_per_section=args.max_items_per_section,
        ).build()
        print(dump_json(data), end="")
        return 0

    if args.command == "impact-analysis":
        if args.export_json:
            with Path(args.export_json).open(encoding="utf-8") as file:
                export_data = json.load(file)
        else:
            export_data = adapter.export_sample(
                path_prefixes=args.path_prefix or None,
                kinds=args.kind or None,
                node_limit=args.node_limit,
                edge_limit=args.edge_limit,
            )
        data = ImpactAnalysisBuilder(
            task=args.task,
            export=export_data,
            changed_files=args.changed_file,
            changed_symbols=args.changed_symbol,
            experience_claims=load_experience_seed(args.experience_seed),
            max_items_per_section=args.max_items_per_section,
        ).build()
        print(dump_json(data), end="")
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
