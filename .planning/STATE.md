# ProjectBrain State

## Current State

- Repository is public on GitHub.
- Current branch is `main`.
- Real private payment code is ignored and not tracked.
- CI is passing.
- MCP server is local-only stdio.
- Product direction is local-first project memory and impact analysis MCP for AI coding agents.
- Do not pivot into a dashboard-first code graph product. ProjectBrain should stay focused on AI-agent workflow, privacy, Context Packs, and impact review.

## Current Priority

Phase 2: Git Diff Impact.

## Current Workspace Status

- PRD and GSD planning docs have been added under `docs/prd.md` and `.planning/`.
- Git diff impact implementation has been added locally but is not committed yet.
- Docs still need a final pass so README, quickstart, MCP usage, and local runtime all describe `impact-diff` and `projectbrain_review_git_diff`.

## Next Engineering Task

Finish Phase 2 by documenting, verifying, committing, and pushing Git Diff Impact.

Recommended order:

1. Review `docs/next-conversation.md`.
2. Update public docs for `impact-diff` and `projectbrain_review_git_diff`.
3. Run tests and CLI/MCP smoke checks.
4. Run privacy scan to ensure private payment code/details are not tracked.
5. Commit and push the public-only tool changes.
6. Check GitHub Actions.

## Verification Commands

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
