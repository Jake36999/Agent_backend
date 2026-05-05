from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .models import PatchArtifact


class PatchRepository:
    def __init__(self, queue_db_path: Path) -> None:
        self.queue_db_path = Path(queue_db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def insert_artifact(self, artifact: PatchArtifact) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO patch_artifacts (
                  patch_id, project_id, project_scope_hash, run_id, selected_skill_id, objective,
                  unified_diff, affected_files_json, test_commands_json, guardrail_checks_json,
                  audit_state_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.patch_id,
                    artifact.project_id,
                    artifact.project_scope_hash,
                    artifact.run_id,
                    artifact.selected_skill_id,
                    artifact.objective,
                    artifact.unified_diff,
                    json.dumps(artifact.affected_files, sort_keys=True),
                    json.dumps(artifact.test_commands, sort_keys=True),
                    json.dumps(artifact.guardrail_checks, sort_keys=True),
                    json.dumps(artifact.audit_state, sort_keys=True),
                    artifact.status,
                    artifact.created_at,
                ),
            )
            conn.commit()

    def get_artifact(self, patch_id: str) -> PatchArtifact | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM patch_artifacts WHERE patch_id = ?", (patch_id,)).fetchone()
        if not row:
            return None
        return PatchArtifact(
            patch_id=row["patch_id"],
            project_id=row["project_id"],
            project_scope_hash=row["project_scope_hash"],
            run_id=row["run_id"],
            selected_skill_id=row["selected_skill_id"],
            objective=row["objective"],
            unified_diff=row["unified_diff"],
            affected_files=json.loads(row["affected_files_json"]),
            test_commands=json.loads(row["test_commands_json"]),
            guardrail_checks=json.loads(row["guardrail_checks_json"]),
            audit_state=json.loads(row["audit_state_json"]),
            status=row["status"],
            created_at=row["created_at"],
        )

    def update_status(self, patch_id: str, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE patch_artifacts SET status = ? WHERE patch_id = ?", (status, patch_id))
            conn.commit()
