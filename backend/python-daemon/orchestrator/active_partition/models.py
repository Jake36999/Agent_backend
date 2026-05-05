from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryProject:
    project_id: str
    project_scope_hash: str
    source: str
    display_name: str
    lmstudio_folder_relpath: str | None
    allowed_roots_json: list[str] = field(default_factory=list)
    rag_enabled: bool = True
    created_at: str = ""
    last_seen_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_scope_hash": self.project_scope_hash,
            "source": self.source,
            "display_name": self.display_name,
            "lmstudio_folder_relpath": self.lmstudio_folder_relpath,
            "allowed_roots_json": list(self.allowed_roots_json),
            "rag_enabled": self.rag_enabled,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
        }


@dataclass(frozen=True)
class ActivePartition:
    client_id: str
    active_project_id: str | None
    active_project_scope_hash: str | None
    active_conversation_id: str | None
    conversation_path: str | None
    confidence: str
    source_event: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "active_project_id": self.active_project_id,
            "active_project_scope_hash": self.active_project_scope_hash,
            "active_conversation_id": self.active_conversation_id,
            "conversation_path": self.conversation_path,
            "confidence": self.confidence,
            "source_event": self.source_event,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class PartitionMappingResult:
    ok: bool
    status: str
    message: str
    conversation_id: str
    folder_relpath: str
    project_id: str
    project_scope_hash: str
    conversation_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "conversation_id": self.conversation_id,
            "folder_relpath": self.folder_relpath,
            "project_id": self.project_id,
            "project_scope_hash": self.project_scope_hash,
            "conversation_path": self.conversation_path,
        }


@dataclass(frozen=True)
class NullPartitionResult:
    ok: bool = False
    status: str = "NO_ACTIVE_PARTITION"
    message: str = "No active partition available."
    conversation_id: str | None = None
    folder_relpath: str | None = None
    conversation_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "conversation_id": self.conversation_id,
            "folder_relpath": self.folder_relpath,
            "conversation_path": self.conversation_path,
        }

