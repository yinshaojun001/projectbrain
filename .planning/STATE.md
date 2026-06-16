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

v0.2 Release Readiness.

## Current Workspace Status

- Phase 2 Git Diff Impact is complete and pushed.
- Commit: `5b6cfef feat: add git diff impact analysis`.
- Phase 3 Agent-Friendly Output is complete and pushed.
- Commit: `4e18822 feat: add agent-friendly output format`.
- Phase 4 Experience Claim Authoring is complete and pushed.
- Commit: `1e17669 feat: add experience claim authoring`.
- Phase 4b Claim Lifecycle is complete and pushed.
- Commit: `782f995 feat: add experience claim lifecycle`.
- Phase 5 Privacy Policy controls are complete and pushed.
- Commit: `d8e4ca4 feat: add local privacy policy controls`.
- Phase 5b Privacy Policy Inspection is complete and pushed.
- Commit: `2633f3a feat: add privacy policy inspection`.
- Phase 6 Human Observability UI is complete (FastAPI + Jinja2 + HTMX, mounted at `/ui/*`, 127.0.0.1 only).
- Working tree should stay limited to v0.2 release readiness docs, tests, and public metadata.

## Next Engineering Task

Prepare v0.2 release readiness.

Recommended order:

1. Add v0.2 release readiness checklist.
2. Add Chinese quickstart documentation.
3. Link release readiness and Chinese docs from README and docs index.
4. Run tests and CLI/MCP smoke checks.
5. Run privacy scan to ensure private payment code/details are not tracked.
6. Commit and push the public-only changes.
7. Check GitHub Actions.

## Verification Commands

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
