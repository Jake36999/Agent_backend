from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .bridge_client import TcpBridgeClient
from .runner import WorkflowRunner
from .state import default_state_dir
from orchestrator.active_partition.service import ActivePartitionService
from orchestrator.pipeline.compiler import PipelineCompiler
from orchestrator.pipeline.loader import PipelineLoader
from orchestrator.candidate_analysis.service import CandidateAnalysisService
from orchestrator.memory.conversation_summary import ConversationSummaryIngestor
from orchestrator.memory.service import MemoryService
from orchestrator.memory.snapshots import SnapshotMemoryService
from orchestrator.patching.apply import PatchApplyService
from orchestrator.skills.importer import SkillImporter
from orchestrator.skills.registry import SkillRegistry
from orchestrator.skills.selection import select_skill


def _allowed_roots_from_env() -> tuple[Path, ...]:
    raw = os.getenv("ALETHEIA_ALLOWED_ROOTS", "").strip()
    if not raw:
        return tuple()
    roots = [Path(part).expanduser().resolve() for part in raw.split(";") if part.strip()]
    return tuple(roots)


def _default_skill_registry_root() -> Path | None:
    candidate = (Path(__file__).resolve().parents[3] / "agent_backend_skill_registry").resolve()
    return candidate if candidate.exists() else None


def _invalid_target_repo(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "POLICY_BLOCK",
        "summary": "target_repo must be an existing absolute path under an allowed root.",
        "run_id": "",
        "artifacts": {},
        "state_path": "",
        "error": {"code": "invalid_target_repo", "message": message},
    }


def validate_target_repo(target_repo: str, allowed_roots: tuple[Path, ...] | None = None) -> tuple[bool, str, Path | None]:
    path = Path(target_repo).expanduser()
    if not path.is_absolute():
        return False, f"target_repo must be absolute: {target_repo}", None
    resolved = path.resolve()
    if not resolved.exists():
        return False, f"target_repo does not exist: {resolved}", None
    roots = tuple(root.resolve() for root in (allowed_roots if allowed_roots is not None else _allowed_roots_from_env()))
    if roots and not any(resolved == root or root in resolved.parents for root in roots):
        return False, f"target_repo must be under an allowed root: {resolved}", None
    return True, "", resolved


def _compact_selected_skill(manifests: list[dict[str, Any]], selection: dict[str, Any] | None) -> dict[str, Any] | None:
    if not selection:
        return None

    selected_skill_id = selection.get("selected_skill_id")
    manifest = next((item for item in manifests if item.get("skill_id") == selected_skill_id), None)
    evidence = next(
        (item for item in selection.get("candidate_analysis", []) if item.get("skill_id") == selected_skill_id),
        None,
    )
    if manifest is None:
        return None

    compact: dict[str, Any] = {
        "skill_id": selected_skill_id,
        "risk_tier": manifest.get("risk_tier"),
        "capabilities": list(manifest.get("capabilities") or []),
        "source": "skill_registry",
        "instruction_loaded": False,
    }
    if evidence:
        compact["evidence"] = {
            key: evidence.get(key)
            for key in ("score", "trigger_hits", "capability_hits", "intent_hits")
            if key in evidence
        }
    return compact


def _compact_candidate_scores(selection: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not selection:
        return []
    candidates: list[dict[str, Any]] = []
    for candidate in selection.get("candidate_analysis", []) or []:
        if not isinstance(candidate, dict):
            continue
        candidates.append(
            {
                "skill_id": candidate.get("skill_id"),
                "score": candidate.get("score"),
                "risk_tier": candidate.get("risk_tier"),
                "trigger_hits": list(candidate.get("trigger_hits") or []),
                "capability_hits": list(candidate.get("capability_hits") or []),
            }
        )
    return candidates


def _load_selected_skill_metadata(
    objective: str,
    *,
    queue_db_path: Path | None = None,
    skill_registry_root: Path | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str, str, int, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    resolved_queue_db_path = Path(queue_db_path).expanduser().resolve() if queue_db_path is not None else (default_state_dir() / "queue.db")
    resolved_registry_root = Path(skill_registry_root).expanduser().resolve() if skill_registry_root is not None else _default_skill_registry_root()

    try:
        registry = SkillRegistry(resolved_queue_db_path)
        manifests = registry.list_verified()
        import_report: dict[str, Any] | None = None
        if not manifests and resolved_registry_root is not None:
            importer = SkillImporter(Path(resolved_registry_root), registry)
            import_report = importer.import_all()
            manifests = registry.list_verified()
        if not manifests:
            warnings.append(
                {
                    "code": "skill_registry_empty",
                    "source": "skill_registry",
                    "db_path": str(resolved_queue_db_path),
                    "registry_root": str(resolved_registry_root) if resolved_registry_root is not None else None,
                    "verified_skill_count": 0,
                    "message": "No verified skill manifests were available.",
                    **(
                        {
                            "import_report": {
                                "ok": bool(import_report.get("ok")),
                                "verified_count": len(import_report.get("verified") or []),
                                "quarantined_count": len(import_report.get("quarantined") or []),
                            }
                        }
                        if import_report is not None
                        else {}
                    ),
                }
            )
            return None, warnings, str(resolved_queue_db_path), str(resolved_registry_root) if resolved_registry_root is not None else "", 0, []

        selection = select_skill(objective, manifests)
        selected_skill = _compact_selected_skill(manifests, selection)
        return (
            selected_skill,
            warnings,
            str(resolved_queue_db_path),
            str(resolved_registry_root) if resolved_registry_root is not None else "",
            len(manifests),
            _compact_candidate_scores(selection),
        )
    except Exception as exc:
        message = str(exc)
        if "no such table: skill_manifests" in message:
            warnings.append(
                {
                    "code": "skill_registry_unavailable",
                    "source": "skill_registry",
                    "db_path": str(resolved_queue_db_path),
                    "registry_root": str(resolved_registry_root) if resolved_registry_root is not None else None,
                    "expected_table": "skill_manifests",
                    "migration": "0004_skill_manifests",
                    "verified_skill_count": 0,
                    "message": message[:200],
                }
            )
        else:
            warnings.append(
                {
                    "code": "skill_registry_unavailable",
                    "source": "skill_registry",
                    "db_path": str(resolved_queue_db_path),
                    "registry_root": str(resolved_registry_root) if resolved_registry_root is not None else None,
                    "expected_table": "skill_manifests",
                    "migration": "0004_skill_manifests",
                    "verified_skill_count": 0,
                    "message": message[:200],
                }
            )
        return None, warnings, str(resolved_queue_db_path), str(resolved_registry_root) if resolved_registry_root is not None else "", 0, []


def run_agent_workflow(
    *,
    objective: str,
    target_repo: str,
    profile: str = "safe",
    allow_ingest: bool = False,
    include_report_preview: bool = False,
    use_model_phases: bool = False,
    bridge_client: TcpBridgeClient | None = None,
    tool_client: Any | None = None,
    state_dir: Path | None = None,
    allowed_roots: tuple[Path, ...] | None = None,
    skill_registry_root: Path | None = None,
    queue_db_path: Path | None = None,
    max_steps: int | None = None,
    max_tool_result_chars: int | None = None,
    active_partition: ActivePartitionService | None = None,
    memory_service: MemoryService | None = None,
    snapshot_memory: SnapshotMemoryService | None = None,
    conversation_summary_ingestor: ConversationSummaryIngestor | None = None,
    candidate_analysis: CandidateAnalysisService | None = None,
    patch_apply: PatchApplyService | None = None,
    patch_apply_request: dict[str, str] | None = None,
    pipeline_id: str | None = None,
    pipeline_vars: dict[str, str] | None = None,
    pipeline_compiler: PipelineCompiler | None = None,
    pipeline_loader: PipelineLoader | None = None,
) -> dict[str, Any]:
    if profile != "safe":
        return {
            "ok": False,
            "status": "POLICY_BLOCK",
            "summary": "profile must be safe for this workflow.",
            "run_id": "",
            "artifacts": {},
            "state_path": "",
            "error": {"code": "unsupported_profile", "message": "profile must be safe"},
        }

    valid, message, resolved = validate_target_repo(target_repo, allowed_roots)
    if not valid or resolved is None:
        return _invalid_target_repo(message)

    selected_skill, skill_warnings, resolved_queue_db_path, resolved_registry_root, verified_skill_count, selector_candidate_scores = _load_selected_skill_metadata(
        objective,
        queue_db_path=queue_db_path,
        skill_registry_root=skill_registry_root,
    )

    runner = WorkflowRunner(
        bridge_client=bridge_client,
        tool_client=tool_client,
        allow_ingest=allow_ingest,
        state_dir=state_dir,
        max_steps=max_steps,
        max_tool_result_chars=max_tool_result_chars,
        active_partition=active_partition,
        memory_service=memory_service,
        snapshot_memory=snapshot_memory,
        conversation_summary_ingestor=conversation_summary_ingestor,
        candidate_analysis=candidate_analysis,
        patch_apply=patch_apply,
        pipeline_compiler=pipeline_compiler or PipelineCompiler(),
        pipeline_loader=pipeline_loader or PipelineLoader(),
    )
    try:
        _, response = runner.run(
            objective=objective,
            target_repo=str(resolved),
            profile=profile,
            allow_ingest=allow_ingest,
            include_report_preview=include_report_preview,
            use_model_phases=use_model_phases,
            selected_skill=selected_skill,
            skill_warnings=skill_warnings,
            skill_registry_db_path=resolved_queue_db_path,
            skill_registry_root=resolved_registry_root,
            verified_skill_count=verified_skill_count,
            selector_candidate_scores=selector_candidate_scores,
            patch_apply_request=patch_apply_request,
            pipeline_id=pipeline_id,
            pipeline_vars=pipeline_vars,
        )
        return response
    except Exception as exc:
        return {
            "ok": False,
            "status": "ERROR",
            "summary": "Workflow execution failed.",
            "run_id": "",
            "artifacts": {},
            "state_path": "",
            "error": {"code": "workflow_runner_failed", "message": str(exc)[:2000]},
        }
