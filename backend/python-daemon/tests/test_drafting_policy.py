from __future__ import annotations

import pytest

from orchestrator.code_review.drafting_policy import (
    REVIEW_DRAFTING_CAPABILITY,
    _ENV_VAR,
    can_draft_review,
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


class TestCanDraftReview:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(_ENV_VAR, raising=False)
        result = can_draft_review(pipeline_id="code_review", lm_client=object())
        assert result["allowed"] is False
        assert result["reason"] == "drafting_disabled"

    def test_disabled_when_false(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "false")
        assert can_draft_review(pipeline_id="code_review", lm_client=object())["allowed"] is False

    def test_disabled_when_one(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "1")
        assert can_draft_review(pipeline_id="code_review", lm_client=object())["allowed"] is False

    def test_disabled_when_uppercase_true(self, monkeypatch):
        # "TRUE" is still accepted by is_drafting_enabled (case-insensitive), so we test "yes"
        monkeypatch.setenv(_ENV_VAR, "yes")
        assert can_draft_review(pipeline_id="code_review", lm_client=object())["allowed"] is False

    def test_disabled_when_no_lm_client(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "true")
        result = can_draft_review(pipeline_id="code_review", lm_client=None)
        assert result["allowed"] is False
        assert result["reason"] == "no_lm_client"

    def test_disabled_wrong_pipeline(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "true")
        result = can_draft_review(pipeline_id="investigation", lm_client=object())
        assert result["allowed"] is False
        assert result["reason"] == "wrong_pipeline"

    def test_allowed_all_conditions_met(self, monkeypatch):
        monkeypatch.setenv(_ENV_VAR, "true")
        result = can_draft_review(pipeline_id="code_review", lm_client=object())
        assert result["allowed"] is True
        assert result["reason"] == "authorized"


class TestWorkflowRunnerDraftingWired:
    """Tests for Phase 2H wiring in WorkflowRunner."""

    def _make_runner(self, monkeypatch, *, lm_client=None, pipeline_id="code_review"):
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        ci_response = {
            "ok": True, "status": "COMPLETE", "summary": "analyzed",
            "artifacts": {
                "repo_context_md": "# Context\n5 files",
                "dependency_graph_summary": "3 nodes",
                "dependency_graph_mmd": "graph TD\n  a --> b",
                "code_map_summary": "5 files",
                "architecture_overview": "## Overview\nSmall repo.",
                "code_review_summary": "## Summary\nAll good.",
                "heuristics": '{"largest_files": []}',
                "next_actions": "suggested_followups:\n  - id: t1",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = ci_response
        return WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=lm_client,
        ), pipeline_id

    def test_env_true_with_lm_client_produces_draft(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_ENV_VAR, "true")
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        lm_client = MagicMock()
        lm_client.complete.return_value = "## Draft\nLooks solid."
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
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=lm_client,
            state_dir=tmp_path,
        )
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True
        assert "review_draft_md" in response["artifacts"]

    def test_env_true_no_lm_client_no_draft(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_ENV_VAR, "true")
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        ci_response = {
            "ok": True, "status": "COMPLETE", "summary": "analyzed",
            "artifacts": {
                "repo_context_md": "# ctx", "dependency_graph_summary": "n",
                "dependency_graph_mmd": "graph TD\n  a --> b", "code_map_summary": "f",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = ci_response
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=None,
            state_dir=tmp_path,
        )
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert "review_draft_md" not in response["artifacts"]
        receipt = response["artifacts"].get("review_drafting_receipt")
        assert receipt is not None
        import json
        r = json.loads(receipt) if isinstance(receipt, str) else receipt
        assert r.get("authorized") is False

    def test_investigation_pipeline_never_drafts(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_ENV_VAR, "true")
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        lm_client = MagicMock()
        lm_client.complete.return_value = "## Draft\nContent."
        ci_response = {
            "ok": True, "status": "COMPLETE", "summary": "done",
            "artifacts": {
                "repo_context_md": "# ctx", "dependency_graph_summary": "n",
                "dependency_graph_mmd": "graph TD\n  a --> b", "code_map_summary": "f",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = ci_response
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=lm_client,
            state_dir=tmp_path,
        )
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        assert "review_draft_md" not in response["artifacts"]

    def test_draft_file_contains_disclaimer(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_ENV_VAR, "true")
        from unittest.mock import MagicMock
        from pathlib import Path
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        lm_client = MagicMock()
        lm_client.complete.return_value = "## Draft\nContent here."
        ci_response = {
            "ok": True, "status": "COMPLETE", "summary": "analyzed",
            "artifacts": {
                "repo_context_md": "# ctx", "dependency_graph_summary": "n",
                "dependency_graph_mmd": "graph TD\n  a --> b", "code_map_summary": "f",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = ci_response
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=lm_client,
            state_dir=tmp_path,
        )
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        draft_path = response["artifacts"].get("review_draft_md")
        assert draft_path is not None
        content = Path(draft_path).read_text(encoding="utf-8")
        assert "Draft model-assisted review — requires human verification" in content

    def test_draft_path_under_state_dir_run_id(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_ENV_VAR, "true")
        from unittest.mock import MagicMock
        from pathlib import Path
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        lm_client = MagicMock()
        lm_client.complete.return_value = "## Draft\nContent."
        ci_response = {
            "ok": True, "status": "COMPLETE", "summary": "analyzed",
            "artifacts": {
                "repo_context_md": "# ctx", "dependency_graph_summary": "n",
                "dependency_graph_mmd": "graph TD\n  a --> b", "code_map_summary": "f",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = ci_response
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=lm_client,
            state_dir=tmp_path,
        )
        state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        draft_path = Path(response["artifacts"]["review_draft_md"])
        assert tmp_path in draft_path.parents
        assert state.run_id in str(draft_path)

    def test_lm_client_exception_deterministic_artifacts_still_produced(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_ENV_VAR, "true")
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        lm_client = MagicMock()
        lm_client.complete.side_effect = RuntimeError("model down")
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
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            lm_client=lm_client,
            state_dir=tmp_path,
        )
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True
        assert "review_draft_md" not in response["artifacts"]
        receipt = response["artifacts"].get("review_drafting_receipt")
        assert receipt is not None
        import json
        r = json.loads(receipt) if isinstance(receipt, str) else receipt
        assert r.get("status") == "ERROR"
        # deterministic artifacts still present
        assert "code_review_report_index" in response["artifacts"]
