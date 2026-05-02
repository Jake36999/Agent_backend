from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Protocol

import yaml


class AdapterFailure(ValueError):
    pass


class SemanticMemoryAdapter(Protocol):
    def search(self, project_id: str, query: str, k: int) -> list[dict[str, object]]:
        ...

    def ingest_target(
        self,
        project_id: str,
        absolute_path: str,
        *,
        mime_type: str | None = None,
        force_reindex: bool = False,
    ) -> dict[str, object]:
        ...


class OCRProvider(Protocol):
    def extract_image_text(self, absolute_path: str, page: int | None, region: dict[str, int] | None) -> str:
        ...


class WorkspaceScoutAdapter(Protocol):
    def scout(
        self,
        project_id: str,
        absolute_path: str,
        *,
        max_files: int = 500,
        include_summaries: bool = True,
    ) -> dict[str, Any]:
        ...


class FileToolAdapter:
    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def _resolve(self, path: str) -> Path:
        resolved = Path(path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise AdapterFailure("path escapes allowed roots")
        return resolved

    def read_file(self, file_path: str) -> str:
        try:
            return self._resolve(file_path).read_text(encoding="utf-8", errors="replace")
        except AdapterFailure:
            raise
        except Exception as exc:
            raise AdapterFailure(f"read_file failed: {exc}") from exc

    def read_file_snippet(self, file_path: str, start_line: int, end_line: int) -> str:
        if start_line < 1 or end_line < start_line:
            raise AdapterFailure("invalid line range")
        lines = self.read_file(file_path).splitlines(keepends=True)
        return "".join(lines[start_line - 1:end_line])

    def list_directory(self, directory_path: str) -> list[str]:
        try:
            return sorted(os.listdir(self._resolve(directory_path)))
        except AdapterFailure:
            raise
        except Exception as exc:
            raise AdapterFailure(f"list_directory failed: {exc}") from exc

    def package_directory(self, directory_path: str) -> str:
        root = self._resolve(directory_path)
        tree: dict[str, Any] = {}
        try:
            for current, dirs, files in os.walk(root):
                dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"})
                rel_root = os.path.relpath(current, root)
                subtree = tree
                if rel_root != ".":
                    for part in rel_root.split(os.sep):
                        subtree = subtree.setdefault(part, {})
                subtree["files"] = sorted(files)
            return yaml.dump(tree, sort_keys=False)
        except Exception as exc:
            raise AdapterFailure(f"package_directory failed: {exc}") from exc

    def verify_integrity(self, absolute_path: str, expected_sha256: str, expected_metadata_hash: str) -> dict[str, Any]:
        path = self._resolve(absolute_path)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            stat = path.stat()
            metadata = {
                "file_sha256": digest,
                "file_name": path.name,
                "absolute_path": str(path),
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
            metadata_hash = hashlib.sha256(
                json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        except Exception as exc:
            raise AdapterFailure(f"verify_integrity failed: {exc}") from exc
        return {
            "ok": digest.lower() == expected_sha256.lower() and metadata_hash == expected_metadata_hash,
            "sha256": digest,
            "metadata_hash": metadata_hash,
            "metadata": metadata,
        }


class ReadOnlySqliteAdapter:
    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def _resolve(self, db_path: str) -> Path:
        resolved = Path(db_path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise AdapterFailure("database path escapes allowed roots")
        return resolved

    def query(self, db_path: str, query: str, *, row_limit: int = 100) -> list[dict[str, Any]]:
        normalized = query.strip().lower()
        if ";" in query:
            raise AdapterFailure("semicolons are not allowed")
        if normalized.startswith("--") or normalized.startswith("/*"):
            raise AdapterFailure("leading comments are not allowed")
        if normalized.startswith("with"):
            raise AdapterFailure("WITH statements are not allowed")
        if not normalized.startswith("select"):
            raise AdapterFailure("only SELECT queries are allowed")
        forbidden = ("pragma", "attach", "detach", "insert", "update", "delete", "drop", "alter")
        if any(token in normalized.split() for token in forbidden):
            raise AdapterFailure("query contains a forbidden operation")
        if row_limit < 1 or row_limit > 1000:
            raise AdapterFailure("row_limit must be between 1 and 1000")
        uri = self._resolve(db_path).as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            cursor = conn.execute(f"SELECT * FROM ({query}) LIMIT ?", (row_limit,))
            columns = [column[0] for column in cursor.description or []]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as exc:
            raise AdapterFailure(f"sqlite query failed: {exc}") from exc
        finally:
            conn.close()


class ToolAdapters:
    def __init__(
        self,
        *,
        semantic_memory: SemanticMemoryAdapter | None = None,
        file_tools: FileToolAdapter | None = None,
        sqlite_tools: ReadOnlySqliteAdapter | None = None,
        workspace_scout: WorkspaceScoutAdapter | None = None,
        ocr_provider: OCRProvider | None = None,
    ) -> None:
        self.semantic_memory = semantic_memory
        self.file_tools = file_tools
        self.sqlite_tools = sqlite_tools
        self.workspace_scout = workspace_scout
        self.ocr_provider = ocr_provider

    def call_mcp_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            if tool_name == "mcp_semantic_search":
                if self.semantic_memory is None:
                    raise AdapterFailure("semantic memory adapter is not configured")
                return {
                    "ok": True,
                    "results": self.semantic_memory.search(
                        str(args["project_id"]),
                        str(args["query"]),
                        int(args.get("k", 8)),
                    ),
                }
            if tool_name == "mcp_ingest_target":
                if self.semantic_memory is None:
                    raise AdapterFailure("semantic memory adapter is not configured")
                return {
                    "ok": True,
                    "result": self.semantic_memory.ingest_target(
                        str(args["project_id"]),
                        str(args["absolute_path"]),
                        mime_type=args.get("mime_type"),
                        force_reindex=bool(args.get("force_reindex", False)),
                    ),
                }
            if tool_name == "mcp_scout_workspace":
                if self.workspace_scout is None:
                    raise AdapterFailure("workspace scout adapter is not configured")
                return {
                    "ok": True,
                    "result": self.workspace_scout.scout(
                        str(args["project_id"]),
                        str(args["absolute_path"]),
                        max_files=int(args.get("max_files", 500)),
                        include_summaries=bool(args.get("include_summaries", True)),
                    ),
                }
            if tool_name == "mcp_verify_integrity":
                if self.file_tools is None:
                    raise AdapterFailure("file tools adapter is not configured")
                return {
                    "ok": True,
                    "result": self.file_tools.verify_integrity(
                        str(args["absolute_path"]),
                        str(args["expected_sha256"]),
                        str(args["expected_metadata_hash"]),
                    ),
                }
            if tool_name == "mcp_extract_image":
                if self.ocr_provider is None:
                    raise AdapterFailure("OCR provider is not configured")
                return {
                    "ok": True,
                    "text": self.ocr_provider.extract_image_text(
                        str(args["absolute_path"]),
                        args.get("page"),
                        args.get("region"),
                    ),
                }
            raise AdapterFailure(f"unknown MCP tool: {tool_name}")
        except KeyError as exc:
            raise AdapterFailure(f"missing required argument: {exc}") from exc
        except ValueError as exc:
            if isinstance(exc, AdapterFailure):
                raise
            raise AdapterFailure(str(exc)) from exc
