import asyncio
import hmac
import tempfile
import unittest
from pathlib import Path

from orchestrator.approval import build_approval_envelope
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.hitl import ApprovalGate
from orchestrator.queue_repo import QueueRepository
from orchestrator.shell import CommandSpec, ShellAdapter, ShellExecutionError, ZombieReaper


class HitlAndShellTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        bootstrap_databases(self.root)
        self.repo = QueueRepository(self.root / "queue.db", self.root / "control.db")

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_pending_approval_blocks_until_valid_authorization_hash(self):
        secret = b"secret"
        diff = b"diff"
        envelope = build_approval_envelope(secret, b"base", b"proposed", diff)
        self.repo.create_task("task", "p", "Task", {"tool": "a"}, depth=0)
        self.repo.create_approval("approval", "task", envelope)
        gate = ApprovalGate(self.repo, secret)

        waiter = asyncio.create_task(gate.wait_for_approval("task", timeout=0.05))
        with self.assertRaises(asyncio.TimeoutError):
            await waiter

        bad = await gate.authorize("task", "not-valid", diff)
        self.assertFalse(bad)
        supplied = hmac.digest(secret, diff, "sha256").hex()
        good = await gate.authorize("task", supplied, diff)

        self.assertTrue(good)
        self.assertEqual(self.repo.get_task("task")["state"], "PLANNING")

    async def test_pending_approval_rejection_prunes_descendants(self):
        secret = b"secret"
        envelope = build_approval_envelope(secret, b"base", b"proposed", b"diff")
        self.repo.create_task("parent", "p", "Parent", {"tool": "a"}, depth=0)
        self.repo.create_task("child", "p", "Child", {"tool": "b"}, depth=1, parent_task_id="parent")
        self.repo.create_approval("approval", "parent", envelope)
        gate = ApprovalGate(self.repo, secret)

        pruned = await gate.reject("parent", decided_by="operator", reason="not safe")

        self.assertEqual(pruned, ["child"])
        self.assertEqual(self.repo.get_task("parent")["resolution"], "REJECTED")
        self.assertEqual(self.repo.get_task("child")["resolution"], "CASCADE_PRUNED")

    async def test_shell_rejects_raw_shell_syntax_and_runs_argument_arrays(self):
        seen = []

        async def fake_runner(spec):
            seen.append((spec.executable, spec.args, spec.cwd))
            return 0, b"ok\n", b""

        adapter = ShellAdapter((self.root,), runner=fake_runner)

        with self.assertRaises(ShellExecutionError):
            await adapter.run(CommandSpec("python", ("-c", "print(1)"), cwd=str(self.root), timeout_seconds=2, mutates_filesystem=False, env={"A": "B; rm"}))

        rc, stdout, stderr = await adapter.run(CommandSpec("python", ("-c", "print('ok')"), cwd=str(self.root)))
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.strip(), "ok")
        self.assertEqual(stderr, "")
        self.assertEqual(seen, [("python", ("-c", "print('ok')"), str(self.root))])

    def test_zombie_reaper_returns_none_for_non_posix_platforms(self):
        reaper = ZombieReaper()
        result = reaper.reap_once(-1)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
