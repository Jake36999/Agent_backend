from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .dependency_extractor import DependencyExtractor
from .mermaid_formatter import format_mermaid
from .models import CodeMapEntry, DependencyGraph

_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".env",
    "dist", "build", ".cache", ".mypy_cache", ".pytest_cache",
    "coverage", ".tox", "eggs", ".eggs",
}

_LANGUAGE_MAP: dict[str, str] = {
    "py": "python",
    "js": "javascript", "mjs": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "json": "json",
    "yaml": "yaml", "yml": "yaml",
    "md": "markdown", "rst": "markdown",
    "toml": "config", "ini": "config", "cfg": "config", "env": "config",
    "sh": "shell", "bash": "shell",
    "sql": "sql",
    "html": "html", "htm": "html",
    "css": "css", "scss": "css",
}


class CodeIntelligenceError(ValueError):
    pass


def _detect_language(name: str) -> str:
    if "." not in name:
        return "other"
    ext = name.rsplit(".", 1)[-1].lower()
    return _LANGUAGE_MAP.get(ext, "other")


def _count_lines(path: Path) -> int:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
    except Exception:
        return 0


class CodeIntelligenceAnalyzer:

    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(r.resolve() for r in allowed_roots)

    def _resolve(self, path: str) -> Path:
        resolved = Path(path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise CodeIntelligenceError("path escapes allowed roots")
        return resolved

    def analyze(
        self,
        target_repo: str,
        mode: str,
        *,
        max_files: int = 500,
        max_edges: int = 500,
        max_chars: int = 8000,
        focus_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        root = self._resolve(target_repo)
        if not root.is_dir():
            raise CodeIntelligenceError(f"not a directory: {target_repo}")

        entries, truncated_scan = self._scan(root, max_files, focus_paths)

        if mode == "code_map":
            return self._code_map(entries, truncated_scan)
        if mode == "dependency_graph":
            return self._dependency_graph(root, entries, max_edges)
        if mode == "repo_context":
            return self._repo_context(root, entries, max_chars)
        if mode == "mermaid":
            graph = self._build_graph(root, entries, max_edges)
            diagram = format_mermaid(graph)
            return {
                "ok": True,
                "mode": "mermaid",
                "diagram": diagram,
                "node_count": len(graph.nodes),
                "edge_count": len([e for e in graph.edges if not e.is_external]),
                "truncated": graph.truncated,
                "artifacts": {"dependency_graph_mmd": diagram},
            }
        raise CodeIntelligenceError(f"unknown mode: {mode}")

    def _scan(
        self,
        root: Path,
        max_files: int,
        focus_paths: list[str] | None,
    ) -> tuple[list[CodeMapEntry], bool]:
        focus_set: set[str] | None = (
            {fp.replace("\\", "/").strip("/") for fp in focus_paths} if focus_paths else None
        )
        entries: list[CodeMapEntry] = []
        truncated = False

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
            rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            for fname in sorted(filenames):
                rel = f"{rel_dir}/{fname}".lstrip("/") if rel_dir else fname
                if focus_set and not any(rel.startswith(fp) for fp in focus_set):
                    continue
                abs_path = Path(dirpath) / fname
                lang = _detect_language(fname)
                try:
                    size = abs_path.stat().st_size
                except OSError:
                    size = 0
                lines = _count_lines(abs_path)
                entries.append(CodeMapEntry(rel_path=rel, language=lang, size_bytes=size, line_count=lines))
                if len(entries) >= max_files:
                    truncated = True
                    return entries, truncated

        return entries, truncated

    def _code_map(self, entries: list[CodeMapEntry], truncated: bool) -> dict[str, Any]:
        lang_counts: dict[str, int] = {}
        for e in entries:
            lang_counts[e.language] = lang_counts.get(e.language, 0) + 1
        total_lines = sum(e.line_count for e in entries)
        lang_summary = ", ".join(f"{k}:{v}" for k, v in sorted(lang_counts.items(), key=lambda x: -x[1]))
        artifact_summary = (
            f"{len(entries)} files, {total_lines:,} lines"
            + (f" [truncated]" if truncated else "")
            + (f" | {lang_summary}" if lang_summary else "")
        )[:2000]
        return {
            "ok": True,
            "mode": "code_map",
            "files": [
                {
                    "path": e.rel_path,
                    "language": e.language,
                    "size_bytes": e.size_bytes,
                    "line_count": e.line_count,
                }
                for e in entries
            ],
            "summary": {
                "total_files": len(entries),
                "total_lines": total_lines,
                "languages": lang_counts,
            },
            "truncated": truncated,
            "artifacts": {"code_map_summary": artifact_summary},
        }

    def _build_graph(
        self, root: Path, entries: list[CodeMapEntry], max_edges: int
    ) -> DependencyGraph:
        all_rel = [e.rel_path for e in entries]
        extractor = DependencyExtractor(all_rel)
        graph = DependencyGraph(nodes=[], edges=[])
        internal_set = set(all_rel)

        for entry in entries:
            if entry.language not in ("python", "javascript", "typescript"):
                continue
            abs_path = root / entry.rel_path
            try:
                source = abs_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for edge in extractor.extract(entry.rel_path, source):
                if not edge.is_external and edge.target not in internal_set:
                    continue
                graph.edges.append(edge)
                if len(graph.edges) >= max_edges:
                    graph.truncated = True
                    break
            if graph.truncated:
                break

        # Nodes = all internal files that appear in at least one edge, plus all parsed files
        referenced: set[str] = set()
        for edge in graph.edges:
            if not edge.is_external:
                referenced.add(edge.source)
                referenced.add(edge.target)
        graph.nodes = sorted(referenced & internal_set)
        return graph

    def _dependency_graph(
        self, root: Path, entries: list[CodeMapEntry], max_edges: int
    ) -> dict[str, Any]:
        graph = self._build_graph(root, entries, max_edges)
        artifact_summary = (
            f"{len(graph.nodes)} nodes, {len(graph.edges)} edges"
            + (" [truncated]" if graph.truncated else "")
        )[:500]
        return {
            "ok": True,
            "mode": "dependency_graph",
            "nodes": graph.nodes,
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "kind": e.kind,
                    "is_external": e.is_external,
                }
                for e in graph.edges
            ],
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "truncated": graph.truncated,
            "artifacts": {"dependency_graph_summary": artifact_summary},
        }

    def _repo_context(
        self, root: Path, entries: list[CodeMapEntry], max_chars: int
    ) -> dict[str, Any]:
        lang_counts: dict[str, int] = {}
        for e in entries:
            lang_counts[e.language] = lang_counts.get(e.language, 0) + 1

        top_dirs: list[str] = []
        seen_dirs: set[str] = set()
        for e in entries:
            parts = e.rel_path.replace("\\", "/").split("/")
            if len(parts) > 1:
                d = parts[0]
                if d not in seen_dirs:
                    seen_dirs.add(d)
                    top_dirs.append(d)

        by_lines = sorted(entries, key=lambda e: -e.line_count)

        sections: list[str] = [
            f"# Repo Context: {root.name}",
            "",
            f"## Summary",
            f"{len(entries)} files, {sum(e.line_count for e in entries):,} total lines",
            "",
            "## Languages",
            *[f"- {lang}: {count}" for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])],
            "",
            "## Top-level directories",
            *[f"- {d}/" for d in sorted(top_dirs)],
            "",
            "## Largest files (by line count)",
            *[f"- {e.rel_path} ({e.line_count} lines)" for e in by_lines[:20]],
        ]

        context = "\n".join(sections)
        if len(context) > max_chars:
            context = context[:max_chars - 3] + "..."

        return {
            "ok": True,
            "mode": "repo_context",
            "context": context,
            "char_count": len(context),
            "truncated": len(context) >= max_chars,
            "artifacts": {"repo_context_md": context},
        }
