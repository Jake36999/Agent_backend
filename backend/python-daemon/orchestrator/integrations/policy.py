from __future__ import annotations

from .models import IntegrationDecision, KNOWN_INTEGRATION_TYPES

# Live invocations are not yet enabled in this sprint.
# This flag gates all non-dry-run paths.
_LIVE_INVOCATIONS_ENABLED = False


def classify_integration_request(
    integration_type: str,
    action: str,
    dry_run: bool,
    profile: str = "safe",
) -> IntegrationDecision:
    """Return a policy decision for an integration invocation request.

    Rules:
    - Unknown integration_type → block.
    - dry_run=False → block (live invocations not yet enabled).
    - dry_run=True → allow with T2 risk tier (no external state written).
    - profile is recorded for future live-invocation gating.
    """
    if integration_type not in KNOWN_INTEGRATION_TYPES:
        return IntegrationDecision(
            allowed=False,
            verdict="block",
            risk_tier="UNKNOWN",
            reason=f"unknown integration_type: {integration_type!r}",
            integration_type=integration_type,
            dry_run=dry_run,
        )

    if not dry_run:
        if not _LIVE_INVOCATIONS_ENABLED:
            return IntegrationDecision(
                allowed=False,
                verdict="block",
                risk_tier="T4",
                reason=(
                    f"live {integration_type} invocations are not yet enabled; "
                    "set dry_run=true or wait for approval workflow"
                ),
                integration_type=integration_type,
                dry_run=dry_run,
            )
        # Future: profile-based verdict for live runs
        verdict = "require_approval" if profile in ("safe", "trusted") else "block"
        return IntegrationDecision(
            allowed=False,
            verdict=verdict,
            risk_tier="T4",
            reason=f"live {integration_type} invocation requires explicit approval",
            integration_type=integration_type,
            dry_run=dry_run,
        )

    return IntegrationDecision(
        allowed=True,
        verdict="allow",
        risk_tier="T2",
        reason=f"dry-run {integration_type} invocation allowed; no external state written",
        integration_type=integration_type,
        dry_run=True,
    )
