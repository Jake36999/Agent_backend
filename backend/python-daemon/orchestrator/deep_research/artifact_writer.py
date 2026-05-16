from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import DeepResearchReport

_ARTIFACT_FILES: dict[str, tuple[str, str]] = {
    "research_report_md":    ("research_report.md",    "text/markdown"),
    "research_findings_md":  ("research_findings.md",  "text/markdown"),
    "research_citations_yaml": ("research_citations.yaml", "text/yaml"),
    "research_sources_md":   ("research_sources.md",   "text/markdown"),
}

_MANIFEST_FILENAME = "deep_research_artifacts_manifest.json"
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


_REPORT_ATTR_MAP: dict[str, str] = {
    "research_report_md":      "executive_summary_md",
    "research_findings_md":    "findings_md",
    "research_citations_yaml": "citations_yaml",
    "research_sources_md":     "sources_index_md",
}


def persist_deep_research_artifacts(
    report: DeepResearchReport,
    run_id: str,
    state_dir: Path,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    artifact_dir = _safe_artifact_dir(state_dir, run_id)
    now = datetime.now(timezone.utc).isoformat()

    refs: dict[str, str] = {}
    manifest_entries: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    for key, (filename, content_type) in _ARTIFACT_FILES.items():
        attr = _REPORT_ATTR_MAP.get(key, key)
        content: str = getattr(report, attr, "") or ""
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
