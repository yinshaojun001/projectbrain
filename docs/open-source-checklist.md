# Open Source Checklist

Use this checklist before pushing ProjectBrain to a public GitHub repository.

## Required Before Push

- Real project source code is not tracked.
- Real CodeGraph databases are not tracked.
- Real configuration files, private keys, and production URLs are not tracked.
- `.projectbrain/`, `.venv/`, `*.egg-info/`, and cache directories are ignored.
- Public examples are synthetic and marked as synthetic.
- Tests pass from a clean checkout with only public files.

## Current Repository Boundary

The public repository should include:

- `apps/`
- `packages/`
- `tests/`
- `examples/payment-mini/`
- `.planning/` public planning docs
- `docs/projectbrain/` design and runtime docs
- `README.md`
- `pyproject.toml`
- `LICENSE`

The public repository should not include:

- `docs/payment/`
- `docs/projectbrain/pilots/zhangfang/`
- `examples/zhangfang/`
- any `.codegraph/codegraph.db` generated from private code
- any `.projectbrain/` runtime store generated from private code

## First Public Release Scope

ProjectBrain is currently a local prototype:

- CodeGraph export adapter
- Context Pack builder
- Impact Analysis builder
- Git diff impact analysis
- JSON-file runtime
- local-only stdio MCP server
- optional FastAPI skeleton

It is not yet a hosted service, full RAG system, or autonomous code modifier.
