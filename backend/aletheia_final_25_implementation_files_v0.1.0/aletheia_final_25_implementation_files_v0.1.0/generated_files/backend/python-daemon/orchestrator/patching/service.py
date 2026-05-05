from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .diff import parse_affected_files, validate_affected_files
from .guardrails import check_diff_generation
from .models import PatchArtifact
from .repo import PatchRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _patch_id(unified_diff: str) -> str:
    digest = hashlib.sha256(unified_diff.encode("utf-8")).hexdigest()[:24]
    return f"patch_{digest}_{uuid.uuid4().hex[:8]}"


class PatchGenerationService:
    def __init__(self, queue_db_path: Path) -> None:
        self.repo = PatchRepository(queue_db_path)

    def create_patch_artifact(
        self,
        *,
        objective: str,
        target_repo: Path,
        unified_diff: str,
        selected_skill_id: str | None,
        project_id: str | None,
        project_scope_hash: str | None,
        run_id: str | None,
        test_commands: list[str],
    ) -> dict[str, object]:
        affected_files = parse_affected_files(unified_diff)
        validate_affected_files(Path(target_repo), affected_files)
        guardrail_checks = check_diff_generation()
        patch_id = _patch_id(unified_diff)
        audit_state: dict[str, Any] = {
            "risk_tier": "T2",
            "unified_diff_sha256": hashlib.sha256(unified_diff.encode("utf-8")).hexdigest(),
            "applied": False,
            "tests_run": False,
            "committed": False,
            "pushed": False,
            "requires_approval_for_apply": True,
        }
        artifact = PatchArtifact(
            patch_id=patch_id,
            project_id=project_id,
            project_scope_hash=project_scope_hash,
            run_id=run_id,
            selected_skill_id=selected_skill_id,
            objective=objective,
            unified_diff=unified_diff,
            affected_files=affected_files,
            test_commands=list(test_commands or []),
            guardrail_checks=guardrail_checks,
            audit_state=audit_state,
            status="generated",
            created_at=_utc_now(),
        )
        self.repo.insert_artifact(artifact)
        return {
            "ok": True,
            "status": "generated",
            "patch_id": patch_id,
            "affected_files": affected_files,
            "test_commands": list(test_commands or []),
            "guardrail_checks": guardrail_checks,
            "audit_state": audit_state,
            "requires_approval_for_apply": True,
        }
