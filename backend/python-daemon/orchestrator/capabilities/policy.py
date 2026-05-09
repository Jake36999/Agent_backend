from __future__ import annotations

from typing import TYPE_CHECKING

from .models import CapabilityManifest

if TYPE_CHECKING:
    from .registry import CapabilityRegistry


class CapabilityPolicyError(ValueError):
    pass


RISK_TIER_REQUIRES_APPROVAL = {"T3", "T4", "T5"}


def check_pipeline_policy(
    pipeline_id: str,
    registry: "CapabilityRegistry | None",
) -> str | None:
    """Check policy for a pipeline. Returns an error message if blocked, None if allowed."""
    if registry is None:
        return None
    capability_id = f"pipeline_template.{pipeline_id}"
    manifest = registry.get(capability_id)
    if manifest is None:
        return None
    try:
        enforce_capability_policy(manifest)
    except CapabilityPolicyError as exc:
        return str(exc)
    return None


def enforce_capability_policy(manifest: CapabilityManifest) -> None:
    if manifest.status == "quarantined":
        raise CapabilityPolicyError(
            f"capability '{manifest.capability_id}' is quarantined and cannot be used"
        )
    if manifest.status == "disabled":
        raise CapabilityPolicyError(
            f"capability '{manifest.capability_id}' is disabled"
        )
    if manifest.risk_tier in RISK_TIER_REQUIRES_APPROVAL and not manifest.requires_approval:
        raise CapabilityPolicyError(
            f"capability '{manifest.capability_id}' has risk_tier {manifest.risk_tier} "
            f"but requires_approval is False — this violates policy"
        )
    if manifest.writes_external_state and not manifest.requires_approval:
        raise CapabilityPolicyError(
            f"capability '{manifest.capability_id}' writes external state "
            f"but requires_approval is False — this violates policy"
        )
