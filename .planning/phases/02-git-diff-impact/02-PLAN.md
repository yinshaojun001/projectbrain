# Phase 2 Plan: Git Diff Impact

## Goal

ProjectBrain can analyze the impact of current Git changes without requiring the user or AI agent to manually list changed files.

## Must Be True

- CLI command `projectbrain impact-diff <project_id> --staged` returns Impact Analysis.
- CLI command `projectbrain impact-diff <project_id> --from <ref> --to <ref>` returns Impact Analysis.
- CLI command `projectbrain impact-diff <project_id> --last-commit` returns Impact Analysis.
- MCP tool `projectbrain_review_git_diff` exposes the same behavior.
- The implementation uses local `git` only.
- No source file bodies are read or returned.
- Tests cover staged and explicit-range diff detection.

## Implementation Steps

1. Add a small Git diff helper in runtime.
2. Add runtime method to turn diff file lists into existing Impact Analysis.
3. Add CLI `impact-diff`.
4. Add MCP tool `projectbrain_review_git_diff`.
5. Add tests using a temporary Git repo and synthetic ProjectBrain facts.
6. Update README, quickstart, MCP docs.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain impact-diff <project_id> --staged
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
