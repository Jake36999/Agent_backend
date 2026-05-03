from __future__ import annotations

import json
import os
import socket
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Aletheia_Orchestrator_Shim")

BRIDGE_HOST = os.environ.get("ALETHEIA_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("ALETHEIA_BRIDGE_PORT", "8765"))
BRIDGE_TIMEOUT_SECONDS = float(os.environ.get("ALETHEIA_BRIDGE_TIMEOUT_SECONDS", "30"))


class BridgeCallError(RuntimeError):
    """Raised when the local Aletheia daemon bridge rejects or fails a request."""


def call_bridge(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Call the local Aletheia Python daemon JSON-RPC bridge.

    This shim intentionally uses the unauthenticated local bridge path.
    Run the daemon without ALETHEIA_BRIDGE_SECRET while using this version.

    Expected topology:
      LM Studio -> this FastMCP stdio shim -> 127.0.0.1:8765 -> Aletheia daemon
    """
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    try:
        with socket.create_connection(
            (BRIDGE_HOST, BRIDGE_PORT),
            timeout=BRIDGE_TIMEOUT_SECONDS,
        ) as sock:
            payload = json.dumps(request, separators=(",", ":")) + "\n"
            sock.sendall(payload.encode("utf-8"))

            chunks: list[bytes] = []
            while True:
                data = sock.recv(65536)
                if not data:
                    break
                chunks.append(data)
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
        raise BridgeCallError(f"Aletheia bridge returned invalid JSON: {raw[:500]}") from exc

    if "error" in response:
        raise BridgeCallError(response["error"])

    result = response.get("result", {})
    if not isinstance(result, dict):
        return {"result": result}
    return result


def call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Forward an MCP tool call to the Aletheia daemon.

    The Python bridge expects params.toolName, not params.tool.
    It also accepts params.name, but toolName matches the backend test contract.
    """
    return call_bridge(
        "tools.call",
        {
            "toolName": tool_name,
            "args": args,
        },
    )


def as_pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


@mcp.tool()
def mcp_scout_workspace(
    project_id: str,
    absolute_path: str,
    max_files: int = 500,
    include_summaries: bool = True,
) -> str:
    """
    Inspect a workspace without indexing vectors.

    Use this before ingestion to confirm the path, skipped-file policy, and project shape.
    """
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
    """
    Index one file or directory into the Aletheia SQLite manifest and Chroma vector store.
    """
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
    """
    Search indexed semantic memory for a project.
    """
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
    """
    Verify file content and metadata hashes.
    """
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
    """
    Extract text from an image or non-selectable document region through the configured OCR provider.
    """
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
        {"session_path": session_path, "artifact_key": artifact_key, "max_chars": max_chars},
    )
    return as_pretty_json(result)


@mcp.tool()
def mcp_investigation_compile_handoff(session_path: str) -> str:
    result = call_tool("mcp_investigation_compile_handoff", {"session_path": session_path})
    return as_pretty_json(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
