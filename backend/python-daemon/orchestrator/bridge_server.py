from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import logging
import time
from typing import Any

from .adapters import AdapterFailure, ToolAdapters

LOGGER = logging.getLogger(__name__)


class JsonRpcError(ValueError):
    pass


@dataclass(frozen=True)
class BridgeSecurity:
    shared_secret: str | None = None
    max_line_bytes: int = 1_000_000
    timestamp_tolerance_seconds: int = 300
    allowed_methods: tuple[str, ...] = ("tools.call", "daemon.health", "daemon.reconcile_project", "daemon.dead_letters")
    enable_admin_bridge: bool = False
    nonce_cache: set[str] = field(default_factory=set)


def line_too_large(line: bytes, security: BridgeSecurity) -> bool:
    return len(line) > security.max_line_bytes


def json_rpc_result(request_id: str | int | None, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def json_rpc_error(request_id: str | int | None, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def signing_payload(message: dict[str, Any], timestamp: str, nonce: str) -> bytes:
    sanitized = json.loads(canonical_json(message))
    params = dict(sanitized.get("params") or {})
    params.pop("auth", None)
    sanitized["params"] = params
    return f"{timestamp}.{nonce}.{canonical_json(sanitized)}".encode("utf-8")


def build_auth_envelope(message: dict[str, Any], shared_secret: str, *, timestamp: str | None = None, nonce: str | None = None) -> dict[str, str]:
    import uuid
    timestamp = timestamp or str(int(time.time()))
    nonce = nonce or str(uuid.uuid4())
    signature = hmac.new(
        shared_secret.encode("utf-8"),
        signing_payload(message, timestamp, nonce),
        hashlib.sha256,
    ).hexdigest()
    return {"timestamp": timestamp, "signature": signature, "nonce": nonce}


def _authorized(message: dict[str, Any], security: BridgeSecurity) -> bool:
    if security.shared_secret is None:
        return True
    auth = (message.get("params") or {}).get("auth")
    if not isinstance(auth, dict):
        return False
    timestamp = auth.get("timestamp")
    signature = auth.get("signature")
    nonce = auth.get("nonce")
    if not isinstance(timestamp, str) or not isinstance(signature, str) or not isinstance(nonce, str):
        return False
    if nonce in security.nonce_cache:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > security.timestamp_tolerance_seconds:
        return False
    expected = build_auth_envelope(message, security.shared_secret, timestamp=timestamp, nonce=nonce)["signature"]
    if not hmac.compare_digest(expected, signature):
        return False
    if len(security.nonce_cache) >= 4096:
        security.nonce_cache.clear()
    security.nonce_cache.add(nonce)
    return True


def handle_json_rpc(
    message: dict[str, Any],
    tool_adapters: ToolAdapters,
    security: BridgeSecurity | None = None,
    internal_api: Any | None = None,
) -> dict[str, Any]:
    security = security or BridgeSecurity()
    request_id = message.get("id")
    if message.get("jsonrpc") != "2.0":
        return json_rpc_error(request_id, -32600, "Invalid Request")
    method = message.get("method")
    LOGGER.info("bridge_request", extra={"extra_fields": {"request_id": request_id, "method": method}})
    if method not in security.allowed_methods:
        return json_rpc_error(request_id, -32601, "Method not found")
    if method.startswith("daemon.") and (not security.enable_admin_bridge or security.shared_secret is None):
        return json_rpc_error(request_id, -32002, "Admin bridge disabled")
    if not _authorized(message, security):
        return json_rpc_error(request_id, -32001, "Unauthorized")
    params = message.get("params") or {}
    if method == "daemon.health":
        if internal_api is None:
            return json_rpc_error(request_id, -32601, "Method not found")
        return json_rpc_result(request_id, internal_api.health())
    if method == "daemon.reconcile_project":
        if internal_api is None:
            return json_rpc_error(request_id, -32601, "Method not found")
        project_id = params.get("project_id")
        if not isinstance(project_id, str):
            return json_rpc_error(request_id, -32602, "Invalid params")
        return json_rpc_result(request_id, internal_api.reconcile_project(project_id))
    if method == "daemon.dead_letters":
        if internal_api is None:
            return json_rpc_error(request_id, -32601, "Method not found")
        return json_rpc_result(request_id, internal_api.dead_letters(int(params.get("limit", 50))))
    tool_name = params.get("toolName") or params.get("name")
    args = params.get("args") or params.get("arguments") or {}
    if not isinstance(tool_name, str) or not isinstance(args, dict):
        return json_rpc_error(request_id, -32602, "Invalid params")
    try:
        return json_rpc_result(request_id, tool_adapters.call_mcp_tool(tool_name, args))
    except AdapterFailure as exc:
        return json_rpc_result(request_id, {"ok": False, "error": "adapter_failure", "message": str(exc)})


async def serve_tcp_bridge(
    host: str,
    port: int,
    tool_adapters: ToolAdapters,
    security: BridgeSecurity | None = None,
    internal_api: Any | None = None,
) -> asyncio.AbstractServer:
    security = security or BridgeSecurity()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await reader.readline()
            if line_too_large(line, security):
                response = json_rpc_error(None, -32000, "Request too large")
                writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                await writer.drain()
                return
            message = json.loads(line.decode("utf-8"))
            response = handle_json_rpc(message, tool_adapters, security, internal_api)
            writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    return await asyncio.start_server(handle_client, host, port)
