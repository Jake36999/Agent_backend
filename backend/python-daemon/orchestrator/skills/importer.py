from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .registry import SkillRegistry
from .schema import SkillManifestError, validate_skill_manifest

class SkillImporter:
    def __init__(self, registry_root: Path, registry: SkillRegistry) -> None:
        self.registry_root = Path(registry_root)
        self.registry = registry

    def import_all(self) -> dict[str, Any]:
        skills_dir = self.registry_root / "skills"
        report: dict[str, Any] = {
            "ok": True,
            "verified": [],
            "quarantined": [],
            "registry_root": str(self.registry_root),
        }

        if not skills_dir.exists():
            report["ok"] = False
            report["error"] = f"skills directory not found: {skills_dir}"
            return report

        for manifest_path in sorted(skills_dir.glob("*/skill.json")):
            skill_id = manifest_path.parent.name
            raw = None

            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = validate_skill_manifest(manifest_path, self.registry_root)
                self.registry.upsert_verified(manifest, manifest_path)
                report["verified"].append(manifest["skill_id"])

            except Exception as exc:
                report["ok"] = False
                self.registry.quarantine(skill_id, manifest_path, str(exc), raw)
                report["quarantined"].append({
                    "skill_id": skill_id,
                    "reason": str(exc),
                })

        return report