from __future__ import annotations

from typing import Any


def compact_tool_result(
    tool_name: str,
    raw: dict[str, Any],
    max_chars: int = 2000,
    include_content: bool = False,
) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    artifacts_raw = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    artifacts = {str(key): str(value) for key, value in artifacts_raw.items() if value is not None}
    top_candidates_raw = payload.get("top_candidates") if isinstance(payload.get("top_candidates"), list) else []
    summary = str(payload.get("summary") or payload.get("message") or payload.get("status") or tool_name)[:1000]
    compact: dict[str, Any] = {
        "ok": bool(payload.get("ok", False)),
        "status": str(payload.get("status", "ERROR")),
        "summary": summary,
        "artifacts": artifacts,
        "top_candidates": top_candidates_raw[:10],
        "recommended_next_tool": str(payload.get("recommended_next_tool", "")),
        "content_omitted": True,
    }
    if include_content and isinstance(payload.get("content"), str):
        content = str(payload["content"])
        compact["content_preview"] = content[: max(1, int(max_chars))]
        compact["content_omitted"] = len(content) > max(1, int(max_chars))
    return compact
