from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .apply import PatchApplyService
from .repo import PatchArtifactRepository
from .rollback import RollbackRestoreService
from .service import PatchGenerationService
from .snapshots import sha256_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _under(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    root = root.resolve()
    return resolved == root or root in resolved.parents


def run_patch_flow_smoke(
    *,
    state_dir: Path,
    allowed_root: Path,
    target_repo_test_fixture: Path | None = None,
    restore_after_apply: bool = True,
    memory_service: Any | None = None,
    conversation_summary_ingestor: Any | None = None,
) -> dict[str, Any]:
    state = Path(state_dir).resolve()
    allowed = Path(allowed_root).resolve()
    queue_db = state / "queue.db"
    rollback_root = state / "rollback"
    patch_root = state / "patch_artifacts"
    smoke_root = state / "smoke"
    if target_repo_test_fixture is not None:
        repo = Path(target_repo_test_fixture).resolve()
        if not _under(repo, allowed):
            return {"ok": False, "status": "POLICY_BLOCK", "summary": "fixture must be under allowed_root"}
        if repo.exists() and any(repo.iterdir()):
            return {"ok": False, "status": "POLICY_BLOCK", "summary": "fixture path must be empty disposable directory"}
        repo.mkdir(parents=True, exist_ok=True)
    else:
        repo = (smoke_root / f"repo_{uuid.uuid4().hex}").resolve()
        if not _under(repo, state):
            return {"ok": False, "status": "POLICY_BLOCK", "summary": "smoke repo must be under state_dir"}
        repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    source = repo / "app.py"
    source.write_bytes(b"old smoke\n")
    original_sha = sha256_file(source)
    generator = PatchGenerationService(queue_db, patch_root, allowed_roots=(allowed, state))
    patch = generator.create_patch_from_before_after(
        run_id="smoke-run",
        project_id="smoke-project",
        project_scope_hash="smoke-scope",
        selected_skill_id="patch_apply_and_test_v1",
        target_repo=repo,
        changes=[{"rel_path": "app.py", "before": "old smoke\n", "after": "new smoke\n"}],
    )["patch_artifact"]
    approval_id = f"approval_{uuid.uuid4().hex}"
    PatchArtifactRepository(queue_db).insert_approval_record(
        {
            "approval_id": approval_id,
            "patch_id": patch["patch_id"],
            "run_id": "smoke-run",
            "project_id": "smoke-project",
            "project_scope_hash": "smoke-scope",
            "target_repo": str(repo),
            "approved": True,
            "approved_by": "smoke-harness",
            "approved_at": _now(),
            "approval_scope": "smoke_test_only",
            "approved_diff_sha256": patch["diff_sha256"],
            "declared_tests_json": [],
            "created_at": _now(),
            "notes": "disposable smoke flow",
        }
    )
    apply = PatchApplyService(
        queue_db,
        rollback_root,
        allowed_roots=(allowed, state),
        memory_service=memory_service,
        conversation_summary_ingestor=conversation_summary_ingestor,
    ).apply_approved_patch(patch_id=str(patch["patch_id"]), approval_id=approval_id, target_repo=repo)
    changed_sha = sha256_file(source)
    snapshots = PatchArtifactRepository(queue_db).list_file_snapshots(str(apply.get("apply_run_id", "")))
    restore = {"ok": True, "status": "SKIPPED"}
    post_restore_sha = changed_sha
    if restore_after_apply and apply.get("apply_run_id"):
        restore = RollbackRestoreService(queue_db, rollback_root).restore_apply_run(str(apply["apply_run_id"]))
        post_restore_sha = sha256_file(source)
    ok = bool(apply.get("ok")) and changed_sha != original_sha and bool(snapshots) and bool(apply.get("rollback_available")) and (not restore_after_apply or post_restore_sha == original_sha)
    return {
        "ok": ok,
        "status": "SMOKE_PASSED" if ok else "SMOKE_FAILED",
        "patch_id": patch["patch_id"],
        "approval_id": approval_id,
        "apply_run_id": apply.get("apply_run_id"),
        "repo_path": str(repo),
        "rollback_available": bool(apply.get("rollback_available")),
        "tests_status": apply.get("tests_status"),
        "original_sha256": original_sha,
        "changed_sha256": changed_sha,
        "post_restore_sha256": post_restore_sha,
        "snapshot_count": len(snapshots),
        "rollback": restore,
        "memory_commit": apply.get("memory_commit", {"status": "SKIPPED", "reason": "memory_service_unavailable"}),
    }
