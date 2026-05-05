from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_MEMORY_TYPES = {
    "architecture",
    "decision",
    "summary",
    "bug_fix",
    "preference",
    "artifact",
}


@dataclass(frozen=True)
class MemoryCommitRequest:
    category: str
    content: str
    confidence_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    project_id: str
    project_scope_hash: str
    memory_type: str
    source: str
    content: str
    content_sha1: str
    metadata_json: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    created_at: str = ""
    index_status: str = "pending"
    indexed_at: str | None = None
    index_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "project_id": self.project_id,
            "project_scope_hash": self.project_scope_hash,
            "memory_type": self.memory_type,
            "source": self.source,
            "content": self.content,
            "content_sha1": self.content_sha1,
            "metadata_json": dict(self.metadata_json),
            "confidence_score": self.confidence_score,
            "created_at": self.created_at,
            "index_status": self.index_status,
            "indexed_at": self.indexed_at,
            "index_error": self.index_error,
        }


@dataclass(frozen=True)
class MemorySearchResult:
    memory_id: str
    project_id: str
    project_scope_hash: str
    memory_type: str
    source: str
    content: str
    content_sha1: str
    metadata_json: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    created_at: str = ""
    distance: float | None = None
