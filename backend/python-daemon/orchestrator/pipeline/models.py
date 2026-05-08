from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ArgBinding:
    from_step: str
    path: str  # shallow dot-path, e.g. "artifacts.session_path"


@dataclass(frozen=True)
class PipelineStep:
    step_id: str
    tool_name: str
    args_template: dict[str, Any]
    description: str
    depends_on: tuple[str, ...] = ()
    outputs: dict[str, str] = field(default_factory=dict)
    required_outputs: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()
    depth: int = 0


@dataclass(frozen=True)
class PipelineDefinition:
    pipeline_id: str
    version: str
    name: str
    description: str
    steps: tuple[PipelineStep, ...]
    variables: dict[str, str] = field(default_factory=dict)
    max_steps: int = 20


@dataclass(frozen=True)
class CompiledPlan:
    pipeline_id: str
    version: str
    todos: list[dict[str, Any]] = field(default_factory=list)
