import json
import sqlite3
import tempfile
import unittest
from collections import deque
from contextlib import closing
from pathlib import Path
import threading
import time

from orchestrator.adapters import ToolAdapters
from orchestrator.bridge_server import BridgeSecurity, build_auth_envelope, handle_json_rpc, line_too_large
from orchestrator.config import RuntimeConfig
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.main import maybe_import_skills
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
            self.assertEqual(config.enable_lmstudio_watcher, False)
            self.assertEqual(config.active_partition_settle_ms, 750)
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
                self.assertIsNone(runtime.active_partition_watcher)
            finally:
                runtime.close()

    def test_build_runtime_starts_and_closes_lmstudio_watcher_only_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conversations = root / "conversations"
            conversations.mkdir()
            config = RuntimeConfig.from_env(
                {
                    "ALETHEIA_PROJECT_ROOT": str(root),
                    "ALETHEIA_STATE_DIR": str(root / "state"),
                    "ALETHEIA_ALLOWED_ROOTS": str(root),
                    "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                    "ALETHEIA_LMSTUDIO_CONVERSATIONS_DIR": str(conversations),
                    "ALETHEIA_ENABLE_LMSTUDIO_WATCHER": "true",
                    "ALETHEIA_ACTIVE_PARTITION_SETTLE_MS": "0",
                }
            )

            runtime = build_runtime(config)

            self.assertIsNotNone(runtime.active_partition_watcher)
            self.assertTrue(runtime.active_partition_watcher.is_running)
            runtime.close()
            self.assertFalse(runtime.active_partition_watcher.is_running)

    def test_runtime_wires_ocr_provider_into_pdf_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = RuntimeConfig.from_env(
                {
                    "ALETHEIA_PROJECT_ROOT": str(root),
                    "ALETHEIA_STATE_DIR": str(root / "state"),
                    "ALETHEIA_ALLOWED_ROOTS": str(root),
                    "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                    "ALETHEIA_OCR_COMMAND": "ocr-binary",
                }
            )

            runtime = build_runtime(config)

            try:
                self.assertIsNotNone(runtime.ingest.pdf_processor.ocr_provider)
                self.assertIs(runtime.ingest.pdf_processor.ocr_provider, runtime.tool_adapters.ocr_provider)
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
                self.assertEqual(
                    [row[0] for row in rows],
                    [
                        "0001_initial",
                        "0002_active_partition_memory",
                        "0003_memory_index_state",
                        "0004_skill_manifests",
                        "0005_snapshot_patch_records",
                        "0006_patch_artifacts",
                    ],
                )
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                self.assertIn("snapshot_records", tables)
                self.assertIn("patch_artifacts", tables)
                self.assertNotIn("file_snapshots", tables)
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

    def test_runtime_config_defaults_embedding_model_to_correct_lm_studio_key(self):
        config = RuntimeConfig.from_env({})
        self.assertEqual(config.embedding_model, "text-embedding-nomic-embed-text-v1.5")

    def test_daemon_startup_imports_verified_skills_into_queue_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            bootstrap_databases(state_dir)
            config = RuntimeConfig.from_env(
                {
                    "ALETHEIA_PROJECT_ROOT": str(root),
                    "ALETHEIA_STATE_DIR": str(state_dir),
                    "ALETHEIA_ALLOWED_ROOTS": str(root),
                }
            )
            report = maybe_import_skills(config, state_dir / "queue.db")

            with closing(sqlite3.connect(state_dir / "queue.db")) as conn:
                verified_count = conn.execute(
                    "SELECT COUNT(*) FROM skill_manifests WHERE status = 'verified'"
                ).fetchone()[0]

            self.assertIsNotNone(report)
            self.assertGreaterEqual(int(verified_count), 1)


class FakeResponseForLMStudio:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class LMStudioManagerTests(unittest.TestCase):
    def test_connection_summary_reports_token_presence_without_leaking_token(self):
        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig

        with_token = LMStudioManager(LMStudioManagerConfig(api_token="super-secret"))
        without_token = LMStudioManager(LMStudioManagerConfig())

        self.assertTrue(with_token.connection_summary()["token_present"])
        self.assertFalse(without_token.connection_summary()["token_present"])
        self.assertNotIn("super-secret", json.dumps(with_token.connection_summary()))

    def test_list_models_accepts_models_and_data_keys(self):
        calls = []
        def get(url, headers=None, timeout=None):
            calls.append((url, headers))
            return FakeResponseForLMStudio({"models": [{"key": "model1", "type": "embedding", "state": "loaded", "loaded_instances": [{"id": "model1"}]}]})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get)

        models = manager.list_models()

        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].key, "model1")
        self.assertEqual(models[0].type, "embedding")

    def test_ensure_embedding_model_loaded_rejects_non_embedding_model(self):
        def get(url, **kwargs):
            return FakeResponseForLMStudio({"models": [{"key": "chat-model", "type": "chat"}]})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig, LMStudioManagerError
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get)

        with self.assertRaises(LMStudioManagerError) as cm:
            manager.ensure_embedding_model_loaded("chat-model")

        self.assertIn("not an embedding model", str(cm.exception))

    def test_ensure_embedding_model_loaded_loads_unloaded_model(self):
        get_calls = []
        post_calls = []
        def get(url, **kwargs):
            get_calls.append(url)
            return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "state": "unloaded", "loaded_instances": []}]})

        def post(url, json=None, **kwargs):
            post_calls.append((url, json))
            return FakeResponseForLMStudio({})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)

        manager.ensure_embedding_model_loaded("embed-model")

        self.assertEqual(len(post_calls), 1)
        self.assertEqual(post_calls[0][0], "http://127.0.0.1:1234/api/v1/models/load")
        self.assertEqual(post_calls[0][1], {"model": "embed-model"})

    def test_ensure_embedding_model_loaded_skips_when_exact_loaded_instance_present(self):
        post_calls = []

        def get(url, **kwargs):
            return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "loaded_instances": [{"id": "embed-model"}], "state": "loaded"}]})

        def post(url, **kwargs):
            post_calls.append(url)
            return FakeResponseForLMStudio({})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)

        manager.ensure_embedding_model_loaded("embed-model")

        self.assertEqual(post_calls, [])

    def test_ensure_embedding_model_loaded_skips_when_suffixed_loaded_instance_present(self):
        post_calls = []

        def get(url, **kwargs):
            return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "loaded_instances": [{"id": "embed-model:4"}], "state": "loaded"}]})

        def post(url, **kwargs):
            post_calls.append(url)
            return FakeResponseForLMStudio({})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)

        manager.ensure_embedding_model_loaded("embed-model")

        self.assertEqual(post_calls, [])

    def test_ensure_embedding_model_loaded_warns_on_multiple_loaded_instances(self):
        post_calls = []

        def get(url, **kwargs):
            return FakeResponseForLMStudio({
                "models": [
                    {
                        "key": "embed-model",
                        "type": "embedding",
                        "loaded_instances": [{"id": "embed-model"}, {"id": "embed-model:2"}],
                        "state": "loaded",
                    }
                ]
            })

        def post(url, **kwargs):
            post_calls.append(url)
            return FakeResponseForLMStudio({})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)

        with self.assertLogs("orchestrator.lm_studio_manager", level="WARNING") as logs:
            manager.ensure_embedding_model_loaded("embed-model")

        self.assertEqual(post_calls, [])
        self.assertTrue(any("multiple loaded instances" in line for line in logs.output))

    def test_concurrent_ensure_embedding_model_loaded_calls_only_load_once(self):
        state = {"loaded": False, "get_calls": 0, "post_calls": 0}
        state_lock = threading.Lock()

        def get(url, **kwargs):
            with state_lock:
                state["get_calls"] += 1
                call_number = state["get_calls"]
                loaded = state["loaded"]
            if call_number == 1:
                time.sleep(0.05)
            payload = {
                "models": [
                    {
                        "key": "embed-model",
                        "type": "embedding",
                        "state": "loaded" if loaded else "unloaded",
                        "loaded_instances": [{"id": "embed-model"}] if loaded else [],
                    }
                ]
            }
            return FakeResponseForLMStudio(payload)

        def post(url, json=None, **kwargs):
            with state_lock:
                state["post_calls"] += 1
                state["loaded"] = True
            return FakeResponseForLMStudio({})

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)

        errors: list[BaseException] = []

        def worker():
            try:
                manager.ensure_embedding_model_loaded("embed-model")
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(state["post_calls"], 1)
        self.assertEqual(errors, [])

    def test_401_from_list_models_gives_clear_token_error(self):
        import requests
        def get(url, **kwargs):
            raise requests.HTTPError(response=type('Response', (), {'status_code': 401})())

        from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig, LMStudioManagerError
        manager = LMStudioManager(LMStudioManagerConfig(), http_get=get)

        with self.assertRaises(LMStudioManagerError) as cm:
            manager.list_models()

        self.assertIn("set ALETHEIA_LM_STUDIO_API_TOKEN", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
