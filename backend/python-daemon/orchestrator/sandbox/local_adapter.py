from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class SandboxError(ValueError):
    pass


_MAX_ENTRIES = 1000
_MAX_BYTES = 65536


class LocalSandboxAdapter:
    """Read-only local filesystem probes, path-validated against allowed_roots."""

    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)

    def _resolve(self, path: str) -> Path:
        resolved = Path(path).resolve()
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise SandboxError("path escapes allowed roots")
        return resolved

    def stat(self, path: str) -> dict[str, Any]:
        resolved = self._resolve(path)
        try:
            s = resolved.stat()
        except FileNotFoundError:
            return {"ok": False, "status": "NOT_FOUND", "path": path, "artifacts": {}}
        except Exception as exc:
            raise SandboxError(f"stat failed: {exc}") from exc
        return {
            "ok": True,
            "status": "OK",
            "path": str(resolved),
            "exists": True,
            "is_dir": resolved.is_dir(),
            "is_file": resolved.is_file(),
            "size_bytes": s.st_size,
            "mtime_ns": s.st_mtime_ns,
            "artifacts": {},
        }

    def list_dir(self, path: str, max_entries: int = 200) -> dict[str, Any]:
        resolved = self._resolve(path)
        if not resolved.is_dir():
            return {
                "ok": False,
                "status": "NOT_A_DIRECTORY",
                "path": path,
                "entries": [],
                "artifacts": {},
            }
        cap = max(1, min(int(max_entries), _MAX_ENTRIES))
        try:
            raw = sorted(os.listdir(resolved))
        except Exception as exc:
            raise SandboxError(f"list_dir failed: {exc}") from exc
        entries = raw[:cap]
        return {
            "ok": True,
            "status": "OK",
            "path": str(resolved),
            "entries": entries,
            "total_available": len(raw),
            "truncated": len(raw) > cap,
            "artifacts": {},
        }

    def read_head(self, path: str, max_bytes: int = 4096) -> dict[str, Any]:
        resolved = self._resolve(path)
        if not resolved.is_file():
            return {
                "ok": False,
                "status": "NOT_A_FILE",
                "path": path,
                "content": "",
                "artifacts": {},
            }
        cap = max(1, min(int(max_bytes), _MAX_BYTES))
        try:
            raw = resolved.read_bytes()[:cap]
        except Exception as exc:
            raise SandboxError(f"read_head failed: {exc}") from exc
        try:
            content = raw.decode("utf-8", errors="replace")
        except Exception:
            content = repr(raw[:200])
        return {
            "ok": True,
            "status": "OK",
            "path": str(resolved),
            "content": content,
            "bytes_read": len(raw),
            "truncated": resolved.stat().st_size > cap,
            "artifacts": {},
        }
