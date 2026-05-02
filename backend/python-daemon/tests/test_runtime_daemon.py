import json
import sqlite3
import tempfile
import unittest
from collections import deque
from contextlib import closing
from pathlib import Path

from orchestrator.adapters import ToolAdapters
from orchestrator.bridge_server import BridgeSecurity, build_auth_envelope, handle_json_rpc, line_too_large
from orchestrator.config import RuntimeConfig
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.queue_repo import QueueRepository
from orchestrator.runtime import build_runtime
from orchestrator.worker import DaemonWorker


class FakeToolAdapters(ToolAdapters):
    def __init__(self):
        super().__init__()
        self.calls = []

    def call_mcp_tool(self, tool_name, args):
        self.calls.append((tool_name, args))
        return {"ok": True, "tool_name": tool_name, "args": args}


class RuntimeDaemonTests(unittest.TestCase):
    def test_runtime_config_loads_paths_and_bridge_from_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = RuntimeConfig.from_env(
                {
                    "ALETHEIA_PROJECT_ROOT": str(root),
                    "ALETHEIA_STATE_DIR": str(root / "state"),
                    "ALETHEIA_ALLOWED_ROOTS": f"{root};{root / 'other'}",
                    "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                    "ALETHEIA_LM_STUDIO_BASE_URL": "http://lm/v1",
                    "ALETHEIA_EMBEDDING_MODEL": "model",
                    "ALETHEIA_BRIDGE_HOST": "127.0.0.1",
                    "ALETHEIA_BRIDGE_PORT": "4567",
                    "ALETHEIA_APPROVAL_SECRET": "secret",
                }
            )

            self.assertEqual(config.project_root, root.resolve())
            self.assertEqual(config.project_id, root.name)
            self.assertEqual(config.enable_admin_bridge, False)
            self.assertEqual(config.bridge_host, "127.0.0.1")
            self.assertEqual(config.bridge_port, 4567)

    def test_runtime_config_project_id_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = RuntimeConfig.from_env(
                {
                    "ALETHEIA_PROJECT_ROOT": str(root),
                    "ALETHEIA_PROJECT_ID": "custom-id",
                    "ALETHEIA_ENABLE_ADMIN_BRIDGE": "true",
                }
            )
            self.assertEqual(config.project_id, "custom-id")
            self.assertEqual(config.enable_admin_bridge, True)

    def test_build_runtime_bootstraps_components_and_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = RuntimeConfig.from_env(
                {
                    "ALETHEIA_PROJECT_ROOT": str(root),
                    "ALETHEIA_STATE_DIR": str(root / "state"),
                    "ALETHEIA_ALLOWED_ROOTS": str(root),
                    "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                }
            )

            runtime = build_runtime(config)

            try:
                self.assertTrue((root / "state" / "queue.db").exists())
                self.assertIsNotNone(runtime.tool_adapters.semantic_memory)
                self.assertIsNotNone(runtime.tool_adapters.workspace_scout)
                self.assertIs(runtime.execution_loop.repo, runtime.repo)
            finally:
                runtime.close()

    def test_worker_executes_payload_tool_and_completes_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = QueueRepository(root / "queue.db", root / "control.db")
            adapters = FakeToolAdapters()
            payload = {"tool": "mcp_scout_workspace", "args": {"project_id": "p", "absolute_path": str(root)}}
            repo.create_task("task", "p", "Task", payload, depth=0)
            worker = DaemonWorker(repo, adapters, project_id="p", worker_id="w")

            result = worker.run_once()

            self.assertEqual(result["task_id"], "task")
            self.assertEqual(repo.get_task("task")["state"], "COMPLETED")
            self.assertEqual(adapters.calls, [("mcp_scout_workspace", payload["args"])])

    def test_worker_registers_and_heartbeats_process_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = QueueRepository(root / "queue.db", root / "control.db")
            worker = DaemonWorker(repo, FakeToolAdapters(), project_id="p", worker_id="w")

            worker.register_process(["aletheia-daemon"])
            worker.heartbeat()

            rows = repo.list_worker_status()
            self.assertEqual(rows[0]["worker_id"], "w")
            self.assertEqual(rows[0]["status"], "RUNNING")
            self.assertIsNotNone(rows[0]["heartbeat_at"])

    def test_worker_dead_letters_invalid_task_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = QueueRepository(root / "queue.db", root / "control.db")
            repo.create_task("task", "p", "Task", {"args": {}}, depth=0)
            worker = DaemonWorker(repo, FakeToolAdapters(), project_id="p", worker_id="w")

            result = worker.run_once()

            self.assertEqual(result["error"], "invalid_task_payload")
            self.assertEqual(len(repo.list_dead_letters()), 1)

    def test_lease_recovery_releases_expired_leases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = QueueRepository(root / "queue.db", root / "control.db")
            repo.create_task("task", "p", "Task", {"tool": "x", "args": {}}, depth=0)
            repo.claim_ready_task("p", "w", "2000-01-01T00:00:00+00:00")

            released = repo.release_expired_leases("2026-01-01T00:00:00+00:00")

            self.assertEqual(released, 1)
            self.assertIsNone(repo.get_task("task")["lease_owner"])

    def test_migrations_record_initial_version_and_reject_unknown_future_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            with closing(sqlite3.connect(root / "queue.db")) as conn:
                rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
                self.assertEqual([row[0] for row in rows], ["0001_initial"])
                conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES ('9999_future', 'now')"
                )
                conn.commit()

            with self.assertRaises(RuntimeError):
                bootstrap_databases(root)

    def test_invalid_task_transition_is_rejected_and_valid_transition_is_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = QueueRepository(root / "queue.db", root / "control.db")
            repo.create_task("task", "p", "Task", {"tool": "x", "args": {}}, depth=0)

            with self.assertRaises(ValueError):
                repo.transition_task_state("task", "COMPLETED", "PLANNING", reason="bad")

            repo.transition_task_state("task", "PLANNING", "PENDING_APPROVAL", reason="needs_human")

            events = repo.list_task_events("task")
            self.assertEqual(events[-1]["event_type"], "state_transition")
            self.assertEqual(json.loads(events[-1]["details_json"])["to_state"], "PENDING_APPROVAL")

    def test_bridge_rejects_oversized_or_unauthorized_requests(self):
        security = BridgeSecurity(shared_secret="secret", max_line_bytes=10)
        self.assertTrue(line_too_large(b"01234567890", security))

        response = handle_json_rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools.call",
                "params": {"toolName": "x", "args": {}, "auth": {"timestamp": "0", "signature": "wrong"}},
            },
            FakeToolAdapters(),
            security,
        )

        self.assertEqual(response["error"]["code"], -32001)

    def test_bridge_accepts_hmac_auth_and_rejects_unknown_methods(self):
        security = BridgeSecurity(shared_secret="secret")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools.call", "params": {"toolName": "x", "args": {}}}
        message["params"]["auth"] = build_auth_envelope(message, "secret")

        response = handle_json_rpc(message, FakeToolAdapters(), security)
        missing = handle_json_rpc({"jsonrpc": "2.0", "id": 2, "method": "daemon.delete"}, FakeToolAdapters(), security)

        self.assertEqual(response["result"]["tool_name"], "x")
        self.assertEqual(missing["error"]["code"], -32601)

    def test_bridge_includes_nonce_in_auth_and_prevents_replay(self):
        security = BridgeSecurity(shared_secret="secret", nonce_cache=set())
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools.call", "params": {"toolName": "x", "args": {}}}
        message["params"]["auth"] = build_auth_envelope(message, "secret")

        response1 = handle_json_rpc(message, FakeToolAdapters(), security)
        self.assertEqual(response1["result"]["tool_name"], "x")

        response2 = handle_json_rpc(message, FakeToolAdapters(), security)
        self.assertEqual(response2["error"]["code"], -32001)

    def test_bridge_admin_gating_blocks_daemon_methods_when_disabled(self):
        security = BridgeSecurity(shared_secret="secret", enable_admin_bridge=False)
        message = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
        message["params"]["auth"] = build_auth_envelope(message, "secret")

        response = handle_json_rpc(message, FakeToolAdapters(), security)

        self.assertEqual(response["error"]["code"], -32002)

    def test_bridge_admin_gating_allows_daemon_methods_when_enabled(self):
        class Internal:
            def health(self):
                return {"ok": True}

        security = BridgeSecurity(shared_secret="secret", enable_admin_bridge=True)
        message = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
        message["params"]["auth"] = build_auth_envelope(message, "secret")

        response = handle_json_rpc(message, FakeToolAdapters(), security, internal_api=Internal())

        self.assertEqual(response["result"]["ok"], True)

    def test_bridge_admin_gating_blocks_daemon_methods_when_shared_secret_none(self):
        security = BridgeSecurity(shared_secret=None, enable_admin_bridge=True)
        message = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}

        response = handle_json_rpc(message, FakeToolAdapters(), security)

        self.assertEqual(response["error"]["code"], -32002)

    def test_nonce_cache_bounds_entries(self):
        security = BridgeSecurity(shared_secret="secret")
        # Simulate adding 4097 nonces
        for i in range(4097):
            nonce = f"nonce-{i}"
            message = {"jsonrpc": "2.0", "id": 1, "method": "tools.call", "params": {"toolName": "x", "args": {}}}
            message["params"]["auth"] = build_auth_envelope(message, "secret", nonce=nonce)
            handle_json_rpc(message, FakeToolAdapters(), security)
        
        self.assertLessEqual(len(security.nonce_cache), 4096)
        self.assertIn("nonce-4096", security.nonce_cache)  # Last one added

    def test_internal_health_and_dead_letter_methods_are_available(self):
        class Internal:
            def health(self):
                return {"ok": True}

            def dead_letters(self, limit=50):
                return [{"task_id": "t"}][:limit]

        security = BridgeSecurity(shared_secret="secret", enable_admin_bridge=True)
        health_msg = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
        health_msg["params"]["auth"] = build_auth_envelope(health_msg, "secret")
        dead_msg = {"jsonrpc": "2.0", "id": 2, "method": "daemon.dead_letters", "params": {"limit": 1}}
        dead_msg["params"]["auth"] = build_auth_envelope(dead_msg, "secret")

        health = handle_json_rpc(health_msg, FakeToolAdapters(), security, internal_api=Internal())
        dead = handle_json_rpc(dead_msg, FakeToolAdapters(), security, internal_api=Internal())

        self.assertEqual(health["result"], {"ok": True})
        self.assertEqual(dead["result"][0]["task_id"], "t")

    def test_operator_readme_exists(self):
        self.assertTrue((Path.cwd().parent / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
