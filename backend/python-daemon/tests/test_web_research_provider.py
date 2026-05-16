from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.research.provider_policy import get_allowed_domains, is_web_research_enabled
from orchestrator.research.providers import (
    ConfiguredWebProvider,
    StaticResearchProvider,
    WebResearchProviderStub,
)
from orchestrator.research.source_normalizer import dedupe_and_cap, normalize_record
from orchestrator.research.models import SourceRecord


# ---------------------------------------------------------------------------
# provider_policy
# ---------------------------------------------------------------------------


class TestIsWebResearchEnabled:
    def test_default_false(self, monkeypatch):
        monkeypatch.delenv("ALETHEIA_ENABLE_WEB_RESEARCH", raising=False)
        assert is_web_research_enabled() is False

    def test_true_when_set(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "true")
        assert is_web_research_enabled() is True

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "TRUE")
        assert is_web_research_enabled() is True

    def test_padded_value(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "  true  ")
        assert is_web_research_enabled() is True

    def test_false_string(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "false")
        assert is_web_research_enabled() is False

    def test_one_string(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "1")
        assert is_web_research_enabled() is False

    def test_yes_string(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "yes")
        assert is_web_research_enabled() is False


class TestGetAllowedDomains:
    def test_empty_when_not_set(self, monkeypatch):
        monkeypatch.delenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", raising=False)
        assert get_allowed_domains() == frozenset()

    def test_single_domain(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", "example.com")
        assert "example.com" in get_allowed_domains()

    def test_multiple_domains(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", "a.com,b.org")
        domains = get_allowed_domains()
        assert "a.com" in domains
        assert "b.org" in domains

    def test_whitespace_trimmed(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", " a.com , b.org ")
        domains = get_allowed_domains()
        assert "a.com" in domains

    def test_returns_frozenset(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", "x.com")
        assert isinstance(get_allowed_domains(), frozenset)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class TestStaticResearchProvider:
    def test_returns_content(self):
        p = StaticResearchProvider("hello world")
        assert p.fetch("http://any") == "hello world"

    def test_url_ignored(self):
        p = StaticResearchProvider("fixed")
        assert p.fetch("http://other") == "fixed"


class TestWebResearchProviderStub:
    def test_always_none(self):
        p = WebResearchProviderStub()
        assert p.fetch("http://example.com") is None


class TestConfiguredWebProvider:
    def test_non_http_url_returns_none(self):
        p = ConfiguredWebProvider(frozenset({"example.com"}))
        assert p.fetch("/local/path") is None

    def test_empty_allowlist_blocks_all(self):
        p = ConfiguredWebProvider(frozenset())
        assert p.fetch("http://example.com/") is None

    def test_domain_not_in_allowlist_returns_none(self):
        p = ConfiguredWebProvider(frozenset({"safe.com"}))
        assert p.fetch("http://evil.com/page") is None

    def test_subdomain_allowed(self):
        p = ConfiguredWebProvider(frozenset({"example.com"}))
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.iter_content.return_value = [b"<html>hello</html>"]
        with patch("requests.get", return_value=mock_resp):
            result = p.fetch("http://docs.example.com/page")
        assert result is not None
        assert "hello" in result

    def test_wrong_content_type_returns_none(self):
        p = ConfiguredWebProvider(frozenset({"example.com"}))
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.iter_content.return_value = [b'{"data": 1}']
        with patch("requests.get", return_value=mock_resp):
            result = p.fetch("http://example.com/api")
        assert result is None

    def test_content_capped_at_32kb(self):
        p = ConfiguredWebProvider(frozenset({"example.com"}))
        big_chunk = b"x" * 40000
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/plain"}
        mock_resp.iter_content.return_value = [big_chunk]
        with patch("requests.get", return_value=mock_resp):
            result = p.fetch("http://example.com/big")
        assert result is not None
        assert len(result) <= 32768

    def test_network_error_returns_none(self):
        p = ConfiguredWebProvider(frozenset({"example.com"}))
        with patch("requests.get", side_effect=Exception("timeout")):
            result = p.fetch("http://example.com/")
        assert result is None

    def test_text_plain_allowed(self):
        p = ConfiguredWebProvider(frozenset({"example.com"}))
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/plain"}
        mock_resp.iter_content.return_value = [b"plain text content"]
        with patch("requests.get", return_value=mock_resp):
            result = p.fetch("http://example.com/readme")
        assert result == "plain text content"


# ---------------------------------------------------------------------------
# source_normalizer
# ---------------------------------------------------------------------------


def _make_record(
    source_id: str = "s1",
    title: str = "Title",
    url_or_path: str = "http://example.com/",
    excerpt: str = "Some excerpt.",
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        title=title,
        url_or_path=url_or_path,
        source_type="web",
        excerpt=excerpt,
        retrieved_at="2025-01-01T00:00:00Z",
        relevance_score=1.0,
    )


class TestNormalizeRecord:
    def test_title_capped_at_200(self):
        rec = _make_record(title="T" * 300)
        n = normalize_record(rec)
        assert len(n.title) == 200

    def test_url_capped_at_1000(self):
        rec = _make_record(url_or_path="http://x.com/" + "a" * 1200)
        n = normalize_record(rec)
        assert len(n.url_or_path) == 1000

    def test_excerpt_capped_at_1200(self):
        rec = _make_record(excerpt="e" * 2000)
        n = normalize_record(rec)
        assert len(n.excerpt) == 1200

    def test_short_fields_unchanged(self):
        rec = _make_record(title="Hi", url_or_path="http://x.com/", excerpt="short")
        n = normalize_record(rec)
        assert n.title == "Hi"
        assert n.excerpt == "short"


class TestDedupeAndCap:
    def test_dedupes_by_url(self):
        records = [_make_record("s1"), _make_record("s2")]
        result = dedupe_and_cap(records)
        assert len(result) == 1

    def test_different_urls_kept(self):
        r1 = _make_record("s1", url_or_path="http://a.com/")
        r2 = _make_record("s2", url_or_path="http://b.com/")
        result = dedupe_and_cap([r1, r2])
        assert len(result) == 2

    def test_total_chars_budget(self):
        records = [
            _make_record(f"s{i}", url_or_path=f"http://x.com/{i}", excerpt="e" * 1200)
            for i in range(20)
        ]
        result = dedupe_and_cap(records)
        total = sum(len(r.excerpt) for r in result)
        assert total <= 12000

    def test_dedupes_by_sha256_when_no_url(self):
        r1 = _make_record("s1", url_or_path="", excerpt="same content here")
        r2 = _make_record("s2", url_or_path="", excerpt="same content here")
        result = dedupe_and_cap([r1, r2])
        assert len(result) == 1

    def test_empty_list_returns_empty(self):
        assert dedupe_and_cap([]) == []


# ---------------------------------------------------------------------------
# web_configured integration via invoke_deep_research
# ---------------------------------------------------------------------------


class TestWebConfiguredMode:
    def test_web_configured_blocked_when_flag_off(self, monkeypatch):
        monkeypatch.delenv("ALETHEIA_ENABLE_WEB_RESEARCH", raising=False)
        from orchestrator.research.deep_research_adapter import invoke_deep_research
        r = invoke_deep_research(query="q", source_mode="web_configured")
        assert r["ok"] is False
        assert r["status"] == "POLICY_BLOCK"
        assert r["capability_receipt"]["authorized"] is False

    def test_web_configured_allowed_when_flag_on(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "true")
        monkeypatch.setenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", "example.com")
        sources = [
            {"source_id": "w1", "title": "Page", "url_or_path": "http://example.com/",
             "source_type": "web", "excerpt": "content here", "retrieved_at": "2025-01-01T00:00:00Z"}
        ]
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.iter_content.return_value = [b"<html>web content</html>"]
        from orchestrator.research.deep_research_adapter import invoke_deep_research
        with patch("requests.get", return_value=mock_resp):
            r = invoke_deep_research(query="q", source_mode="web_configured", sources_raw=sources)
        assert r["ok"] is True
        assert r["status"] == "OK"

    def test_web_configured_receipt_authorized_when_enabled(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "true")
        monkeypatch.delenv("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", raising=False)
        from orchestrator.research.deep_research_adapter import invoke_deep_research
        r = invoke_deep_research(query="q", source_mode="web_configured", sources_raw=[])
        assert r["ok"] is True
        assert r["capability_receipt"]["authorized"] is True

    def test_web_stub_still_blocked_when_flag_on(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_ENABLE_WEB_RESEARCH", "true")
        from orchestrator.research.deep_research_adapter import invoke_deep_research
        r = invoke_deep_research(query="q", source_mode="web_stub")
        assert r["ok"] is False
        assert r["status"] == "POLICY_BLOCK"

    def test_block_message_hints_env_var(self, monkeypatch):
        monkeypatch.delenv("ALETHEIA_ENABLE_WEB_RESEARCH", raising=False)
        from orchestrator.research.deep_research_adapter import invoke_deep_research
        r = invoke_deep_research(query="q", source_mode="web_configured")
        assert "ALETHEIA_ENABLE_WEB_RESEARCH" in r["summary"]
