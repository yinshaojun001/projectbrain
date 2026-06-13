# ProjectBrain Roadmap

## Phase 1: Open Source Baseline

Status: done.

- Public GitHub repository.
- Private code excluded.
- README, license, synthetic demo.
- Installable CLI.
- CI.
- Local-only stdio MCP server.

## Phase 2: Git Diff Impact

Status: done.

Goal: let an AI agent review current changes without manually listing files.

Must be true:

- `projectbrain impact-diff <project_id> --staged` works.
- `projectbrain impact-diff <project_id> --from main --to HEAD` works.
- MCP tool `projectbrain_review_git_diff` works.
- Tests cover staged and explicit range parsing.
- Docs explain the local-only privacy boundary.

## Phase 3: Agent-Friendly Output

Status: active.

Goal: make MCP output easier for AI agents to consume.

Must be true:

- Context and impact tools support compact markdown.
- JSON remains available.
- Output size controls exist.

## Phase 4: Experience Claim Authoring

Status: planned.

Goal: make human project memory easy to add locally.

Must be true:

- CLI can add claims.
- MCP can add claims.
- Claims are matched in context/impact.
- Claims can be reviewed and marked stale later.

## Phase 5: Privacy Policy

Status: planned.

Goal: move from documented privacy guidance to enforceable local policy.

Must be true:

- `.projectbrain-policy` controls output.
- deny path rules exist.
- output size caps exist.
- source snippets remain disabled by default.
