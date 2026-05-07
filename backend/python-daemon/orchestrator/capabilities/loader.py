from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .models import CapabilityManifest, CapabilityType
from .registry import CapabilityRegistry

log = logging.getLogger(__name__)


class CapabilityLoader:

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def import_pipeline_templates(self, templates_dir: Path) -> dict[str, Any]:
        imported = 0
        if not templates_dir.is_dir():
            return {"imported": 0}
        for yaml_path in sorted(templates_dir.glob("*.yaml")):
            if yaml_path.name.startswith("_"):
                continue
            try:
                with open(yaml_path, encoding="utf-8") as fh:
                    raw = yaml.safe_load(fh)
                if not isinstance(raw, dict):
                    continue
                cap = CapabilityManifest(
                    capability_id=f"pipeline.{raw.get('pipeline_id', yaml_path.stem)}",
                    capability_type=CapabilityType.PIPELINE_TEMPLATE,
                    version=str(raw.get("version", "0.0.0")),
                    name=str(raw.get("name", yaml_path.stem)),
                    description=str(raw.get("description", "")),
                    risk_tier="T1",
                    source_path=str(yaml_path),
                    metadata={"pipeline_id": raw.get("pipeline_id", yaml_path.stem)},
                )
                self.registry.upsert(cap)
                imported += 1
            except Exception as exc:
                log.warning("failed to import pipeline template %s: %s", yaml_path.name, exc)
        return {"imported": imported}

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
