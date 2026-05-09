from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orchestrator.agent_workflow.compaction import _compact_error, compact_tool_result
from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
from orchestrator.agent_workflow.runner import WorkflowRunner
from orchestrator.capabilities.models import CapabilityManifest, CapabilityType
from orchestrator.capabilities.policy import check_pipeline_policy, CapabilityPolicyError
from orchestrator.pipeline.compiler import PipelineCompiler
from orchestrator.pipeline.loader import PipelineLoader


class TestCompactError:
    def test_none_input_returns_none(self):
        assert _compact_error(None) is None

    def test_non_dict_returns_none(self):
        assert _compact_error("binding_resolution_failed") is None
        assert _compact_error(42) is None

    def test_oversized_code_is_truncated(self):
        result = _compact_error({"code": "x" * 200, "message": "ok"})
        assert result is not None
        assert len(result["code"]) == 120

    def test_oversized_message_is_truncated(self):
        result = _compact_error({"code": "err", "message": "m" * 2000})
        assert result is not None
        assert len(result["message"]) == 1000

    def test_binding_resolution_failed_survives_compaction(self):
        raw = {
            "ok": False,
            "status": "POLICY_BLOCK",
            "summary": "binding failed",
            "artifacts": {},
            "error": {"code": "binding_resolution_failed", "message": "step 'x' requires artifacts.session_path from start"},
        }
        compact = compact_tool_result("mcp_investigation_filemap", raw)
        err = compact.get("error")
        assert isinstance(err, dict)
        assert err["code"] == "binding_resolution_failed"
        assert "session_path" in err["message"]

    def test_extra_error_fields_are_dropped(self):
        result = _compact_error({"code": "err", "message": "msg", "stack": "x" * 5000, "internal": {}})
        assert result is not None
        assert set(result.keys()) == {"code", "message"}


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

    def test_patch_plan_session_path_flows_via_binding(self):
        """patch_plan.yaml uses bind: syntax — session_path resolved from start_investigation."""
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


class TestPipelineReceiptAttachment:
    def test_pipeline_receipt_present_on_success(self):
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
        receipt = response.get("artifacts", {}).get("pipeline_receipt")
        assert isinstance(receipt, dict), "pipeline_receipt must be a dict"
        assert receipt["operation"] == "capability.execute"
        assert receipt["capability_id"] == "pipeline.investigation"
        assert receipt["capability_type"] == "pipeline"
        assert receipt["risk_tier"] == "T2"
        assert receipt["authorized"] is True
        assert receipt["network_access"] is False

    def test_pipeline_receipt_present_without_explicit_pipeline_id(self):
        """Without explicit pipeline_id, defaults to investigation — receipt still attached."""
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/s"},
            }
        })
        _state, response = runner.run(objective="audit", target_repo="/tmp/repo")
        receipt = response.get("artifacts", {}).get("pipeline_receipt")
        assert isinstance(receipt, dict)
        assert receipt["capability_id"] == "pipeline.investigation"

    def test_pipeline_receipt_no_source_path(self):
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/s"},
            }
        })
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        receipt_str = str(response.get("artifacts", {}).get("pipeline_receipt", {}))
        assert "source_path" not in receipt_str
        assert "allowed_roots" not in receipt_str

    def test_pipeline_receipt_artifact_refs_bounded(self):
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {f"key_{i}": f"val_{i}" for i in range(25)},
            }
        })
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        receipt = response.get("artifacts", {}).get("pipeline_receipt") or {}
        assert len(receipt.get("artifact_refs", [])) <= 20


class TestCodeReviewPipeline:
    _CI_RESPONSE = {
        "ok": True, "status": "COMPLETE", "summary": "analyzed",
        "artifacts": {
            "repo_context_md": "# Repo Context\n\n10 files, 1000 lines",
            "dependency_graph_summary": "5 nodes, 8 edges",
            "dependency_graph_mmd": "graph TD\n  a --> b",
            "code_map_summary": "10 files",
        },
    }

    def _code_review_runner(self):
        return _make_runner_with_capture({"mcp_code_intelligence": self._CI_RESPONSE})

    def test_code_review_pipeline_completes(self):
        runner, _calls = self._code_review_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["ok"] is True

    def test_code_review_pipeline_id_in_artifacts(self):
        runner, _calls = self._code_review_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        assert response["artifacts"]["pipeline_id"] == "code_review"
        assert response["artifacts"]["compiled_step_count"] == 3

    def test_code_review_report_artifacts_present(self):
        runner, _calls = self._code_review_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        artifacts = response["artifacts"]
        for key in ("architecture_overview_md", "dependency_graph_mmd",
                     "code_review_summary_md", "next_actions_yaml", "heuristics_json"):
            assert key in artifacts, f"missing artifact ref: {key}"
            from pathlib import Path
            assert Path(artifacts[key]).exists(), f"artifact file missing: {artifacts[key]}"
        assert "code_review_report_index" in artifacts

    def test_code_review_summary_md_content(self):
        runner, _calls = self._code_review_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        path = response["artifacts"].get("code_review_summary_md", "")
        from pathlib import Path
        summary = Path(path).read_text(encoding="utf-8") if Path(path).exists() else path
        assert "read-only" in summary.lower() or "no files modified" in summary.lower()

    def test_code_review_next_actions_deterministic(self):
        runner, _calls = self._code_review_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        path = response["artifacts"].get("next_actions_yaml", "")
        from pathlib import Path
        yaml_text = Path(path).read_text(encoding="utf-8") if Path(path).exists() else path
        assert "suggested_followups" in yaml_text
        assert "candidate follow-up" in yaml_text
        for forbidden in ("vulnerability", "bug", "security risk", "severity"):
            assert forbidden not in yaml_text.lower()

    def test_code_review_pipeline_receipt_is_t2(self):
        runner, _calls = self._code_review_runner()
        _state, response = runner.run(
            objective="review", target_repo="/tmp/repo", pipeline_id="code_review"
        )
        receipt = response["artifacts"].get("pipeline_receipt", {})
        assert receipt.get("capability_id") == "pipeline.code_review"
        assert receipt.get("risk_tier") == "T2"

    def test_code_review_calls_only_mcp_code_intelligence(self):
        runner, calls = self._code_review_runner()
        runner.run(objective="review", target_repo="/tmp/repo", pipeline_id="code_review")
        tools_called = {tool for tool, _ in calls}
        assert tools_called == {"mcp_code_intelligence"}

    def test_code_review_no_file_mutation_args(self):
        runner, calls = self._code_review_runner()
        runner.run(objective="review", target_repo="/tmp/repo", pipeline_id="code_review")
        for _tool, args in calls:
            assert "write" not in str(args).lower()
            assert "create" not in str(args).lower()


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

    def test_workflow_runner_without_pipeline_id_defaults_to_investigation(self):
        """Without explicit pipeline_id, defaults to investigation pipeline."""
        runner = _make_runner()
        _state, response = runner.run(
            objective="audit codebase",
            target_repo="/tmp/repo",
        )
        artifacts = response.get("artifacts", {})
        assert artifacts.get("pipeline_id") == "investigation"
        assert artifacts.get("compiled_step_count") == 5


def _make_manifest(capability_id: str, *, status: str = "verified", risk_tier: str = "T2") -> CapabilityManifest:
    return CapabilityManifest(
        capability_id=capability_id,
        capability_type=CapabilityType.PIPELINE_TEMPLATE,
        version="1.0.0",
        name=capability_id,
        description="test",
        risk_tier=risk_tier,
        status=status,
    )


class _FakeRegistry:
    """Minimal registry stub for policy tests — no SQLite needed."""

    def __init__(self, manifests: dict[str, CapabilityManifest] | None = None):
        self._manifests = manifests or {}

    def get(self, capability_id: str) -> CapabilityManifest | None:
        return self._manifests.get(capability_id)


class TestCapabilityPolicyEnforcement:
    def test_quarantined_pipeline_blocked(self):
        registry = _FakeRegistry({
            "pipeline_template.investigation": _make_manifest(
                "pipeline_template.investigation", status="quarantined"
            ),
        })
        error = check_pipeline_policy("investigation", registry)
        assert error is not None
        assert "quarantined" in error

    def test_disabled_pipeline_blocked(self):
        registry = _FakeRegistry({
            "pipeline_template.investigation": _make_manifest(
                "pipeline_template.investigation", status="disabled"
            ),
        })
        error = check_pipeline_policy("investigation", registry)
        assert error is not None
        assert "disabled" in error

    def test_verified_pipeline_allowed(self):
        registry = _FakeRegistry({
            "pipeline_template.investigation": _make_manifest(
                "pipeline_template.investigation", status="verified"
            ),
        })
        error = check_pipeline_policy("investigation", registry)
        assert error is None

    def test_no_registry_means_no_enforcement(self):
        error = check_pipeline_policy("investigation", None)
        assert error is None

    def test_unknown_pipeline_allowed(self):
        registry = _FakeRegistry({})
        error = check_pipeline_policy("nonexistent", registry)
        assert error is None

    def test_runner_blocks_quarantined_pipeline(self):
        registry = _FakeRegistry({
            "pipeline_template.investigation": _make_manifest(
                "pipeline_template.investigation", status="quarantined"
            ),
        })
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/s"},
            }
        })
        runner.capability_registry = registry
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        assert response["ok"] is False
        assert response["status"] == "POLICY_BLOCK"
        err = response.get("error", {})
        assert err.get("code") == "capability_policy_block"
        assert "quarantined" in err.get("message", "")

    def test_runner_allows_verified_pipeline(self):
        registry = _FakeRegistry({
            "pipeline_template.investigation": _make_manifest(
                "pipeline_template.investigation", status="verified"
            ),
        })
        runner, _calls = _make_runner_with_capture({
            "mcp_investigation_start": {
                "ok": True, "status": "COMPLETE", "summary": "started",
                "artifacts": {"session_path": "/tmp/s"},
            }
        })
        runner.capability_registry = registry
        _state, response = runner.run(
            objective="audit", target_repo="/tmp/repo", pipeline_id="investigation"
        )
        assert response["ok"] is True

    def test_runner_no_registry_passes(self):
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
