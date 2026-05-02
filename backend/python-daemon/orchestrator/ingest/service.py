from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

from ..chroma_manager import ChromaAdapterError, ChromaManager
from ..queue_repo import QueueRepository
from .processors import (
    DocumentChunk,
    IngestProcessorError,
    MetadataAdapter,
    PdfProcessorAdapter,
    SemanticSlicerAdapter,
    TextProcessorAdapter,
)


class IngestTargetService:
    python_exts = {".py"}
    ignored_directory_names = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".cache",
        "output",
        "runs",
        "failed_workspaces",
        "unsloth_compiled_cache",
        ".venv_semantic",
        ".venv_training",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
    }
    ignored_file_suffixes = {
        ".db",
        ".sqlite",
        ".sqlite3",
        ".h5",
        ".hdf5",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".parquet",
    }
    ignored_file_patterns = (
        "*_bundle*.py",
        "*_bundle*.yaml",
        "*_Extraction.*",
        "agnostic_bundle*",
        "Data_Processing_Efficiency_Audit*",
        "DAG_Math_Logic_Extraction*",
    )

    def __init__(
        self,
        repo: QueueRepository,
        chroma: ChromaManager,
        *,
        allowed_roots: tuple[Path, ...],
        metadata: MetadataAdapter | None = None,
        text_processor: TextProcessorAdapter | None = None,
        pdf_processor: PdfProcessorAdapter | None = None,
        semantic_slicer: SemanticSlicerAdapter | None = None,
    ) -> None:
        self.repo = repo
        self.chroma = chroma
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
        self.metadata = metadata or MetadataAdapter()
        self.text_processor = text_processor or TextProcessorAdapter()
        self.pdf_processor = pdf_processor or PdfProcessorAdapter()
        self.semantic_slicer = semantic_slicer or SemanticSlicerAdapter()

    def ingest_target(
        self,
        project_id: str,
        absolute_path: str,
        *,
        mime_type: str | None = None,
        force_reindex: bool = False,
    ) -> dict[str, Any]:
        path = self._resolve(absolute_path)
        files = self._target_files(path)
        scope_hash = self.chroma.project_scope_hash(project_id)
        run_id = hashlib.sha1(f"{project_id}|{path}|{scope_hash}".encode("utf-8")).hexdigest()
        self.repo.start_ingestion_run(run_id, project_id, scope_hash, str(path))
        indexed = 0
        skipped = 0
        removed = 0
        try:
            current_paths = {str(file_path.resolve()) for file_path in files}
            if path.is_dir():
                stale_paths = self.repo.file_paths_for_scope(scope_hash) - current_paths
                for stale_path in sorted(stale_paths):
                    self.repo.delete_file_manifest(scope_hash, stale_path)
                    self.chroma.delete_chunks(project_id=project_id, absolute_path=stale_path)
                    removed += 1
            for file_path in files:
                file_metadata = self.metadata.extract(file_path)
                resolved_path = str(file_path.resolve())
                previous = self.repo.file_manifest(scope_hash, resolved_path)
                unchanged = previous is not None and previous["file_sha256"] == file_metadata["file_sha256"]
                if unchanged and not force_reindex:
                    skipped += 1
                    continue
                if force_reindex or previous is not None:
                    self.repo.delete_chunks_for_path(scope_hash, resolved_path)
                    self.chroma.delete_chunks(project_id=project_id, absolute_path=resolved_path)
                chunks = self._process_file(file_path, mime_type)
                if not chunks:
                    continue
                chunk_payloads = []
                for chunk in chunks:
                    metadata = {**file_metadata, **chunk.metadata}
                    metadata["project_id"] = project_id
                    metadata["project_scope_hash"] = scope_hash
                    metadata["absolute_path"] = str(file_path.resolve())
                    chunk_id = self._chunk_id(scope_hash, metadata, chunk.content)
                    chunk_payloads.append({"chunk_id": chunk_id, "content": chunk.content, "metadata": metadata})
                self.repo.record_file_manifest(project_id, scope_hash, file_metadata)
                self.repo.record_chunks(project_id, scope_hash, run_id, chunk_payloads)
                try:
                    self.chroma.upsert_chunks(project_id=project_id, chunks=chunk_payloads)
                except ChromaAdapterError as exc:
                    self.repo.finish_ingestion_run(run_id, "FAILED_VECTOR_UPSERT", str(exc))
                    raise
                indexed += len(chunk_payloads)
            self.repo.finish_ingestion_run(run_id, "COMPLETED", None)
        except Exception as exc:
            try:
                if self.repo.latest_ingestion_run(project_id)["state"] != "FAILED_VECTOR_UPSERT":
                    self.repo.finish_ingestion_run(run_id, "FAILED", str(exc))
            except KeyError:
                self.repo.finish_ingestion_run(run_id, "FAILED", str(exc))
            raise
        return {
            "project_id": project_id,
            "project_scope_hash": scope_hash,
            "absolute_path": str(path),
            "chunks_indexed": indexed,
            "files_skipped": skipped,
            "files_removed": removed,
            "run_id": run_id,
        }

    def search(self, project_id: str, query: str, k: int) -> list[dict[str, object]]:
        return self.chroma.search(project_id, query, k)

    def rebuild_chroma_for_project(self, project_id: str) -> dict[str, Any]:
        chunks = self.repo.list_rebuildable_chunks(project_id)
        if not chunks:
            chunks = self.repo.chunks_for_rebuild(project_id)
        result = self.chroma.rebuild_from_chunks(project_id, chunks)
        self.repo.mark_rebuildable_runs_reconciled(project_id)
        return result

    def _resolve(self, target: str) -> Path:
        resolved = Path(target).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise ValueError("path escapes allowed roots")
        if not resolved.exists():
            raise ValueError(f"target does not exist: {target}")
        return resolved

    def _ignored_file(self, path: Path) -> bool:
        lower_name = path.name.lower()
        normalized = path.as_posix()
        return (
            path.suffix.lower() in self.ignored_file_suffixes
            or any(
                fnmatch.fnmatch(path.name, pattern)
                or fnmatch.fnmatch(normalized, pattern)
                for pattern in self.ignored_file_patterns
            )
            or lower_name.endswith(".jsonl")
        )

    def _ignored_path_parts(self, path: Path) -> bool:
        return any(
            part in self.ignored_directory_names
            or fnmatch.fnmatch(part, "*_bundle_*")
            or fnmatch.fnmatch(part, "*_bundle*")
            for part in path.parts
        )

    def _target_files(self, target: Path) -> list[Path]:
        if target.is_file():
            return [target]
        return sorted(
            path
            for path in target.rglob("*")
            if path.is_file()
            and not self._ignored_path_parts(path)
            and not self._ignored_file(path)
        )

    def _process_file(self, path: Path, mime_type: str | None) -> list[DocumentChunk]:
        if path.suffix.lower() == ".pdf" or mime_type == "application/pdf":
            return self.pdf_processor.process_file(path)
        if path.suffix.lower() in self.python_exts:
            try:
                chunks = self.semantic_slicer.process_file(path)
                if chunks:
                    return chunks
            except IngestProcessorError:
                return self.text_processor.process_file(path)
        return self.text_processor.process_file(path)

    def _chunk_id(self, scope_hash: str, metadata: dict[str, Any], content: str) -> str:
        material = {
            "scope": scope_hash,
            "path": metadata.get("absolute_path"),
            "chunk_index": metadata.get("chunk_index"),
            "processor": metadata.get("processor"),
            "content_sha1": hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest(),
        }
        return hashlib.sha1(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
