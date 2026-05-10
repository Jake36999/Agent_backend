from __future__ import annotations

import pytest

from orchestrator.code_review.drafting_policy import (
    REVIEW_DRAFTING_CAPABILITY,
    _ENV_VAR,
    is_drafting_enabled,
)


class TestIsDraftingEnabled:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(_ENV_VAR, raising=False)
        assert is_drafting_enabled() is False

    def test_disabled_when_env_empty(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "")
        assert is_drafting_enabled() is False

    def test_disabled_when_env_false(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "false")
        assert is_drafting_enabled() is False

    def test_disabled_when_env_zero(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "0")
        assert is_drafting_enabled() is False

    def test_disabled_when_env_arbitrary(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "yes")
        assert is_drafting_enabled() is False

    def test_enabled_when_env_true(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "true")
        assert is_drafting_enabled() is True

    def test_enabled_case_insensitive(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "TRUE")
        assert is_drafting_enabled() is True

    def test_enabled_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "  true  ")
        assert is_drafting_enabled() is True


class TestReviewDraftingCapabilityDescriptor:
    def test_capability_id_present(self):
        assert REVIEW_DRAFTING_CAPABILITY["capability_id"] == "review_drafting.lm_assisted"

    def test_status_is_disabled(self):
        assert REVIEW_DRAFTING_CAPABILITY["status"] == "disabled"

    def test_risk_tier_is_t3(self):
        assert REVIEW_DRAFTING_CAPABILITY["risk_tier"] == "T3"

    def test_requires_approval(self):
        assert REVIEW_DRAFTING_CAPABILITY["requires_approval"] is True

    def test_network_access_flagged(self):
        assert REVIEW_DRAFTING_CAPABILITY["network_access"] is True

    def test_does_not_write_external_state(self):
        assert REVIEW_DRAFTING_CAPABILITY["writes_external_state"] is False


class TestWorkflowRunnerRespectsPolicy:
    """Prove drafting is bypassed when policy is disabled."""

    def _make_code_review_runner(self, monkeypatch):
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        monkeypatch.delenv(_ENV_VAR, raising=False)

        ci_response = {
            "ok": True, "status": "COMPLETE", "summary": "analyzed",
            "artifacts": {
                "repo_context_md": "# Context\n5 files",
                "dependency_graph_summary": "3 nodes",
                "dependency_graph_mmd": "graph TD\n  a --> b",
                "code_map_summary": "5 files",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = ci_response
        return WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
        )

    def test_no_draft_artifact_when_disabled(self, monkeypatch):
        runner = self._make_code_review_runner(monkeypatch)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True
        assert "review_draft_md" not in response["artifacts"]

    def test_no_draft_artifact_by_default(self, monkeypatch):
        monkeypatch.delenv(_ENV_VAR, raising=False)
        runner = self._make_code_review_runner(monkeypatch)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert "review_draft_md" not in response["artifacts"]
