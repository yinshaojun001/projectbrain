# Quickstart

This guide runs ProjectBrain from a clean checkout using only the synthetic public demo.

Chinese version: [中文快速上手](zh/quickstart.md).

## 1. Install Locally

Install with Homebrew:

```bash
brew tap yinshaojun001/projectbrain https://github.com/yinshaojun001/projectbrain
brew trust yinshaojun001/projectbrain
brew install projectbrain
projectbrain doctor
```

For local formula testing from this checkout:

```bash
brew tap yinshaojun001/projectbrain /path/to/projectbrain
brew trust yinshaojun001/projectbrain
brew install --build-from-source projectbrain
projectbrain doctor
```

Or install an editable development checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Check the CLI:

```bash
.venv/bin/projectbrain doctor
```

Expected shape:

```json
{
  "status": "ok",
  "python": "3.x.x",
  "store_root": ".projectbrain"
}
```

## 2. Generate Context From Public Demo

```bash
.venv/bin/projectbrain facts context \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```

The output is a Context Pack with:

- recommended files
- important symbols
- call relationships
- inferred business concepts
- human-review warnings

## 3. Generate Impact Analysis From Public Demo

```bash
.venv/bin/projectbrain facts impact \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Change the settlement contract" \
  --changed-file contract/src/main/java/example/payment/settlement/SettlementService.java
```

The output explains which entities and relations are adjacent to the changed file and whether manual review is recommended.

## 4. Use Your Own Project

For an AI coding agent, use one setup command:

```bash
projectbrain --store-root ~/.projectbrain-work setup /path/to/your/project \
  --id my_project
```

`setup` initializes and indexes CodeGraph, imports ProjectBrain facts, runs a Context Pack smoke test, detects local agents, and prompts you to install ProjectBrain MCP where supported, including Codex CLI, Claude Code, Cursor, and Trae. It also prints an MCP config for manual setup:

```bash
projectbrain --store-root /absolute/path/to/.projectbrain-work mcp serve
```

Then ask the agent to call `projectbrain_context_pack` before editing and `projectbrain_review_git_diff` after editing, both with `output_format: "agent"`.

For non-interactive setup, pass one or more agents:

```bash
projectbrain --store-root ~/.projectbrain-work setup /path/to/your/project \
  --id my_project \
  --agent codex
```

For manual or advanced setup, ProjectBrain expects a CodeGraph SQLite database at:

```text
<your-project>/.codegraph/codegraph.db
```

Import a bounded project scope:

```bash
.venv/bin/projectbrain import /path/to/your/project \
  --id my_project \
  --name "My Project" \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method
```

If installed with Homebrew, run `projectbrain` directly from any directory:

```bash
projectbrain --store-root ~/.projectbrain-work import /path/to/your/project \
  --id my_project \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method

projectbrain --store-root ~/.projectbrain-work context my_project "Explain the checkout flow" --format agent
```

Generate a Context Pack:

```bash
.venv/bin/projectbrain context my_project "Explain the checkout flow"
```

Generate Impact Analysis:

```bash
.venv/bin/projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java
```

Review the current staged Git diff:

```bash
.venv/bin/projectbrain impact-diff my_project "Review staged checkout changes" --staged
```

Review a branch or ref range:

```bash
.venv/bin/projectbrain impact-diff my_project "Review branch impact" --from main --to HEAD
```

`impact-diff` uses local Git to read changed file names, then maps those paths to imported ProjectBrain facts. It does not read or return source file bodies.

Use compact agent output when the result is meant to drive the next AI coding step:

```bash
.venv/bin/projectbrain context my_project "Explain the checkout flow" --format agent

.venv/bin/projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java \
  --format agent

.venv/bin/projectbrain impact-diff my_project "Review staged checkout changes" \
  --staged \
  --format agent
```

The default format remains full JSON. The `agent` format keeps the output structured, but reduces it to summary, must-read files, risk warnings, tests, and manual-review guidance.

Add a local experience claim:

```bash
.venv/bin/projectbrain claim add my_project \
  --id exp_checkout_validation \
  --applies-to checkout \
  --risk high \
  --review-state approved \
  --claim-type HUMAN_CONFIRMED \
  --statement "Checkout validation changes require compatibility review."
```

New claims are stored in `.projectbrain/projects/<project_id>/experience_claims.json` and are used by later Context Pack and Impact Analysis runs. Keep claim statements concise and do not include secrets, customer data, private URLs, or source code bodies.

List, review, and archive claims:

```bash
.venv/bin/projectbrain claim list my_project

.venv/bin/projectbrain claim review my_project exp_checkout_validation \
  --review-state needs_review \
  --risk medium

.venv/bin/projectbrain claim archive my_project exp_checkout_validation \
  --reason "Superseded by newer checkout guidance."

.venv/bin/projectbrain claim list my_project --include-archived
```

Archived claims remain in local storage for audit history, but Context Pack and Impact Analysis ignore them.

Runtime artifacts are stored under `.projectbrain/`, which is ignored by Git.

## Run Codex With ProjectBrain Memory

From a local project directory:

```bash
codex-brain
```

Review extracted memory candidates:

```bash
projectbrain brain candidates .
projectbrain brain confirm-candidate . <candidate_id>
```

## Privacy Boundary

Do not publish private source code, private `.codegraph/codegraph.db` files, private `.projectbrain/` stores, or private exported facts.

For private repositories, put a local `.projectbrain-policy.json` in the imported project root to minimize outputs:

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

Context Pack, Impact Analysis, and Git diff review apply this policy before saving or returning artifacts. Source snippets are disabled by default.

Inspect the loaded policy for an imported project:

```bash
.venv/bin/projectbrain policy inspect my_project
```

The checked-in `examples/payment-mini/` data is synthetic.

## Local MCP Server

ProjectBrain can also run as a local stdio MCP server:

```bash
.venv/bin/projectbrain --store-root /absolute/path/to/.projectbrain mcp serve
```

Use it from an MCP-capable AI coding client when you want the agent to request Context Packs and Impact Analysis without uploading project facts to a ProjectBrain server. See [Local MCP Usage](mcp-usage.md).

## v0.2 Readiness

Before publishing or recommending a v0.2 build, run the release checklist in [v0.2 Release Readiness](release-readiness.md).
