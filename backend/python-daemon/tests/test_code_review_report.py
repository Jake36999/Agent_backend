from __future__ import annotations

import yaml

import pytest

from orchestrator.code_review.report_builder import (
    _bounded,
    _extract_dependency_counts,
    _extract_mermaid,
    _extract_repo_context,
    build_code_review_report,
)
from orchestrator.code_review.models import CodeReviewReport


_STEP_OUTPUTS = {
    "repo_context": {
        "ok": True,
        "artifacts": {
            "repo_context_md": "# Repo Context: my_repo\n\n10 files, 1,000 lines\n## Languages\n- python: 8",
            "code_map_summary": "10 files, 1,000 lines | python:8, yaml:2",
        },
    },
    "dependency_graph": {
        "ok": True,
        "artifacts": {
            "dependency_graph_summary": "5 nodes, 8 edges",
        },
    },
    "mermaid": {
        "ok": True,
        "artifacts": {
            "dependency_graph_mmd": "graph TD\n  a.py --> b.py",
        },
    },
}


class TestBounded:
    def test_short_text_unchanged(self):
        assert _bounded("hello", 100) == "hello"

    def test_long_text_truncated_with_marker(self):
        result = _bounded("x" * 200, 100)
        assert result.endswith("...[truncated]")
        assert len(result) == 100

    def test_exact_cap_unchanged(self):
        text = "a" * 100
        assert _bounded(text, 100) == text


class TestExtractors:
    def test_extract_repo_context(self):
        v = _extract_repo_context(_STEP_OUTPUTS)
        assert "Repo Context" in v

    def test_extract_mermaid(self):
        v = _extract_mermaid(_STEP_OUTPUTS)
        assert "graph TD" in v

    def test_extract_dependency_counts(self):
        v = _extract_dependency_counts(_STEP_OUTPUTS)
        assert "5 nodes" in v

    def test_extract_missing_step_returns_empty(self):
        assert _extract_repo_context({}) == ""
        assert _extract_mermaid({}) == ""
        assert _extract_dependency_counts({}) == ""


class TestBuildCodeReviewReport:
    def _build(self, step_outputs=None, target_repo="/tmp/my_repo", receipt=None):
        return build_code_review_report(
            target_repo=target_repo,
            step_outputs=step_outputs or _STEP_OUTPUTS,
            pipeline_receipt=receipt,
        )

    def test_returns_code_review_report_instance(self):
        assert isinstance(self._build(), CodeReviewReport)

    def test_all_five_fields_populated(self):
        r = self._build()
        assert r.architecture_overview_md
        assert r.dependency_graph_mmd
        assert r.code_review_summary_md
        assert r.next_actions_yaml
        assert r.heuristics_json

    def test_architecture_overview_includes_repo_name(self):
        r = self._build(target_repo="/tmp/my_repo")
        assert "my_repo" in r.architecture_overview_md

    def test_architecture_overview_has_read_only_disclaimer(self):
        r = self._build()
        assert "read-only" in r.architecture_overview_md.lower() or "No files were modified" in r.architecture_overview_md

    def test_dependency_graph_mmd_contains_diagram(self):
        r = self._build()
        assert "graph TD" in r.dependency_graph_mmd

    def test_mermaid_fallback_when_empty(self):
        outputs = {k: v for k, v in _STEP_OUTPUTS.items() if k != "mermaid"}
        r = self._build(step_outputs=outputs)
        assert "graph TD" in r.dependency_graph_mmd  # fallback placeholder

    def test_summary_md_includes_no_files_modified(self):
        r = self._build()
        assert "No files modified" in r.code_review_summary_md

    def test_summary_md_includes_repo_name(self):
        r = self._build(target_repo="/tmp/my_repo")
        assert "my_repo" in r.code_review_summary_md

    def test_next_actions_parseable_as_yaml(self):
        r = self._build()
        parsed = yaml.safe_load(r.next_actions_yaml)
        assert "suggested_followups" in parsed

    def test_next_actions_no_llm_critique_language(self):
        r = self._build()
        for forbidden in ("vulnerability", "bug", "security risk", "severity", "critical"):
            assert forbidden not in r.next_actions_yaml.lower()

    def test_next_actions_uses_neutral_wording(self):
        r = self._build()
        assert "candidate follow-up" in r.next_actions_yaml

    def test_artifact_index_contains_all_keys(self):
        r = self._build()
        expected = {"architecture_overview_md", "dependency_graph_mmd", "code_review_summary_md", "next_actions_yaml", "heuristics_json"}
        assert expected.issubset(r.artifact_index.keys())

    def test_architecture_overview_bounded(self):
        big_context = "x" * 20000
        outputs = {
            "repo_context": {"ok": True, "artifacts": {"repo_context_md": big_context, "code_map_summary": ""}},
            "dependency_graph": {"ok": True, "artifacts": {"dependency_graph_summary": ""}},
            "mermaid": {"ok": True, "artifacts": {"dependency_graph_mmd": "graph TD"}},
        }
        r = self._build(step_outputs=outputs)
        assert len(r.architecture_overview_md) <= 10000

    def test_dependency_graph_mmd_bounded(self):
        big_diagram = "graph TD\n" + "  a --> b\n" * 5000
        outputs = dict(_STEP_OUTPUTS)
        outputs["mermaid"] = {"ok": True, "artifacts": {"dependency_graph_mmd": big_diagram}}
        r = self._build(step_outputs=outputs)
        assert len(r.dependency_graph_mmd) <= 12000

    def test_summary_md_bounded(self):
        big_ctx = "line content\n" * 2000
        outputs = dict(_STEP_OUTPUTS)
        outputs["repo_context"] = {"ok": True, "artifacts": {"repo_context_md": big_ctx, "code_map_summary": ""}}
        r = self._build(step_outputs=outputs)
        assert len(r.code_review_summary_md) <= 8000

    def test_next_actions_bounded(self):
        r = self._build()
        assert len(r.next_actions_yaml) <= 6000

    def test_heuristics_json_parseable(self):
        import json
        r = self._build()
        parsed = json.loads(r.heuristics_json)
        assert "largest_files" in parsed
        assert "highest_fan_in" in parsed
        assert "external_dependencies" in parsed
        assert "test_directories" in parsed

    def test_heuristics_json_bounded(self):
        r = self._build()
        assert len(r.heuristics_json) <= 6000

    def test_receipt_info_included_in_summary(self):
        receipt = {"capability_id": "pipeline.code_review", "risk_tier": "T2"}
        r = self._build(receipt=receipt)
        assert "pipeline.code_review" in r.code_review_summary_md

    def test_empty_step_outputs_produces_valid_report(self):
        r = self._build(step_outputs={})
        assert isinstance(r, CodeReviewReport)
        assert r.architecture_overview_md
        assert r.next_actions_yaml
