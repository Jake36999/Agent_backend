from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

from .models import ArgBinding, PipelineDefinition, PipelineStep


class PipelineLoadError(ValueError):
    pass


_PIPELINE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Allowed shallow binding paths: prefix.name, e.g. "artifacts.session_path"
_BINDING_PATH_RE = re.compile(
    r"^(artifacts|result|error|status|summary)\.[A-Za-z_][A-Za-z0-9_]*$"
)


def _parse_arg_value(v: Any) -> Any:
    """Convert a raw YAML arg value to a Python value, parsing bind: dicts into ArgBinding."""
    if isinstance(v, dict):
        keys = set(v.keys())
        if keys == {"bind"}:
            inner = v["bind"]
            if not isinstance(inner, dict) or "from_step" not in inner or "path" not in inner:
                raise PipelineLoadError(
                    "malformed binding: 'bind' must contain 'from_step' and 'path'"
                )
            path = str(inner["path"])
            if not _BINDING_PATH_RE.fullmatch(path):
                raise PipelineLoadError(
                    f"binding path {path!r} must be a shallow dot-path "
                    "(e.g. 'artifacts.session_path'); deep paths are not supported"
                )
            return ArgBinding(from_step=str(inner["from_step"]), path=path)
        # Normal dict (nested args) — recurse
        return {k: _parse_arg_value(inner) for k, inner in v.items()}
    return v

ACTIVE_PIPELINES: frozenset[str] = frozenset({"investigation", "patch_plan", "code_review", "deep_research"})

RESERVED_PIPELINE_IDS: frozenset[str] = frozenset({
    "mcp_pipeline_run",
    "mcp_agent_workflow_run",
    "tools",
    "admin",
    "debug",
    "schema",
    "examples",
    "staging",
})

_SCHEMA_PATH = Path(__file__).parent / "templates" / "pipeline.schema.json"


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.exists():
        return {}
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class PipelineLoader:

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"

    def list_templates(self) -> list[str]:
        if not self.templates_dir.exists():
            return []
        return sorted(
            p.stem for p in self.templates_dir.glob("*.yaml")
            if _PIPELINE_ID_RE.fullmatch(p.stem) and p.stem in ACTIVE_PIPELINES
        )

    def load(self, pipeline_id: str) -> PipelineDefinition:
        if not _PIPELINE_ID_RE.fullmatch(pipeline_id):
            raise PipelineLoadError(f"invalid pipeline_id: {pipeline_id!r}")
        if pipeline_id in RESERVED_PIPELINE_IDS:
            raise PipelineLoadError(f"reserved pipeline_id: {pipeline_id!r}")
        if pipeline_id not in ACTIVE_PIPELINES:
            raise PipelineLoadError(f"pipeline_id is not active: {pipeline_id!r}")
        path = (self.templates_dir / f"{pipeline_id}.yaml").resolve()
        templates_root = self.templates_dir.resolve()
        if templates_root not in path.parents:
            raise PipelineLoadError("pipeline path escapes templates directory")
        if not path.exists():
            raise PipelineLoadError(f"pipeline template not found: {pipeline_id}")
        return self.load_file(path)

    def load_file(self, path: Path) -> PipelineDefinition:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict):
            raise PipelineLoadError(f"pipeline file is not a YAML mapping: {path}")
        schema = _load_schema()
        if schema:
            errors = sorted(Draft7Validator(schema).iter_errors(raw), key=lambda e: list(e.path))
            if errors:
                msg = "; ".join(e.message for e in errors[:3])
                raise PipelineLoadError(f"pipeline schema validation failed in {path.name}: {msg}")
        return self._parse(raw, source_path=path)

    def _parse(self, raw: dict[str, Any], source_path: Path | None = None) -> PipelineDefinition:
        missing = {"pipeline_id", "version", "name", "steps"} - set(raw.keys())
        if missing:
            raise PipelineLoadError(
                f"pipeline missing required fields: {', '.join(sorted(missing))}"
                + (f" in {source_path}" if source_path else "")
            )

        raw_steps = raw["steps"]
        if not isinstance(raw_steps, list) or not raw_steps:
            raise PipelineLoadError("pipeline 'steps' must be a non-empty list")

        steps: list[PipelineStep] = []
        for i, raw_step in enumerate(raw_steps):
            if not isinstance(raw_step, dict):
                raise PipelineLoadError(f"step {i} is not a mapping")
            step_missing = {"step_id", "tool_name", "description"} - set(raw_step.keys())
            if step_missing:
                raise PipelineLoadError(f"step {i} missing fields: {', '.join(sorted(step_missing))}")
            args_template = {
                str(k): _parse_arg_value(val)
                for k, val in raw_step.get("args", {}).items()
            }
            outputs = {str(k): str(v) for k, v in raw_step.get("outputs", {}).items()}
            steps.append(
                PipelineStep(
                    step_id=str(raw_step["step_id"]),
                    tool_name=str(raw_step["tool_name"]),
                    args_template=args_template,
                    description=str(raw_step["description"]),
                    depends_on=tuple(str(d) for d in raw_step.get("depends_on", [])),
                    outputs=outputs,
                    required_outputs=tuple(str(o) for o in raw_step.get("required_outputs", [])),
                    negative_constraints=tuple(str(c) for c in raw_step.get("negative_constraints", [])),
                    depth=int(raw_step.get("depth", 0)),
                )
            )

        return PipelineDefinition(
            pipeline_id=str(raw["pipeline_id"]),
            version=str(raw["version"]),
            name=str(raw["name"]),
            description=str(raw.get("description", "")),
            steps=tuple(steps),
            variables=dict(raw.get("variables", {})),
            max_steps=int(raw.get("max_steps", 20)),
        )
