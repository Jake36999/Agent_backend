from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Protocol

from .active_partition.models import ActivePartition, MemoryProject
from .active_partition.service import ActivePartitionService, ActivePartitionServiceError
from .agent_workflow.bridge_client import InProcessToolClient
from .agent_workflow.mcp_tool import run_agent_workflow
from .candidate_analysis.service import CandidateAnalysisService
from .capabilities.registry import CapabilityRegistry
from .code_intelligence.analyzer import CodeIntelligenceAnalyzer
from .memory.conversation_summary import ConversationSummaryIngestor
from .memory.service import MemoryService
from .memory.snapshots import SnapshotMemoryService
from .patching.service import PatchGenerationService
from .patching.apply import PatchApplyService
from .pipeline.compiler import PipelineCompiler
from .pipeline.loader import PipelineLoader
from .tool_assist_adapter import ToolAssistAdapter

import yaml


class AdapterFailure(ValueError):
    pass


def _to_public_capability_dict(manifest: Any) -> dict[str, Any]:
    data = manifest.to_dict()
    data.pop("source_path", None)
    return data


class SemanticMemoryAdapter(Protocol):
    def search(self, project_id: str, query: str, k: int) -> list[dict[str, object]]:
        ...

    def ingest_target(
        self,
        project_id: str,
        absolute_path: str,
        *,
        mime_type: str | None = None,
        force_reindex: bool = False,
    ) -> dict[str, object]:
        ...


class OCRProvider(Protocol):
    def extract_image_text(self, absolute_path: str, page: int | None, region: dict[str, int] | None) -> str:
        ...


class WorkspaceScoutAdapter(Protocol):
    def scout(
        self,
        project_id: str,
        absolute_path: str,
        *,
        max_files: int = 500,
        include_summaries: bool = True,
        ) -> dict[str, Any]:
        ...


class ActivePartitionAdapter(Protocol):
    def get_active_partition(self) -> ActivePartition | None:
        ...

    def set_active_from_conversation_path(self, conversation_json_path: str, source_event: str = "manual_override") -> ActivePartition:
        ...

    def set_active_project(self, project_id: str, display_name: str | None = None) -> ActivePartition:
        ...

    def list_memory_projects(self) -> list[MemoryProject]:
        ...


class FileToolAdapter:
    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def _resolve(self, path: str) -> Path:
        resolved = Path(path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise AdapterFailure("path escapes allowed roots")
        return resolved

    def read_file(self, file_path: str) -> str:
        try:
            return self._resolve(file_path).read_text(encoding="utf-8", errors="replace")
        except AdapterFailure:
            raise
        except Exception as exc:
            raise AdapterFailure(f"read_file failed: {exc}") from exc

    def read_file_snippet(self, file_path: str, start_line: int, end_line: int) -> str:
        if start_line < 1 or end_line < start_line:
            raise AdapterFailure("invalid line range")
        lines = self.read_file(file_path).splitlines(keepends=True)
        return "".join(lines[start_line - 1:end_line])

    def list_directory(self, directory_path: str) -> list[str]:
        try:
            return sorted(os.listdir(self._resolve(directory_path)))
        except AdapterFailure:
            raise
        except Exception as exc:
            raise AdapterFailure(f"list_directory failed: {exc}") from exc

    def package_directory(self, directory_path: str) -> str:
        root = self._resolve(directory_path)
        tree: dict[str, Any] = {}
        try:
            for current, dirs, files in os.walk(root):
                dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"})
                rel_root = os.path.relpath(current, root)
                subtree = tree
                if rel_root != ".":
                    for part in rel_root.split(os.sep):
                        subtree = subtree.setdefault(part, {})
                subtree["files"] = sorted(files)
            return yaml.dump(tree, sort_keys=False)
        except Exception as exc:
            raise AdapterFailure(f"package_directory failed: {exc}") from exc

    def verify_integrity(self, absolute_path: str, expected_sha256: str, expected_metadata_hash: str) -> dict[str, Any]:
        path = self._resolve(absolute_path)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            stat = path.stat()
            metadata = {
                "file_sha256": digest,
                "file_name": path.name,
                "absolute_path": str(path),
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
            metadata_hash = hashlib.sha256(
                json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        except Exception as exc:
            raise AdapterFailure(f"verify_integrity failed: {exc}") from exc
        return {
            "ok": digest.lower() == expected_sha256.lower() and metadata_hash == expected_metadata_hash,
            "sha256": digest,
            "metadata_hash": metadata_hash,
            "metadata": metadata,
        }


class ReadOnlySqliteAdapter:
    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def _resolve(self, db_path: str) -> Path:
        resolved = Path(db_path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise AdapterFailure("database path escapes allowed roots")
        return resolved

    def query(self, db_path: str, query: str, *, row_limit: int = 100) -> list[dict[str, Any]]:
        normalized = query.strip().lower()
        if ";" in query:
            raise AdapterFailure("semicolons are not allowed")
        if normalized.startswith("--") or normalized.startswith("/*"):
            raise AdapterFailure("leading comments are not allowed")
        if normalized.startswith("with"):
            raise AdapterFailure("WITH statements are not allowed")
        if not normalized.startswith("select"):
            raise AdapterFailure("only SELECT queries are allowed")
        forbidden = ("pragma", "attach", "detach", "insert", "update", "delete", "drop", "alter")
        if any(token in normalized.split() for token in forbidden):
            raise AdapterFailure("query contains a forbidden operation")
        if row_limit < 1 or row_limit > 1000:
            raise AdapterFailure("row_limit must be between 1 and 1000")
        uri = self._resolve(db_path).as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            cursor = conn.execute(f"SELECT * FROM ({query}) LIMIT ?", (row_limit,))
            columns = [column[0] for column in cursor.description or []]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as exc:
            raise AdapterFailure(f"sqlite query failed: {exc}") from exc
        finally:
            conn.close()


class ToolAdapters:
    def __init__(
        self,
        *,
        semantic_memory: SemanticMemoryAdapter | None = None,
        file_tools: FileToolAdapter | None = None,
        sqlite_tools: ReadOnlySqliteAdapter | None = None,
        workspace_scout: WorkspaceScoutAdapter | None = None,
        ocr_provider: OCRProvider | None = None,
        tool_assist: ToolAssistAdapter | None = None,
        active_partition: ActivePartitionService | None = None,
        memory_service: MemoryService | None = None,
        snapshot_memory: SnapshotMemoryService | None = None,
        conversation_summary_ingestor: ConversationSummaryIngestor | None = None,
        candidate_analysis: CandidateAnalysisService | None = None,
        patch_generation: PatchGenerationService | None = None,
        patch_apply: PatchApplyService | None = None,
        allowed_roots: tuple[Path, ...] | None = None,
        skill_registry_root: Path | None = None,
        queue_db_path: Path | None = None,
        pipeline_compiler: PipelineCompiler | None = None,
        pipeline_loader: PipelineLoader | None = None,
        capability_registry: CapabilityRegistry | None = None,
        code_intelligence: CodeIntelligenceAnalyzer | None = None,
        sandbox: Any | None = None,
    ) -> None:
        self.semantic_memory = semantic_memory
        self.file_tools = file_tools
        self.sqlite_tools = sqlite_tools
        self.workspace_scout = workspace_scout
        self.ocr_provider = ocr_provider
        self.tool_assist = tool_assist or ToolAssistAdapter()
        self.active_partition = active_partition
        self.memory_service = memory_service
        self.snapshot_memory = snapshot_memory
        self.conversation_summary_ingestor = conversation_summary_ingestor
        self.candidate_analysis = candidate_analysis
        self.patch_generation = patch_generation
        self.patch_apply = patch_apply
        self.pipeline_compiler = pipeline_compiler
        self.pipeline_loader = pipeline_loader
        self.capability_registry = capability_registry
        self.code_intelligence = code_intelligence
        self.sandbox = sandbox
        self.allowed_roots = tuple(root.resolve() for root in (allowed_roots or ()))
        self.skill_registry_root = Path(skill_registry_root).resolve() if skill_registry_root is not None else None
        if queue_db_path is not None:
            self.queue_db_path = Path(queue_db_path).resolve()
        elif memory_service is not None and hasattr(memory_service, "repo") and hasattr(memory_service.repo, "queue_db"):
            self.queue_db_path = Path(memory_service.repo.queue_db).resolve()
        elif active_partition is not None and hasattr(active_partition, "repo") and hasattr(active_partition.repo, "queue_db"):
            self.queue_db_path = Path(active_partition.repo.queue_db).resolve()
        else:
            self.queue_db_path = None

    def _workflow_tool_client(self) -> InProcessToolClient:
        return InProcessToolClient(
            self.call_mcp_tool,
            allowed_tools={
                "mcp_investigation_start",
                "mcp_investigation_filemap",
                "mcp_investigation_validate_manifest",
                "mcp_investigation_read_report",
                "mcp_investigation_compile_handoff",
            },
        )

    def call_mcp_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            if tool_name == "mcp_semantic_search":
                if self.semantic_memory is None:
                    raise AdapterFailure("semantic memory adapter is not configured")
                return {
                    "ok": True,
                    "results": self.semantic_memory.search(
                        str(args["project_id"]),
                        str(args["query"]),
                        int(args.get("k", 8)),
                    ),
                }
            if tool_name == "mcp_get_active_partition":
                if self.active_partition is None:
                    raise AdapterFailure("active partition service is not configured")
                partition = self.active_partition.get_active_partition()
                if partition is None:
                    return {
                        "ok": False,
                        "status": "NO_ACTIVE_PARTITION",
                        "summary": "No active partition is available.",
                        "artifacts": {},
                        "error": {"code": "no_active_partition", "message": "No active partition is available."},
                    }
                return {"ok": True, "status": "OK", "summary": "Active partition loaded.", "partition": partition.to_dict(), "artifacts": {}}
            if tool_name == "mcp_set_active_partition":
                if self.active_partition is None:
                    raise AdapterFailure("active partition service is not configured")
                if "project_id" in args:
                    return {
                        "ok": False,
                        "status": "POLICY_BLOCK",
                        "summary": "mcp_set_active_partition accepts only conversation_path.",
                        "artifacts": {},
                        "error": {"code": "invalid_active_partition_input", "message": "mcp_set_active_partition accepts only conversation_path."},
                    }
                try:
                    if not args.get("conversation_path"):
                        return {
                            "ok": False,
                            "status": "POLICY_BLOCK",
                            "summary": "conversation_path is required.",
                            "artifacts": {},
                            "error": {"code": "missing_active_partition_input", "message": "conversation_path is required."},
                        }
                    partition = self.active_partition.set_active_from_conversation_path(
                        str(args["conversation_path"]),
                        str(args.get("source_event", "manual_override")),
                    )
                except ActivePartitionServiceError as exc:
                    return {
                        "ok": False,
                        "status": exc.code,
                        "summary": exc.message,
                        "artifacts": {},
                        "error": exc.to_dict(),
                    }
                return {"ok": True, "status": "OK", "summary": "Active partition updated.", "partition": partition.to_dict(), "artifacts": {}}
            if tool_name == "mcp_set_active_project_manual":
                if self.active_partition is None:
                    raise AdapterFailure("active partition service is not configured")
                if "project_id" not in args:
                    return {
                        "ok": False,
                        "status": "POLICY_BLOCK",
                        "summary": "project_id is required.",
                        "artifacts": {},
                        "error": {"code": "missing_active_project_id", "message": "project_id is required."},
                    }
                try:
                    partition = self.active_partition.set_active_project(
                        str(args["project_id"]),
                        display_name=args.get("display_name"),
                    )
                except ActivePartitionServiceError as exc:
                    return {
                        "ok": False,
                        "status": exc.code,
                        "summary": exc.message,
                        "artifacts": {},
                        "error": exc.to_dict(),
                    }
                return {"ok": True, "status": "OK", "summary": "Active project override updated.", "partition": partition.to_dict(), "artifacts": {}}
            if tool_name == "mcp_list_memory_projects":
                if self.active_partition is None:
                    raise AdapterFailure("active partition service is not configured")
                projects = [project.to_dict() for project in self.active_partition.list_memory_projects()]
                return {"ok": True, "status": "OK", "summary": f"Loaded {len(projects)} memory projects.", "projects": projects, "artifacts": {}}
            if tool_name == "mcp_semantic_search_active":
                if self.memory_service is None:
                    raise AdapterFailure("memory service is not configured")
                return self.memory_service.semantic_search_active(str(args["query"]), int(args.get("k", 8)))
            if tool_name == "mcp_commit_memory":
                if self.memory_service is None:
                    raise AdapterFailure("memory service is not configured")
                metadata = args.get("metadata")
                if metadata is not None and not isinstance(metadata, dict):
                    raise AdapterFailure("metadata must be an object")
                return self.memory_service.commit_memory(
                    str(args["category"]),
                    str(args["content"]),
                    float(args.get("confidence_score", 1.0)),
                    metadata=metadata,
                )
            if tool_name == "mcp_agent_workflow_run":
                objective = args.get("objective")
                target_repo = args.get("target_repo")
                if not isinstance(objective, str) or not isinstance(target_repo, str):
                    return {
                        "ok": False,
                        "status": "POLICY_BLOCK",
                        "summary": "objective and target_repo are required.",
                        "artifacts": {},
                        "error": {"code": "missing_workflow_input", "message": "objective and target_repo are required."},
                    }
                pipeline_id = str(args.get("pipeline_id", "")) or None
                pipeline_vars = args.get("pipeline_vars")
                if pipeline_vars is not None and not isinstance(pipeline_vars, dict):
                    raise AdapterFailure("pipeline_vars must be an object")
                return run_agent_workflow(
                    objective=objective,
                    target_repo=target_repo,
                    profile=str(args.get("profile", "safe")),
                    allow_ingest=bool(args.get("allow_ingest", False)),
                    include_report_preview=bool(args.get("include_report_preview", False)),
                    use_model_phases=bool(args.get("use_model_phases", False)),
                    allowed_roots=self.allowed_roots if self.allowed_roots else None,
                    skill_registry_root=self.skill_registry_root,
                    queue_db_path=self.queue_db_path,
                    tool_client=self._workflow_tool_client(),
                    active_partition=self.active_partition,
                    memory_service=self.memory_service,
                    snapshot_memory=self.snapshot_memory,
                    conversation_summary_ingestor=self.conversation_summary_ingestor,
                    candidate_analysis=self.candidate_analysis,
                    pipeline_id=pipeline_id,
                    pipeline_vars=dict(pipeline_vars or {}),
                    pipeline_compiler=self.pipeline_compiler,
                    pipeline_loader=self.pipeline_loader,
                )
            if tool_name == "mcp_ingest_target":
                if self.semantic_memory is None:
                    raise AdapterFailure("semantic memory adapter is not configured")
                return {
                    "ok": True,
                    "result": self.semantic_memory.ingest_target(
                        str(args["project_id"]),
                        str(args["absolute_path"]),
                        mime_type=args.get("mime_type"),
                        force_reindex=bool(args.get("force_reindex", False)),
                    ),
                }
            if tool_name == "mcp_scout_workspace":
                if self.workspace_scout is None:
                    raise AdapterFailure("workspace scout adapter is not configured")
                return {
                    "ok": True,
                    "result": self.workspace_scout.scout(
                        str(args["project_id"]),
                        str(args["absolute_path"]),
                        max_files=int(args.get("max_files", 500)),
                        include_summaries=bool(args.get("include_summaries", True)),
                    ),
                }
            if tool_name == "mcp_verify_integrity":
                if self.file_tools is None:
                    raise AdapterFailure("file tools adapter is not configured")
                return {
                    "ok": True,
                    "result": self.file_tools.verify_integrity(
                        str(args["absolute_path"]),
                        str(args["expected_sha256"]),
                        str(args["expected_metadata_hash"]),
                    ),
                }
            if tool_name == "mcp_investigation_start":
                if self.tool_assist is None:
                    raise AdapterFailure("tool assist adapter is not configured")
                return self.tool_assist.investigation_start(
                    str(args["objective"]),
                    str(args["target_repo"]),
                    str(args.get("profile", "safe")),
                )
            if tool_name == "mcp_investigation_filemap":
                if self.tool_assist is None:
                    raise AdapterFailure("tool assist adapter is not configured")
                return self.tool_assist.investigation_filemap(
                    str(args["session_path"]),
                    str(args.get("profile", "safe")),
                )
            if tool_name == "mcp_investigation_validate_manifest":
                if self.tool_assist is None:
                    raise AdapterFailure("tool assist adapter is not configured")
                return self.tool_assist.investigation_validate_manifest(str(args["session_path"]))
            if tool_name == "mcp_investigation_read_report":
                if self.tool_assist is None:
                    raise AdapterFailure("tool assist adapter is not configured")
                return self.tool_assist.investigation_read_report(
                    str(args["session_path"]),
                    str(args["artifact_key"]),
                    int(args.get("max_chars", 12000)),
                )
            if tool_name == "mcp_investigation_compile_handoff":
                if self.tool_assist is None:
                    raise AdapterFailure("tool assist adapter is not configured")
                return self.tool_assist.investigation_compile_handoff(str(args["session_path"]))
            if tool_name == "mcp_extract_image":
                if self.ocr_provider is None:
                    raise AdapterFailure("OCR provider is not configured")
                return {
                    "ok": True,
                    "text": self.ocr_provider.extract_image_text(
                        str(args["absolute_path"]),
                        args.get("page"),
                        args.get("region"),
                    ),
                }
            if tool_name == "mcp_list_capabilities":
                if self.capability_registry is None:
                    raise AdapterFailure("capability registry is not configured")
                cap_type = args.get("capability_type")
                status = args.get("status")
                from .capabilities.models import CapabilityType as CT
                ct = CT(cap_type) if cap_type else None
                manifests = self.capability_registry.list_all(capability_type=ct, status=status)
                return {
                    "ok": True,
                    "status": "OK",
                    "summary": f"Found {len(manifests)} capabilities.",
                    "capabilities": [_to_public_capability_dict(m) for m in manifests],
                    "artifacts": {},
                }
            if tool_name == "mcp_code_intelligence":
                if self.code_intelligence is None:
                    raise AdapterFailure("code intelligence analyzer is not configured")
                mode = str(args["mode"])
                result = self.code_intelligence.analyze(
                    str(args["target_repo"]),
                    mode,
                    max_files=int(args.get("max_files", 500)),
                    max_edges=int(args.get("max_edges", 500)),
                    max_chars=int(args.get("max_chars", 8000)),
                    focus_paths=list(args["focus_paths"]) if args.get("focus_paths") else None,
                )
                from .capabilities.receipt import build_receipt, compact_receipt
                receipt = build_receipt(
                    capability_id=f"code_intelligence.{mode}",
                    capability_type="adapter",
                    risk_tier="T1",
                    status="OK" if result.get("ok") else "ERROR",
                    authorized=True,
                    network_access=False,
                    writes_external_state=False,
                    summary=f"Executed read-only {mode} analysis.",
                )
                result["capability_receipt"] = compact_receipt(receipt)
                return result
            if tool_name == "mcp_integration_invoke":
                from .integrations.policy import classify_integration_request
                from .integrations.adapters import get_adapter, IntegrationError
                from .capabilities.receipt import build_receipt, compact_receipt
                integration_type = str(args.get("integration_type", ""))
                action = str(args.get("action", ""))
                params = args.get("params") or {}
                if not isinstance(params, dict):
                    raise AdapterFailure("params must be an object")
                dry_run = bool(args.get("dry_run", True))
                decision = classify_integration_request(
                    integration_type=integration_type,
                    action=action,
                    dry_run=dry_run,
                    profile="safe",
                )
                if not decision.allowed:
                    receipt = build_receipt(
                        capability_id=f"integration.{integration_type}",
                        capability_type="integration",
                        risk_tier=decision.risk_tier if decision.risk_tier in {"T1","T2","T3","T4"} else "T4",
                        status="POLICY_BLOCK",
                        authorized=False,
                        network_access=True,
                        writes_external_state=not dry_run,
                        summary=decision.reason[:200],
                    )
                    return {
                        "ok": False,
                        "status": "POLICY_BLOCK",
                        "summary": decision.reason,
                        "artifacts": {},
                        "integration_receipt": compact_receipt(receipt),
                        "error": {"code": "integration_policy_block", "message": decision.reason},
                    }
                try:
                    adapter = get_adapter(integration_type)
                    result = adapter.invoke(action, params, dry_run=dry_run)
                except IntegrationError as exc:
                    raise AdapterFailure(str(exc)) from exc
                receipt = build_receipt(
                    capability_id=f"integration.{integration_type}",
                    capability_type="integration",
                    risk_tier=decision.risk_tier,
                    status="OK",
                    authorized=True,
                    network_access=False,
                    writes_external_state=False,
                    summary=f"Dry-run {integration_type}.{action} completed; no external call made.",
                )
                result["integration_receipt"] = compact_receipt(receipt)
                return result
            if tool_name == "mcp_deep_research":
                from .research.deep_research_adapter import invoke_deep_research
                query = str(args.get("query", ""))
                if not query:
                    raise AdapterFailure("query is required")
                source_mode = str(args.get("source_mode", "static"))
                target_repo = str(args.get("target_repo", ""))
                max_sources = int(args.get("max_sources", 12))
                max_depth = int(args.get("max_depth", 1))
                sources_raw = args.get("sources")
                if sources_raw is not None and not isinstance(sources_raw, list):
                    raise AdapterFailure("sources must be an array")
                return invoke_deep_research(
                    query=query,
                    source_mode=source_mode,
                    sources_raw=list(sources_raw) if sources_raw else None,
                    target_repo=target_repo,
                    max_sources=max_sources,
                    max_depth=max_depth,
                )
            if tool_name == "mcp_sandbox_probe":
                from .sandbox.policy import classify_sandbox_request
                from .capabilities.receipt import build_receipt, compact_receipt
                operation = str(args.get("operation", ""))
                path = str(args.get("path", ""))
                sandbox_decision = classify_sandbox_request(
                    "mcp_sandbox_probe", args, profile="safe"
                )
                if not sandbox_decision.allowed:
                    receipt = build_receipt(
                        capability_id="sandbox.local_readonly_probe",
                        capability_type="sandbox",
                        risk_tier=sandbox_decision.risk_tier,
                        status="POLICY_BLOCK",
                        authorized=False,
                        network_access=False,
                        writes_external_state=False,
                        summary=sandbox_decision.reason[:200],
                    )
                    return {
                        "ok": False,
                        "status": "POLICY_BLOCK",
                        "summary": sandbox_decision.reason,
                        "artifacts": {},
                        "error": {"code": "sandbox_policy_block", "message": sandbox_decision.reason},
                        "capability_receipt": compact_receipt(receipt),
                    }
                if self.sandbox is None:
                    raise AdapterFailure("sandbox adapter is not configured")
                if operation == "stat":
                    result = self.sandbox.stat(path)
                elif operation == "list_dir":
                    result = self.sandbox.list_dir(path, int(args.get("max_entries", 200)))
                elif operation == "read_head":
                    result = self.sandbox.read_head(path, int(args.get("max_bytes", 4096)))
                else:
                    raise AdapterFailure(f"unknown sandbox operation: {operation!r}")
                probe_status = "OK" if result.get("ok", True) else "ERROR"
                receipt = build_receipt(
                    capability_id="sandbox.local_readonly_probe",
                    capability_type="sandbox",
                    risk_tier="T1",
                    status=probe_status,
                    authorized=True,
                    network_access=False,
                    writes_external_state=False,
                    summary=f"Executed read-only sandbox probe: {operation}.",
                )
                result["capability_receipt"] = compact_receipt(receipt)
                return result
            raise AdapterFailure(f"unknown MCP tool: {tool_name}")
        except KeyError as exc:
            raise AdapterFailure(f"missing required argument: {exc}") from exc
        except ValueError as exc:
            if isinstance(exc, AdapterFailure):
                raise
            raise AdapterFailure(str(exc)) from exc
