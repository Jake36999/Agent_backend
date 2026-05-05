import tempfile
import time
import unittest
from pathlib import Path

from orchestrator.active_partition.watcher import ActivePartitionWatcher


class FakeResult:
    def __init__(self, **payload):
        self.payload = payload
    def to_dict(self):
        return self.payload


class FakeService:
    def __init__(self):
        self.calls = []
    def set_active_from_conversation_path(self, path):
        self.calls.append(path)
        p = Path(path)
        if p.parent.name == "root":
            return FakeResult(ok=False, status="NEEDS_PROJECT_FOLDER", message="needs project folder")
        return FakeResult(ok=True, status="OK", project_id=p.parent.name, project_scope_hash="scope", message="ok")


class ActivePartitionWatcherTests(unittest.TestCase):
    def test_newest_nested_conversation_maps_to_active_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / "p1" / "old.conversation.json"
            newer = root / "p2" / "new.conversation.json"
            older.parent.mkdir(); newer.parent.mkdir()
            older.write_text("{}")
            time.sleep(0.01)
            newer.write_text("{}")
            watcher = ActivePartitionWatcher(FakeService(), root, settle_ms=0)
            result = watcher.poll_once()
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["project_id"], "p2")

    def test_outside_root_policy_block(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            path = Path(other) / "x.conversation.json"
            path.write_text("{}")
            watcher = ActivePartitionWatcher(FakeService(), Path(tmp), settle_ms=0)
            result = watcher._handle_conversation_path(path)
            self.assertEqual(result["status"], "POLICY_BLOCK")

    def test_settle_logic_skips_unstable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "project" / "x.conversation.json"
            path.parent.mkdir()
            path.write_text("a")
            watcher = ActivePartitionWatcher(FakeService(), root, settle_ms=1)
            watcher._is_settled = lambda _path: False  # type: ignore[method-assign]
            result = watcher._handle_conversation_path(path)
            self.assertEqual(result["status"], "UNSTABLE")


if __name__ == "__main__":
    unittest.main()
