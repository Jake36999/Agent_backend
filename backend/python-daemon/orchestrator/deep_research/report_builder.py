from __future__ import annotations

from typing import Any

from .collector import collect_research_sources
from .models import DeepResearchReport, ResearchCitation, ResearchSource

_SUMMARY_CAP = 8000
_FINDINGS_CAP = 10000
_CITATIONS_CAP = 6000
_SOURCES_CAP = 4000
_TRUNCATION_MARKER = "\n...[truncated]"

_CLAIM_TEMPLATES: dict[str, str] = {
    "repo_context":     "Repository context and architecture overview observed from static analysis.",
    "code_map":         "File structure and module layout observed from code map.",
    "dependency_graph": "Inter-module dependency relationships observed from dependency graph.",
    "mermaid":          "Dependency graph topology available as Mermaid diagram.",
}


def _bounded(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _repo_name(target_repo: str) -> str:
    return target_repo.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or target_repo


def _build_citations(sources: list[ResearchSource]) -> list[ResearchCitation]:
    citations: list[ResearchCitation] = []
    for i, src in enumerate(sources, start=1):
        cid = f"cite_{i:03d}"
        claim = _CLAIM_TEMPLATES.get(src.source_type, f"Data observed from {src.source_type}.")
        excerpt = src.content[:800].rstrip()
        citations.append(
            ResearchCitation(
                citation_id=cid,
                claim=claim,
                source_id=src.source_id,
                excerpt=excerpt,
                confidence="observed",
            )
        )
    return citations


def _build_executive_summary(
    objective: str,
    target_repo: str,
    sources: list[ResearchSource],
    citations: list[ResearchCitation],
) -> str:
    repo = _repo_name(target_repo)
    source_types = sorted({s.source_type for s in sources})
    parts = [
        f"# Deep Research Report: {repo}",
        "",
        f"**Objective:** {objective}",
        "",
        "> **Analysis type:** read-only. No files were modified. No external calls were made.",
        "",
        "## Executive Summary",
        "",
        f"Collected {len(sources)} source(s) from static analysis of `{repo}`: "
        f"{', '.join(source_types)}.",
        f"Generated {len(citations)} citation(s) from deterministic artifact data.",
        "",
        "All findings are bounded excerpts from the analysis artifacts. "
        "No inferences have been made beyond what is directly observable in the data.",
        "",
    ]

    # Include repo_context preview if present
    ctx_src = next((s for s in sources if s.source_type == "repo_context"), None)
    if ctx_src:
        preview = ctx_src.content[:600].rstrip()
        parts += ["## Repository Context (preview)", "", preview, ""]

    return _bounded("\n".join(parts), _SUMMARY_CAP)


def _build_findings(
    sources: list[ResearchSource],
    citations: list[ResearchCitation],
) -> str:
    cite_map = {c.source_id: c.citation_id for c in citations}
    parts = ["## Findings", ""]

    for src in sources:
        cid = cite_map.get(src.source_id, "")
        cite_ref = f" [{cid}]" if cid else ""
        heading = {
            "repo_context":     "Repository Context",
            "code_map":         "Code Map",
            "dependency_graph": "Dependency Graph",
            "mermaid":          "Mermaid Diagram",
        }.get(src.source_type, src.source_type.replace("_", " ").title())

        parts += [f"### {heading}{cite_ref}", ""]
        parts.append(src.content[:2000].rstrip())
        parts.append("")

    if not sources:
        parts.append("_No source data collected. Ensure the pipeline steps ran successfully._")
        parts.append("")

    return _bounded("\n".join(parts), _FINDINGS_CAP)


def _build_citations_yaml(citations: list[ResearchCitation]) -> str:
    if not citations:
        return "citations: []\n"
    lines = ["citations:"]
    for c in citations:
        safe_claim = c.claim.replace('"', '\\"')
        safe_excerpt = c.excerpt[:300].replace('"', '\\"').replace("\n", " ")
        lines += [
            f"  - citation_id: {c.citation_id}",
            f"    source_id: {c.source_id}",
            f'    claim: "{safe_claim}"',
            f"    confidence: {c.confidence}",
            f'    excerpt: "{safe_excerpt}"',
        ]
    return _bounded("\n".join(lines) + "\n", _CITATIONS_CAP)


def _build_sources_index(sources: list[ResearchSource]) -> str:
    if not sources:
        return "# Research Sources\n\n_No sources collected._\n"
    lines = ["# Research Sources", ""]
    for src in sources:
        lines.append(f"- **{src.source_id}** (`{src.source_type}`) — `{src.artifact_key}`")
    lines.append("")
    return _bounded("\n".join(lines), _SOURCES_CAP)


def build_deep_research_report(
    *,
    objective: str,
    target_repo: str,
    step_outputs: dict[str, dict[str, Any]],
    pipeline_receipt: dict[str, Any] | None = None,
) -> DeepResearchReport:
    sources = collect_research_sources(step_outputs)
    citations = _build_citations(sources)

    executive_summary_md = _build_executive_summary(objective, target_repo, sources, citations)
    findings_md = _build_findings(sources, citations)
    citations_yaml = _build_citations_yaml(citations)
    sources_index_md = _build_sources_index(sources)

    return DeepResearchReport(
        objective=objective,
        target_repo=target_repo,
        executive_summary_md=executive_summary_md,
        findings_md=findings_md,
        citations_yaml=citations_yaml,
        sources_index_md=sources_index_md,
    )
