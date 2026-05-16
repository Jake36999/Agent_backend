from __future__ import annotations

import os
from typing import Any


ALLOWED_TOOLS = {
    "mcp_agent_workflow_run",
    "mcp_commit_memory",
    "mcp_extract_image",
    "mcp_get_active_partition",
    "mcp_ingest_target",
    "mcp_investigation_compile_handoff",
    "mcp_investigation_filemap",
    "mcp_investigation_read_report",
    "mcp_investigation_start",
    "mcp_investigation_validate_manifest",
    "mcp_code_intelligence",
    "mcp_list_capabilities",
    "mcp_list_memory_projects",
    "mcp_scout_workspace",
    "mcp_semantic_search",
    "mcp_semantic_search_active",
    "mcp_set_active_partition",
    "mcp_integration_invoke",
    "mcp_sandbox_probe",
    "mcp_set_active_project_manual",
    "mcp_verify_integrity",
}

RAW_SHELL_TOOLS = {"sh", "bash", "shell", "exec", "python"}

REQUIRED_ARGS = {
    "mcp_agent_workflow_run": ("objective", "target_repo"),
    "mcp_commit_memory": ("category", "content"),
    "mcp_ingest_target": ("project_id", "absolute_path"),
    "mcp_investigation_compile_handoff": ("session_path",),
    "mcp_investigation_filemap": ("session_path",),
    "mcp_investigation_read_report": ("session_path", "artifact_key"),
    "mcp_investigation_start": ("objective", "target_repo"),
    "mcp_investigation_validate_manifest": ("session_path",),
    "mcp_code_intelligence": ("target_repo", "mode"),
    "mcp_semantic_search": ("project_id", "query"),
    "mcp_semantic_search_active": ("query",),
    "mcp_set_active_partition": ("conversation_path",),
    "mcp_integration_invoke": ("integration_type", "action"),
    "mcp_sandbox_probe": ("path", "operation"),
    "mcp_set_active_project_manual": ("project_id",),
    "mcp_scout_workspace": ("project_id", "absolute_path"),
    "mcp_verify_integrity": ("absolute_path", "expected_sha256", "expected_metadata_hash"),
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
    if tool_name in RAW_SHELL_TOOLS:
        return False, f"raw shell tool rejected: {tool_name}"
    if tool_name not in ALLOWED_TOOLS:
        return False, f"tool not allowlisted: {tool_name}"
    if not isinstance(args, dict):
        return False, "tool arguments must be an object"
    if tool_name == "mcp_ingest_target" and not allow_ingest:
        return False, "mcp_ingest_target is blocked unless ingest is explicitly allowed"

    required = REQUIRED_ARGS.get(tool_name, ())
    missing = [name for name in required if name not in args]
    if missing:
        return False, f"missing required args: {', '.join(missing)}"
    return True, ""
