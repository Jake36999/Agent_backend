import sqlite3
import tempfile
import unittest
from pathlib import Path

from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.memory.snapshots import SnapshotMemoryService
from orchestrator.active_partition.models import ActivePartition


class FakeChroma:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
    def upsert_snapshot_text(self, snapshot_id, content, metadata):
        if self.fail:
            raise RuntimeError("boom")
        self.calls.append((snapshot_id, content, metadata))


class SnapshotMemoryTests(unittest.TestCase):
    def test_workflow_result_creates_snapshot_record_and_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            chroma = FakeChroma()
            service = SnapshotMemoryService(root / "queue.db", chroma)
            active = ActivePartition("client", "p", "scope", None, None, "high", "test", "now")
            result = service.record_workflow_snapshot(
                workflow_result={"run_id": "r1", "summary": "done", "artifacts": {"final_markdown_path": "out.md", "full_report": "x" * 10000}},
                active_partition=active,
                selected_skill={"skill_id": "bug_triage_v1"},
            )
            self.assertTrue(result["ok"])
            self.assertEqual(len(chroma.calls), 1)
            conn = sqlite3.connect(root / "queue.db")
            row = conn.execute("SELECT summary, final_markdown_path, artifact_json FROM snapshot_records").fetchone()
            self.assertEqual(row[0], "done")
            self.assertEqual(row[1], "out.md")
            self.assertNotIn("full_report", row[2])

    def test_no_active_project_stores_without_indexing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            chroma = FakeChroma()
            service = SnapshotMemoryService(root / "queue.db", chroma)
            result = service.record_workflow_snapshot(workflow_result={"summary": "done", "artifacts": {}}, active_partition=None, selected_skill=None)
            self.assertEqual(result["index_result"]["status"], "SKIPPED_NO_ACTIVE_PROJECT")
            self.assertEqual(chroma.calls, [])

    def test_chroma_failure_marks_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            service = SnapshotMemoryService(root / "queue.db", FakeChroma(fail=True))
            active = ActivePartition("client", "p", "scope", None, None, "high", "test", "now")
            result = service.record_workflow_snapshot(workflow_result={"summary": "done", "artifacts": {}}, active_partition=active, selected_skill=None)
            self.assertEqual(result["index_result"]["status"], "INDEX_FAILED")


if __name__ == "__main__":
    unittest.main()
