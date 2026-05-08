from __future__ import annotations

import re
from graphlib import CycleError, TopologicalSorter
from typing import Any

from .models import ArgBinding, CompiledPlan, PipelineDefinition, PipelineStep


_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)}")

ALLOWED_UNRESOLVED_VARS: frozenset[str] = frozenset({"session_path"})


class PipelineCompileError(ValueError):
    pass


class PipelineCompiler:

    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        self.allowed_tools = allowed_tools

    def compile(
        self,
        definition: PipelineDefinition,
        runtime_vars: dict[str, str] | None = None,
    ) -> CompiledPlan:
        self._validate(definition)
        ordered = self._topological_order(definition.steps)
        ordered_ids = [s.step_id for s in ordered]
        self._validate_bindings(definition.steps, ordered_ids)
        todos: list[dict[str, Any]] = []
        for step in ordered:
            resolved_args = self._resolve_args(step.args_template, runtime_vars or {}, definition.variables)
            unresolved = self._collect_unresolved(resolved_args)
            if unresolved:
                raise PipelineCompileError(
                    f"step '{step.step_id}' has unresolved variables: {sorted(set(unresolved))}"
                )
            todos.append(
                {
                    "id": step.step_id,
                    "status": "pending",
                    "description": step.description,
                    "tool_name": step.tool_name,
                    "args": self._serialize_args(resolved_args),
                    "outputs": dict(step.outputs),
                }
            )
        return CompiledPlan(
            pipeline_id=definition.pipeline_id,
            version=definition.version,
            todos=todos,
        )

    def compile_to_plan_list(
        self,
        definition: PipelineDefinition,
        runtime_vars: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        return self.compile(definition, runtime_vars).todos

    def _validate(self, definition: PipelineDefinition) -> None:
        if not definition.steps:
            raise PipelineCompileError("pipeline has no steps")
        if len(definition.steps) > definition.max_steps:
            raise PipelineCompileError(
                f"pipeline has {len(definition.steps)} steps, exceeds max_steps={definition.max_steps}"
            )
        step_ids = {s.step_id for s in definition.steps}
        if len(step_ids) != len(definition.steps):
            raise PipelineCompileError("duplicate step_id in pipeline")

        for step in definition.steps:
            if self.allowed_tools is not None and step.tool_name not in self.allowed_tools:
                raise PipelineCompileError(f"tool '{step.tool_name}' is not in allowed_tools")
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise PipelineCompileError(
                        f"step '{step.step_id}' depends on unknown step '{dep}'"
                    )

    def _validate_bindings(
        self,
        steps: tuple[PipelineStep, ...],
        ordered_ids: list[str],
    ) -> None:
        step_id_set = {s.step_id for s in steps}
        dep_map = {s.step_id: set(s.depends_on) for s in steps}

        for step in steps:
            for key, arg_val in step.args_template.items():
                if not isinstance(arg_val, ArgBinding):
                    continue
                ref = arg_val.from_step
                if ref == step.step_id:
                    raise PipelineCompileError(
                        f"step '{step.step_id}' binding '{key}' references itself"
                    )
                if ref not in step_id_set:
                    raise PipelineCompileError(
                        f"step '{step.step_id}' binding '{key}' references unknown step '{ref}'"
                    )
                if ordered_ids.index(ref) >= ordered_ids.index(step.step_id):
                    raise PipelineCompileError(
                        f"step '{step.step_id}' binding '{key}' references step '{ref}' "
                        "which does not precede it in topological order"
                    )
                if ref not in dep_map[step.step_id]:
                    raise PipelineCompileError(
                        f"step '{step.step_id}' binding '{key}' references step '{ref}' "
                        f"but '{ref}' is not listed in depends_on — add it"
                    )

    def _topological_order(self, steps: tuple[PipelineStep, ...]) -> list[PipelineStep]:
        step_map = {s.step_id: s for s in steps}
        graph: dict[str, set[str]] = {}
        for step in steps:
            graph[step.step_id] = set(step.depends_on)
        sorter = TopologicalSorter(graph)
        try:
            ordered_ids = list(sorter.static_order())
        except CycleError as exc:
            raise PipelineCompileError(f"dependency cycle detected: {exc}") from exc
        return [step_map[sid] for sid in ordered_ids]

    def _collect_unresolved(self, args: dict[str, Any]) -> list[str]:
        found: list[str] = []
        for value in args.values():
            if isinstance(value, ArgBinding):
                continue  # runtime-resolved; not a template variable
            elif isinstance(value, str):
                for m in _VAR_RE.finditer(value):
                    if m.group(1) not in ALLOWED_UNRESOLVED_VARS:
                        found.append(m.group(1))
            elif isinstance(value, dict):
                found.extend(self._collect_unresolved(value))
        return found

    def _resolve_args(
        self,
        args_template: dict[str, Any],
        runtime_vars: dict[str, str],
        declared_vars: dict[str, str],
    ) -> dict[str, Any]:
        merged = {**declared_vars, **runtime_vars}
        resolved: dict[str, Any] = {}
        for key, value in args_template.items():
            if isinstance(value, ArgBinding):
                resolved[key] = value  # preserved until _serialize_args
            elif isinstance(value, str):
                resolved[key] = _VAR_RE.sub(lambda m: merged.get(m.group(1), m.group(0)), value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_args(value, runtime_vars, declared_vars)
            else:
                resolved[key] = value
        return resolved

    def _serialize_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Convert ArgBinding instances to JSON-serializable sentinel dicts."""
        out: dict[str, Any] = {}
        for k, v in args.items():
            if isinstance(v, ArgBinding):
                out[k] = {"__binding__": True, "from_step": v.from_step, "path": v.path}
            elif isinstance(v, dict):
                out[k] = self._serialize_args(v)
            else:
                out[k] = v
        return out
