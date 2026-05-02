from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from .queue_repo import QueueRepository
from .shell import ZombieReaper


class RecoveryService:
    def __init__(self, repo: QueueRepository, *, reaper: ZombieReaper | None = None) -> None:
        self.repo = repo
        self.reaper = reaper or ZombieReaper()

    def recover_once(self, *, lease_now: str | None = None, stale_after_seconds: int = 120) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        released = self.repo.release_expired_leases(lease_now or now.isoformat())
        stale_before = (now - timedelta(seconds=stale_after_seconds)).isoformat()
        stale_workers = self.repo.mark_stale_workers(stale_before)
        reaped = 0
        for worker in self.repo.list_worker_status():
            if worker.get("status") not in {"RUNNING", "STALE"}:
                continue
            result = self.reaper.reap_once(int(worker["pid"]))
            if result is not None:
                waited_pid, status = result
                self.repo.mark_worker_exited(waited_pid, os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else status)
                reaped += 1
        return {"released_leases": released, "stale_workers": stale_workers, "reaped_processes": reaped}
