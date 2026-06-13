# ProjectBrain

ProjectBrain is a local project cognition layer for AI coding agents.

It turns code-structure facts and human project experience into task-scoped artifacts that an AI agent can use before changing code:

- **Context Pack**: the files, symbols, flows, risks, and human notes relevant to a task.
- **Impact Analysis**: the files, symbols, callers, dependencies, tests, and review risks likely affected by a change.

ProjectBrain is not a code search UI, a generic RAG chatbot, or an automatic code modifier. The first public version is a small local prototype that is useful for experimenting with project memory and impact analysis workflows.

## Status

Prototype / local MVP.

Current capabilities:

- CodeGraph SQLite adapter.
- ProjectBrain JSON schema models and validation.
- Context Pack builder.
- Impact Analysis builder.
- JSON-file local runtime.
- Optional FastAPI API skeleton.
- Synthetic public demo under `examples/payment-mini/`.

## Quickstart

Run the tests:

```bash
python3 -m unittest discover -s tests
```

Generate a Context Pack from the synthetic public demo:

```bash
python3 apps/tools/codegraph_adapter_cli.py \
  --project-path . \
  --project-id payment_mini \
  context-pack \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```

Generate an Impact Analysis:

```bash
python3 apps/tools/codegraph_adapter_cli.py \
  --project-path . \
  --project-id payment_mini \
  impact-analysis \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Change the settlement contract" \
  --changed-file contract/src/main/java/example/payment/settlement/SettlementService.java
```

## Use With Your Own Repository

ProjectBrain currently expects CodeGraph facts at:

```text
<your-project>/.codegraph/codegraph.db
```

Import a local project into the JSON runtime:

```bash
python3 apps/tools/projectbrain_runtime_cli.py \
  import-project \
  --project-id my_project \
  --project-path /path/to/my/project \
  --name "My Project" \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method
```

Then generate artifacts from the stored facts:

```bash
python3 apps/tools/projectbrain_runtime_cli.py \
  context-pack \
  --project-id my_project \
  --task "Explain the checkout flow"

python3 apps/tools/projectbrain_runtime_cli.py \
  impact-analysis \
  --project-id my_project \
  --task "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java
```

Runtime artifacts are written under `.projectbrain/`, which is ignored by Git.

## Optional FastAPI Server

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[api]'

PYTHONPATH=apps/api:packages/adapters:packages/runtime:packages/schema \
.venv/bin/uvicorn projectbrain_api.main:app --reload
```

Routes:

```text
GET  /health
POST /api/v1/projects/import
GET  /api/v1/projects
POST /api/v1/projects/{project_id}/context-pack
POST /api/v1/projects/{project_id}/impact-analysis
```

## Repository Layout

```text
apps/
  tools/                 CLI tools
  api/projectbrain_api/  optional FastAPI API
packages/
  adapters/              CodeGraph adapter and artifact builders
  runtime/               local JSON runtime and repository abstraction
  schema/                dataclass schemas and validation
examples/payment-mini/   synthetic public demo data
tests/                   unit and API tests
docs/                    design and implementation notes
```

## Public Data Boundary

This repository intentionally does not include real project source code, real CodeGraph databases, private configs, or production runtime stores.

The public demo is synthetic. If you use ProjectBrain on a private repository, keep these paths out of Git:

- `docs/payment/`
- `.projectbrain/`
- `.codegraph/` generated from private code
- private experience seeds
- private exported facts

See [Open Source Checklist](docs/open-source-checklist.md).

## Design Docs

| Document | Purpose |
| --- | --- |
| [Design Document](docs/projectbrain/design-document.md) | Product positioning, architecture, components, APIs, and roadmap. |
| [Domain Model](docs/projectbrain/domain-model.md) | Project cognition domain model and bounded contexts. |
| [Knowledge Schema](docs/projectbrain/knowledge-schema.md) | Knowledge graph, source refs, claims, confidence, and lifecycle. |
| [MVP Architecture](docs/projectbrain/mvp-architecture.md) | Local MVP architecture, service boundaries, storage, and acceptance criteria. |
| [Implementation Plan](docs/projectbrain/implementation-plan.md) | Engineering phases, tests, operations, and open-source setup. |
| [Agent Skills](docs/projectbrain/agent-skills.md) | Agent-facing skills for project understanding and impact analysis. |
| [API Contract](docs/projectbrain/api-contract.md) | REST and MCP contract draft. |
| [CodeGraph Integration](docs/projectbrain/codegraph-integration.md) | CodeGraph as the first code-fact provider. |
| [Local Runtime](docs/projectbrain/local-runtime.md) | CLI/runtime/API usage for the current local prototype. |
| [Delivery Gap Analysis](docs/projectbrain/delivery-gap-analysis.md) | Remaining gaps between design and implementation. |
| [Evaluation Plan](docs/projectbrain/evaluation-plan.md) | How to evaluate context quality, impact quality, and agent outcomes. |

## Roadmap

- Add typed API request/response models.
- Add OpenAPI snapshot tests.
- Add import support for Git diffs.
- Add project experience review workflow.
- Add MCP tools for AI coding agents.
- Add database-backed repository implementation.
- Add more language adapters and richer source-fact extraction.

## License

MIT
