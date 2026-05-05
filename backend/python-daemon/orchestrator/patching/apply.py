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
        memory_service: Any | None = None,
        conversation_summary_ingestor: Any | None = None,
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
        self.memory_service = memory_service
        self.conversation_summary_ingestor = conversation_summary_ingestor

    def validate_patch_text(self, diff_text: str, *, target_repo: str | Path) -> PatchValidationResult:
        return self.validator.validate_unified_diff(diff_text, target_repo=target_repo, run_git_check=False)

    def apply_approved_patch(self, *, patch_id: str, approval_id: str, target_repo: str | Path) -> dict[str, object]:
        repo_path = Path(target_repo).resolve()
        if not self._is_under_allowed(repo_path):
            return self._failure("validate", "POLICY_BLOCK", patch_id, message="target_repo is outside allowed roots", validation_code="outside_allowed_roots")
        artifact = self.repo.get(patch_id)
        if artifact is None:
            return self._failure("load_patch", "PATCH_NOT_FOUND", patch_id, message="patch artifact was not found")
        approval = self.repo.get_approval_record(approval_id)
        if approval is None:
            return self._failure("load_approval", "APPROVAL_NOT_FOUND", patch_id, approval_id=approval_id, message="approval record was not found")
        if approval.patch_id != patch_id:
            return self._failure("approval", "APPROVAL_PATCH_MISMATCH", patch_id, approval_id=approval_id, message="approval does not reference this patch")
        if not approval.approved:
            return self._failure("approval", "PENDING_APPROVAL", patch_id, approval_id=approval_id, message="approval is not approved")
        if approval.approved_diff_sha256 != artifact.diff_sha256:
            return self._failure("approval", "APPROVAL_HASH_MISMATCH", patch_id, approval_id=approval_id, message="approved diff sha256 does not match patch artifact")
        patch_path = Path(artifact.patch_path).resolve()
        if patch_path == repo_path or repo_path in patch_path.parents:
            return self._failure("validate", "POLICY_BLOCK", patch_id, message="patch path must be outside target_repo", validation_code="patch_path_inside_repo")
        if not patch_path.exists():
            return self._failure("load_patch", "PATCH_FILE_MISSING", patch_id, message="patch file is missing")
        diff_bytes = patch_path.read_bytes()
        if hashlib.sha256(diff_bytes).hexdigest() != artifact.diff_sha256:
            return self._failure("load_patch", "PATCH_HASH_MISMATCH", patch_id, message="patch file sha256 does not match stored sha256")
        try:
            diff_text = diff_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return self._failure("validate", "POLICY_BLOCK", patch_id, message="patch must be utf-8 unified diff text", validation_code="patch_not_utf8")
        validation = self.validator.validate_unified_diff(diff_text, target_repo=repo_path, run_git_check=False)
        if not validation.ok:
            return self._failure("validate", validation.status, patch_id, message=validation.error or "patch validation failed", validation_code="patch_validation_failed")
        if sorted(validation.affected_paths) != sorted(artifact.affected_paths_json):
            return self._failure("validate", "AFFECTED_PATH_MISMATCH", patch_id, message="affected paths do not match patch artifact metadata")
        check = self._git_apply(repo_path, diff_bytes, check=True)
        if check["returncode"] != 0:
            return self._failure("preflight", "APPLY_CHECK_FAILED", patch_id, message=check["stderr_tail"] or check["stdout_tail"], validation_code="git_apply_check_failed")

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
            return self._failure("snapshot", "SNAPSHOT_FAILED", patch_id, apply_run_id=apply_run_id, message=exc)

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
                    "diagnostic": self._diagnostic("test", "TESTS_BLOCKED", patch_id, apply_run_id=apply_run_id, message=exc),
                }
        final_status = "APPLIED_TESTS_PASSED" if tests_status == "passed" else ("APPLIED_TESTS_FAILED" if tests_status == "failed" else "APPLIED")
        self.repo.update_apply_run(apply_run_id, status=final_status, tests_status=tests_status, completed_at=utc_now(), rollback_available=True)
        memory_commit = self._commit_patch_memory(
            artifact=artifact,
            apply_run_id=apply_run_id,
            target_repo=repo_path,
            affected_paths=validation.affected_paths,
            tests_status=tests_status,
        )
        return {
            "ok": tests_status in {"not_run", "passed"},
            "status": final_status,
            "patch_id": patch_id,
            "apply_run_id": apply_run_id,
            "rollback_available": True,
            "tests_status": tests_status,
            "test_results": test_results,
            "memory_commit": memory_commit,
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

    def _commit_patch_memory(self, *, artifact: Any, apply_run_id: str, target_repo: Path, affected_paths: list[str], tests_status: str) -> dict[str, object]:
        if self.memory_service is None:
            return {"status": "SKIPPED", "reason": "memory_service_unavailable"}
        active_repo = getattr(self.memory_service, "active_repo", None)
        if active_repo is not None:
            active = active_repo.get_active_partition(getattr(self.memory_service, "client_id", "local-lmstudio"))
            if active is None or not active.active_project_id or not active.active_project_scope_hash:
                return {"status": "SKIPPED", "reason": "no_active_partition"}
        content = (
            "Approved patch applied.\n"
            f"patch_id: {artifact.patch_id}\n"
            f"apply_run_id: {apply_run_id}\n"
            f"target_repo: {target_repo}\n"
            f"affected_paths: {', '.join(affected_paths)}\n"
            f"selected_skill_id: {artifact.selected_skill_id or 'unknown'}\n"
            f"tests_status: {tests_status}\n"
            "rollback_available: true"
        )
        metadata = {
            "patch_id": artifact.patch_id,
            "apply_run_id": apply_run_id,
            "target_repo": str(target_repo),
            "affected_paths": list(affected_paths),
            "selected_skill_id": artifact.selected_skill_id,
            "tests_status": tests_status,
            "rollback_available": True,
            "source": "patch_apply_service",
        }
        if self.conversation_summary_ingestor is not None:
            candidate = self.conversation_summary_ingestor.build_memory_candidate(
                conversation_events=[{"type": "tool_result", "content": content}],
                target_repo=str(target_repo),
                source_artifacts=[{"artifact": artifact.patch_id, "status": "completed", "verified": True, "summary": f"Approved patch {artifact.patch_id} applied."}],
                write_intent="approved patch apply result",
                selected_skill={"skill_id": artifact.selected_skill_id} if artifact.selected_skill_id else None,
            )
            if not candidate.get("write_allowed"):
                return {"status": "SKIPPED", "reason": "memory_candidate_not_allowed"}
            result = self.conversation_summary_ingestor.commit_if_allowed(candidate_result=candidate, memory_service=self.memory_service)
        else:
            result = self.memory_service.commit_memory(category="artifact", content=content, metadata=metadata)
        if result.get("status") == "NO_ACTIVE_PARTITION":
            return {"status": "SKIPPED", "reason": "no_active_partition"}
        return {
            "status": result.get("status", "ERROR"),
            "memory_id": result.get("memory_id"),
            "index_status": result.get("index_status"),
            "ok": bool(result.get("ok")),
        }

    def _diagnostic(self, phase: str, status: str, patch_id: str, *, apply_run_id: str | None = None, approval_id: str | None = None, affected_path: str | None = None, validation_code: str | None = None, message: object = "") -> dict[str, object]:
        return {
            "phase": phase,
            "status": status,
            "patch_id": patch_id,
            **({"apply_run_id": apply_run_id} if apply_run_id else {}),
            **({"approval_id": approval_id} if approval_id else {}),
            **({"affected_path": affected_path} if affected_path else {}),
            **({"validation_code": validation_code} if validation_code else {}),
            "message": bounded(message, 500),
        }

    def _failure(self, phase: str, status: str, patch_id: str, *, apply_run_id: str | None = None, approval_id: str | None = None, affected_path: str | None = None, validation_code: str | None = None, message: object = "") -> dict[str, object]:
        diagnostic = self._diagnostic(
            phase,
            status,
            patch_id,
            apply_run_id=apply_run_id,
            approval_id=approval_id,
            affected_path=affected_path,
            validation_code=validation_code,
            message=message,
        )
        return {"ok": False, "status": status, "patch_id": patch_id, **({"apply_run_id": apply_run_id} if apply_run_id else {}), "error": diagnostic["message"], "diagnostic": diagnostic}
