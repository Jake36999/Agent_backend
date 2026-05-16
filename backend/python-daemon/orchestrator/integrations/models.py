from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Capability descriptors — not DB-registered; document intent for policy checks.
COMPOSIO_CAPABILITY = {
    "capability_id": "integration.composio",
    "capability_type": "integration_provider",
    "risk_tier": "T4",
    "requires_approval": True,
    "network_access": True,
    "writes_external_state": True,
    "status": "disabled",
    "description": (
        "Composio external integration adapter. "
        "Dry-run enabled; live invocations blocked until approval workflow is wired."
    ),
}

RUBE_CAPABILITY = {
    "capability_id": "integration.rube",
    "capability_type": "integration_provider",
    "risk_tier": "T4",
    "requires_approval": True,
    "network_access": True,
    "writes_external_state": True,
    "status": "disabled",
    "description": (
        "Rube external integration adapter. "
        "Dry-run enabled; live invocations blocked until approval workflow is wired."
    ),
}

KNOWN_INTEGRATION_TYPES: frozenset[str] = frozenset({"composio", "rube"})

_PARAMS_CAP = 20          # max number of params entries
_PARAM_STR_CAP = 200      # max chars per string param value
_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "key", "secret", "token", "password", "auth", "credential",
    "api_key", "apikey", "access_token",
})


def _bounded_params(params: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitised, size-bounded copy of params safe for logging/receipts."""
    out: dict[str, Any] = {}
    for k, v in list(params.items())[:_PARAMS_CAP]:
        k_lower = str(k).lower()
        if any(sk in k_lower for sk in _SENSITIVE_KEYS):
            out[k] = "[redacted]"
        elif isinstance(v, str):
            out[k] = v[:_PARAM_STR_CAP]
        else:
            out[k] = v
    return out


@dataclass(frozen=True)
class IntegrationRequest:
    integration_type: str       # "composio" | "rube"
    action: str                 # action/method identifier
    params: dict[str, Any]      # action parameters
    dry_run: bool               # must be True in this sprint
    approval_id: str | None     # required for live invocations (future)


@dataclass(frozen=True)
class IntegrationDecision:
    allowed: bool
    verdict: str                # "allow" | "require_approval" | "block"
    risk_tier: str              # "T2" (dry-run) | "T4" (live)
    reason: str
    integration_type: str
    dry_run: bool
