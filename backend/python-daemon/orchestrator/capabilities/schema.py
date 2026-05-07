from __future__ import annotations

from .models import VALID_RISK_TIERS, VALID_STATUSES, CapabilityType


class CapabilitySchemaError(ValueError):
    pass


def validate_capability_manifest(data: dict) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["manifest must be a mapping"]

    required = {"capability_id", "capability_type", "version", "risk_tier"}
    missing = required - set(data.keys())
    if missing:
        errors.append(f"missing required fields: {', '.join(sorted(missing))}")
        return errors

    cid = data.get("capability_id", "")
    if not isinstance(cid, str) or not cid:
        errors.append("capability_id must be a non-empty string")

    ct = data.get("capability_type", "")
    valid_types = {t.value for t in CapabilityType}
    if ct not in valid_types:
        errors.append(f"capability_type must be one of: {', '.join(sorted(valid_types))}")

    rt = data.get("risk_tier", "")
    if rt not in VALID_RISK_TIERS:
        errors.append(f"risk_tier must be one of: {', '.join(sorted(VALID_RISK_TIERS))}")

    status = data.get("status", "verified")
    if status not in VALID_STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    version = data.get("version", "")
    if not isinstance(version, str) or not version:
        errors.append("version must be a non-empty string")

    for bool_field in ("requires_approval", "network_access", "writes_external_state"):
        val = data.get(bool_field)
        if val is not None and not isinstance(val, bool):
            errors.append(f"{bool_field} must be a boolean")

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append("metadata must be an object")

    return errors
