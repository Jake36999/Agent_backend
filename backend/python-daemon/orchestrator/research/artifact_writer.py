from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ARTIFACT_FILES: dict[str, tuple[str, str]] = {
    "research_report_md":         ("research_report.md",       "text/markdown"),
    "research_citations_json":    ("research_citations.json",  "application/json"),
    "research_sources_json":      ("research_sources.json",    "application/json"),
    "research_next_actions_yaml": ("research_next_actions.yaml", "text/yaml"),
}

_MANIFEST_FILENAME = "research_artifacts_manifest.json"
_MAX_ARTIFACT_BYTES = 64 * 1024


def _safe_artifact_dir(state_dir: Path, run_id: str) -> Path:
    artifact_dir = (state_dir / run_id).resolve()
    resolved_state = state_dir.resolve()
    if not (artifact_dir == resolved_state or resolved_state in artifact_dir.parents):
        raise ValueError(f"run_id '{run_id}' escapes state_dir")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _write_artifact(dest: Path, content: str) -> tuple[str, int]:
    encoded = content.encode("utf-8")[: _MAX_ARTIFACT_BYTES]
    dest.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest(), len(encoded)


def persist_research_artifacts(
    content: dict[str, str],
    run_id: str,
    state_dir: Path,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Write recognised artifact keys from *content* to ``{state_dir}/{run_id}/``.

    Returns:
        refs: artifact_key → absolute file path
        manifest_entries: artifact_key → metadata dict
    """
    artifact_dir = _safe_artifact_dir(state_dir, run_id)
    now = datetime.now(timezone.utc).isoformat()

    refs: dict[str, str] = {}
    manifest_entries: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    for key, (filename, content_type) in _ARTIFACT_FILES.items():
        raw = content.get(key, "")
        if not raw:
            continue
        dest = artifact_dir / filename
        try:
            sha256, byte_size = _write_artifact(dest, raw)
        except Exception as exc:
            errors[key] = str(exc)[:200]
            continue
        refs[key] = str(dest)
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
    (artifact_dir / _MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return refs, manifest_entries


def build_research_index(manifest_entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        key: {
            "path": entry["filename"],
            "sha256": entry["sha256"],
            "bytes": entry["bytes"],
        }
        for key, entry in manifest_entries.items()
    }
