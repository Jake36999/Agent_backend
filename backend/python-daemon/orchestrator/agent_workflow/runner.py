from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .bridge_client import TcpBridgeClient
from .compaction import compact_tool_result
from .policies import reasoning_policy
from .state import WorkflowState, default_state_dir, utc_now_iso


class WorkflowRunner:
    def __init__(
        self,
        lm_client: Any | None = None,
        bridge_client: TcpBridgeClient | None = None,
        tool_client: Any | None = None,
        allow_ingest: bool = False,
        *,
        state_dir: Path | None = None,
        max_steps: int | None = None,
        max_tool_result_chars: int | None = None,
    ) -> None:
        self.lm_client = lm_client
        self.bridge_client = bridge_client
        self.tool_client = tool_client
        self.allow_ingest = allow_ingest
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self.max_steps = int(max_steps or 8)
        self.max_tool_result_chars = int(max_tool_result_chars or 2000)

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

        plan = self._build_plan(objective, target_repo, profile)
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
        session_path = ""
        executor = self.tool_client or self.bridge_client

        for todo in state.todos:
            state.phase = "ACT"
            todo["status"] = "active"
            state_path = state.save(self.state_dir)
            try:
                if executor is None:
                    executor = TcpBridgeClient()
                raw_result = executor.call_tool(todo["tool_name"], self._resolve_args(todo["args"], session_path))
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

            if todo["tool_name"] == "mcp_investigation_start":
                session_path = str(state.artifacts.get("session_path") or session_path)

            if todo["tool_name"] == "mcp_investigation_compile_handoff":
                state.phase = "SYNTHESIZE"
                state.final_summary = self._success_summary(state)
                state_path = state.save(self.state_dir)
                state.phase = "FINAL"
                state_path = state.save(self.state_dir)
                return state, self._final_response(state, state_path, ok=True, status="COMPLETE")

        state.phase = "SYNTHESIZE"
        state.final_summary = self._success_summary(state)
        state_path = state.save(self.state_dir)
        state.phase = "FINAL"
        state_path = state.save(self.state_dir)
        return state, self._final_response(state, state_path, ok=True, status="COMPLETE")

    def _build_plan(self, objective: str, target_repo: str, profile: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "start_investigation",
                "status": "pending",
                "description": "Create a Tool Assist session",
                "tool_name": "mcp_investigation_start",
                "args": {
                    "objective": objective,
                    "target_repo": target_repo,
                    "profile": profile,
                },
            },
            {
                "id": "filemap",
                "status": "pending",
                "description": "Build the file map for the investigation session",
                "tool_name": "mcp_investigation_filemap",
                "args": {
                    "session_path": "${session_path}",
                    "profile": profile,
                },
            },
            {
                "id": "validate_manifest",
                "status": "pending",
                "description": "Validate the manifest output",
                "tool_name": "mcp_investigation_validate_manifest",
                "args": {
                    "session_path": "${session_path}",
                },
            },
            {
                "id": "read_report",
                "status": "pending",
                "description": "Read a bounded report preview",
                "tool_name": "mcp_investigation_read_report",
                "args": {
                    "session_path": "${session_path}",
                    "artifact_key": "manifest_doctor_md",
                    "max_chars": self.max_tool_result_chars,
                },
            },
            {
                "id": "compile_handoff",
                "status": "pending",
                "description": "Compile the final handoff artifacts",
                "tool_name": "mcp_investigation_compile_handoff",
                "args": {
                    "session_path": "${session_path}",
                },
            },
        ]

    def _clone_todo(self, todo: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": todo["id"],
            "status": todo["status"],
            "description": todo["description"],
            "tool_name": todo["tool_name"],
            "args": dict(todo["args"]),
        }

    def _resolve_args(self, args: dict[str, Any], session_path: str) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in args.items():
            if value == "${session_path}":
                resolved[key] = session_path
            else:
                resolved[key] = value
        return resolved

    def _merge_artifacts(self, merged: dict[str, str], artifacts: dict[str, Any]) -> None:
        for key, value in artifacts.items():
            if isinstance(key, str) and value is not None:
                merged.setdefault(key, str(value))

    def _success_summary(self, state: WorkflowState) -> str:
        return "Workflow complete. Generated session, manifest, validation, handoff, and archive artifacts."

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
