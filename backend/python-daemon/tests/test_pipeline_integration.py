from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
from orchestrator.agent_workflow.runner import WorkflowRunner
from orchestrator.pipeline.compiler import PipelineCompiler
from orchestrator.pipeline.loader import PipelineLoader


def _make_runner(tool_responses: list[dict] | None = None) -> WorkflowRunner:
    loader = PipelineLoader()
    compiler = PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS))

    responses = iter(tool_responses or [])

    def _call_tool(tool_name, args):
        try:
            return next(responses)
        except StopIteration:
            return {"ok": True, "status": "COMPLETE", "summary": "ok", "artifacts": {}}

    tool_client = MagicMock()
    tool_client.call_tool.side_effect = _call_tool
    return WorkflowRunner(
        tool_client=tool_client,
        pipeline_loader=loader,
        pipeline_compiler=compiler,
    )


def _make_runner_with_capture(responses_by_tool: dict[str, dict] | None = None) -> tuple[WorkflowRunner, list]:
    """Returns (runner, calls) where calls accumulates (tool_name, args) tuples."""
    calls: list = []
    responses_by_tool = responses_by_tool or {}

    def _call_tool(tool_name, args):
        calls.append((tool_name, dict(args)))
        if tool_name in responses_by_tool:
            return responses_by_tool[tool_name]
        return {"ok": True, "status": "COMPLETE", "summary": "ok", "artifacts": {}}

    loader = PipelineLoader()
    compiler = PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS))
    tool_client = MagicMock()
    tool_client.call_tool.side_effect = _call_tool
    runner = WorkflowRunner(tool_client=tool_client, pipeline_loader=loader, pipeline_compiler=compiler)
    return runner, calls


class TestPipelineOutputBindings:
    def test_session_path_flows_via_binding(self):
        runner, calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/bound_session"},
            }
        })
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        assert response["ok"] is True
        filemap_args = next(args for tool, args in calls if tool == "mcp_investigation_filemap")
        assert filemap_args["session_path"] == "/tmp/bound_session"

    def test_missing_bound_artifact_produces_policy_block(self):
        # start returns no session_path → filemap binding fails
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {},
            }
        })
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        assert response["ok"] is False
        assert response["status"] == "POLICY_BLOCK"
        err = response.get("error") or {}
        assert isinstance(err, dict) and err.get("code") == "binding_resolution_failed"

    def test_no_binding_sentinel_reaches_executor(self):
        runner, calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/s"},
            }
        })
        runner.run(objective="audit", target_repo="/tmp/repo", pipeline_id="investigation")
        for _tool, args in calls:
            for v in args.values():
                assert not (isinstance(v, dict) and v.get("__binding__") is True), \
                    f"Binding sentinel reached executor in args: {args}"

    def test_binding_trace_appears_in_artifacts(self):
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/s"},
            }
        })
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        assert response["ok"] is True
        artifacts = response.get("artifacts", {})
        assert "binding_trace" in artifacts
        trace = artifacts["binding_trace"]
        assert "start_investigation" in trace
        assert isinstance(trace["start_investigation"], list)

    def test_patch_plan_backward_compat_session_path(self):
        """patch_plan.yaml uses ${session_path} legacy syntax — must still resolve."""
        runner, calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/patch_session"},
            }
        })
        _state, response = runner.run(
            objective="patch it", target_repo="/tmp/repo", pipeline_id="patch_plan"
        )
        assert response["ok"] is True
        filemap_args = next(args for tool, args in calls if tool == "mcp_investigation_filemap")
        assert filemap_args["session_path"] == "/tmp/patch_session"


class TestPipelineIntegration:
    def test_workflow_runner_sets_pipeline_artifacts(self):
        runner = _make_runner()
        _state, response = runner.run(
            objective="audit codebase",
            target_repo="/tmp/repo",
            pipeline_id="investigation",
        )
        artifacts = response.get("artifacts", {})
        assert artifacts.get("pipeline_id") == "investigation"
        assert artifacts.get("compiled_step_count") == 5

    def test_workflow_runner_without_pipeline_id_omits_pipeline_artifacts(self):
        runner = _make_runner()
        _state, response = runner.run(
            objective="audit codebase",
            target_repo="/tmp/repo",
        )
        artifacts = response.get("artifacts", {})
        assert "pipeline_id" not in artifacts
        assert "compiled_step_count" not in artifacts
