import json
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.agent_workflow.bridge_client import TcpBridgeClient
from orchestrator.agent_workflow.compaction import compact_tool_result
from orchestrator.agent_workflow.lmstudio_client import LMStudioClient, ModelOutputInvalid
from orchestrator.agent_workflow.policies import validate_tool
from orchestrator.agent_workflow.runner import WorkflowRunner


class FakeLM:
    def __init__(self, plan=None, synth=None, final=None, invalid_plan=False, fallback_phases=None):
        self.calls = []
        self.invalid_plan = invalid_plan
        self.fallback_phases = set(fallback_phases or [])
        self.plan = plan or {
            "goal": "Run smoke workflow",
            "stop_condition": "handoff compiled",
            "notes": "compact",
            "todos": [],
        }
        self.synth = synth or {"summary": "Internal compact summary"}
        self.final = final or {"response": "Workflow finished without raw backend JSON."}

    def chat_json(self, *, messages, schema, reasoning, max_tokens=300, phase=None):
        self.calls.append({"phase": phase, "reasoning": reasoning, "max_tokens": max_tokens})
        if phase == "PLAN":
            if self.invalid_plan:
                raise ModelOutputInvalid("bad plan")
            return self.plan, phase in self.fallback_phases
        if phase == "SYNTHESIZE":
            return self.synth, phase in self.fallback_phases
        if phase == "FINAL":
            return self.final, phase in self.fallback_phases
        raise AssertionError(f"unexpected model phase: {phase}")


class FakeBridge:
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
                "artifacts": {"manifest_csv": "C:/tmp/session/manifest.csv"},
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
                "summary": "read report",
                "artifacts": {"manifest_health_json": "C:/tmp/session/health.json"},
                "content": "col1,col2\n" + ("raw," * 2000),
                "recommended_next_tool": "mcp_investigation_compile_handoff",
            }
        if tool_name == "mcp_investigation_compile_handoff":
            return {
                "ok": True,
                "status": "COMPLETE",
                "summary": "handoff",
                "artifacts": {"handoff_markdown": "C:/tmp/session/final.md"},
            }
        return {"ok": False, "status": "ERROR", "summary": f"unexpected {tool_name}", "artifacts": {}}


class AgentWorkflowTests(unittest.TestCase):
    def test_policy_rejects_raw_shell_and_blocks_ingest_by_default(self):
        self.assertFalse(validate_tool("bash", {}, allow_ingest=True)[0])
        self.assertFalse(validate_tool("mcp_unknown", {}, allow_ingest=True)[0])
        self.assertFalse(validate_tool("mcp_ingest_target", {"project_id": "p", "absolute_path": "x"})[0])
        self.assertTrue(
            validate_tool(
                "mcp_ingest_target",
                {"project_id": "p", "absolute_path": "x"},
                allow_ingest=True,
            )[0]
        )

    def test_policy_enforces_required_investigation_start_args(self):
        ok, reason = validate_tool("mcp_investigation_start", {"objective": "x"})
        self.assertFalse(ok)
        self.assertIn("target_repo", reason)

    def test_compaction_omits_large_content_by_default_and_caps_when_requested(self):
        raw = {
            "ok": True,
            "status": "PASS",
            "summary": "s" * 1500,
            "artifacts": {"report": "C:/tmp/report.md"},
            "content": "X" * 5000,
            "top_candidates": list(range(20)),
            "recommended_next_tool": "mcp_investigation_compile_handoff",
        }
        compact = compact_tool_result("mcp_investigation_read_report", raw, max_chars=100)
        self.assertNotIn("content_preview", compact)
        self.assertTrue(compact["content_omitted"])
        self.assertEqual(compact["artifacts"], {"report": "C:/tmp/report.md"})
        self.assertEqual(len(compact["top_candidates"]), 10)

        with_content = compact_tool_result(
            "mcp_investigation_read_report",
            raw,
            max_chars=100,
            include_content=True,
        )
        self.assertEqual(len(with_content["content_preview"]), 100)
        self.assertTrue(with_content["content_omitted"])

    def test_workflow_uses_only_plan_synthesize_final_model_phases_and_smokes_five_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = tmp
            os.environ["ALETHEIA_AGENT_REASONING_PLAN"] = "medium"
            os.environ["ALETHEIA_AGENT_REASONING_SYNTHESIZE"] = "low"
            os.environ["ALETHEIA_AGENT_REASONING_FINAL"] = "off"
            lm = FakeLM(invalid_plan=True)
            bridge = FakeBridge()
            state, response = WorkflowRunner(lm_client=lm, bridge_client=bridge).run(
                "Objective: Smoke test\nTarget repo: C:/repo\nProfile: safe",
                objective="Smoke test",
                target_repo="C:/repo",
                profile="safe",
            )

            self.assertEqual([call["phase"] for call in lm.calls], ["PLAN", "SYNTHESIZE", "FINAL"])
            self.assertEqual([call["reasoning"] for call in lm.calls], ["medium", "low", "off"])
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
            self.assertEqual(response, "Workflow finished without raw backend JSON.")
            self.assertTrue(Path(state.path).exists())
            self.assertEqual({todo["status"] for todo in state.todos}, {"done"})
            self.assertEqual(state.errors[0]["code"], "MODEL_OUTPUT_INVALID")

            saved = json.loads(Path(state.path).read_text(encoding="utf-8"))
            self.assertNotIn("raw,raw,raw", json.dumps(saved))
            read_result = [r for r in saved["tool_results"] if r["tool_name"] == "mcp_investigation_read_report"][0]
            self.assertNotIn("content_preview", read_result)
            self.assertTrue(read_result["content_omitted"])

    def test_invalid_planner_without_target_repo_returns_model_output_invalid_and_needs_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = tmp
            state, response = WorkflowRunner(lm_client=FakeLM(invalid_plan=True), bridge_client=FakeBridge()).run(
                "Investigate something vague"
            )
            self.assertEqual(response, "Unable to create a valid workflow plan.")
            codes = [err["code"] for err in state.errors]
            self.assertIn("MODEL_OUTPUT_INVALID", codes)
            self.assertIn("NEEDS_INPUT", codes)
            self.assertEqual(len(FakeBridge().calls), 0)

    def test_blocked_tool_sets_blocked_todo_and_no_extra_model_check(self):
        class BlockingBridge(FakeBridge):
            def call_tool(self, tool_name, args):
                self.calls.append((tool_name, dict(args)))
                return {"ok": False, "status": "ERROR", "summary": "blocked", "artifacts": {}}

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ALETHEIA_AGENT_STATE_DIR"] = tmp
            lm = FakeLM()
            bridge = BlockingBridge()
            state, _ = WorkflowRunner(lm_client=lm, bridge_client=bridge).run(
                "Objective: x\nTarget repo: C:/repo",
                objective="x",
                target_repo="C:/repo",
            )
            self.assertEqual([call["phase"] for call in lm.calls], ["PLAN", "SYNTHESIZE", "FINAL"])
            self.assertEqual(state.todos[0]["status"], "blocked")
            self.assertEqual(len(bridge.calls), 1)

    def test_lmstudio_payloads_are_separated_by_api_mode(self):
        posted = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.status = 200

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(request, timeout):
            body = json.loads(request.data.decode("utf-8"))
            posted.append((request.full_url, body))
            if "/api/v1/chat" in request.full_url:
                return FakeResponse({"message": {"content": "{\"ok\": true}"}})
            return FakeResponse({"choices": [{"message": {"content": "{\"ok\": true}"}}]})

        with mock.patch.dict(
            os.environ,
            {
                "ALETHEIA_AGENT_MODEL": "test-model",
                "ALETHEIA_AGENT_API_MODE": "native",
                "ALETHEIA_AGENT_CHAT_URL": "http://127.0.0.1:1234/api/v1/chat",
            },
            clear=False,
        ):
            with mock.patch("urllib.request.urlopen", fake_urlopen):
                result, fallback = LMStudioClient().chat_json(
                    messages=[{"role": "user", "content": "x"}],
                    schema={"name": "s"},
                    reasoning="low",
                    phase="PLAN",
                )
        self.assertEqual(result, {"ok": True})
        self.assertFalse(fallback)
        self.assertIn("reasoning", posted[-1][1])
        self.assertNotIn("response_format", posted[-1][1])

        with mock.patch.dict(
            os.environ,
            {
                "ALETHEIA_AGENT_MODEL": "test-model",
                "ALETHEIA_AGENT_API_MODE": "compatible",
                "ALETHEIA_AGENT_CHAT_URL": "http://127.0.0.1:1234/v1/chat/completions",
            },
            clear=False,
        ):
            with mock.patch("urllib.request.urlopen", fake_urlopen):
                LMStudioClient().chat_json(
                    messages=[{"role": "user", "content": "x"}],
                    schema={"name": "s"},
                    reasoning="low",
                    phase="PLAN",
                )
        self.assertIn("response_format", posted[-1][1])
        self.assertNotIn("reasoning", posted[-1][1])

    def test_lmstudio_retries_without_reasoning_when_native_endpoint_rejects_it(self):
        attempts = []

        class FakeResponse:
            status = 200

            def read(self):
                return b'{"message":{"content":"{\\"ok\\": true}"}}'

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(request, timeout):
            body = json.loads(request.data.decode("utf-8"))
            attempts.append(body)
            if len(attempts) == 1:
                raise Exception("reasoning unsupported")
            return FakeResponse()

        with mock.patch.dict(
            os.environ,
            {
                "ALETHEIA_AGENT_MODEL": "test-model",
                "ALETHEIA_AGENT_API_MODE": "native",
                "ALETHEIA_AGENT_CHAT_URL": "http://127.0.0.1:1234/api/v1/chat",
            },
            clear=False,
        ):
            with mock.patch("urllib.request.urlopen", fake_urlopen):
                result, fallback = LMStudioClient().chat_json(
                    messages=[{"role": "user", "content": "x"}],
                    schema={"name": "s"},
                    reasoning="low",
                    phase="PLAN",
                )
        self.assertEqual(result, {"ok": True})
        self.assertTrue(fallback)
        self.assertIn("reasoning", attempts[0])
        self.assertNotIn("reasoning", attempts[1])

    def test_tcp_bridge_reads_split_responses(self):
        payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True, "summary": "split"}}

        def handler(conn):
            conn.recv(4096)
            encoded = (json.dumps(payload) + "\n").encode("utf-8")
            conn.sendall(encoded[:10])
            conn.sendall(encoded[10:])
            conn.close()

        port = self._serve_once(handler)
        result = TcpBridgeClient(host="127.0.0.1", port=port, timeout=2).call_tool("mcp_scout_workspace", {})
        self.assertEqual(result["summary"], "split")

    def test_tcp_bridge_handles_malformed_and_oversized_compactly(self):
        def malformed(conn):
            conn.recv(4096)
            conn.sendall(b"{not json}\n")
            conn.close()

        malformed_port = self._serve_once(malformed)
        malformed_result = TcpBridgeClient(host="127.0.0.1", port=malformed_port, timeout=2).call_tool("x", {})
        self.assertFalse(malformed_result["ok"])
        self.assertEqual(malformed_result["status"], "ERROR")

        def oversized(conn):
            conn.recv(4096)
            conn.sendall(b'{"jsonrpc":"2.0","id":1,"result":{"summary":"' + (b"X" * 200) + b'"}}\n')
            conn.close()

        oversized_port = self._serve_once(oversized)
        oversized_result = TcpBridgeClient(
            host="127.0.0.1",
            port=oversized_port,
            timeout=2,
            max_response_bytes=20,
        ).call_tool("x", {})
        self.assertFalse(oversized_result["ok"])
        self.assertIn("bridge_call_failed", oversized_result["summary"])

    def _serve_once(self, handler):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def run():
            try:
                conn, _ = server.accept()
                handler(conn)
            finally:
                server.close()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return port


if __name__ == "__main__":
    unittest.main()
