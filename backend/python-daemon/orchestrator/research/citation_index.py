from __future__ import annotations

from .models import CitationRecord, SourceRecord

_CLAIM_TEMPLATES: dict[str, str] = {
    "file":     "Content observed from local file.",
    "artifact": "Content observed from pipeline artifact.",
    "provided": "Content provided directly by caller.",
    "web":      "Content retrieved from web source.",
}
_EXCERPT_CAP = 600


def build_citations(sources: list[SourceRecord]) -> list[CitationRecord]:
    """Produce one CitationRecord per SourceRecord, in order."""
    citations: list[CitationRecord] = []
    for i, src in enumerate(sources, start=1):
        claim = _CLAIM_TEMPLATES.get(src.source_type, f"Data observed from {src.source_type}.")
        excerpt = src.excerpt[:_EXCERPT_CAP].rstrip()
        citations.append(
            CitationRecord(
                citation_id=f"cite_{i:03d}",
                claim=claim,
                source_id=src.source_id,
                excerpt=excerpt,
                confidence="observed",
            )
        )
    return citations
