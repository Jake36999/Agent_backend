from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from orchestrator.active_partition.models import ActivePartition
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.memory.snapshots import SnapshotMemoryService


class FakeChroma:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def upsert_chunks(self, **kwargs):
        if self.fail:
            raise RuntimeError("boom")
        self.calls.append(kwargs)
        return {"chunks_indexed": len(kwargs["chunks"])}


class SnapshotMemoryTests(unittest.TestCase):
    def test_snapshot_table_exists_with_later_patch_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)

            with closing(sqlite3.connect(root / "queue.db")) as conn:
                versions = [row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()]
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            self.assertIn("0005_snapshot_patch_records", versions)
            self.assertIn("snapshot_records", tables)
            self.assertIn("file_snapshots", tables)

    def test_workflow_result_creates_compact_snapshot_record_and_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            chroma = FakeChroma()
            service = SnapshotMemoryService(root / "queue.db", chroma)
            active = ActivePartition("client", "p", "scope", None, None, "high", "test", "now")

            result = service.record_workflow_snapshot(
                workflow_result={
                    "run_id": "r1",
                    "summary": "done",
                    "artifacts": {
                        "final_markdown": "C:/work/final.md",
                        "final_python_bundle": "C:/work/final.py",
                        "manifest_csv": "C:/work/manifest.csv",
                        "raw_manifest_csv": "path\nsecret.py",
                        "raw_report_body": "x" * 10000,
                        "conversation_json": '{"messages": []}',
                        "env_dump": "TOKEN=abcdef1234567890",
                    },
                },
                active_partition=active,
                selected_skill={"skill_id": "bug_triage_v1"},
            )

            self.assertTrue(result["ok"])
            self.assertEqual(len(chroma.calls), 1)
            with closing(sqlite3.connect(root / "queue.db")) as conn:
                row = conn.execute(
                    "SELECT summary, final_markdown_path, final_python_bundle_path, manifest_csv_path, artifact_json, index_status FROM snapshot_records"
                ).fetchone()
            self.assertEqual(row[0], "done")
            self.assertEqual(row[1], "C:/work/final.md")
            self.assertEqual(row[2], "C:/work/final.py")
            self.assertEqual(row[3], "C:/work/manifest.csv")
            self.assertNotIn("raw_report_body", row[4])
            self.assertNotIn("raw_manifest_csv", row[4])
            self.assertNotIn("conversation_json", row[4])
            self.assertNotIn("env_dump", row[4])
            self.assertEqual(row[5], "indexed")

    def test_no_active_project_stores_without_indexing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            chroma = FakeChroma()
            service = SnapshotMemoryService(root / "queue.db", chroma)

            result = service.record_workflow_snapshot(
                workflow_result={"summary": "done", "artifacts": {}},
                active_partition=None,
                selected_skill=None,
            )

            self.assertEqual(result["index_result"]["status"], "SKIPPED_NO_ACTIVE_PROJECT")
            self.assertEqual(chroma.calls, [])

    def test_chroma_failure_marks_failed_with_bounded_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            service = SnapshotMemoryService(root / "queue.db", FakeChroma(fail=True))
            active = ActivePartition("client", "p", "scope", None, None, "high", "test", "now")

            result = service.record_workflow_snapshot(
                workflow_result={"summary": "done", "artifacts": {}},
                active_partition=active,
                selected_skill=None,
            )

            self.assertEqual(result["index_result"]["status"], "INDEX_FAILED")
            with closing(sqlite3.connect(root / "queue.db")) as conn:
                row = conn.execute("SELECT index_status, index_error FROM snapshot_records").fetchone()
            self.assertEqual(row[0], "failed")
            self.assertLessEqual(len(row[1]), 1000)


if __name__ == "__main__":
    unittest.main()
