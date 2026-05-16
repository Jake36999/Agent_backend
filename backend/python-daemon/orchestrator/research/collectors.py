from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .models import SourceRecord

_MAX_SOURCES = 12
_MAX_EXCERPT_CHARS = 1200
_MAX_TOTAL_CHARS = 12000

_SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".next",
})
_LOCAL_EXTENSIONS = frozenset({
    ".md", ".py", ".ts", ".tsx", ".js", ".json", ".yaml", ".yml",
    ".txt", ".rst", ".toml",
})


@runtime_checkable
class SourceCollector(Protocol):
    def collect(self, query: str, *, max_sources: int = _MAX_SOURCES) -> list[SourceRecord]:
        ...


class StaticSourceCollector:
    """Wraps a pre-provided list of source dicts into SourceRecords."""

    def __init__(self, sources: list[dict[str, Any]]) -> None:
        self._sources = sources

    def collect(self, query: str, *, max_sources: int = _MAX_SOURCES) -> list[SourceRecord]:
        now = datetime.now(timezone.utc).isoformat()
        records: list[SourceRecord] = []
        for i, s in enumerate(self._sources[:max_sources]):
            excerpt = str(s.get("excerpt", s.get("content", "")))[:_MAX_EXCERPT_CHARS]
            records.append(
                SourceRecord(
                    source_id=str(s.get("source_id", f"static_{i:03d}")),
                    title=str(s.get("title", f"Source {i + 1}")),
                    url_or_path=str(s.get("url_or_path", s.get("path", ""))),
                    source_type=str(s.get("source_type", "provided")),
                    excerpt=excerpt,
                    retrieved_at=str(s.get("retrieved_at", now)),
                    relevance_score=float(s.get("relevance_score", 1.0)),
                )
            )
        return records


class LocalArtifactSourceCollector:
    """Reads files from a local repo directory, producing bounded SourceRecords."""

    def __init__(
        self,
        target_repo: str,
        allowed_extensions: frozenset[str] = _LOCAL_EXTENSIONS,
    ) -> None:
        self.target_repo = target_repo
        self.allowed_extensions = allowed_extensions

    def collect(self, query: str, *, max_sources: int = _MAX_SOURCES) -> list[SourceRecord]:
        now = datetime.now(timezone.utc).isoformat()
        repo_path = Path(self.target_repo)
        if not repo_path.is_dir():
            return []

        candidates: list[Path] = []
        try:
            for p in sorted(repo_path.rglob("*")):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in self.allowed_extensions:
                    continue
                if any(part in _SKIP_DIRS or part.startswith(".") for part in p.parts):
                    continue
                candidates.append(p)
                if len(candidates) >= max_sources * 8:
                    break
        except (PermissionError, OSError):
            return []

        records: list[SourceRecord] = []
        total_chars = 0

        for path in candidates:
            if len(records) >= max_sources:
                break
            remaining = _MAX_TOTAL_CHARS - total_chars
            if remaining <= 0:
                break
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except (PermissionError, OSError):
                continue
            excerpt = raw[: min(_MAX_EXCERPT_CHARS, remaining)]
            if not excerpt.strip():
                continue
            total_chars += len(excerpt)
            try:
                rel = str(path.relative_to(repo_path)).replace("\\", "/")
            except ValueError:
                rel = path.name
            records.append(
                SourceRecord(
                    source_id=f"local.{rel.replace('/', '_')}",
                    title=rel,
                    url_or_path=str(path),
                    source_type="file",
                    excerpt=excerpt,
                    retrieved_at=now,
                    relevance_score=1.0,
                )
            )

        return records


class WebSourceCollector:
    """Stub — live web access is not yet enabled; always returns empty list.

    Callers must check is_configured() before use; the adapter returns
    POLICY_BLOCK when source_mode='web_stub'.
    """

    def is_configured(self) -> bool:
        return False

    def collect(self, query: str, *, max_sources: int = _MAX_SOURCES) -> list[SourceRecord]:
        return []


class ConfiguredWebCollector:
    """Fetches real content from http/https URLs listed in source dicts.

    Each source dict must have a ``url_or_path`` field that starts with
    http:// or https://.  The provider handles domain-allowlist and
    content-type guards; this collector wraps results into SourceRecords.
    """

    def __init__(
        self,
        sources: list[dict[str, Any]],
        provider: Any,
    ) -> None:
        self._sources = sources
        self._provider = provider

    def collect(self, query: str, *, max_sources: int = _MAX_SOURCES) -> list[SourceRecord]:
        from .source_normalizer import dedupe_and_cap

        now = datetime.now(timezone.utc).isoformat()
        raw_records: list[SourceRecord] = []

        for i, s in enumerate(self._sources[:max_sources]):
            url = str(s.get("url_or_path", s.get("path", ""))).strip()
            title = str(s.get("title", url or f"Web Source {i + 1}"))
            content = self._provider.fetch(url) if url.startswith(("http://", "https://")) else None
            if content is None:
                excerpt = str(s.get("excerpt", s.get("content", "")))[:_MAX_EXCERPT_CHARS]
            else:
                excerpt = content[:_MAX_EXCERPT_CHARS]
            if not excerpt.strip():
                continue
            raw_records.append(
                SourceRecord(
                    source_id=str(s.get("source_id", f"web_{i:03d}")),
                    title=title,
                    url_or_path=url,
                    source_type="web",
                    excerpt=excerpt,
                    retrieved_at=str(s.get("retrieved_at", now)),
                    relevance_score=float(s.get("relevance_score", 1.0)),
                )
            )

        return dedupe_and_cap(raw_records)
