from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.active_partition.models import ActivePartition, MemoryProject
from orchestrator.active_partition.repo import ActivePartitionRepository
from orchestrator.db_bootstrap import bootstrap_databases


class ActivePartitionRepositoryTests(unittest.TestCase):
    def test_active_partition_persists_in_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = ActivePartitionRepository(root / "queue.db")
            project = MemoryProject(
                project_id="lmstudio-client-a-backend-debug",
                project_scope_hash="scope-1",
                source="manual_override",
                display_name="client-a / backend-debug",
                lmstudio_folder_relpath="client-a/backend-debug",
                allowed_roots_json=[str(root)],
                rag_enabled=True,
                created_at="2026-01-01T00:00:00Z",
                last_seen_at="2026-01-01T00:00:00Z",
            )
            repo.upsert_memory_project(project)
            partition = ActivePartition(
                client_id="local-lmstudio",
                active_project_id=project.project_id,
                active_project_scope_hash=project.project_scope_hash,
                active_conversation_id="chat",
                conversation_path=str(root / "client-a" / "backend-debug" / "chat.conversation.json"),
                confidence="high",
                source_event="manual_override",
                updated_at="2026-01-01T00:00:01Z",
            )
            repo.set_active_partition(partition)

            loaded = repo.get_active_partition()
            projects = repo.list_memory_projects()

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.active_project_scope_hash, "scope-1")
            self.assertEqual(projects[0].project_id, project.project_id)

