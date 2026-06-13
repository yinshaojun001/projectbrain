# ProjectBrain

ProjectBrain is a local project cognition layer for AI coding agents.

It turns code-structure facts and human project experience into task-scoped artifacts that an AI agent can use before changing code:

- **Context Pack**: the files, symbols, flows, risks, and human notes relevant to a task.
- **Impact Analysis**: the files, symbols, callers, dependencies, tests, and review risks likely affected by a change.
- **Git Diff Impact**: a local review of staged, branch, or last-commit changes based on changed file names from Git.

ProjectBrain is not a code search UI, a generic RAG chatbot, or an automatic code modifier. The first public version is a small local prototype that is useful for experimenting with project memory and impact analysis workflows.

## Status

Prototype / local MVP.

Current capabilities:

- CodeGraph SQLite adapter.
- ProjectBrain JSON schema models and validation.
- Context Pack builder.
- Impact Analysis builder.
- Git diff Impact Analysis from local Git changed files.
- Agent-friendly compact output for Context Pack and Impact Analysis.
- Local experience claim authoring.
- JSON-file local runtime.
- Local-only stdio MCP server.
- Optional FastAPI API skeleton.
- Synthetic public demo under `examples/payment-mini/`.

## Quickstart

Install locally:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/projectbrain doctor
```

Run the tests:

```bash
python3 -m unittest discover -s tests
```

Generate a Context Pack from the synthetic public demo:

```bash
.venv/bin/projectbrain facts context \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```

Generate an Impact Analysis:

```bash
.venv/bin/projectbrain facts impact \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Change the settlement contract" \
  --changed-file contract/src/main/java/example/payment/settlement/SettlementService.java
```

See [Quickstart](docs/quickstart.md) for a fuller walkthrough.

## Use With Your Own Repository

ProjectBrain currently expects CodeGraph facts at:

```text
<your-project>/.codegraph/codegraph.db
```

Import a local project into the JSON runtime:

```bash
.venv/bin/projectbrain import /path/to/my/project \
  --id my_project \
  --name "My Project" \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method
```

Then generate artifacts from the stored facts:

```bash
.venv/bin/projectbrain context my_project "Explain the checkout flow"

.venv/bin/projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java

.venv/bin/projectbrain impact-diff my_project "Review staged checkout changes" --staged

.venv/bin/projectbrain impact-diff my_project "Review branch impact" --from main --to HEAD
```

Use compact output when an AI coding agent needs the next actions without the full artifact:

```bash
.venv/bin/projectbrain context my_project "Explain the checkout flow" --format agent

.venv/bin/projectbrain impact-diff my_project "Review staged checkout changes" --staged --format agent
```

Add local project experience so future context and impact results include human constraints:

```bash
.venv/bin/projectbrain claim add my_project \
  --id exp_checkout_validation \
  --applies-to checkout \
  --risk high \
  --review-state approved \
  --claim-type HUMAN_CONFIRMED \
  --statement "Checkout validation changes require compatibility review."
```

Review and archive local claims without deleting their history:

```bash
.venv/bin/projectbrain claim list my_project

.venv/bin/projectbrain claim review my_project exp_checkout_validation \
  --review-state needs_review \
  --risk medium

.venv/bin/projectbrain claim archive my_project exp_checkout_validation \
  --reason "Superseded by newer checkout guidance."
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

## Local MCP Server

ProjectBrain can run as a local stdio MCP server for AI coding agents:

```bash
.venv/bin/projectbrain --store-root /absolute/path/to/.projectbrain mcp serve
```

It is a local child process. It does not open network sockets or upload source code. See [Local MCP Usage](docs/mcp-usage.md).

MCP tools include project import, project listing, experience claim authoring, Context Packs, Impact Analysis, and Git diff review through `projectbrain_review_git_diff`. The read tools accept `output_format: "agent"` for compact agent-oriented results.

Privacy note: ProjectBrain controls the tool side, not the AI client side. MCP results may contain file paths, symbol names, and inferred risk notes. Whether those results are sent to a model provider depends on your AI client and model settings. For strict private-code environments, use a local model or an approved enterprise endpoint.

For additional local output controls, add `.projectbrain-policy.json` or `.projectbrain-policy.yml` to the imported project root:

```json
{
  "deny_paths": ["private/**", "src/main/resources/config/**"],
  "output_limits": {
    "max_items_per_section": 8,
    "max_recommended_files": 8,
    "max_recommended_tests": 5
  },
  "include_source_snippets": false
}
```

Context Pack, Impact Analysis, Git diff review, API, and MCP read outputs apply the policy. Source snippets remain disabled by default.

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
| [MCP Usage](docs/mcp-usage.md) | Local-only stdio MCP server usage and privacy boundary. |
| [Delivery Gap Analysis](docs/projectbrain/delivery-gap-analysis.md) | Remaining gaps between design and implementation. |
| [Evaluation Plan](docs/projectbrain/evaluation-plan.md) | How to evaluate context quality, impact quality, and agent outcomes. |

## Roadmap

- Add typed API request/response models.
- Add OpenAPI snapshot tests.
- Add richer Git diff symbol matching.
- Add richer agent output controls.
- Add project experience review and stale-claim workflow.
- Add database-backed repository implementation.
- Add more language adapters and richer source-fact extraction.

## License

MIT
