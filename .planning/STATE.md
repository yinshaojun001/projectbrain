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

Phase 5: Privacy Policy.

## Current Workspace Status

- Phase 2 Git Diff Impact is complete and pushed.
- Commit: `5b6cfef feat: add git diff impact analysis`.
- Phase 3 Agent-Friendly Output is complete and pushed.
- Commit: `4e18822 feat: add agent-friendly output format`.
- Phase 4 Experience Claim Authoring is complete and pushed.
- Commit: `1e17669 feat: add experience claim authoring`.
- Phase 4b Claim Lifecycle is complete and pushed.
- Commit: `782f995 feat: add experience claim lifecycle`.
- Working tree should stay limited to Phase 5 planning, implementation, tests, and public docs.

## Next Engineering Task

Implement Phase 5 Privacy Policy.

Recommended order:

1. Add project-local `.projectbrain-policy` loading.
2. Add deny path filtering for read artifacts.
3. Add output size caps for read artifacts.
4. Keep source snippets disabled by default.
5. Apply policy to CLI, API, and MCP context/impact/git-diff output.
6. Update README, quickstart, MCP usage, local runtime, PRD, and roadmap.
7. Run tests and CLI/MCP smoke checks.
8. Run privacy scan to ensure private payment code/details are not tracked.
9. Commit and push the public-only changes.
10. Check GitHub Actions.

## Verification Commands

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
