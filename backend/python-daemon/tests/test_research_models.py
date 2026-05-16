from __future__ import annotations

import pytest

from orchestrator.research.models import (
    CitationRecord,
    ResearchQuery,
    ResearchReport,
    ResearchResult,
    SourceRecord,
)


class TestResearchQuery:
    def test_defaults(self):
        q = ResearchQuery(query="test", source_mode="static")
        assert q.max_sources == 12
        assert q.max_depth == 1
        assert q.target_repo == ""

    def test_frozen(self):
        q = ResearchQuery(query="x", source_mode="local")
        with pytest.raises(Exception):
            q.query = "y"  # type: ignore[misc]


class TestSourceRecord:
    def _make(self, **kw):
        defaults = dict(
            source_id="s1",
            title="My file",
            url_or_path="/tmp/f.py",
            source_type="file",
            excerpt="some text",
            retrieved_at="2025-01-01T00:00:00Z",
        )
        defaults.update(kw)
        return SourceRecord(**defaults)

    def test_fields_accessible(self):
        s = self._make()
        assert s.source_id == "s1"
        assert s.source_type == "file"
        assert s.relevance_score == 1.0

    def test_frozen(self):
        s = self._make()
        with pytest.raises(Exception):
            s.source_id = "x"  # type: ignore[misc]


class TestCitationRecord:
    def test_fields(self):
        c = CitationRecord(
            citation_id="cite_001",
            claim="Content observed.",
            source_id="s1",
            excerpt="short excerpt",
            confidence="observed",
        )
        assert c.citation_id == "cite_001"
        assert c.confidence == "observed"

    def test_frozen(self):
        c = CitationRecord("c", "claim", "s", "exc", "observed")
        with pytest.raises(Exception):
            c.claim = "x"  # type: ignore[misc]


class TestResearchReport:
    def _make(self, **kw):
        defaults = dict(
            query="q",
            source_mode="static",
            answer_summary_md="answer",
            evidence_table_md="table",
            citations_md="cites",
            known_gaps=("gap1",),
            suggested_next_actions=("action1",),
            confidence_note="medium",
            research_report_md="full report",
            research_citations_json='{"citations":[]}',
            research_sources_json='{"sources":[]}',
            research_next_actions_yaml="next_actions:\n",
        )
        defaults.update(kw)
        return ResearchReport(**defaults)

    def test_known_gaps_is_tuple(self):
        r = self._make()
        assert isinstance(r.known_gaps, tuple)

    def test_suggested_actions_is_tuple(self):
        r = self._make()
        assert isinstance(r.suggested_next_actions, tuple)

    def test_frozen(self):
        r = self._make()
        with pytest.raises(Exception):
            r.query = "new"  # type: ignore[misc]
