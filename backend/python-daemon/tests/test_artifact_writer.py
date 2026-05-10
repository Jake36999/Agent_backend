from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from orchestrator.code_review.artifact_writer import (
    _MANIFEST_FILENAME,
    _MAX_ARTIFACT_BYTES,
    _ARTIFACT_FILES,
    _safe_artifact_dir,
    build_report_index,
    persist_code_review_artifacts,
    persist_draft_review,
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


class TestSafeArtifactDir:
    def test_creates_directory(self, tmp_path: Path):
        d = _safe_artifact_dir(tmp_path, "run-1")
        assert d.is_dir()

    def test_resolves_under_state_dir(self, tmp_path: Path):
        d = _safe_artifact_dir(tmp_path, "run-abc")
        assert str(d).startswith(str(tmp_path.resolve()))

    def test_rejects_traversal_in_run_id(self, tmp_path: Path):
        with pytest.raises(ValueError, match="escapes state_dir"):
            _safe_artifact_dir(tmp_path, "../../etc")


class TestPersistCodeReviewArtifacts:
    def test_creates_artifact_directory(self, tmp_path: Path):
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, "run-1", tmp_path)
        assert (tmp_path / "run-1").is_dir()
        assert len(refs) == 5

    def test_returns_absolute_paths(self, tmp_path: Path):
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, "run-2", tmp_path)
        for path_str in refs.values():
            p = Path(path_str)
            assert p.is_absolute()
            assert p.exists()

    def test_paths_stay_under_state_dir(self, tmp_path: Path):
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, "run-3", tmp_path)
        resolved_state = tmp_path.resolve()
        for path_str in refs.values():
            p = Path(path_str).resolve()
            assert str(p).startswith(str(resolved_state)), f"{p} escapes {resolved_state}"

    def test_filenames_are_fixed_constants(self, tmp_path: Path):
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, "run-4", tmp_path)
        for key, path_str in refs.items():
            expected_filename = _ARTIFACT_FILES[key][0]
            assert Path(path_str).name == expected_filename

    def test_correct_file_extensions(self, tmp_path: Path):
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, "run-5", tmp_path)
        assert refs["architecture_overview_md"].endswith(".md")
        assert refs["dependency_graph_mmd"].endswith(".mmd")
        assert refs["code_review_summary_md"].endswith(".md")
        assert refs["next_actions_yaml"].endswith(".yaml")
        assert refs["heuristics_json"].endswith(".json")

    def test_file_content_matches_report(self, tmp_path: Path):
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, "run-6", tmp_path)
        content = Path(refs["architecture_overview_md"]).read_text(encoding="utf-8")
        assert content == report.architecture_overview_md

    def test_empty_artifact_skipped(self, tmp_path: Path):
        report = _minimal_report(dependency_graph_mmd="")
        refs, _ = persist_code_review_artifacts(report, "run-7", tmp_path)
        assert "dependency_graph_mmd" not in refs
        assert not (tmp_path / "run-7" / "dependency_graph.mmd").exists()

    def test_large_artifact_truncated_at_byte_limit(self, tmp_path: Path):
        huge = "x" * (_MAX_ARTIFACT_BYTES + 10000)
        report = _minimal_report(architecture_overview_md=huge)
        refs, _ = persist_code_review_artifacts(report, "run-8", tmp_path)
        written = Path(refs["architecture_overview_md"]).stat().st_size
        assert written <= _MAX_ARTIFACT_BYTES

    def test_idempotent_overwrite(self, tmp_path: Path):
        report = _minimal_report()
        persist_code_review_artifacts(report, "run-9", tmp_path)
        report2 = _minimal_report(architecture_overview_md="# Updated")
        refs2, _ = persist_code_review_artifacts(report2, "run-9", tmp_path)
        content = Path(refs2["architecture_overview_md"]).read_text(encoding="utf-8")
        assert content == "# Updated"

    def test_heuristics_json_is_valid_json(self, tmp_path: Path):
        h = json.dumps({"largest_files": [{"path": "a.py", "line_count": 100}]})
        report = _minimal_report(heuristics_json=h)
        refs, _ = persist_code_review_artifacts(report, "run-10", tmp_path)
        data = json.loads(Path(refs["heuristics_json"]).read_text(encoding="utf-8"))
        assert data["largest_files"][0]["path"] == "a.py"

    def test_nested_run_id_with_uuid(self, tmp_path: Path):
        run_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        report = _minimal_report()
        refs, _ = persist_code_review_artifacts(report, run_id, tmp_path)
        assert (tmp_path / run_id).is_dir()
        assert len(refs) == 5


class TestManifest:
    def test_manifest_file_written(self, tmp_path: Path):
        report = _minimal_report()
        persist_code_review_artifacts(report, "run-m1", tmp_path)
        assert (tmp_path / "run-m1" / _MANIFEST_FILENAME).exists()

    def test_manifest_is_valid_json(self, tmp_path: Path):
        report = _minimal_report()
        persist_code_review_artifacts(report, "run-m2", tmp_path)
        raw = (tmp_path / "run-m2" / _MANIFEST_FILENAME).read_text(encoding="utf-8")
        data = json.loads(raw)
        assert "artifacts" in data
        assert "run_id" in data

    def test_manifest_contains_sha256(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-m3", tmp_path)
        for entry in manifest_entries.values():
            assert "sha256" in entry
            assert len(entry["sha256"]) == 64  # hex sha256

    def test_manifest_sha256_is_correct(self, tmp_path: Path):
        content = "# Test content"
        report = _minimal_report(architecture_overview_md=content)
        _, manifest_entries = persist_code_review_artifacts(report, "run-m4", tmp_path)
        entry = manifest_entries["architecture_overview_md"]
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert entry["sha256"] == expected

    def test_manifest_contains_byte_size(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-m5", tmp_path)
        for entry in manifest_entries.values():
            assert "bytes" in entry
            assert isinstance(entry["bytes"], int)
            assert entry["bytes"] > 0

    def test_manifest_contains_created_at(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-m6", tmp_path)
        for entry in manifest_entries.values():
            assert "created_at" in entry
            assert "T" in entry["created_at"]  # ISO 8601

    def test_manifest_contains_content_type(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-m7", tmp_path)
        assert manifest_entries["heuristics_json"]["content_type"] == "application/json"
        assert manifest_entries["architecture_overview_md"]["content_type"] == "text/markdown"

    def test_manifest_relative_path_has_no_directory_component(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-m8", tmp_path)
        for entry in manifest_entries.values():
            assert "/" not in entry["relative_path"]
            assert "\\" not in entry["relative_path"]

    def test_manifest_no_absolute_target_repo_path(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-m9", tmp_path)
        manifest_str = json.dumps(manifest_entries)
        assert "/target/repo" not in manifest_str
        assert "C:\\" not in manifest_str


class TestBuildReportIndex:
    def test_returns_dict_with_path_sha256_bytes(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-i1", tmp_path)
        index = build_report_index(manifest_entries)
        for key, entry in index.items():
            assert "path" in entry
            assert "sha256" in entry
            assert "bytes" in entry

    def test_index_keys_match_artifact_keys(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-i2", tmp_path)
        index = build_report_index(manifest_entries)
        assert set(index.keys()) == set(manifest_entries.keys())

    def test_index_path_is_filename_only(self, tmp_path: Path):
        report = _minimal_report()
        _, manifest_entries = persist_code_review_artifacts(report, "run-i3", tmp_path)
        index = build_report_index(manifest_entries)
        for entry in index.values():
            assert "/" not in entry["path"]
            assert "\\" not in entry["path"]

    def test_empty_manifest_returns_empty_index(self):
        assert build_report_index({}) == {}


class TestPersistDraftReview:
    def test_writes_file(self, tmp_path: Path):
        path = persist_draft_review("## Draft\nGood repo.", "run-d1", tmp_path)
        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8") == "## Draft\nGood repo."

    def test_file_named_review_draft_md(self, tmp_path: Path):
        path = persist_draft_review("content", "run-d2", tmp_path)
        assert Path(path).name == "review_draft.md"

    def test_path_under_state_dir(self, tmp_path: Path):
        path = persist_draft_review("content", "run-d3", tmp_path)
        assert str(Path(path).resolve()).startswith(str(tmp_path.resolve()))
