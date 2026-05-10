from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from orchestrator.active_partition.service import ActivePartitionService
from orchestrator.candidate_analysis.manifest import load_manifest_candidates
from orchestrator.candidate_analysis.service import CandidateAnalysisService
from orchestrator.memory.conversation_summary import ConversationSummaryIngestor
from orchestrator.memory.service import MemoryService
from orchestrator.memory.snapshots import SnapshotMemoryService
from orchestrator.patching.apply import PatchApplyService
from orchestrator.pipeline.compiler import PipelineCompiler
from orchestrator.pipeline.loader import PipelineLoader

from orchestrator.capabilities.policy import check_pipeline_policy

from .bridge_client import TcpBridgeClient
from .compaction import compact_tool_result
from .policies import reasoning_policy
from .state import WorkflowState, default_state_dir, utc_now_iso


class WorkflowRunner:
    def __init__(
        self,
        bridge_client: TcpBridgeClient | None = None,
        tool_client: Any | None = None,
        allow_ingest: bool = False,
        *,
        state_dir: Path | None = None,
        max_steps: int | None = None,
        max_tool_result_chars: int | None = None,
        active_partition: ActivePartitionService | None = None,
        memory_service: MemoryService | None = None,
        snapshot_memory: SnapshotMemoryService | None = None,
        conversation_summary_ingestor: ConversationSummaryIngestor | None = None,
        candidate_analysis: CandidateAnalysisService | None = None,
        patch_apply: PatchApplyService | None = None,
        pipeline_compiler: PipelineCompiler | None = None,
        pipeline_loader: PipelineLoader | None = None,
        capability_registry: Any | None = None,
    ) -> None:
        self.bridge_client = bridge_client
        self.tool_client = tool_client
        self.allow_ingest = allow_ingest
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self.max_steps = int(max_steps or 8)
        self.max_tool_result_chars = int(max_tool_result_chars or 2000)
        self.active_partition = active_partition
        self.memory_service = memory_service
        self.snapshot_memory = snapshot_memory
        self.conversation_summary_ingestor = conversation_summary_ingestor
        self.candidate_analysis = candidate_analysis
        self.patch_apply = patch_apply
        self.pipeline_compiler = pipeline_compiler
        self.pipeline_loader = pipeline_loader
        self.capability_registry = capability_registry

    def run(
        self,
        *,
        objective: str,
        target_repo: str,
        profile: str = "safe",
        allow_ingest: bool | None = None,
        include_report_preview: bool = False,
        use_model_phases: bool = False,
        selected_skill: dict[str, Any] | None = None,
        skill_warnings: list[dict[str, Any]] | None = None,
        skill_registry_db_path: str = "",
        skill_registry_root: str = "",
        verified_skill_count: int = 0,
        selector_candidate_scores: list[dict[str, Any]] | None = None,
        patch_apply_request: dict[str, str] | None = None,
        pipeline_id: str | None = None,
        pipeline_vars: dict[str, str] | None = None,
    ) -> tuple[WorkflowState, dict[str, Any]]:
        state = WorkflowState(
            run_id=str(uuid.uuid4()),
            created_at=utc_now_iso(),
            user_prompt=f"objective={objective}; target_repo={target_repo}; profile={profile}",
            goal=objective,
            reasoning_policy=reasoning_policy(),
            skill_registry_db_path=skill_registry_db_path,
            skill_registry_root=skill_registry_root,
            verified_skill_count=int(verified_skill_count),
            selector_candidate_scores=list(selector_candidate_scores or []),
            selected_skill=selected_skill,
            warnings=list(skill_warnings or []),
        )

        if patch_apply_request is not None:
            return self._run_internal_patch_apply(state, target_repo, patch_apply_request)

        effective_pipeline_id = pipeline_id if pipeline_id is not None else "investigation"

        policy_error = check_pipeline_policy(effective_pipeline_id, self.capability_registry)
        if policy_error is not None:
            state.phase = "FINAL"
            state.final_summary = policy_error
            state.errors.append({"code": "capability_policy_block", "message": policy_error})
            state_path = state.save(self.state_dir)
            return state, self._final_response(state, state_path, ok=False, status="POLICY_BLOCK")

        plan = self._build_plan(objective, target_repo, profile, pipeline_id=pipeline_id, pipeline_vars=pipeline_vars)
        state.artifacts["pipeline_id"] = effective_pipeline_id
        state.artifacts["compiled_step_count"] = len(plan)
        if len(plan) > self.max_steps:
            state.phase = "FINAL"
            state.final_summary = "Workflow blocked: plan exceeds the configured maximum step count."
            state.errors.append(
                {
                    "code": "plan_too_long",
                    "message": state.final_summary,
                }
            )
            state_path = state.save(self.state_dir)
            return state, self._final_response(state, state_path, ok=False, status="POLICY_BLOCK")

        state.todos = [self._clone_todo(todo) for todo in plan]
        state_path = state.save(self.state_dir)
        step_outputs: dict[str, dict[str, Any]] = {}
        executor = self.tool_client or self.bridge_client

        for todo in state.todos:
            state.phase = "ACT"
            todo["status"] = "active"
            state_path = state.save(self.state_dir)
            try:
                if executor is None:
                    executor = TcpBridgeClient()
                resolved_args, binding_failures = self._resolve_args(
                    todo["args"], step_outputs, step_id=todo["id"]
                )
                if binding_failures:
                    msg = "; ".join(binding_failures)
                    raw_result = {
                        "ok": False,
                        "status": "POLICY_BLOCK",
                        "summary": msg,
                        "artifacts": {},
                        "error": {"code": "binding_resolution_failed", "message": msg},
                    }
                else:
                    raw_result = executor.call_tool(todo["tool_name"], resolved_args)
            except Exception as exc:
                raw_result = {
                    "ok": False,
                    "status": "ERROR",
                    "summary": f"workflow tool execution failed: {exc}",
                    "artifacts": {},
                    "error": {"code": "tool_execution_failed", "message": str(exc)[:2000]},
                }
            compact = compact_tool_result(
                todo["tool_name"],
                raw_result,
                max_chars=self.max_tool_result_chars,
                include_content=include_report_preview and todo["tool_name"] == "mcp_investigation_read_report",
            )
            step_outputs[todo["id"]] = {
                "ok": compact.get("ok"),
                "status": compact.get("status"),
                "summary": compact.get("summary"),
                "artifacts": compact.get("artifacts", {}),
                "error": compact.get("error"),
            }
            state.tool_results.append(compact)
            self._merge_artifacts(state.artifacts, compact.get("artifacts", {}))

            state.phase = "SUMMARISE_TOOL_RESULT"
            todo["status"] = "done" if compact["ok"] else "blocked"
            state_path = state.save(self.state_dir)

            state.phase = "CHECK"
            state_path = state.save(self.state_dir)

            if not compact["ok"]:
                state.errors.append(
                    {
                        "code": compact.get("error", {}).get("code", "tool_failed")
                        if isinstance(compact.get("error"), dict)
                        else "tool_failed",
                        "message": compact.get("summary", "Tool execution failed."),
                    }
                )
                state.phase = "FINAL"
                state.final_summary = compact.get("summary", "Workflow blocked.")
                state_path = state.save(self.state_dir)
                return state, self._final_response(state, state_path, ok=False, status=str(compact.get("status", "ERROR")))

            if todo["tool_name"] == "mcp_investigation_compile_handoff":
                state.phase = "SYNTHESIZE"
                state.final_summary = self._success_summary(state)
                self._attach_round_one_artifacts(state, target_repo)
                self._record_binding_trace(state, step_outputs)
                self._attach_pipeline_receipt(state, plan, step_outputs)
                if state.artifacts.get("pipeline_id") == "code_review":
                    self._attach_code_review_summary(state, step_outputs, target_repo)
                state_path = state.save(self.state_dir)
                state.phase = "FINAL"
                state_path = state.save(self.state_dir)
                return state, self._final_response(state, state_path, ok=True, status="COMPLETE")

        state.phase = "SYNTHESIZE"
        state.final_summary = self._success_summary(state)
        self._attach_round_one_artifacts(state, target_repo)
        self._record_binding_trace(state, step_outputs)
        self._attach_pipeline_receipt(state, plan, step_outputs)
        if state.artifacts.get("pipeline_id") == "code_review":
            self._attach_code_review_summary(state, step_outputs, target_repo)
        state_path = state.save(self.state_dir)
        state.phase = "FINAL"
        state_path = state.save(self.state_dir)
        return state, self._final_response(state, state_path, ok=True, status="COMPLETE")

    def _run_internal_patch_apply(self, state: WorkflowState, target_repo: str, patch_apply_request: dict[str, str]) -> tuple[WorkflowState, dict[str, Any]]:
        state.phase = "PATCH_APPLY"
        if self.patch_apply is None:
            state.errors.append({"code": "patch_apply_unavailable", "message": "Patch apply service is not configured."})
            state.final_summary = "Patch apply service is not configured."
            state_path = state.save(self.state_dir)
            return state, self._final_response(state, state_path, ok=False, status="ERROR")
        patch_id = str(patch_apply_request.get("patch_id") or "")
        approval_id = str(patch_apply_request.get("approval_id") or "")
        if not patch_id or not approval_id:
            state.errors.append({"code": "missing_patch_apply_request", "message": "patch_id and approval_id are required."})
            state.final_summary = "Patch apply request requires patch_id and approval_id."
            state_path = state.save(self.state_dir)
            return state, self._final_response(state, state_path, ok=False, status="POLICY_BLOCK")
        result = self.patch_apply.apply_approved_patch(patch_id=patch_id, approval_id=approval_id, target_repo=target_repo)
        compact = {
            "apply_run_id": result.get("apply_run_id"),
            "rollback_available": bool(result.get("rollback_available", False)),
            "tests_status": result.get("tests_status"),
            "patch_apply_status": result.get("status"),
        }
        state.artifacts["patch_apply"] = compact
        state.final_summary = "Approved patch apply completed." if result.get("ok") else "Approved patch apply did not complete."
        state.phase = "FINAL"
        state_path = state.save(self.state_dir)
        return state, self._final_response(state, state_path, ok=bool(result.get("ok")), status=str(result.get("status", "ERROR")))

    def _build_plan(
        self,
        objective: str,
        target_repo: str,
        profile: str,
        pipeline_id: str | None = None,
        pipeline_vars: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        effective_id = pipeline_id if pipeline_id is not None else "investigation"
        if self.pipeline_compiler is not None and self.pipeline_loader is not None:
            definition = self.pipeline_loader.load(effective_id)
            runtime_vars = {
                "objective": objective,
                "target_repo": target_repo,
                "profile": profile,
                "max_chars": str(self.max_tool_result_chars),
                **(pipeline_vars or {}),
            }
            return self.pipeline_compiler.compile_to_plan_list(definition, runtime_vars)

        raise RuntimeError("pipeline_compiler and pipeline_loader are required")

    def _clone_todo(self, todo: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": todo["id"],
            "status": todo["status"],
            "description": todo["description"],
            "tool_name": todo["tool_name"],
            "args": dict(todo["args"]),
            "outputs": dict(todo.get("outputs", {})),
        }

    @staticmethod
    def _is_binding(v: Any) -> bool:
        return isinstance(v, dict) and v.get("__binding__") is True

    def _resolve_binding(
        self,
        binding: dict[str, Any],
        step_outputs: dict[str, dict[str, Any]],
    ) -> tuple[bool, Any]:
        """Returns (resolved, value). resolved=False if the bound artifact is missing."""
        from_step = str(binding["from_step"])
        path = str(binding["path"])
        step_result = step_outputs.get(from_step)
        if step_result is None:
            return False, None
        # Shallow two-segment path only, e.g. "artifacts.session_path"
        prefix, _, key = path.partition(".")
        cursor: Any = step_result.get(prefix) if isinstance(step_result, dict) else None
        if isinstance(cursor, dict):
            cursor = cursor.get(key)
        else:
            cursor = None
        return (cursor is not None), cursor

    def _resolve_args(
        self,
        args: dict[str, Any],
        step_outputs: dict[str, dict[str, Any]] | None = None,
        *,
        step_id: str = "",
    ) -> tuple[dict[str, Any], list[str]]:
        """Returns (resolved_args, binding_failures). Non-empty failures → policy block."""
        resolved: dict[str, Any] = {}
        failures: list[str] = []
        for key, value in args.items():
            if self._is_binding(value):
                ok, result = self._resolve_binding(value, step_outputs or {})
                if not ok:
                    failures.append(
                        f"step '{step_id}' requires {value['path']} from {value['from_step']}"
                    )
                    resolved[key] = None
                else:
                    resolved[key] = result
            else:
                resolved[key] = value
        return resolved, failures

    def _record_binding_trace(
        self,
        state: WorkflowState,
        step_outputs: dict[str, dict[str, Any]],
    ) -> None:
        if step_outputs:
            state.artifacts["binding_trace"] = {
                step_id: list(result.get("artifacts", {}).keys())
                for step_id, result in step_outputs.items()
            }

    def _attach_code_review_summary(
        self,
        state: WorkflowState,
        step_outputs: dict[str, dict[str, Any]],
        target_repo: str,
    ) -> None:
        import json
        from orchestrator.code_review.artifact_writer import build_report_index, persist_code_review_artifacts
        from orchestrator.code_review.report_builder import build_code_review_report
        pipeline_receipt = state.artifacts.get("pipeline_receipt")
        report = build_code_review_report(
            target_repo=target_repo,
            step_outputs=step_outputs,
            pipeline_receipt=pipeline_receipt if isinstance(pipeline_receipt, dict) else None,
        )
        refs, manifest_entries = persist_code_review_artifacts(report, state.run_id, self.state_dir)
        for key, path in refs.items():
            state.artifacts[key] = path

        state.artifacts["code_review_report_index"] = json.dumps(
            build_report_index(manifest_entries),
        )[:2000]

    def _attach_pipeline_receipt(
        self,
        state: WorkflowState,
        plan: list[dict[str, Any]],
        step_outputs: dict[str, dict[str, Any]],
    ) -> None:
        pipeline_id = state.artifacts.get("pipeline_id")
        if not pipeline_id:
            return
        from orchestrator.capabilities.receipt import build_receipt, compact_receipt
        artifact_refs = [
            key
            for result in step_outputs.values()
            for key in result.get("artifacts", {}).keys()
        ][:20]
        completed = sum(1 for r in step_outputs.values() if r.get("ok"))
        receipt = build_receipt(
            capability_id=f"pipeline.{pipeline_id}",
            capability_type="pipeline",
            risk_tier="T2",
            status="OK",
            authorized=True,
            network_access=False,
            writes_external_state=True,
            artifact_refs=artifact_refs,
            summary=f"Executed {pipeline_id} pipeline ({len(plan)} steps, {completed} complete).",
        )
        state.artifacts["pipeline_receipt"] = compact_receipt(receipt)

    def _merge_artifacts(self, merged: dict[str, str], artifacts: dict[str, Any]) -> None:
        for key, value in artifacts.items():
            if isinstance(key, str) and value is not None:
                merged.setdefault(key, str(value))

    def _success_summary(self, state: WorkflowState) -> str:
        return "Workflow complete. Generated session, manifest, validation, handoff, and archive artifacts."

    def _attach_round_one_artifacts(self, state: WorkflowState, target_repo: str) -> None:
        active = self.active_partition.get_active_partition() if self.active_partition is not None else None
        if (
            self.candidate_analysis is not None
            and isinstance(state.selected_skill, dict)
            and self._should_run_candidate_analysis(state.selected_skill)
        ):
            manifest_result = self._load_candidate_manifest(state, target_repo)
            if not manifest_result["ok"]:
                state.artifacts["candidate_analysis"] = {
                    "ok": False,
                    "status": "WARN",
                    "summary": "Candidate analysis could not rank target repository files.",
                    "ranked_candidates": [],
                    "warnings": manifest_result["warnings"],
                    "missing_context": [{"item": "manifest_csv", "reason": manifest_result["reason"]}],
                    "ranking_policy_applied": self.candidate_analysis.ranking_policy,
                    "next_action": "Provide a readable manifest_csv containing target_repo source files.",
                }
            else:
                state.artifacts["candidate_analysis"] = self.candidate_analysis.analyze(
                    {
                        "objective": state.goal,
                        "target_repo": target_repo,
                        "logs": self._tool_result_context(state),
                        "manifest_candidates": manifest_result["candidates"],
                        "workspace_summary": "",
                        "rag_context": "",
                        "max_candidates": 10,
                    }
                )

        if self.snapshot_memory is not None:
            snapshot_result = self.snapshot_memory.record_workflow_snapshot(
                workflow_result={
                    "run_id": state.run_id,
                    "summary": state.final_summary or self._success_summary(state),
                    "artifacts": state.artifacts,
                    "state_path": "",
                },
                active_partition=active,
                selected_skill=state.selected_skill,
            )
            if snapshot_result.get("snapshot_id"):
                state.artifacts["snapshot_id"] = snapshot_result["snapshot_id"]

        if self.conversation_summary_ingestor is not None and self.memory_service is not None and active is not None:
            source_artifacts = [
                {"artifact": key, "path": value, "verified": True}
                for key, value in state.artifacts.items()
                if isinstance(key, str) and (key.endswith("_path") or key in {"final_markdown", "archive_yaml", "manifest_csv"})
            ]
            candidate = self.conversation_summary_ingestor.build_memory_candidate(
                conversation_events=[
                    {
                        "type": "completed_artifact",
                        "summary": state.final_summary or self._success_summary(state),
                    }
                ],
                target_repo=target_repo,
                project_id=active.active_project_id,
                source_artifacts=source_artifacts,
                write_intent="workflow snapshot summary",
                selected_skill=state.selected_skill,
            )
            if candidate.get("write_allowed"):
                memory_result = self.conversation_summary_ingestor.commit_if_allowed(
                    candidate_result=candidate,
                    memory_service=self.memory_service,
                )
                if memory_result.get("ok"):
                    state.artifacts["summary_memory_result"] = {
                        key: memory_result.get(key)
                        for key in ("ok", "status", "memory_id", "index_status", "project_id", "project_scope_hash")
                        if key in memory_result
                    }

    def _should_run_candidate_analysis(self, selected_skill: dict[str, Any]) -> bool:
        return selected_skill.get("skill_id") == "candidate_analysis_v1" or "candidate_analysis" in set(selected_skill.get("capabilities") or [])

    def _load_candidate_manifest(self, state: WorkflowState, target_repo: str) -> dict[str, Any]:
        manifest_path = state.artifacts.get("manifest_csv")
        if not isinstance(manifest_path, str) or not manifest_path.strip():
            return {
                "ok": False,
                "reason": "manifest_csv artifact path missing",
                "warnings": [{"artifact_key": "manifest_csv", "message": "manifest_csv artifact path missing"}],
            }
        result = load_manifest_candidates(manifest_path, target_repo)
        if not result.ok:
            return {
                "ok": False,
                "reason": result.error or (result.warnings[0]["message"] if result.warnings else "manifest_csv yielded no candidates"),
                "warnings": result.warnings,
            }
        return {"ok": True, "candidates": result.candidates, "warnings": result.warnings}

    def _tool_result_context(self, state: WorkflowState) -> str:
        return "\n".join(str(item.get("summary") or "") for item in state.tool_results if isinstance(item, dict))

    def _artifact_context(self, state: WorkflowState) -> str:
        return "\n".join(f"{key},{value}" for key, value in state.artifacts.items() if isinstance(value, str))

    def _final_response(self, state: WorkflowState, state_path: Path, *, ok: bool, status: str) -> dict[str, Any]:
        artifacts = dict(state.artifacts)
        artifacts["selected_skill"] = state.selected_skill
        return {
            "ok": ok,
            "status": status,
            "run_id": state.run_id,
            "summary": state.final_summary or self._success_summary(state),
            "artifacts": artifacts,
            "state_path": str(state_path),
            "error": None if ok else (state.errors[-1] if state.errors else {"code": "workflow_failed", "message": "Workflow failed."}),
        }
