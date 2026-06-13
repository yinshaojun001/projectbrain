import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "adapters"))
sys.path.insert(0, str(ROOT / "packages" / "runtime"))
sys.path.insert(0, str(ROOT / "packages" / "schema"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures import create_payment_mini_codegraph_project  # noqa: E402
from projectbrain_cli.mcp_server import ProjectBrainMcpServer, serve_stdio  # noqa: E402


class ProjectBrainMcpServerTest(unittest.TestCase):
    def test_initialize_and_list_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = ProjectBrainMcpServer(store_root=tmp)

            initialize = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
            self.assertEqual(initialize["result"]["serverInfo"]["name"], "projectbrain")
            self.assertIn("tools", initialize["result"]["capabilities"])

            tools = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            tool_names = {tool["name"] for tool in tools["result"]["tools"]}
            self.assertIn("projectbrain_import_project", tool_names)
            self.assertIn("projectbrain_context_pack", tool_names)
            self.assertIn("projectbrain_impact_analysis", tool_names)
            self.assertIn("projectbrain_review_git_diff", tool_names)

    def test_tool_calls_use_local_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))

            import_result = _call_tool(
                server,
                "projectbrain_import_project",
                {
                    "project_id": "payment_mini_mcp_test",
                    "project_path": str(fixture["project_path"]),
                    "experience_seed": str(fixture["experience_seed"]),
                    "path_prefixes": [
                        "contract/src/main/java/example/payment/settlement/",
                        "service/src/main/java/example/payment/settlement/",
                    ],
                    "kinds": ["class", "interface", "method"],
                },
            )
            self.assertEqual(import_result["project"]["project_id"], "payment_mini_mcp_test")

            context_result = _call_tool(
                server,
                "projectbrain_context_pack",
                {"project_id": "payment_mini_mcp_test", "task": "Explain settlement"},
            )
            self.assertIn("context_pack", context_result)

            impact_result = _call_tool(
                server,
                "projectbrain_impact_analysis",
                {
                    "project_id": "payment_mini_mcp_test",
                    "task": "Change settlement contract",
                    "changed_files": [
                        "contract/src/main/java/example/payment/settlement/SettlementService.java"
                    ],
                },
            )
            self.assertEqual(
                impact_result["impact_analysis"]["review_recommendation"]["action"],
                "manual_review_required",
            )

    def test_stdio_server_uses_newline_delimited_json_rpc(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            stdin = StringIO(json.dumps(request) + "\n")
            stdout = StringIO()

            result = serve_stdio(store_root=str(Path(tmp) / "store"), stdin=stdin, stdout=stdout, stderr=StringIO())

            self.assertEqual(result, 0)
            response = json.loads(stdout.getvalue())
            self.assertEqual(response["id"], 1)
            self.assertIn("tools", response["result"])


def _call_tool(server: ProjectBrainMcpServer, name: str, arguments: dict) -> dict:
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    if response["result"].get("isError"):
        raise AssertionError(response["result"]["content"][0]["text"])
    return json.loads(response["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
