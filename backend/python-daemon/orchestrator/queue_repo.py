from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approval import DiffApprovalEnvelope, md5_novelty_hex
from .dag_runtime import topological_descendants

ALLOWED_TASK_TRANSITIONS = {
    ("PLANNING", "PENDING_APPROVAL"),
    ("PLANNING", "COMPLETED"),
    ("PENDING_APPROVAL", "PLANNING"),
    ("PENDING_APPROVAL", "COMPLETED"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class QueueRepository:
    def __init__(self, queue_db: Path, control_db: Path) -> None:
        self.queue_db = queue_db
        self.control_db = control_db

    def _queue(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.queue_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _control(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.control_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def create_task(
        self,
        task_id: str,
        project_id: str,
        title: str,
        payload: dict[str, Any],
        *,
        depth: int,
        parent_task_id: str | None = None,
    ) -> None:
        now = _now()
        novelty = md5_novelty_hex(
            {
                "tool": payload.get("tool"),
                "arg_shape": sorted(payload.keys()),
                "parent_task_id": parent_task_id,
                "depth": depth,
            }
        )
        with closing(self._queue()) as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                  task_id, project_id, state, resolution, parent_task_id, title, payload_json,
                  slr_score, depth_penalty, final_score, depth, novelty_md5, created_at, updated_at
                ) VALUES (?, ?, 'PLANNING', 'ACTIVE', ?, ?, ?, 0.0, 0.0, 0.0, ?, ?, ?, ?)
                """,
                (task_id, project_id, parent_task_id, title, json.dumps(payload), depth, novelty, now, now),
            )
            if parent_task_id is not None:
                conn.execute(
                    "INSERT INTO task_edges(parent_task_id, child_task_id) VALUES (?, ?)",
                    (parent_task_id, task_id),
                )
            conn.commit()

    def _record_task_event(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        event_type: str,
        details: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO task_events(event_id, task_id, event_type, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), task_id, event_type, json.dumps(details, sort_keys=True), _now()),
        )

    def list_task_events(self, task_id: str) -> list[dict[str, Any]]:
        with closing(self._queue()) as conn:
            rows = conn.execute(
                "SELECT * FROM task_events WHERE task_id = ? ORDER BY created_at ASC",
                (task_id,),
            ).fetchall()
        return [_dict(row) for row in rows if row is not None]

    def get_task(self, task_id: str) -> dict[str, Any]:
        with closing(self._queue()) as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        result = _dict(row)
        if result is None:
            raise KeyError(task_id)
        return result

    def claim_ready_task(self, project_id: str, worker_id: str, lease_expires_at: str) -> dict[str, Any] | None:
        now = _now()
        conn = self._queue()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                WITH next_task AS (
                    SELECT t.task_id
                    FROM tasks t
                    WHERE t.project_id = ?
                      AND t.state = 'PLANNING'
                      AND t.resolution = 'ACTIVE'
                      AND t.lease_owner IS NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM task_edges e
                          JOIN tasks p ON p.task_id = e.parent_task_id
                          WHERE e.child_task_id = t.task_id
                            AND (p.state <> 'COMPLETED' OR p.resolution <> 'ACTIVE')
                      )
                    ORDER BY t.created_at ASC
                    LIMIT 1
                )
                UPDATE tasks
                SET lease_owner = ?,
                    lease_expires_at = ?,
                    revision = revision + 1,
                    updated_at = ?
                WHERE task_id IN (SELECT task_id FROM next_task)
                RETURNING task_id, project_id, state, resolution, payload_json, revision
                """,
                (project_id, worker_id, lease_expires_at, now),
            ).fetchone()
            conn.commit()
            result = _dict(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        if result is not None:
            with closing(self._control()) as control:
                control.execute(
                    """
                    INSERT INTO leases(lease_id, task_id, worker_id, acquired_at, expires_at, heartbeat_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), result["task_id"], worker_id, now, lease_expires_at, now),
                )
                control.commit()
        return result

    def release_expired_leases(self, now_iso: str) -> int:
        conn = self._queue()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """
                SELECT task_id
                FROM tasks
                WHERE lease_owner IS NOT NULL
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at < ?
                """,
                (now_iso,),
            ).fetchall()
            task_ids = [row["task_id"] for row in rows]
            for task_id in task_ids:
                conn.execute(
                    """
                    UPDATE tasks
                    SET lease_owner = NULL,
                        lease_expires_at = NULL,
                        updated_at = ?,
                        revision = revision + 1
                    WHERE task_id = ?
                    """,
                    (_now(), task_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        if task_ids:
            with closing(self._control()) as control:
                for task_id in task_ids:
                    control.execute("DELETE FROM leases WHERE task_id = ?", (task_id,))
                control.commit()
        return len(task_ids)

    def set_task_state(self, task_id: str, state: str) -> None:
        current = self.get_task(task_id)["state"]
        self.transition_task_state(task_id, current, state, reason="set_task_state")

    def transition_task_state(
        self,
        task_id: str,
        from_state: str,
        to_state: str,
        *,
        reason: str,
    ) -> None:
        if (from_state, to_state) not in ALLOWED_TASK_TRANSITIONS:
            raise ValueError(f"invalid task transition: {from_state} -> {to_state}")
        now = _now()
        with closing(self._queue()) as conn:
            row = conn.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            if row["state"] != from_state:
                raise ValueError(f"task {task_id} is {row['state']}, not {from_state}")
            conn.execute(
                "UPDATE tasks SET state = ?, updated_at = ?, revision = revision + 1 WHERE task_id = ?",
                (to_state, now, task_id),
            )
            self._record_task_event(
                conn,
                task_id,
                "state_transition",
                {"from_state": from_state, "to_state": to_state, "reason": reason},
            )
            conn.commit()

    def complete_task(self, task_id: str) -> None:
        now = _now()
        with closing(self._queue()) as conn:
            row = conn.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            if (row["state"], "COMPLETED") not in ALLOWED_TASK_TRANSITIONS:
                raise ValueError(f"invalid task transition: {row['state']} -> COMPLETED")
            conn.execute(
                """
                UPDATE tasks
                SET state = 'COMPLETED', lease_owner = NULL, lease_expires_at = NULL,
                    completed_at = ?, updated_at = ?, revision = revision + 1
                WHERE task_id = ?
                """,
                (now, now, task_id),
            )
            self._record_task_event(
                conn,
                task_id,
                "state_transition",
                {"from_state": row["state"], "to_state": "COMPLETED", "reason": "complete_task"},
            )
            conn.commit()
        with closing(self._control()) as conn:
            conn.execute("DELETE FROM leases WHERE task_id = ?", (task_id,))
            conn.commit()

    def reject_and_prune(self, task_id: str, reason: str) -> list[str]:
        descendants = self._descendants(task_id)
        now = _now()
        with closing(self._queue()) as conn:
            conn.execute(
                """
                UPDATE tasks
                SET resolution = 'REJECTED', lease_owner = NULL, lease_expires_at = NULL,
                    pruned_reason = ?, updated_at = ?, revision = revision + 1
                WHERE task_id = ?
                """,
                (reason, now, task_id),
            )
            self._record_task_event(
                conn,
                task_id,
                "resolution_transition",
                {"to_resolution": "REJECTED", "reason": reason},
            )
            for child_id in descendants:
                conn.execute(
                    """
                    UPDATE tasks
                    SET resolution = 'CASCADE_PRUNED', lease_owner = NULL, lease_expires_at = NULL,
                        pruned_by_task_id = ?, pruned_reason = ?, updated_at = ?, revision = revision + 1
                    WHERE task_id = ? AND resolution = 'ACTIVE'
                    """,
                    (task_id, reason, now, child_id),
                )
                self._record_task_event(
                    conn,
                    child_id,
                    "resolution_transition",
                    {"to_resolution": "CASCADE_PRUNED", "pruned_by_task_id": task_id, "reason": reason},
                )
            conn.commit()
        with closing(self._control()) as conn:
            for affected_id in [task_id, *descendants]:
                conn.execute("DELETE FROM leases WHERE task_id = ?", (affected_id,))
            conn.commit()
        return descendants

    def _descendants(self, task_id: str) -> list[str]:
        with closing(self._queue()) as conn:
            rows = conn.execute(
                """
                WITH RECURSIVE descendants(parent_task_id, child_task_id) AS (
                    SELECT parent_task_id, child_task_id FROM task_edges WHERE parent_task_id = ?
                    UNION ALL
                    SELECT e.parent_task_id, e.child_task_id
                    FROM task_edges e
                    JOIN descendants d ON e.parent_task_id = d.child_task_id
                )
                SELECT parent_task_id, child_task_id FROM descendants
                """,
                (task_id,),
            ).fetchall()
        edges = [(row["parent_task_id"], row["child_task_id"]) for row in rows]
        return topological_descendants(task_id, edges)

    def create_approval(self, approval_id: str, task_id: str, envelope: DiffApprovalEnvelope) -> None:
        task = self.get_task(task_id)
        with closing(self._queue()) as conn:
            conn.execute(
                """
                INSERT INTO approvals (
                  approval_id, task_id, diff_sha256, diff_hmac_sha256,
                  base_snapshot_sha256, proposed_snapshot_sha256, decision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """,
                (
                    approval_id,
                    task_id,
                    envelope.diff_sha256,
                    envelope.diff_hmac_sha256,
                    envelope.base_snapshot_sha256,
                    envelope.proposed_snapshot_sha256,
                    _now(),
                ),
            )
            conn.commit()
        self.transition_task_state(task_id, task["state"], "PENDING_APPROVAL", reason="approval_created")

    def approve_task(self, task_id: str, decided_by: str) -> None:
        now = _now()
        with closing(self._queue()) as conn:
            conn.execute(
                """
                UPDATE approvals
                SET decision = 'APPROVED', decided_by = ?, decided_at = ?
                WHERE task_id = ? AND decision = 'PENDING'
                """,
                (decided_by, now, task_id),
            )
            conn.commit()
        self.transition_task_state(task_id, "PENDING_APPROVAL", "PLANNING", reason="approval_approved")

    def reject_approval(self, task_id: str, decided_by: str, reason: str) -> list[str]:
        now = _now()
        with closing(self._queue()) as conn:
            conn.execute(
                """
                UPDATE approvals
                SET decision = 'REJECTED', decided_by = ?, decided_at = ?
                WHERE task_id = ? AND decision = 'PENDING'
                """,
                (decided_by, now, task_id),
            )
            conn.commit()
        return self.reject_and_prune(task_id, reason)

    def update_scores(self, task_id: str, slr_score: float, depth_penalty: float, final_score: float) -> None:
        with closing(self._queue()) as conn:
            conn.execute(
                """
                UPDATE tasks
                SET slr_score = ?, depth_penalty = ?, final_score = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (slr_score, depth_penalty, final_score, _now(), task_id),
            )
            conn.commit()

    def add_negative_constraint(self, task_id: str, constraint: str) -> int:
        task = self.get_task(task_id)
        constraints = json.loads(task["negative_constraints_json"])
        constraints.append(constraint)
        reroll_count = int(task["reroll_count"]) + 1
        with closing(self._queue()) as conn:
            conn.execute(
                """
                UPDATE tasks
                SET negative_constraints_json = ?, reroll_count = ?, lease_owner = NULL,
                    lease_expires_at = NULL, updated_at = ?, revision = revision + 1
                WHERE task_id = ?
                """,
                (json.dumps(constraints), reroll_count, _now(), task_id),
            )
            conn.commit()
        return reroll_count

    def dead_letter(self, task_id: str, reason: str, payload: dict[str, Any]) -> None:
        with closing(self._control()) as conn:
            conn.execute(
                """
                INSERT INTO dead_letters(dead_letter_id, task_id, reason, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), task_id, reason, json.dumps(payload), _now()),
            )
            conn.commit()

    def list_dead_letters(self, limit: int = 100) -> list[dict[str, Any]]:
        with closing(self._control()) as conn:
            rows = conn.execute(
                "SELECT * FROM dead_letters ORDER BY created_at DESC LIMIT ?",
                (max(1, min(int(limit), 1000)),),
            ).fetchall()
        return [_dict(row) for row in rows if row is not None]

    def start_ingestion_run(self, run_id: str, project_id: str, project_scope_hash: str, target_path: str) -> None:
        now = _now()
        with closing(self._queue()) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ingestion_runs(
                  run_id, project_id, project_scope_hash, target_path, state, error, started_at, finished_at
                ) VALUES (?, ?, ?, ?, 'RUNNING', NULL, ?, NULL)
                """,
                (run_id, project_id, project_scope_hash, target_path, now),
            )
            conn.commit()

    def finish_ingestion_run(self, run_id: str, state: str, error: str | None) -> None:
        with closing(self._queue()) as conn:
            conn.execute(
                """
                UPDATE ingestion_runs
                SET state = ?, error = ?, finished_at = ?
                WHERE run_id = ?
                """,
                (state, error, _now(), run_id),
            )
            conn.commit()

    def latest_ingestion_run(self, project_id: str) -> dict[str, Any]:
        with closing(self._queue()) as conn:
            row = conn.execute(
                """
                SELECT *
                FROM ingestion_runs
                WHERE project_id = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        result = _dict(row)
        if result is None:
            raise KeyError(project_id)
        return result

    def record_file_manifest(self, project_id: str, project_scope_hash: str, metadata: dict[str, Any]) -> None:
        with closing(self._queue()) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files(
                  project_id, project_scope_hash, absolute_path, file_sha256, file_name,
                  metadata_hash, size_bytes, mtime_ns, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    project_scope_hash,
                    metadata["absolute_path"],
                    metadata["file_sha256"],
                    metadata["file_name"],
                    metadata["metadata_hash"],
                    int(metadata["size_bytes"]),
                    int(metadata["mtime_ns"]),
                    _now(),
                ),
            )
            conn.commit()

    def file_manifest(self, project_scope_hash: str, absolute_path: str) -> dict[str, Any] | None:
        with closing(self._queue()) as conn:
            row = conn.execute(
                """
                SELECT *
                FROM files
                WHERE project_scope_hash = ? AND absolute_path = ?
                """,
                (project_scope_hash, absolute_path),
            ).fetchone()
        return _dict(row)

    def file_paths_for_scope(self, project_scope_hash: str) -> set[str]:
        with closing(self._queue()) as conn:
            rows = conn.execute(
                "SELECT absolute_path FROM files WHERE project_scope_hash = ?",
                (project_scope_hash,),
            ).fetchall()
        return {str(row["absolute_path"]) for row in rows}

    def delete_file_manifest(self, project_scope_hash: str, absolute_path: str) -> int:
        with closing(self._queue()) as conn:
            conn.execute(
                "DELETE FROM chunks WHERE project_scope_hash = ? AND absolute_path = ?",
                (project_scope_hash, absolute_path),
            )
            cursor = conn.execute(
                "DELETE FROM files WHERE project_scope_hash = ? AND absolute_path = ?",
                (project_scope_hash, absolute_path),
            )
            conn.commit()
            return cursor.rowcount

    def record_chunks(
        self,
        project_id: str,
        project_scope_hash: str,
        run_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        now = _now()
        with closing(self._queue()) as conn:
            for chunk in chunks:
                metadata = dict(chunk.get("metadata") or {})
                content = str(chunk["content"])
                conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks(
                      chunk_id, project_id, project_scope_hash, run_id, file_sha256, absolute_path,
                      chunk_index, processor, content_sha1, content, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk["chunk_id"],
                        project_id,
                        project_scope_hash,
                        run_id,
                        metadata["file_sha256"],
                        metadata["absolute_path"],
                        int(metadata.get("chunk_index", 0)),
                        str(metadata.get("processor", "unknown")),
                        hashlib_sha1(content),
                        content,
                        json.dumps(metadata, sort_keys=True),
                        now,
                    ),
                )
            conn.commit()

    def list_chunks(self, project_id: str) -> list[dict[str, Any]]:
        with closing(self._queue()) as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE project_id = ? ORDER BY chunk_index ASC, chunk_id ASC",
                (project_id,),
            ).fetchall()
        return [_dict(row) for row in rows if row is not None]

    def delete_chunks_for_path(self, project_scope_hash: str, absolute_path: str) -> int:
        with closing(self._queue()) as conn:
            cursor = conn.execute(
                "DELETE FROM chunks WHERE project_scope_hash = ? AND absolute_path = ?",
                (project_scope_hash, absolute_path),
            )
            conn.commit()
            return cursor.rowcount

    def chunks_for_rebuild(self, project_id: str) -> list[dict[str, Any]]:
        with closing(self._queue()) as conn:
            rows = conn.execute(
                """
                SELECT chunk_id, project_id, project_scope_hash, absolute_path, chunk_index,
                       processor, content, metadata_json
                FROM chunks
                WHERE project_id = ?
                ORDER BY absolute_path ASC, chunk_index ASC
                """,
                (project_id,),
            ).fetchall()
        payloads = []
        for row in rows:
            item = _dict(row)
            if item is None:
                continue
            payloads.append(
                {
                    "chunk_id": item["chunk_id"],
                    "content": item["content"],
                    "metadata": json.loads(item["metadata_json"]),
                }
            )
        return payloads

    def list_rebuildable_chunks(self, project_id: str) -> list[dict[str, Any]]:
        with closing(self._queue()) as conn:
            rows = conn.execute(
                """
                SELECT c.chunk_id, c.project_id, c.project_scope_hash, c.absolute_path, c.chunk_index,
                       c.processor, c.content, c.metadata_json
                FROM chunks c
                JOIN ingestion_runs r ON r.run_id = c.run_id
                WHERE c.project_id = ?
                  AND r.state IN ('FAILED_VECTOR_UPSERT', 'FAILED')
                ORDER BY c.absolute_path ASC, c.chunk_index ASC
                """,
                (project_id,),
            ).fetchall()
        payloads = []
        for row in rows:
            item = _dict(row)
            if item is None:
                continue
            payloads.append(
                {
                    "chunk_id": item["chunk_id"],
                    "content": item["content"],
                    "metadata": json.loads(item["metadata_json"]),
                }
            )
        return payloads

    def mark_rebuildable_runs_reconciled(self, project_id: str) -> int:
        with closing(self._queue()) as conn:
            cursor = conn.execute(
                """
                UPDATE ingestion_runs
                SET state = 'RECONCILED',
                    error = NULL,
                    finished_at = ?
                WHERE project_id = ?
                  AND state IN ('FAILED_VECTOR_UPSERT', 'FAILED')
                """,
                (_now(), project_id),
            )
            conn.commit()
            return cursor.rowcount

    def count_file_manifests(self) -> int:
        with closing(self._queue()) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM files").fetchone()[0])

    def register_worker(self, worker_id: str, command: list[str], pid: int | None = None) -> None:
        now = _now()
        with closing(self._control()) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO process_registry(
                  pid, worker_id, command_json, started_at, heartbeat_at, status, exited_at, exit_code, orphaned
                ) VALUES (?, ?, ?, ?, ?, 'RUNNING', NULL, NULL, 0)
                """,
                (pid if pid is not None else os.getpid(), worker_id, json.dumps(command), now, now),
            )
            conn.commit()

    def heartbeat_worker(self, worker_id: str, pid: int | None = None) -> None:
        with closing(self._control()) as conn:
            conn.execute(
                """
                UPDATE process_registry
                SET heartbeat_at = ?, status = 'RUNNING'
                WHERE worker_id = ? AND pid = ?
                """,
                (_now(), worker_id, pid if pid is not None else os.getpid()),
            )
            conn.execute(
                "UPDATE leases SET heartbeat_at = ? WHERE worker_id = ?",
                (_now(), worker_id),
            )
            conn.commit()

    def mark_stale_workers(self, stale_before_iso: str) -> int:
        with closing(self._control()) as conn:
            cursor = conn.execute(
                """
                UPDATE process_registry
                SET status = 'STALE'
                WHERE status = 'RUNNING'
                  AND heartbeat_at IS NOT NULL
                  AND heartbeat_at < ?
                """,
                (stale_before_iso,),
            )
            conn.commit()
            return cursor.rowcount

    def list_worker_status(self) -> list[dict[str, Any]]:
        with closing(self._control()) as conn:
            rows = conn.execute(
                "SELECT * FROM process_registry ORDER BY started_at ASC"
            ).fetchall()
        return [_dict(row) for row in rows if row is not None]

    def mark_worker_exited(self, pid: int, exit_code: int) -> None:
        with closing(self._control()) as conn:
            conn.execute(
                """
                UPDATE process_registry
                SET status = 'EXITED', exited_at = ?, exit_code = ?
                WHERE pid = ?
                """,
                (_now(), exit_code, pid),
            )
            conn.commit()


def hashlib_sha1(text: str) -> str:
    import hashlib

    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
