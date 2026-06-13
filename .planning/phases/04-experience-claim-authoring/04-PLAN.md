# Phase 4 Plan: Experience Claim Authoring

## Goal

ProjectBrain can add human project experience claims directly to the local runtime store, so agents can use new constraints in Context Packs and Impact Analysis without editing seed files by hand.

## Must Be True

- CLI command `projectbrain claim add <project_id>` adds a claim to local runtime storage.
- MCP tool `projectbrain_add_experience_claim` adds a claim to local runtime storage.
- Added claims are stored in `.projectbrain/projects/<project_id>/experience_claims.json`.
- Added claims are immediately matched by Context Pack and Impact Analysis.
- Claim fields are validated for risk level, review state, claim type, confidence, and non-empty statement.
- Existing JSON runtime remains local-only.
- No source file bodies are read or returned.
- Tests cover CLI add, MCP add, validation, and matching behavior.

## Claim Shape

```text
id
claim_type
review_state
risk_level
applies_to
statement
confidence
sources
```

## Implementation Steps

1. Add runtime method to validate, normalize, and append a claim.
2. Add CLI `claim add` subcommand.
3. Add MCP tool `projectbrain_add_experience_claim`.
4. Add tests for CLI, MCP, and matching.
5. Update public docs with claim authoring examples and privacy notes.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```
