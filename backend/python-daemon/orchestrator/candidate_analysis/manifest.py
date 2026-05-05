from __future__ import annotations

import csv
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ABSOLUTE_PATH_COLUMNS = ("abs_path", "absolute_path", "path", "file")
RELATIVE_PATH_COLUMNS = ("rel_path", "relative_path")
EXCLUDED_NAMES = {"session.yaml"}
EXCLUDED_PATTERNS = (
    "local_tool_assist_outputs/*",
    "*/local_tool_assist_outputs/*",
    "reports/final_handoff*",
    "archive/session*",
    "sessions/*/intermediate/*",
    "*_bundle*.py",
    "*_bundle*.yaml",
    "manifest_doctor.*",
    "*/manifest_doctor.*",
)


@dataclass(frozen=True)
class ManifestLoadResult:
    ok: bool
    status: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None


def load_manifest_candidates(manifest_path: str | Path, target_repo: str | Path) -> ManifestLoadResult:
    manifest = Path(manifest_path).expanduser().resolve()
    repo = Path(target_repo).expanduser().resolve()
    warnings: list[dict[str, str]] = []
    try:
        with manifest.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        return ManifestLoadResult(
            ok=False,
            status="WARN",
            warnings=[{"artifact_key": "manifest_csv", "message": str(exc)[:500]}],
            error=str(exc)[:500],
        )
    if not rows:
        return ManifestLoadResult(
            ok=False,
            status="WARN",
            warnings=[{"artifact_key": "manifest_csv", "message": "manifest_csv contained no rows"}],
        )

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        candidate = _row_to_candidate(row, repo, manifest)
        if candidate is None:
            continue
        key = str(candidate["path"])
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    candidates.sort(key=lambda item: str(item["rel_path"]))
    if not candidates:
        return ManifestLoadResult(
            ok=False,
            status="WARN",
            warnings=[{"artifact_key": "manifest_csv", "message": "manifest_csv yielded no target_repo source files"}],
        )
    return ManifestLoadResult(ok=True, status="OK", candidates=candidates, warnings=warnings)


def _row_to_candidate(row: dict[str, Any], repo: Path, manifest: Path) -> dict[str, Any] | None:
    abs_value = _first_present(row, ABSOLUTE_PATH_COLUMNS)
    rel_value = _first_present(row, RELATIVE_PATH_COLUMNS)
    if abs_value:
        path = Path(str(abs_value)).expanduser()
        if not path.is_absolute():
            path = repo / path
    elif rel_value:
        path = repo / str(rel_value)
    else:
        return None
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if resolved == manifest:
        return None
    if not _is_under(resolved, repo):
        return None
    try:
        rel_path = resolved.relative_to(repo).as_posix()
    except ValueError:
        return None
    if rel_value:
        normalized_rel = Path(str(rel_value).replace("\\", "/")).as_posix()
        if normalized_rel and not normalized_rel.startswith(".."):
            rel_path = normalized_rel
    if _is_excluded(rel_path):
        return None
    return {
        "path": str(resolved),
        "rel_path": rel_path,
        "ext": str(row.get("ext") or resolved.suffix),
        "size": str(row.get("size") or ""),
        "sha1": str(row.get("sha1") or ""),
    }


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _is_excluded(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    name = Path(normalized).name
    if name in EXCLUDED_NAMES:
        return True
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in EXCLUDED_PATTERNS)
