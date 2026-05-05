from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

class SkillManifestError(ValueError):
    pass

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def validate_skill_manifest(manifest_path: Path, registry_root: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    schema = load_json(registry_root / "manifest.schema.json")

    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))

    if errors:
        messages = [
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        ]
        raise SkillManifestError("; ".join(messages))

    _validate_backend_policy(manifest, manifest_path)
    return manifest

def _validate_backend_policy(manifest: dict[str, Any], manifest_path: Path) -> None:
    for schema_key in ("inputs_schema", "outputs_schema"):
        schema = manifest[schema_key]
        if schema.get("type") != "object":
            raise SkillManifestError(f"{schema_key} must be object schema")
        if schema.get("additionalProperties") is not False:
            raise SkillManifestError(f"{schema_key} must set additionalProperties=false")

    for entrypoint in manifest.get("tool_entrypoints", []):
        if entrypoint["entrypoint_type"] == "instruction_only":
            target = manifest_path.parent / entrypoint["target"]
            if not target.exists():
                raise SkillManifestError(f"missing instruction target: {target}")

    if manifest["risk_tier"] == "T3":
        approvals = manifest["approval_requirements"]
        if approvals.get("requires_user_approval") is not True:
            raise SkillManifestError("T3 skills require user approval")
        if approvals.get("requires_diff_approval") is not True:
            raise SkillManifestError("T3 skills require diff approval")