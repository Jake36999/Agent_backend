from __future__ import annotations

import json
import os
import socket
import time
import traceback
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Aletheia_Orchestrator_Shim")

BRIDGE_HOST = os.environ.get("ALETHEIA_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("ALETHEIA_BRIDGE_PORT", "8765"))
BRIDGE_TIMEOUT_SECONDS = float(os.environ.get("ALETHEIA_BRIDGE_TIMEOUT_SECONDS", "180"))
MAX_RESPONSE_BYTES = int(os.environ.get("ALETHEIA_SHIM_MAX_RESPONSE_BYTES", "25000000"))


class BridgeCallError(RuntimeError):
    """Raised internally when the local Aletheia daemon bridge rejects or fails a request."""


def as_pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)


def error_payload(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": code,
        "message": str(message),
        "bridge": {
            "host": BRIDGE_HOST,
            "port": BRIDGE_PORT,
            "timeout_seconds": BRIDGE_TIMEOUT_SECONDS,
        },
    }
    if details:
        payload["details"] = details
    return payload


def call_bridge(method: str, params: dict[str, Any]) -> dict[str, Any]:
    request = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params,
    }

    try:
        with socket.create_connection(
            (BRIDGE_HOST, BRIDGE_PORT),
            timeout=BRIDGE_TIMEOUT_SECONDS,
        ) as sock:
            sock.settimeout(BRIDGE_TIMEOUT_SECONDS)
            payload = json.dumps(request, separators=(",", ":")) + "\n"
            sock.sendall(payload.encode("utf-8"))

            chunks: list[bytes] = []
            total = 0
            while True:
                data = sock.recv(65536)
                if not data:
                    break
                chunks.append(data)
                total += len(data)

                if total > MAX_RESPONSE_BYTES:
                    raise BridgeCallError(
                        f"Aletheia bridge response exceeded {MAX_RESPONSE_BYTES} bytes"
                    )

                if b"\n" in data:
                    break

    except OSError as exc:
        raise BridgeCallError(
            f"Could not connect to Aletheia bridge at {BRIDGE_HOST}:{BRIDGE_PORT}: {exc}"
        ) from exc

    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw:
        raise BridgeCallError("Aletheia bridge returned an empty response")

    try:
        response = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BridgeCallError(f"Aletheia bridge returned invalid JSON: {raw[:1000]}") from exc

    if "error" in response:
        raise BridgeCallError(as_pretty_json(response["error"]))

    result = response.get("result", {})
    if not isinstance(result, dict):
        return {"ok": True, "result": result}
    return result


def call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        return call_bridge(
            "tools.call",
            {
                "toolName": tool_name,
                "args": args,
            },
        )
    except BridgeCallError as exc:
        return error_payload(
            "bridge_call_failed",
            str(exc),
            details={"tool_name": tool_name, "args": args},
        )
    except Exception as exc:
        return error_payload(
            "shim_unhandled_exception",
            str(exc),
            details={
                "tool_name": tool_name,
                "args": args,
                "traceback": traceback.format_exc(limit=5),
            },
        )


@mcp.tool()
def mcp_agent_workflow_run(
    objective: str,
    target_repo: str,
    profile: str = "safe",
    allow_ingest: bool = False,
    include_report_preview: bool = False,
    use_model_phases: bool = False,
) -> str:
    """Run the deterministic Tool Assist workflow once.

    target_repo must be the exact absolute local path to investigate.
    Do not infer, abbreviate, or invent target_repo.
    Recommended LM Studio exposure is allowed_tools = ["mcp_agent_workflow_run"].
    """
    result = call_tool(
        "mcp_agent_workflow_run",
        {
            "objective": objective,
            "target_repo": target_repo,
            "profile": profile,
            "allow_ingest": allow_ingest,
            "include_report_preview": include_report_preview,
            "use_model_phases": use_model_phases,
        },
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_scout_workspace(
    project_id: str,
    absolute_path: str,
    max_files: int = 500,
    include_summaries: bool = True,
) -> str:
    result = call_tool(
        "mcp_scout_workspace",
        {
            "project_id": project_id,
            "absolute_path": absolute_path,
            "max_files": max_files,
            "include_summaries": include_summaries,
        },
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_ingest_target(
    project_id: str,
    absolute_path: str,
    mime_type: str | None = None,
    force_reindex: bool = False,
) -> str:
    args: dict[str, Any] = {
        "project_id": project_id,
        "absolute_path": absolute_path,
        "force_reindex": force_reindex,
    }
    if mime_type:
        args["mime_type"] = mime_type

    result = call_tool("mcp_ingest_target", args)
    return as_pretty_json(result)


@mcp.tool()
def mcp_semantic_search(project_id: str, query: str, k: int = 8) -> str:
    result = call_tool(
        "mcp_semantic_search",
        {
            "project_id": project_id,
            "query": query,
            "k": k,
        },
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_verify_integrity(
    absolute_path: str,
    expected_sha256: str,
    expected_metadata_hash: str,
) -> str:
    result = call_tool(
        "mcp_verify_integrity",
        {
            "absolute_path": absolute_path,
            "expected_sha256": expected_sha256,
            "expected_metadata_hash": expected_metadata_hash,
        },
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_extract_image(
    absolute_path: str,
    page: int | None = None,
    region: dict[str, int] | None = None,
) -> str:
    args: dict[str, Any] = {"absolute_path": absolute_path}
    if page is not None:
        args["page"] = page
    if region is not None:
        args["region"] = region

    result = call_tool("mcp_extract_image", args)
    return as_pretty_json(result)


@mcp.tool()
def mcp_investigation_start(objective: str, target_repo: str, profile: str = "safe") -> str:
    result = call_tool(
        "mcp_investigation_start",
        {"objective": objective, "target_repo": target_repo, "profile": profile},
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_investigation_filemap(session_path: str, profile: str = "safe") -> str:
    result = call_tool(
        "mcp_investigation_filemap",
        {"session_path": session_path, "profile": profile},
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_investigation_validate_manifest(session_path: str) -> str:
    result = call_tool("mcp_investigation_validate_manifest", {"session_path": session_path})
    return as_pretty_json(result)


@mcp.tool()
def mcp_investigation_read_report(session_path: str, artifact_key: str, max_chars: int = 12000) -> str:
    result = call_tool(
        "mcp_investigation_read_report",
        {
            "session_path": session_path,
            "artifact_key": artifact_key,
            "max_chars": max_chars,
        },
    )

    compact: dict[str, Any] = {
        "ok": bool(result.get("ok", False)),
        "status": str(result.get("status", "")),
        "summary": str(result.get("summary", "")),
        "artifacts": result.get("artifacts", {}),
        "recommended_next_tool": result.get("recommended_next_tool", ""),
    }

    if "error" in result:
        compact["error"] = result["error"]

    if "content_omitted" in result:
        compact["content_omitted"] = bool(result.get("content_omitted"))

    if "char_count" in result:
        compact["char_count"] = int(result.get("char_count") or 0)

    if "content" in result:
        compact["content_omitted"] = True
        compact["char_count"] = len(str(result.get("content", "")))

    return as_pretty_json(compact)


@mcp.tool()
def mcp_investigation_compile_handoff(session_path: str) -> str:
    result = call_tool("mcp_investigation_compile_handoff", {"session_path": session_path})
    return as_pretty_json(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
