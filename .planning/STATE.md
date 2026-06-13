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

Phase 3: Agent-Friendly Output.

## Current Workspace Status

- Phase 2 Git Diff Impact is complete and pushed.
- Commit: `5b6cfef feat: add git diff impact analysis`.
- CI passed for the Phase 2 push.
- Working tree should stay limited to Phase 3 planning, implementation, tests, and public docs.

## Next Engineering Task

Implement Phase 3 Agent-Friendly Output.

Recommended order:

1. Add a compact agent output formatter for Context Pack and Impact Analysis artifacts.
2. Add CLI `--format json|agent` for `context`, `impact`, and `impact-diff`.
3. Add MCP `output_format` argument for `projectbrain_context_pack`, `projectbrain_impact_analysis`, and `projectbrain_review_git_diff`.
4. Update README, quickstart, MCP usage, local runtime, and PRD.
5. Run tests and CLI/MCP smoke checks.
6. Run privacy scan to ensure private payment code/details are not tracked.
7. Commit and push the public-only changes.
8. Check GitHub Actions.

## Verification Commands

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
