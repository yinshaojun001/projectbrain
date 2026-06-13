# Quickstart

This guide runs ProjectBrain from a clean checkout using only the synthetic public demo.

## 1. Install Locally

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

ProjectBrain currently expects a CodeGraph SQLite database at:

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

Runtime artifacts are stored under `.projectbrain/`, which is ignored by Git.

## Privacy Boundary

Do not publish private source code, private `.codegraph/codegraph.db` files, private `.projectbrain/` stores, or private exported facts.

The checked-in `examples/payment-mini/` data is synthetic.

## Local MCP Server

ProjectBrain can also run as a local stdio MCP server:

```bash
.venv/bin/projectbrain --store-root /absolute/path/to/.projectbrain mcp serve
```

Use it from an MCP-capable AI coding client when you want the agent to request Context Packs and Impact Analysis without uploading project facts to a ProjectBrain server. See [Local MCP Usage](mcp-usage.md).
