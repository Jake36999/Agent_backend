import unittest

from orchestrator.adapters import ToolAdapters
from orchestrator.bridge_server import handle_json_rpc


class FakeAdapters(ToolAdapters):
    def call_mcp_tool(self, tool_name, args):
        return {"ok": True, "tool_name": tool_name, "args": args}


class BridgeServerTests(unittest.TestCase):
    def test_tools_call_reaches_python_tool_adapters(self):
        response = handle_json_rpc(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools.call",
                "params": {"toolName": "mcp_scout_workspace", "args": {"project_id": "p"}},
            },
            FakeAdapters(),
        )

        self.assertEqual(response["result"]["tool_name"], "mcp_scout_workspace")
        self.assertEqual(response["result"]["args"], {"project_id": "p"})


if __name__ == "__main__":
    unittest.main()
