# ProjectBrain Local App & Brain Explorer Redesign

| Field | Value |
| --- | --- |
| Status | Draft for review |
| Date | 2026-06-22 |
| Owner | ProjectBrain |
| Scope | Product repositioning, local app mode, project brain store, Brain Explorer UI |

## 1. Problem

ProjectBrain started as a local project cognition layer for AI coding agents. The current implementation is useful for generating Context Packs and Impact Analysis from CodeGraph facts, but the product has drifted away from the original goal: a durable project brain that lives alongside a project and accumulates important knowledge beyond source code.

The desired product is not only an agent output enhancer. It should be a local project knowledge base that combines:

- CodeGraph-based code structure indexing.
- Durable project knowledge extracted from conversations and human experience.
- Searchable, reviewable, and migratable project memory.
- Brain-aware context retrieval before development work.
- Brain-aware impact analysis after code changes.
- A visual local application where users can select a project and inspect its knowledge base.

## 2. Product Repositioning

ProjectBrain should be repositioned as:

> A local project brain application that stores code facts, conversation-derived memory, human-confirmed constraints, decisions, gotchas, workflows, risks, and test guidance for a specific project. It helps developers and AI agents retrieve project knowledge, evaluate impact, and keep the brain up to date as the code changes.

The new product center is the **Project Brain Knowledge Base**. Existing Context Pack and Impact Analysis capabilities become application-layer features that consume the brain, not the core product identity.

## 3. Target User Flow

### 3.1 Local App Flow

```text
Open ProjectBrain
  -> Select or open a local project
  -> ProjectBrain checks code index and brain status
  -> Enter the project Brain Explorer
  -> Search, filter, inspect, and review project knowledge
  -> Codex/MCP writes durable knowledge into the same project brain
  -> Impact analysis reads both code facts and brain knowledge
```

### 3.2 First Implementation Flow

The first implementation should ship as a local app mode command:

```bash
projectbrain app
```

This command should:

1. Start the local FastAPI/HTMX application automatically.
2. Open the user's browser to a Project Picker page.
3. Let the user select or open a project directory.
4. Initialize or locate that project's `.projectbrain/brain/` store.
5. Navigate to the Brain Explorer page for that project.

This validates the product flow quickly. A true desktop wrapper can be added after the web-based local app mode is useful.

### 3.3 Later Desktop Flow

A later phase can package the same backend and UI behind a desktop shell such as PyWebView, Tauri, or Electron:

```text
Double-click ProjectBrain.app
  -> Project Picker
  -> Brain Explorer
```

The user should not need to manually run `uvicorn`, remember a localhost URL, or manage a web server.

## 4. Architecture Overview

```text
ProjectBrain Local App
├── App Registry
│   └── recent projects and preferences
├── Project Picker UI
│   └── open/select local project
├── Project Brain Store
│   └── project-local durable knowledge
├── Code Facts Cache
│   └── CodeGraph-derived entities and relations
├── Brain Explorer UI
│   └── search/filter/detail/review project knowledge
├── CLI
│   └── app, brain remember/list/search/export/import
└── MCP Server
    └── remember/search/list/review/task-context/impact
```

The app, CLI, API, and MCP server must share the same project-local brain data.

## 5. Data Location

ProjectBrain should separate project-owned knowledge from app-owned preferences and generated cache.

### 5.1 Project-local Durable Brain

Stored under the selected project:

```text
<project>/.projectbrain/brain/
  manifest.json
  knowledge_units.jsonl
  concepts.jsonl
  conversations.jsonl
  links.jsonl
```

This directory is the portable project brain. It can be copied, exported, imported, or optionally versioned by the user.

### 5.2 Project-local Generated Data

Stored under:

```text
<project>/.projectbrain/cache/
  code_facts.json
  retrieval_index.json

<project>/.projectbrain/runs/
  context-pack-latest.json
  impact-analysis-latest.json
```

Cache and run artifacts are re-creatable and should not be treated as the durable knowledge source.

### 5.3 App-global Registry

Stored in an OS-appropriate local app data directory in the long term:

```text
~/Library/Application Support/ProjectBrain/recent_projects.json
```

For the initial implementation, an app registry file under the configured store root is acceptable if the OS path abstraction is not yet implemented.

The registry stores only app metadata:

```json
{
  "recent_projects": [
    {
      "project_id": "codeunderstand",
      "name": "codeunderstand",
      "path": "/Users/a58/personal/codeunderstand",
      "last_opened_at": "2026-06-22T00:00:00Z",
      "brain_status": "ready",
      "codegraph_status": "ready"
    }
  ]
}
```

Project knowledge itself must not be stored only in the global registry.

## 6. Brain Data Model

### 6.1 KnowledgeUnit

`KnowledgeUnit` is the durable atomic memory unit for the project brain.

```json
{
  "id": "ku_refund_fee_settlement_constraint",
  "type": "constraint",
  "title": "Refund fee must not change settlement principal",
  "statement": "Refund handling fee must not change settlement principal amount.",
  "summary": "退款手续费需要单独记账，不能影响结算本金。",
  "tags": ["refund", "settlement", "fee"],
  "applies_to": ["refund", "settlement", "RefundService.calculate"],
  "related_code": [
    {
      "kind": "symbol",
      "stable_key": "method:RefundService.calculate",
      "file": "service/refund/RefundService.java",
      "symbol": "RefundService.calculate"
    }
  ],
  "evidence": [
    {
      "type": "conversation",
      "session_id": "session_2026_06_22_refund_fee",
      "summary": "User confirmed this during refund fee design discussion."
    }
  ],
  "confidence": 0.92,
  "risk_level": "high",
  "review_state": "human_confirmed",
  "staleness": {
    "state": "fresh",
    "reason": null
  },
  "created_at": "2026-06-22T00:00:00Z",
  "updated_at": "2026-06-22T00:00:00Z"
}
```

### 6.2 Knowledge Types

The first version supports:

| Type | Meaning |
| --- | --- |
| `constraint` | A rule or invariant that code changes should not violate. |
| `decision` | Architecture, product, technical, or business decision. |
| `gotcha` | A known trap, surprising behavior, or historical caveat. |
| `workflow` | A business or technical flow explanation. |
| `risk` | A known risk area that deserves caution. |
| `test_guidance` | Testing strategy or important test cases. |
| `open_question` | A question that remains unresolved. |
| `concept_note` | Explanation of a domain concept. |
| `incident` | Historical bug, outage, or root-cause note. |

### 6.3 Review States

The first version supports:

| State | Meaning |
| --- | --- |
| `draft` | Locally created but not trusted. |
| `ai_inferred` | Suggested by an AI and not confirmed. |
| `human_review_required` | Needs human validation before high-trust use. |
| `human_confirmed` | Confirmed by a human and safe to use as durable knowledge. |
| `rejected` | Reviewed and rejected. |
| `archived` | Historical, hidden from active retrieval by default. |

### 6.4 Staleness States

The first version supports:

| State | Meaning |
| --- | --- |
| `fresh` | No stale signal. |
| `maybe_stale` | Related code changed and review is recommended. |
| `stale` | Known outdated. |
| `source_missing` | Referenced file or symbol no longer exists in imported facts. |

## 7. Brain Explorer UI

The first visual surface is the Brain Explorer, not a graph map.

### 7.1 Project Picker Page

Route:

```text
GET /ui/app/projects
```

Purpose:

- Show recent projects.
- Open a local project path.
- Show project status: brain ready, needs init, codegraph missing, stale knowledge count.
- Navigate to Brain Explorer.

### 7.2 Brain Explorer Page

Route:

```text
GET /ui/projects/{project_id}/brain
```

Layout:

```text
Header: project name, brain summary counts
Left sidebar: type/review/staleness/tag filters
Center: search input and knowledge list
Right panel: selected knowledge detail
```

The first version must show:

- Total knowledge count.
- Count by knowledge type.
- Count by review state.
- Count by staleness.
- Search box.
- Type filter.
- Review-state filter.
- Staleness filter.
- Knowledge cards/list.
- Detail panel.

### 7.3 Knowledge Card

Each knowledge card should display:

- Title or short statement.
- Type.
- Review state.
- Risk level.
- Tags.
- Applies-to summary.
- Related-code count.
- Updated timestamp.

### 7.4 Knowledge Detail Panel

The detail panel should display:

- Title.
- Type.
- Statement.
- Summary.
- Tags.
- Applies-to values.
- Related code references.
- Evidence.
- Conversation references.
- Review state.
- Confidence.
- Risk level.
- Staleness.
- Created/updated timestamps.

### 7.5 First-version Actions

The first UI version should allow lightweight review actions:

- Mark as `human_confirmed`.
- Mark as `rejected`.
- Mark as `archived`.
- Mark as `maybe_stale` or `fresh`.

Full rich editing can wait. New knowledge is primarily created through CLI/MCP in the first phase.

## 8. API Design

### 8.1 App API

```text
GET  /api/v1/app/projects
POST /api/v1/app/projects/open
```

`POST /api/v1/app/projects/open` accepts:

```json
{
  "project_path": "/path/to/project",
  "project_id": "optional_id"
}
```

It returns:

```json
{
  "project": {
    "project_id": "codeunderstand",
    "name": "codeunderstand",
    "path": "/Users/a58/personal/codeunderstand"
  },
  "brain_status": "ready",
  "codegraph_status": "missing | ready | stale",
  "next_url": "/ui/projects/codeunderstand/brain"
}
```

### 8.2 Brain API

```text
GET   /api/v1/projects/{project_id}/brain/summary
GET   /api/v1/projects/{project_id}/brain/knowledge
GET   /api/v1/projects/{project_id}/brain/knowledge/{knowledge_id}
POST  /api/v1/projects/{project_id}/brain/knowledge
PATCH /api/v1/projects/{project_id}/brain/knowledge/{knowledge_id}
```

List endpoint query parameters:

```text
q
kind or type
review_state
staleness
risk_level
tag
limit
offset
```

## 9. CLI Design

### 9.1 Local App Mode

```bash
projectbrain app
```

Options:

```bash
projectbrain app --host 127.0.0.1 --port 0
projectbrain app --project /path/to/project
```

Behavior:

- Start local API/UI server.
- Pick an available port if not specified.
- Open browser automatically unless disabled.
- If `--project` is provided, open or initialize that project and navigate directly to its Brain Explorer.

### 9.2 Brain Commands

```bash
projectbrain brain init <project_path> --id my_project
projectbrain brain remember my_project \
  --type constraint \
  --statement "Refund handling fee must not change settlement principal amount." \
  --applies-to refund \
  --applies-to settlement \
  --review-state human_confirmed

projectbrain brain list my_project
projectbrain brain search my_project "refund fee settlement"
projectbrain brain export my_project --output my_project.projectbrain.zip
projectbrain brain import --input my_project.projectbrain.zip --id my_project
```

Existing `claim` commands should remain for compatibility but should write/read compatible `KnowledgeUnit` records over time.

## 10. MCP Design

The first Brain-oriented MCP tools should be:

### 10.1 `projectbrain_remember`

Writes durable knowledge into the selected project's brain.

```json
{
  "project_id": "my_project",
  "type": "constraint",
  "statement": "Refund handling fee must not change settlement principal amount.",
  "applies_to": ["refund", "settlement"],
  "review_state": "human_confirmed",
  "tags": ["refund", "fee"],
  "source": ["conversation://current"]
}
```

### 10.2 `projectbrain_search_brain`

Searches durable project knowledge.

```json
{
  "project_id": "my_project",
  "query": "refund fee settlement",
  "types": ["constraint", "decision", "gotcha"],
  "limit": 10
}
```

### 10.3 `projectbrain_list_memory`

Lists brain knowledge units with filters.

```json
{
  "project_id": "my_project",
  "types": ["constraint"],
  "review_state": "human_confirmed",
  "include_archived": false
}
```

### 10.4 `projectbrain_review_memory`

Updates review/staleness metadata.

```json
{
  "project_id": "my_project",
  "memory_id": "ku_refund_fee_settlement_constraint",
  "review_state": "human_confirmed"
}
```

Existing Context Pack and Impact MCP tools should later become brain-aware by including relevant `KnowledgeUnit` records.

## 11. Retrieval Design

The first version should use local lexical scoring. It should not require embeddings, a vector database, or network services.

Search should match:

- `title`
- `statement`
- `summary`
- `tags`
- `applies_to`
- related code file paths
- related symbol names
- evidence summaries

Boosts:

- Exact tag match.
- Exact applies-to match.
- Human-confirmed knowledge.
- Constraint/risk/gotcha types for impact-sensitive tasks.
- High risk level.

## 12. Brain-aware Context and Impact

### 12.1 Context

Existing Context Pack should be upgraded to include:

- `relevant_knowledge_units`
- `relevant_constraints`
- `relevant_decisions`
- `relevant_gotchas`
- `relevant_test_guidance`
- `open_questions`

The current `experience_claims` section should become a compatibility view over relevant `KnowledgeUnit` records.

### 12.2 Impact

Existing Impact Analysis should be upgraded to include:

- `affected_knowledge_units`
- `possibly_stale_knowledge`
- `violated_or_relevant_constraints`
- `related_decisions`
- `brain_update_suggestions`

This is the mechanism that supports global impact evaluation beyond direct code graph neighbors.

## 13. Migration and Compatibility

Current `experience_claims.json` records should not be discarded.

Compatibility plan:

1. Keep old claim commands working.
2. Map each experience claim into a `KnowledgeUnit` view.
3. New brain commands write to `knowledge_units.jsonl`.
4. Context/impact retrieval reads both sources during transition.
5. Add a migration command later:

```bash
projectbrain brain migrate-claims my_project
```

## 14. Phased Implementation Plan

### Phase 1: Brain Core + Local App Mode

Must include:

- `KnowledgeUnit` model.
- Project-local `.projectbrain/brain/` layout.
- Brain repository with JSONL persistence.
- Brain summary/list/search/detail/update functions.
- `projectbrain app` command that starts UI and opens Project Picker.
- Project Picker route.
- Brain Explorer route.
- CLI `brain remember/list/search`.
- MCP `projectbrain_remember`, `projectbrain_search_brain`, `projectbrain_list_memory`, `projectbrain_review_memory`.

### Phase 2: Brain-aware Context and Impact

Must include:

- Context Pack includes relevant brain knowledge.
- Impact Analysis includes affected knowledge and stale suggestions.
- Git diff impact uses brain knowledge.
- Tests cover code + brain combined impact.

### Phase 3: Export/Import and Migration

Must include:

- Brain export package.
- Brain import.
- Claim migration command.
- App UI for export/import.

### Phase 4: Desktop Wrapper

Must include:

- PyWebView or Tauri prototype.
- Automatic backend lifecycle management.
- Packaged local app for macOS first.

### Phase 5: Relationship Graph and Advanced Review

Potential future scope:

- Knowledge-code graph visualization.
- Conversation memory inbox.
- Staleness review queue.
- Brain health score.
- Optional embedding index.

## 15. Testing Strategy

### Unit Tests

- `KnowledgeUnit` validation and defaults.
- JSONL repository append/list/update behavior.
- Search scoring and filters.
- Summary stats.
- App project registry.

### API Tests

- Open project.
- Brain summary.
- Brain list/search/detail.
- Brain update review state.

### CLI Tests

- `projectbrain brain remember` writes a knowledge unit.
- `projectbrain brain search` finds it.
- `projectbrain app --project` resolves the target project.

### MCP Tests

- `projectbrain_remember` writes local brain memory.
- `projectbrain_search_brain` returns it.
- `projectbrain_review_memory` updates state.

### UI Smoke Tests

- Project Picker renders.
- Brain Explorer renders.
- Search/filter returns expected visible content.
- Detail panel renders selected knowledge.

## 16. Non-goals for First Version

- Native desktop packaging.
- Complex graph visualization.
- Automatic LLM extraction inside ProjectBrain.
- Vector database.
- Cloud sync.
- Multi-user collaboration.
- Full rich-text knowledge editor.
- Authentication and permissions.

## 17. Open Decisions

1. Whether the first app registry should live under OS app data or under `--store-root`.
2. Whether `.projectbrain/brain/` should be recommended for Git versioning by default or only exported manually.
3. Whether first-version UI should support creating knowledge units manually or only reviewing existing units.
4. Whether PyWebView or Tauri is preferred for the desktop wrapper phase.

## 18. Recommended First Cut

The recommended first cut is:

1. Implement Brain Core and JSONL store.
2. Implement CLI/MCP memory commands.
3. Implement local app mode with Project Picker and Brain Explorer.
4. Keep new knowledge creation primarily through CLI/MCP.
5. Let the UI read, search, filter, inspect, and lightly review knowledge.
6. Delay graph visualization and desktop packaging until the local app mode validates the experience.
