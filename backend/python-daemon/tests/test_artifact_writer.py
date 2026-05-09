from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.code_review.artifact_writer import (
    _MAX_ARTIFACT_BYTES,
    persist_code_review_artifacts,
)
from orchestrator.code_review.models import CodeReviewReport


def _minimal_report(**overrides: str) -> CodeReviewReport:
    defaults = {
        "architecture_overview_md": "# Overview\nSmall repo.",
        "dependency_graph_mmd": "graph TD\n  a --> b",
        "code_review_summary_md": "# Summary\nAll clear.",
        "next_actions_yaml": "suggested_followups:\n  - id: test",
        "heuristics_json": json.dumps({"largest_files": []}),
        "artifact_index": {"architecture_overview_md": "architecture_overview_md"},
    }
    defaults.update(overrides)
    return CodeReviewReport(**defaults)


class TestPersistCodeReviewArtifacts:
    def test_creates_artifact_directory(self, tmp_path: Path):
        report = _minimal_report()
        refs = persist_code_review_artifacts(report, "run-1", tmp_path)
        assert (tmp_path / "run-1").is_dir()
        assert len(refs) == 5

    def test_returns_absolute_paths(self, tmp_path: Path):
        report = _minimal_report()
        refs = persist_code_review_artifacts(report, "run-2", tmp_path)
        for key, path_str in refs.items():
            p = Path(path_str)
            assert p.is_absolute()
            assert p.exists()

    def test_correct_file_extensions(self, tmp_path: Path):
        report = _minimal_report()
        refs = persist_code_review_artifacts(report, "run-3", tmp_path)
        assert refs["architecture_overview_md"].endswith(".md")
        assert refs["dependency_graph_mmd"].endswith(".mmd")
        assert refs["code_review_summary_md"].endswith(".md")
        assert refs["next_actions_yaml"].endswith(".yaml")
        assert refs["heuristics_json"].endswith(".json")

    def test_file_content_matches_report(self, tmp_path: Path):
        report = _minimal_report()
        refs = persist_code_review_artifacts(report, "run-4", tmp_path)
        content = Path(refs["architecture_overview_md"]).read_text(encoding="utf-8")
        assert content == report.architecture_overview_md

    def test_empty_artifact_skipped(self, tmp_path: Path):
        report = _minimal_report(dependency_graph_mmd="")
        refs = persist_code_review_artifacts(report, "run-5", tmp_path)
        assert "dependency_graph_mmd" not in refs
        assert not (tmp_path / "run-5" / "dependency_graph_mmd.mmd").exists()

    def test_large_artifact_truncated_at_byte_limit(self, tmp_path: Path):
        huge = "x" * (_MAX_ARTIFACT_BYTES + 10000)
        report = _minimal_report(architecture_overview_md=huge)
        refs = persist_code_review_artifacts(report, "run-6", tmp_path)
        written = Path(refs["architecture_overview_md"]).stat().st_size
        assert written <= _MAX_ARTIFACT_BYTES

    def test_nested_run_id_with_uuid(self, tmp_path: Path):
        run_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        report = _minimal_report()
        refs = persist_code_review_artifacts(report, run_id, tmp_path)
        assert (tmp_path / run_id).is_dir()
        assert len(refs) == 5

    def test_idempotent_overwrite(self, tmp_path: Path):
        report = _minimal_report()
        persist_code_review_artifacts(report, "run-7", tmp_path)
        report2 = _minimal_report(architecture_overview_md="# Updated")
        refs2 = persist_code_review_artifacts(report2, "run-7", tmp_path)
        content = Path(refs2["architecture_overview_md"]).read_text(encoding="utf-8")
        assert content == "# Updated"

    def test_heuristics_json_is_valid_json(self, tmp_path: Path):
        h = json.dumps({"largest_files": [{"path": "a.py", "line_count": 100}]})
        report = _minimal_report(heuristics_json=h)
        refs = persist_code_review_artifacts(report, "run-8", tmp_path)
        data = json.loads(Path(refs["heuristics_json"]).read_text(encoding="utf-8"))
        assert data["largest_files"][0]["path"] == "a.py"
