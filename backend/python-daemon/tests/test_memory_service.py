from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.active_partition.models import ActivePartition
from orchestrator.active_partition.repo import ActivePartitionRepository
from orchestrator.chroma_manager import ChromaConfig, ChromaManager
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.memory.models import MemoryRecord
from orchestrator.memory.repo import MemoryRepository
from orchestrator.memory.service import MemoryService


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeCollection:
    def __init__(self):
        self.upserts = []
        self.queries = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return {
            "ids": [["memory-1"]],
            "documents": [["memory result"]],
            "metadatas": [[{"project_scope_hash": kwargs["where"]["project_scope_hash"]}]],
            "distances": [[0.1]],
        }


class FakeChromaClient:
    def __init__(self):
        self.collection = FakeCollection()

    def get_or_create_collection(self, name):
        return self.collection


class MemoryServiceTests(unittest.TestCase):
    def test_commit_memory_stores_bounded_record_and_indexes_project_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            active_repo.set_active_partition(
                ActivePartition(
                    client_id="local-lmstudio",
                    active_project_id="lmstudio-client-a-backend-debug",
                    active_project_scope_hash="scope-1",
                    active_conversation_id="chat",
                    conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                    confidence="high",
                    source_event="manual_override",
                    updated_at="2026-01-01T00:00:01Z",
                )
            )
            chroma = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                chroma_client=FakeChromaClient(),
            )
            service = MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma)

            result = service.commit_memory(
                "decision",
                "This is a bounded memory record for the active partition." * 200,
                metadata={"source_note": "unit-test"},
            )
            records = MemoryRepository(root / "queue.db").list_memory_records("scope-1")

            self.assertTrue(result["ok"])
            self.assertLessEqual(len(records[0].content), 8000)
            self.assertEqual(chroma.collection.upserts[0]["metadatas"][0]["project_scope_hash"], "scope-1")
            self.assertEqual(chroma.collection.upserts[0]["metadatas"][0]["source"], "memory_record")
            self.assertEqual(records[0].index_status, "indexed")
            self.assertIsNotNone(records[0].indexed_at)

    def test_commit_memory_marks_failed_when_chroma_upsert_fails_and_can_reindex(self):
        class BrokenCollection(FakeCollection):
            def upsert(self, **kwargs):
                raise RuntimeError("vector store unavailable")

        class BrokenChromaClient(FakeChromaClient):
            def __init__(self):
                self.collection = BrokenCollection()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            active_repo.set_active_partition(
                ActivePartition(
                    client_id="local-lmstudio",
                    active_project_id="lmstudio-client-a-backend-debug",
                    active_project_scope_hash="scope-1",
                    active_conversation_id="chat",
                    conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                    confidence="high",
                    source_event="manual_override",
                    updated_at="2026-01-01T00:00:01Z",
                )
            )
            failing = MemoryService(
                MemoryRepository(root / "queue.db"),
                active_repo,
                ChromaManager(
                    ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                    http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                    chroma_client=BrokenChromaClient(),
                ),
            )

            failed = failing.commit_memory("decision", "This content is long enough to store.", metadata={"source_note": "unit-test"})
            failed_record = MemoryRepository(root / "queue.db").list_memory_records("scope-1")[0]

            self.assertFalse(failed["ok"])
            self.assertEqual(failed["index_status"], "failed")
            self.assertEqual(failed_record.index_status, "failed")
            self.assertIsNotNone(failed_record.index_error)

            recovering = MemoryService(
                MemoryRepository(root / "queue.db"),
                active_repo,
                ChromaManager(
                    ChromaConfig(chroma_path=root / "chroma-retry", auto_load_embedding_model=False),
                    http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                    chroma_client=FakeChromaClient(),
                ),
            )
            repaired = recovering.rebuild_memory_index_for_project("scope-1")
            refreshed = MemoryRepository(root / "queue.db").list_memory_records("scope-1")[0]

            self.assertEqual(repaired["indexed"], 1)
            self.assertEqual(refreshed.index_status, "indexed")

    def test_semantic_search_active_requires_active_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            chroma = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                chroma_client=FakeChromaClient(),
            )
            service = MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma)

            result = service.semantic_search_active("hello")

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "NO_ACTIVE_PARTITION")

    def test_semantic_search_active_injects_active_scope_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            active_repo.set_active_partition(
                ActivePartition(
                    client_id="local-lmstudio",
                    active_project_id="lmstudio-client-a-backend-debug",
                    active_project_scope_hash="scope-1",
                    active_conversation_id="chat",
                    conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                    confidence="high",
                    source_event="manual_override",
                    updated_at="2026-01-01T00:00:01Z",
                )
            )
            fake_client = FakeChromaClient()
            chroma = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                chroma_client=fake_client,
            )
            service = MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma)

            result = service.semantic_search_active("hello")

            self.assertTrue(result["ok"])
            self.assertEqual(fake_client.collection.queries[0]["where"], {"project_scope_hash": "scope-1"})
