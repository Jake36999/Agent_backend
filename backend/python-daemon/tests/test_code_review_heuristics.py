from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from orchestrator.code_intelligence.analyzer import (
    CodeIntelligenceAnalyzer,
    _compute_fan,
    _compute_orphans,
    _detect_entrypoints,
    _detect_test_dirs,
    _extract_externals,
    _scan_todo_fixme,
)
from orchestrator.code_intelligence.models import CodeMapEntry, DependencyEdge, DependencyGraph
from orchestrator.code_review.heuristics import CodeReviewHeuristics, extract_heuristics
from orchestrator.code_review.report_builder import build_code_review_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("# TODO: add more tests\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "from src import models, utils\nimport requests\n", encoding="utf-8"
    )
    (tmp_path / "src" / "models.py").write_text(
        "from src import utils\n# FIXME: incomplete\n", encoding="utf-8"
    )
    (tmp_path / "src" / "utils.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "src" / "orphan.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def analyzer(repo):
    return CodeIntelligenceAnalyzer(allowed_roots=(repo,))


# ---------------------------------------------------------------------------
# Analyzer enriched artifacts: repo_context mode
# ---------------------------------------------------------------------------


class TestRepoContextEnrichedArtifacts:
    def test_largest_files_json_present(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        assert "largest_files_json" in r["artifacts"]

    def test_largest_files_json_sorted_descending(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        files = json.loads(r["artifacts"]["largest_files_json"])
        counts = [f["line_count"] for f in files]
        assert counts == sorted(counts, reverse=True)

    def test_largest_files_bounded_to_20(self, tmp_path):
        for i in range(30):
            (tmp_path / f"file_{i}.py").write_text(f"x = {i}\n" * (i + 1), encoding="utf-8")
        a = CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        r = a.analyze(str(tmp_path), "repo_context")
        files = json.loads(r["artifacts"]["largest_files_json"])
        assert len(files) <= 20

    def test_test_dirs_json_detects_tests_dir(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        dirs = json.loads(r["artifacts"]["test_dirs_json"])
        assert "tests" in dirs

    def test_entrypoints_json_detects_main_py(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        eps = json.loads(r["artifacts"]["entrypoints_json"])
        assert any("main.py" in ep for ep in eps)

    def test_todo_fixme_json_detects_markers(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        todos = json.loads(r["artifacts"]["todo_fixme_json"])
        assert len(todos) > 0
        paths = [t["path"] for t in todos]
        assert any("test_main.py" in p or "models.py" in p for p in paths)

    def test_todo_fixme_sorted_by_count_descending(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        todos = json.loads(r["artifacts"]["todo_fixme_json"])
        counts = [t["count"] for t in todos]
        assert counts == sorted(counts, reverse=True)

    def test_todo_fixme_includes_kinds(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        todos = json.loads(r["artifacts"]["todo_fixme_json"])
        for t in todos:
            assert isinstance(t["kinds"], list)
            assert len(t["kinds"]) > 0

    def test_code_map_summary_produced_by_repo_context(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "repo_context")
        summary = r["artifacts"].get("code_map_summary", "")
        assert "files" in summary
        assert "lines" in summary

    def test_large_file_skipped_in_todo_scan(self, tmp_path):
        big = tmp_path / "big.py"
        big.write_bytes(b"# TODO: something\n" + b"x" * 1_000_001)
        a = CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        r = a.analyze(str(tmp_path), "repo_context")
        todos = json.loads(r["artifacts"]["todo_fixme_json"])
        assert not any("big.py" in t["path"] for t in todos)


# ---------------------------------------------------------------------------
# Analyzer enriched artifacts: dependency_graph mode
# ---------------------------------------------------------------------------


class TestDependencyGraphEnrichedArtifacts:
    def test_fan_in_json_present(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        assert "fan_in_json" in r["artifacts"]

    def test_fan_out_json_present(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        assert "fan_out_json" in r["artifacts"]

    def test_orphans_json_present(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        assert "orphans_json" in r["artifacts"]

    def test_external_deps_json_present(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        assert "external_deps_json" in r["artifacts"]

    def test_fan_in_sorted_descending(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        fi = json.loads(r["artifacts"]["fan_in_json"])
        counts = [d["count"] for d in fi]
        assert counts == sorted(counts, reverse=True)

    def test_fan_out_sorted_descending(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        fo = json.loads(r["artifacts"]["fan_out_json"])
        counts = [d["count"] for d in fo]
        assert counts == sorted(counts, reverse=True)

    def test_external_deps_includes_requests(self, analyzer, repo):
        r = analyzer.analyze(str(repo), "dependency_graph")
        deps = json.loads(r["artifacts"]["external_deps_json"])
        assert "requests" in deps or "os" in deps


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------


class TestComputeFan:
    def _edges(self, pairs):
        return [
            DependencyEdge(source=s, target=t, kind="import", is_external=False)
            for s, t in pairs
        ]

    def test_fan_in_counts_incoming_edges(self):
        edges = self._edges([("a.py", "c.py"), ("b.py", "c.py"), ("d.py", "c.py")])
        fi, fo = _compute_fan(edges)
        c_fan_in = next(d for d in fi if d["path"] == "c.py")
        assert c_fan_in["count"] == 3

    def test_fan_out_counts_outgoing_edges(self):
        edges = self._edges([("a.py", "b.py"), ("a.py", "c.py"), ("a.py", "d.py")])
        fi, fo = _compute_fan(edges)
        a_fan_out = next(d for d in fo if d["path"] == "a.py")
        assert a_fan_out["count"] == 3

    def test_external_edges_excluded(self):
        edges = [
            DependencyEdge(source="a.py", target="os", kind="import", is_external=True),
            DependencyEdge(source="a.py", target="b.py", kind="import", is_external=False),
        ]
        fi, fo = _compute_fan(edges)
        assert not any(d["path"] == "os" for d in fi + fo)

    def test_fan_in_sorted_descending(self):
        edges = self._edges([
            ("a.py", "z.py"), ("b.py", "z.py"),
            ("c.py", "y.py"),
        ])
        fi, _ = _compute_fan(edges)
        counts = [d["count"] for d in fi]
        assert counts == sorted(counts, reverse=True)

    def test_bounded_to_20(self):
        edges = self._edges([(f"src_{i}.py", "hub.py") for i in range(30)])
        fi, _ = _compute_fan(edges)
        assert len(fi) <= 20


class TestComputeOrphans:
    def test_orphan_has_no_edges(self):
        graph = DependencyGraph(
            nodes=["a.py", "b.py", "orphan.py"],
            edges=[DependencyEdge(source="a.py", target="b.py", kind="import", is_external=False)],
        )
        orphans = _compute_orphans(graph)
        assert "orphan.py" in orphans
        assert "a.py" not in orphans
        assert "b.py" not in orphans

    def test_empty_graph_all_nodes_are_orphans(self):
        graph = DependencyGraph(nodes=["a.py", "b.py"], edges=[])
        orphans = _compute_orphans(graph)
        assert set(orphans) == {"a.py", "b.py"}

    def test_bounded_to_20(self):
        graph = DependencyGraph(nodes=[f"f{i}.py" for i in range(30)], edges=[])
        orphans = _compute_orphans(graph)
        assert len(orphans) <= 20


class TestDetectTestDirs:
    def _entries(self, paths):
        return [CodeMapEntry(rel_path=p, language="python", size_bytes=0, line_count=1) for p in paths]

    def test_detects_tests_dir(self):
        entries = self._entries(["tests/test_foo.py", "src/main.py"])
        dirs = _detect_test_dirs(entries)
        assert "tests" in dirs

    def test_detects_nested_test_dir(self):
        entries = self._entries(["backend/tests/test_api.py"])
        dirs = _detect_test_dirs(entries)
        assert "backend/tests" in dirs

    def test_no_false_positive_on_test_in_filename(self):
        entries = self._entries(["src/test_utils.py"])
        dirs = _detect_test_dirs(entries)
        assert not dirs

    def test_bounded_to_20(self):
        entries = self._entries([f"test_{i}/x.py" for i in range(30)])
        dirs = _detect_test_dirs(entries)
        assert len(dirs) <= 20


class TestDetectEntrypoints:
    def _entries(self, paths):
        return [CodeMapEntry(rel_path=p, language="python", size_bytes=0, line_count=1) for p in paths]

    def test_detects_main_py(self):
        entries = self._entries(["src/main.py", "src/utils.py"])
        eps = _detect_entrypoints(entries)
        assert "src/main.py" in eps

    def test_detects_app_py(self):
        entries = self._entries(["app.py"])
        eps = _detect_entrypoints(entries)
        assert "app.py" in eps

    def test_does_not_flag_arbitrary_files(self):
        entries = self._entries(["src/database.py"])
        eps = _detect_entrypoints(entries)
        assert not eps


# ---------------------------------------------------------------------------
# extract_heuristics integration
# ---------------------------------------------------------------------------


class TestExtractHeuristics:
    def _step_outputs(self, *, fan_in=None, largest=None, todos=None, test_dirs=None, externals=None, entrypoints=None):
        return {
            "repo_context": {
                "ok": True,
                "artifacts": {
                    "repo_context_md": "# Repo",
                    "largest_files_json": json.dumps(largest or []),
                    "test_dirs_json": json.dumps(test_dirs or []),
                    "entrypoints_json": json.dumps(entrypoints or []),
                    "todo_fixme_json": json.dumps(todos or []),
                },
            },
            "dependency_graph": {
                "ok": True,
                "artifacts": {
                    "dependency_graph_summary": "2 nodes, 1 edge",
                    "fan_in_json": json.dumps(fan_in or []),
                    "fan_out_json": json.dumps([]),
                    "orphans_json": json.dumps([]),
                    "external_deps_json": json.dumps(externals or []),
                },
            },
        }

    def test_returns_code_review_heuristics(self):
        h = extract_heuristics(self._step_outputs())
        assert isinstance(h, CodeReviewHeuristics)

    def test_largest_files_populated(self):
        largest = [{"path": "big.py", "line_count": 500}, {"path": "small.py", "line_count": 10}]
        h = extract_heuristics(self._step_outputs(largest=largest))
        assert len(h.largest_files) == 2
        assert h.largest_files[0].path == "big.py"
        assert h.largest_files[0].line_count == 500

    def test_fan_in_populated(self):
        fi = [{"path": "hub.py", "count": 8}]
        h = extract_heuristics(self._step_outputs(fan_in=fi))
        assert h.highest_fan_in[0].path == "hub.py"
        assert h.highest_fan_in[0].count == 8

    def test_test_directories_populated(self):
        h = extract_heuristics(self._step_outputs(test_dirs=["tests", "backend/tests"]))
        assert "tests" in h.test_directories

    def test_external_deps_populated(self):
        h = extract_heuristics(self._step_outputs(externals=["requests", "flask"]))
        assert "requests" in h.external_dependencies
        assert "flask" in h.external_dependencies

    def test_todo_fixme_kinds_are_tuple(self):
        todos = [{"path": "main.py", "count": 3, "kinds": ["FIXME", "TODO"]}]
        h = extract_heuristics(self._step_outputs(todos=todos))
        assert isinstance(h.todo_fixme_counts[0].kinds, tuple)

    def test_empty_step_outputs_returns_empty_heuristics(self):
        h = extract_heuristics({})
        assert h.largest_files == ()
        assert h.highest_fan_in == ()
        assert h.external_dependencies == ()

    def test_malformed_json_falls_back_to_empty(self):
        outputs = {
            "repo_context": {
                "ok": True,
                "artifacts": {"largest_files_json": "not valid json {{{"},
            }
        }
        h = extract_heuristics(outputs)
        assert h.largest_files == ()

    def test_missing_path_entries_skipped(self):
        largest = [{"line_count": 100}, {"path": "ok.py", "line_count": 50}]
        h = extract_heuristics(self._step_outputs(largest=largest))
        assert len(h.largest_files) == 1
        assert h.largest_files[0].path == "ok.py"


# ---------------------------------------------------------------------------
# Report builder with real heuristics
# ---------------------------------------------------------------------------


class TestReportBuilderWithHeuristics:
    def _build_with_heuristics(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_core.py").write_text("# TODO: fill in\n", encoding="utf-8")
        (tmp_path / "orchestrator").mkdir()
        (tmp_path / "orchestrator" / "main.py").write_text(
            "from orchestrator import models\nimport requests\n", encoding="utf-8"
        )
        (tmp_path / "orchestrator" / "models.py").write_text(
            "from orchestrator import utils\n# FIXME: stub\n", encoding="utf-8"
        )
        (tmp_path / "orchestrator" / "utils.py").write_text("x = 1\n", encoding="utf-8")

        a = CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        repo_ctx = a.analyze(str(tmp_path), "repo_context")
        dep_graph = a.analyze(str(tmp_path), "dependency_graph")
        mermaid = a.analyze(str(tmp_path), "mermaid")

        step_outputs = {
            "repo_context": {
                "ok": True, "status": "COMPLETE", "summary": "ok",
                "artifacts": repo_ctx["artifacts"],
                "error": None,
            },
            "dependency_graph": {
                "ok": True, "status": "COMPLETE", "summary": "ok",
                "artifacts": dep_graph["artifacts"],
                "error": None,
            },
            "mermaid": {
                "ok": True, "status": "COMPLETE", "summary": "ok",
                "artifacts": mermaid["artifacts"],
                "error": None,
            },
        }
        return build_code_review_report(
            target_repo=str(tmp_path),
            step_outputs=step_outputs,
        )

    def test_architecture_overview_includes_largest_files(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        assert "Largest Files" in r.architecture_overview_md

    def test_architecture_overview_includes_test_dir(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        assert "tests" in r.architecture_overview_md

    def test_architecture_overview_includes_entrypoint(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        assert "main.py" in r.architecture_overview_md

    def test_summary_includes_heuristic_signals(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        # External deps, TODO counts, or fan-in must appear — at least one signal present
        has_signal = any(kw in r.code_review_summary_md for kw in ("External", "Fan-in", "TODO"))
        assert has_signal

    def test_summary_includes_external_deps(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        assert "requests" in r.code_review_summary_md or "External" in r.code_review_summary_md

    def test_next_actions_contains_file_specific_items(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        parsed = yaml.safe_load(r.next_actions_yaml)
        assert "suggested_followups" in parsed
        items = parsed["suggested_followups"]
        assert isinstance(items, list)
        assert len(items) > 0
        assert any(isinstance(item, dict) and "id" in item for item in items)

    def test_next_actions_file_specific_items_have_signal(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        parsed = yaml.safe_load(r.next_actions_yaml)
        items = parsed["suggested_followups"]
        for item in items:
            assert "signal" in item

    def test_next_actions_no_forbidden_language(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        for forbidden in ("vulnerability", "bug", "security risk", "severity", "critical"):
            assert forbidden not in r.next_actions_yaml.lower()

    def test_heuristics_json_contains_real_data(self, tmp_path):
        import json
        r = self._build_with_heuristics(tmp_path)
        data = json.loads(r.heuristics_json)
        assert len(data["largest_files"]) > 0
        assert len(data["test_directories"]) > 0

    def test_report_bounds_respected(self, tmp_path):
        r = self._build_with_heuristics(tmp_path)
        assert len(r.architecture_overview_md) <= 10000
        assert len(r.dependency_graph_mmd) <= 12000
        assert len(r.code_review_summary_md) <= 8000
        assert len(r.next_actions_yaml) <= 6000
        assert len(r.heuristics_json) <= 6000
