from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from .git_guardrails import GitGuardrailsService
from .models import PatchValidationResult


class PatchValidationService:
    blocked_patterns = (
        "*_bundle*.py",
        "*_bundle*.yaml",
        "local_tool_assist_outputs/*",
        "*/local_tool_assist_outputs/*",
        "reports/final_handoff*",
        "archive/session*",
        "sessions/*/intermediate/*",
        ".env",
        "*.env",
        "*secret*",
        "*token*",
    )

    def __init__(
        self,
        *,
        allowed_roots: tuple[Path, ...],
        subprocess_run: Callable[..., Any] = subprocess.run,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.allowed_roots = tuple(Path(root).resolve() for root in allowed_roots)
        self.subprocess_run = subprocess_run
        self.timeout_seconds = timeout_seconds
        self.guardrails = GitGuardrailsService()

    def validate_unified_diff(self, diff_text: str, *, target_repo: str | Path, run_git_check: bool = True) -> PatchValidationResult:
        repo = Path(target_repo).resolve()
        if not self._is_under_allowed(repo):
            return PatchValidationResult(False, "POLICY_BLOCK", error="target_repo is outside allowed roots")
        if "Binary files " in diff_text or "GIT binary patch" in diff_text:
            return PatchValidationResult(False, "POLICY_BLOCK", error="binary patches are not allowed")
        affected = self._affected_paths(diff_text)
        if not affected:
            return PatchValidationResult(False, "WARN", error="unified diff contains no affected paths")
        for rel_path in affected:
            reason = self._blocked_path_reason(rel_path, repo)
            if reason:
                return PatchValidationResult(False, "POLICY_BLOCK", affected, reason)
        if run_git_check:
            argv = ["git", "apply", "--check", "--", "-"]
            guard = self.guardrails.check_command(argv)
            if not guard.allowed:
                return PatchValidationResult(False, "POLICY_BLOCK", affected, guard.reason)
            try:
                result = self.subprocess_run(
                    argv,
                    input=diff_text,
                    text=True,
                    cwd=str(repo),
                    capture_output=True,
                    shell=False,
                    timeout=self.timeout_seconds,
                )
            except Exception as exc:
                return PatchValidationResult(False, "WARN", affected, str(exc)[:500])
            if int(getattr(result, "returncode", 1)) != 0:
                message = (getattr(result, "stderr", "") or getattr(result, "stdout", "") or "git apply --check failed")[:500]
                return PatchValidationResult(False, "WARN", affected, message)
        return PatchValidationResult(True, "OK", affected)

    def _affected_paths(self, diff_text: str) -> list[str]:
        paths: list[str] = []
        for line in diff_text.splitlines():
            if not line.startswith(("--- ", "+++ ")):
                continue
            raw = line[4:].strip().split("\t", 1)[0]
            if raw == "/dev/null":
                continue
            if raw.startswith(("a/", "b/")):
                raw = raw[2:]
            paths.append(raw.replace("\\", "/"))
        deduped: list[str] = []
        for path in paths:
            if path not in deduped:
                deduped.append(path)
        return deduped

    def _blocked_path_reason(self, rel_path: str, repo: Path) -> str | None:
        normalized = rel_path.replace("\\", "/")
        if ".." in Path(normalized).parts:
            return "path traversal is not allowed"
        if re.match(r"^[A-Za-z]:", normalized) or normalized.startswith("/"):
            return "absolute patch paths are not allowed"
        if any(fnmatch.fnmatch(normalized, pattern) for pattern in self.blocked_patterns):
            return "blocked generated, Tool Assist, or secret/env target"
        target = (repo / normalized).resolve()
        if not (target == repo or repo in target.parents):
            return "patch target escapes target_repo"
        return None

    def _is_under_allowed(self, path: Path) -> bool:
        return any(path == root or root in path.parents for root in self.allowed_roots)
