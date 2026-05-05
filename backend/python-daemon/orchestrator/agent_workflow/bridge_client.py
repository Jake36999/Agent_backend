from __future__ import annotations

import json
import hashlib
import hmac
import os
import socket
import time
import uuid
from typing import Any, Callable


class TcpBridgeClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float = 30.0,
        max_response_bytes: int | None = None,
    ) -> None:
        self.host = host or os.getenv("ALETHEIA_BRIDGE_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("ALETHEIA_BRIDGE_PORT", "8765"))
        self.timeout = float(timeout)
        self.max_response_bytes = int(max_response_bytes or os.getenv("ALETHEIA_SHIM_MAX_RESPONSE_BYTES", "25000000"))
        self.shared_secret = os.getenv("ALETHEIA_BRIDGE_SECRET")

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools.call",
            "params": {
                "toolName": tool_name,
                "args": args,
            },
        }
        if self.shared_secret:
            request["params"]["auth"] = self._build_auth_envelope(request, self.shared_secret)

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                payload = json.dumps(request, separators=(",", ":")) + "\n"
                sock.sendall(payload.encode("utf-8"))

                chunks: list[bytes] = []
                total = 0
                while True:
                    try:
                        data = sock.recv(65536)
                    except socket.timeout:
                        return self._error("bridge_call_failed", f"bridge_call_failed: timeout waiting for {tool_name}")
                    if not data:
                        break
                    chunks.append(data)
                    total += len(data)
                    if total > self.max_response_bytes:
                        return self._error(
                            "bridge_call_failed",
                            f"bridge_call_failed: bridge response exceeded {self.max_response_bytes} bytes",
                        )
                    if b"\n" in data:
                        break
        except OSError as exc:
            return self._error("bridge_call_failed", f"bridge_call_failed: {exc}")

        raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
        if not raw:
            return self._error("bridge_call_failed", "bridge_call_failed: empty bridge response")

        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            return self._error("bridge_call_failed", f"bridge_call_failed: invalid JSON response ({exc})")

        if not isinstance(response, dict):
            return self._error("bridge_call_failed", "bridge_call_failed: bridge returned a non-object response")

        if "error" in response:
            error = response.get("error")
            if isinstance(error, dict):
                message = str(error.get("message", "bridge error"))
                code = str(error.get("code", "bridge_error"))
            else:
                message = str(error)
                code = "bridge_error"
            return self._error(code, f"bridge_call_failed: {message}")

        result = response.get("result")
        if isinstance(result, dict):
            return result
        return {"ok": True, "status": "OK", "summary": "Bridge call completed.", "result": result, "artifacts": {}}

    def _error(self, code: str, summary: str) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "ERROR",
            "summary": summary,
            "artifacts": {},
            "error": {"code": code, "message": summary},
        }

    def _build_auth_envelope(
        self,
        message: dict[str, Any],
        shared_secret: str,
        *,
        timestamp: str | None = None,
        nonce: str | None = None,
    ) -> dict[str, str]:
        timestamp = timestamp or str(int(time.time()))
        nonce = nonce or str(uuid.uuid4())
        sanitized = json.loads(json.dumps(message, sort_keys=True, separators=(",", ":")))
        params = dict(sanitized.get("params") or {})
        params.pop("auth", None)
        sanitized["params"] = params
        payload = f"{timestamp}.{nonce}.{json.dumps(sanitized, sort_keys=True, separators=(',', ':'))}".encode("utf-8")
        signature = hmac.new(shared_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return {"timestamp": timestamp, "signature": signature, "nonce": nonce}


class DirectToolExecutor:
    def __init__(
        self,
        dispatch: Callable[[str, dict[str, Any]], dict[str, Any]],
        *,
        allowed_tools: set[str] | tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.dispatch = dispatch
        self.allowed_tools = set(allowed_tools or ())

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return {
                "ok": False,
                "status": "POLICY_BLOCK",
                "summary": f"tool not allowed in direct workflow executor: {tool_name}",
                "artifacts": {},
                "error": {"code": "tool_not_allowed", "message": tool_name},
            }
        return self.dispatch(tool_name, args)


class InProcessToolClient(DirectToolExecutor):
    """Alias for the in-process workflow tool executor."""
