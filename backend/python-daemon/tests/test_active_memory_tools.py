from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.active_partition.models import ActivePartition
from orchestrator.active_partition.repo import ActivePartitionRepository
from orchestrator.active_partition.service import ActivePartitionService
from orchestrator.adapters import ToolAdapters
from orchestrator.chroma_manager import ChromaConfig, ChromaManager
from orchestrator.db_bootstrap import bootstrap_databases
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


class ActiveMemoryToolTests(unittest.TestCase):
    def test_mcp_get_active_partition_returns_persisted_partition(self):
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
            adapters = ToolAdapters(
                active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations"),
                memory_service=MemoryService(
                    MemoryRepository(root / "queue.db"),
                    active_repo,
                    ChromaManager(
                        ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                        http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                        chroma_client=FakeChromaClient(),
                    ),
                ),
            )

            result = adapters.call_mcp_tool("mcp_get_active_partition", {})

            self.assertTrue(result["ok"])
            self.assertEqual(result["partition"]["active_project_scope_hash"], "scope-1")

    def test_mcp_semantic_search_active_requires_partition_and_uses_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            fake_client = FakeChromaClient()
            chroma = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                chroma_client=fake_client,
            )
            adapters = ToolAdapters(
                active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations"),
                memory_service=MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma),
            )

            missing = adapters.call_mcp_tool("mcp_semantic_search_active", {"query": "hello"})
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
            result = adapters.call_mcp_tool("mcp_semantic_search_active", {"query": "hello", "k": 3})

            self.assertEqual(missing["status"], "NO_ACTIVE_PARTITION")
            self.assertTrue(result["ok"])
            self.assertEqual(fake_client.collection.queries[0]["where"], {"project_scope_hash": "scope-1"})

    def test_mcp_commit_memory_persists_record_and_indexes_scope(self):
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
            adapters = ToolAdapters(
                active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations"),
                memory_service=MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma),
            )

            result = adapters.call_mcp_tool(
                "mcp_commit_memory",
                {
                    "category": "decision",
                    "content": "This is a bounded memory record for the active partition.",
                    "metadata": {"source_note": "unit-test"},
                },
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["project_scope_hash"], "scope-1")
            self.assertEqual(fake_client.collection.upserts[0]["metadatas"][0]["project_scope_hash"], "scope-1")

    def test_mcp_set_active_partition_accepts_only_conversation_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            conversations = root / "conversations" / "client-a" / "backend-debug"
            conversations.mkdir(parents=True)
            conversation = conversations / "chat.conversation.json"
            conversation.write_text("{}", encoding="utf-8")
            adapters = ToolAdapters(
                active_partition=ActivePartitionService(ActivePartitionRepository(root / "queue.db"), conversations_root=root / "conversations", allowed_roots=(root,)),
                memory_service=MemoryService(
                    MemoryRepository(root / "queue.db"),
                    ActivePartitionRepository(root / "queue.db"),
                    ChromaManager(
                        ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                        http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                        chroma_client=FakeChromaClient(),
                    ),
                ),
            )

            blocked = adapters.call_mcp_tool("mcp_set_active_partition", {"project_id": "p"})
            result = adapters.call_mcp_tool("mcp_set_active_partition", {"conversation_path": str(conversation)})

            self.assertEqual(blocked["status"], "POLICY_BLOCK")
            self.assertTrue(result["ok"])
            self.assertEqual(result["partition"]["active_project_id"], "lmstudio-client-a-backend-debug")

    def test_mcp_set_active_project_manual_updates_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            active_repo = ActivePartitionRepository(root / "queue.db")
            adapters = ToolAdapters(
                active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations", allowed_roots=(root,)),
                memory_service=MemoryService(
                    MemoryRepository(root / "queue.db"),
                    active_repo,
                    ChromaManager(
                        ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                        http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                        chroma_client=FakeChromaClient(),
                    ),
                ),
            )

            result = adapters.call_mcp_tool(
                "mcp_set_active_project_manual",
                {"project_id": "lmstudio-client-a-backend-debug", "display_name": "client-a / backend-debug"},
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["partition"]["active_project_id"], "lmstudio-client-a-backend-debug")
