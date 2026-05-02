from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .adapters import ToolAdapters
from .execution_loop import ExecutionLoop
from .queue_repo import QueueRepository

LOGGER = logging.getLogger(__name__)


class DaemonWorker:
    def __init__(
        self,
        repo: QueueRepository,
        tool_adapters: ToolAdapters,
        *,
        project_id: str,
        worker_id: str,
        lease_seconds: int = 60,
        idle_sleep_seconds: float = 0.25,
    ) -> None:
        self.repo = repo
        self.loop = ExecutionLoop(repo, tool_adapters=tool_adapters)
        self.project_id = project_id
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.idle_sleep_seconds = idle_sleep_seconds
        self._wake_event = asyncio.Event()

    def wake(self) -> None:
        self._wake_event.set()

    def register_process(self, command: list[str] | None = None) -> None:
        self.repo.register_worker(self.worker_id, command or ["aletheia-daemon"], os.getpid())

    def heartbeat(self) -> None:
        self.repo.heartbeat_worker(self.worker_id, os.getpid())

    def run_once(self) -> dict[str, Any]:
        self.heartbeat()
        self.repo.release_expired_leases(datetime.now(timezone.utc).isoformat())
        lease_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=self.lease_seconds)).isoformat()
        task = self.repo.claim_ready_task(self.project_id, self.worker_id, lease_expires_at)
        if task is None:
            return {"ok": True, "idle": True}
        task_id = task["task_id"]
        LOGGER.info("worker_claimed_task", extra={"extra_fields": {"task_id": task_id, "project_id": self.project_id, "worker_id": self.worker_id}})
        try:
            payload = json.loads(task["payload_json"])
            tool_name = payload["tool"]
            args = payload.get("args", {})
            if not isinstance(tool_name, str) or not isinstance(args, dict):
                raise ValueError("invalid task payload")
        except Exception as exc:
            self.repo.dead_letter(task_id, "invalid_task_payload", {"error": str(exc), "payload_json": task["payload_json"]})
            self.repo.complete_task(task_id)
            LOGGER.info("worker_dead_lettered_task", extra={"extra_fields": {"task_id": task_id, "reason": "invalid_task_payload"}})
            return {"ok": False, "task_id": task_id, "error": "invalid_task_payload"}
        result = self.loop.execute_tool_for_task(task_id, tool_name, args)
        if result.get("ok") is not False:
            self.repo.complete_task(task_id)
            LOGGER.info("worker_completed_task", extra={"extra_fields": {"task_id": task_id, "project_id": self.project_id}})
        return {"ok": result.get("ok", True), "task_id": task_id, "result": result}

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        self.register_process()
        while not stop_event.is_set():
            result = self.run_once()
            if result.get("idle"):
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=self.idle_sleep_seconds)
                except asyncio.TimeoutError:
                    pass
                self._wake_event.clear()
