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
