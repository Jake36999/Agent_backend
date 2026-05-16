from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from orchestrator.deep_research.collector import collect_research_sources
from orchestrator.deep_research.models import DeepResearchReport, ResearchCitation, ResearchSource
from orchestrator.deep_research.report_builder import build_deep_research_report
from orchestrator.deep_research.artifact_writer import (
    build_research_index,
    persist_deep_research_artifacts,
)
from orchestrator.pipeline.loader import PipelineLoader, ACTIVE_PIPELINES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_STEP_OUTPUTS: dict = {
    "repo_context": {
        "ok": True,
        "artifacts": {
            "repo_context_md": "# Repo\n10 files, 3 packages.",
            "code_map_summary": "5 modules; main.py is the entrypoint.",
        },
    },
    "code_map": {
        "ok": True,
        "artifacts": {
            "code_map_summary": "Detailed: 12 files across 3 dirs.",
        },
    },
    "dependency_graph": {
        "ok": True,
        "artifacts": {
            "dependency_graph_summary": "15 edges, 2 high fan-in modules.",
        },
    },
    "mermaid": {
        "ok": True,
        "artifacts": {
            "dependency_graph_mmd": "graph TD\n  a --> b",
        },
    },
}


# ---------------------------------------------------------------------------
# Sprint 4A: collector
# ---------------------------------------------------------------------------

class TestCollectResearchSources:
    def test_collects_repo_context(self):
        sources = collect_research_sources(_SAMPLE_STEP_OUTPUTS)
        ids = [s.source_id for s in sources]
        assert "repo_context.repo_context_md" in ids

    def test_collects_dependency_graph(self):
        sources = collect_research_sources(_SAMPLE_STEP_OUTPUTS)
        types = {s.source_type for s in sources}
        assert "dependency_graph" in types

    def test_collects_mermaid(self):
        sources = collect_research_sources(_SAMPLE_STEP_OUTPUTS)
        types = {s.source_type for s in sources}
        assert "mermaid" in types

    def test_deduplicates_same_artifact_key(self):
        # repo_context and code_map both provide code_map_summary; should not double-count same step+key
        sources = collect_research_sources(_SAMPLE_STEP_OUTPUTS)
        seen = [(s.source_id) for s in sources]
        assert len(seen) == len(set(seen))

    def test_empty_outputs_returns_empty(self):
        assert collect_research_sources({}) == []

    def test_missing_artifacts_skipped(self):
        outputs = {"repo_context": {"ok": True, "artifacts": {}}}
        sources = collect_research_sources(outputs)
        assert sources == []

    def test_content_is_bounded(self):
        big = "x" * 10000
        outputs = {"repo_context": {"ok": True, "artifacts": {"repo_context_md": big}}}
        sources = collect_research_sources(outputs)
        assert len(sources[0].content) < 10000

    def test_source_fields_populated(self):
        sources = collect_research_sources(_SAMPLE_STEP_OUTPUTS)
        s = next(s for s in sources if s.source_id == "repo_context.repo_context_md")
        assert s.source_type == "repo_context"
        assert s.artifact_key == "repo_context_md"
        assert "Repo" in s.content


# ---------------------------------------------------------------------------
# Sprint 4A: report builder
# ---------------------------------------------------------------------------

class TestBuildDeepResearchReport:
    def _build(self, step_outputs=None):
        return build_deep_research_report(
            objective="Understand the architecture",
            target_repo="/tmp/myrepo",
            step_outputs=step_outputs or _SAMPLE_STEP_OUTPUTS,
        )

    def test_returns_report_instance(self):
        r = self._build()
        assert isinstance(r, DeepResearchReport)

    def test_objective_preserved(self):
        r = self._build()
        assert r.objective == "Understand the architecture"

    def test_target_repo_preserved(self):
        r = self._build()
        assert r.target_repo == "/tmp/myrepo"

    def test_executive_summary_contains_repo_name(self):
        r = self._build()
        assert "myrepo" in r.executive_summary_md

    def test_executive_summary_contains_disclaimer(self):
        r = self._build()
        assert "No files were modified" in r.executive_summary_md

    def test_findings_contains_repo_context(self):
        r = self._build()
        assert "Repository Context" in r.findings_md

    def test_citations_yaml_well_formed(self):
        r = self._build()
        assert "citations:" in r.citations_yaml
        assert "cite_001" in r.citations_yaml

    def test_citations_reference_source_ids(self):
        r = self._build()
        assert "source_id:" in r.citations_yaml

    def test_sources_index_lists_sources(self):
        r = self._build()
        assert "repo_context" in r.sources_index_md

    def test_empty_step_outputs_produces_report(self):
        r = build_deep_research_report(
            objective="test", target_repo="/tmp/r", step_outputs={}
        )
        assert isinstance(r, DeepResearchReport)
        assert "citations: []" in r.citations_yaml

    def test_executive_summary_bounded(self):
        big_outputs = {
            "repo_context": {"ok": True, "artifacts": {"repo_context_md": "x" * 20000}}
        }
        r = self._build(step_outputs=big_outputs)
        assert len(r.executive_summary_md) <= 8500


# ---------------------------------------------------------------------------
# Sprint 4A: artifact writer
# ---------------------------------------------------------------------------

class TestPersistDeepResearchArtifacts:
    def _report(self):
        return build_deep_research_report(
            objective="test", target_repo="/tmp/r", step_outputs=_SAMPLE_STEP_OUTPUTS
        )

    def test_writes_report_md(self, tmp_path: Path):
        report = self._report()
        refs, _ = persist_deep_research_artifacts(report, "run-1", tmp_path)
        assert "research_report_md" in refs
        assert Path(refs["research_report_md"]).exists()

    def test_writes_citations_yaml(self, tmp_path: Path):
        report = self._report()
        refs, _ = persist_deep_research_artifacts(report, "run-1", tmp_path)
        assert "research_citations_yaml" in refs

    def test_all_files_under_run_dir(self, tmp_path: Path):
        report = self._report()
        refs, _ = persist_deep_research_artifacts(report, "run-99", tmp_path)
        for path_str in refs.values():
            assert "run-99" in path_str
            assert tmp_path.resolve() in Path(path_str).parents

    def test_manifest_written(self, tmp_path: Path):
        report = self._report()
        persist_deep_research_artifacts(report, "run-m", tmp_path)
        manifest = tmp_path / "run-m" / "deep_research_artifacts_manifest.json"
        assert manifest.exists()

    def test_index_build(self, tmp_path: Path):
        report = self._report()
        _, manifest_entries = persist_deep_research_artifacts(report, "run-idx", tmp_path)
        index = build_research_index(manifest_entries)
        assert all("sha256" in v and "bytes" in v for v in index.values())

    def test_run_id_escape_rejected(self, tmp_path: Path):
        report = self._report()
        with pytest.raises(ValueError, match="escapes"):
            persist_deep_research_artifacts(report, "../../etc", tmp_path)


# ---------------------------------------------------------------------------
# Pipeline template (updated: single-step mcp_deep_research)
# ---------------------------------------------------------------------------

class TestDeepResearchPipeline:
    def test_deep_research_in_active_pipelines(self):
        assert "deep_research" in ACTIVE_PIPELINES

    def test_pipeline_loads(self):
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        assert defn.pipeline_id == "deep_research"

    def test_pipeline_has_one_step(self):
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        assert len(defn.steps) == 1

    def test_step_uses_mcp_deep_research(self):
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        assert defn.steps[0].tool_name == "mcp_deep_research"

    def test_step_id_is_deep_research(self):
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        assert defn.steps[0].step_id == "deep_research"

    def test_pipeline_compiles(self):
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
        loader = PipelineLoader()
        defn = loader.load("deep_research")
        compiler = PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS))
        plan = compiler.compile_to_plan_list(
            defn, {"objective": "test", "target_repo": "/tmp/r", "profile": "safe"}
        )
        assert len(plan) == 1


# ---------------------------------------------------------------------------
# WorkflowRunner integration (updated: mocks mcp_deep_research)
# ---------------------------------------------------------------------------

_DR_TOOL_RESPONSE = {
    "ok": True,
    "status": "OK",
    "query": "research the architecture",
    "source_mode": "static",
    "sources_count": 0,
    "answer_md": "Insufficient evidence.",
    "gaps": [],
    "confidence": "none",
    "suggested_next_actions": [],
    "artifacts": {
        "research_report_md": "# Research Report\n\nTest content.",
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
        "artifact_refs": ["research_report_md"],
        "summary": "ok",
    },
}

_CI_RESPONSE = {
    "ok": True,
    "status": "COMPLETE",
    "summary": "analyzed",
    "artifacts": {
        "repo_context_md": "# Repo\n5 files.",
        "code_map_summary": "3 modules.",
        "dependency_graph_summary": "5 edges.",
        "dependency_graph_mmd": "graph TD\n  a --> b",
    },
}


class TestDeepResearchRunnerIntegration:
    def _make_runner(self, tmp_path: Path):
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        tool_client = MagicMock()
        tool_client.call_tool.return_value = _DR_TOOL_RESPONSE
        return WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            state_dir=tmp_path,
        )

    def _make_ci_runner(self, tmp_path: Path):
        from orchestrator.agent_workflow.runner import WorkflowRunner
        from orchestrator.pipeline.compiler import PipelineCompiler
        from orchestrator.pipeline.loader import PipelineLoader
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS

        tool_client = MagicMock()
        tool_client.call_tool.return_value = _CI_RESPONSE
        return WorkflowRunner(
            tool_client=tool_client,
            pipeline_loader=PipelineLoader(),
            pipeline_compiler=PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS)),
            state_dir=tmp_path,
        )

    def test_deep_research_pipeline_completes(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        _state, response = runner.run(
            objective="research the architecture",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert response["ok"] is True
        assert response["status"] == "COMPLETE"

    def test_research_report_md_in_artifacts(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        _state, response = runner.run(
            objective="research",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert "research_report_md" in response["artifacts"]

    def test_research_citations_json_in_artifacts(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        _state, response = runner.run(
            objective="research",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert "research_citations_json" in response["artifacts"]

    def test_research_report_index_in_artifacts(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        _state, response = runner.run(
            objective="research",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert "research_report_index" in response["artifacts"]

    def test_artifacts_under_state_dir_run_id(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        state, response = runner.run(
            objective="research",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        report_path = Path(response["artifacts"]["research_report_md"])
        assert tmp_path.resolve() in report_path.parents
        assert state.run_id in str(report_path)

    def test_pipeline_id_in_artifacts(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        _state, response = runner.run(
            objective="research",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert response["artifacts"]["pipeline_id"] == "deep_research"

    def test_deep_research_does_not_produce_code_review_artifacts(self, tmp_path: Path):
        runner = self._make_runner(tmp_path)
        _state, response = runner.run(
            objective="research",
            target_repo="/tmp/repo",
            pipeline_id="deep_research",
        )
        assert "code_review_report_index" not in response["artifacts"]

    def test_code_review_does_not_produce_research_artifacts(self, tmp_path: Path):
        runner = self._make_ci_runner(tmp_path)
        _state, response = runner.run(
            objective="review",
            target_repo="/tmp/repo",
            pipeline_id="code_review",
        )
        assert "research_report_md" not in response["artifacts"]
