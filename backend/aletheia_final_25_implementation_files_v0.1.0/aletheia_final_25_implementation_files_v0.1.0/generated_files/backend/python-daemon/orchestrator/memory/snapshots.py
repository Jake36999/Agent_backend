from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.active_partition.models import ActivePartition

_ALLOWED_ARTIFACT_KEYS = {
    "archive_yaml_path",
    "archive_yaml",
    "manifest_csv_path",
    "manifest_csv",
    "final_markdown_path",
    "final_markdown",
    "final_python_bundle_path",
    "final_python_bundle",
    "state_path",
}
_MAX_SUMMARY_CHARS = 2000
_MAX_JSON_CHARS = 8000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded(value: Any, max_chars: int) -> str:
    return str(value or "")[:max(1, int(max_chars))]


def _json_dumps_bounded(value: Any, max_chars: int = _MAX_JSON_CHARS) -> str:
    text = json.dumps(value, sort_keys=True, default=str)
    return text[:max_chars]


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}_{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class SnapshotRecord:
    snapshot_id: str
    project_id: str | None
    project_scope_hash: str | None
    run_id: str | None
    session_id: str | None
    source_tool: str
    archive_yaml_path: str | None
    manifest_csv_path: str | None
    final_markdown_path: str | None
    final_python_bundle_path: str | None
    state_path: str | None
    summary: str
    artifact_json: dict[str, object]
    selected_skill_json: dict[str, object] | None
    created_at: str
    index_status: str = "pending"
    indexed_at: str | None = None
    index_error: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SnapshotRecord":
        return cls(
            snapshot_id=row["snapshot_id"],
            project_id=row["project_id"],
            project_scope_hash=row["project_scope_hash"],
            run_id=row["run_id"],
            session_id=row["session_id"],
            source_tool=row["source_tool"],
            archive_yaml_path=row["archive_yaml_path"],
            manifest_csv_path=row["manifest_csv_path"],
            final_markdown_path=row["final_markdown_path"],
            final_python_bundle_path=row["final_python_bundle_path"],
            state_path=row["state_path"],
            summary=row["summary"],
            artifact_json=json.loads(row["artifact_json"] or "{}"),
            selected_skill_json=json.loads(row["selected_skill_json"]) if row["selected_skill_json"] else None,
            created_at=row["created_at"],
            index_status=row["index_status"],
            indexed_at=row["indexed_at"],
            index_error=row["index_error"],
        )


class SnapshotRepository:
    def __init__(self, queue_db_path: Path) -> None:
        self.queue_db_path = Path(queue_db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def insert(self, record: SnapshotRecord) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO snapshot_records (
                  snapshot_id, project_id, project_scope_hash, run_id, session_id, source_tool,
                  archive_yaml_path, manifest_csv_path, final_markdown_path, final_python_bundle_path,
                  state_path, summary, artifact_json, selected_skill_json, created_at,
                  index_status, indexed_at, index_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.snapshot_id,
                    record.project_id,
                    record.project_scope_hash,
                    record.run_id,
                    record.session_id,
                    record.source_tool,
                    record.archive_yaml_path,
                    record.manifest_csv_path,
                    record.final_markdown_path,
                    record.final_python_bundle_path,
                    record.state_path,
                    record.summary,
                    _json_dumps_bounded(record.artifact_json),
                    _json_dumps_bounded(record.selected_skill_json) if record.selected_skill_json else None,
                    record.created_at,
                    record.index_status,
                    record.indexed_at,
                    record.index_error,
                ),
            )
            conn.commit()

    def get(self, snapshot_id: str) -> SnapshotRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM snapshot_records WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        return SnapshotRecord.from_row(row) if row else None

    def update_index_status(self, snapshot_id: str, status: str, *, error: str | None = None) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                UPDATE snapshot_records
                SET index_status = ?, indexed_at = ?, index_error = ?
                WHERE snapshot_id = ?
                """,
                (status, _utc_now() if status == "indexed" else None, _bounded(error, 1000) if error else None, snapshot_id),
            )
            conn.commit()

    def list_for_reindex(self, project_scope_hash: str | None = None, limit: int = 200) -> list[SnapshotRecord]:
        limit = max(1, min(int(limit), 1000))
        with closing(self._connect()) as conn:
            if project_scope_hash:
                rows = conn.execute(
                    """
                    SELECT * FROM snapshot_records
                    WHERE project_scope_hash = ? AND index_status IN ('pending', 'failed')
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (project_scope_hash, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM snapshot_records
                    WHERE index_status IN ('pending', 'failed')
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [SnapshotRecord.from_row(row) for row in rows]


class SnapshotMemoryService:
    def __init__(self, queue_db_path: Path, chroma_manager: Any | None = None) -> None:
        self.repo = SnapshotRepository(queue_db_path)
        self.chroma_manager = chroma_manager

    def record_workflow_snapshot(
        self,
        *,
        workflow_result: dict[str, object],
        active_partition: ActivePartition | None,
        selected_skill: dict[str, object] | None,
    ) -> dict[str, object]:
        artifacts = self._extract_artifacts(workflow_result.get("artifacts"))
        project_id = active_partition.active_project_id if active_partition else None
        project_scope_hash = active_partition.active_project_scope_hash if active_partition else None
        summary = _bounded(workflow_result.get("summary"), _MAX_SUMMARY_CHARS)
        run_id = str(workflow_result.get("run_id") or "") or None
        session_id = str(workflow_result.get("session_id") or "") or None
        payload = {"run_id": run_id, "summary": summary, "artifacts": artifacts}
        snapshot_id = _stable_id("snapshot", payload)
        record = SnapshotRecord(
            snapshot_id=snapshot_id,
            project_id=project_id,
            project_scope_hash=project_scope_hash,
            run_id=run_id,
            session_id=session_id,
            source_tool="mcp_agent_workflow_run",
            archive_yaml_path=artifacts.get("archive_yaml_path") or artifacts.get("archive_yaml"),
            manifest_csv_path=artifacts.get("manifest_csv_path") or artifacts.get("manifest_csv"),
            final_markdown_path=artifacts.get("final_markdown_path") or artifacts.get("final_markdown"),
            final_python_bundle_path=artifacts.get("final_python_bundle_path") or artifacts.get("final_python_bundle"),
            state_path=artifacts.get("state_path"),
            summary=summary,
            artifact_json=dict(artifacts),
            selected_skill_json=selected_skill,
            created_at=_utc_now(),
        )
        self.repo.insert(record)
        index_result = self.index_snapshot_record(snapshot_id) if project_scope_hash else {"ok": True, "status": "SKIPPED_NO_ACTIVE_PROJECT"}
        return {"ok": True, "status": "RECORDED", "snapshot_id": snapshot_id, "index_result": index_result}

    def index_snapshot_record(self, snapshot_id: str) -> dict[str, object]:
        record = self.repo.get(snapshot_id)
        if record is None:
            return {"ok": False, "status": "NOT_FOUND", "snapshot_id": snapshot_id}
        if not record.project_scope_hash:
            return {"ok": True, "status": "SKIPPED_NO_SCOPE", "snapshot_id": snapshot_id}
        try:
            content = self._snapshot_index_text(record)
            metadata = {
                "source": "snapshot_record",
                "snapshot_id": record.snapshot_id,
                "run_id": record.run_id,
                "project_id": record.project_id,
                "project_scope_hash": record.project_scope_hash,
                "archive_yaml_path": record.archive_yaml_path,
                "manifest_csv_path": record.manifest_csv_path,
                "final_markdown_path": record.final_markdown_path,
                "final_python_bundle_path": record.final_python_bundle_path,
                "state_path": record.state_path,
            }
            self._upsert_chroma(record, content, metadata)
            self.repo.update_index_status(snapshot_id, "indexed")
            return {"ok": True, "status": "INDEXED", "snapshot_id": snapshot_id}
        except Exception as exc:
            self.repo.update_index_status(snapshot_id, "failed", error=str(exc))
            return {"ok": False, "status": "INDEX_FAILED", "snapshot_id": snapshot_id, "error": str(exc)[:1000]}

    def list_snapshots_for_reindex(self, project_scope_hash: str | None = None, limit: int = 200) -> list[SnapshotRecord]:
        return self.repo.list_for_reindex(project_scope_hash=project_scope_hash, limit=limit)

    def _extract_artifacts(self, raw: object) -> dict[str, str]:
        if not isinstance(raw, dict):
            return {}
        bounded: dict[str, str] = {}
        for key, value in raw.items():
            key_s = str(key)
            if key_s not in _ALLOWED_ARTIFACT_KEYS and not key_s.endswith("_path"):
                continue
            if value is None:
                continue
            value_s = str(value)
            if len(value_s) > 1000:
                continue
            bounded[key_s] = value_s
        return bounded

    def _snapshot_index_text(self, record: SnapshotRecord) -> str:
        artifacts = ", ".join(f"{k}={v}" for k, v in sorted(record.artifact_json.items()))
        return _bounded(f"Workflow snapshot: {record.summary}. Artifacts: {artifacts}", 4000)

    def _upsert_chroma(self, record: SnapshotRecord, content: str, metadata: dict[str, object]) -> None:
        if self.chroma_manager is None:
            return
        if hasattr(self.chroma_manager, "upsert_snapshot_text"):
            self.chroma_manager.upsert_snapshot_text(record.snapshot_id, content, metadata)
            return
        if hasattr(self.chroma_manager, "upsert_text"):
            self.chroma_manager.upsert_text(record.snapshot_id, content, metadata)
            return
        raise RuntimeError("configured Chroma manager does not expose a snapshot upsert method")
