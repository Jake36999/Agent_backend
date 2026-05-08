from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FileSignal:
    path: str
    line_count: int


@dataclass(frozen=True)
class DependencySignal:
    path: str
    count: int


@dataclass(frozen=True)
class TodoSignal:
    path: str
    count: int
    kinds: tuple[str, ...]


@dataclass(frozen=True)
class CodeReviewHeuristics:
    largest_files: tuple[FileSignal, ...]
    highest_fan_in: tuple[DependencySignal, ...]
    highest_fan_out: tuple[DependencySignal, ...]
    orphan_files: tuple[str, ...]
    external_dependencies: tuple[str, ...]
    todo_fixme_counts: tuple[TodoSignal, ...]
    test_directories: tuple[str, ...]
    likely_entrypoints: tuple[str, ...]


_EMPTY = CodeReviewHeuristics(
    largest_files=(),
    highest_fan_in=(),
    highest_fan_out=(),
    orphan_files=(),
    external_dependencies=(),
    todo_fixme_counts=(),
    test_directories=(),
    likely_entrypoints=(),
)


def _parse_json(text: str, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return default


def _artifact(step_outputs: dict[str, Any], step_id: str, key: str) -> str:
    return str(step_outputs.get(step_id, {}).get("artifacts", {}).get(key) or "")


def extract_heuristics(step_outputs: dict[str, Any]) -> CodeReviewHeuristics:
    raw_largest = _parse_json(_artifact(step_outputs, "repo_context", "largest_files_json"), [])
    raw_test_dirs = _parse_json(_artifact(step_outputs, "repo_context", "test_dirs_json"), [])
    raw_entrypoints = _parse_json(_artifact(step_outputs, "repo_context", "entrypoints_json"), [])
    raw_todos = _parse_json(_artifact(step_outputs, "repo_context", "todo_fixme_json"), [])

    raw_fan_in = _parse_json(_artifact(step_outputs, "dependency_graph", "fan_in_json"), [])
    raw_fan_out = _parse_json(_artifact(step_outputs, "dependency_graph", "fan_out_json"), [])
    raw_orphans = _parse_json(_artifact(step_outputs, "dependency_graph", "orphans_json"), [])
    raw_externals = _parse_json(_artifact(step_outputs, "dependency_graph", "external_deps_json"), [])

    largest_files = tuple(
        FileSignal(path=str(f.get("path", "")), line_count=int(f.get("line_count", 0)))
        for f in raw_largest[:20]
        if isinstance(f, dict) and f.get("path")
    )
    highest_fan_in = tuple(
        DependencySignal(path=str(d.get("path", "")), count=int(d.get("count", 0)))
        for d in raw_fan_in[:20]
        if isinstance(d, dict) and d.get("path")
    )
    highest_fan_out = tuple(
        DependencySignal(path=str(d.get("path", "")), count=int(d.get("count", 0)))
        for d in raw_fan_out[:20]
        if isinstance(d, dict) and d.get("path")
    )
    todo_fixme_counts = tuple(
        TodoSignal(
            path=str(t.get("path", "")),
            count=int(t.get("count", 0)),
            kinds=tuple(str(k) for k in (t.get("kinds") or [])),
        )
        for t in raw_todos[:20]
        if isinstance(t, dict) and t.get("path")
    )

    return CodeReviewHeuristics(
        largest_files=largest_files,
        highest_fan_in=highest_fan_in,
        highest_fan_out=highest_fan_out,
        orphan_files=tuple(str(o) for o in raw_orphans[:20] if isinstance(o, str)),
        external_dependencies=tuple(str(e) for e in raw_externals[:50] if isinstance(e, str)),
        todo_fixme_counts=todo_fixme_counts,
        test_directories=tuple(str(d) for d in raw_test_dirs[:20] if isinstance(d, str)),
        likely_entrypoints=tuple(str(ep) for ep in raw_entrypoints[:20] if isinstance(ep, str)),
    )
