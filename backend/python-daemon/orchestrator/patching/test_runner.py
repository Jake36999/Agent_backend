from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from .git_guardrails import GitGuardrailsService


class DeclaredTestRunner:
    shell_metacharacters = {";", "&&", "||", "|", ">", ">>", "<", "$(", "`"}

    def __init__(
        self,
        *,
        subprocess_run: Callable[..., Any] = subprocess.run,
        timeout_seconds: float = 120.0,
        tail_chars: int = 4000,
        allow_pytest: bool = False,
        allow_node: bool = False,
    ) -> None:
        self.subprocess_run = subprocess_run
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.tail_chars = max(100, int(tail_chars))
        if tail_chars < 100:
            self.tail_chars = int(tail_chars)
        self.allow_pytest = allow_pytest
        self.allow_node = allow_node
        self.guardrails = GitGuardrailsService()

    def run(self, *, target_repo: Path, commands: list[Any]) -> list[dict[str, object]]:
        repo = Path(target_repo).resolve()
        results: list[dict[str, object]] = []
        for command in commands:
            argv = self._validate_argv(command)
            started = time.monotonic()
            completed = self.subprocess_run(
                argv,
                cwd=str(repo),
                shell=False,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            duration = time.monotonic() - started
            stdout = getattr(completed, "stdout", "") or ""
            stderr = getattr(completed, "stderr", "") or ""
            returncode = int(getattr(completed, "returncode", 1))
            results.append(
                {
                    "argv": argv,
                    "returncode": returncode,
                    "duration": round(duration, 3),
                    "status": "passed" if returncode == 0 else "failed",
                    "stdout_tail": stdout[-self.tail_chars :],
                    "stderr_tail": stderr[-self.tail_chars :],
                }
            )
        return results

    def _validate_argv(self, command: Any) -> list[str]:
        if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("declared test command must be an argv array")
        if any(any(meta in part for meta in self.shell_metacharacters) for part in command):
            raise ValueError("shell metacharacters are not allowed")
        lowered = [part.lower() for part in command]
        guard = self.guardrails.check_command(command)
        if guard.allowed and lowered[0] == "git":
            raise ValueError("git commands are not declared tests")
        if lowered[:3] == ["python", "-m", "unittest"]:
            return list(command)
        if lowered[0] == "pytest" and self.allow_pytest:
            return list(command)
        if lowered[0] in {"node", "npm"} and self.allow_node:
            return list(command)
        if not guard.allowed:
            raise ValueError(guard.reason)
        raise ValueError("test command is not explicitly allowed")
