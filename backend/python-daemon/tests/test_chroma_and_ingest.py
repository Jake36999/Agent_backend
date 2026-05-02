import tempfile
import unittest
from pathlib import Path

from orchestrator.chroma_manager import ChromaAdapterError, ChromaConfig, ChromaManager
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.ingest.service import IngestTargetService
from orchestrator.queue_repo import QueueRepository


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeCollection:
    def __init__(self):
        self.upserts = []
        self.queries = []
        self.deletes = []
        self.rows = {}

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)
        for index, chunk_id in enumerate(kwargs["ids"]):
            self.rows[chunk_id] = {
                "document": kwargs["documents"][index],
                "metadata": kwargs["metadatas"][index],
                "embedding": kwargs["embeddings"][index],
            }

    def delete(self, **kwargs):
        self.deletes.append(kwargs)
        where = kwargs["where"]
        stale = [
            chunk_id
            for chunk_id, row in self.rows.items()
            if all(row["metadata"].get(key) == value for key, value in where.items())
        ]
        for chunk_id in stale:
            del self.rows[chunk_id]

    def query(self, **kwargs):
        self.queries.append(kwargs)
        matches = [
            (chunk_id, row)
            for chunk_id, row in self.rows.items()
            if all(row["metadata"].get(key) == value for key, value in kwargs["where"].items())
        ]
        if matches:
            return {
                "ids": [[chunk_id for chunk_id, _ in matches]],
                "documents": [[row["document"] for _, row in matches]],
                "metadatas": [[row["metadata"] for _, row in matches]],
                "distances": [[0.1 for _ in matches]],
            }
        return {
            "ids": [["chunk-1"]],
            "documents": [["hello world"]],
            "metadatas": [[{"project_scope_hash": kwargs["where"]["project_scope_hash"]}]],
            "distances": [[0.1]],
        }


class FakeChromaClient:
    def __init__(self):
        self.collection = FakeCollection()

    def get_or_create_collection(self, name):
        self.name = name
        return self.collection


class ChromaAndIngestTests(unittest.TestCase):
    def test_embedding_payload_uses_lm_studio_model_and_nomic_prefix(self):
        calls = []

        def post(url, json, timeout):
            calls.append((url, json, timeout))
            return FakeResponse({"data": [{"embedding": [1, 2, 3]}]})

        manager = ChromaManager(
            ChromaConfig(chroma_path=Path("unused"), lm_studio_base_url="http://lm/v1"),
            http_post=post,
            chroma_client=FakeChromaClient(),
        )

        self.assertEqual(manager.embed_text("abc"), [1.0, 2.0, 3.0])
        self.assertEqual(calls[0][0], "http://lm/v1/embeddings")
        self.assertEqual(calls[0][1]["input"], "search_document: abc")

    def test_search_enforces_project_scope_hash_where_filter(self):
        fake_client = FakeChromaClient()
        manager = ChromaManager(
            ChromaConfig(chroma_path=Path("unused")),
            http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1]}]}),
            chroma_client=fake_client,
        )

        results = manager.search("project-a", "hello", k=3)

        query = fake_client.collection.queries[0]
        self.assertEqual(query["where"], {"project_scope_hash": manager.project_scope_hash("project-a")})
        self.assertEqual(query["n_results"], 3)
        self.assertEqual(results[0]["content"], "hello world")

    def test_ingest_service_records_sqlite_manifest_and_upserts_chroma(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.py"
            source.write_text("def alpha():\n    return 1\n", encoding="utf-8")
            fake_client = FakeChromaClient()
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2, 0.3]}]}),
                chroma_client=fake_client,
            )
            repo = QueueRepository(root / "queue.db", root / "control.db")
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            result = service.ingest_target("project-a", str(source))

            self.assertEqual(result["chunks_indexed"], 1)
            upsert = fake_client.collection.upserts[0]
            self.assertEqual(upsert["metadatas"][0]["project_id"], "project-a")
            self.assertEqual(upsert["metadatas"][0]["processor"], "semantic_slicer")
            chunks = repo.list_chunks("project-a")
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0]["processor"], "semantic_slicer")

    def test_file_manifest_key_allows_same_file_hash_in_multiple_project_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("shared content", encoding="utf-8")
            repo = QueueRepository(root / "queue.db", root / "control.db")

            for project_id in ("project-a", "project-b"):
                manager = ChromaManager(
                    ChromaConfig(chroma_path=root / f"chroma-{project_id}"),
                    http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                    chroma_client=FakeChromaClient(),
                )
                IngestTargetService(repo, manager, allowed_roots=(root,)).ingest_target(project_id, str(source))

            self.assertEqual(repo.count_file_manifests(), 2)

    def test_force_reindex_removes_stale_sqlite_chunks_and_chroma_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("old content that is long enough", encoding="utf-8")
            fake_client = FakeChromaClient()
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                chroma_client=fake_client,
            )
            repo = QueueRepository(root / "queue.db", root / "control.db")
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            service.ingest_target("project-a", str(source))
            source.write_text("new content that replaces the old content", encoding="utf-8")
            service.ingest_target("project-a", str(source), force_reindex=True)

            chunks = repo.list_chunks("project-a")
            self.assertEqual(len(chunks), 1)
            self.assertIn("new content", chunks[0]["content"])
            results = manager.search("project-a", "content", k=10)
            self.assertEqual(len(results), 1)
            self.assertIn("new content", results[0]["content"])
            self.assertTrue(fake_client.collection.deletes)

    def test_unchanged_file_skips_reindex_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("same content", encoding="utf-8")
            fake_client = FakeChromaClient()
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                chroma_client=fake_client,
            )
            repo = QueueRepository(root / "queue.db", root / "control.db")
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            first = service.ingest_target("project-a", str(source))
            second = service.ingest_target("project-a", str(source))

            self.assertEqual(first["chunks_indexed"], 1)
            self.assertEqual(second["chunks_indexed"], 0)
            self.assertEqual(second["files_skipped"], 1)
            self.assertEqual(len(fake_client.collection.upserts), 1)

    def test_changed_file_reindexes_without_force_and_removes_stale_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("old content", encoding="utf-8")
            fake_client = FakeChromaClient()
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                chroma_client=fake_client,
            )
            repo = QueueRepository(root / "queue.db", root / "control.db")
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            service.ingest_target("project-a", str(source))
            source.write_text("brand new content", encoding="utf-8")
            second = service.ingest_target("project-a", str(source))

            chunks = repo.list_chunks("project-a")
            self.assertEqual(second["chunks_indexed"], 1)
            self.assertEqual(len(chunks), 1)
            self.assertIn("brand new content", chunks[0]["content"])
            self.assertTrue(fake_client.collection.deletes)

    def test_directory_ingest_removes_deleted_file_manifests_and_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            first = root / "a.txt"
            second = root / "b.txt"
            first.write_text("alpha", encoding="utf-8")
            second.write_text("beta", encoding="utf-8")
            fake_client = FakeChromaClient()
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                chroma_client=fake_client,
            )
            repo = QueueRepository(root / "queue.db", root / "control.db")
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            service.ingest_target("project-a", str(root))
            second.unlink()
            result = service.ingest_target("project-a", str(root))

            paths = {chunk["absolute_path"] for chunk in repo.list_chunks("project-a")}
            self.assertEqual(result["files_removed"], 1)
            self.assertEqual(paths, {str(first.resolve())})

    def test_rebuild_chroma_from_sqlite_chunk_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("rebuild me", encoding="utf-8")
            repo = QueueRepository(root / "queue.db", root / "control.db")
            first = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.4]}]}),
                chroma_client=FakeChromaClient(),
            )
            service = IngestTargetService(repo, first, allowed_roots=(root,))
            service.ingest_target("project-a", str(source))
            rebuilt = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma2"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.5]}]}),
                chroma_client=FakeChromaClient(),
            )

            result = rebuilt.rebuild_from_chunks("project-a", repo.chunks_for_rebuild("project-a"))

            self.assertEqual(result["chunks_indexed"], 1)
            self.assertEqual(rebuilt.search("project-a", "rebuild", k=5)[0]["content"], "rebuild me")

    def test_failed_vector_upsert_preserves_sqlite_chunks_for_reconciliation(self):
        class BrokenUpsertCollection(FakeCollection):
            def upsert(self, **kwargs):
                raise RuntimeError("vector store unavailable")

        class BrokenUpsertClient(FakeChromaClient):
            def __init__(self):
                self.collection = BrokenUpsertCollection()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("keep this chunk", encoding="utf-8")
            repo = QueueRepository(root / "queue.db", root / "control.db")
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.6]}]}),
                chroma_client=BrokenUpsertClient(),
            )
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            with self.assertRaises(ChromaAdapterError):
                service.ingest_target("project-a", str(source))

            run = repo.latest_ingestion_run("project-a")
            self.assertEqual(run["state"], "FAILED_VECTOR_UPSERT")
            rebuildable = repo.list_rebuildable_chunks("project-a")
            self.assertEqual(len(rebuildable), 1)
            self.assertEqual(rebuildable[0]["content"], "keep this chunk")

    def test_rebuild_chroma_for_project_uses_rebuildable_chunks(self):
        class BrokenOnceCollection(FakeCollection):
            def __init__(self):
                super().__init__()
                self.fail = True

            def upsert(self, **kwargs):
                if self.fail:
                    self.fail = False
                    raise RuntimeError("first upsert fails")
                super().upsert(**kwargs)

        class BrokenOnceClient(FakeChromaClient):
            def __init__(self):
                self.collection = BrokenOnceCollection()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "sample.txt"
            source.write_text("restore me", encoding="utf-8")
            repo = QueueRepository(root / "queue.db", root / "control.db")
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.7]}]}),
                chroma_client=BrokenOnceClient(),
            )
            service = IngestTargetService(repo, manager, allowed_roots=(root,))
            with self.assertRaises(ChromaAdapterError):
                service.ingest_target("project-a", str(source))

            result = service.rebuild_chroma_for_project("project-a")

            self.assertEqual(result["chunks_indexed"], 1)
            self.assertEqual(repo.latest_ingestion_run("project-a")["state"], "RECONCILED")
            self.assertEqual(manager.search("project-a", "restore", k=5)[0]["content"], "restore me")

    def test_chroma_failures_raise_formal_value_error(self):
        class BrokenCollection(FakeCollection):
            def query(self, **kwargs):
                raise RuntimeError("chroma down")

        class BrokenClient(FakeChromaClient):
            def __init__(self):
                self.collection = BrokenCollection()

        manager = ChromaManager(
            ChromaConfig(chroma_path=Path("unused")),
            http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1]}]}),
            chroma_client=BrokenClient(),
        )

        with self.assertRaises(ChromaAdapterError):
            manager.search("project-a", "hello")


if __name__ == "__main__":
    unittest.main()
