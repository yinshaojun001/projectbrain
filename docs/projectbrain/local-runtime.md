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

It is still intentionally zero-dependency and uses JSON files instead of a database. This keeps the local prototype easy to run while FastAPI remains optional and database-backed storage is still planned.

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
context      Build a context pack from imported facts.
impact       Build impact analysis from imported facts.
impact-diff  Build impact analysis from local Git changed file names.
facts        Work directly with CodeGraph facts or exported facts.
mcp          Run the local-only stdio MCP server.
```

Legacy script entry points under `apps/tools/` are still present for source-tree development, but the installable CLI is preferred.

## 3. Storage Layout

Default store root:

```text
.projectbrain/
```

Project layout:

```text
.projectbrain/
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
| `experience_claims.json` | Claims loaded from `experience-seed.md`. |
| `runs/*.json` | Latest generated context/impact artifacts. |

## 4. Public Demo Without Private Code

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

## 5. Import Your Own Project

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

## 6. Generate Context Pack

After import, this no longer needs `--project-path`, `--path-prefix`, or `--experience-seed`; it uses stored facts.

```bash
projectbrain context my_project "Explain the checkout flow and risk points"
```

Output is written to:

```text
.projectbrain/projects/my_project/runs/context-pack-latest.json
```

## 7. Generate Impact Analysis

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

## 8. Review Local Git Diff Impact

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

## 9. Current Limits

- Storage is JSON files, not PostgreSQL.
- Import scope is fixed at import time; broaden `--path-prefix` and re-import to analyze more code.
- Impact analysis can use explicit changed files/symbols or local Git changed file names.
- Git diff impact currently matches changed files; symbol-level hunk parsing is planned.
- Agent output is compact structured JSON; richer field selection and policy-driven caps are planned.
- Experience claims are loaded from Markdown seed tables; review workflow is manual.
- The runtime is local-first; FastAPI is optional and MCP exists as a local-only stdio server.

## 10. Repository Boundary

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

## 11. FastAPI Skeleton

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

## 12. Next Step

The next engineering steps are to improve agent-friendly output modes, add request/response schema models for the API boundary, and generate an OpenAPI snapshot:

```text
ImportProjectRequest
ContextPackRequest
ImpactAnalysisRequest
ProjectListResponse
```

After that, the API can be exercised with FastAPI `TestClient` in environments that install the `api` extra.
