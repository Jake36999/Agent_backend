from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CapabilityManifest, CapabilityType, VALID_STATUSES
from .schema import CapabilitySchemaError, validate_capability_manifest


class CapabilityRegistry:

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def upsert(self, manifest: CapabilityManifest) -> None:
        data = manifest.to_dict()
        errors = validate_capability_manifest(data)
        if errors:
            raise CapabilitySchemaError(f"invalid manifest: {'; '.join(errors)}")

        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as conn:
            conn.execute(
                """
                INSERT INTO capability_manifests (
                    capability_id, capability_type, version, risk_tier,
                    requires_approval, network_access, writes_external_state,
                    manifest_json, status, source_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(capability_id) DO UPDATE SET
                    capability_type = excluded.capability_type,
                    version = excluded.version,
                    risk_tier = excluded.risk_tier,
                    requires_approval = excluded.requires_approval,
                    network_access = excluded.network_access,
                    writes_external_state = excluded.writes_external_state,
                    manifest_json = excluded.manifest_json,
                    status = excluded.status,
                    source_path = excluded.source_path,
                    updated_at = excluded.updated_at
                """,
                (
                    manifest.capability_id,
                    manifest.capability_type.value,
                    manifest.version,
                    manifest.risk_tier,
                    int(manifest.requires_approval),
                    int(manifest.network_access),
                    int(manifest.writes_external_state),
                    json.dumps(data, sort_keys=True),
                    manifest.status,
                    manifest.source_path,
                    now,
                    now,
                ),
            )
            conn.commit()

    def _row_to_manifest(self, row: sqlite3.Row) -> CapabilityManifest:
        data = json.loads(row["manifest_json"])
        data["status"] = row["status"]
        return CapabilityManifest.from_dict(data)

    def get(self, capability_id: str) -> CapabilityManifest | None:
        with closing(self._conn()) as conn:
            row = conn.execute(
                "SELECT manifest_json, status FROM capability_manifests WHERE capability_id = ?",
                (capability_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_manifest(row)

    def list_all(self, *, capability_type: CapabilityType | None = None, status: str | None = None) -> list[CapabilityManifest]:
        clauses: list[str] = []
        params: list[Any] = []
        if capability_type is not None:
            clauses.append("capability_type = ?")
            params.append(capability_type.value)
        if status is not None:
            if status not in VALID_STATUSES:
                return []
            clauses.append("status = ?")
            params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with closing(self._conn()) as conn:
            rows = conn.execute(
                f"SELECT manifest_json, status FROM capability_manifests{where} ORDER BY capability_id",
                params,
            ).fetchall()
        return [self._row_to_manifest(r) for r in rows]

    def quarantine(self, capability_id: str, reason: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as conn:
            cur = conn.execute(
                "UPDATE capability_manifests SET status = 'quarantined', updated_at = ? WHERE capability_id = ?",
                (now, capability_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def disable(self, capability_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as conn:
            cur = conn.execute(
                "UPDATE capability_manifests SET status = 'disabled', updated_at = ? WHERE capability_id = ?",
                (now, capability_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def enable(self, capability_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as conn:
            cur = conn.execute(
                "UPDATE capability_manifests SET status = 'verified', updated_at = ? WHERE capability_id = ?",
                (now, capability_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete(self, capability_id: str) -> bool:
        with closing(self._conn()) as conn:
            cur = conn.execute(
                "DELETE FROM capability_manifests WHERE capability_id = ?",
                (capability_id,),
            )
            conn.commit()
            return cur.rowcount > 0
