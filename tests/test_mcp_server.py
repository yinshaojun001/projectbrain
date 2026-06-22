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
from projectbrain_runtime.models import ProjectRecord  # noqa: E402


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
            self.assertIn("projectbrain_inspect_policy", tool_names)
            self.assertIn("projectbrain_add_experience_claim", tool_names)
            self.assertIn("projectbrain_list_experience_claims", tool_names)
            self.assertIn("projectbrain_review_experience_claim", tool_names)
            self.assertIn("projectbrain_archive_experience_claim", tool_names)
            self.assertIn("projectbrain_remember", tool_names)
            self.assertIn("projectbrain_propose_memories", tool_names)
            self.assertIn("projectbrain_search_brain", tool_names)
            self.assertIn("projectbrain_list_memory_candidates", tool_names)
            self.assertIn("projectbrain_review_memory_candidate", tool_names)
            self.assertIn("projectbrain_context_pack", tool_names)
            self.assertIn("projectbrain_impact_analysis", tool_names)
            self.assertIn("projectbrain_review_git_diff", tool_names)
            context_tool = next(tool for tool in tools["result"]["tools"] if tool["name"] == "projectbrain_context_pack")
            self.assertIn("output_format", context_tool["inputSchema"]["properties"])

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

            policy_result = _call_tool(
                server,
                "projectbrain_inspect_policy",
                {"project_id": "payment_mini_mcp_test"},
            )
            self.assertFalse(policy_result["policy_found"])

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

    def test_mcp_can_propose_search_and_confirm_brain_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "repo"
            project_path.mkdir()
            server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
            server.repository.save_project(ProjectRecord(
                project_id="payment",
                name="Payment",
                source_path=str(project_path),
                codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
            ))

            proposed = server.handle_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_propose_memories",
                    "arguments": {
                        "project_id": "payment",
                        "session_id": "session1",
                        "candidates": [
                            {"type": "constraint", "statement": "Refund fee must be booked separately.", "tags": ["refund"]}
                        ],
                    },
                },
            })
            proposed_data = json.loads(proposed["result"]["content"][0]["text"])
            candidate_id = proposed_data["candidates"][0]["candidate_id"]

            confirmed = server.handle_message({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_review_memory_candidate",
                    "arguments": {"project_id": "payment", "candidate_id": candidate_id, "action": "confirm"},
                },
            })
            confirmed_data = json.loads(confirmed["result"]["content"][0]["text"])
            self.assertEqual(confirmed_data["knowledge_unit"]["type"], "constraint")

            search = server.handle_message({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_search_brain",
                    "arguments": {"project_id": "payment", "query": "refund"},
                },
            })
            search_data = json.loads(search["result"]["content"][0]["text"])
            self.assertEqual(search_data["matches"][0]["type"], "constraint")

    def test_review_memory_candidate_requires_action_without_confirming_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _server_with_project(tmp)
            candidate_id = _propose_memory_candidate(server)

            missing_action = server.handle_message({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_review_memory_candidate",
                    "arguments": {"project_id": "payment", "candidate_id": candidate_id},
                },
            })

            self.assertTrue(missing_action["result"]["isError"])
            self.assertIn("Missing required argument: action", missing_action["result"]["content"][0]["text"])
            candidates = _call_tool(server, "projectbrain_list_memory_candidates", {"project_id": "payment"})
            self.assertEqual(candidates["candidates"][0]["review_state"], "human_review_required")
            search = _call_tool(server, "projectbrain_search_brain", {"project_id": "payment", "query": "refund"})
            self.assertEqual(search["matches"], [])

    def test_review_memory_candidate_rejects_invalid_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _server_with_project(tmp)
            candidate_id = _propose_memory_candidate(server)

            invalid_action = server.handle_message({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_review_memory_candidate",
                    "arguments": {"project_id": "payment", "candidate_id": candidate_id, "action": "approve"},
                },
            })

            self.assertTrue(invalid_action["result"]["isError"])
            self.assertIn("action must be confirm or reject", invalid_action["result"]["content"][0]["text"])

    def test_review_memory_candidate_reject_marks_candidate_without_creating_searchable_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _server_with_project(tmp)
            candidate_id = _propose_memory_candidate(server)

            rejected = _call_tool(
                server,
                "projectbrain_review_memory_candidate",
                {"project_id": "payment", "candidate_id": candidate_id, "action": "reject"},
            )

            self.assertEqual(rejected["candidate"]["review_state"], "rejected")
            search = _call_tool(server, "projectbrain_search_brain", {"project_id": "payment", "query": "refund"})
            self.assertEqual(search["matches"], [])

    def test_propose_memories_requires_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _server_with_project(tmp)

            missing_candidates = server.handle_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_propose_memories",
                    "arguments": {"project_id": "payment"},
                },
            })

            self.assertTrue(missing_candidates["result"]["isError"])
            self.assertIn("Missing required argument: candidates", missing_candidates["result"]["content"][0]["text"])

    def test_propose_memories_rejects_privacy_unsafe_candidate_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _server_with_project(tmp)

            unsafe = server.handle_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_propose_memories",
                    "arguments": {
                        "project_id": "payment",
                        "candidates": [
                            {
                                "type": "constraint",
                                "statement": "Refund fee must be booked separately.",
                                "transcript": "raw private session transcript",
                            }
                        ],
                    },
                },
            })

            self.assertTrue(unsafe["result"]["isError"])
            self.assertIn("Unsupported candidate field: transcript", unsafe["result"]["content"][0]["text"])

    def test_propose_memories_rejects_candidate_missing_required_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = _server_with_project(tmp)

            missing_type = server.handle_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "projectbrain_propose_memories",
                    "arguments": {
                        "project_id": "payment",
                        "candidates": [{"statement": "Refund fee must be booked separately."}],
                    },
                },
            })

            self.assertTrue(missing_type["result"]["isError"])
            self.assertIn("Missing required candidate field: type", missing_type["result"]["content"][0]["text"])

    def test_propose_memories_schema_restricts_candidate_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = ProjectBrainMcpServer(store_root=tmp)

            tools = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

            propose = next(
                tool for tool in tools["result"]["tools"] if tool["name"] == "projectbrain_propose_memories"
            )
            candidate_schema = propose["inputSchema"]["properties"]["candidates"]["items"]
            self.assertEqual(candidate_schema["required"], ["type", "statement"])
            self.assertFalse(candidate_schema["additionalProperties"])
            self.assertIn("evidence_summary", candidate_schema["properties"])
            self.assertNotIn("transcript", candidate_schema["properties"])


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


def _server_with_project(tmp: str) -> ProjectBrainMcpServer:
    project_path = Path(tmp) / "repo"
    project_path.mkdir()
    server = ProjectBrainMcpServer(store_root=str(Path(tmp) / "store"))
    server.repository.save_project(ProjectRecord(
        project_id="payment",
        name="Payment",
        source_path=str(project_path),
        codegraph_db_path=str(project_path / ".codegraph/codegraph.db"),
    ))
    return server


def _propose_memory_candidate(server: ProjectBrainMcpServer) -> str:
    proposed = _call_tool(
        server,
        "projectbrain_propose_memories",
        {
            "project_id": "payment",
            "session_id": "session1",
            "candidates": [
                {"type": "constraint", "statement": "Refund fee must be booked separately.", "tags": ["refund"]}
            ],
        },
    )
    return proposed["candidates"][0]["candidate_id"]


if __name__ == "__main__":
    unittest.main()
