from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .models import CapabilityManifest, CapabilityType
from .registry import CapabilityRegistry

if TYPE_CHECKING:
    from ..pipeline.compiler import PipelineCompiler
    from ..pipeline.loader import PipelineLoader

log = logging.getLogger(__name__)

_STARTUP_VARS: dict[str, str] = {
    "objective": "startup validation",
    "target_repo": "/__startup_validation__",
    "profile": "safe",
    "session_path": "/__session__",
    "max_chars": "2000",
}


class CapabilityLoader:

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def import_pipeline_templates(
        self,
        templates_dir: Path,
        loader: "PipelineLoader | None" = None,
        compiler: "PipelineCompiler | None" = None,
    ) -> dict[str, Any]:
        if not templates_dir.is_dir():
            return {"imported": 0, "quarantined": 0, "errors": []}

        imported = quarantined = 0
        errors: list[str] = []

        if loader is not None:
            template_ids = loader.list_templates()
        else:
            template_ids = [
                p.stem for p in sorted(templates_dir.glob("*.yaml"))
                if not p.name.startswith("_")
            ]

        for pipeline_id in template_ids:
            yaml_path = templates_dir / f"{pipeline_id}.yaml"
            if not yaml_path.exists():
                continue

            raw: dict[str, Any] = {}
            status = "verified"
            validation_error: str | None = None

            try:
                with open(yaml_path, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    raise ValueError("not a YAML mapping")
                raw = data

                if loader is not None and compiler is not None:
                    definition = loader.load(pipeline_id)
                    compiler.compile_to_plan_list(definition, runtime_vars=_STARTUP_VARS)

            except Exception as exc:
                status = "quarantined"
                validation_error = str(exc)
                quarantined += 1
                errors.append(f"{pipeline_id}: {validation_error}")
                log.warning("pipeline template %s failed startup validation: %s", pipeline_id, validation_error)
            else:
                imported += 1

            metadata: dict[str, Any] = {
                "pipeline_id": raw.get("pipeline_id", pipeline_id),
                "executable": status == "verified",
            }
            if validation_error:
                metadata["validation_error"] = validation_error[:500]

            cap = CapabilityManifest(
                capability_id=f"pipeline.{pipeline_id}",
                capability_type=CapabilityType.PIPELINE_TEMPLATE,
                version=str(raw.get("version", "0.0.0")),
                name=str(raw.get("name", pipeline_id)),
                description=str(raw.get("description", "")),
                risk_tier="T1",
                source_path=None,
                metadata=metadata,
                status=status,
            )
            self.registry.upsert(cap)

        return {"imported": imported, "quarantined": quarantined, "errors": errors}

    def register_adapter(
        self,
        capability_id: str,
        name: str,
        description: str,
        version: str = "1.0.0",
        risk_tier: str = "T1",
        requires_approval: bool = False,
        network_access: bool = False,
        writes_external_state: bool = False,
        source_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        cap = CapabilityManifest(
            capability_id=capability_id,
            capability_type=CapabilityType.ADAPTER,
            version=version,
            name=name,
            description=description,
            risk_tier=risk_tier,
            requires_approval=requires_approval,
            network_access=network_access,
            writes_external_state=writes_external_state,
            source_path=source_path,
            metadata=metadata or {},
        )
        self.registry.upsert(cap)
