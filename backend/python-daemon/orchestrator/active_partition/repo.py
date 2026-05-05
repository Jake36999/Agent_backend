from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ActivePartition, MemoryProject


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class ActivePartitionRepository:
    def __init__(self, queue_db: Path) -> None:
        self.queue_db = Path(queue_db)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def upsert_memory_project(self, project: MemoryProject) -> None:
        with closing(self._conn()) as conn:
            conn.execute(
                """
                INSERT INTO memory_projects (
                  project_id, project_scope_hash, source, display_name, lmstudio_folder_relpath,
                  allowed_roots_json, rag_enabled, created_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_scope_hash) DO UPDATE SET
                  project_id = excluded.project_id,
                  source = excluded.source,
                  display_name = excluded.display_name,
                  lmstudio_folder_relpath = excluded.lmstudio_folder_relpath,
                  allowed_roots_json = excluded.allowed_roots_json,
                  rag_enabled = excluded.rag_enabled,
                  last_seen_at = excluded.last_seen_at
                """,
                (
                    project.project_id,
                    project.project_scope_hash,
                    project.source,
                    project.display_name,
                    project.lmstudio_folder_relpath,
                    json.dumps(project.allowed_roots_json, sort_keys=True),
                    1 if project.rag_enabled else 0,
                    project.created_at or _now(),
                    project.last_seen_at or _now(),
                ),
            )
            conn.commit()

    def list_memory_projects(self) -> list[MemoryProject]:
        with closing(self._conn()) as conn:
            rows = conn.execute(
                "SELECT * FROM memory_projects ORDER BY last_seen_at DESC, created_at DESC, project_id ASC"
            ).fetchall()
        return [self._row_to_memory_project(row) for row in rows if row is not None]

    def set_active_partition(self, partition: ActivePartition) -> None:
        with closing(self._conn()) as conn:
            conn.execute(
                """
                INSERT INTO active_partitions (
                  client_id, active_project_id, active_project_scope_hash, active_conversation_id,
                  conversation_path, confidence, source_event, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                  active_project_id = excluded.active_project_id,
                  active_project_scope_hash = excluded.active_project_scope_hash,
                  active_conversation_id = excluded.active_conversation_id,
                  conversation_path = excluded.conversation_path,
                  confidence = excluded.confidence,
                  source_event = excluded.source_event,
                  updated_at = excluded.updated_at
                """,
                (
                    partition.client_id,
                    partition.active_project_id,
                    partition.active_project_scope_hash,
                    partition.active_conversation_id,
                    partition.conversation_path,
                    partition.confidence,
                    partition.source_event,
                    partition.updated_at,
                ),
            )
            conn.commit()

    def get_active_partition(self, client_id: str = "local-lmstudio") -> ActivePartition | None:
        with closing(self._conn()) as conn:
            row = conn.execute("SELECT * FROM active_partitions WHERE client_id = ?", (client_id,)).fetchone()
        result = _dict(row)
        if result is None:
            return None
        return ActivePartition(
            client_id=str(result["client_id"]),
            active_project_id=result.get("active_project_id"),
            active_project_scope_hash=result.get("active_project_scope_hash"),
            active_conversation_id=result.get("active_conversation_id"),
            conversation_path=result.get("conversation_path"),
            confidence=str(result["confidence"]),
            source_event=str(result["source_event"]),
            updated_at=str(result["updated_at"]),
        )

    def clear_active_partition(self, client_id: str = "local-lmstudio") -> None:
        with closing(self._conn()) as conn:
            conn.execute("DELETE FROM active_partitions WHERE client_id = ?", (client_id,))
            conn.commit()

    def record_conversation_event(
        self,
        project_scope_hash: str,
        session_id: str,
        role: str,
        content_json: dict[str, Any],
        token_count: int = 0,
        timestamp: str | None = None,
    ) -> None:
        with closing(self._conn()) as conn:
            conn.execute(
                """
                INSERT INTO conversation_events (
                  event_id, project_scope_hash, session_id, role, content_json, token_count, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    project_scope_hash,
                    session_id,
                    role,
                    json.dumps(content_json, sort_keys=True),
                    int(token_count),
                    timestamp or _now(),
                ),
            )
            conn.commit()

    def _row_to_memory_project(self, row: sqlite3.Row) -> MemoryProject:
        allowed_roots = json.loads(row["allowed_roots_json"]) if row["allowed_roots_json"] else []
        return MemoryProject(
            project_id=str(row["project_id"]),
            project_scope_hash=str(row["project_scope_hash"]),
            source=str(row["source"]),
            display_name=str(row["display_name"]),
            lmstudio_folder_relpath=row["lmstudio_folder_relpath"],
            allowed_roots_json=[str(value) for value in allowed_roots],
            rag_enabled=bool(row["rag_enabled"]),
            created_at=str(row["created_at"]),
            last_seen_at=str(row["last_seen_at"]),
        )
