from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.active_partition.mapper import PartitionMapper


class ActivePartitionMapperTests(unittest.TestCase):
    def test_folder_path_maps_to_deterministic_project_id_and_scope_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "conversations"
            folder = root / "testing folder 2"
            folder.mkdir(parents=True)
            conversation = folder / "chat.conversation.json"
            conversation.write_text("{}", encoding="utf-8")

            result1 = PartitionMapper(root).map(conversation)
            result2 = PartitionMapper(root).map(conversation)

            self.assertTrue(result1.ok)
            self.assertEqual(result1.project_id, "lmstudio-testing-folder-2")
            self.assertEqual(result1.project_scope_hash, result2.project_scope_hash)

    def test_nested_folders_produce_distinct_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "conversations"
            nested_a = root / "client-a" / "backend-debug"
            nested_b = root / "client-a" / "backend-debug-v2"
            nested_a.mkdir(parents=True)
            nested_b.mkdir(parents=True)
            path_a = nested_a / "chat.conversation.json"
            path_b = nested_b / "chat.conversation.json"
            path_a.write_text("{}", encoding="utf-8")
            path_b.write_text("{}", encoding="utf-8")

            result_a = PartitionMapper(root).map(path_a)
            result_b = PartitionMapper(root).map(path_b)

            self.assertTrue(result_a.ok)
            self.assertTrue(result_b.ok)
            self.assertNotEqual(result_a.project_id, result_b.project_id)
            self.assertNotEqual(result_a.project_scope_hash, result_b.project_scope_hash)

    def test_root_level_conversation_requires_project_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "conversations"
            root.mkdir(parents=True)
            conversation = root / "chat.conversation.json"
            conversation.write_text("{}", encoding="utf-8")

            result = PartitionMapper(root).map(conversation)

            self.assertFalse(result.ok)
            self.assertEqual(result.status, "NEEDS_PROJECT_FOLDER")

