from __future__ import annotations

import re
from pathlib import Path

_DIFF_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$")


class DiffValidationError(ValueError):
    pass


def parse_affected_files(unified_diff: str) -> list[str]:
    if not unified_diff or not unified_diff.strip():
        raise DiffValidationError("unified diff is empty")
    files: list[str] = []
    for line in unified_diff.splitlines():
        match = _DIFF_FILE_RE.match(line.strip())
        if not match:
            continue
        for candidate in match.groups():
            if candidate not in files:
                files.append(candidate)
    if not files:
        raise DiffValidationError("unified diff did not contain diff --git file headers")
    return files


def validate_affected_files(target_repo: Path, affected_files: list[str]) -> list[Path]:
    root = Path(target_repo).resolve()
    resolved: list[Path] = []
    for rel in affected_files:
        rel_norm = rel.replace("\\", "/")
        if rel_norm.startswith("/") or ".." in rel_norm.split("/"):
            raise DiffValidationError(f"unsafe diff path: {rel}")
        lower = rel_norm.lower()
        if lower.startswith(".git/") or "/.git/" in lower:
            raise DiffValidationError("diff may not touch .git")
        if lower.endswith(".env") or "/.env" in lower:
            raise DiffValidationError("diff may not touch env/secret files")
        if "private" in lower and ("key" in lower or lower.endswith(".pem")):
            raise DiffValidationError("diff may not touch private key files")
        if any(part in {".aletheia_state", "chroma", "__pycache__", ".pytest_cache"} for part in lower.split("/")):
            raise DiffValidationError("diff may not touch generated runtime state/cache directories")
        absolute = (root / rel_norm).resolve()
        if absolute != root and root not in absolute.parents:
            raise DiffValidationError(f"diff path escapes target repo: {rel}")
        resolved.append(absolute)
    return resolved
