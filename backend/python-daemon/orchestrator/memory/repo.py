from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .models import MemoryRecord


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class MemoryRepository:
    def __init__(self, queue_db: Path) -> None:
        self.queue_db = Path(queue_db)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def insert_memory_record(self, record: MemoryRecord) -> None:
        with closing(self._conn()) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_records (
                  memory_id, project_id, project_scope_hash, memory_type, source,
                  content, content_sha1, metadata_json, confidence_score, created_at,
                  index_status, indexed_at, index_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_id,
                    record.project_id,
                    record.project_scope_hash,
                    record.memory_type,
                    record.source,
                    record.content,
                    record.content_sha1,
                    json.dumps(record.metadata_json, sort_keys=True),
                    record.confidence_score,
                    record.created_at,
                    record.index_status,
                    record.indexed_at,
                    record.index_error,
                ),
            )
            conn.commit()

    def update_memory_index_state(
        self,
        memory_id: str,
        status: str,
        *,
        indexed_at: str | None = None,
        index_error: str | None = None,
    ) -> None:
        if status not in {"pending", "indexed", "failed"}:
            raise ValueError(f"invalid memory index status: {status}")
        with closing(self._conn()) as conn:
            conn.execute(
                """
                UPDATE memory_records
                SET index_status = ?, indexed_at = ?, index_error = ?
                WHERE memory_id = ?
                """,
                (status, indexed_at, index_error, memory_id),
            )
            conn.commit()

    def list_memory_records(self, project_scope_hash: str, limit: int = 50) -> list[MemoryRecord]:
        with closing(self._conn()) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM memory_records
                WHERE project_scope_hash = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_scope_hash, max(1, min(int(limit), 200))),
            ).fetchall()
        records: list[MemoryRecord] = []
        for row in rows:
            item = _dict(row)
            if item is None:
                continue
            records.append(
                MemoryRecord(
                    memory_id=str(item["memory_id"]),
                    project_id=str(item["project_id"]),
                    project_scope_hash=str(item["project_scope_hash"]),
                    memory_type=str(item["memory_type"]),
                    source=str(item["source"]),
                    content=str(item["content"]),
                    content_sha1=str(item["content_sha1"]),
                    metadata_json=json.loads(item["metadata_json"]) if item["metadata_json"] else {},
                    confidence_score=float(item["confidence_score"]),
                    created_at=str(item["created_at"]),
                    index_status=str(item.get("index_status", "pending")),
                    indexed_at=item.get("indexed_at"),
                    index_error=item.get("index_error"),
                )
            )
        return records

    def list_memory_records_for_reindex(self, project_scope_hash: str | None = None, limit: int = 200) -> list[MemoryRecord]:
        sql = """
            SELECT *
            FROM memory_records
            WHERE index_status IN ('pending', 'failed')
        """
        params: list[Any] = []
        if project_scope_hash:
            sql += " AND project_scope_hash = ?"
            params.append(project_scope_hash)
        sql += " ORDER BY created_at ASC LIMIT ?"
        params.append(max(1, min(int(limit), 500)))
        with closing(self._conn()) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        item = _dict(row)
        if item is None:
            raise ValueError("row is empty")
        return MemoryRecord(
            memory_id=str(item["memory_id"]),
            project_id=str(item["project_id"]),
            project_scope_hash=str(item["project_scope_hash"]),
            memory_type=str(item["memory_type"]),
            source=str(item["source"]),
            content=str(item["content"]),
            content_sha1=str(item["content_sha1"]),
            metadata_json=json.loads(item["metadata_json"]) if item["metadata_json"] else {},
            confidence_score=float(item["confidence_score"]),
            created_at=str(item["created_at"]),
            index_status=str(item.get("index_status", "pending")),
            indexed_at=item.get("indexed_at"),
            index_error=item.get("index_error"),
        )
