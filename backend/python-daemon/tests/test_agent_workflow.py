from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.agent_workflow.mcp_tool import run_agent_workflow
from orchestrator.adapters import ToolAdapters
from orchestrator.active_partition.models import ActivePartition
from orchestrator.active_partition.repo import ActivePartitionRepository
from orchestrator.candidate_analysis.service import CandidateAnalysisService
from orchestrator.chroma_manager import ChromaConfig, ChromaManager
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.memory.conversation_summary import ConversationSummaryIngestor
from orchestrator.memory.repo import MemoryRepository
from orchestrator.memory.service import MemoryService
from orchestrator.memory.snapshots import SnapshotMemoryService
from orchestrator.active_partition.service import ActivePartitionService
from orchestrator.skills.registry import SkillRegistry as RealSkillRegistry


class FakeBridgeClient:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, object]]] = []

    def call_tool(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        self.calls.append((tool_name, dict(args)))
        if tool_name == "mcp_investigation_start":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "session started",
                "artifacts": {
                    "session_path": "C:/work/session.yaml",
                    "session_yaml": "C:/work/session.yaml",
                },
            }
        if tool_name == "mcp_investigation_filemap":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "file map complete",
                "artifacts": {"manifest_csv": "C:/work/manifest.csv"},
            }
        if tool_name == "mcp_investigation_validate_manifest":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "manifest validated",
                "artifacts": {"manifest_health_json": "C:/work/manifest-health.json", "manifest_doctor_json": "C:/work/manifest-doctor.json"},
            }
        if tool_name == "mcp_investigation_read_report":
            return {
                "ok": True,
                "status": "PASS",
                "summary": "report read",
                "content": "X" * 5000,
                "artifacts": {"manifest_doctor_md": "C:/work/manifest-doctor.md"},
            }
        if tool_name == "mcp_investigation_compile_handoff":
            return {
                "ok": True,
                "status": "COMPLETE",
                "summary": "handoff complete",
                "artifacts": {
                    "final_markdown": "C:/work/final.md",
                    "final_python_bundle": "C:/work/final.py",
                    "archive_yaml": "C:/work/archive.yaml",
                },
            }
        return {"ok": False, "status": "ERROR", "summary": f"unexpected tool {tool_name}", "artifacts": {}}


class FakeManifestBridgeClient:
    def __init__(self):
        self.target_repo: Path | None = None
        self.output_root: Path | None = None

    def call_tool(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        if tool_name == "mcp_investigation_start":
            self.target_repo = Path(str(args["target_repo"])).resolve()
            self.output_root = self.target_repo.parent / "local_tool_assist_outputs" / "sessions" / "s1"
            self.output_root.mkdir(parents=True, exist_ok=True)
            return {
                "ok": True,
                "status": "PASS",
                "summary": "session started",
                "artifacts": {"session_path": str(self.output_root / "session.yaml"), "session_yaml": str(self.output_root / "session.yaml")},
            }
        if tool_name == "mcp_investigation_filemap":
            assert self.target_repo is not None
            assert self.output_root is not None
            source = self.target_repo / "orchestrator" / "active_partition" / "service.py"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("class ActivePartitionService: pass\n", encoding="utf-8")
            generated = self.target_repo / "final_handoff_bundle_123.py"
            generated.write_text("bundle\n", encoding="utf-8")
            doctor = self.output_root / "intermediate" / "manifest_doctor.md"
            doctor.parent.mkdir(parents=True, exist_ok=True)
            doctor.write_text("doctor\n", encoding="utf-8")
            manifest = self.output_root / "manifest.csv"
            manifest.write_text(
                "root,rel_path,abs_path,ext,size,mtime_iso,sha1\n"
                f"{self.target_repo},orchestrator/active_partition/service.py,{source},.py,1,2026-01-01T00:00:00Z,abc\n"
                f"{self.target_repo},final_handoff_bundle_123.py,{generated},.py,1,2026-01-01T00:00:00Z,def\n"
                f"{self.target_repo},reports/manifest_doctor.md,{doctor},.md,1,2026-01-01T00:00:00Z,ghi\n",
                encoding="utf-8",
            )
            return {"ok": True, "status": "PASS", "summary": "file map complete", "artifacts": {"manifest_csv": str(manifest)}}
        if tool_name == "mcp_investigation_validate_manifest":
            return {"ok": True, "status": "PASS", "summary": "manifest validated", "artifacts": {"manifest_health_json": "health.json"}}
        if tool_name == "mcp_investigation_read_report":
            return {"ok": True, "status": "PASS", "summary": "report read", "content": "raw report", "artifacts": {"manifest_doctor_md": "doctor.md"}}
        if tool_name == "mcp_investigation_compile_handoff":
            return {"ok": True, "status": "COMPLETE", "summary": "handoff complete", "artifacts": {"final_markdown": "final.md", "archive_yaml": "archive.yaml"}}
        return {"ok": False, "status": "ERROR", "summary": f"unexpected tool {tool_name}", "artifacts": {}}


class FakeCollection:
    def upsert(self, **kwargs):
        return None

    def query(self, **kwargs):
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


class FakeChromaClient:
    def __init__(self):
        self.collection = FakeCollection()

    def get_or_create_collection(self, name):
        return self.collection


class FakeSnapshotChroma:
    def __init__(self):
        self.calls = []

    def upsert_chunks(self, **kwargs):
        self.calls.append(kwargs)
        return {"chunks_indexed": len(kwargs["chunks"])}


class FakeMemoryService:
    def __init__(self):
        self.calls = []

    def commit_memory(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ok": True,
            "status": "COMMITTED",
            "memory_id": "memory-1",
            "index_status": "indexed",
            "project_id": "p",
            "project_scope_hash": "scope",
        }


class FakeSkillRegistry:
    def __init__(self, queue_db_path, manifests=None, *, fail=False):
        self.queue_db_path = Path(queue_db_path)
        self.manifests = list(manifests or [])
        self.fail = fail
        self.list_calls = 0

    def list_verified(self):
        self.list_calls += 1
        if self.fail:
            raise RuntimeError("skill registry unavailable")
        return list(self.manifests)


BUG_TRIAGE_MANIFESTS = [
    {
        "skill_id": "bug_triage_v1",
        "triggers": ["triage bug", "regression", "diagnose"],
        "capabilities": ["bug_triage", "candidate_analysis", "tdd_planning", "root_cause_analysis"],
        "risk_tier": "T1",
    },
    {
        "skill_id": "candidate_analysis_v1",
        "triggers": ["candidate analysis", "rank files", "likely files"],
        "capabilities": ["candidate_analysis", "file_ranking"],
        "risk_tier": "T1",
    },
    {
        "skill_id": "refactor_plan_v1",
        "triggers": ["refactor plan", "technical debt plan", "rewrite plan"],
        "capabilities": ["refactor_planning"],
        "risk_tier": "T1",
    },
]


class WorkflowToolTests(unittest.TestCase):
    def test_invalid_target_repo_is_blocked_before_state_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "states"
            result = run_agent_workflow(
                objective="Investigate backend",
                target_repo="backend-orchestrator-repo",
                profile="safe",
                state_dir=state_dir,
                allowed_roots=(root,),
                bridge_client=FakeBridgeClient(),
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "POLICY_BLOCK")
            self.assertEqual(result["error"]["code"], "invalid_target_repo")
            self.assertFalse(state_dir.exists())

    def test_nonexistent_or_outside_target_repo_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "states"
            outside = root.parent / "outside-workspace"
            outside.mkdir(exist_ok=True)
            missing = root / "missing-workspace"

            missing_result = run_agent_workflow(
                objective="Investigate backend",
                target_repo=str(missing),
                profile="safe",
                state_dir=state_dir,
                allowed_roots=(root,),
                bridge_client=FakeBridgeClient(),
            )
            outside_result = run_agent_workflow(
                objective="Investigate backend",
                target_repo=str(outside),
                profile="safe",
                state_dir=state_dir,
                allowed_roots=(root,),
                bridge_client=FakeBridgeClient(),
            )

            self.assertEqual(missing_result["error"]["code"], "invalid_target_repo")
            self.assertEqual(outside_result["error"]["code"], "invalid_target_repo")

    def test_workflow_run_returns_compact_state_and_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            result = run_agent_workflow(
                objective="Investigate backend",
                target_repo=str(root),
                profile="safe",
                state_dir=state_dir,
                allowed_roots=(root,),
                bridge_client=FakeBridgeClient(),
            )
            state_path = Path(result["state_path"])
            state = json.loads(state_path.read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "COMPLETE")
            self.assertNotIn("C:/work/", result["summary"])
            self.assertTrue(state_path.exists())
            self.assertEqual(state["phase"], "FINAL")
            self.assertEqual(state["tool_results"][3]["content_omitted"], True)
            self.assertNotIn("content", state["tool_results"][3])
            self.assertEqual(state["tool_results"][3]["summary"], "report read")
            self.assertEqual(state["artifacts"]["session_path"], "C:/work/session.yaml")
            self.assertEqual(result["artifacts"]["session_yaml"], "C:/work/session.yaml")
            self.assertIn("manifest_csv", result["artifacts"])
            self.assertIn("manifest_health_json", result["artifacts"])
            self.assertIn("manifest_doctor_json", result["artifacts"])
            self.assertIn("manifest_doctor_md", result["artifacts"])
            self.assertIn("final_markdown", result["artifacts"])
            self.assertIn("final_python_bundle", result["artifacts"])
            self.assertIn("archive_yaml", result["artifacts"])
            self.assertNotIn("[", result["summary"])

    def test_tool_adapter_calls_workflow_helper_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = ActivePartitionRepository(root / "queue.db")
            active = ActivePartitionService(repo, conversations_root=root / "conversations", allowed_roots=(root,))
            memory = MemoryService(
                MemoryRepository(root / "queue.db"),
                repo,
                ChromaManager(
                    ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                    chroma_client=FakeChromaClient(),
                ),
            )
            adapters = ToolAdapters(active_partition=active, memory_service=memory, allowed_roots=(root,))

            with patch("orchestrator.adapters.run_agent_workflow") as mocked:
                mocked.return_value = {"ok": True, "status": "COMPLETE", "run_id": "r1", "summary": "done", "artifacts": {}, "state_path": "state.json", "error": None}
                result = adapters.call_mcp_tool(
                    "mcp_agent_workflow_run",
                    {"objective": "Investigate", "target_repo": str(root), "profile": "safe"},
                )

            self.assertTrue(result["ok"])
            self.assertEqual(mocked.call_count, 1)

    def test_workflow_selects_bug_triage_skill_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                with patch("orchestrator.agent_workflow.mcp_tool.SkillImporter.import_all") as mocked_import:
                    mocked_import.side_effect = AssertionError("SKILL.md import should not run during metadata-only selection")
                    result = run_agent_workflow(
                        objective="Triage this regression in the backend and identify the root cause.",
                        target_repo=str(root),
                        profile="safe",
                        state_dir=state_dir,
                        allowed_roots=(root,),
                        bridge_client=FakeBridgeClient(),
                    )

            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            selected = result["artifacts"]["selected_skill"]

            self.assertTrue(result["ok"])
            self.assertEqual(selected["skill_id"], "bug_triage_v1")
            self.assertEqual(selected["source"], "skill_registry")
            self.assertFalse(selected["instruction_loaded"])
            self.assertEqual(state["selected_skill"]["skill_id"], "bug_triage_v1")
            self.assertFalse(state.get("warnings"))

    def test_workflow_selects_bug_triage_from_live_skill_registry_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            bootstrap_databases(state_dir)
            skill_registry_root = Path(__file__).resolve().parents[2] / "agent_backend_skill_registry"

            result = run_agent_workflow(
                objective="Triage a regression/race condition in worker daemon startup and identify likely candidate files.",
                target_repo=str(root),
                profile="safe",
                state_dir=state_dir,
                allowed_roots=(root,),
                queue_db_path=state_dir / "queue.db",
                skill_registry_root=skill_registry_root,
                bridge_client=FakeBridgeClient(),
            )

            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            selected = result["artifacts"]["selected_skill"]

            self.assertTrue(result["ok"])
            self.assertEqual(selected["skill_id"], "bug_triage_v1")
            self.assertGreater(state["verified_skill_count"], 0)
            self.assertEqual(Path(state["skill_registry_root"]), skill_registry_root.resolve())
            self.assertTrue(state["selector_candidate_scores"])
            self.assertEqual(state["selector_candidate_scores"][0]["skill_id"], "bug_triage_v1")

    def test_workflow_selects_candidate_analysis_skill_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                result = run_agent_workflow(
                    objective="Rank candidate files for the likely fix location.",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    bridge_client=FakeBridgeClient(),
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["artifacts"]["selected_skill"]["skill_id"], "candidate_analysis_v1")
            self.assertIn("capabilities", result["artifacts"]["selected_skill"])

    def test_workflow_adds_round_one_compact_artifacts_when_services_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            active_repo.set_active_partition(
                ActivePartition(
                    client_id="local-lmstudio",
                    active_project_id="p",
                    active_project_scope_hash="scope",
                    active_conversation_id="chat",
                    conversation_path=str(root / "conversations" / "project" / "chat.conversation.json"),
                    confidence="high",
                    source_event="test",
                    updated_at="now",
                )
            )
            active = ActivePartitionService(active_repo, conversations_root=root / "conversations", allowed_roots=(root,))
            snapshot_chroma = FakeSnapshotChroma()
            memory = FakeMemoryService()
            state_dir = root / "agent-workflows"

            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                result = run_agent_workflow(
                    objective="Rank candidate files for the likely fix location.",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    queue_db_path=root / "queue.db",
                    bridge_client=FakeBridgeClient(),
                    active_partition=active,
                    memory_service=memory,  # type: ignore[arg-type]
                    snapshot_memory=SnapshotMemoryService(root / "queue.db", snapshot_chroma),
                    conversation_summary_ingestor=ConversationSummaryIngestor(),
                    candidate_analysis=CandidateAnalysisService(),
                )

            self.assertTrue(result["ok"])
            self.assertIn("snapshot_id", result["artifacts"])
            self.assertIn("candidate_analysis", result["artifacts"])
            self.assertIn("ranked_candidates", result["artifacts"]["candidate_analysis"])
            self.assertEqual(result["artifacts"]["summary_memory_result"]["memory_id"], "memory-1")
            self.assertEqual(len(snapshot_chroma.calls), 1)
            self.assertEqual(len(memory.calls), 1)

    def test_workflow_candidate_analysis_reads_manifest_and_excludes_artifacts_without_raw_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            bridge = FakeManifestBridgeClient()

            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                result = run_agent_workflow(
                    objective="Rank candidate files for active partition likely files.",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    bridge_client=bridge,
                    candidate_analysis=CandidateAnalysisService(),
                )

            state_text = Path(result["state_path"]).read_text(encoding="utf-8")
            candidate_result = result["artifacts"]["candidate_analysis"]
            paths = [item["rel_path"] for item in candidate_result["ranked_candidates"]]

            self.assertTrue(result["ok"])
            self.assertEqual(candidate_result["status"], "OK")
            self.assertIn("orchestrator/active_partition/service.py", paths)
            self.assertNotIn("final_handoff_bundle_123.py", paths)
            self.assertNotIn("reports/manifest_doctor.md", paths)
            self.assertNotIn("root,rel_path,abs_path", json.dumps(result))
            self.assertNotIn("root,rel_path,abs_path", state_text)

    def test_workflow_selects_refactor_plan_skill_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                result = run_agent_workflow(
                    objective="Create a refactor plan for the service layer.",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    bridge_client=FakeBridgeClient(),
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["artifacts"]["selected_skill"]["skill_id"], "refactor_plan_v1")

    def test_workflow_sets_selected_skill_null_when_no_manifest_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            with patch(
                "orchestrator.agent_workflow.mcp_tool.SkillRegistry",
                lambda queue_db_path: FakeSkillRegistry(
                    queue_db_path,
                    [
                        {
                            "skill_id": "architecture_review_v1",
                            "triggers": ["architecture review"],
                            "capabilities": ["architecture_review"],
                            "risk_tier": "T1",
                        }
                    ],
                ),
            ):
                result = run_agent_workflow(
                    objective="Draft a release note for the team.",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    bridge_client=FakeBridgeClient(),
                )

            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertIsNone(result["artifacts"]["selected_skill"])
            self.assertIsNone(state["selected_skill"])

    def test_workflow_records_registry_warning_when_registry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, fail=True)):
                result = run_agent_workflow(
                    objective="Investigate a backend bug report.",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    bridge_client=FakeBridgeClient(),
                )

            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertIsNone(result["artifacts"]["selected_skill"])
            self.assertTrue(state["warnings"])
            self.assertEqual(state["warnings"][0]["source"], "skill_registry")

    def test_workflow_invoked_through_tool_adapters_uses_in_process_dispatcher(self):
        class FakeWorkflowToolAssist:
            def __init__(self) -> None:
                self.calls: list[tuple[str, tuple[object, ...]]] = []

            def investigation_start(self, objective: str, target_repo: str, profile: str) -> dict[str, object]:
                self.calls.append(("start", (objective, target_repo, profile)))
                return {
                    "ok": True,
                    "status": "created",
                    "summary": "session started",
                    "artifacts": {
                        "session_path": "C:/work/session.yaml",
                        "session_yaml": "C:/work/session.yaml",
                    },
                }

            def investigation_filemap(self, session_path: str, profile: str) -> dict[str, object]:
                self.calls.append(("filemap", (session_path, profile)))
                return {
                    "ok": True,
                    "status": "PASS",
                    "summary": "file map complete",
                    "artifacts": {"manifest_csv": "C:/work/manifest.csv"},
                }

            def investigation_validate_manifest(self, session_path: str) -> dict[str, object]:
                self.calls.append(("validate", (session_path,)))
                return {
                    "ok": True,
                    "status": "PASS",
                    "summary": "manifest validated",
                    "artifacts": {
                        "manifest_health_json": "C:/work/manifest-health.json",
                        "manifest_doctor_json": "C:/work/manifest-doctor.json",
                    },
                }

            def investigation_read_report(self, session_path: str, artifact_key: str, max_chars: int) -> dict[str, object]:
                self.calls.append(("read_report", (session_path, artifact_key, max_chars)))
                return {
                    "ok": True,
                    "status": "PASS",
                    "summary": "report read",
                    "content": "X" * 5000,
                    "artifacts": {"manifest_doctor_md": "C:/work/manifest-doctor.md"},
                }

            def investigation_compile_handoff(self, session_path: str) -> dict[str, object]:
                self.calls.append(("compile", (session_path,)))
                return {
                    "ok": True,
                    "status": "COMPLETE",
                    "summary": "handoff complete",
                    "artifacts": {
                        "final_markdown": "C:/work/final.md",
                        "final_python_bundle": "C:/work/final.py",
                        "archive_yaml": "C:/work/archive.yaml",
                    },
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = ActivePartitionRepository(root / "queue.db")
            active = ActivePartitionService(repo, conversations_root=root / "conversations", allowed_roots=(root,))
            memory = MemoryService(
                MemoryRepository(root / "queue.db"),
                repo,
                ChromaManager(
                    ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                    chroma_client=FakeChromaClient(),
                ),
            )
            tool_assist = FakeWorkflowToolAssist()
            adapters = ToolAdapters(
                active_partition=active,
                memory_service=memory,
                tool_assist=tool_assist,
                allowed_roots=(root,),
                queue_db_path=root / "queue.db",
            )

            with patch("orchestrator.agent_workflow.runner.TcpBridgeClient") as mocked_bridge_client:
                result = adapters.call_mcp_tool(
                    "mcp_agent_workflow_run",
                    {"objective": "Investigate backend", "target_repo": str(root), "profile": "safe"},
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(tool_assist.calls[0][0], "start")
            self.assertEqual(mocked_bridge_client.call_count, 0)

    def test_workflow_tool_failure_inside_in_process_dispatcher_is_compact(self):
        class FailingWorkflowToolAssist:
            def investigation_start(self, objective: str, target_repo: str, profile: str) -> dict[str, object]:
                raise RuntimeError("nested start failed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = ActivePartitionRepository(root / "queue.db")
            active = ActivePartitionService(repo, conversations_root=root / "conversations", allowed_roots=(root,))
            memory = MemoryService(
                MemoryRepository(root / "queue.db"),
                repo,
                ChromaManager(
                    ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                    chroma_client=FakeChromaClient(),
                ),
            )
            adapters = ToolAdapters(
                active_partition=active,
                memory_service=memory,
                tool_assist=FailingWorkflowToolAssist(),
                allowed_roots=(root,),
                queue_db_path=root / "queue.db",
            )

            result = adapters.call_mcp_tool(
                "mcp_agent_workflow_run",
                {"objective": "Investigate backend", "target_repo": str(root), "profile": "safe"},
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "ERROR")
            self.assertIn("nested start failed", result["summary"])

    def test_workflow_skill_registry_uses_expected_queue_db_and_does_not_warn_when_table_exists(self):
        seen_paths: list[Path] = []

        class CapturingSkillRegistry(RealSkillRegistry):
            def __init__(self, queue_db_path: Path) -> None:
                seen_paths.append(Path(queue_db_path).resolve())
                super().__init__(queue_db_path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            state_dir = root / "agent-workflows"
            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", CapturingSkillRegistry):
                result = run_agent_workflow(
                    objective="Investigate backend",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    queue_db_path=root / "queue.db",
                    bridge_client=FakeBridgeClient(),
                )

            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertEqual(seen_paths[0], (root / "queue.db").resolve())
            self.assertFalse(any(warning.get("code") == "skill_registry_unavailable" for warning in state["warnings"]))
            self.assertEqual(state["skill_registry_db_path"], str((root / "queue.db").resolve()))

    def test_workflow_registry_failure_warning_includes_db_path_and_migration(self):
        class FailingSkillRegistry:
            def __init__(self, queue_db_path: Path) -> None:
                self.queue_db_path = Path(queue_db_path)

            def list_verified(self) -> list[dict[str, object]]:
                raise RuntimeError("registry open failed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "agent-workflows"
            with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", FailingSkillRegistry):
                result = run_agent_workflow(
                    objective="Investigate backend",
                    target_repo=str(root),
                    profile="safe",
                    state_dir=state_dir,
                    allowed_roots=(root,),
                    queue_db_path=root / "queue.db",
                    bridge_client=FakeBridgeClient(),
                )

            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            warning = state["warnings"][0]
            self.assertEqual(warning["code"], "skill_registry_unavailable")
            self.assertEqual(warning["db_path"], str((root / "queue.db").resolve()))
            self.assertEqual(warning["expected_table"], "skill_manifests")
            self.assertEqual(warning["migration"], "0004_skill_manifests")

    def test_direct_mcp_investigation_start_behavior_remains_unchanged(self):
        class FakeWorkflowToolAssist:
            def investigation_start(self, objective: str, target_repo: str, profile: str) -> dict[str, object]:
                return {
                    "ok": True,
                    "status": "created",
                    "summary": "session started",
                    "artifacts": {"session_path": "C:/work/session.yaml"},
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = ActivePartitionRepository(root / "queue.db")
            active = ActivePartitionService(repo, conversations_root=root / "conversations", allowed_roots=(root,))
            memory = MemoryService(
                MemoryRepository(root / "queue.db"),
                repo,
                ChromaManager(
                    ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                    chroma_client=FakeChromaClient(),
                ),
            )
            adapters = ToolAdapters(
                active_partition=active,
                memory_service=memory,
                tool_assist=FakeWorkflowToolAssist(),
                allowed_roots=(root,),
                queue_db_path=root / "queue.db",
            )

            result = adapters.call_mcp_tool(
                "mcp_investigation_start",
                {"objective": "Investigate backend", "target_repo": str(root), "profile": "safe"},
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "created")
