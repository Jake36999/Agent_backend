from __future__ import annotations

from pathlib import Path
from contextlib import closing
from datetime import datetime, timezone
import sqlite3


QUEUE_MIGRATION_0001 = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('PLANNING', 'PENDING_APPROVAL', 'COMPLETED')),
  resolution TEXT NOT NULL CHECK (resolution IN ('ACTIVE', 'REJECTED', 'CASCADE_PRUNED')),
  parent_task_id TEXT,
  title TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  slr_score REAL NOT NULL DEFAULT 0.0,
  depth_penalty REAL NOT NULL DEFAULT 0.0,
  final_score REAL NOT NULL DEFAULT 0.0,
  depth INTEGER NOT NULL DEFAULT 0,
  reroll_count INTEGER NOT NULL DEFAULT 0,
  negative_constraints_json TEXT NOT NULL DEFAULT '[]',
  novelty_md5 TEXT NOT NULL,
  lease_owner TEXT,
  lease_expires_at TEXT,
  revision INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  pruned_by_task_id TEXT,
  pruned_reason TEXT,
  FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS task_edges (
  parent_task_id TEXT NOT NULL,
  child_task_id TEXT NOT NULL,
  PRIMARY KEY (parent_task_id, child_task_id),
  FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id),
  FOREIGN KEY (child_task_id) REFERENCES tasks(task_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS task_events (
  event_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(task_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  diff_sha256 TEXT NOT NULL,
  diff_hmac_sha256 TEXT NOT NULL,
  base_snapshot_sha256 TEXT NOT NULL,
  proposed_snapshot_sha256 TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('PENDING', 'APPROVED', 'REJECTED')),
  decided_by TEXT,
  decided_at TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(task_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_tasks_ready
  ON tasks(project_id, created_at)
  WHERE state = 'PLANNING' AND resolution = 'ACTIVE' AND lease_owner IS NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_waiting_approval
  ON tasks(project_id, updated_at)
  WHERE state = 'PENDING_APPROVAL' AND resolution = 'ACTIVE';

CREATE TABLE IF NOT EXISTS files (
  project_id TEXT NOT NULL,
  project_scope_hash TEXT NOT NULL,
  absolute_path TEXT NOT NULL,
  file_sha256 TEXT NOT NULL,
  file_name TEXT NOT NULL,
  metadata_hash TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (project_scope_hash, absolute_path)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS ingestion_runs (
  run_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  project_scope_hash TEXT NOT NULL,
  target_path TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('RUNNING', 'COMPLETED', 'FAILED', 'FAILED_VECTOR_UPSERT', 'RECONCILED')),
  error TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  project_scope_hash TEXT NOT NULL,
  run_id TEXT NOT NULL,
  file_sha256 TEXT NOT NULL,
  absolute_path TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  processor TEXT NOT NULL,
  content_sha1 TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id),
  FOREIGN KEY (project_scope_hash, absolute_path) REFERENCES files(project_scope_hash, absolute_path)
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_chunks_project_scope
  ON chunks(project_id, project_scope_hash, chunk_index);
"""


QUEUE_MIGRATION_0002 = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memory_projects (
  project_id TEXT NOT NULL,
  project_scope_hash TEXT NOT NULL PRIMARY KEY,
  source TEXT NOT NULL,
  display_name TEXT NOT NULL,
  lmstudio_folder_relpath TEXT,
  allowed_roots_json TEXT NOT NULL DEFAULT '[]',
  rag_enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_memory_projects_project_id
  ON memory_projects(project_id);

CREATE TABLE IF NOT EXISTS active_partitions (
  client_id TEXT NOT NULL PRIMARY KEY,
  active_project_id TEXT,
  active_project_scope_hash TEXT,
  active_conversation_id TEXT,
  conversation_path TEXT,
  confidence TEXT NOT NULL,
  source_event TEXT NOT NULL,
  updated_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_active_partitions_scope_hash
  ON active_partitions(active_project_scope_hash);

CREATE TABLE IF NOT EXISTS conversation_events (
  event_id TEXT NOT NULL PRIMARY KEY,
  project_scope_hash TEXT NOT NULL,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content_json TEXT NOT NULL,
  token_count INTEGER NOT NULL DEFAULT 0,
  timestamp TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_conversation_events_project_scope_hash
  ON conversation_events(project_scope_hash);

CREATE INDEX IF NOT EXISTS idx_conversation_events_session_id
  ON conversation_events(session_id);

CREATE TABLE IF NOT EXISTS memory_records (
  memory_id TEXT NOT NULL PRIMARY KEY,
  project_id TEXT NOT NULL,
  project_scope_hash TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  source TEXT NOT NULL,
  content TEXT NOT NULL,
  content_sha1 TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  confidence_score REAL NOT NULL DEFAULT 1.0,
  created_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_memory_records_project_scope_hash
  ON memory_records(project_scope_hash);

CREATE INDEX IF NOT EXISTS idx_memory_records_memory_type
  ON memory_records(memory_type);

CREATE INDEX IF NOT EXISTS idx_memory_records_project_scope_type
  ON memory_records(project_scope_hash, memory_type);
"""


def _queue_migration_0003(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memory_records)").fetchall()}
    if "index_status" not in existing:
        conn.execute("ALTER TABLE memory_records ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'")
    if "indexed_at" not in existing:
        conn.execute("ALTER TABLE memory_records ADD COLUMN indexed_at TEXT")
    if "index_error" not in existing:
        conn.execute("ALTER TABLE memory_records ADD COLUMN index_error TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_records_index_status ON memory_records(index_status)"
    )


QUEUE_MIGRATION_0004 = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS skill_manifests (
  skill_id TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  project_scope_hash TEXT,
  manifest_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('verified', 'quarantined', 'disabled')),
  source_path TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_skill_manifests_status
ON skill_manifests(status);

CREATE INDEX IF NOT EXISTS idx_skill_manifests_project_scope_hash
ON skill_manifests(project_scope_hash);
"""


CONTROL_MIGRATION_0001 = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS leases (
  lease_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  worker_id TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  heartbeat_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS process_registry (
  pid INTEGER PRIMARY KEY,
  worker_id TEXT NOT NULL,
  command_json TEXT NOT NULL,
  started_at TEXT NOT NULL,
  heartbeat_at TEXT,
  status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'STALE', 'EXITED', 'ORPHANED')),
  exited_at TEXT,
  exit_code INTEGER,
  orphaned INTEGER NOT NULL DEFAULT 0
) STRICT;

CREATE TABLE IF NOT EXISTS dead_letters (
  dead_letter_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;
"""


QUEUE_MIGRATIONS = (
    ("0001_initial", QUEUE_MIGRATION_0001),
    ("0002_active_partition_memory", QUEUE_MIGRATION_0002),
    ("0003_memory_index_state", None),
    ("0004_skill_manifests", QUEUE_MIGRATION_0004),  # noqa: F821
)
CONTROL_MIGRATIONS = (("0001_initial", CONTROL_MIGRATION_0001),)


def bootstrap_databases(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for db_name, migrations in (("queue.db", QUEUE_MIGRATIONS), ("control.db", CONTROL_MIGRATIONS)):
        with closing(sqlite3.connect(root / db_name)) as conn:
            _apply_migrations(conn, migrations)
            conn.commit()


def _apply_migrations(conn: sqlite3.Connection, migrations: tuple[tuple[str, str], ...]) -> None:
    known = {version for version, _ in migrations}
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        ) STRICT, WITHOUT ROWID
        """
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    unknown = sorted(applied - known)
    if unknown:
        raise RuntimeError(f"database has unsupported future migrations: {', '.join(unknown)}")
    now = datetime.now(timezone.utc).isoformat()
    for version, script in migrations:
        if version in applied:
            continue
        if version == "0003_memory_index_state":
            _queue_migration_0003(conn)
        else:
            conn.executescript(script)
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, now),
        )
