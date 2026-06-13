# Phase 3 Plan: Agent-Friendly Output

## Goal

ProjectBrain can return compact, action-oriented output that AI coding agents can read before editing or reviewing code without parsing the full artifact JSON.

## Must Be True

- CLI `context`, `impact`, and `impact-diff` support `--format json`.
- CLI `context`, `impact`, and `impact-diff` support `--format agent`.
- Existing JSON output remains the default.
- MCP tools `projectbrain_context_pack`, `projectbrain_impact_analysis`, and `projectbrain_review_git_diff` accept `output_format`.
- MCP `output_format=agent` returns compact fields for agent execution.
- Agent output includes summary, must-read files, risk warnings, recommended tests, and manual-review guidance.
- Agent output does not include source file bodies.
- Tests cover CLI and MCP agent output.

## Output Shape

Context Pack agent output:

```text
artifact_type
project_id
task
summary
must_read_files
important_symbols
risk_warnings
recommended_tests
manual_review
omissions
```

Impact Analysis agent output:

```text
artifact_type
project_id
task
summary
changed_files
matched_entities
affected_relations
risk_warnings
recommended_tests
manual_review
review_recommendation
omissions
```

## Implementation Steps

1. Add a runtime formatter module that converts existing artifacts to compact agent output.
2. Add CLI `--format json|agent` to `context`, `impact`, and `impact-diff`.
3. Add MCP `output_format` argument to the three agent-facing read tools.
4. Add focused tests for CLI and MCP output formatting.
5. Update public docs with the new output mode.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
