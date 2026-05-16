from __future__ import annotations

from typing import Any

from .models import _bounded_params

_DRY_RUN_NOTE = "dry-run only — no external call was made"
_ACTION_CAP = 120
_LIVE_BLOCKED_MSG = "live invocations are not yet enabled; use dry_run=true"


class IntegrationError(ValueError):
    pass


class ComposioAdapter:
    """Skeleton adapter for Composio external integrations.

    Only dry-run is enabled in this sprint. All methods return a structured
    preview of what would be invoked without making any external call.
    """

    def invoke(
        self,
        action: str,
        params: dict[str, Any],
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if not dry_run:
            raise IntegrationError(_LIVE_BLOCKED_MSG)
        safe_action = str(action)[:_ACTION_CAP]
        return {
            "ok": True,
            "dry_run": True,
            "integration_type": "composio",
            "would_call": f"composio.{safe_action}",
            "params_preview": _bounded_params(params),
            "note": _DRY_RUN_NOTE,
            "artifacts": {},
        }


class RubeAdapter:
    """Skeleton adapter for Rube external integrations.

    Only dry-run is enabled in this sprint. All methods return a structured
    preview of what would be invoked without making any external call.
    """

    def invoke(
        self,
        action: str,
        params: dict[str, Any],
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if not dry_run:
            raise IntegrationError(_LIVE_BLOCKED_MSG)
        safe_action = str(action)[:_ACTION_CAP]
        return {
            "ok": True,
            "dry_run": True,
            "integration_type": "rube",
            "would_call": f"rube.{safe_action}",
            "params_preview": _bounded_params(params),
            "note": _DRY_RUN_NOTE,
            "artifacts": {},
        }


_ADAPTERS: dict[str, ComposioAdapter | RubeAdapter] = {
    "composio": ComposioAdapter(),
    "rube": RubeAdapter(),
}


def get_adapter(integration_type: str) -> ComposioAdapter | RubeAdapter:
    adapter = _ADAPTERS.get(integration_type)
    if adapter is None:
        raise IntegrationError(f"no adapter registered for integration_type: {integration_type!r}")
    return adapter
