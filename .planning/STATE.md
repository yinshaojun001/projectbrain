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

Phase 4: Experience Claim Authoring.

## Current Workspace Status

- Phase 2 Git Diff Impact is complete and pushed.
- Commit: `5b6cfef feat: add git diff impact analysis`.
- Phase 3 Agent-Friendly Output is complete and pushed.
- Commit: `4e18822 feat: add agent-friendly output format`.
- CI passed for the Phase 3 push.
- Working tree should stay limited to Phase 4 planning, implementation, tests, and public docs.

## Next Engineering Task

Implement Phase 4 Experience Claim Authoring.

Recommended order:

1. Add runtime support for appending validated experience claims.
2. Add CLI `projectbrain claim add`.
3. Add MCP tool `projectbrain_add_experience_claim`.
4. Ensure new claims are immediately used by Context Pack and Impact Analysis.
5. Update README, quickstart, MCP usage, local runtime, and PRD.
6. Run tests and CLI/MCP smoke checks.
7. Run privacy scan to ensure private payment code/details are not tracked.
8. Commit and push the public-only changes.
9. Check GitHub Actions.

## Verification Commands

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
