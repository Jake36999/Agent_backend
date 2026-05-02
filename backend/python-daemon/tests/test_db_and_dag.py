import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.queue_repo import QueueRepository


class DbAndDagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        bootstrap_databases(self.root)
        self.repo = QueueRepository(self.root / "queue.db", self.root / "control.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bootstrap_uses_wal_and_strict_tables(self):
        with closing(sqlite3.connect(self.root / "queue.db")) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO tasks (
                      task_id, project_id, state, resolution, title, payload_json,
                      slr_score, depth_penalty, final_score, novelty_md5, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("bad", "p", "NOT_A_STATE", "ACTIVE", "bad", "{}", 0.0, 0.0, 0.0, "x", "now", "now"),
                )

    def test_claim_ready_task_blocks_on_unfinished_parent(self):
        self.repo.create_task("parent", "p", "Parent", {"tool": "a"}, depth=0)
        self.repo.create_task("child", "p", "Child", {"tool": "b"}, depth=1, parent_task_id="parent")

        claimed = self.repo.claim_ready_task("p", "worker", "2099-01-01T00:00:00Z")

        self.assertEqual(claimed["task_id"], "parent")
        self.assertIsNone(self.repo.claim_ready_task("p", "worker2", "2099-01-01T00:00:00Z"))

    def test_rejection_cascade_prunes_descendants_and_revokes_leases(self):
        self.repo.create_task("root", "p", "Root", {"tool": "a"}, depth=0)
        self.repo.create_task("child", "p", "Child", {"tool": "b"}, depth=1, parent_task_id="root")
        self.repo.create_task("grandchild", "p", "Grandchild", {"tool": "c"}, depth=2, parent_task_id="child")
        self.repo.claim_ready_task("p", "worker", "2099-01-01T00:00:00Z")

        pruned = self.repo.reject_and_prune("root", "human_rejected")

        self.assertEqual(pruned, ["child", "grandchild"])
        root = self.repo.get_task("root")
        child = self.repo.get_task("child")
        grandchild = self.repo.get_task("grandchild")
        self.assertEqual(root["resolution"], "REJECTED")
        self.assertEqual(child["resolution"], "CASCADE_PRUNED")
        self.assertEqual(grandchild["resolution"], "CASCADE_PRUNED")
        self.assertIsNone(root["lease_owner"])


if __name__ == "__main__":
    unittest.main()
