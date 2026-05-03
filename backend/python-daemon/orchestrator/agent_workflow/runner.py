from __future__ import annotations

import json
import os
import re
from typing import Any

from .bridge_client import TcpBridgeClient
from .compaction import compact_tool_result
from .lmstudio_client import LMStudioClient, ModelOutputInvalid
from .policies import ALLOWED_TOOLS, validate_tool, reasoning_policy
from .state import WorkflowState


PLAN_SCHEMA = {
    "name": "agent_workflow_plan",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "goal": {"type": "string"},
            "stop_condition": {"type": "string"},
            "notes": {"type": "string"},
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "id": {"type": "string"},
                        "description": {"type": "string"},
                        "tool_name": {"type": "string"},
                        "args": {"type": "object"},
                    },
                    "required": ["id", "description", "tool_name", "args"],
                },
            },
        },
        "required": ["goal", "stop_condition", "notes", "todos"],
    },
}


class WorkflowRunner:
    def __init__(
        self,
        lm_client: LMStudioClient | None = None,
        bridge_client: TcpBridgeClient | None = None,
        allow_ingest: bool = False,
    ) -> None:
        self.lm_client = lm_client or LMStudioClient()
        self.bridge_client = bridge_client or TcpBridgeClient()
        self.allow_ingest = allow_ingest
        self.max_steps = int(os.getenv("ALETHEIA_AGENT_MAX_STEPS", "8"))
        self.max_tool_result_chars = int(os.getenv("ALETHEIA_AGENT_MAX_TOOL_RESULT_CHARS", "2000"))

    def run(
        self,
        user_prompt: str,
        *,
        objective: str | None = None,
        target_repo: str | None = None,
        profile: str = "safe",
    ) -> tuple[WorkflowState, str]:
        state = WorkflowState.create(user_prompt)
        policy = reasoning_policy()
        state.reasoning_policy = {**policy, "fallbacks": {}}
        state.phase = "PLAN"
        state.save()

        plan = self._plan(state, policy, objective=objective, target_repo=target_repo, profile=profile)
        if plan is None:
            state.final_summary = "Unable to create a valid workflow plan."
            state.save()
            return state, state.final_summary

        state.goal = str(plan.get("goal", ""))
        state.todos = self._normalize_todos(plan.get("todos", []))
        state.save()

        if not state.todos:
            state.errors.append({"code": "MODEL_OUTPUT_INVALID", "message": "plan did not contain todos"})
            state.final_summary = "Unable to create a valid workflow plan."
            state.save()
            return state, state.final_summary

        self._execute_todos(state)
        self._synthesize(state, policy)
        final_response = self._final(state, policy)
        state.phase = "FINAL"
        state.save()
        return state, final_response

    def _plan(
        self,
        state: WorkflowState,
        policy: dict[str, str],
        *,
        objective: str | None,
        target_repo: str | None,
        profile: str,
    ) -> dict[str, Any] | None:
        model_plan: dict[str, Any] | None = None
        try:
            model_plan, fallback = self.lm_client.chat_json(
                messages=[
                    {"role": "system", "content": "Output compact workflow JSON only. Do not call tools."},
                    {"role": "user", "content": state.user_prompt},
                ],
                schema=PLAN_SCHEMA,
                reasoning=policy["PLAN"],
                max_tokens=500,
                phase="PLAN",
            )
            state.reasoning_policy["fallbacks"]["PLAN"] = fallback
        except ModelOutputInvalid as exc:
            state.errors.append({"code": "MODEL_OUTPUT_INVALID", "message": str(exc)[:1000]})
        except Exception as exc:
            state.errors.append({"code": "MODEL_CALL_FAILED", "message": str(exc)[:1000]})

        if model_plan and self._plan_valid(model_plan):
            if model_plan.get("todos"):
                return model_plan

        inferred_objective = objective or self._extract_prompt_value(state.user_prompt, "objective")
        inferred_target_repo = target_repo or self._extract_prompt_value(state.user_prompt, "target repo")
        if inferred_objective and inferred_target_repo:
            return self._canonical_plan(inferred_objective, inferred_target_repo, profile)
        state.errors.append({"code": "NEEDS_INPUT", "message": "objective and target_repo are required"})
        if not any(err["code"] == "MODEL_OUTPUT_INVALID" for err in state.errors):
            state.errors.append({"code": "MODEL_OUTPUT_INVALID", "message": "planner output could not be used"})
        return None

    def _execute_todos(self, state: WorkflowState) -> None:
        steps = 0
        while steps < self.max_steps:
            todo = self._next_pending_todo(state)
            if todo is None:
                state.phase = "SYNTHESIZE"
                state.save()
                return
            state.phase = "ACT"
            todo["status"] = "active"
            todo["args"] = self._resolve_args(todo.get("args", {}), state)
            state.save()
            ok, reason = validate_tool(todo.get("tool_name", ""), todo.get("args", {}), allow_ingest=self._todo_allows_ingest(todo))
            if not ok:
                todo["status"] = "blocked"
                state.errors.append({"code": "POLICY_BLOCK", "message": reason, "todo_id": todo.get("id", "")})
                state.save()
                return

            raw = self.bridge_client.call_tool(todo["tool_name"], todo["args"])
            state.phase = "SUMMARISE_TOOL_RESULT"
            compact = compact_tool_result(
                todo["tool_name"],
                raw,
                max_chars=self.max_tool_result_chars,
                include_content=bool(todo.get("include_content", False)),
            )
            state.tool_results.append(compact)
            state.artifacts.update(compact.get("artifacts", {}))
            state.save()

            state.phase = "CHECK"
            if not compact.get("ok"):
                todo["status"] = "blocked"
                state.errors.append({"code": "TOOL_BLOCKED", "message": compact.get("summary", ""), "todo_id": todo.get("id", "")})
                state.save()
                return
            todo["status"] = "done"
            state.save()
            if todo["tool_name"] == "mcp_investigation_compile_handoff":
                return
            recommended = compact.get("recommended_next_tool")
            if recommended:
                if recommended not in ALLOWED_TOOLS:
                    state.errors.append({"code": "POLICY_BLOCK", "message": f"recommended tool is not allowlisted: {recommended}"})
                    state.save()
                    return
                if not any(t.get("tool_name") == recommended and t.get("status") == "pending" for t in state.todos):
                    state.errors.append({"code": "PLAN_MISMATCH", "message": f"recommended tool is not pending in plan: {recommended}"})
                    state.save()
                    return
            steps += 1
        state.errors.append({"code": "MAX_STEPS_EXCEEDED", "message": f"workflow exceeded {self.max_steps} steps"})
        state.save()

    def _synthesize(self, state: WorkflowState, policy: dict[str, str]) -> None:
        state.phase = "SYNTHESIZE"
        state.save()
        try:
            result, fallback = self.lm_client.chat_json(
                messages=[
                    {"role": "system", "content": "Summarize compact workflow state as JSON only. Do not dump artifact content."},
                    {"role": "user", "content": self._compact_state_json(state)},
                ],
                schema={"name": "workflow_summary", "schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}},
                reasoning=policy["SYNTHESIZE"],
                max_tokens=300,
                phase="SYNTHESIZE",
            )
            state.reasoning_policy["fallbacks"]["SYNTHESIZE"] = fallback
            state.final_summary = str(result.get("summary", ""))[:2000]
        except Exception as exc:
            state.errors.append({"code": "MODEL_OUTPUT_INVALID", "message": str(exc)[:1000], "phase": "SYNTHESIZE"})
            state.final_summary = self._deterministic_summary(state)
        state.save()

    def _final(self, state: WorkflowState, policy: dict[str, str]) -> str:
        state.phase = "FINAL"
        state.save()
        try:
            result, fallback = self.lm_client.chat_json(
                messages=[
                    {"role": "system", "content": "Write a concise user-facing response. Do not include raw backend JSON, manifest CSV, or report bodies."},
                    {"role": "user", "content": self._compact_state_json(state)},
                ],
                schema={"name": "workflow_final", "schema": {"type": "object", "properties": {"response": {"type": "string"}}, "required": ["response"]}},
                reasoning=policy["FINAL"],
                max_tokens=300,
                phase="FINAL",
            )
            state.reasoning_policy["fallbacks"]["FINAL"] = fallback
            response = str(result.get("response", "")).strip()
            state.final_summary = response or state.final_summary
            return state.final_summary
        except Exception as exc:
            state.errors.append({"code": "MODEL_OUTPUT_INVALID", "message": str(exc)[:1000], "phase": "FINAL"})
            return state.final_summary or self._deterministic_summary(state)

    def _plan_valid(self, plan: dict[str, Any]) -> bool:
        if not isinstance(plan, dict) or not isinstance(plan.get("todos"), list):
            return False
        if len(plan["todos"]) > self.max_steps:
            return False
        for todo in plan["todos"]:
            if not isinstance(todo, dict):
                return False
            if not isinstance(todo.get("args", {}), dict):
                return False
            try:
                json.dumps(todo.get("args", {}))
            except TypeError:
                return False
            allow_ingest = self.allow_ingest and bool(todo.get("allow_ingest", False))
            ok, _ = validate_tool(str(todo.get("tool_name", "")), todo.get("args", {}), allow_ingest=allow_ingest)
            if not ok:
                return False
        return True

    def _canonical_plan(self, objective: str, target_repo: str, profile: str) -> dict[str, Any]:
        return {
            "goal": objective,
            "stop_condition": "handoff compiled or blocking error returned",
            "notes": "deterministic canonical Tool Assist investigation",
            "todos": [
                {
                    "id": "start_investigation",
                    "description": "Create Tool Assist session",
                    "tool_name": "mcp_investigation_start",
                    "args": {"objective": objective, "target_repo": target_repo, "profile": profile},
                },
                {
                    "id": "filemap",
                    "description": "Build constrained file map",
                    "tool_name": "mcp_investigation_filemap",
                    "args": {"session_path": "${artifacts.session_path}", "profile": profile},
                },
                {
                    "id": "validate_manifest",
                    "description": "Validate investigation manifest",
                    "tool_name": "mcp_investigation_validate_manifest",
                    "args": {"session_path": "${artifacts.session_path}"},
                },
                {
                    "id": "read_report",
                    "description": "Read bounded manifest health report metadata",
                    "tool_name": "mcp_investigation_read_report",
                    "args": {
                        "session_path": "${artifacts.session_path}",
                        "artifact_key": "manifest_health_json",
                        "max_chars": self.max_tool_result_chars,
                    },
                },
                {
                    "id": "compile_handoff",
                    "description": "Compile investigation handoff",
                    "tool_name": "mcp_investigation_compile_handoff",
                    "args": {"session_path": "${artifacts.session_path}"},
                },
            ],
        }

    def _normalize_todos(self, todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for index, todo in enumerate(todos[: self.max_steps]):
            item = dict(todo)
            item.setdefault("id", f"todo_{index + 1}")
            item.setdefault("description", item["id"])
            item.setdefault("args", {})
            item["status"] = "pending"
            normalized.append(item)
        return normalized

    def _next_pending_todo(self, state: WorkflowState) -> dict[str, Any] | None:
        for todo in state.todos:
            if todo.get("status") == "pending":
                return todo
        return None

    def _resolve_args(self, args: dict[str, Any], state: WorkflowState) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("${artifacts.") and value.endswith("}"):
                artifact_key = value[len("${artifacts.") : -1]
                resolved[key] = state.artifacts.get(artifact_key, "")
            else:
                resolved[key] = value
        return resolved

    def _todo_allows_ingest(self, todo: dict[str, Any]) -> bool:
        return self.allow_ingest and bool(todo.get("allow_ingest", False))

    def _extract_prompt_value(self, prompt: str, label: str) -> str:
        match = re.search(rf"^{re.escape(label)}\s*:\s*(.+)$", prompt, flags=re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _compact_state_json(self, state: WorkflowState) -> str:
        safe = {
            "run_id": state.run_id,
            "goal": state.goal,
            "phase": state.phase,
            "todos": state.todos,
            "artifacts": state.artifacts,
            "tool_results": state.tool_results,
            "errors": state.errors,
            "final_summary": state.final_summary,
        }
        return json.dumps(safe, sort_keys=True)

    def _deterministic_summary(self, state: WorkflowState) -> str:
        status = "blocked" if any(todo.get("status") == "blocked" for todo in state.todos) else "complete"
        return f"Workflow {status}. Artifacts: {sorted(state.artifacts.values())}"
