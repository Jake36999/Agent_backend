from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PatchValidationResult:
    ok: bool
    status: str
    affected_paths: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "affected_paths": list(self.affected_paths),
            "error": self.error,
        }


@dataclass(frozen=True)
class PatchArtifact:
    patch_id: str
    run_id: str | None
    project_id: str | None
    project_scope_hash: str | None
    selected_skill_id: str | None
    target_repo: str
    status: str
    patch_path: str
    diff_sha256: str
    affected_paths_json: list[str]
    created_at: str
    validation_status: str
    validation_error: str | None = None

    def to_record_tuple(self) -> tuple[object, ...]:
        import json

        return (
            self.patch_id,
            self.run_id,
            self.project_id,
            self.project_scope_hash,
            self.selected_skill_id,
            self.target_repo,
            self.status,
            self.patch_path,
            self.diff_sha256,
            json.dumps(self.affected_paths_json, sort_keys=True),
            self.created_at,
            self.validation_status,
            self.validation_error,
        )

    def to_compact_dict(self) -> dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "status": self.status,
            "patch_path": self.patch_path,
            "diff_sha256": self.diff_sha256,
            "affected_paths": list(self.affected_paths_json),
            "validation_status": self.validation_status,
            "validation_error": self.validation_error,
        }
