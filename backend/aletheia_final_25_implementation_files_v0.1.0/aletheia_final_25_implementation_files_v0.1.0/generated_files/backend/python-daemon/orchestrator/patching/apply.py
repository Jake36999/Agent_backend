from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .diff import validate_affected_files
from .guardrails import validate_test_command
from .repo import PatchRepository
from .snapshots import RollbackService
from .test_runner import DeclaredTestRunner


class PatchApplyError(ValueError):
    pass


class PatchApplyService:
    def __init__(self, queue_db_path: Path, rollback_root: Path, *, allowed_roots: list[Path] | None = None) -> None:
        self.repo = PatchRepository(queue_db_path)
        self.rollback = RollbackService(queue_db_path, rollback_root)
        self.test_runner = DeclaredTestRunner()
        self.allowed_roots = [Path(p).resolve() for p in (allowed_roots or [])]

    def apply_approved_patch_and_test(
        self,
        *,
        patch_id: str,
        target_repo: Path,
        approval_record: dict[str, object],
    ) -> dict[str, object]:
        root = Path(target_repo).resolve()
        self._validate_allowed_root(root)
        artifact = self.repo.get_artifact(patch_id)
        if artifact is None:
            return {"ok": False, "status": "PATCH_NOT_FOUND", "patch_id": patch_id}
        if artifact.status not in {"generated", "approved"}:
            return {"ok": False, "status": "INVALID_PATCH_STATUS", "patch_id": patch_id, "current_status": artifact.status}
        if approval_record.get("approved") is not True:
            return {"ok": False, "status": "PENDING_APPROVAL", "patch_id": patch_id}
        approved_hash = approval_record.get("unified_diff_sha256")
        if approved_hash and approved_hash != artifact.audit_state.get("unified_diff_sha256"):
            return {"ok": False, "status": "APPROVAL_HASH_MISMATCH", "patch_id": patch_id}
        affected_paths = validate_affected_files(root, artifact.affected_files)
        for command in artifact.test_commands:
            ok, reason = validate_test_command(command)
            if not ok:
                return {"ok": False, "status": "BLOCKED_TEST_COMMAND", "patch_id": patch_id, "error": reason}

        snapshots = self.rollback.snapshot_files(patch_id, affected_paths)
        check = self._git_apply(root, artifact.unified_diff, check=True)
        if check["returncode"] != 0:
            self.repo.update_status(patch_id, "apply_failed")
            return {"ok": False, "status": "APPLY_CHECK_FAILED", "patch_id": patch_id, "stderr_tail": check["stderr_tail"], "rollback_snapshots": snapshots}
        apply = self._git_apply(root, artifact.unified_diff, check=False)
        if apply["returncode"] != 0:
            self.repo.update_status(patch_id, "apply_failed")
            return {"ok": False, "status": "APPLY_FAILED", "patch_id": patch_id, "stderr_tail": apply["stderr_tail"], "rollback_snapshots": snapshots}
        self.repo.update_status(patch_id, "applied")
        test_logs = self.test_runner.run(target_repo=root, commands=artifact.test_commands)
        test_status = "passed" if all(item["returncode"] == 0 for item in test_logs) else "failed"
        self.repo.update_status(patch_id, "test_passed" if test_status == "passed" else "test_failed")
        return {
            "ok": test_status == "passed",
            "status": "TEST_PASSED" if test_status == "passed" else "TEST_FAILED",
            "patch_id": patch_id,
            "applied_files": artifact.affected_files,
            "test_logs": test_logs,
            "test_status": test_status,
            "rollback_artifact": str((self.rollback.rollback_root / patch_id).resolve()),
            "audit_state": {"committed": False, "pushed": False, "deployed": False, "approval_verified": True},
        }

    def _git_apply(self, target_repo: Path, unified_diff: str, *, check: bool) -> dict[str, object]:
        args = ["git", "apply"]
        if check:
            args.append("--check")
        completed = subprocess.run(args, input=unified_diff, cwd=str(target_repo), text=True, capture_output=True, check=False, timeout=120)
        return {"returncode": completed.returncode, "stdout_tail": completed.stdout[-4000:], "stderr_tail": completed.stderr[-4000:]}

    def _validate_allowed_root(self, target_repo: Path) -> None:
        if not self.allowed_roots:
            return
        if not any(target_repo == root or root in target_repo.parents for root in self.allowed_roots):
            raise PatchApplyError(f"target repo is outside allowed roots: {target_repo}")
