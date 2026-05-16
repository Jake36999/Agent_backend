from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchSource:
    source_id: str       # e.g. "repo_context.repo_context_md"
    source_type: str     # "repo_context" | "code_map" | "dependency_graph" | "mermaid"
    content: str         # bounded content excerpt
    artifact_key: str    # the step-output artifact key this came from


@dataclass(frozen=True)
class ResearchCitation:
    citation_id: str     # e.g. "cite_001"
    claim: str           # what the citation supports
    source_id: str       # references a ResearchSource.source_id
    excerpt: str         # bounded excerpt from the source
    confidence: str      # "observed" (directly in data) | "derived" (inferred)


@dataclass(frozen=True)
class DeepResearchReport:
    objective: str
    target_repo: str
    executive_summary_md: str   # persisted as research_report.md
    findings_md: str            # detailed findings with citation refs
    citations_yaml: str         # structured citation list
    sources_index_md: str       # source listing (bounded)
