from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CodeReviewReport

# Fixed artifact filenames — never user-controlled
_ARTIFACT_FILES: dict[str, tuple[str, str]] = {
    "architecture_overview_md": ("architecture_overview.md", "text/markdown"),
    "dependency_graph_mmd": ("dependency_graph.mmd", "text/plain"),
    "code_review_summary_md": ("code_review_summary.md", "text/markdown"),
    "next_actions_yaml": ("next_actions.yaml", "text/yaml"),
    "heuristics_json": ("heuristics.json", "application/json"),
}

_MANIFEST_FILENAME = "code_review_artifacts_manifest.json"
_MAX_ARTIFACT_BYTES = 64 * 1024  # 64 KB hard ceiling per file


def _safe_artifact_dir(state_dir: Path, run_id: str) -> Path:
    """Return {state_dir}/{run_id}/, rejecting any traversal in run_id."""
    artifact_dir = (state_dir / run_id).resolve()
    resolved_state = state_dir.resolve()
    if not (artifact_dir == resolved_state or resolved_state in artifact_dir.parents):
        raise ValueError(f"run_id '{run_id}' escapes state_dir")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _write_artifact(dest: Path, content: str) -> tuple[str, int, str]:
    """Write content (bounded) to dest. Returns (hex_sha256, byte_size, truncation note)."""
    encoded = content.encode("utf-8")[: _MAX_ARTIFACT_BYTES]
    dest.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    return digest, len(encoded)


def persist_code_review_artifacts(
    report: CodeReviewReport,
    run_id: str,
    state_dir: Path,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Write each report artifact to ``{state_dir}/{run_id}/``.

    Returns:
        refs: artifact key → absolute file path (str)
        manifest_entries: artifact key → manifest dict
    """
    artifact_dir = _safe_artifact_dir(state_dir, run_id)
    now = datetime.now(timezone.utc).isoformat()

    refs: dict[str, str] = {}
    manifest_entries: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    for key, (filename, content_type) in _ARTIFACT_FILES.items():
        content: str = getattr(report, key, "") or ""
        if not content:
            continue
        dest = artifact_dir / filename
        try:
            sha256, byte_size = _write_artifact(dest, content)
        except Exception as exc:
            errors[key] = str(exc)[:200]
            continue
        path_str = str(dest)
        refs[key] = path_str
        manifest_entries[key] = {
            "artifact_key": key,
            "filename": filename,
            "relative_path": filename,
            "sha256": sha256,
            "bytes": byte_size,
            "content_type": content_type,
            "created_at": now,
        }

    manifest = {
        "run_id": run_id,
        "created_at": now,
        "artifacts": manifest_entries,
        **({"errors": errors} if errors else {}),
    }
    manifest_path = artifact_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return refs, manifest_entries


def build_report_index(manifest_entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build the ``code_review_report_index`` dict from manifest entries."""
    return {
        key: {
            "path": entry["filename"],
            "sha256": entry["sha256"],
            "bytes": entry["bytes"],
        }
        for key, entry in manifest_entries.items()
    }


def persist_draft_review(
    draft: str,
    run_id: str,
    state_dir: Path,
) -> str:
    """Write the model-assisted draft review and return its absolute path."""
    artifact_dir = _safe_artifact_dir(state_dir, run_id)
    encoded = draft.encode("utf-8")[:_MAX_ARTIFACT_BYTES]
    dest = artifact_dir / "review_draft.md"
    dest.write_bytes(encoded)
    return str(dest)
