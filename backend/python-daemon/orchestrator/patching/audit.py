from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .admin_service import PatchAdminService
from .repo import PatchArtifactRepository


class PatchAuditService:
    def __init__(self, queue_db_path: Path) -> None:
        self.queue_db_path = Path(queue_db_path)
        self.repo = PatchArtifactRepository(self.queue_db_path)
        self.admin = PatchAdminService(self.queue_db_path)

    def summary_for_patch(self, patch_id: str) -> dict[str, Any]:
        artifact = self.repo.get(patch_id)
        if artifact is None:
            return {"ok": False, "status": "PATCH_NOT_FOUND", "patch_id": patch_id}
        runs = self.repo.list_apply_runs_for_patch(patch_id)
        latest = runs[0] if runs else None
        return self._summary(artifact.patch_id, latest.apply_run_id if latest else None)

    def summary_for_apply_run(self, apply_run_id: str) -> dict[str, Any]:
        run = self.repo.get_apply_run(apply_run_id)
        if run is None:
            return {"ok": False, "status": "APPLY_RUN_NOT_FOUND", "apply_run_id": apply_run_id}
        return self._summary(run.patch_id, apply_run_id)

    def _summary(self, patch_id: str, apply_run_id: str | None) -> dict[str, Any]:
        artifact = self.repo.get(patch_id)
        if artifact is None:
            return {"ok": False, "status": "PATCH_NOT_FOUND", "patch_id": patch_id}
        patch = self.admin.show_patch_artifact(patch_id)
        apply = self.admin.show_patch_apply_run(apply_run_id) if apply_run_id else None
        approval = None
        snapshots = []
        if apply_run_id:
            run = self.repo.get_apply_run(apply_run_id)
            if run is not None:
                approval_record = self.repo.get_approval_record(run.approval_id)
                approval = self.admin._approval(approval_record) if approval_record is not None else None
                snapshots = self.repo.list_file_snapshots(apply_run_id)
        memory = self._memory_status(patch_id, apply_run_id)
        return {
            "ok": True,
            "status": "OK",
            "patch": patch,
            "approval": approval,
            "apply": apply,
            "affected_paths": patch.get("affected_paths", []),
            "snapshot_count": len(snapshots),
            "rollback_available": bool((apply or {}).get("rollback_available", False)),
            "tests_status": (apply or {}).get("tests_status"),
            "bounded_error": (apply or {}).get("bounded_error") or patch.get("validation_error"),
            "memory_commit_status": memory.get("status"),
            "memory": memory,
        }

    def _memory_status(self, patch_id: str, apply_run_id: str | None) -> dict[str, Any]:
        try:
            with closing(sqlite3.connect(self.queue_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT memory_id, index_status, metadata_json, created_at
                    FROM memory_records
                    ORDER BY created_at DESC
                    LIMIT 200
                    """
                ).fetchall()
        except sqlite3.Error:
            return {"status": "not_found"}
        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if metadata.get("patch_id") == patch_id or (apply_run_id and metadata.get("apply_run_id") == apply_run_id):
                return {
                    "status": "COMMITTED",
                    "memory_id": row["memory_id"],
                    "index_status": row["index_status"],
                    "created_at": row["created_at"],
                }
        return {"status": "not_found"}
