import os
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.adapters import ToolAdapters
from orchestrator.tool_assist_adapter import ToolAssistAdapter


class ToolAssistAdapterTests(unittest.TestCase):
    def test_tool_adapters_default_has_tool_assist_without_env(self):
        previous = os.environ.pop("TOOLSET_ROOT", None)
        try:
            adapters = ToolAdapters()
            self.assertIsNotNone(adapters.tool_assist)
        finally:
            if previous is not None:
                os.environ["TOOLSET_ROOT"] = previous

    def test_missing_toolset_root_fails_clearly(self):
        result = ToolAssistAdapter(toolset_root=None).investigation_start("obj", "repo")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "missing_toolset_root")

    def test_missing_backend_api_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "local_tool_assist_mcp").mkdir()
            (root / "local_tool_assist_mcp" / "__init__.py").write_text("", encoding="utf-8")
            sys.modules.pop("local_tool_assist_mcp.backend_api", None)
            sys.modules.pop("local_tool_assist_mcp", None)
            result = ToolAssistAdapter(toolset_root=str(root)).investigation_start("obj", "repo")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "missing_backend_api")

    def test_method_mapping_output_root_error_and_bounded_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "outputs"
            outputs.mkdir()
            session = outputs / "s1"
            session.mkdir()
            pkg = root / "local_tool_assist_mcp"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "backend_api.py").write_text(
                """
CALLS=[]
def create_session(objective, target_repo, profile='safe', output_root=None):
    CALLS.append(('create_session', output_root))
    return {'ok': True, 'status': 'PASS', 'summary': 'ok', 'artifacts': {'session_path': '/tmp/s'}, 'top_candidates': list(range(50)), 'recommended_next_tool': 'mcp_investigation_filemap'}
def scan_directory(session_path, profile='safe'):
    CALLS.append(('scan_directory', None))
    return {'ok': True, 'status': 'PASS', 'summary': 'x'*5000, 'artifacts': {'a': '/tmp/a', 'b': 1}, 'error': {'code': 'upstream_warn', 'message': 'warn-msg'}}
def validate_manifest(session_path):
    CALLS.append(('validate_manifest', None))
    return {'ok': False, 'status': 'WARN', 'summary': 'warn', 'error': 'string upstream err'}
def read_report(session_path, artifact_key, max_chars=12000):
    CALLS.append(('read_report', None))
    return {'ok': True, 'status': 'PASS', 'summary': 'read', 'content': 'Y'*200}
def compile_handoff_report(session_path):
    CALLS.append(('compile_handoff_report', None))
    return {'ok': True, 'status': 'COMPLETE', 'summary': 'done'}
""",
                encoding="utf-8",
            )
            sys.modules.pop("local_tool_assist_mcp.backend_api", None)
            sys.modules.pop("local_tool_assist_mcp", None)
            adapter = ToolAssistAdapter(toolset_root=str(root), lta_output_root=str(outputs))
            start = adapter.investigation_start("o", "r")
            filemap = adapter.investigation_filemap(str(session))
            validate = adapter.investigation_validate_manifest(str(session))
            read = adapter.investigation_read_report(str(session), "manifest_csv", 88)
            compile_result = adapter.investigation_compile_handoff(str(session))
            api = adapter._load_backend_api()

        self.assertEqual([name for name, _ in api.CALLS], [
            "create_session", "scan_directory", "validate_manifest", "read_report", "compile_handoff_report"
        ])
        self.assertEqual(api.CALLS[0][1], str(outputs))
        self.assertEqual(start["artifacts"], {"session_path": "/tmp/s"})
        self.assertEqual(len(start["top_candidates"]), 10)
        self.assertLessEqual(len(filemap["summary"]), 2000)
        self.assertEqual(filemap["artifacts"], {"a": "/tmp/a"})
        self.assertEqual(filemap["error"]["code"], "upstream_warn")
        self.assertEqual(validate["error"]["code"], "toolset_error")
        self.assertEqual(len(read["content"]), 88)
        self.assertEqual(compile_result["status"], "COMPLETE")

    def test_dispatch_missing_toolset_root_from_default_adapter(self):
        previous = os.environ.pop("TOOLSET_ROOT", None)
        try:
            result = ToolAdapters().call_mcp_tool("mcp_investigation_start", {"objective": "a", "target_repo": "b"})
        finally:
            if previous is not None:
                os.environ["TOOLSET_ROOT"] = previous
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "missing_toolset_root")

    def test_session_path_policy_block_and_allow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "outputs"
            outputs.mkdir()
            session = outputs / "inside"
            session.mkdir()
            outside = root / "outside"
            outside.mkdir()
            pkg = root / "local_tool_assist_mcp"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "backend_api.py").write_text(
                """
def scan_directory(session_path, profile='safe'):
    return {'ok': True, 'status': 'PASS', 'summary': session_path}
""",
                encoding="utf-8",
            )
            sys.modules.pop("local_tool_assist_mcp.backend_api", None)
            sys.modules.pop("local_tool_assist_mcp", None)
            adapter = ToolAssistAdapter(toolset_root=str(root), lta_output_root=str(outputs))

            blocked = adapter.investigation_filemap(str(outside))
            allowed = adapter.investigation_filemap(str(session))

        self.assertEqual(blocked["status"], "POLICY_BLOCK")
        self.assertEqual(blocked["error"]["code"], "session_path_outside_output_root")
        self.assertTrue(allowed["ok"])


if __name__ == "__main__":
    unittest.main()
