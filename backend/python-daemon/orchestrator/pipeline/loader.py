from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import PipelineDefinition, PipelineStep


class PipelineLoadError(ValueError):
    pass


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
            if not p.name.startswith("_")
        )

    def load(self, pipeline_id: str) -> PipelineDefinition:
        path = self.templates_dir / f"{pipeline_id}.yaml"
        if not path.exists():
            raise PipelineLoadError(f"pipeline template not found: {pipeline_id}")
        return self.load_file(path)

    def load_file(self, path: Path) -> PipelineDefinition:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict):
            raise PipelineLoadError(f"pipeline file is not a YAML mapping: {path}")
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
            steps.append(
                PipelineStep(
                    step_id=str(raw_step["step_id"]),
                    tool_name=str(raw_step["tool_name"]),
                    args_template=dict(raw_step.get("args", {})),
                    description=str(raw_step["description"]),
                    depends_on=tuple(str(d) for d in raw_step.get("depends_on", [])),
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
