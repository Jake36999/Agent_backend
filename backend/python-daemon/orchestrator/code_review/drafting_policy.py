from __future__ import annotations

import os
from typing import Any

# Feature flag — disabled by default.
# Set ALETHEIA_ENABLE_REVIEW_DRAFTING=true to allow model-assisted review drafting.
# When disabled, WorkflowRunner skips the draft_review() call entirely.
_ENV_VAR = "ALETHEIA_ENABLE_REVIEW_DRAFTING"

# Stub capability descriptor — not registered in the DB, not a public MCP tool.
# Documents intent so policy checks are self-describing.
REVIEW_DRAFTING_CAPABILITY = {
    "capability_id": "review_drafting.lm_assisted",
    "capability_type": "adapter",
    "risk_tier": "T3",
    "requires_approval": True,
    "network_access": True,
    "writes_external_state": False,
    "status": "disabled",
    "description": (
        "LM-assisted review drafting via review_drafter.py. "
        "Requires ALETHEIA_ENABLE_REVIEW_DRAFTING=true and an injected lm_client."
    ),
}


def is_drafting_enabled() -> bool:
    """Return True only when ALETHEIA_ENABLE_REVIEW_DRAFTING is explicitly 'true'."""
    return os.getenv(_ENV_VAR, "").strip().lower() == "true"


def can_draft_review(*, pipeline_id: str, lm_client: Any | None) -> dict:
    """Return a decision dict indicating whether model-assisted drafting is permitted."""
    if not is_drafting_enabled():
        return {"allowed": False, "reason": "drafting_disabled"}
    if lm_client is None:
        return {"allowed": False, "reason": "no_lm_client"}
    if pipeline_id != "code_review":
        return {"allowed": False, "reason": "wrong_pipeline"}
    return {"allowed": True, "reason": "authorized"}
