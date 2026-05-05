from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
import json
from typing import Any

from .models import ApprovalRecord, FileSnapshot, PatchApplyRun, PatchArtifact


class PatchArtifactRepository:
    def __init__(self, queue_db_path: Path) -> None:
        self.queue_db_path = Path(queue_db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db_path)
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def insert(self, artifact: PatchArtifact) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO patch_artifacts (
                  patch_id, run_id, project_id, project_scope_hash, selected_skill_id,
                  target_repo, status, patch_path, diff_sha256, affected_paths_json,
                  created_at, validation_status, validation_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                artifact.to_record_tuple(),
            )
            conn.commit()

    def get(self, patch_id: str) -> PatchArtifact | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM patch_artifacts WHERE patch_id = ?", (patch_id,)).fetchone()
        if row is None:
            return None
        return PatchArtifact(
            patch_id=row["patch_id"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            project_scope_hash=row["project_scope_hash"],
            selected_skill_id=row["selected_skill_id"],
            target_repo=row["target_repo"],
            status=row["status"],
            patch_path=row["patch_path"],
            diff_sha256=row["diff_sha256"],
            affected_paths_json=json.loads(row["affected_paths_json"]),
            created_at=row["created_at"],
            validation_status=row["validation_status"],
            validation_error=row["validation_error"],
        )

    def insert_approval_record(self, record: dict[str, Any] | ApprovalRecord) -> None:
        if isinstance(record, ApprovalRecord):
            payload = {
                "approval_id": record.approval_id,
                "patch_id": record.patch_id,
                "run_id": record.run_id,
                "project_id": record.project_id,
                "project_scope_hash": record.project_scope_hash,
                "target_repo": record.target_repo,
                "approved": record.approved,
                "approved_by": record.approved_by,
                "approved_at": record.approved_at,
                "approval_scope": record.approval_scope,
                "approved_diff_sha256": record.approved_diff_sha256,
                "declared_tests_json": record.declared_tests_json,
                "created_at": record.created_at,
                "notes": record.notes,
            }
        else:
            payload = dict(record)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO approval_records (
                  approval_id, patch_id, run_id, project_id, project_scope_hash, target_repo,
                  approved, approved_by, approved_at, approval_scope, approved_diff_sha256,
                  declared_tests_json, created_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["approval_id"],
                    payload["patch_id"],
                    payload.get("run_id"),
                    payload.get("project_id"),
                    payload.get("project_scope_hash"),
                    payload["target_repo"],
                    1 if payload.get("approved") is True else 0,
                    payload.get("approved_by"),
                    payload.get("approved_at"),
                    payload.get("approval_scope"),
                    payload["approved_diff_sha256"],
                    json.dumps(payload.get("declared_tests_json") or [], sort_keys=True),
                    payload["created_at"],
                    payload.get("notes"),
                ),
            )
            conn.commit()

    def get_approval_record(self, approval_id: str) -> ApprovalRecord | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM approval_records WHERE approval_id = ?", (approval_id,)).fetchone()
        if row is None:
            return None
        return ApprovalRecord(
            approval_id=row["approval_id"],
            patch_id=row["patch_id"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            project_scope_hash=row["project_scope_hash"],
            target_repo=row["target_repo"],
            approved=bool(row["approved"]),
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            approval_scope=row["approval_scope"],
            approved_diff_sha256=row["approved_diff_sha256"],
            declared_tests_json=json.loads(row["declared_tests_json"] or "[]"),
            created_at=row["created_at"],
            notes=row["notes"],
        )

    def insert_apply_run(self, run: PatchApplyRun) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO patch_apply_runs (
                  apply_run_id, patch_id, approval_id, run_id, project_id, project_scope_hash,
                  target_repo, status, applied_at, completed_at, rollback_available, tests_status, bounded_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.apply_run_id,
                    run.patch_id,
                    run.approval_id,
                    run.run_id,
                    run.project_id,
                    run.project_scope_hash,
                    run.target_repo,
                    run.status,
                    run.applied_at,
                    run.completed_at,
                    1 if run.rollback_available else 0,
                    run.tests_status,
                    run.bounded_error,
                ),
            )
            conn.commit()

    def update_apply_run(self, apply_run_id: str, *, status: str, completed_at: str | None = None, applied_at: str | None = None, rollback_available: bool | None = None, tests_status: str | None = None, bounded_error: str | None = None) -> None:
        assignments = ["status = ?"]
        values: list[Any] = [status]
        if completed_at is not None:
            assignments.append("completed_at = ?")
            values.append(completed_at)
        if applied_at is not None:
            assignments.append("applied_at = ?")
            values.append(applied_at)
        if rollback_available is not None:
            assignments.append("rollback_available = ?")
            values.append(1 if rollback_available else 0)
        if tests_status is not None:
            assignments.append("tests_status = ?")
            values.append(tests_status)
        if bounded_error is not None:
            assignments.append("bounded_error = ?")
            values.append(bounded_error[:500])
        values.append(apply_run_id)
        with closing(self._connect()) as conn:
            conn.execute(f"UPDATE patch_apply_runs SET {', '.join(assignments)} WHERE apply_run_id = ?", values)
            conn.commit()

    def get_apply_run(self, apply_run_id: str) -> PatchApplyRun | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM patch_apply_runs WHERE apply_run_id = ?", (apply_run_id,)).fetchone()
        if row is None:
            return None
        return PatchApplyRun(
            apply_run_id=row["apply_run_id"],
            patch_id=row["patch_id"],
            approval_id=row["approval_id"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            project_scope_hash=row["project_scope_hash"],
            target_repo=row["target_repo"],
            status=row["status"],
            applied_at=row["applied_at"],
            completed_at=row["completed_at"],
            rollback_available=bool(row["rollback_available"]),
            tests_status=row["tests_status"],
            bounded_error=row["bounded_error"],
        )

    def insert_file_snapshot(self, snapshot: FileSnapshot) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO file_snapshots (
                  snapshot_file_id, apply_run_id, patch_id, target_path, pre_apply_sha256,
                  pre_apply_size, backup_path, created_at, created_target
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_file_id,
                    snapshot.apply_run_id,
                    snapshot.patch_id,
                    snapshot.target_path,
                    snapshot.pre_apply_sha256,
                    snapshot.pre_apply_size,
                    snapshot.backup_path,
                    snapshot.created_at,
                    1 if snapshot.created_target else 0,
                ),
            )
            conn.commit()

    def list_file_snapshots(self, apply_run_id: str) -> list[FileSnapshot]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM file_snapshots WHERE apply_run_id = ? ORDER BY created_at ASC", (apply_run_id,)).fetchall()
        return [
            FileSnapshot(
                snapshot_file_id=row["snapshot_file_id"],
                apply_run_id=row["apply_run_id"],
                patch_id=row["patch_id"],
                target_path=row["target_path"],
                pre_apply_sha256=row["pre_apply_sha256"],
                pre_apply_size=row["pre_apply_size"],
                backup_path=row["backup_path"],
                created_at=row["created_at"],
                created_target=bool(row["created_target"]),
            )
            for row in rows
        ]
