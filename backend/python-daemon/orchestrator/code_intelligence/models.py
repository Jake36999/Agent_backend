from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CodeMapEntry:
    rel_path: str
    language: str
    size_bytes: int
    line_count: int


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    kind: str
    is_external: bool


@dataclass
class DependencyGraph:
    nodes: list[str] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)
    truncated: bool = False
