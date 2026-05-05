from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..active_partition.repo import ActivePartitionRepository
from ..chroma_manager import ChromaAdapterError, ChromaManager
from .models import ALLOWED_MEMORY_TYPES, MemoryRecord
from .repo import MemoryRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryService:
    def __init__(
        self,
        repo: MemoryRepository,
        active_repo: ActivePartitionRepository,
        chroma: ChromaManager,
        *,
        client_id: str = "local-lmstudio",
    ) -> None:
        self.repo = repo
        self.active_repo = active_repo
        self.chroma = chroma
        self.client_id = client_id

    def commit_memory(
        self,
        category: str,
        content: str,
        confidence_score: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if category not in ALLOWED_MEMORY_TYPES:
            return self._error("invalid_category", f"Unsupported memory category: {category}", status="POLICY_BLOCK")
        bounded_content = content[:8000]
        if len(bounded_content.strip()) < 10:
            return self._error("content_too_short", "Memory content must be at least 10 characters.", status="POLICY_BLOCK")
        active = self.active_repo.get_active_partition(self.client_id)
        if active is None or not active.active_project_id or not active.active_project_scope_hash:
            return self._error(
                "no_active_partition",
                "No active partition is available. Set an LM Studio folder first.",
                status="NO_ACTIVE_PARTITION",
            )
        memory_id = str(uuid.uuid4())
        content_sha1 = hashlib.sha1(bounded_content.encode("utf-8")).hexdigest()
        record = MemoryRecord(
            memory_id=memory_id,
            project_id=active.active_project_id,
            project_scope_hash=active.active_project_scope_hash,
            memory_type=category,
            source="memory_record",
            content=bounded_content,
            content_sha1=content_sha1,
            metadata_json=dict(metadata or {}),
            confidence_score=float(confidence_score),
            created_at=_now(),
            index_status="pending",
        )
        self.repo.insert_memory_record(record)
        chroma_metadata = {
            **dict(metadata or {}),
            "project_id": active.active_project_id,
            "project_scope_hash": active.active_project_scope_hash,
            "memory_id": memory_id,
            "memory_type": category,
            "source": "memory_record",
            "confidence_score": float(confidence_score),
        }
        try:
            chroma_result = self.chroma.upsert_chunks(
                project_id=active.active_project_id,
                project_scope_hash=active.active_project_scope_hash,
                chunks=[
                    {
                        "chunk_id": memory_id,
                        "content": bounded_content,
                        "metadata": chroma_metadata,
                    }
                ],
            )
            self.repo.update_memory_index_state(
                memory_id,
                "indexed",
                indexed_at=_now(),
                index_error=None,
            )
        except Exception as exc:
            index_error = str(exc)[:2000]
            self.repo.update_memory_index_state(
                memory_id,
                "failed",
                indexed_at=None,
                index_error=index_error,
            )
            failure = self._error("chroma_index_failed", f"Memory indexed in SQLite but Chroma indexing failed: {exc}")
            failure["memory_id"] = memory_id
            failure["index_status"] = "failed"
            return failure
        return {
            "ok": True,
            "status": "COMMITTED",
            "summary": "Memory committed to the active partition.",
            "memory_id": memory_id,
            "project_id": active.active_project_id,
            "project_scope_hash": active.active_project_scope_hash,
            "index_status": "indexed",
            "artifacts": {"memory_id": memory_id},
            "chroma": chroma_result,
        }

    def rebuild_memory_index_for_project(self, project_scope_hash: str, limit: int = 200) -> dict[str, Any]:
        records = self.repo.list_memory_records_for_reindex(project_scope_hash, limit)
        indexed = 0
        failed = 0
        for record in records:
            metadata = {
                **dict(record.metadata_json),
                "project_id": record.project_id,
                "project_scope_hash": record.project_scope_hash,
                "memory_id": record.memory_id,
                "memory_type": record.memory_type,
                "source": "memory_record",
                "confidence_score": float(record.confidence_score),
            }
            try:
                self.chroma.upsert_chunks(
                    project_id=record.project_id,
                    project_scope_hash=record.project_scope_hash,
                    chunks=[
                        {
                            "chunk_id": record.memory_id,
                            "content": record.content,
                            "metadata": metadata,
                        }
                    ],
                )
                self.repo.update_memory_index_state(record.memory_id, "indexed", indexed_at=_now(), index_error=None)
                indexed += 1
            except Exception as exc:
                self.repo.update_memory_index_state(
                    record.memory_id,
                    "failed",
                    indexed_at=None,
                    index_error=str(exc)[:2000],
                )
                failed += 1
        return {
            "ok": failed == 0,
            "status": "COMPLETE" if failed == 0 else "WARN",
            "summary": f"Reindexed {indexed} memory records; {failed} failed.",
            "indexed": indexed,
            "failed": failed,
            "project_scope_hash": project_scope_hash,
        }

    def semantic_search_active(self, query: str, k: int = 8) -> dict[str, Any]:
        if not query.strip():
            return self._error("invalid_query", "Query must not be empty.", status="POLICY_BLOCK")
        if k < 1 or k > 50:
            return self._error("invalid_k", "k must be between 1 and 50.", status="POLICY_BLOCK")
        active = self.active_repo.get_active_partition(self.client_id)
        if active is None or not active.active_project_id or not active.active_project_scope_hash:
            return self._error(
                "no_active_partition",
                "No active partition is available. Set an LM Studio folder first.",
                status="NO_ACTIVE_PARTITION",
            )
        try:
            results = self.chroma.search(
                active.active_project_id,
                query,
                k,
                project_scope_hash=active.active_project_scope_hash,
            )
        except ChromaAdapterError as exc:
            return self._error("chroma_search_failed", f"Active memory search failed: {exc}")
        return {
            "ok": True,
            "status": "OK",
            "summary": f"Found {len(results)} active memory results.",
            "results": results,
            "artifacts": {},
            "active_partition": active.to_dict(),
        }

    def _error(self, code: str, summary: str, *, status: str = "ERROR") -> dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "summary": summary,
            "artifacts": {},
            "error": {"code": code, "message": summary},
        }
