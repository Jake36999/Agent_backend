from __future__ import annotations

import os


def is_web_research_enabled() -> bool:
    return os.environ.get("ALETHEIA_ENABLE_WEB_RESEARCH", "").strip().lower() == "true"


def get_allowed_domains() -> frozenset[str]:
    raw = os.environ.get("ALETHEIA_WEB_RESEARCH_ALLOWED_DOMAINS", "")
    domains = {d.strip().lower() for d in raw.split(",") if d.strip()}
    return frozenset(domains)
