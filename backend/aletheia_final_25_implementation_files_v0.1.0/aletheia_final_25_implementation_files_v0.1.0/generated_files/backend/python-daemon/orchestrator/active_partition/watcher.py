from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from .service import ActivePartitionService


class ActivePartitionWatcher:
    """Dependency-free polling watcher for LM Studio conversation paths.

    The watcher deliberately does not parse conversation JSON. It observes file
    paths only, waits for size/mtime to settle, and delegates project mapping to
    ActivePartitionService.set_active_from_conversation_path.
    """

    def __init__(
        self,
        service: ActivePartitionService,
        conversations_root: Path,
        *,
        settle_ms: int = 750,
        logger: logging.Logger | None = None,
    ) -> None:
        self.service = service
        self.conversations_root = Path(conversations_root).expanduser().resolve()
        self.settle_ms = max(0, int(settle_ms))
        self.logger = logger or logging.getLogger(__name__)
        self._last_applied_path: Path | None = None
        self._last_applied_mtime_ns: int | None = None

    def poll_once(self) -> dict[str, object]:
        if not self.conversations_root.exists():
            return self._result(False, "CONVERSATIONS_ROOT_NOT_FOUND", None, message=f"Conversation root not found: {self.conversations_root}")
        candidate = self._newest_conversation_file()
        if candidate is None:
            return self._result(True, "NO_CONVERSATIONS_FOUND", None, message="No *.conversation.json files found.")
        return self._handle_conversation_path(candidate)

    async def run_forever(
        self,
        stop_event: asyncio.Event,
        *,
        interval_seconds: float = 1.0,
    ) -> None:
        interval = max(0.05, float(interval_seconds))
        while not stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                self.logger.exception("active partition watcher poll failed")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    def _newest_conversation_file(self) -> Path | None:
        newest: tuple[int, Path] | None = None
        for path in self.conversations_root.rglob("*.conversation.json"):
            if not path.is_file():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            item = (stat.st_mtime_ns, path.resolve())
            if newest is None or item[0] > newest[0] or (item[0] == newest[0] and str(item[1]) > str(newest[1])):
                newest = item
        return newest[1] if newest else None

    def _handle_conversation_path(self, path: Path) -> dict[str, object]:
        candidate = Path(path).expanduser().resolve()
        if not self._is_within_root(candidate):
            return self._result(False, "POLICY_BLOCK", candidate, message="Conversation path is outside watcher root.")
        if not self._is_settled(candidate):
            return self._result(True, "UNSTABLE", candidate, message="Conversation file is still changing; skipped this poll.")
        try:
            stat = candidate.stat()
        except OSError as exc:
            return self._result(False, "FILE_UNAVAILABLE", candidate, message=str(exc))
        if self._last_applied_path == candidate and self._last_applied_mtime_ns == stat.st_mtime_ns:
            return self._result(True, "UNCHANGED", candidate, message="Newest conversation already applied.")

        result = self.service.set_active_from_conversation_path(str(candidate))
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result) if isinstance(result, dict) else {}
        status = str(payload.get("status") or ("OK" if payload.get("ok") else "ERROR"))
        ok = bool(payload.get("ok", status == "OK"))
        if ok:
            self._last_applied_path = candidate
            self._last_applied_mtime_ns = stat.st_mtime_ns
        return {
            "ok": ok,
            "status": status,
            "conversation_path": str(candidate),
            "project_id": payload.get("project_id"),
            "project_scope_hash": payload.get("project_scope_hash"),
            "source_event": "lmstudio_conversation_watcher",
            "message": str(payload.get("message") or status),
        }

    def _is_within_root(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return resolved == self.conversations_root or self.conversations_root in resolved.parents
        except OSError:
            return False

    def _is_settled(self, path: Path) -> bool:
        if self.settle_ms <= 0:
            return True
        try:
            first = path.stat()
            time.sleep(self.settle_ms / 1000.0)
            second = path.stat()
        except OSError:
            return False
        return first.st_size == second.st_size and first.st_mtime_ns == second.st_mtime_ns

    def _result(self, ok: bool, status: str, path: Path | None, *, message: str) -> dict[str, object]:
        return {
            "ok": ok,
            "status": status,
            "conversation_path": str(path) if path is not None else None,
            "project_id": None,
            "project_scope_hash": None,
            "source_event": "lmstudio_conversation_watcher",
            "message": message,
        }
