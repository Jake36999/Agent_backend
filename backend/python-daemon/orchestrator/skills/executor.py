from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

class SkillPolicyError(ValueError):
    pass

def enforce_manifest_policy(manifest: dict[str, Any]) -> None:
    for tool_name in manifest.get("allowed_tools", []):
        if tool_name not in ALLOWED_TOOLS:
            raise SkillPolicyError(f"skill allows unknown tool: {tool_name}")

    risk_tier = manifest["risk_tier"]
    approvals = manifest["approval_requirements"]

    if risk_tier == "T3":
        if approvals.get("requires_user_approval") is not True:
            raise SkillPolicyError("T3 skill requires user approval")
        if approvals.get("requires_diff_approval") is not True:
            raise SkillPolicyError("T3 skill requires diff approval")

def load_skill_instructions(manifest: dict[str, Any]) -> str:
    source_path = Path(manifest["source_path"])
    skill_dir = source_path.parent

    for entrypoint in manifest.get("tool_entrypoints", []):
        if entrypoint["entrypoint_type"] == "instruction_only":
            target = skill_dir / entrypoint["target"]
            return target.read_text(encoding="utf-8")

    raise SkillPolicyError("no instruction_only entrypoint found")

def build_skill_context(manifest: dict[str, Any], *, include_instructions: bool = True) -> dict[str, Any]:
    enforce_manifest_policy(manifest)

    context = {
        "skill_id": manifest["skill_id"],
        "risk_tier": manifest["risk_tier"],
        "allowed_tools": manifest.get("allowed_tools", []),
        "approval_requirements": manifest["approval_requirements"],
        "artifacts_produced": manifest.get("artifacts_produced", []),
    }

    if include_instructions:
        context["instructions"] = load_skill_instructions(manifest)

    return context