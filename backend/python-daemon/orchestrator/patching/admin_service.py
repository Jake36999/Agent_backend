from __future__ import annotations

from pathlib import Path
from typing import Any

from .repo import PatchArtifactRepository
from .rollback import RollbackRestoreService
from .snapshots import sha256_file


def _bounded(value: object, limit: int = 500) -> str | None:
    if value is None:
        return None
    return str(value)[:limit]


class PatchAdminService:
    def __init__(self, queue_db_path: Path, rollback_root: Path | None = None) -> None:
        self.queue_db_path = Path(queue_db_path)
        self.repo = PatchArtifactRepository(self.queue_db_path)
        self.rollback_root = Path(rollback_root).resolve() if rollback_root is not None else self.queue_db_path.parent / "rollback"

    def list_patch_artifacts(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._artifact(item) for item in self.repo.list_artifacts(limit)]

    def show_patch_artifact(self, patch_id: str) -> dict[str, Any]:
        artifact = self.repo.get(patch_id)
        if artifact is None:
            return self._error("PATCH_NOT_FOUND", patch_id=patch_id)
        return self._artifact(artifact)

    def list_patch_apply_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._apply_run(item) for item in self.repo.list_apply_runs(limit)]

    def show_patch_apply_run(self, apply_run_id: str) -> dict[str, Any]:
        run = self.repo.get_apply_run(apply_run_id)
        if run is None:
            return self._error("APPLY_RUN_NOT_FOUND", apply_run_id=apply_run_id)
        return self._apply_run(run)

    def list_approvals(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._approval(item) for item in self.repo.list_approval_records(limit)]

    def list_file_snapshots(self, apply_run_id: str) -> list[dict[str, Any]]:
        return [self._snapshot(item) for item in self.repo.list_file_snapshots(apply_run_id)]

    def verify_rollback(self, apply_run_id: str) -> dict[str, Any]:
        run = self.repo.get_apply_run(apply_run_id)
        if run is None:
            return self._error("APPLY_RUN_NOT_FOUND", apply_run_id=apply_run_id, phase="rollback_verify")
        snapshots = self.repo.list_file_snapshots(apply_run_id)
        if not snapshots:
            return self._error("SNAPSHOTS_NOT_FOUND", apply_run_id=apply_run_id, phase="rollback_verify")
        checked: list[dict[str, Any]] = []
        for snapshot in snapshots:
            if snapshot.created_target:
                checked.append({"snapshot_file_id": snapshot.snapshot_file_id, "target_path": snapshot.target_path, "created_target": True, "backup_status": "not_required"})
                continue
            if not snapshot.backup_path or not snapshot.pre_apply_sha256:
                return self._error("SNAPSHOT_INVALID", apply_run_id=apply_run_id, phase="rollback_verify", affected_path=snapshot.target_path)
            backup = Path(snapshot.backup_path).resolve()
            if not backup.exists():
                return self._error("SNAPSHOT_MISSING", apply_run_id=apply_run_id, phase="rollback_verify", affected_path=snapshot.target_path)
            digest = sha256_file(backup)
            if digest != snapshot.pre_apply_sha256:
                return self._error("SNAPSHOT_HASH_MISMATCH", apply_run_id=apply_run_id, phase="rollback_verify", affected_path=snapshot.target_path)
            checked.append({"snapshot_file_id": snapshot.snapshot_file_id, "target_path": snapshot.target_path, "created_target": False, "backup_status": "verified", "pre_apply_sha256": snapshot.pre_apply_sha256})
        return {"ok": True, "status": "ROLLBACK_VERIFIED", "apply_run_id": apply_run_id, "snapshot_count": len(snapshots), "snapshots": checked}

    def restore_patch_run(self, apply_run_id: str, *, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            return {"ok": False, "status": "CONFIRMATION_REQUIRED", "apply_run_id": apply_run_id, "summary": "Pass --confirm to restore a patch apply run."}
        return RollbackRestoreService(self.queue_db_path, self.rollback_root).restore_apply_run(apply_run_id)

    def _artifact(self, item: Any) -> dict[str, Any]:
        return {
            "patch_id": item.patch_id,
            "run_id": item.run_id,
            "project_id": item.project_id,
            "project_scope_hash": item.project_scope_hash,
            "selected_skill_id": item.selected_skill_id,
            "target_repo": item.target_repo,
            "status": item.status,
            "patch_path": item.patch_path,
            "diff_sha256": item.diff_sha256,
            "affected_paths": list(item.affected_paths_json),
            "created_at": item.created_at,
            "validation_status": item.validation_status,
            "validation_error": _bounded(item.validation_error),
        }

    def _approval(self, item: Any) -> dict[str, Any]:
        tests = item.declared_tests_json or []
        return {
            "approval_id": item.approval_id,
            "patch_id": item.patch_id,
            "run_id": item.run_id,
            "project_id": item.project_id,
            "project_scope_hash": item.project_scope_hash,
            "target_repo": item.target_repo,
            "approved": item.approved,
            "approved_by": item.approved_by,
            "approved_at": item.approved_at,
            "approval_scope": item.approval_scope,
            "approved_diff_sha256": item.approved_diff_sha256,
            "declared_test_count": len(tests),
            "declared_tests": [{"argv": command[:8]} for command in tests if isinstance(command, list)],
            "created_at": item.created_at,
            "notes": _bounded(item.notes, 200),
        }

    def _apply_run(self, item: Any) -> dict[str, Any]:
        return {
            "apply_run_id": item.apply_run_id,
            "patch_id": item.patch_id,
            "approval_id": item.approval_id,
            "run_id": item.run_id,
            "project_id": item.project_id,
            "project_scope_hash": item.project_scope_hash,
            "target_repo": item.target_repo,
            "status": item.status,
            "applied_at": item.applied_at,
            "completed_at": item.completed_at,
            "rollback_available": item.rollback_available,
            "tests_status": item.tests_status,
            "bounded_error": _bounded(item.bounded_error),
        }

    def _snapshot(self, item: Any) -> dict[str, Any]:
        return {
            "snapshot_file_id": item.snapshot_file_id,
            "apply_run_id": item.apply_run_id,
            "patch_id": item.patch_id,
            "target_path": item.target_path,
            "pre_apply_sha256": item.pre_apply_sha256,
            "pre_apply_size": item.pre_apply_size,
            "backup_path": item.backup_path,
            "created_at": item.created_at,
            "created_target": item.created_target,
        }

    def _error(self, status: str, **kwargs: Any) -> dict[str, Any]:
        return {"ok": False, "status": status, **{key: value for key, value in kwargs.items() if value is not None}}
