from __future__ import annotations

from pathlib import Path

from .repo import PatchArtifactRepository
from .snapshots import sha256_file


class RollbackRestoreService:
    def __init__(self, queue_db_path: Path, rollback_root: Path) -> None:
        self.repo = PatchArtifactRepository(queue_db_path)
        self.rollback_root = Path(rollback_root).resolve()

    def restore_apply_run(self, apply_run_id: str) -> dict[str, object]:
        run = self.repo.get_apply_run(apply_run_id)
        if run is None:
            return {"ok": False, "status": "APPLY_RUN_NOT_FOUND", "apply_run_id": apply_run_id}
        target_repo = Path(run.target_repo).resolve()
        restored: list[str] = []
        deleted: list[str] = []
        for snapshot in self.repo.list_file_snapshots(apply_run_id):
            target = Path(snapshot.target_path).resolve()
            if not (target == target_repo or target_repo in target.parents):
                return {"ok": False, "status": "POLICY_BLOCK", "error": "snapshot target escapes target_repo"}
            if target.exists() and target.is_symlink():
                return {"ok": False, "status": "POLICY_BLOCK", "error": "symlink target restore is not allowed"}
            if snapshot.created_target:
                if target.exists():
                    target.unlink()
                    deleted.append(str(target))
                continue
            if not snapshot.backup_path or not snapshot.pre_apply_sha256:
                return {"ok": False, "status": "SNAPSHOT_INVALID", "error": "missing backup metadata"}
            backup = Path(snapshot.backup_path).resolve()
            if not (backup == self.rollback_root or self.rollback_root in backup.parents):
                return {"ok": False, "status": "POLICY_BLOCK", "error": "backup path escapes rollback root"}
            if sha256_file(backup) != snapshot.pre_apply_sha256:
                return {"ok": False, "status": "SNAPSHOT_HASH_MISMATCH", "error": "backup sha256 mismatch"}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(backup.read_bytes())
            if sha256_file(target) != snapshot.pre_apply_sha256:
                return {"ok": False, "status": "RESTORE_HASH_MISMATCH", "error": "restored sha256 mismatch"}
            restored.append(str(target))
        self.repo.update_apply_run(apply_run_id, status="ROLLED_BACK", rollback_available=False)
        return {"ok": True, "status": "ROLLED_BACK", "apply_run_id": apply_run_id, "restored_files": restored, "deleted_created_files": deleted}
