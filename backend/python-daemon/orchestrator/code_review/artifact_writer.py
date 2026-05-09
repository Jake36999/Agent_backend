from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import CodeReviewReport

_ARTIFACT_EXTENSIONS: dict[str, str] = {
    "architecture_overview_md": ".md",
    "dependency_graph_mmd": ".mmd",
    "code_review_summary_md": ".md",
    "next_actions_yaml": ".yaml",
    "heuristics_json": ".json",
}

_MAX_ARTIFACT_BYTES = 64 * 1024  # 64 KB hard ceiling per file


def persist_code_review_artifacts(
    report: CodeReviewReport,
    run_id: str,
    state_dir: Path,
) -> dict[str, str]:
    """Write each report artifact to ``{state_dir}/{run_id}/`` and return
    a mapping of artifact key → absolute file path."""
    artifact_dir = state_dir / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    refs: dict[str, str] = {}
    for key, ext in _ARTIFACT_EXTENSIONS.items():
        content: str = getattr(report, key, "")
        if not content:
            continue
        encoded = content.encode("utf-8")[:_MAX_ARTIFACT_BYTES]
        dest = artifact_dir / f"{key}{ext}"
        dest.write_bytes(encoded)
        refs[key] = str(dest)

    return refs


def persist_draft_review(
    draft: str,
    run_id: str,
    state_dir: Path,
) -> str:
    """Write the model-assisted draft review and return its absolute path."""
    artifact_dir = state_dir / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    encoded = draft.encode("utf-8")[:_MAX_ARTIFACT_BYTES]
    dest = artifact_dir / "review_draft.md"
    dest.write_bytes(encoded)
    return str(dest)
