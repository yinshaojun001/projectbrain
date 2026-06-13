# ProjectBrain PRD

| Field | Value |
| --- | --- |
| Product | ProjectBrain |
| Version | v0.2 planning |
| Status | Active development |
| Last updated | 2026-06-13 |

## 1. Product Positioning

ProjectBrain is a local-first project memory and impact analysis layer for AI coding agents.

It helps an AI agent answer these questions before editing code:

- What context is relevant to this task?
- Which files, symbols, flows, and tests should be inspected?
- What human-confirmed or human-review-required constraints apply?
- What is likely affected by the current code change?
- Does this change need manual review?

ProjectBrain is not a dashboard-first code graph explorer, generic RAG chatbot, or automatic code modifier.

## 2. Differentiation

Tools like Understand-Anything focus on broad codebase understanding, interactive knowledge graphs, search, and onboarding views.

ProjectBrain focuses on the agent execution moment:

```text
AI agent receives task
  -> asks ProjectBrain for scoped context
  -> edits code
  -> asks ProjectBrain for impact and risk review
  -> runs recommended tests / requests human review
```

The product wedge is:

- local-only MCP server
- privacy-first private-code workflow
- task-scoped Context Packs
- Git diff Impact Analysis
- first-class human experience claims
- stale knowledge lifecycle

## 3. Target Users

- Developers using AI coding agents on private repositories.
- Maintainers of large legacy systems where project knowledge is distributed across code, conventions, and human experience.
- Platform engineers building local or enterprise AI software engineering workflows.
- Open-source maintainers who want agent-readable project context without building a full documentation portal.

## 4. Core User Stories

### US1: Agent Gets Task Context

As a developer using an AI coding agent, I want the agent to request a Context Pack before editing so it reads the right files and risk notes.

Acceptance:

- Agent can call local MCP tool `projectbrain_context_pack`.
- Output includes recommended files, symbols, flows, risks, tests, and omissions.
- Output does not include full source code by default.

### US2: Agent Reviews Current Diff

As a developer, I want the agent to analyze staged or branch diff impact before committing.

Acceptance:

- CLI supports staged diff impact.
- CLI supports branch/range diff impact.
- MCP exposes a local tool for diff impact.
- Output includes changed files, matched entities, affected relations, recommended tests, and review recommendation.

### US3: Developer Adds Project Experience

As a project maintainer, I want to record constraints and tribal knowledge as experience claims.

Acceptance:

- CLI can add a claim to local project storage.
- Claims have risk level, review state, applies-to tags, statement, confidence, and source.
- Context Pack and Impact Analysis can match claims to selected entities.

### US4: Privacy Policy Controls Output

As a developer on private code, I want local policy controls so ProjectBrain minimizes tool output and never returns source snippets by default.

Acceptance:

- `.projectbrain-policy.yml` or JSON policy can set output limits and deny paths.
- MCP tools apply output limits.
- Documentation clearly separates tool-side privacy from AI-client privacy.

### US5: Knowledge Becomes Stale When Code Moves

As a maintainer, I want ProjectBrain to mark old claims stale when their source files or symbols change.

Acceptance:

- Brain Update can compare source refs to changed files/symbols.
- Impact output can warn about stale or source-missing claims.
- Claims can be reviewed and re-approved.

## 5. Non-Goals

- Build a visual graph dashboard before the local agent workflow is strong.
- Replace CodeGraph as a code facts provider in v0.2.
- Upload source code to a hosted ProjectBrain service.
- Modify code automatically.
- Become a general document search product.

## 6. Current Capabilities

- Installable CLI: `projectbrain`.
- Local JSON runtime under `.projectbrain/`.
- CodeGraph SQLite adapter.
- Context Pack builder.
- Impact Analysis builder.
- Git diff Impact Analysis from local Git changed file names.
- Local-only stdio MCP server.
- MCP diff review tool: `projectbrain_review_git_diff`.
- Compact agent output for Context Pack and Impact Analysis.
- Synthetic public demo.
- CI on GitHub Actions.

## 7. v0.2 Requirements

### R1: Git Diff Impact

ProjectBrain must analyze changed files from Git without requiring manual `--changed-file` input.

Commands:

```bash
projectbrain impact-diff my_project --staged
projectbrain impact-diff my_project --from main --to HEAD
projectbrain impact-diff my_project --last-commit
```

MCP tool:

```text
projectbrain_review_git_diff
```

Current Phase 2 status: implemented for file-level changed path matching from local Git. Symbol-level hunk parsing remains planned.

### R2: Local MCP Privacy

MCP must remain stdio-only and local-only.

Requirements:

- No network listener.
- No remote API call.
- No source file body output by default.
- Tool results may include paths/symbols/risks and must document client-side privacy implications.

### R3: Agent-Friendly Output

Add compact output modes suitable for AI agents:

```text
summary
must_read_files
risk_warnings
recommended_tests
manual_review
structured_json
```

Current Phase 3 status: active implementation. CLI and MCP read tools should keep full JSON as the default and expose compact agent output on request.

### R4: Experience Claim Authoring

Add local CLI and MCP flow to add claims.

Commands:

```bash
projectbrain claim add my_project \
  --applies-to settlement,refund \
  --risk high \
  --statement "Settlement amount is stored in cents."
```

### R5: Synthetic Mini Repo

Provide a tiny source repository demo in addition to exported JSON.

## 8. Success Metrics

- New user can run demo in under 5 minutes.
- Agent can call MCP tools without any hosted ProjectBrain dependency.
- Current Git diff can be reviewed without manually listing files.
- No private pilot files are tracked in Git.
- CI validates CLI and MCP smoke tests.
- README first screen clearly explains why ProjectBrain is different from generic code graph explorers.

## 9. Release Plan

### v0.1.0

Initial open-source release:

- CLI
- local runtime
- synthetic demo
- MCP server
- CI

### v0.2.0

Agent workflow release:

- Git diff impact from local Git changed file names
- MCP diff review tool
- compact agent output
- improved quickstart
- privacy policy scaffold

### v0.3.0

Project memory release:

- experience claim authoring
- claim review state workflow
- stale claim detection
- synthetic mini source repo

### v0.4.0

Provider maturity release:

- direct CodeGraph setup guide
- optional parser fallback spike
- packaged releases
- PyPI publishing plan
