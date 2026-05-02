import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from orchestrator.adapters import AdapterFailure, FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters
from orchestrator.chroma_manager import ChromaConfig, ChromaManager
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.ingest.processors import MetadataAdapter, SemanticSlicerAdapter, TextProcessorAdapter, WorkspaceScout
from orchestrator.ingest.service import IngestTargetService
from orchestrator.queue_repo import QueueRepository
from orchestrator.ocr import CommandOCRProvider
from orchestrator.shell import CommandSpec, ShellAdapter


class ProcessorAndToolTests(unittest.TestCase):
    def test_text_processor_uses_deterministic_overlap(self):
        processor = TextProcessorAdapter(chunk_size=5, chunk_overlap=2)
        chunks = processor.process_text("abcdefghij", file_path="a.txt", file_name="a.txt")

        self.assertEqual([chunk.content for chunk in chunks], ["abcde", "defgh", "ghij"])
        self.assertEqual(chunks[1].metadata["chunk_index"], 1)

    def test_semantic_slicer_emits_stable_function_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("import os\n\ndef alpha(x):\n    return x + 1\n", encoding="utf-8")

            chunks = SemanticSlicerAdapter().process_file(path)

            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].metadata["processor"], "semantic_slicer")
            self.assertEqual(chunks[0].metadata["symbol_name"], "alpha")
            self.assertIn("sample.py::alpha@", chunks[0].metadata["slice_id"])

    def test_metadata_adapter_hashes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_text("abc", encoding="utf-8")

            metadata = MetadataAdapter().extract(path)

            self.assertEqual(metadata["file_name"], "a.txt")
            self.assertEqual(len(metadata["file_sha256"]), 64)
            self.assertEqual(len(metadata["metadata_hash"]), 64)

    def test_workspace_scout_is_deterministic_and_reports_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
            (root / "image.png").write_bytes(b"\x00")
            (root / "cache.db").write_bytes(b"sqlite bytes")
            (root / "paper.pdf").write_bytes(b"%PDF")
            (root / "model.h5").write_bytes(b"heavy")
            bundle_dir = root / "New project_bundle_123"
            bundle_dir.mkdir()
            (bundle_dir / "generated_bundle.py").write_text("print('skip')\n", encoding="utf-8")

            first = WorkspaceScout(allowed_roots=(root,)).scout("project-a", str(root), include_summaries=True)
            second = WorkspaceScout(allowed_roots=(root,)).scout("project-a", str(root), include_summaries=True)

            self.assertEqual(first["package_hash"], second["package_hash"])
            self.assertEqual(first["file_count"], 1)
            self.assertGreaterEqual(first["skipped_count"], 4)
            self.assertGreaterEqual(first["skipped_details"]["ignored_extension"], 4)

    def test_file_tools_enforce_allowed_roots_and_verify_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "a.txt"
            path.write_text("abc", encoding="utf-8")
            tools = FileToolAdapter((root,))
            expected = MetadataAdapter().extract(path)

            self.assertEqual(tools.read_file_snippet(str(path), 1, 1), "abc")
            result = tools.verify_integrity(str(path), expected["file_sha256"], expected["metadata_hash"])
            self.assertTrue(result["ok"])

            with self.assertRaises(AdapterFailure):
                tools.read_file(str(Path(tmp).parent / "outside.txt"))

    def test_shell_adapter_sync_run_uses_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = ShellAdapter((root,))
            spec = CommandSpec(
                executable=sys.executable,
                args=("-c", "print('ok')"),
                cwd=str(root),
            )
            rc, stdout, stderr = shell.sync_run(spec)

            self.assertEqual(rc, 0)
            self.assertIn("ok", stdout)
            self.assertEqual(stderr, "")

    def test_read_only_sqlite_rejects_non_select(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("CREATE TABLE items(id INTEGER)")
                conn.execute("INSERT INTO items(id) VALUES (1)")
                conn.commit()

            adapter = ReadOnlySqliteAdapter((Path(tmp),))

            self.assertEqual(adapter.query(str(db), "SELECT id FROM items", row_limit=1)[0]["id"], 1)
            with self.assertRaises(AdapterFailure):
                adapter.query(str(db), "DELETE FROM items")
            with self.assertRaises(AdapterFailure):
                adapter.query(str(db), "SELECT id FROM items; SELECT id FROM items")

    def test_read_only_sqlite_applies_row_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("CREATE TABLE items(id INTEGER)")
                conn.executemany("INSERT INTO items(id) VALUES (?)", [(1,), (2,), (3,)])
                conn.commit()

            rows = ReadOnlySqliteAdapter((Path(tmp),)).query(str(db), "SELECT id FROM items ORDER BY id", row_limit=2)

            self.assertEqual([row["id"] for row in rows], [1, 2])

    def test_js_and_ts_fall_back_to_text_chunking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            source = root / "app.ts"
            source.write_text("export const value = 1;\n", encoding="utf-8")
            manager = ChromaManager(
                ChromaConfig(chroma_path=root / "chroma"),
                http_post=lambda **_: FakeResponseForTools({"data": [{"embedding": [0.1]}]}),
                chroma_client=FakeChromaClientForTools(),
            )
            repo = QueueRepository(root / "queue.db", root / "control.db")
            service = IngestTargetService(repo, manager, allowed_roots=(root,))

            service.ingest_target("project-a", str(source))

            self.assertEqual(repo.list_chunks("project-a")[0]["processor"], "text")

    def test_tool_adapters_route_scout_workspace_and_sqlite(self):
        class FakeScout:
            def scout(self, project_id, absolute_path, max_files=500, include_summaries=True):
                return {"project_id": project_id, "absolute_path": absolute_path, "max_files": max_files}

        adapters = ToolAdapters(workspace_scout=FakeScout())

        result = adapters.call_mcp_tool(
            "mcp_scout_workspace",
            {"project_id": "p", "absolute_path": "x", "max_files": 2},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["max_files"], 2)

    def test_ocr_disabled_and_enabled_adapter_paths(self):
        with self.assertRaises(AdapterFailure):
            ToolAdapters().call_mcp_tool("mcp_extract_image", {"absolute_path": "x"})

        calls = []

        def runner(command, args, timeout):
            calls.append((command, args, timeout))
            return "detected text"

        with tempfile.TemporaryDirectory() as tmp:
            shell = ShellAdapter((Path(tmp),))
            provider = CommandOCRProvider(shell_adapter=shell, command="ocr-bin", runner=runner)
            result = ToolAdapters(ocr_provider=provider).call_mcp_tool(
                "mcp_extract_image",
                {"absolute_path": "image.png", "page": 2, "region": {"x": 1}},
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["text"], "detected text")
            self.assertEqual(calls[0][0], "ocr-bin")

    def test_sqlite_adapter_rejects_comments_with_hidden_writes_and_with_statements(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("CREATE TABLE items(id INTEGER)")
                conn.execute("INSERT INTO items(id) VALUES (1)")
                conn.commit()

            adapter = ReadOnlySqliteAdapter((Path(tmp),))

            with self.assertRaises(AdapterFailure):
                adapter.query(str(db), "-- comment\nSELECT id FROM items")
            with self.assertRaises(AdapterFailure):
                adapter.query(str(db), "WITH rows AS (SELECT id FROM items) SELECT id FROM rows")


if __name__ == "__main__":
    unittest.main()


class FakeResponseForTools:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeChromaClientForTools:
    def get_or_create_collection(self, name):
        class Collection:
            def upsert(self, **kwargs):
                return None

        return Collection()
