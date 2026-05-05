from __future__ import annotations

from dataclasses import dataclass

from .adapters import FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters
from .active_partition.repo import ActivePartitionRepository
from .active_partition.service import ActivePartitionService
from .active_partition.watcher import ActivePartitionWatcher
from .bridge_server import BridgeSecurity
from .candidate_analysis.service import CandidateAnalysisService
from .chroma_manager import ChromaConfig, ChromaManager
from .config import RuntimeConfig
from .memory.conversation_summary import ConversationSummaryIngestor
from .memory.repo import MemoryRepository
from .memory.service import MemoryService
from .memory.snapshots import SnapshotMemoryService
from .patching.service import PatchGenerationService
from .patching.apply import PatchApplyService
from .tool_assist_adapter import ToolAssistAdapter
from .db_bootstrap import bootstrap_databases
from .execution_loop import ExecutionLoop
from .ingest.processors import WorkspaceScout
from .ingest.processors import PdfProcessorAdapter
from .ingest.service import IngestTargetService
from .ocr import CommandOCRProvider
from .queue_repo import QueueRepository
from .shell import ShellAdapter


@dataclass(frozen=True)
class RuntimeComponents:
    config: RuntimeConfig
    repo: QueueRepository
    chroma: ChromaManager
    ingest: IngestTargetService
    tool_adapters: ToolAdapters
    execution_loop: ExecutionLoop
    bridge_security: BridgeSecurity
    active_partition_watcher: ActivePartitionWatcher | None = None
    snapshot_memory: SnapshotMemoryService | None = None
    conversation_summary_ingestor: ConversationSummaryIngestor | None = None
    candidate_analysis: CandidateAnalysisService | None = None
    patch_generation: PatchGenerationService | None = None
    patch_apply: PatchApplyService | None = None

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "queue_db": str(self.config.state_dir / "queue.db"),
            "control_db": str(self.config.state_dir / "control.db"),
            "bridge_host": self.config.bridge_host,
            "bridge_port": self.config.bridge_port,
            "workers": self.repo.list_worker_status(),
            "allowed_roots": [str(root) for root in self.config.allowed_roots],
        }

    def reconcile_project(self, project_id: str) -> dict[str, object]:
        return self.ingest.rebuild_chroma_for_project(project_id)

    def dead_letters(self, limit: int = 50) -> list[dict[str, object]]:
        return self.repo.list_dead_letters(limit)

    def close(self) -> None:
        if self.active_partition_watcher is not None:
            self.active_partition_watcher.stop(timeout=5.0)
        system = getattr(getattr(self.chroma, "client", None), "_system", None)
        stop = getattr(system, "stop", None)
        if callable(stop):
            stop()


def build_runtime(config: RuntimeConfig) -> RuntimeComponents:
    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.chroma_path.mkdir(parents=True, exist_ok=True)
    for root in config.allowed_roots:
        root.mkdir(parents=True, exist_ok=True)
    bootstrap_databases(config.state_dir)
    repo = QueueRepository(config.state_dir / "queue.db", config.state_dir / "control.db")
    chroma = ChromaManager(
        ChromaConfig(
            chroma_path=config.chroma_path,
            lm_studio_base_url=config.lm_studio_base_url,
            lm_studio_api_base_url=config.lm_studio_api_base_url,
            lm_studio_api_token=config.lm_studio_api_token,
            embedding_model=config.embedding_model,
            auto_load_embedding_model=config.auto_load_embedding_model,
        )
    )
    active_partition_repo = ActivePartitionRepository(repo.queue_db)
    memory_repo = MemoryRepository(repo.queue_db)
    active_partition = ActivePartitionService(
        active_partition_repo,
        conversations_root=config.lmstudio_conversations_dir,
        allowed_roots=config.allowed_roots,
    )
    memory_service = MemoryService(memory_repo, active_partition_repo, chroma)
    snapshot_memory = SnapshotMemoryService(repo.queue_db, chroma)
    conversation_summary_ingestor = ConversationSummaryIngestor()
    candidate_analysis = CandidateAnalysisService()
    patch_generation = PatchGenerationService(repo.queue_db, config.state_dir / "patch_artifacts", allowed_roots=config.allowed_roots)
    patch_apply = PatchApplyService(
        repo.queue_db,
        config.state_dir / "rollback",
        allowed_roots=config.allowed_roots,
        memory_service=memory_service,
        conversation_summary_ingestor=conversation_summary_ingestor,
    )
    active_partition_watcher = None
    if config.enable_lmstudio_watcher:
        active_partition_watcher = ActivePartitionWatcher(
            active_partition,
            config.lmstudio_conversations_dir,
            settle_ms=config.active_partition_settle_ms,
        )
        active_partition_watcher.start()
    file_tools = FileToolAdapter(config.allowed_roots)
    sqlite_tools = ReadOnlySqliteAdapter(config.allowed_roots)
    scout = WorkspaceScout(config.allowed_roots)
    shell_adapter = ShellAdapter(config.allowed_roots)
    ocr_provider = CommandOCRProvider(shell_adapter=shell_adapter, command=config.ocr_command) if config.ocr_command else None
    pdf_processor = PdfProcessorAdapter(ocr_provider=ocr_provider)
    ingest = IngestTargetService(repo, chroma, allowed_roots=config.allowed_roots, pdf_processor=pdf_processor)
    tool_adapters = ToolAdapters(
        semantic_memory=ingest,
        file_tools=file_tools,
        sqlite_tools=sqlite_tools,
        workspace_scout=scout,
        ocr_provider=ocr_provider,
        tool_assist=ToolAssistAdapter(),
        active_partition=active_partition,
        memory_service=memory_service,
        snapshot_memory=snapshot_memory,
        conversation_summary_ingestor=conversation_summary_ingestor,
        candidate_analysis=candidate_analysis,
        patch_generation=patch_generation,
        patch_apply=patch_apply,
        allowed_roots=config.allowed_roots,
        skill_registry_root=config.skill_registry_root,
        queue_db_path=repo.queue_db,
    )
    return RuntimeComponents(
        config=config,
        repo=repo,
        chroma=chroma,
        ingest=ingest,
        tool_adapters=tool_adapters,
        execution_loop=ExecutionLoop(repo, tool_adapters=tool_adapters),
        bridge_security=BridgeSecurity(shared_secret=config.bridge_shared_secret, enable_admin_bridge=config.enable_admin_bridge),
        active_partition_watcher=active_partition_watcher,
        snapshot_memory=snapshot_memory,
        conversation_summary_ingestor=conversation_summary_ingestor,
        candidate_analysis=candidate_analysis,
        patch_generation=patch_generation,
        patch_apply=patch_apply,
    )
