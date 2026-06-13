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

## Privacy Boundary

The MCP server does not contain any network client code. It only reads and writes local files.

Keep these paths private and out of Git:

- source repositories you import
- `.codegraph/codegraph.db` generated from private repositories
- `.projectbrain/` runtime stores generated from private repositories
- private experience seed files

The tool output may contain local file paths, symbol names, and inferred risk notes. That output stays in the local MCP conversation unless your AI client sends conversation contents to its model provider. Choose your AI client and model settings accordingly.
