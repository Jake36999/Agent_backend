from __future__ import annotations

import json
import os
import socket
from typing import Any


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
        self.timeout = timeout
        self.max_response_bytes = int(max_response_bytes or os.getenv("ALETHEIA_SHIM_MAX_RESPONSE_BYTES", "25000000"))

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools.call",
                "params": {"toolName": tool_name, "args": args},
            }
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
                chunks: list[bytes] = []
                total = 0
                while True:
                    data = sock.recv(65536)
                    if not data:
                        break
                    chunks.append(data)
                    total += len(data)
                    if total > self.max_response_bytes:
                        return self._error(f"response exceeded {self.max_response_bytes} bytes")
                    if b"\n" in data:
                        break
            raw = b"".join(chunks).split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
            if not raw:
                return self._error("empty response")
            try:
                response = json.loads(raw)
            except json.JSONDecodeError as exc:
                return self._error(f"malformed JSON: {exc}")
            if "error" in response:
                return self._error(json.dumps(response["error"], sort_keys=True))
            result = response.get("result", {})
            if isinstance(result, dict):
                return result
            return {"ok": True, "status": "PASS", "summary": "bridge returned non-object result", "artifacts": {}, "result": result}
        except (OSError, TimeoutError, socket.timeout) as exc:
            return self._error(str(exc))

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "ERROR",
            "summary": f"bridge_call_failed: {message}"[:1000],
            "artifacts": {},
        }
