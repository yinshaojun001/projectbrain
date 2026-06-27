# ProjectBrain Local Runtime

| Field | Value |
| --- | --- |
| Component | Local Runtime |
| Status | Prototype |
| Last updated | 2026-06-13 |

## 1. Goal

The local runtime upgrades the first CodeGraph adapter prototype from one-shot JSON commands into a small persistent workflow:

```text
import-project
  -> store project metadata, inventory, facts, experience claims
  -> context-pack
  -> impact-analysis
  -> git-diff impact review
```

It is still intentionally zero-dependency. Runtime facts and artifacts remain JSON-backed, while V1 now also bootstraps a local SQLite `knowledge.db` for future knowledge-governance work. This keeps the local prototype easy to run while FastAPI remains optional and fuller database-backed storage is still planned.

## 2. CLI

Entry point:

```text
projectbrain
```

Commands:

```text
doctor       Check local CLI health.
import       Import CodeGraph facts into local runtime storage.
list         List imported projects.
claim        Add local experience claims.
context      Build a context pack from imported facts.
understand   Build a Task Understanding Bundle from imported facts.
impact       Build impact analysis from imported facts.
impact-diff  Build impact analysis from local Git changed file names.
intake       Start minimal intake workflows for project onboarding.
facts        Work directly with CodeGraph facts or exported facts.
mcp          Run the local-only stdio MCP server.
```

`intake project` currently starts a minimal six-step onboarding flow: capture the project goal, primary users, core modules, key flows, third-party integrations, and high-risk areas, while keeping `project-intake-session-latest.json` plus a lightweight `baseline_draft` in sync.

Legacy script entry points under `apps/tools/` are still present for source-tree development, but the installable CLI is preferred.

## 3. Storage Layout

Default store root:

```text
.projectbrain/
```

Project layout:

```text
.projectbrain/
  knowledge.db
  projects/
    <project_id>/
      project.json
      inventory.json
      facts.json
      experience_claims.json
      runs/
        context-pack-latest.json
        impact-analysis-latest.json
```

Files:

| File | Purpose |
| --- | --- |
| `project.json` | Project metadata and import options. |
| `inventory.json` | CodeGraph inventory summary from `.codegraph/codegraph.db`. |
| `facts.json` | ProjectBrain-shaped `entities`, `relations`, and `sources`. |
| `experience_claims.json` | Claims loaded from `experience-seed.md` and claims added locally with `claim add`. |
| `runs/*.json` | Latest generated context/impact artifacts. |

## 4. Local Privacy Policy

Add `.projectbrain-policy.json`, `.projectbrain-policy.yml`, or `.projectbrain-policy.yaml` to the imported project root when outputs need local controls:

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

The policy is loaded from the project source path recorded at import time. It applies to generated Context Pack, Impact Analysis, and Git diff review artifacts before they are saved under `.projectbrain/projects/<project_id>/runs/` or returned through CLI, API, or MCP.

Inspect the policy currently loaded for an imported project:

```bash
projectbrain policy inspect my_project
```

Supported fields:

| Field | Behavior |
| --- | --- |
| `deny_paths` | Glob-like path patterns removed from structured output. |
| `max_items_per_section` | Caps `sections[].items`. |
| `max_recommended_files` | Caps `recommended_files`. |
| `max_recommended_tests` | Caps `recommended_tests`. |
| `include_source_snippets` | Defaults to `false`; source-like fields such as `body`, `snippet`, and `source_code` are stripped unless enabled. |

## 5. Public Demo Without Private Code

The public repository includes a synthetic export under:

```text
examples/payment-mini/projectbrain-codegraph-export.json
```

Generate a Context Pack from that export:

```bash
projectbrain facts context \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```

Generate an Impact Analysis:

```bash
projectbrain facts impact \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Change the settlement contract" \
  --changed-file contract/src/main/java/example/payment/settlement/SettlementService.java
```

## 6. Import Your Own Project

For real local projects, ProjectBrain expects CodeGraph facts at:

```text
<your-project>/.codegraph/codegraph.db
```

Import a bounded scope into the local JSON runtime:

```bash
projectbrain import /path/to/my/project \
  --id my_project \
  --name "My Project" \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method \
  --node-limit 100 \
  --edge-limit 160
```

Do not publish private source code, private CodeGraph databases, or private exported facts.

## 7. Add Local Experience Claims

Add a local human claim:

```bash
projectbrain claim add my_project \
  --id exp_checkout_validation \
  --applies-to checkout \
  --risk high \
  --review-state approved \
  --claim-type HUMAN_CONFIRMED \
  --statement "Checkout validation changes require compatibility review."
```

The claim is stored under:

```text
.projectbrain/projects/my_project/experience_claims.json
```

Later Context Pack and Impact Analysis runs use the updated claims automatically. Do not put secrets, customer data, private URLs, or source code bodies into claim statements.

List, review, and archive local claims:

```bash
projectbrain claim list my_project

projectbrain claim review my_project exp_checkout_validation \
  --review-state needs_review \
  --risk medium

projectbrain claim archive my_project exp_checkout_validation \
  --reason "Superseded by newer checkout guidance."
```

Archived claims stay in `experience_claims.json` and can be listed with `--include-archived`, but Context Pack, Impact Analysis, and Git diff review ignore archived claims.

## 8. Generate Context Pack

After import, this no longer needs `--project-path`, `--path-prefix`, or `--experience-seed`; it uses stored facts.

```bash
projectbrain context my_project "Explain the checkout flow and risk points"
```

Output is written to:

```text
.projectbrain/projects/my_project/runs/context-pack-latest.json
```

## 9. Generate Impact Analysis

```bash
projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java
```

Output is written to:

```text
.projectbrain/projects/my_project/runs/impact-analysis-latest.json
```

Use compact agent output:

```bash
projectbrain context my_project "Explain the checkout flow and risk points" --format agent

projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java \
  --format agent
```

## 10. Review Local Git Diff Impact

Review staged changes:

```bash
projectbrain impact-diff my_project "Review staged checkout changes" --staged
```

Review a branch or ref range:

```bash
projectbrain impact-diff my_project "Review branch impact" --from main --to HEAD
```

Review the last commit:

```bash
projectbrain impact-diff my_project "Review last commit" --last-commit
```

`impact-diff` calls local Git for changed file names, then runs the existing impact analysis over those paths. It does not read or return source file bodies.

Use `--format agent` to return a compact `agent_output` object for AI coding clients:

```bash
projectbrain impact-diff my_project "Review staged checkout changes" --staged --format agent
```

## 11. Current Limits

- Storage is JSON files, not PostgreSQL.
- Import scope is fixed at import time; broaden `--path-prefix` and re-import to analyze more code.
- Impact analysis can use explicit changed files/symbols or local Git changed file names.
- Git diff impact currently matches changed files; symbol-level hunk parsing is planned.
- Agent output is compact structured JSON; richer field selection and policy-driven caps are planned.
- Experience claims can be loaded from Markdown seed tables, added locally, reviewed, and archived; stale-claim detection is still planned.
- The runtime is local-first; FastAPI is optional and MCP exists as a local-only stdio server.

## 12. Repository Boundary

The minimal schema package now exists under:

```text
packages/schema/projectbrain_schema/
```

It defines and validates these V0.1 artifact shapes:

```text
KnowledgeEntity
KnowledgeRelation
SourceRef
ExperienceClaim
ContextPack
ImpactAnalysis
```

The runtime service now depends on a repository interface instead of direct JSON storage:

```text
packages/runtime/projectbrain_runtime/repository.py
```

Current repository types:

| Type | Status | Purpose |
| --- | --- | --- |
| `ProjectBrainRepository` | implemented | Abstract runtime storage contract. |
| `JsonProjectBrainRepository` | implemented | Current zero-dependency JSON-file implementation. |
| `PostgresProjectBrainRepository` | planned | Future DB-backed implementation for API/MCP deployment. |

This keeps the current local runtime usable while preparing the same service layer for FastAPI, MCP, and database-backed storage.

## 13. FastAPI Skeleton

A thin FastAPI service now exists under:

```text
apps/api/projectbrain_api/
```

Routes:

```text
POST /api/v1/projects/import
GET  /api/v1/projects
POST /api/v1/projects/{project_id}/context-pack
POST /api/v1/projects/{project_id}/impact-analysis
```

The API uses `JsonProjectBrainRepository` by default and reads the store root from:

```text
PROJECTBRAIN_STORE_ROOT
```

Install API dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[api]'
```

Run locally:

```bash
PYTHONPATH=apps/api:packages/adapters:packages/runtime:packages/schema \
.venv/bin/uvicorn projectbrain_api.main:app --reload
```

The route handlers are split into `handlers.py`, so tests can validate API behavior without FastAPI installed. When the `api` extra is installed, FastAPI `TestClient` exercises the real HTTP routes.

## 14. Next Step

The next engineering steps are to improve agent-friendly output modes, add request/response schema models for the API boundary, and generate an OpenAPI snapshot:

```text
ImportProjectRequest
ContextPackRequest
ImpactAnalysisRequest
ProjectListResponse
```

After that, the API can be exercised with FastAPI `TestClient` in environments that install the `api` extra.
