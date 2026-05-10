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
    """Prove drafting is gated on both is_drafting_enabled() and lm_client."""

    _CI_RESPONSE = {
        "ok": True, "status": "COMPLETE", "summary": "analyzed",
        "artifacts": {
            "repo_context_md": "# Context\n5 files",
            "dependency_graph_summary": "3 nodes",
            "dependency_graph_mmd": "graph TD\n  a --> b",
            "code_map_summary": "5 files",
        },
    }

    def _make_runner(self, *, lm_client=None):
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
        tool_client = MagicMock()
        tool_client.call_tool.return_value = self._CI_RESPONSE
        return WorkflowRunner(
            tool_client=tool_client,
            lm_client=lm_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
        )

    def test_no_draft_by_default(self, monkeypatch):
        monkeypatch.delenv(_ENV_VAR, raising=False)
        runner = self._make_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True
        assert "review_draft_md" not in response["artifacts"]

    def test_no_draft_when_flag_disabled_even_with_lm_client(self, monkeypatch):
        from unittest.mock import MagicMock
        monkeypatch.setenv(_ENV_VAR, "false")
        lm = MagicMock()
        lm.complete.return_value = "## Draft"
        runner = self._make_runner(lm_client=lm)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert "review_draft_md" not in response["artifacts"]
        lm.complete.assert_not_called()

    def test_no_draft_when_flag_enabled_but_no_lm_client(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "true")
        runner = self._make_runner(lm_client=None)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert "review_draft_md" not in response["artifacts"]

    def test_draft_produced_when_flag_enabled_and_lm_client_present(self, monkeypatch):
        from unittest.mock import MagicMock
        monkeypatch.setenv(_ENV_VAR, "true")
        lm = MagicMock()
        lm.complete.return_value = "## Draft Review\nWell-structured."
        runner = self._make_runner(lm_client=lm)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True
        assert "review_draft_md" in response["artifacts"]
        from pathlib import Path
        content = Path(response["artifacts"]["review_draft_md"]).read_text(encoding="utf-8")
        assert "Well-structured" in content

    def test_draft_in_report_index_when_produced(self, monkeypatch):
        import json
        from unittest.mock import MagicMock
        monkeypatch.setenv(_ENV_VAR, "true")
        lm = MagicMock()
        lm.complete.return_value = "## Draft"
        runner = self._make_runner(lm_client=lm)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        index = json.loads(response["artifacts"]["code_review_report_index"])
        assert "review_draft_md" in index

    def test_lm_client_failure_does_not_break_pipeline(self, monkeypatch):
        from unittest.mock import MagicMock
        monkeypatch.setenv(_ENV_VAR, "true")
        lm = MagicMock()
        lm.complete.side_effect = RuntimeError("model down")
        runner = self._make_runner(lm_client=lm)
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True
        assert "review_draft_md" not in response["artifacts"]
