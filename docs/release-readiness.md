# v0.2 Release Readiness

This checklist is the release gate for the local ProjectBrain v0.2 workflow.

v0.2 is ready when a clean checkout can install the CLI, run the synthetic demo, expose the MCP server, enforce local privacy policy, and pass the public-data boundary scan.

## Scope

v0.2 includes:

- local JSON runtime
- CodeGraph SQLite import
- Context Pack generation
- Impact Analysis generation
- Git diff impact review
- compact agent output
- experience claim authoring
- claim list, review, and archive
- local `.projectbrain-policy` output controls
- policy inspection through CLI and MCP
- local-only stdio MCP server

v0.2 does not include:

- hosted ProjectBrain service
- source code upload
- dashboard-first graph UI
- automatic code modification
- stale claim detection
- symbol-level Git hunk parsing

## Required Local Checks

Run these from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests

.venv/bin/projectbrain doctor

printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```

Expected result:

- tests complete with `OK`
- `doctor` returns `status: ok`
- MCP `tools/list` includes:
  - `projectbrain_import_project`
  - `projectbrain_list_projects`
  - `projectbrain_inspect_policy`
  - `projectbrain_add_experience_claim`
  - `projectbrain_list_experience_claims`
  - `projectbrain_review_experience_claim`
  - `projectbrain_archive_experience_claim`
  - `projectbrain_context_pack`
  - `projectbrain_impact_analysis`
  - `projectbrain_review_git_diff`

## Public Demo Smoke

Generate a Context Pack:

```bash
.venv/bin/projectbrain facts context \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```

Generate an Impact Analysis:

```bash
.venv/bin/projectbrain facts impact \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Change the settlement contract" \
  --changed-file contract/src/main/java/example/payment/settlement/SettlementService.java
```

Expected result:

- output is valid JSON
- output references only synthetic `examples/payment-mini` facts
- no source file bodies are returned

## Runtime Smoke

Use a local project with CodeGraph facts:

```bash
.venv/bin/projectbrain import /path/to/project \
  --id my_project \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method

.venv/bin/projectbrain policy inspect my_project

.venv/bin/projectbrain context my_project "Explain the checkout flow" --format agent

.venv/bin/projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java \
  --format agent
```

If the local project is a Git repository, also run:

```bash
.venv/bin/projectbrain impact-diff my_project "Review staged checkout changes" --staged --format agent
```

Expected result:

- policy inspection reports whether a policy file was found
- agent output includes summary, must-read files, risks, tests, and manual-review guidance
- Git diff impact reads changed file names from local Git only

## Privacy Policy Smoke

Add this to the imported project root:

```json
{
  "deny_paths": ["private/**", "src/main/resources/config/**"],
  "output_limits": {
    "max_items_per_section": 8,
    "max_recommended_files": 8,
    "max_recommended_tests": 5
  },
  "include_source_snippets": false
}
```

Then run:

```bash
.venv/bin/projectbrain policy inspect my_project
.venv/bin/projectbrain context my_project "Explain the checkout flow"
.venv/bin/projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java
```

Expected result:

- `policy_found` is `true`
- `source_path` points to the local policy file
- denied paths are absent from generated artifacts
- output caps are applied
- source-like fields such as `body`, `snippet`, and `source_code` are stripped unless explicitly enabled

## Public Data Boundary

Before committing or publishing, confirm private/local paths are not staged:

```bash
git diff --cached --name-only -- \
  docs/payment \
  docs/projectbrain/pilots \
  examples/zhangfang \
  zhangfang \
  .projectbrain \
  .codegraph \
  docs/next-conversation.md
```

Expected result:

- no output

Run a targeted staged diff scan:

```bash
git diff --cached | rg -n "PRIVATE KEY|PASSWORD|SECRET_KEY|AKIA|sk-[A-Za-z0-9]|internal-only|customer-data|production-url"
```

Expected result:

- no output

## GitHub Actions

After pushing, check GitHub Actions for the pushed commit.

Required result:

- latest workflow run for `main` is green

If local GitHub CLI credentials are available:

```bash
gh run list --repo yinshaojun001/projectbrain --limit 5
```

## Release Decision

Do not tag or announce v0.2 if any required check fails.

When all required checks pass:

- update release notes
- tag the release
- verify the tag workflow if one exists
- keep private `.projectbrain`, `.codegraph`, pilot docs, and private source out of Git
