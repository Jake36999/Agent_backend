from __future__ import annotations

import csv
import io
import re
from pathlib import PurePosixPath
from typing import Any

STOPWORDS = {
    "a", "an", "and", "as", "by", "do", "for", "from", "in", "into", "of", "on", "only", "or",
    "the", "this", "to", "with", "plan", "produce", "create", "write", "fix", "issue", "bug",
}
PENALIZED_SEGMENTS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".mypy_cache"}
PENALIZED_PATTERNS = ("bundle", "generated", "cache", "coverage")
TEST_PATTERNS = ("tests/", "test_", "_test.", ".test.")
SYMBOL_RE = re.compile(r"\b(class|def|function|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)")


def tokenize(text: str | None) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", (text or "").lower()) if t not in STOPWORDS and len(t) > 1}


def parse_manifest_candidates(manifest_csv: str | None) -> list[dict[str, Any]]:
    if not manifest_csv:
        return []
    candidates: list[dict[str, Any]] = []
    try:
        reader = csv.DictReader(io.StringIO(manifest_csv))
        if reader.fieldnames:
            for row in reader:
                path = row.get("path") or row.get("file") or row.get("relative_path")
                if path:
                    candidates.append({"path": str(path), "row": dict(row)})
            if candidates:
                return candidates
    except csv.Error:
        pass
    for line in manifest_csv.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        first = line.split(",", 1)[0].strip()
        if "/" in first or "\\" in first or "." in PurePosixPath(first.replace("\\", "/")).name:
            candidates.append({"path": first.replace("\\", "/"), "row": {}})
    return candidates


def score_path(path: str, context_tokens: set[str], rag_tokens: set[str]) -> dict[str, Any]:
    normalized = path.replace("\\", "/")
    p = PurePosixPath(normalized)
    path_tokens = tokenize(normalized.replace("/", " ").replace(".", " ").replace("_", " "))
    stem_tokens = tokenize(p.stem.replace("_", " ").replace("-", " "))
    evidence: list[str] = []
    risk_notes: list[str] = []
    test_seams: list[str] = []
    score = 0.0

    direct = path_tokens.intersection(context_tokens)
    if direct:
        score += 3.0 * len(direct)
        evidence.append(f"path token match: {', '.join(sorted(direct)[:6])}")
    stem = stem_tokens.intersection(context_tokens)
    if stem:
        score += 2.0 * len(stem)
        evidence.append(f"filename/stem match: {', '.join(sorted(stem)[:6])}")
    semantic = path_tokens.intersection(rag_tokens)
    if semantic:
        score += 1.5 * len(semantic)
        evidence.append(f"rag context match: {', '.join(sorted(semantic)[:6])}")

    lower = normalized.lower()
    if any(pattern in lower for pattern in TEST_PATTERNS):
        score += 1.5
        test_seams.append(normalized)
        evidence.append("test seam proximity")
    if any(segment in lower.split("/") for segment in PENALIZED_SEGMENTS) or any(pattern in lower for pattern in PENALIZED_PATTERNS):
        score -= 8.0
        risk_notes.append("generated or non-source path penalty")
    if lower.endswith(('.py', '.mjs', '.js', '.ts', '.tsx', '.json', '.md')):
        score += 0.25
    confidence = max(0.0, min(1.0, score / 20.0))
    return {"path": normalized, "score": score, "confidence": confidence, "evidence": evidence, "risk_notes": risk_notes, "test_seams": test_seams}
