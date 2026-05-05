from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class SkillRegistry:
    def __init__(self, queue_db_path: Path) -> None:
        self.queue_db_path = Path(queue_db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def upsert_verified(self, manifest: dict[str, Any], source_path: Path) -> None:
        now = utc_now()
        manifest_for_storage = dict(manifest)
        manifest_for_storage["source_path"] = str(source_path)

        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO skill_manifests (
                  skill_id, version, project_scope_hash, manifest_json,
                  status, source_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 'verified', ?, ?, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                  version = excluded.version,
                  project_scope_hash = excluded.project_scope_hash,
                  manifest_json = excluded.manifest_json,
                  status = 'verified',
                  source_path = excluded.source_path,
                  updated_at = excluded.updated_at
                """,
                (
                    manifest["skill_id"],
                    manifest["version"],
                    None,
                    json.dumps(manifest_for_storage, sort_keys=True),
                    str(source_path),
                    now,
                    now,
                ),
            )
            conn.commit()

    def quarantine(self, skill_id: str, source_path: Path, reason: str, raw: dict[str, Any] | None = None) -> None:
        now = utc_now()
        payload = {
            "manifest": raw or {},
            "quarantine_reason": reason,
        }

        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO skill_manifests (
                  skill_id, version, project_scope_hash, manifest_json,
                  status, source_path, created_at, updated_at
                )
                VALUES (?, ?, NULL, ?, 'quarantined', ?, ?, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                  manifest_json = excluded.manifest_json,
                  status = 'quarantined',
                  source_path = excluded.source_path,
                  updated_at = excluded.updated_at
                """,
                (
                    skill_id,
                    (raw or {}).get("version", "0.0.0"),
                    json.dumps(payload, sort_keys=True),
                    str(source_path),
                    now,
                    now,
                ),
            )
            conn.commit()

    def list_verified(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT manifest_json
                FROM skill_manifests
                WHERE status = 'verified'
                ORDER BY skill_id ASC
                """
            ).fetchall()
        return [json.loads(row["manifest_json"]) for row in rows]

    def get_verified(self, skill_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT manifest_json
                FROM skill_manifests
                WHERE skill_id = ? AND status = 'verified'
                """,
                (skill_id,),
            ).fetchone()
        return json.loads(row["manifest_json"]) if row else None