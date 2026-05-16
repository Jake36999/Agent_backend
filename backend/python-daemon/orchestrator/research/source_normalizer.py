from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .models import SourceRecord

_TITLE_MAX = 200
_URL_MAX = 1000
_EXCERPT_MAX = 1200
_TOTAL_CHARS_MAX = 12_000


def _source_key(record: SourceRecord) -> str:
    url = record.url_or_path.strip()
    if url:
        return url.lower()[:_URL_MAX]
    digest_input = record.title[:100] + record.excerpt[:50]
    return hashlib.sha256(digest_input.encode("utf-8", errors="replace")).hexdigest()


def normalize_record(record: SourceRecord) -> SourceRecord:
    return SourceRecord(
        source_id=record.source_id,
        title=record.title[:_TITLE_MAX],
        url_or_path=record.url_or_path[:_URL_MAX],
        source_type=record.source_type,
        excerpt=record.excerpt[:_EXCERPT_MAX],
        retrieved_at=record.retrieved_at,
        relevance_score=record.relevance_score,
    )


def dedupe_and_cap(records: list[SourceRecord]) -> list[SourceRecord]:
    """Normalize fields, dedupe by url/sha256, and enforce total-char budget."""
    seen: set[str] = set()
    result: list[SourceRecord] = []
    total_chars = 0

    for rec in records:
        normed = normalize_record(rec)
        key = _source_key(normed)
        if key in seen:
            continue
        seen.add(key)
        remaining = _TOTAL_CHARS_MAX - total_chars
        if remaining <= 0:
            break
        if len(normed.excerpt) > remaining:
            normed = SourceRecord(
                source_id=normed.source_id,
                title=normed.title,
                url_or_path=normed.url_or_path,
                source_type=normed.source_type,
                excerpt=normed.excerpt[:remaining],
                retrieved_at=normed.retrieved_at,
                relevance_score=normed.relevance_score,
            )
        total_chars += len(normed.excerpt)
        result.append(normed)

    return result
