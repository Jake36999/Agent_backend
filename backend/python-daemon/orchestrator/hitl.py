from __future__ import annotations

import asyncio
import hmac

from .queue_repo import QueueRepository


class ApprovalGate:
    def __init__(self, repo: QueueRepository, secret: bytes) -> None:
        self.repo = repo
        self.secret = secret
        self._events: dict[str, asyncio.Event] = {}

    def _event(self, task_id: str) -> asyncio.Event:
        if task_id not in self._events:
            self._events[task_id] = asyncio.Event()
        return self._events[task_id]

    async def wait_for_approval(self, task_id: str, *, timeout: float | None = None) -> None:
        task = self.repo.get_task(task_id)
        if task["state"] != "PENDING_APPROVAL":
            return
        await asyncio.wait_for(self._event(task_id).wait(), timeout=timeout)

    async def authorize(self, task_id: str, authorization_hash: str, diff_bytes: bytes) -> bool:
        expected = hmac.digest(self.secret, diff_bytes, "sha256").hex()
        if not hmac.compare_digest(expected, authorization_hash):
            return False
        self.repo.approve_task(task_id, "stdin-or-socket")
        self._event(task_id).set()
        return True

    async def reject(self, task_id: str, *, decided_by: str, reason: str) -> list[str]:
        pruned = self.repo.reject_approval(task_id, decided_by, reason)
        self._event(task_id).set()
        return pruned
