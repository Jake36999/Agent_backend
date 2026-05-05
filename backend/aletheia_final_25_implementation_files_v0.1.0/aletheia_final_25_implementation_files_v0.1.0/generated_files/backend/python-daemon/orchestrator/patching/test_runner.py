from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .guardrails import validate_test_command


class TestCommandError(ValueError):
    pass


class DeclaredTestRunner:
    def __init__(self, *, timeout_seconds: int = 120, tail_chars: int = 4000) -> None:
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.tail_chars = max(100, int(tail_chars))

    def run(self, *, target_repo: Path, commands: list[str]) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for command in commands:
            ok, reason = validate_test_command(command)
            if not ok:
                raise TestCommandError(reason)
            args = shlex.split(command)
            if not args:
                raise TestCommandError("empty test command")
            completed = subprocess.run(
                args,
                cwd=str(target_repo),
                shell=False,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            stdout_tail = completed.stdout[-self.tail_chars:]
            stderr_tail = completed.stderr[-self.tail_chars:]
            results.append({
                "command": command,
                "returncode": completed.returncode,
                "status": "passed" if completed.returncode == 0 else "failed",
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            })
        return results
