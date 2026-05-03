from __future__ import annotations

import os
from typing import Any


ALLOWED_TOOLS = {
    "mcp_investigation_start",
    "mcp_investigation_filemap",
    "mcp_investigation_validate_manifest",
    "mcp_investigation_read_report",
    "mcp_investigation_compile_handoff",
    "mcp_scout_workspace",
    "mcp_semantic_search",
    "mcp_ingest_target",
}

RAW_TOOL_NAMES = {"sh", "bash", "shell", "exec", "python", "python3", "powershell", "cmd"}

REQUIRED_ARGS = {
    "mcp_investigation_start": ("objective", "target_repo", "profile"),
    "mcp_investigation_filemap": ("session_path",),
    "mcp_investigation_validate_manifest": ("session_path",),
    "mcp_investigation_read_report": ("session_path", "artifact_key"),
    "mcp_investigation_compile_handoff": ("session_path",),
}


def reasoning_policy() -> dict[str, str]:
    return {
        "PLAN": os.getenv("ALETHEIA_AGENT_REASONING_PLAN", "low"),
        "ACT": os.getenv("ALETHEIA_AGENT_REASONING_ACT", "off"),
        "CHECK": os.getenv("ALETHEIA_AGENT_REASONING_CHECK", "low"),
        "SYNTHESIZE": os.getenv("ALETHEIA_AGENT_REASONING_SYNTHESIZE", "low"),
        "FINAL": os.getenv("ALETHEIA_AGENT_REASONING_FINAL", "off"),
    }


def validate_tool(tool_name: str, args: dict[str, Any], allow_ingest: bool = False) -> tuple[bool, str]:
    normalized = str(tool_name).strip().lower()
    if normalized in RAW_TOOL_NAMES:
        return False, f"raw tool is not allowed: {tool_name}"
    if tool_name not in ALLOWED_TOOLS:
        return False, f"tool is not allowlisted: {tool_name}"
    if not isinstance(args, dict):
        return False, "tool args must be an object"
    if tool_name == "mcp_ingest_target" and not allow_ingest:
        return False, "mcp_ingest_target is blocked unless ingestion is explicitly allowed"
    for required in REQUIRED_ARGS.get(tool_name, ()):
        if required not in args or args.get(required) in (None, ""):
            return False, f"missing required argument: {required}"
    return True, ""
