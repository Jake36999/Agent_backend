from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.adapters import ToolAdapters
from orchestrator.research.deep_research_adapter import invoke_deep_research


# ---------------------------------------------------------------------------
# invoke_deep_research unit tests
# ---------------------------------------------------------------------------

class TestInvokeDeepResearch:
    def test_static_empty_sources_returns_ok(self):
        r = invoke_deep_research(query="test", source_mode="static")
        assert r["ok"] is True
        assert r["status"] == "OK"

    def test_static_with_sources_returns_ok(self):
        sources = [
            {"source_id": "s1", "title": "T", "url_or_path": "/f", "source_type": "provided",
             "excerpt": "Some content.", "retrieved_at": "2025-01-01T00:00:00Z"}
        ]
        r = invoke_deep_research(query="find bug", source_mode="static", sources_raw=sources)
        assert r["ok"] is True
        assert r["sources_count"] == 1

    def test_result_has_artifacts(self):
        r = invoke_deep_research(query="q", source_mode="static")
        assert "artifacts" in r
        assert "research_report_md" in r["artifacts"]
        assert "research_citations_json" in r["artifacts"]

    def test_result_has_capability_receipt(self):
        r = invoke_deep_research(query="q", source_mode="static")
        cr = r["capability_receipt"]
        assert cr["capability_id"] == "research.deep_research"
        assert cr["capability_type"] == "research"
        assert cr["risk_tier"] == "T2"
        assert cr["network_access"] is False
        assert cr["writes_external_state"] is False

    def test_result_ok_receipt_authorized(self):
        r = invoke_deep_research(query="q", source_mode="static")
        assert r["capability_receipt"]["authorized"] is True
        assert r["capability_receipt"]["status"] == "OK"

    def test_web_stub_returns_policy_block(self):
        r = invoke_deep_research(query="q", source_mode="web_stub")
        assert r["ok"] is False
        assert r["status"] == "POLICY_BLOCK"
        assert r["capability_receipt"]["authorized"] is False

    def test_invalid_source_mode_returns_policy_block(self):
        r = invoke_deep_research(query="q", source_mode="browser_magic")
        assert r["ok"] is False
        assert r["status"] == "POLICY_BLOCK"

    def test_answer_md_present(self):
        r = invoke_deep_research(query="q", source_mode="static")
        assert "answer_md" in r
        assert isinstance(r["answer_md"], str)

    def test_gaps_is_list(self):
        r = invoke_deep_research(query="q", source_mode="static")
        assert isinstance(r["gaps"], list)

    def test_suggested_next_actions_is_list(self):
        r = invoke_deep_research(query="q", source_mode="static")
        assert isinstance(r["suggested_next_actions"], list)

    def test_max_sources_capped(self):
        sources = [
            {"source_id": f"s{i}", "title": f"T{i}", "url_or_path": f"/f{i}",
             "source_type": "provided", "excerpt": f"text {i}", "retrieved_at": "2025-01-01T00:00:00Z"}
            for i in range(60)
        ]
        r = invoke_deep_research(query="q", source_mode="static", sources_raw=sources, max_sources=5)
        assert r["sources_count"] <= 5

    def test_local_nonexistent_repo_still_ok(self):
        r = invoke_deep_research(
            query="q", source_mode="local", target_repo="/nonexistent/path"
        )
        assert r["ok"] is True
        assert r["sources_count"] == 0

    def test_report_md_bounded(self):
        big_sources = [
            {"source_id": f"s{i}", "title": f"T{i}", "url_or_path": f"/f{i}",
             "source_type": "provided", "excerpt": "y" * 2000, "retrieved_at": "2025-01-01T00:00:00Z"}
            for i in range(20)
        ]
        r = invoke_deep_research(query="q", source_mode="static", sources_raw=big_sources)
        assert len(r["artifacts"]["research_report_md"]) <= 11000


# ---------------------------------------------------------------------------
# ToolAdapters dispatch tests
# ---------------------------------------------------------------------------

class TestMcpDeepResearchDispatch:
    def _ta(self):
        return ToolAdapters()

    def test_dispatch_static_ok(self):
        r = self._ta().call_mcp_tool("mcp_deep_research", {"query": "test query"})
        assert r["ok"] is True

    def test_dispatch_web_stub_policy_block(self):
        r = self._ta().call_mcp_tool("mcp_deep_research", {
            "query": "test", "source_mode": "web_stub"
        })
        assert r["ok"] is False
        assert r["status"] == "POLICY_BLOCK"

    def test_dispatch_artifacts_present(self):
        r = self._ta().call_mcp_tool("mcp_deep_research", {"query": "test query"})
        assert "research_report_md" in r["artifacts"]

    def test_dispatch_receipt_research_type(self):
        r = self._ta().call_mcp_tool("mcp_deep_research", {"query": "q"})
        assert r["capability_receipt"]["capability_type"] == "research"

    def test_mcp_deep_research_not_in_node_contracts(self):
        import json
        from pathlib import Path
        manifest_path = Path(__file__).parent.parent.parent / "tool_manifest.json"
        if not manifest_path.exists():
            pytest.skip("tool_manifest.json not found")
        manifest = json.loads(manifest_path.read_text())
        tool = next((t for t in manifest["tools"] if t["tool_id"] == "mcp_deep_research"), None)
        assert tool is not None, "mcp_deep_research not in manifest"
        assert tool.get("internal_only") is True, "mcp_deep_research must be internal_only"
        assert all(s in ("python-daemon", "internal") for s in tool["surfaces"]), \
            "mcp_deep_research must not have node-mcp surface"


# ---------------------------------------------------------------------------
# Pipeline-level tests
# ---------------------------------------------------------------------------

class TestDeepResearchPipelineNew:
    def test_pipeline_loads_with_single_step(self):
        from orchestrator.pipeline.loader import PipelineLoader
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        assert defn.pipeline_id == "deep_research"
        assert len(defn.steps) == 1
        assert defn.steps[0].step_id == "deep_research"
        assert defn.steps[0].tool_name == "mcp_deep_research"

    def test_pipeline_compiles(self):
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        compiler = PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS))
        plan = compiler.compile_to_plan_list(
            defn, {"objective": "test", "target_repo": "/tmp/r", "profile": "safe"}
        )
        assert len(plan) == 1

    def test_runner_integration(self, tmp_path: Path):
        from unittest.mock import MagicMock
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader

        dr_response = {
            "ok": True,
            "status": "OK",
            "query": "research the repo",
            "source_mode": "static",
            "sources_count": 0,
            "answer_md": "Insufficient evidence.",
            "gaps": [],
            "confidence": "none",
            "suggested_next_actions": [],
            "artifacts": {
                "research_report_md": "# Report\n\nTest.",
                "research_citations_json": '{"citations":[]}',
                "research_sources_json": '{"sources":[]}',
                "research_next_actions_yaml": "next_actions:\n",
            },
            "capability_receipt": {
                "operation": "capability.execute",
                "capability_id": "research.deep_research",
                "capability_type": "research",
                "risk_tier": "T2",
                "status": "OK",
                "authorized": True,
                "network_access": False,
                "writes_external_state": False,
                "approval_id": None,
                "artifact_refs": [],
                "summary": "ok",
            },
        }
        tool_client = MagicMock()
        tool_client.call_tool.return_value = dr_response
        runner = WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            state_dir=tmp_path,
        )
        _state, response = runner.run(
            objective="research the repo",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert response["ok"] is True
        assert response["status"] == "COMPLETE"
        assert "research_report_md" in response["artifacts"]
        assert "research_report_index" in response["artifacts"]
        assert response["artifacts"]["pipeline_id"] == "deep_research"
