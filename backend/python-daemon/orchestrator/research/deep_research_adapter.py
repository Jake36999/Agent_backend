from __future__ import annotations

from typing import Any

from .collectors import (
    ConfiguredWebCollector,
    LocalArtifactSourceCollector,
    SourceCollector,
    StaticSourceCollector,
    WebSourceCollector,
)
from .models import SourceRecord
from .provider_policy import get_allowed_domains, is_web_research_enabled
from .providers import ConfiguredWebProvider
from .report_builder import build_research_report

_MAX_SOURCES_DEFAULT = 12
_MAX_SOURCES_CAP = 50
_VALID_MODES = frozenset({"static", "local", "web_stub", "web_configured"})


def _parse_sources(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [s for s in raw if isinstance(s, dict)]


def _pick_collector(
    source_mode: str,
    sources_raw: list[dict[str, Any]],
    target_repo: str,
) -> tuple[SourceCollector, bool]:
    """Return (collector, is_policy_blocked)."""
    if source_mode == "static":
        return StaticSourceCollector(sources_raw), False
    if source_mode == "local":
        return LocalArtifactSourceCollector(target_repo), False
    if source_mode == "web_configured":
        if not is_web_research_enabled():
            return WebSourceCollector(), True
        provider = ConfiguredWebProvider(get_allowed_domains())
        return ConfiguredWebCollector(sources_raw, provider), False
    # web_stub — always policy-blocked
    return WebSourceCollector(), True


def invoke_deep_research(
    *,
    query: str,
    source_mode: str = "static",
    sources_raw: list[dict[str, Any]] | None = None,
    target_repo: str = "",
    max_sources: int = _MAX_SOURCES_DEFAULT,
    max_depth: int = 1,
) -> dict[str, Any]:
    """Core implementation for mcp_deep_research.

    Returns a tool-result dict suitable for direct return from call_mcp_tool().
    Does not write to disk — artifact content is returned in the 'artifacts' key
    and written by the runner's _attach_deep_research_report hook.
    """
    from orchestrator.capabilities.receipt import build_receipt, compact_receipt

    max_sources = min(int(max_sources), _MAX_SOURCES_CAP)

    if source_mode not in _VALID_MODES:
        receipt = build_receipt(
            capability_id="research.deep_research",
            capability_type="research",
            risk_tier="T2",
            status="POLICY_BLOCK",
            authorized=False,
            network_access=False,
            writes_external_state=False,
            summary=f"Invalid source_mode: {source_mode!r}. Must be one of: {sorted(_VALID_MODES)}.",
        )
        return {
            "ok": False,
            "status": "POLICY_BLOCK",
            "summary": f"Invalid source_mode: {source_mode!r}.",
            "artifacts": {},
            "error": {
                "code": "invalid_source_mode",
                "message": f"source_mode must be one of {sorted(_VALID_MODES)}",
            },
            "capability_receipt": compact_receipt(receipt),
        }

    collector, is_policy_blocked = _pick_collector(
        source_mode, _parse_sources(sources_raw or []), target_repo
    )

    if is_policy_blocked:
        if source_mode == "web_configured":
            block_summary = "web_configured requires ALETHEIA_ENABLE_WEB_RESEARCH=true."
            block_message = "Web research is disabled; set ALETHEIA_ENABLE_WEB_RESEARCH=true to enable."
        else:
            block_summary = "Web source collection is not yet enabled; use source_mode='static' or 'local'."
            block_message = "source_mode='web_stub' is not yet enabled in this release."
        receipt = build_receipt(
            capability_id="research.deep_research",
            capability_type="research",
            risk_tier="T2",
            status="POLICY_BLOCK",
            authorized=False,
            network_access=False,
            writes_external_state=False,
            summary=block_summary,
        )
        return {
            "ok": False,
            "status": "POLICY_BLOCK",
            "summary": block_summary,
            "artifacts": {},
            "error": {
                "code": "web_not_configured",
                "message": block_message,
            },
            "capability_receipt": compact_receipt(receipt),
        }

    sources: list[SourceRecord] = collector.collect(query, max_sources=max_sources)
    report = build_research_report(
        query=query,
        source_mode=source_mode,
        sources=sources,
    )

    artifact_keys = [
        k for k in (
            "research_report_md",
            "research_citations_json",
            "research_sources_json",
            "research_next_actions_yaml",
        )
        if getattr(report, k, "")
    ]

    receipt = build_receipt(
        capability_id="research.deep_research",
        capability_type="research",
        risk_tier="T2",
        status="OK",
        authorized=True,
        network_access=False,
        writes_external_state=False,
        artifact_refs=artifact_keys,
        summary=(
            f"Collected {len(sources)} source(s), built citation-first research report."
            if sources
            else "No sources collected; report contains insufficient-evidence notice."
        ),
    )

    return {
        "ok": True,
        "status": "OK",
        "query": query,
        "source_mode": source_mode,
        "sources_count": len(sources),
        "answer_md": report.answer_summary_md,
        "gaps": list(report.known_gaps),
        "confidence": report.confidence_note,
        "suggested_next_actions": list(report.suggested_next_actions),
        "artifacts": {
            "research_report_md": report.research_report_md,
            "research_citations_json": report.research_citations_json,
            "research_sources_json": report.research_sources_json,
            "research_next_actions_yaml": report.research_next_actions_yaml,
        },
        "capability_receipt": compact_receipt(receipt),
    }
