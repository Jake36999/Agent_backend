from __future__ import annotations

import hashlib
import shutil
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class RollbackService:
    def __init__(self, queue_db_path: Path, rollback_root: Path) -> None:
        self.queue_db_path = Path(queue_db_path)
        self.rollback_root = Path(rollback_root)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def snapshot_files(self, patch_id: str, files: list[Path]) -> list[dict[str, object]]:
        base = self.rollback_root / patch_id
        base.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, object]] = []
        with closing(self._connect()) as conn:
            for absolute in files:
                snapshot_id = f"file_snapshot_{uuid.uuid4().hex}"
                target = base / f"{snapshot_id}.content"
                absolute = absolute.resolve()
                if absolute.exists():
                    shutil.copyfile(absolute, target)
                    digest = sha256_file(absolute)
                else:
                    target.write_bytes(b"")
                    digest = "MISSING"
                conn.execute(
                    """
                    INSERT INTO file_snapshots(snapshot_id, patch_id, absolute_path, file_sha_before, content_before_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (snapshot_id, patch_id, str(absolute), digest, str(target), _utc_now()),
                )
                records.append({"snapshot_id": snapshot_id, "absolute_path": str(absolute), "file_sha_before": digest, "content_before_path": str(target)})
            conn.commit()
        return records

    def restore_snapshots(self, patch_id: str) -> dict[str, object]:
        restored: list[str] = []
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM file_snapshots WHERE patch_id = ? ORDER BY created_at ASC", (patch_id,)).fetchall()
        for row in rows:
            absolute = Path(row["absolute_path"])
            source = Path(row["content_before_path"])
            absolute.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, absolute)
            restored.append(str(absolute))
        return {"ok": True, "status": "RESTORED", "patch_id": patch_id, "restored_files": restored}
