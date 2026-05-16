from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Verdict = Literal["allow", "read_only", "require_approval", "block"]

# Risk level → profile → verdict
_VERDICT_TABLE: dict[str, dict[str, Verdict]] = {
    "read_only":    {"safe": "allow",            "trusted": "allow"},
    "write_memory": {"safe": "allow",            "trusted": "allow"},
    "write_files":  {"safe": "require_approval", "trusted": "allow"},
    "admin":        {"safe": "block",            "trusted": "require_approval"},
}

# Mirrors tool_manifest.json risk_level fields — kept in sync manually.
_KNOWN_RISK_LEVELS: dict[str, str] = {
    "mcp_agent_workflow_run":           "read_only",
    "mcp_code_intelligence":            "read_only",
    "mcp_commit_memory":                "write_memory",
    "mcp_extract_image":                "read_only",
    "mcp_get_active_partition":         "read_only",
    "mcp_ingest_target":                "write_files",
    "mcp_investigation_compile_handoff":"read_only",
    "mcp_investigation_filemap":        "read_only",
    "mcp_investigation_read_report":    "read_only",
    "mcp_investigation_start":          "read_only",
    "mcp_investigation_validate_manifest": "read_only",
    "mcp_list_capabilities":            "read_only",
    "mcp_list_memory_projects":         "read_only",
    "mcp_sandbox_probe":                "read_only",
    "mcp_scout_workspace":              "read_only",
    "mcp_semantic_search":              "read_only",
    "mcp_semantic_search_active":       "read_only",
    "mcp_set_active_partition":         "write_memory",
    "mcp_set_active_project_manual":    "admin",
    "mcp_verify_integrity":             "read_only",
}

_RISK_TIER: dict[str, str] = {
    "read_only":    "T1",
    "write_memory": "T2",
    "write_files":  "T3",
    "admin":        "T4",
}


@dataclass(frozen=True)
class SandboxDecision:
    verdict: str          # "allow" | "read_only" | "require_approval" | "block"
    reason: str
    risk_tier: str        # "T1" | "T2" | "T3" | "T4" | "UNKNOWN"
    tool_name: str
    requires_root: bool
    allowed: bool         # True when verdict == "allow"


def classify_sandbox_request(
    tool_name: str,
    args: dict[str, Any],
    profile: str = "safe",
    *,
    risk_level: str | None = None,
    requires_root: bool = False,
) -> SandboxDecision:
    """Classify a tool invocation into a sandbox verdict.

    risk_level overrides the built-in lookup when provided.
    Unknown tools or unknown risk levels are blocked.
    Unknown profiles are treated as 'safe' (most restrictive).
    """
    effective_risk = risk_level if risk_level is not None else _KNOWN_RISK_LEVELS.get(tool_name)

    if effective_risk is None:
        return SandboxDecision(
            verdict="block",
            reason=f"unknown tool: {tool_name!r}",
            risk_tier="UNKNOWN",
            tool_name=tool_name,
            requires_root=requires_root,
            allowed=False,
        )

    profile_verdicts = _VERDICT_TABLE.get(effective_risk)
    if profile_verdicts is None:
        return SandboxDecision(
            verdict="block",
            reason=f"unknown risk_level: {effective_risk!r}",
            risk_tier="UNKNOWN",
            tool_name=tool_name,
            requires_root=requires_root,
            allowed=False,
        )

    effective_profile = profile if profile in profile_verdicts else "safe"
    verdict: Verdict = profile_verdicts[effective_profile]
    tier = _RISK_TIER.get(effective_risk, "UNKNOWN")

    reason_map: dict[str, str] = {
        "allow": f"{effective_risk} tool allowed under {effective_profile!r} profile",
        "read_only": f"{effective_risk} tool allowed read-only under {effective_profile!r} profile",
        "require_approval": f"{effective_risk} tool requires approval under {effective_profile!r} profile",
        "block": f"{effective_risk} tool blocked under {effective_profile!r} profile",
    }

    return SandboxDecision(
        verdict=verdict,
        reason=reason_map.get(verdict, verdict),
        risk_tier=tier,
        tool_name=tool_name,
        requires_root=requires_root,
        allowed=verdict == "allow",
    )
