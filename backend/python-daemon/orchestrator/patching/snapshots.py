from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import FileSnapshot
from .repo import PatchArtifactRepository


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class RollbackSnapshotService:
    def __init__(self, queue_db_path: Path, rollback_root: Path) -> None:
        self.repo = PatchArtifactRepository(queue_db_path)
        self.rollback_root = Path(rollback_root).resolve()

    def snapshot_targets(self, *, apply_run_id: str, patch_id: str, target_repo: Path, rel_paths: list[str]) -> list[FileSnapshot]:
        snapshots: list[FileSnapshot] = []
        base = self.rollback_root / apply_run_id
        base.mkdir(parents=True, exist_ok=True)
        repo = Path(target_repo).resolve()
        for rel_path in rel_paths:
            target = (repo / rel_path).resolve()
            if not (target == repo or repo in target.parents):
                raise ValueError("snapshot target escapes target_repo")
            if target.exists() and target.is_symlink():
                raise ValueError("symlink target mutation is not allowed")
            snapshot_id = f"snapshot_{uuid.uuid4().hex}"
            if target.exists():
                pre_sha = sha256_file(target)
                pre_size = target.stat().st_size
                backup_path = base / f"{snapshot_id}.bin"
                shutil.copy2(target, backup_path)
                if sha256_file(backup_path) != pre_sha:
                    raise ValueError("snapshot sha256 verification failed")
                snapshot = FileSnapshot(
                    snapshot_file_id=snapshot_id,
                    apply_run_id=apply_run_id,
                    patch_id=patch_id,
                    target_path=str(target),
                    pre_apply_sha256=pre_sha,
                    pre_apply_size=pre_size,
                    backup_path=str(backup_path),
                    created_at=utc_now(),
                    created_target=False,
                )
            else:
                snapshot = FileSnapshot(
                    snapshot_file_id=snapshot_id,
                    apply_run_id=apply_run_id,
                    patch_id=patch_id,
                    target_path=str(target),
                    pre_apply_sha256=None,
                    pre_apply_size=None,
                    backup_path=None,
                    created_at=utc_now(),
                    created_target=True,
                )
            self.repo.insert_file_snapshot(snapshot)
            snapshots.append(snapshot)
        return snapshots
