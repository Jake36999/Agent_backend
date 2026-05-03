from __future__ import annotations

from typing import Any


def _cap(value: Any, limit: int) -> str:
    return str(value or "")[: max(0, limit)]


def compact_tool_result(
    tool_name: str,
    raw: dict[str, Any],
    max_chars: int = 2000,
    include_content: bool = False,
) -> dict[str, Any]:
    artifacts = raw.get("artifacts") if isinstance(raw.get("artifacts"), dict) else {}
    compact: dict[str, Any] = {
        "tool_name": tool_name,
        "ok": bool(raw.get("ok", False)),
        "status": str(raw.get("status", "ERROR")),
        "summary": _cap(raw.get("summary") or raw.get("message") or raw.get("error"), 1000),
        "artifacts": {str(k): str(v) for k, v in artifacts.items() if isinstance(v, (str, int, float))},
        "top_candidates": raw.get("top_candidates", [])[:10] if isinstance(raw.get("top_candidates"), list) else [],
        "recommended_next_tool": str(raw.get("recommended_next_tool", "")),
        "content_omitted": False,
    }
    if isinstance(raw.get("error"), dict):
        compact["error"] = {
            "code": str(raw["error"].get("code", "tool_error")),
            "message": _cap(raw["error"].get("message", compact["summary"]), 1000),
        }
    elif isinstance(raw.get("error"), str):
        compact["error"] = {"code": "tool_error", "message": _cap(raw["error"], 1000)}

    content = raw.get("content")
    if isinstance(content, str):
        compact["content_omitted"] = True
        if include_content:
            compact["content_preview"] = content[: max(0, max_chars)]
            compact["content_omitted"] = len(content) > max_chars
    return compact
