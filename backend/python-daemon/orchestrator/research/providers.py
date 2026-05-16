from __future__ import annotations

from typing import Protocol, runtime_checkable
from urllib.parse import urlparse

_FETCH_TIMEOUT_S = 5
_MAX_RESPONSE_BYTES = 32 * 1024  # 32 KB
_ALLOWED_CONTENT_TYPES = frozenset({"text/html", "text/plain"})


@runtime_checkable
class ResearchProvider(Protocol):
    def fetch(self, url: str) -> str | None:
        ...


class StaticResearchProvider:
    """Returns a fixed string for any URL — for tests only."""

    def __init__(self, content: str) -> None:
        self._content = content

    def fetch(self, url: str) -> str | None:
        return self._content


class LocalFileResearchProvider:
    """Reads a local file path as content — for offline testing."""

    def fetch(self, url: str) -> str | None:
        from pathlib import Path

        p = Path(url)
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return None


class WebResearchProviderStub:
    """Always returns None — live web access is not enabled."""

    def fetch(self, url: str) -> str | None:
        return None


class ConfiguredWebProvider:
    """Real bounded HTTP fetch with domain allowlist, size, and content-type guards."""

    def __init__(self, allowed_domains: frozenset[str]) -> None:
        self._allowed_domains = allowed_domains

    def _is_domain_allowed(self, url: str) -> bool:
        if not self._allowed_domains:
            return False
        try:
            host = urlparse(url).hostname or ""
        except Exception:
            return False
        host = host.lower()
        return any(
            host == d or host.endswith("." + d)
            for d in self._allowed_domains
        )

    def fetch(self, url: str) -> str | None:
        if not url.startswith(("http://", "https://")):
            return None
        if not self._is_domain_allowed(url):
            return None
        try:
            import requests  # noqa: PLC0415

            resp = requests.get(
                url,
                timeout=_FETCH_TIMEOUT_S,
                allow_redirects=False,
                stream=True,
                headers={"User-Agent": "Aletheia-Research/1.0"},
            )
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ct not in _ALLOWED_CONTENT_TYPES:
                return None
            content = b""
            for chunk in resp.iter_content(chunk_size=4096):
                content += chunk
                if len(content) >= _MAX_RESPONSE_BYTES:
                    break
            return content[:_MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")
        except Exception:
            return None
