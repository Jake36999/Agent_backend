from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PatchArtifact:
    patch_id: str
    project_id: str | None
    project_scope_hash: str | None
    run_id: str | None
    selected_skill_id: str | None
    objective: str
    unified_diff: str
    affected_files: list[str]
    test_commands: list[str]
    guardrail_checks: list[dict[str, Any]]
    audit_state: dict[str, Any]
    status: str
    created_at: str


@dataclass(frozen=True)
class FileSnapshot:
    snapshot_id: str
    patch_id: str
    absolute_path: str
    file_sha_before: str
    content_before_path: str
    created_at: str
