from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable


@dataclass(frozen=True)
class CommandSpec:
    executable: str
    args: tuple[str, ...] = field(default_factory=tuple)
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    expected_exit_codes: tuple[int, ...] = (0,)
    mutates_filesystem: bool = False


class ShellExecutionError(RuntimeError):
    pass


Runner = Callable[[CommandSpec], Awaitable[tuple[int, bytes, bytes]]]


class ShellAdapter:
    def __init__(self, allowed_roots: tuple[Path, ...], runner: Runner | None = None) -> None:
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
        self.runner = runner

    def _validate(self, spec: CommandSpec) -> None:
        if not spec.executable:
            raise ShellExecutionError("executable is required")
        forbidden = ["|", "&", ";", ">", "<"]
        if any(char in spec.executable for char in forbidden):
            raise ShellExecutionError("raw shell syntax is forbidden")
        for key, value in spec.env.items():
            if any(char in key for char in forbidden) or any(char in value for char in forbidden):
                raise ShellExecutionError("raw shell syntax is forbidden in env")
        if spec.cwd is not None:
            cwd = Path(spec.cwd).resolve()
            if not any(cwd == root or root in cwd.parents for root in self.allowed_roots):
                raise ShellExecutionError("cwd escapes allowed roots")

    async def run(self, spec: CommandSpec) -> tuple[int, str, str]:
        self._validate(spec)
        if self.runner is None:
            rc, stdout_b, stderr_b = await self._run_subprocess(spec)
        else:
            rc, stdout_b, stderr_b = await self.runner(spec)
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        if rc not in spec.expected_exit_codes:
            raise ShellExecutionError(f"unexpected exit code={rc}: {stderr}")
        return rc, stdout, stderr

    def sync_run(self, spec: CommandSpec) -> tuple[int, str, str]:
        self._validate(spec)
        if self.runner is None:
            rc, stdout_b, stderr_b = self._run_subprocess_sync(spec)
        else:
            import asyncio
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                rc, stdout_b, stderr_b = asyncio.run(self.runner(spec))
            else:
                raise ShellExecutionError("async runner cannot be used from a running event loop")
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        if rc not in spec.expected_exit_codes:
            raise ShellExecutionError(f"unexpected exit code={rc}: {stderr}")
        return rc, stdout, stderr

    def _run_subprocess_sync(self, spec: CommandSpec) -> tuple[int, bytes, bytes]:
        import subprocess
        try:
            completed = subprocess.run(
                [spec.executable, *spec.args],
                cwd=spec.cwd,
                env=spec.env or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=spec.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ShellExecutionError("command timed out") from exc
        return completed.returncode, completed.stdout, completed.stderr

    async def _run_subprocess(self, spec: CommandSpec) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            spec.executable,
            *spec.args,
            cwd=spec.cwd,
            env=spec.env or None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=spec.timeout_seconds)
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.communicate()
            raise ShellExecutionError("command timed out") from exc
        return proc.returncode if proc.returncode is not None else 0, stdout_b, stderr_b


class ZombieReaper:
    def reap_once(self, pid: int) -> tuple[int, int] | None:
        if os.name == "nt" or pid <= 0 or not hasattr(os, "waitpid") or not hasattr(os, "WNOHANG"):
            return None
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid == 0:
            return None
        return waited_pid, status
