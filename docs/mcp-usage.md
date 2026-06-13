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
| `projectbrain_context_pack` | Build a task-scoped Context Pack for an imported project. |
| `projectbrain_impact_analysis` | Analyze likely impact for changed files or symbols. |
| `projectbrain_review_git_diff` | Analyze likely impact for local staged, branch/range, or last-commit Git changes. |

## Git Diff Review Tool

Use `projectbrain_review_git_diff` when an agent needs to review current changes before commit or PR.

Example arguments for staged changes:

```json
{
  "project_id": "private_project",
  "task": "Review the current staged change before commit",
  "staged": true
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

Still, outputs can reveal architecture and business context. For sensitive projects:

- import the narrowest useful scope with `path_prefixes`
- use lower `node_limit` and `edge_limit` values when importing
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
