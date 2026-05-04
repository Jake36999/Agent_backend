from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from .runner import WorkflowRunner


COMPLETE_SUMMARY = "Workflow complete. Final report, Python bundle, archive YAML, manifest, and session artifacts are available."


class InProcessBridgeClient:
    def __init__(self, call_tool: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        self._call_tool = call_tool

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return self._call_tool(tool_name, args)


def compact_workflow_response(state: Any, final_response: str) -> dict[str, Any]:
    blocked = next((todo for todo in getattr(state, "todos", []) if todo.get("status") == "blocked"), None)
    errors = getattr(state, "errors", [])
    ok = blocked is None and not errors
    result: dict[str, Any] = {
        "ok": ok,
        "status": "blocked" if blocked else ("partial" if errors else "complete"),
        "run_id": str(getattr(state, "run_id", "")),
        "summary": _compact_summary(ok=ok, blocked=blocked, errors=errors, final_response=final_response),
        "artifacts": _dedupe_artifacts(dict(getattr(state, "artifacts", {}) or {})),
        "state_path": str(getattr(state, "path", "")),
    }
    if blocked:
        result["block_reason"] = str(blocked.get("description") or blocked.get("id") or "workflow blocked")[:1000]
    if errors:
        first = errors[0]
        result["error"] = {
            "code": str(first.get("code", "workflow_error")),
            "message": str(first.get("message", ""))[:1000],
        }
    return result


def run_agent_workflow_tool(
    args: dict[str, Any],
    *,
    tool_caller: Callable[[str, dict[str, Any]], dict[str, Any]],
    runner_factory: Callable[..., WorkflowRunner] | None = None,
) -> dict[str, Any]:
    try:
        objective = str(args["objective"])
        target_repo = str(args["target_repo"])
        profile = str(args.get("profile", "safe"))
        if profile != "safe":
            return _policy_block("unsupported profile for mcp_agent_workflow_run")
        target_error = _validate_target_repo(target_repo)
        if target_error:
            return target_error
        allow_ingest = bool(args.get("allow_ingest", False))
        include_report_preview = bool(args.get("include_report_preview", False))
        use_model_phases = bool(args.get("use_model_phases", False))
        prompt = f"Objective: {objective}\nTarget repo: {target_repo}\nProfile: {profile}"
        bridge_client = InProcessBridgeClient(tool_caller)
        factory = runner_factory or WorkflowRunner
        runner = factory(
            allow_ingest=allow_ingest,
            bridge_client=bridge_client,
            use_model_phases=use_model_phases,
        )
        state, final_response = runner.run(
            prompt,
            objective=objective,
            target_repo=target_repo,
            profile=profile,
            include_report_preview=include_report_preview,
        )
        return compact_workflow_response(state, final_response)
    except KeyError as exc:
        return _policy_block(f"missing required argument: {exc.args[0]}")
    except Exception as exc:
        return {
            "ok": False,
            "status": "ERROR",
            "run_id": "",
            "summary": "Agent workflow failed before producing a compact state.",
            "artifacts": {},
            "state_path": "",
            "error": {"code": "workflow_run_failed", "message": str(exc)[:1000]},
        }


def _policy_block(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "POLICY_BLOCK",
        "run_id": "",
        "summary": message,
        "artifacts": {},
        "state_path": "",
        "error": {"code": "policy_block", "message": message},
    }


def _invalid_target_repo(message: str) -> dict[str, Any]:
    summary = "target_repo must be an existing absolute path under an allowed root."
    return {
        "ok": False,
        "status": "POLICY_BLOCK",
        "run_id": "",
        "summary": summary,
        "artifacts": {},
        "state_path": "",
        "error": {"code": "invalid_target_repo", "message": message},
    }


def _validate_target_repo(target_repo: str) -> dict[str, Any] | None:
    try:
        path = Path(target_repo).expanduser()
        if not path.is_absolute():
            return _invalid_target_repo("target_repo must be an absolute local path.")
        if not path.exists():
            return _invalid_target_repo("target_repo does not exist.")
        resolved = path.resolve()
        roots_raw = os.getenv("ALETHEIA_ALLOWED_ROOTS", "")
        if roots_raw.strip():
            roots = [Path(part).expanduser().resolve() for part in roots_raw.split(";") if part.strip()]
            if roots and not any(resolved == root or root in resolved.parents for root in roots):
                return _invalid_target_repo("target_repo is outside ALETHEIA_ALLOWED_ROOTS.")
    except OSError as exc:
        return _invalid_target_repo(f"target_repo could not be resolved: {exc}")
    return None


def _compact_summary(*, ok: bool, blocked: dict[str, Any] | None, errors: list[dict[str, Any]], final_response: str) -> str:
    if ok:
        return COMPLETE_SUMMARY
    if blocked:
        return "Workflow blocked before completion."
    if errors:
        return "Workflow completed with errors."
    return str(final_response or "")[:2000]


def _dedupe_artifacts(artifacts: dict[str, Any]) -> dict[str, str]:
    deduped: dict[str, str] = {}
    seen_paths: set[str] = set()
    for key, value in artifacts.items():
        path = str(value)
        if path in seen_paths:
            continue
        deduped[str(key)] = path
        seen_paths.add(path)
    return deduped
