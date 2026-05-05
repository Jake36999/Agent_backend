from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from .service import ActivePartitionService, ActivePartitionServiceError


class ActivePartitionWatcher:
    """Polling watcher for LM Studio conversation paths.

    The watcher observes path metadata only. It never reads conversation JSON
    content and delegates all partition policy decisions to ActivePartitionService.
    """

    def __init__(
        self,
        service: ActivePartitionService,
        conversations_root: Path,
        *,
        settle_ms: int = 750,
        interval_seconds: float = 1.0,
        logger: logging.Logger | None = None,
    ) -> None:
        self.service = service
        self.conversations_root = Path(conversations_root).expanduser().resolve()
        self.settle_ms = max(0, int(settle_ms))
        self.interval_seconds = max(0.05, float(interval_seconds))
        self.logger = logger or logging.getLogger(__name__)
        self._last_applied_path: Path | None = None
        self._last_applied_mtime_ns: int | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def last_applied_path(self) -> Path | None:
        return self._last_applied_path

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self.run_until_stopped,
            name="aletheia-active-partition-watcher",
            daemon=False,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.1, float(timeout)))

    def run_until_stopped(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                self.logger.exception("active partition watcher poll failed")
            self._stop_event.wait(self.interval_seconds)

    def poll_once(self) -> dict[str, object]:
        if not self.conversations_root.exists():
            return self._result(
                False,
                "CONVERSATIONS_ROOT_NOT_FOUND",
                None,
                message=f"Conversation root not found: {self.conversations_root}",
            )
        candidate = self._newest_conversation_file()
        if candidate is None:
            return self._result(True, "NO_CONVERSATIONS_FOUND", None, message="No *.conversation.json files found.")
        return self.handle_conversation_path(candidate)

    def handle_conversation_path(self, path: Path) -> dict[str, object]:
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

        try:
            result = self.service.set_active_from_conversation_path(
                str(candidate),
                source_event="lmstudio_conversation_watcher",
            )
            payload = result.to_dict()
        except ActivePartitionServiceError as exc:
            payload = exc.to_dict()
            payload.setdefault("status", exc.code)
            payload.setdefault("ok", False)

        status = str(payload.get("status") or ("OK" if payload.get("ok") else "ERROR"))
        ok = bool(payload.get("ok", status in {"OK", "MAPPED"}))
        if ok:
            self._last_applied_path = candidate
            self._last_applied_mtime_ns = stat.st_mtime_ns
        return {
            "ok": ok,
            "status": status,
            "conversation_path": str(candidate),
            "project_id": payload.get("project_id") or payload.get("active_project_id"),
            "project_scope_hash": payload.get("project_scope_hash") or payload.get("active_project_scope_hash"),
            "source_event": "lmstudio_conversation_watcher",
            "message": str(payload.get("message") or status),
        }

    # Backward-compatible private alias for reference-package tests.
    def _handle_conversation_path(self, path: Path) -> dict[str, object]:
        return self.handle_conversation_path(path)

    def _newest_conversation_file(self) -> Path | None:
        newest: tuple[int, str, Path] | None = None
        for path in self.conversations_root.rglob("*.conversation.json"):
            if not path.is_file():
                continue
            try:
                stat = path.stat()
                resolved = path.resolve()
            except OSError:
                continue
            item = (stat.st_mtime_ns, str(resolved), resolved)
            if newest is None or item[:2] > newest[:2]:
                newest = item
        return newest[2] if newest else None

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
