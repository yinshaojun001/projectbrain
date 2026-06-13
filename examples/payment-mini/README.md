# Payment Mini Example

This directory contains synthetic ProjectBrain facts for a tiny payment-like Java service.

It is only a public demo fixture. It is not copied from a real production project.

Use it to try the CLI without a CodeGraph database:

```bash
python3 apps/tools/codegraph_adapter_cli.py \
  --project-path . \
  --project-id payment_mini \
  context-pack \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```
