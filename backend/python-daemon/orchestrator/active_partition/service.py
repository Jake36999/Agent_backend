from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mapper import PartitionMapper
from .models import ActivePartition, MemoryProject
from .repo import ActivePartitionRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActivePartitionServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class ActivePartitionService:
    def __init__(
        self,
        repo: ActivePartitionRepository,
        *,
        conversations_root: Path,
        client_id: str = "local-lmstudio",
        allowed_roots: tuple[Path, ...] | None = None,
    ) -> None:
        self.repo = repo
        self.mapper = PartitionMapper(conversations_root)
        self.client_id = client_id
        self.allowed_roots = tuple(root.resolve() for root in (allowed_roots or (conversations_root,)))

    def set_active_from_conversation_path(self, conversation_json_path: str, source_event: str = "manual_override") -> ActivePartition:
        mapping = self.mapper.map(conversation_json_path)
        if not mapping.ok:
            raise ActivePartitionServiceError(
                mapping.status,
                mapping.message,
                details=mapping.to_dict(),
            )
        project = MemoryProject(
            project_id=mapping.project_id,
            project_scope_hash=mapping.project_scope_hash,
            source="lmstudio_folder",
            display_name=mapping.folder_relpath.replace("/", " / "),
            lmstudio_folder_relpath=mapping.folder_relpath,
            allowed_roots_json=[str(root) for root in self.allowed_roots],
            rag_enabled=True,
            created_at=_now(),
            last_seen_at=_now(),
        )
        self.repo.upsert_memory_project(project)
        partition = ActivePartition(
            client_id=self.client_id,
            active_project_id=project.project_id,
            active_project_scope_hash=project.project_scope_hash,
            active_conversation_id=mapping.conversation_id,
            conversation_path=mapping.conversation_path,
            confidence="high",
            source_event=source_event,
            updated_at=_now(),
        )
        self.repo.set_active_partition(partition)
        self.repo.record_conversation_event(
            project_scope_hash=project.project_scope_hash,
            session_id=mapping.conversation_id,
            role="system",
            content_json={
                "event": "active_partition_mapped",
                "conversation_path": mapping.conversation_path,
                "folder_relpath": mapping.folder_relpath,
                "project_id": project.project_id,
            },
        )
        return partition

    def set_active_project(self, project_id: str, display_name: str | None = None) -> ActivePartition:
        normalized_display_name = display_name or project_id
        stable_scope_hash = self._project_scope_hash(project_id)
        project = MemoryProject(
            project_id=project_id,
            project_scope_hash=stable_scope_hash,
            source="manual_override",
            display_name=normalized_display_name,
            lmstudio_folder_relpath=None,
            allowed_roots_json=[str(root) for root in self.allowed_roots],
            rag_enabled=True,
            created_at=_now(),
            last_seen_at=_now(),
        )
        self.repo.upsert_memory_project(project)
        partition = ActivePartition(
            client_id=self.client_id,
            active_project_id=project_id,
            active_project_scope_hash=stable_scope_hash,
            active_conversation_id=None,
            conversation_path=None,
            confidence="high",
            source_event="manual_override",
            updated_at=_now(),
        )
        self.repo.set_active_partition(partition)
        self.repo.record_conversation_event(
            project_scope_hash=stable_scope_hash,
            session_id=project_id,
            role="system",
            content_json={
                "event": "manual_active_project_override",
                "project_id": project_id,
                "display_name": normalized_display_name,
            },
        )
        return partition

    def get_active_partition(self) -> ActivePartition | None:
        return self.repo.get_active_partition(self.client_id)

    def list_memory_projects(self) -> list[MemoryProject]:
        return self.repo.list_memory_projects()

    def _project_scope_hash(self, project_id: str) -> str:
        import hashlib
        import json

        return hashlib.sha1(
            json.dumps({"project_id": project_id}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
