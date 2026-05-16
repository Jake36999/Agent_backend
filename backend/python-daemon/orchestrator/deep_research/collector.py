from __future__ import annotations

from typing import Any

from .models import ResearchSource

_CONTENT_CAP = 4000
_TRUNCATION_MARKER = "\n...[truncated]"


def _bounded(text: str, cap: int = _CONTENT_CAP) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


# (step_id, source_type, artifact_key) — ordered by priority
_SOURCE_SLOTS: list[tuple[str, str, str]] = [
    ("repo_context",     "repo_context",     "repo_context_md"),
    ("repo_context",     "code_map",         "code_map_summary"),
    ("code_map",         "code_map",         "code_map_summary"),
    ("dependency_graph", "dependency_graph", "dependency_graph_summary"),
    ("mermaid",          "mermaid",          "dependency_graph_mmd"),
]


def collect_research_sources(
    step_outputs: dict[str, dict[str, Any]],
) -> list[ResearchSource]:
    """Extract bounded ResearchSource objects from pipeline step outputs.

    Deduplicates by (step_id, artifact_key). Returns sources in priority order.
    """
    sources: list[ResearchSource] = []
    seen: set[tuple[str, str]] = set()

    for step_id, source_type, artifact_key in _SOURCE_SLOTS:
        if (step_id, artifact_key) in seen:
            continue
        raw = step_outputs.get(step_id, {}).get("artifacts", {}).get(artifact_key, "")
        if not raw:
            continue
        seen.add((step_id, artifact_key))
        sources.append(
            ResearchSource(
                source_id=f"{step_id}.{artifact_key}",
                source_type=source_type,
                content=_bounded(str(raw)),
                artifact_key=artifact_key,
            )
        )

    return sources
