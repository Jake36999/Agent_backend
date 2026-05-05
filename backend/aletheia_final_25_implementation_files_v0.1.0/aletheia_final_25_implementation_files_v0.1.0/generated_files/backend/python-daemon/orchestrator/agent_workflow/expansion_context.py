from __future__ import annotations

from typing import Any


def compact_selected_skill(selected: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return model-safe selected-skill metadata for workflow artifacts."""
    if not selected:
        return None
    return {
        "skill_id": selected.get("skill_id") or selected.get("selected_skill_id"),
        "risk_tier": selected.get("risk_tier"),
        "candidate_analysis": list(selected.get("candidate_analysis", []))[:5]
        if isinstance(selected.get("candidate_analysis"), list) else [],
    }


def attach_compact_artifact(artifacts: dict[str, Any], key: str, value: Any, *, max_chars: int = 1000) -> None:
    """Attach bounded artifact metadata without large report bodies."""
    if value is None:
        return
    if isinstance(value, str):
        artifacts[key] = value[:max(1, int(max_chars))]
    elif isinstance(value, (int, float, bool)):
        artifacts[key] = value
    elif isinstance(value, dict):
        artifacts[key] = {str(k): str(v)[:max_chars] for k, v in list(value.items())[:20]}
    else:
        artifacts[key] = str(value)[:max_chars]
