from __future__ import annotations

import hashlib
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .models import PatchApplyRun, PatchValidationResult
from .repo import PatchArtifactRepository
from .rollback import RollbackRestoreService
from .snapshots import RollbackSnapshotService
from .test_runner import DeclaredTestRunner
from .validation import PatchValidationService


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bounded(value: object, limit: int = 500) -> str:
    return str(value)[:limit]


class PatchApplyService:
    def __init__(
        self,
        queue_db_path: Path,
        rollback_root: Path,
        *,
        allowed_roots: tuple[Path, ...],
        subprocess_run: Callable[..., Any] = subprocess.run,
        timeout_seconds: float = 10.0,
        test_runner: DeclaredTestRunner | None = None,
    ) -> None:
        self.repo = PatchArtifactRepository(queue_db_path)
        self.rollback_root = Path(rollback_root).resolve()
        self.allowed_roots = tuple(Path(root).resolve() for root in allowed_roots)
        self.subprocess_run = subprocess_run
        self.timeout_seconds = timeout_seconds
        self.validator = PatchValidationService(allowed_roots=self.allowed_roots, subprocess_run=subprocess_run, timeout_seconds=timeout_seconds)
        self.snapshots = RollbackSnapshotService(queue_db_path, self.rollback_root)
        self.rollback = RollbackRestoreService(queue_db_path, self.rollback_root)
        self.test_runner = test_runner or DeclaredTestRunner(timeout_seconds=timeout_seconds)

    def validate_patch_text(self, diff_text: str, *, target_repo: str | Path) -> PatchValidationResult:
        return self.validator.validate_unified_diff(diff_text, target_repo=target_repo, run_git_check=False)

    def apply_approved_patch(self, *, patch_id: str, approval_id: str, target_repo: str | Path) -> dict[str, object]:
        repo_path = Path(target_repo).resolve()
        if not self._is_under_allowed(repo_path):
            return {"ok": False, "status": "POLICY_BLOCK", "patch_id": patch_id, "error": "target_repo is outside allowed roots"}
        artifact = self.repo.get(patch_id)
        if artifact is None:
            return {"ok": False, "status": "PATCH_NOT_FOUND", "patch_id": patch_id}
        approval = self.repo.get_approval_record(approval_id)
        if approval is None:
            return {"ok": False, "status": "APPROVAL_NOT_FOUND", "patch_id": patch_id, "approval_id": approval_id}
        if approval.patch_id != patch_id:
            return {"ok": False, "status": "APPROVAL_PATCH_MISMATCH", "patch_id": patch_id, "approval_id": approval_id}
        if not approval.approved:
            return {"ok": False, "status": "PENDING_APPROVAL", "patch_id": patch_id, "approval_id": approval_id}
        if approval.approved_diff_sha256 != artifact.diff_sha256:
            return {"ok": False, "status": "APPROVAL_HASH_MISMATCH", "patch_id": patch_id, "approval_id": approval_id}
        patch_path = Path(artifact.patch_path).resolve()
        if patch_path == repo_path or repo_path in patch_path.parents:
            return {"ok": False, "status": "POLICY_BLOCK", "patch_id": patch_id, "error": "patch path must be outside target_repo"}
        if not patch_path.exists():
            return {"ok": False, "status": "PATCH_FILE_MISSING", "patch_id": patch_id}
        diff_bytes = patch_path.read_bytes()
        if hashlib.sha256(diff_bytes).hexdigest() != artifact.diff_sha256:
            return {"ok": False, "status": "PATCH_HASH_MISMATCH", "patch_id": patch_id}
        try:
            diff_text = diff_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return {"ok": False, "status": "POLICY_BLOCK", "patch_id": patch_id, "error": "patch must be utf-8 unified diff text"}
        validation = self.validator.validate_unified_diff(diff_text, target_repo=repo_path, run_git_check=False)
        if not validation.ok:
            return {"ok": False, "status": validation.status, "patch_id": patch_id, "error": validation.error}
        if sorted(validation.affected_paths) != sorted(artifact.affected_paths_json):
            return {"ok": False, "status": "AFFECTED_PATH_MISMATCH", "patch_id": patch_id}
        check = self._git_apply(repo_path, diff_bytes, check=True)
        if check["returncode"] != 0:
            return {"ok": False, "status": "APPLY_CHECK_FAILED", "patch_id": patch_id, "error": check["stderr_tail"] or check["stdout_tail"]}

        apply_run_id = f"apply_{uuid.uuid4().hex}"
        self.repo.insert_apply_run(
            PatchApplyRun(
                apply_run_id=apply_run_id,
                patch_id=patch_id,
                approval_id=approval_id,
                run_id=artifact.run_id,
                project_id=artifact.project_id,
                project_scope_hash=artifact.project_scope_hash,
                target_repo=str(repo_path),
                status="SNAPSHOTTING",
                applied_at=None,
                completed_at=None,
                rollback_available=False,
                tests_status=None,
            )
        )
        try:
            self.snapshots.snapshot_targets(
                apply_run_id=apply_run_id,
                patch_id=patch_id,
                target_repo=repo_path,
                rel_paths=validation.affected_paths,
            )
            self.repo.update_apply_run(apply_run_id, status="SNAPSHOTTED", rollback_available=True)
        except Exception as exc:
            self.repo.update_apply_run(apply_run_id, status="SNAPSHOT_FAILED", completed_at=utc_now(), bounded_error=bounded(exc))
            return {"ok": False, "status": "SNAPSHOT_FAILED", "patch_id": patch_id, "apply_run_id": apply_run_id, "error": bounded(exc)}

        applied = self._git_apply(repo_path, diff_bytes, check=False)
        if applied["returncode"] != 0:
            rollback = self.rollback.restore_apply_run(apply_run_id)
            status = "APPLY_FAILED_ROLLED_BACK" if rollback.get("ok") else "APPLY_FAILED_ROLLBACK_FAILED"
            self.repo.update_apply_run(
                apply_run_id,
                status=status,
                completed_at=utc_now(),
                rollback_available=bool(rollback.get("ok")),
                bounded_error=bounded(applied["stderr_tail"] or applied["stdout_tail"]),
            )
            return {"ok": False, "status": status, "patch_id": patch_id, "apply_run_id": apply_run_id, "rollback": rollback}

        self.repo.update_apply_run(apply_run_id, status="APPLIED", applied_at=utc_now(), rollback_available=True)
        tests_status = "not_run"
        test_results: list[dict[str, object]] = []
        if approval.declared_tests_json:
            try:
                test_results = self.test_runner.run(target_repo=repo_path, commands=approval.declared_tests_json)
                tests_status = "passed" if all(item["returncode"] == 0 for item in test_results) else "failed"
            except Exception as exc:
                tests_status = "blocked"
                self.repo.update_apply_run(apply_run_id, status="TESTS_BLOCKED", tests_status=tests_status, bounded_error=bounded(exc), completed_at=utc_now())
                return {
                    "ok": False,
                    "status": "TESTS_BLOCKED",
                    "patch_id": patch_id,
                    "apply_run_id": apply_run_id,
                    "rollback_available": True,
                    "tests_status": tests_status,
                    "error": bounded(exc),
                }
        final_status = "APPLIED_TESTS_PASSED" if tests_status == "passed" else ("APPLIED_TESTS_FAILED" if tests_status == "failed" else "APPLIED")
        self.repo.update_apply_run(apply_run_id, status=final_status, tests_status=tests_status, completed_at=utc_now(), rollback_available=True)
        return {
            "ok": tests_status in {"not_run", "passed"},
            "status": final_status,
            "patch_id": patch_id,
            "apply_run_id": apply_run_id,
            "rollback_available": True,
            "tests_status": tests_status,
            "test_results": test_results,
        }

    def _git_apply(self, target_repo: Path, diff_bytes: bytes, *, check: bool) -> dict[str, object]:
        argv = ["git", "apply"]
        if check:
            argv.append("--check")
        argv.extend(["--", "-"])
        completed = self.subprocess_run(
            argv,
            input=diff_bytes,
            cwd=str(target_repo),
            capture_output=True,
            shell=False,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout = getattr(completed, "stdout", b"") or b""
        stderr = getattr(completed, "stderr", b"") or b""
        if isinstance(stdout, bytes):
            stdout_tail = stdout.decode("utf-8", errors="replace")[-500:]
        else:
            stdout_tail = str(stdout)[-500:]
        if isinstance(stderr, bytes):
            stderr_tail = stderr.decode("utf-8", errors="replace")[-500:]
        else:
            stderr_tail = str(stderr)[-500:]
        return {"returncode": int(getattr(completed, "returncode", 1)), "stdout_tail": stdout_tail, "stderr_tail": stderr_tail}

    def _is_under_allowed(self, path: Path) -> bool:
        return any(path == root or root in path.parents for root in self.allowed_roots)
