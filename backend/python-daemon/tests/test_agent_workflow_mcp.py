import json
import os
import tempfile
import unittest
from pathlib import Path

from orchestrator.adapters import ToolAdapters
from orchestrator.agent_workflow.runner import WorkflowRunner


class NoModelClient:
    def __init__(self):
        self.calls = []

    def chat_json(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("model phases must not run in deterministic MCP mode")


class SmokeBridge:
    def __init__(self):
        self.calls = []

    def call_tool(self, tool_name, args):
        self.calls.append((tool_name, dict(args)))
        if tool_name == "mcp_investigation_start":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "started",
                "artifacts": {"session_path": "C:/tmp/session"},
                "recommended_next_tool": "mcp_investigation_filemap",
            }
        if tool_name == "mcp_investigation_filemap":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "mapped",
                "artifacts": {
                    "manifest_csv": "C:/tmp/session/manifest.csv",
                    "manifest_doctor_json": "C:/tmp/session/doctor.json",
                    "manifest_doctor_md": "C:/tmp/session/doctor.md",
                },
                "recommended_next_tool": "mcp_investigation_validate_manifest",
            }
        if tool_name == "mcp_investigation_validate_manifest":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "validated",
                "artifacts": {"manifest_health_json": "C:/tmp/session/health.json"},
                "recommended_next_tool": "mcp_investigation_read_report",
            }
        if tool_name == "mcp_investigation_read_report":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "read",
                "artifacts": {"manifest_health_json": "C:/tmp/session/health.json"},
                "content": "manifest_csv_content," * 1000,
                "recommended_next_tool": "mcp_investigation_compile_handoff",
            }
        if tool_name == "mcp_investigation_compile_handoff":
            return {
                "ok": True,
                "status": "COMPLETE",
                "summary": "handoff compiled",
                "artifacts": {
                    "final_markdown": "C:/tmp/session/final.md",
                    "final_python_bundle": "C:/tmp/session/bundle.py",
                    "archive_yaml": "C:/tmp/session/session.yaml",
                    "session_path": "C:/tmp/session",
                },
            }
        return {"ok": False, "status": "ERROR", "summary": tool_name, "artifacts": {}}


class AgentWorkflowMcpTests(unittest.TestCase):
    def setUp(self):
        self._previous_env = {
            key: os.environ.get(key)
            for key in ("ALETHEIA_AGENT_STATE_DIR", "ALETHEIA_ALLOWED_ROOTS")
        }

    def tearDown(self):
        for key, value in self._previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_mcp_agent_workflow_run_defaults_are_deterministic_and_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_repo = Path(tmp) / "repo"
            target_repo.mkdir()
            state_dir = Path(tmp) / "state"
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = str(state_dir)
            os.environ["ALETHEIA_ALLOWED_ROOTS"] = tmp
            lm = NoModelClient()
            bridge = SmokeBridge()
            adapters = ToolAdapters(
                workflow_runner_factory=lambda *, allow_ingest, bridge_client=None, use_model_phases=True: WorkflowRunner(
                    lm_client=lm,
                    bridge_client=bridge,
                    allow_ingest=allow_ingest,
                    use_model_phases=use_model_phases,
                )
            )

            result = adapters.call_mcp_tool(
                "mcp_agent_workflow_run",
                {"objective": "Smoke", "target_repo": str(target_repo)},
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "complete")
            self.assertEqual(lm.calls, [])
            self.assertEqual(
                [tool for tool, _ in bridge.calls],
                [
                    "mcp_investigation_start",
                    "mcp_investigation_filemap",
                    "mcp_investigation_validate_manifest",
                    "mcp_investigation_read_report",
                    "mcp_investigation_compile_handoff",
                ],
            )
            self.assertIn("run_id", result)
            self.assertIn("state_path", result)
            self.assertEqual(
                result["summary"],
                "Workflow complete. Final report, Python bundle, archive YAML, manifest, and session artifacts are available.",
            )
            self.assertNotIn(str(target_repo), result["summary"])
            self.assertNotIn("C:/", result["summary"])
            self.assertNotIn("[", result["summary"])
            self.assertNotIn("]", result["summary"])
            self.assertNotIn("session.yaml", result["summary"])
            for key in [
                "final_markdown",
                "final_python_bundle",
                "archive_yaml",
                "session_path",
                "manifest_csv",
                "manifest_health_json",
                "manifest_doctor_json",
                "manifest_doctor_md",
            ]:
                self.assertIn(key, result["artifacts"])
            encoded = json.dumps(result)
            self.assertNotIn("manifest_csv_content", encoded)
            self.assertNotIn("tool_results", encoded)

    def test_mcp_agent_workflow_run_accepts_explicit_model_phases_only(self):
        calls = []

        class ModelClient:
            def chat_json(self, *, phase=None, **kwargs):
                calls.append(phase)
                if phase == "PLAN":
                    return {"goal": "x", "stop_condition": "done", "notes": "", "todos": []}, False
                if phase == "SYNTHESIZE":
                    return {"summary": "summary"}, False
                return {"response": "final"}, False

        with tempfile.TemporaryDirectory() as tmp:
            target_repo = Path(tmp) / "repo"
            target_repo.mkdir()
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = str(Path(tmp) / "state")
            os.environ["ALETHEIA_ALLOWED_ROOTS"] = tmp
            adapters = ToolAdapters(
                workflow_runner_factory=lambda *, allow_ingest, bridge_client=None, use_model_phases=True: WorkflowRunner(
                    lm_client=ModelClient(),
                    bridge_client=SmokeBridge(),
                    allow_ingest=allow_ingest,
                    use_model_phases=use_model_phases,
                )
            )
            adapters.call_mcp_tool(
                "mcp_agent_workflow_run",
                {"objective": "Smoke", "target_repo": str(target_repo), "use_model_phases": True},
            )
        self.assertEqual(calls, ["PLAN", "SYNTHESIZE", "FINAL"])

    def test_mcp_agent_workflow_run_rejects_relative_target_repo_without_state_or_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            bridge = SmokeBridge()
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = str(state_dir)
            os.environ["ALETHEIA_ALLOWED_ROOTS"] = tmp
            result = ToolAdapters(
                workflow_runner_factory=lambda *, allow_ingest, bridge_client=None, use_model_phases=True: WorkflowRunner(
                    lm_client=NoModelClient(),
                    bridge_client=bridge,
                    allow_ingest=allow_ingest,
                    use_model_phases=use_model_phases,
                )
            ).call_mcp_tool("mcp_agent_workflow_run", {"objective": "Smoke", "target_repo": "backend-orchestrator-repo"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "POLICY_BLOCK")
        self.assertEqual(result["error"]["code"], "invalid_target_repo")
        self.assertEqual(bridge.calls, [])
        self.assertFalse(state_dir.exists())

    def test_mcp_agent_workflow_run_rejects_nonexistent_absolute_target_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            bridge = SmokeBridge()
            os.environ["ALETHEIA_ALLOWED_ROOTS"] = tmp
            result = ToolAdapters(
                workflow_runner_factory=lambda *, allow_ingest, bridge_client=None, use_model_phases=True: WorkflowRunner(
                    lm_client=NoModelClient(),
                    bridge_client=bridge,
                    allow_ingest=allow_ingest,
                    use_model_phases=use_model_phases,
                )
            ).call_mcp_tool("mcp_agent_workflow_run", {"objective": "Smoke", "target_repo": str(missing)})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_target_repo")
        self.assertEqual(bridge.calls, [])

    def test_mcp_agent_workflow_run_rejects_target_repo_outside_allowed_roots(self):
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
            target_repo = Path(outside) / "repo"
            target_repo.mkdir()
            bridge = SmokeBridge()
            os.environ["ALETHEIA_ALLOWED_ROOTS"] = allowed
            result = ToolAdapters(
                workflow_runner_factory=lambda *, allow_ingest, bridge_client=None, use_model_phases=True: WorkflowRunner(
                    lm_client=NoModelClient(),
                    bridge_client=bridge,
                    allow_ingest=allow_ingest,
                    use_model_phases=use_model_phases,
                )
            ).call_mcp_tool("mcp_agent_workflow_run", {"objective": "Smoke", "target_repo": str(target_repo)})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_target_repo")
        self.assertEqual(bridge.calls, [])

    def test_mcp_agent_workflow_run_rejects_unsupported_profile(self):
        result = ToolAdapters().call_mcp_tool(
            "mcp_agent_workflow_run",
            {"objective": "Smoke", "target_repo": "C:/repo", "profile": "unsafe"},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "POLICY_BLOCK")

    def test_mcp_agent_workflow_run_state_dir_unavailable_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_repo = Path(tmp) / "repo"
            target_repo.mkdir()
            state_file = Path(tmp) / "not-a-dir"
            state_file.write_text("x", encoding="utf-8")
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = str(state_file)
            os.environ["ALETHEIA_ALLOWED_ROOTS"] = tmp
            result = ToolAdapters(
                workflow_runner_factory=lambda *, allow_ingest, bridge_client=None, use_model_phases=True: WorkflowRunner(
                    lm_client=NoModelClient(),
                    bridge_client=SmokeBridge(),
                    allow_ingest=allow_ingest,
                    use_model_phases=use_model_phases,
                )
            ).call_mcp_tool("mcp_agent_workflow_run", {"objective": "Smoke", "target_repo": str(target_repo)})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["error"]["code"], "workflow_run_failed")


if __name__ == "__main__":
    unittest.main()
