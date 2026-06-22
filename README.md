# ProjectBrain

[中文文档](docs/zh/quickstart.md) | [English Quickstart](docs/quickstart.md)

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

Install with Homebrew:

```bash
brew tap yinshaojun001/projectbrain https://github.com/yinshaojun001/projectbrain
brew trust yinshaojun001/projectbrain
brew install projectbrain
projectbrain doctor
```

For local formula testing from a checkout:

```bash
brew tap yinshaojun001/projectbrain /path/to/projectbrain
brew trust yinshaojun001/projectbrain
brew install --build-from-source projectbrain
projectbrain doctor
```

Or install from source:

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

See [Quickstart](docs/quickstart.md) for a fuller walkthrough. A Chinese walkthrough is available at [中文快速上手](docs/zh/quickstart.md).

## Use With Your Own Repository

One command sets up a local repository for agent use:

```bash
projectbrain --store-root ~/.projectbrain-work setup /path/to/my/project \
  --id my_project
```

`setup` runs CodeGraph init/index, imports ProjectBrain facts, runs a Context Pack smoke test, detects local agents, and prompts you to install the MCP server into supported agents such as Codex CLI, Claude Code, Cursor, and Trae. It also prints an MCP config for manual setup:

```bash
projectbrain --store-root /absolute/path/to/.projectbrain-work mcp serve
```

Ask the agent to call `projectbrain_context_pack` before editing and `projectbrain_review_git_diff` after editing, both with `output_format: "agent"`.

For non-interactive setup, pass one or more agents:

```bash
projectbrain --store-root ~/.projectbrain-work setup /path/to/my/project \
  --id my_project \
  --agent codex
```

For manual or advanced setup, ProjectBrain expects CodeGraph facts at:

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

If installed with Homebrew, run the same commands from any directory without the `.venv/bin/` prefix:

```bash
projectbrain --store-root ~/.projectbrain-work import /path/to/my/project \
  --id my_project \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method

projectbrain --store-root ~/.projectbrain-work context my_project "Explain the checkout flow" --format agent
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

JSON routes:

```text
GET    /health
POST   /api/v1/projects/import
GET    /api/v1/projects
POST   /api/v1/projects/{project_id}/context-pack
POST   /api/v1/projects/{project_id}/impact-analysis
POST   /api/v1/projects/{project_id}/impact-analysis/git-diff
GET    /api/v1/projects/{project_id}/policy
GET    /api/v1/projects/{project_id}/claims
POST   /api/v1/projects/{project_id}/claims
PATCH  /api/v1/projects/{project_id}/claims/{claim_id}
DELETE /api/v1/projects/{project_id}/claims/{claim_id}
```

### Optional Observability UI

With the same `--reload` server running, open the local-only HTMX UI at
[http://127.0.0.1:8000/ui/projects](http://127.0.0.1:8000/ui/projects) to:

- import a project through a form (same runtime path as the JSON API),
- inspect the Context Pack a coding agent would receive,
- run Impact Analysis from manual changes, a `git diff`, or the cached
  `impact-analysis-latest.json`,
- view the effective `.projectbrain-policy` (deny paths, output limits,
  source-snippet flag).

The UI is an observability layer for AI-agent context, not a code editor or
code-search tool. It binds to `127.0.0.1` only, ships no third-party CDN by
default when `apps/api/projectbrain_api/ui/static/vendor/htmx.min.js` is
present, and re-uses the same policy enforcement as the CLI/MCP surfaces.

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

Inspect the policy that an imported project is using:

```bash
.venv/bin/projectbrain policy inspect my_project
```

## codex-brain: Run Codex With Project Memory

`codex-brain` starts Codex CLI as an explicit child process for a local project. In the current MVP it initializes the project Brain store, opens the local Brain Explorer URL when `--no-ui` is not set, and runs Codex from the detected project root. Start the local API/UI server separately if it is not already running.

```bash
cd /path/to/my/project
codex-brain
```

The first MVP does not monitor ordinary `codex` sessions, other terminals, the clipboard, or background activity. When managed-session capture or extraction is enabled, its boundary is limited to the Codex CLI child process explicitly started by `codex-brain`.

Project-local Brain data is stored under:

```text
<project>/.projectbrain/brain/
  knowledge_units.jsonl
  memory_candidates.jsonl
  conversations.jsonl
```

Use the Brain Explorer or CLI to review memory candidates proposed through `projectbrain brain propose` or the MCP memory tools:

```bash
projectbrain brain propose /path/to/my/project --type constraint --statement "Refund fee must be booked separately."
projectbrain brain candidates /path/to/my/project
projectbrain brain confirm-candidate /path/to/my/project <candidate_id>
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
| [MCP Usage](docs/mcp-usage.md) | Local-only stdio MCP server usage and privacy boundary. |
| [v0.2 Release Readiness](docs/release-readiness.md) | Release gate checks for tests, CLI/MCP smoke, policy, and privacy boundary. |
| [中文快速上手](docs/zh/quickstart.md) | Chinese quickstart for local install, demo, MCP, claims, and privacy policy. |
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
