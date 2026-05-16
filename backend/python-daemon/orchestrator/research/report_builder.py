from __future__ import annotations

import json

from .citation_index import build_citations
from .models import CitationRecord, ResearchReport, SourceRecord

_ANSWER_CAP = 3000
_REPORT_CAP = 10000
_TABLE_CAP = 4000
_CITATIONS_CAP = 6000
_SOURCES_CAP = 3000
_ACTIONS_CAP = 2000
_TRUNCATION_MARKER = "\n...[truncated]"

_INSUFFICIENT_EVIDENCE = (
    "Insufficient evidence — no source records were collected. "
    "Verify that the collector is configured and that sources are reachable."
)

_DISCLAIMER = (
    "> **Analysis type:** read-only. No files were modified. No external calls were made.\n"
    "> All findings are bounded excerpts from collected sources.\n"
    "> No inferences beyond directly observable data."
)


def _bounded(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _build_answer_summary(
    query: str,
    sources: list[SourceRecord],
    citations: list[CitationRecord],
) -> str:
    if not sources:
        return _INSUFFICIENT_EVIDENCE
    parts = [
        f"Collected {len(sources)} source(s) across mode(s): "
        f"{', '.join(sorted({s.source_type for s in sources}))}.",
        f"Generated {len(citations)} citation(s) from deterministic source analysis.",
        "All claims in this report are grounded in the collected sources.",
    ]
    return _bounded(" ".join(parts), _ANSWER_CAP)


def _build_evidence_table(sources: list[SourceRecord], citations: list[CitationRecord]) -> str:
    if not sources:
        return "| — | — | — |\n_No sources collected._"
    cite_map = {c.source_id: c.citation_id for c in citations}
    rows = ["| Citation | Source | Type |", "| --- | --- | --- |"]
    for src in sources:
        cid = cite_map.get(src.source_id, "—")
        rows.append(f"| {cid} | {src.title[:80]} | {src.source_type} |")
    return _bounded("\n".join(rows), _TABLE_CAP)


def _build_citations_section(citations: list[CitationRecord]) -> str:
    if not citations:
        return "## Citations\n\n_No citations generated._"
    lines = ["## Citations", ""]
    for c in citations:
        safe_excerpt = c.excerpt[:300].replace("\n", " ")
        lines += [
            f"### [{c.citation_id}] {c.source_id}",
            "",
            f"**Claim:** {c.claim}",
            f"**Confidence:** {c.confidence}",
            f"**Excerpt:** {safe_excerpt}",
            "",
        ]
    return _bounded("\n".join(lines), _CITATIONS_CAP)


def _build_known_gaps(sources: list[SourceRecord]) -> tuple[str, ...]:
    if not sources:
        return ("No sources were available for analysis.",)
    gaps: list[str] = []
    types = {s.source_type for s in sources}
    if "web" not in types:
        gaps.append("Web sources were not collected (web_stub mode active).")
    if len(sources) < 3:
        gaps.append("Fewer than 3 sources collected; coverage may be limited.")
    return tuple(gaps)


def _build_suggested_actions(query: str, sources: list[SourceRecord]) -> tuple[str, ...]:
    actions: list[str] = []
    if not sources:
        actions.append("Configure a source collector and retry.")
        actions.append("Provide explicit source records via source_mode='static'.")
    else:
        actions.append("Review citations for accuracy against original sources.")
        actions.append("Run with source_mode='local' targeting a broader directory for more coverage.")
    return tuple(actions)


def _build_full_report(
    query: str,
    source_mode: str,
    answer_summary: str,
    evidence_table: str,
    citations_section: str,
    known_gaps: tuple[str, ...],
    suggested_next_actions: tuple[str, ...],
    confidence_note: str,
) -> str:
    parts = [
        f"# Research Report",
        "",
        f"**Query:** {query}",
        f"**Source mode:** {source_mode}",
        "",
        _DISCLAIMER,
        "",
        "## Answer Summary",
        "",
        answer_summary,
        "",
        "## Evidence Table",
        "",
        evidence_table,
        "",
        citations_section,
        "",
        "## Known Gaps",
        "",
        *[f"- {g}" for g in known_gaps],
        "",
        "## Suggested Next Actions",
        "",
        *[f"- {a}" for a in suggested_next_actions],
        "",
        "## Confidence Note",
        "",
        confidence_note,
        "",
    ]
    return _bounded("\n".join(parts), _REPORT_CAP)


def _build_citations_json(citations: list[CitationRecord]) -> str:
    data = [
        {
            "citation_id": c.citation_id,
            "claim": c.claim,
            "source_id": c.source_id,
            "confidence": c.confidence,
            "excerpt": c.excerpt[:300],
        }
        for c in citations
    ]
    return _bounded(json.dumps({"citations": data}, indent=2), _CITATIONS_CAP)


def _build_sources_json(sources: list[SourceRecord]) -> str:
    data = [
        {
            "source_id": s.source_id,
            "title": s.title,
            "url_or_path": s.url_or_path,
            "source_type": s.source_type,
            "retrieved_at": s.retrieved_at,
            "relevance_score": s.relevance_score,
            "excerpt_chars": len(s.excerpt),
        }
        for s in sources
    ]
    return _bounded(json.dumps({"sources": data}, indent=2), _SOURCES_CAP)


def _build_next_actions_yaml(actions: tuple[str, ...]) -> str:
    lines = ["next_actions:"]
    for a in actions:
        safe = a.replace('"', '\\"')
        lines.append(f'  - "{safe}"')
    return _bounded("\n".join(lines) + "\n", _ACTIONS_CAP)


def build_research_report(
    *,
    query: str,
    source_mode: str,
    sources: list[SourceRecord],
) -> ResearchReport:
    citations = build_citations(sources)
    known_gaps = _build_known_gaps(sources)
    suggested_next_actions = _build_suggested_actions(query, sources)
    confidence_note = (
        "medium — based on bounded static file analysis; no model inference performed."
        if sources
        else "none — no sources collected."
    )

    answer_summary = _build_answer_summary(query, sources, citations)
    evidence_table = _build_evidence_table(sources, citations)
    citations_section = _build_citations_section(citations)

    report_md = _build_full_report(
        query=query,
        source_mode=source_mode,
        answer_summary=answer_summary,
        evidence_table=evidence_table,
        citations_section=citations_section,
        known_gaps=known_gaps,
        suggested_next_actions=suggested_next_actions,
        confidence_note=confidence_note,
    )
    citations_json = _build_citations_json(citations)
    sources_json = _build_sources_json(sources)
    next_actions_yaml = _build_next_actions_yaml(suggested_next_actions)

    return ResearchReport(
        query=query,
        source_mode=source_mode,
        answer_summary_md=answer_summary,
        evidence_table_md=evidence_table,
        citations_md=citations_section,
        known_gaps=known_gaps,
        suggested_next_actions=suggested_next_actions,
        confidence_note=confidence_note,
        research_report_md=report_md,
        research_citations_json=citations_json,
        research_sources_json=sources_json,
        research_next_actions_yaml=next_actions_yaml,
    )
