from __future__ import annotations

import difflib
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import PatchArtifact
from .repo import PatchArtifactRepository
from .validation import PatchValidationService


class PatchGenerationService:
    def __init__(
        self,
        queue_db_path: Path,
        artifact_root: Path,
        *,
        allowed_roots: tuple[Path, ...],
        validator: PatchValidationService | None = None,
    ) -> None:
        self.repo = PatchArtifactRepository(queue_db_path)
        self.artifact_root = Path(artifact_root).resolve()
        self.allowed_roots = tuple(Path(root).resolve() for root in allowed_roots)
        self.validator = validator or PatchValidationService(allowed_roots=self.allowed_roots)

    def create_patch_from_before_after(
        self,
        *,
        run_id: str | None,
        project_id: str | None,
        project_scope_hash: str | None,
        selected_skill_id: str | None,
        target_repo: str | Path,
        changes: list[dict[str, str]],
    ) -> dict[str, Any]:
        target_repo_path = Path(target_repo).resolve()
        diff_text = self._build_diff(changes)
        validation = self.validator.validate_unified_diff(diff_text, target_repo=target_repo_path, run_git_check=False)
        patch_id = f"patch_{uuid.uuid4().hex}"
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        patch_path = self.artifact_root / f"{patch_id}.diff"
        diff_bytes = diff_text.encode("utf-8")
        patch_path.write_bytes(diff_bytes)
        digest = hashlib.sha256(diff_bytes).hexdigest()
        artifact = PatchArtifact(
            patch_id=patch_id,
            run_id=run_id,
            project_id=project_id,
            project_scope_hash=project_scope_hash,
            selected_skill_id=selected_skill_id,
            target_repo=str(target_repo_path),
            status="created" if validation.ok else "validation_failed",
            patch_path=str(patch_path),
            diff_sha256=digest,
            affected_paths_json=validation.affected_paths,
            created_at=datetime.now(timezone.utc).isoformat(),
            validation_status=validation.status,
            validation_error=validation.error[:500] if validation.error else None,
        )
        self.repo.insert(artifact)
        return {
            "ok": validation.ok,
            "status": "CREATED" if validation.ok else "VALIDATION_FAILED",
            "patch_artifact": artifact.to_compact_dict(),
            "validation": validation.to_dict(),
        }

    def _build_diff(self, changes: list[dict[str, str]]) -> str:
        pieces: list[str] = []
        for change in changes:
            rel_path = str(change["rel_path"]).replace("\\", "/")
            before = str(change.get("before") or "")
            after = str(change.get("after") or "")
            fromfile = f"a/{rel_path}" if before else "/dev/null"
            tofile = f"b/{rel_path}" if after else "/dev/null"
            pieces.extend(
                difflib.unified_diff(
                    before.splitlines(),
                    after.splitlines(),
                    fromfile=fromfile,
                    tofile=tofile,
                    lineterm="\n",
                )
            )
        return "".join(line if line.endswith("\n") else f"{line}\n" for line in pieces)
