from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchQuery:
    query: str
    source_mode: str        # "static" | "local" | "web_stub"
    max_sources: int = 12
    max_depth: int = 1
    target_repo: str = ""


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    url_or_path: str
    source_type: str        # "file" | "artifact" | "provided" | "web"
    excerpt: str
    retrieved_at: str
    relevance_score: float = 1.0


@dataclass(frozen=True)
class CitationRecord:
    citation_id: str
    claim: str
    source_id: str
    excerpt: str
    confidence: str         # "observed" | "derived" | "inferred"


@dataclass(frozen=True)
class ResearchReport:
    query: str
    source_mode: str
    answer_summary_md: str
    evidence_table_md: str
    citations_md: str
    known_gaps: tuple[str, ...]
    suggested_next_actions: tuple[str, ...]
    confidence_note: str
    # Serialised artifact content — written to disk by artifact_writer
    research_report_md: str
    research_citations_json: str
    research_sources_json: str
    research_next_actions_yaml: str


@dataclass(frozen=True)
class ResearchResult:
    query: str
    source_mode: str
    answer_md: str
    report_md: str
    citations_json: str
    gaps: tuple[str, ...]
    confidence: str
    suggested_next_actions: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    capability_receipt: dict[str, Any]
