from __future__ import annotations

import json

import pytest

from orchestrator.research.collectors import StaticSourceCollector
from orchestrator.research.models import ResearchReport, SourceRecord
from orchestrator.research.report_builder import build_research_report


def _static_sources(n: int = 2) -> list[SourceRecord]:
    return StaticSourceCollector(
        [
            {
                "source_id": f"src_{i}",
                "title": f"File {i}",
                "url_or_path": f"/tmp/file{i}.py",
                "source_type": "file",
                "excerpt": f"Content of file {i}",
                "retrieved_at": "2025-01-01T00:00:00Z",
            }
            for i in range(n)
        ]
    ).collect("test query")


class TestBuildResearchReport:
    def test_returns_report_instance(self):
        r = build_research_report(query="test", source_mode="static", sources=_static_sources())
        assert isinstance(r, ResearchReport)

    def test_query_preserved(self):
        r = build_research_report(query="my query", source_mode="static", sources=_static_sources())
        assert r.query == "my query"

    def test_source_mode_preserved(self):
        r = build_research_report(query="q", source_mode="local", sources=_static_sources())
        assert r.source_mode == "local"

    def test_answer_summary_nonempty_with_sources(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources(2))
        assert r.answer_summary_md
        assert "Insufficient" not in r.answer_summary_md

    def test_no_sources_produces_insufficient_evidence(self):
        r = build_research_report(query="q", source_mode="static", sources=[])
        assert "Insufficient" in r.answer_summary_md or "insufficient" in r.answer_summary_md.lower()

    def test_evidence_table_contains_citations(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources(2))
        assert "cite_001" in r.evidence_table_md

    def test_citations_md_present(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources(2))
        assert "cite_001" in r.citations_md
        assert "source_id" in r.citations_md.lower() or "src_0" in r.citations_md

    def test_known_gaps_is_tuple(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources())
        assert isinstance(r.known_gaps, tuple)

    def test_suggested_next_actions_nonempty(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources())
        assert len(r.suggested_next_actions) >= 1

    def test_report_md_contains_disclaimer(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources())
        assert "No files were modified" in r.research_report_md

    def test_report_md_contains_query(self):
        r = build_research_report(query="find the bug", source_mode="static", sources=_static_sources())
        assert "find the bug" in r.research_report_md

    def test_citations_json_valid(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources(2))
        data = json.loads(r.research_citations_json)
        assert "citations" in data
        assert len(data["citations"]) == 2

    def test_citations_reference_source_ids(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources(2))
        data = json.loads(r.research_citations_json)
        source_ids = {c["source_id"] for c in data["citations"]}
        assert "src_0" in source_ids

    def test_sources_json_valid(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources(2))
        data = json.loads(r.research_sources_json)
        assert "sources" in data
        assert len(data["sources"]) == 2

    def test_next_actions_yaml_present(self):
        r = build_research_report(query="q", source_mode="static", sources=_static_sources())
        assert "next_actions:" in r.research_next_actions_yaml

    def test_report_bounded(self):
        big_sources = StaticSourceCollector(
            [{"source_id": f"s{i}", "title": f"T{i}", "url_or_path": f"/f{i}", "source_type": "file",
              "excerpt": "x" * 2000, "retrieved_at": "2025-01-01T00:00:00Z"} for i in range(20)]
        ).collect("q")
        r = build_research_report(query="q", source_mode="static", sources=big_sources)
        assert len(r.research_report_md) <= 11000

    def test_no_uncited_factual_claims_without_sources(self):
        r = build_research_report(query="q", source_mode="static", sources=[])
        assert "citations: []" not in r.research_citations_json or "Insufficient" in r.answer_summary_md


class TestCollectorIntegration:
    def test_static_collector_produces_source_records(self):
        collector = StaticSourceCollector([
            {"source_id": "x", "title": "T", "url_or_path": "/p", "source_type": "provided",
             "excerpt": "text", "retrieved_at": "2025-01-01T00:00:00Z"}
        ])
        sources = collector.collect("q")
        assert len(sources) == 1
        assert sources[0].source_id == "x"

    def test_static_collector_respects_max_sources(self):
        collector = StaticSourceCollector(
            [{"source_id": f"s{i}", "title": f"T{i}", "url_or_path": f"/f{i}",
              "source_type": "provided", "excerpt": "text", "retrieved_at": "2025-01-01T00:00:00Z"}
             for i in range(20)]
        )
        sources = collector.collect("q", max_sources=5)
        assert len(sources) == 5

    def test_static_collector_bounds_excerpt(self):
        collector = StaticSourceCollector([
            {"source_id": "s", "title": "T", "url_or_path": "/f", "source_type": "provided",
             "excerpt": "x" * 2000, "retrieved_at": "2025-01-01T00:00:00Z"}
        ])
        sources = collector.collect("q")
        assert len(sources[0].excerpt) <= 1200

    def test_local_collector_empty_for_nonexistent_path(self):
        from orchestrator.research.collectors import LocalArtifactSourceCollector
        collector = LocalArtifactSourceCollector("/nonexistent/path/that/does/not/exist")
        sources = collector.collect("q")
        assert sources == []

    def test_web_collector_always_empty(self):
        from orchestrator.research.collectors import WebSourceCollector
        collector = WebSourceCollector()
        assert collector.is_configured() is False
        assert collector.collect("q") == []
