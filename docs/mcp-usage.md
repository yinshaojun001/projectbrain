# Local MCP Usage

ProjectBrain's MCP server is designed to run like CodeGraph-style local tooling:

- it is started by your AI coding client as a local child process
- it communicates over stdio JSON-RPC
- it does not open network sockets
- it does not upload source code
- it reads only local ProjectBrain runtime files and local CodeGraph databases that you point it at

## Start Command

After installing ProjectBrain:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

The MCP server command is:

```bash
.venv/bin/projectbrain --store-root /absolute/path/to/.projectbrain mcp serve
```

Use an absolute `--store-root` in editor or agent configs so the MCP process always reads the intended local ProjectBrain store.

## Example MCP Client Config

```json
{
  "mcpServers": {
    "projectbrain": {
      "command": "/absolute/path/to/projectbrain/.venv/bin/projectbrain",
      "args": [
        "--store-root",
        "/absolute/path/to/projectbrain/.projectbrain",
        "mcp",
        "serve"
      ]
    }
  }
}
```

## Exposed Tools

| Tool | Purpose |
| --- | --- |
| `projectbrain_import_project` | Import CodeGraph facts from a local repository into local ProjectBrain storage. |
| `projectbrain_list_projects` | List projects already imported into the local store. |
| `projectbrain_inspect_policy` | Inspect the local output policy loaded for an imported project. |
| `projectbrain_add_experience_claim` | Add a local human experience claim to an imported project. |
| `projectbrain_list_experience_claims` | List local experience claims, hiding archived claims by default. |
| `projectbrain_review_experience_claim` | Update local claim review metadata. |
| `projectbrain_archive_experience_claim` | Archive a claim while preserving it in local storage. |
| `projectbrain_context_pack` | Build a task-scoped Context Pack for an imported project. |
| `projectbrain_impact_analysis` | Analyze likely impact for changed files or symbols. |
| `projectbrain_review_git_diff` | Analyze likely impact for local staged, branch/range, or last-commit Git changes. |
| `projectbrain_remember` | Write durable project knowledge into the local project Brain. |
| `projectbrain_propose_memories` | Submit memory candidates extracted from a Codex session for review. |
| `projectbrain_search_brain` | Search durable project Brain knowledge. |
| `projectbrain_list_memory_candidates` | List memory candidates awaiting review. |
| `projectbrain_review_memory_candidate` | Confirm or reject a memory candidate. |

The three read tools accept `output_format`:

| Value | Behavior |
| --- | --- |
| `json` | Default full ProjectBrain artifact JSON. |
| `agent` | Compact structured output for AI coding agents. |

`agent` output keeps the most actionable fields: summary, must-read files, matched entities, affected relations, risk warnings, recommended tests, manual-review guidance, and omissions.

### codex-brain Privacy Boundary

`codex-brain` captures only the Codex CLI process it explicitly starts. It does not monitor ordinary `codex` sessions, other shells, system clipboard contents, or background applications. Full transcripts are not part of the durable Brain by default; durable Brain records store concise summaries, candidates, and reviewed knowledge units.

## Experience Claim Tool

Use `projectbrain_add_experience_claim` to add local project memory that later Context Pack and Impact Analysis calls can match.

Example arguments:

```json
{
  "project_id": "private_project",
  "claim_id": "exp_checkout_validation",
  "statement": "Checkout validation changes require compatibility review.",
  "applies_to": ["checkout"],
  "risk_level": "high",
  "review_state": "approved",
  "claim_type": "HUMAN_CONFIRMED",
  "confidence": 0.8,
  "source": ["projectbrain://local-note/checkout-validation"]
}
```

The tool writes to local `.projectbrain/projects/<project_id>/experience_claims.json`. Keep statements concise and avoid secrets, credentials, customer data, private URLs, or source code bodies.

Review a claim:

```json
{
  "project_id": "private_project",
  "claim_id": "exp_checkout_validation",
  "review_state": "needs_review",
  "risk_level": "medium"
}
```

Archive a claim:

```json
{
  "project_id": "private_project",
  "claim_id": "exp_checkout_validation",
  "reason": "Superseded by newer checkout guidance."
}
```

Archived claims remain in `.projectbrain/projects/<project_id>/experience_claims.json` and can be listed with `include_archived: true`. Context Pack, Impact Analysis, and Git diff review ignore archived claims.

## Git Diff Review Tool

Use `projectbrain_review_git_diff` when an agent needs to review current changes before commit or PR.

Example arguments for staged changes:

```json
{
  "project_id": "private_project",
  "task": "Review the current staged change before commit",
  "staged": true,
  "output_format": "agent"
}
```

Example arguments for a branch or ref range:

```json
{
  "project_id": "private_project",
  "task": "Review branch impact",
  "from_ref": "main",
  "to_ref": "HEAD"
}
```

The tool reads changed file names from local Git and maps them to imported ProjectBrain facts. It does not read source file bodies, return source snippets, upload source code, or open network sockets.

## Privacy Boundary

The MCP server does not contain any network client code. It only reads and writes local files.

Keep these paths private and out of Git:

- source repositories you import
- `.codegraph/codegraph.db` generated from private repositories
- `.projectbrain/` runtime stores generated from private repositories
- private experience seed files

## Tool-Side Vs Client-Side Privacy

ProjectBrain controls the tool side:

- it does not upload source code
- it does not call hosted ProjectBrain services
- it does not open network sockets
- it does not read repositories unless you pass their local path
- it stores runtime data under the local `--store-root`

Your AI coding client controls the conversation side:

- MCP tool results are returned to the client
- tool results may include local paths, symbol names, call relationships, inferred business concepts, and risk notes
- the client may include those results in prompts sent to a model provider
- the client may log prompts, responses, and tool results depending on its settings

So the correct privacy model is:

```text
ProjectBrain MCP server: local-only
AI client + model provider: depends on your chosen client and model settings
```

## Recommended Use By Environment

| Environment | Recommendation |
| --- | --- |
| Private company code with strict policy | Use a local model or an approved enterprise AI endpoint. Disable prompt/tool-result retention if the client supports it. |
| Company code with approved cloud AI | Confirm that your AI client, model provider, and account settings allow source-derived paths/symbols to be sent. |
| Open-source code | Normal cloud AI clients are generally fine, but avoid committing `.projectbrain/` runtime stores. |
| Unknown or highly sensitive code | Do not use remote models. Run ProjectBrain MCP only with a local model/client stack. |

## Output Minimization

ProjectBrain's current MCP tools return structured analysis, not source file contents. This keeps output smaller and reduces accidental disclosure.

Imported projects can define a local `.projectbrain-policy.json`, `.projectbrain-policy.yml`, or `.projectbrain-policy.yaml` in the project root:

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

The policy applies to Context Pack, Impact Analysis, and Git diff review outputs returned through CLI, API, and MCP. Denied paths are removed from structured artifacts, output caps reduce list sizes, and source-like fields such as `body`, `snippet`, and `source_code` are stripped unless explicitly enabled.

Inspect the policy through MCP:

```json
{
  "project_id": "private_project"
}
```

Call this with `projectbrain_inspect_policy` to see whether a policy file was found, which path was loaded, deny path count, output cap presence, and whether source snippets are enabled.

Still, outputs can reveal architecture and business context. For sensitive projects:

- import the narrowest useful scope with `path_prefixes`
- use lower `node_limit` and `edge_limit` values when importing
- add deny paths for private modules, config directories, generated secrets, and local-only test fixtures
- keep private experience seed statements concise
- avoid putting secrets, credentials, private URLs, or customer data in experience seeds
- review generated Context Packs before sharing them outside your trusted environment

## Safe Local Workflow

For a private repository, a conservative workflow is:

```bash
projectbrain --store-root /private/local/.projectbrain import /private/repo \
  --id private_project \
  --path-prefix src/main/java/com/acme/checkout/ \
  --kind class \
  --kind interface \
  --kind method \
  --node-limit 100 \
  --edge-limit 150
```

Then configure the MCP client to use the same absolute store:

```json
{
  "mcpServers": {
    "projectbrain": {
      "command": "/absolute/path/to/projectbrain/.venv/bin/projectbrain",
      "args": [
        "--store-root",
        "/private/local/.projectbrain",
        "mcp",
        "serve"
      ]
    }
  }
}
```

## What Not To Do

- Do not publish private `.codegraph/codegraph.db` files.
- Do not publish private `.projectbrain/` stores.
- Do not point a remote or untrusted MCP host at private repositories.
- Do not add secrets or credentials to experience seed files.
- Do not assume "local MCP server" means your AI client is also local.
