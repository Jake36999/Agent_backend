from __future__ import annotations

import ast
import hashlib
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class IngestProcessorError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    metadata: dict[str, Any]


class OCRProvider(Protocol):
    def extract_pdf_page_text(self, absolute_path: str, page_number: int) -> str:
        ...


class MetadataAdapter:
    def extract(self, path: Path) -> dict[str, Any]:
        resolved = path.resolve()
        if not resolved.exists() or not resolved.is_file():
            raise IngestProcessorError(f"file does not exist: {path}")
        stat = resolved.stat()
        file_sha256 = self.file_sha256(resolved)
        metadata = {
            "file_sha256": file_sha256,
            "file_name": resolved.name,
            "absolute_path": str(resolved),
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
        metadata["metadata_hash"] = hashlib.sha256(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return metadata

    def file_sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(8192), b""):
                    digest.update(block)
        except Exception as exc:
            raise IngestProcessorError(f"hash generation failed: {exc}") from exc
        return digest.hexdigest()


class TextProcessorAdapter:
    def __init__(self, *, chunk_size: int = 1500, chunk_overlap: int = 200) -> None:
        if chunk_overlap >= chunk_size:
            raise IngestProcessorError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, path: Path) -> list[DocumentChunk]:
        try:
            raw_text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            raise IngestProcessorError(f"text read failed: {exc}") from exc
        return self.process_text(raw_text, file_path=str(path.resolve()), file_name=path.name)

    def process_text(self, text: str, *, file_path: str, file_name: str) -> list[DocumentChunk]:
        if not text.strip():
            return []
        chunks: list[DocumentChunk] = []
        start = 0
        chunk_index = 0
        step = self.chunk_size - self.chunk_overlap
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            content = text[start:end]
            if chunk_index > 0 and len(content) <= self.chunk_overlap:
                break
            chunks.append(
                DocumentChunk(
                    content=content,
                    metadata={
                        "absolute_path": file_path,
                        "file_name": file_name,
                        "file_type": "text",
                        "processor": "text",
                        "page_number": 0,
                        "chunk_index": chunk_index,
                    },
                )
            )
            start += step
            chunk_index += 1
        return chunks


class PdfProcessorAdapter:
    def __init__(self, *, ocr_provider: OCRProvider | None = None, text_density_threshold: int = 50) -> None:
        self.ocr_provider = ocr_provider
        self.text_density_threshold = text_density_threshold
        self.text_fallback = TextProcessorAdapter()

    def process_file(self, path: Path) -> list[DocumentChunk]:
        try:
            import fitz
        except Exception as exc:
            raise IngestProcessorError("PDF ingestion requires PyMuPDF/fitz") from exc
        chunks: list[DocumentChunk] = []
        try:
            doc = fitz.open(path)
            for page_index, page in enumerate(doc, start=1):
                raw_text = page.get_text()
                if len(raw_text.strip()) < self.text_density_threshold and self.ocr_provider is not None:
                    ocr_text = self.ocr_provider.extract_pdf_page_text(str(path.resolve()), page_index)
                    if len(ocr_text.strip()) > len(raw_text.strip()):
                        raw_text = ocr_text
                for chunk in self.text_fallback.process_text(
                    raw_text,
                    file_path=str(path.resolve()),
                    file_name=path.name,
                ):
                    metadata = dict(chunk.metadata)
                    metadata["file_type"] = "pdf"
                    metadata["processor"] = "pdf"
                    metadata["page_number"] = page_index
                    chunks.append(DocumentChunk(chunk.content, metadata))
            doc.close()
        except Exception as exc:
            raise IngestProcessorError(f"PDF processing failed: {exc}") from exc
        return chunks


class SemanticSlicerAdapter:
    def process_file(self, path: Path) -> list[DocumentChunk]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise IngestProcessorError(f"syntax error at line {exc.lineno}: {exc.msg}") from exc
        except Exception as exc:
            raise IngestProcessorError(f"semantic slicing failed: {exc}") from exc
        lines = source.splitlines()
        chunks: list[DocumentChunk] = []
        rel_name = path.name
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            start = int(getattr(node, "lineno", 1))
            end = int(getattr(node, "end_lineno", start))
            body = "\n".join(lines[start - 1:end])
            node_dump = ast.dump(node, annotate_fields=False, include_attributes=False)
            body_hash = hashlib.sha1(node_dump.encode("utf-8", errors="ignore")).hexdigest()[:10]
            calls = sorted(
                {
                    self._call_name(child)
                    for child in ast.walk(node)
                    if isinstance(child, ast.Call) and self._call_name(child)
                }
            )
            chunk_index = len(chunks)
            chunks.append(
                DocumentChunk(
                    content=body,
                    metadata={
                        "absolute_path": str(path.resolve()),
                        "file_name": path.name,
                        "file_type": "code",
                        "processor": "semantic_slicer",
                        "chunk_index": chunk_index,
                        "symbol_name": node.name,
                        "symbol_type": type(node).__name__,
                        "start_line": start,
                        "end_line": end,
                        "slice_id": f"{rel_name}::{node.name}@{body_hash}",
                        "calls_json": json.dumps(calls),
                    },
                )
            )
        return chunks

    def _call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None


class WorkspaceScout:
    ignore_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".idea", ".vscode", "dist", "build"}
    ignore_exts = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".tiff",
        ".zip", ".gz", ".tar", ".tgz", ".bz2", ".xz", ".7z", ".rar",
        ".exe", ".dll", ".so", ".dylib", ".pdf", ".bin", ".class",
        ".pyc", ".sqlite", ".sqlite3", ".db", ".h5", ".hdf5", ".parquet",
    }

    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def scout(
        self,
        project_id: str,
        absolute_path: str,
        *,
        max_files: int = 500,
        include_summaries: bool = True,
    ) -> dict[str, Any]:
        root = self._resolve(absolute_path)
        if not root.is_dir():
            raise IngestProcessorError("workspace scout target must be a directory")
        files: list[dict[str, Any]] = []
        skipped = 0
        skipped_details = {"ignored_extension": 0, "binary": 0, "oversize": 0, "errors": 0}
        for current, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in self.ignore_dirs and not d.startswith("."))
            for name in sorted(names):
                path = Path(current) / name
                if len(files) >= max_files:
                    skipped += 1
                    skipped_details["oversize"] += 1
                    continue
                if path.suffix.lower() in self.ignore_exts:
                    skipped += 1
                    skipped_details["ignored_extension"] += 1
                    continue
                if path.stat().st_size > 1_500_000:
                    skipped += 1
                    skipped_details["oversize"] += 1
                    continue
                if self._is_binary(path):
                    skipped += 1
                    skipped_details["binary"] += 1
                    continue
                try:
                    raw = path.read_text(encoding="utf-8", errors="ignore")
                    rel = path.relative_to(root).as_posix()
                    entry: dict[str, Any] = {
                        "path": rel,
                        "size_bytes": path.stat().st_size,
                        "sha256": MetadataAdapter().file_sha256(path),
                    }
                    if include_summaries:
                        entry["summary"] = self._summary(path, raw)
                    files.append(entry)
                except Exception:
                    skipped += 1
                    skipped_details["errors"] += 1
        files.sort(key=lambda item: item["path"])
        tree = self._tree(root, files)
        payload = {"project_id": project_id, "root": str(root), "tree": tree, "files": files, "skipped_count": skipped}
        package_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return {
            "project_id": project_id,
            "absolute_path": str(root),
            "tree": tree,
            "file_count": len(files),
            "skipped_count": skipped,
            "files": files,
            "package_hash": package_hash,
            "skipped_details": skipped_details,
        }

    def _resolve(self, path: str) -> Path:
        resolved = Path(path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise IngestProcessorError("path escapes allowed roots")
        return resolved

    def _is_binary(self, path: Path, scan_bytes: int = 2048) -> bool:
        try:
            sample = path.read_bytes()[:scan_bytes]
        except Exception:
            return True
        if b"\x00" in sample:
            return True
        guess, _ = mimetypes.guess_type(str(path))
        return bool(guess and not guess.startswith(("text", "application")))

    def _summary(self, path: Path, raw: str) -> dict[str, Any]:
        if path.suffix.lower() == ".py":
            try:
                tree = ast.parse(raw)
            except SyntaxError:
                return {"syntax_valid": False}
            return {
                "syntax_valid": True,
                "functions": [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)][:20],
                "classes": [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)][:20],
            }
        if path.suffix.lower() in {".md", ".markdown"}:
            return {"headers": re.findall(r"^#{1,3}\s+(.*)", raw, re.MULTILINE)[:20]}
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
                return {"keys": list(data.keys())[:20] if isinstance(data, dict) else ["<array>"]}
            except json.JSONDecodeError:
                return {"syntax_valid": False}
        return {}

    def _tree(self, root: Path, files: list[dict[str, Any]]) -> str:
        lines = [f"{root.name}/"]
        seen_dirs: set[str] = set()
        for entry in files:
            parts = Path(entry["path"]).parts
            for index, part in enumerate(parts[:-1]):
                directory = str(Path(*parts[: index + 1]))
                if directory not in seen_dirs:
                    lines.append(f"{'  ' * (index + 1)}|-- {part}/")
                    seen_dirs.add(directory)
            lines.append(f"{'  ' * len(parts)}|-- {parts[-1]}")
        return "\n".join(lines)
