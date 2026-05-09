from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .dependency_extractor import DependencyExtractor
from .mermaid_formatter import format_mermaid
from .models import CodeMapEntry, DependencyEdge, DependencyGraph

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


_TEST_DIR_NAMES = frozenset({
    "tests", "test", "spec", "specs", "__tests__", "e2e", "testing", "integration",
})
_ENTRYPOINT_NAMES = frozenset({
    "main.py", "__main__.py", "app.py", "server.py", "index.py", "run.py",
    "cli.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.mjs", "index.ts", "server.js", "app.js", "main.js", "main.ts",
})
_TODO_PATTERNS = ("TODO", "FIXME", "HACK", "XXX")
_MAX_TODO_FILE_SIZE = 1_000_000


def _detect_test_dirs(entries: list[CodeMapEntry]) -> list[str]:
    dirs: set[str] = set()
    for e in entries:
        parts = e.rel_path.replace("\\", "/").split("/")
        for i, part in enumerate(parts[:-1]):
            if part.lower() in _TEST_DIR_NAMES:
                dirs.add("/".join(parts[: i + 1]))
    return sorted(dirs)[:20]


def _detect_entrypoints(entries: list[CodeMapEntry]) -> list[str]:
    result = []
    for e in entries:
        fname = e.rel_path.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if fname in _ENTRYPOINT_NAMES:
            result.append(e.rel_path)
    return result[:20]


def _scan_todo_fixme(root: Path, entries: list[CodeMapEntry]) -> list[dict]:
    results = []
    for e in entries:
        abs_path = root / e.rel_path
        try:
            if abs_path.stat().st_size > _MAX_TODO_FILE_SIZE:
                continue
            text = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        counts: dict[str, int] = {}
        for pattern in _TODO_PATTERNS:
            c = text.count(pattern)
            if c:
                counts[pattern] = c
        if counts:
            results.append({
                "path": e.rel_path,
                "count": sum(counts.values()),
                "kinds": sorted(counts.keys()),
            })
    results.sort(key=lambda x: -x["count"])
    return results[:20]


def _compute_fan(edges: list[DependencyEdge]) -> tuple[list[dict], list[dict]]:
    fan_in: dict[str, int] = {}
    fan_out: dict[str, int] = {}
    for edge in edges:
        if edge.is_external:
            continue
        fan_out[edge.source] = fan_out.get(edge.source, 0) + 1
        fan_in[edge.target] = fan_in.get(edge.target, 0) + 1
    fi = sorted([{"path": k, "count": v} for k, v in fan_in.items()], key=lambda x: -x["count"])[:20]
    fo = sorted([{"path": k, "count": v} for k, v in fan_out.items()], key=lambda x: -x["count"])[:20]
    return fi, fo


def _compute_orphans(graph: DependencyGraph) -> list[str]:
    connected: set[str] = set()
    for edge in graph.edges:
        if not edge.is_external:
            connected.add(edge.source)
            connected.add(edge.target)
    return sorted(n for n in graph.nodes if n not in connected)[:20]


def _extract_externals(graph: DependencyGraph) -> list[str]:
    ext: set[str] = set()
    for edge in graph.edges:
        if edge.is_external:
            pkg = edge.target.split(".")[0].split("/")[0]
            ext.add(pkg)
    return sorted(ext)[:50]


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
            return self._repo_context(root, entries, max_chars, truncated_scan)
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
        fan_in, fan_out = _compute_fan(graph.edges)
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
            "artifacts": {
                "dependency_graph_summary": artifact_summary,
                "fan_in_json": json.dumps(fan_in)[:2000],
                "fan_out_json": json.dumps(fan_out)[:2000],
                "orphans_json": json.dumps(_compute_orphans(graph))[:2000],
                "external_deps_json": json.dumps(_extract_externals(graph))[:2000],
            },
        }

    def _repo_context(
        self, root: Path, entries: list[CodeMapEntry], max_chars: int,
        truncated_scan: bool = False,
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
        total_lines = sum(e.line_count for e in entries)

        sections: list[str] = [
            f"# Repo Context: {root.name}",
            "",
            "## Summary",
            f"{len(entries)} files, {total_lines:,} total lines",
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

        lang_summary = ", ".join(f"{k}:{v}" for k, v in sorted(lang_counts.items(), key=lambda x: -x[1]))
        code_map_summary = (
            f"{len(entries)} files, {total_lines:,} lines"
            + (" [truncated]" if truncated_scan else "")
            + (f" | {lang_summary}" if lang_summary else "")
        )[:2000]

        return {
            "ok": True,
            "mode": "repo_context",
            "context": context,
            "char_count": len(context),
            "truncated": len(context) >= max_chars,
            "artifacts": {
                "repo_context_md": context,
                "code_map_summary": code_map_summary,
                "largest_files_json": json.dumps(
                    [{"path": e.rel_path, "line_count": e.line_count} for e in by_lines[:20]]
                )[:4000],
                "language_counts_json": json.dumps(
                    [[k, v] for k, v in sorted(lang_counts.items(), key=lambda x: -x[1])]
                )[:1000],
                "test_dirs_json": json.dumps(_detect_test_dirs(entries))[:1000],
                "entrypoints_json": json.dumps(_detect_entrypoints(entries))[:1000],
                "todo_fixme_json": json.dumps(_scan_todo_fixme(root, entries))[:4000],
            },
        }
