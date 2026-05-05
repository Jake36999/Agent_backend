from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from .models import PatchArtifact


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
