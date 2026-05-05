from __future__ import annotations

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

    def set_active_from_conversation_path(self, path, source_event="manual_override"):
        self.calls.append((path, source_event))
        p = Path(path)
        if p.parent == p.parent.parent:
            return FakeResult(ok=False, status="NEEDS_PROJECT_FOLDER", message="needs project folder")
        return FakeResult(ok=True, status="MAPPED", project_id=p.parent.name, project_scope_hash="scope", message="ok")


class ActivePartitionWatcherTests(unittest.TestCase):
    def test_newest_nested_conversation_maps_to_active_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / "p1" / "old.conversation.json"
            newer = root / "p2" / "new.conversation.json"
            older.parent.mkdir()
            newer.parent.mkdir()
            older.write_text("not json inspected", encoding="utf-8")
            time.sleep(0.01)
            newer.write_text("{this is intentionally not parsed", encoding="utf-8")
            service = FakeService()
            watcher = ActivePartitionWatcher(service, root, settle_ms=0)

            result = watcher.poll_once()

            self.assertEqual(result["status"], "MAPPED")
            self.assertEqual(result["project_id"], "p2")
            self.assertEqual(service.calls[0][1], "lmstudio_conversation_watcher")

    def test_outside_root_policy_block(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            path = Path(other) / "x.conversation.json"
            path.write_text("{}", encoding="utf-8")
            watcher = ActivePartitionWatcher(FakeService(), Path(tmp), settle_ms=0)

            result = watcher.handle_conversation_path(path)

            self.assertEqual(result["status"], "POLICY_BLOCK")

    def test_root_level_conversation_does_not_overwrite_active_project(self):
        class RootAwareService(FakeService):
            def set_active_from_conversation_path(self, path, source_event="manual_override"):
                self.calls.append((path, source_event))
                return FakeResult(ok=False, status="NEEDS_PROJECT_FOLDER", message="needs project folder")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "x.conversation.json"
            path.write_text("{}", encoding="utf-8")
            service = RootAwareService()
            watcher = ActivePartitionWatcher(service, root, settle_ms=0)

            result = watcher.poll_once()

            self.assertEqual(result["status"], "NEEDS_PROJECT_FOLDER")
            self.assertIsNone(watcher.last_applied_path)

    def test_settle_logic_skips_unstable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "project" / "x.conversation.json"
            path.parent.mkdir()
            path.write_text("a", encoding="utf-8")
            watcher = ActivePartitionWatcher(FakeService(), root, settle_ms=1)
            watcher._is_settled = lambda _path: False  # type: ignore[method-assign]

            result = watcher.handle_conversation_path(path)

            self.assertEqual(result["status"], "UNSTABLE")

    def test_thread_lifecycle_stops_and_joins_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            watcher = ActivePartitionWatcher(FakeService(), Path(tmp), settle_ms=0, interval_seconds=0.01)

            watcher.start()
            self.assertTrue(watcher.is_running)
            watcher.stop(timeout=1.0)

            self.assertFalse(watcher.is_running)


if __name__ == "__main__":
    unittest.main()
