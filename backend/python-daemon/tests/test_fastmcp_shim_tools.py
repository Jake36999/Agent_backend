from pathlib import Path
import unittest


class FastMcpShimTests(unittest.TestCase):
    def test_investigation_tools_are_declared(self):
        shim_path = Path(__file__).resolve().parents[2] / "lmstudio_fastmcp_shim.py"
        source = shim_path.read_text(encoding="utf-8")
        for signature in [
            "def mcp_investigation_start(",
            "def mcp_investigation_filemap(",
            "def mcp_investigation_validate_manifest(",
            "def mcp_investigation_read_report(",
            "def mcp_investigation_compile_handoff(",
            "def mcp_agent_workflow_run(",
            "def mcp_set_active_partition(",
            "def mcp_set_active_project_manual(",
        ]:
            self.assertIn(signature, source)

        self.assertIn(
            'Recommended LM Studio exposure is allowed_tools = ["mcp_agent_workflow_run"].',
            source,
        )


if __name__ == "__main__":
    unittest.main()
