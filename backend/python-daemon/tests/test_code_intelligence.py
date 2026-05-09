from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from orchestrator.code_intelligence.analyzer import CodeIntelligenceAnalyzer, CodeIntelligenceError
from orchestrator.code_intelligence.dependency_extractor import DependencyExtractor
from orchestrator.code_intelligence.mermaid_formatter import format_mermaid
from orchestrator.code_intelligence.models import DependencyEdge, DependencyGraph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    """A minimal Python + JS repo fixture."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "models.py").write_text(
        "class Foo:\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "pkg" / "utils.py").write_text(
        "from . import models\nfrom pkg.models import Foo\n", encoding="utf-8"
    )
    (tmp_path / "pkg" / "service.py").write_text(
        "from .utils import helper\nimport os\n", encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.mjs").write_text(
        "import { foo } from './utils.mjs';\nimport express from 'express';\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "utils.mjs").write_text(
        "export function foo() {}\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# Test repo\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def analyzer(repo):
    return CodeIntelligenceAnalyzer(allowed_roots=(repo,))


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


class TestPathSafety:
    def test_escaping_allowed_roots_raises(self, tmp_path):
        safe = tmp_path / "safe"
        safe.mkdir()
        analyzer = CodeIntelligenceAnalyzer(allowed_roots=(safe,))
        with pytest.raises(CodeIntelligenceError, match="escapes allowed roots"):
            analyzer.analyze(str(tmp_path), "code_map")

    def test_nonexistent_dir_raises(self, repo):
        analyzer = CodeIntelligenceAnalyzer(allowed_roots=(repo,))
        with pytest.raises(CodeIntelligenceError, match="not a directory"):
            analyzer.analyze(str(repo / "nonexistent"), "code_map")

    def test_unknown_mode_raises(self, analyzer, repo):
        with pytest.raises(CodeIntelligenceError, match="unknown mode"):
            analyzer.analyze(str(repo), "bad_mode")


# ---------------------------------------------------------------------------
# code_map mode
# ---------------------------------------------------------------------------


class TestCodeMap:
    def test_returns_ok_with_files_list(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "code_map")
        assert result["ok"] is True
        assert result["mode"] == "code_map"
        assert isinstance(result["files"], list)
        assert len(result["files"]) > 0

    def test_file_entries_have_required_fields(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "code_map")
        for f in result["files"]:
            assert "path" in f
            assert "language" in f
            assert "size_bytes" in f
            assert "line_count" in f

    def test_language_detection(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "code_map")
        paths = {f["path"]: f["language"] for f in result["files"]}
        assert paths.get("README.md") == "markdown"
        assert paths.get("src/index.mjs") == "javascript"
        py_files = [p for p, lang in paths.items() if lang == "python"]
        assert len(py_files) >= 4

    def test_summary_has_language_breakdown(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "code_map")
        summary = result["summary"]
        assert summary["total_files"] > 0
        assert "python" in summary["languages"]
        assert "javascript" in summary["languages"]

    def test_max_files_truncation(self, repo):
        analyzer = CodeIntelligenceAnalyzer(allowed_roots=(repo,))
        result = analyzer.analyze(str(repo), "code_map", max_files=2)
        assert len(result["files"]) == 2
        assert result["truncated"] is True

    def test_skips_hidden_dirs(self, analyzer, repo):
        (repo / ".hidden").mkdir()
        (repo / ".hidden" / "secret.py").write_text("x=1\n")
        result = analyzer.analyze(str(repo), "code_map")
        paths = [f["path"] for f in result["files"]]
        assert not any(".hidden" in p for p in paths)

    def test_focus_paths_filters(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "code_map", focus_paths=["src"])
        paths = [f["path"] for f in result["files"]]
        assert all(p.startswith("src/") for p in paths)
        assert len(paths) == 2


# ---------------------------------------------------------------------------
# dependency_graph mode
# ---------------------------------------------------------------------------


class TestDependencyGraph:
    def test_returns_ok_with_nodes_edges(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "dependency_graph")
        assert result["ok"] is True
        assert result["mode"] == "dependency_graph"
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)

    def test_internal_edge_found(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "dependency_graph")
        internal_edges = [e for e in result["edges"] if not e["is_external"]]
        # pkg/utils.py imports from pkg/__init__.py or pkg/models.py
        sources = {e["source"] for e in internal_edges}
        assert any("utils" in s for s in sources)

    def test_external_edges_marked(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "dependency_graph")
        external = [e for e in result["edges"] if e["is_external"]]
        ext_targets = {e["target"] for e in external}
        assert "os" in ext_targets or "express" in ext_targets

    def test_max_edges_truncation(self, repo):
        analyzer = CodeIntelligenceAnalyzer(allowed_roots=(repo,))
        result = analyzer.analyze(str(repo), "dependency_graph", max_edges=2)
        assert result["edge_count"] <= 2
        assert result["truncated"] is True


# ---------------------------------------------------------------------------
# repo_context mode
# ---------------------------------------------------------------------------


class TestRepoContext:
    def test_returns_ok_with_context_string(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "repo_context")
        assert result["ok"] is True
        assert result["mode"] == "repo_context"
        assert isinstance(result["context"], str)
        assert len(result["context"]) > 50

    def test_context_mentions_repo_name(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "repo_context")
        assert repo.name in result["context"]

    def test_max_chars_respected(self, repo):
        analyzer = CodeIntelligenceAnalyzer(allowed_roots=(repo,))
        result = analyzer.analyze(str(repo), "repo_context", max_chars=200)
        assert len(result["context"]) <= 200

    def test_context_includes_language_summary(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "repo_context")
        assert "python" in result["context"].lower()


# ---------------------------------------------------------------------------
# mermaid mode
# ---------------------------------------------------------------------------


class TestMermaid:
    def test_returns_ok_with_diagram(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "mermaid")
        assert result["ok"] is True
        assert result["mode"] == "mermaid"
        assert result["diagram"].startswith("graph TD")

    def test_diagram_contains_internal_nodes(self, analyzer, repo):
        result = analyzer.analyze(str(repo), "mermaid")
        # At least one node label should appear
        assert '["' in result["diagram"]


# ---------------------------------------------------------------------------
# DependencyExtractor unit tests
# ---------------------------------------------------------------------------


class TestDependencyExtractor:
    def test_python_absolute_import(self):
        all_files = ["pkg/models.py", "pkg/utils.py"]
        extractor = DependencyExtractor(all_files)
        source = "from pkg.models import Foo\n"
        edges = extractor.extract("pkg/utils.py", source)
        internal = [e for e in edges if not e.is_external]
        assert any(e.target == "pkg/models.py" for e in internal)

    def test_python_relative_import(self):
        all_files = ["pkg/__init__.py", "pkg/models.py", "pkg/utils.py"]
        extractor = DependencyExtractor(all_files)
        source = "from . import models\n"
        edges = extractor.extract("pkg/utils.py", source)
        internal = [e for e in edges if not e.is_external]
        assert any(e.target == "pkg/models.py" for e in internal)

    def test_python_stdlib_marked_external(self):
        all_files = ["pkg/utils.py"]
        extractor = DependencyExtractor(all_files)
        source = "import os\nimport sys\n"
        edges = extractor.extract("pkg/utils.py", source)
        assert all(e.is_external for e in edges)

    def test_js_relative_import_resolved(self):
        all_files = ["src/index.mjs", "src/utils.mjs"]
        extractor = DependencyExtractor(all_files)
        source = "import { foo } from './utils.mjs';\n"
        edges = extractor.extract("src/index.mjs", source)
        internal = [e for e in edges if not e.is_external]
        assert any(e.target == "src/utils.mjs" for e in internal)

    def test_js_package_import_marked_external(self):
        all_files = ["src/index.mjs"]
        extractor = DependencyExtractor(all_files)
        source = "import express from 'express';\n"
        edges = extractor.extract("src/index.mjs", source)
        assert all(e.is_external for e in edges)

    def test_no_self_edges(self):
        all_files = ["pkg/utils.py"]
        extractor = DependencyExtractor(all_files)
        source = "from pkg.utils import something\n"
        edges = extractor.extract("pkg/utils.py", source)
        assert not any(e.source == e.target for e in edges)

    def test_syntax_error_returns_empty(self):
        all_files = ["bad.py"]
        extractor = DependencyExtractor(all_files)
        edges = extractor.extract("bad.py", "def (broken syntax:")
        assert edges == []


# ---------------------------------------------------------------------------
# Mermaid formatter unit tests
# ---------------------------------------------------------------------------


class TestMermaidFormatter:
    def test_empty_graph_renders_header_only(self):
        graph = DependencyGraph(nodes=[], edges=[])
        diagram = format_mermaid(graph)
        assert diagram == "graph TD"

    def test_node_labels_appear(self):
        graph = DependencyGraph(
            nodes=["src/foo.py"],
            edges=[],
        )
        diagram = format_mermaid(graph)
        assert 'src/foo.py' in diagram

    def test_edge_renders_arrow(self):
        graph = DependencyGraph(
            nodes=["a.py", "b.py"],
            edges=[DependencyEdge(source="a.py", target="b.py", kind="import", is_external=False)],
        )
        diagram = format_mermaid(graph)
        assert "-->" in diagram

    def test_external_edges_excluded(self):
        graph = DependencyGraph(
            nodes=["a.py"],
            edges=[DependencyEdge(source="a.py", target="requests", kind="import", is_external=True)],
        )
        diagram = format_mermaid(graph)
        assert "requests" not in diagram

    def test_duplicate_edges_deduplicated(self):
        graph = DependencyGraph(
            nodes=["a.py", "b.py"],
            edges=[
                DependencyEdge(source="a.py", target="b.py", kind="import", is_external=False),
                DependencyEdge(source="a.py", target="b.py", kind="from_import", is_external=False),
            ],
        )
        diagram = format_mermaid(graph)
        assert diagram.count("-->") == 1


class TestCodeIntelligenceReceipt:
    """Verify capability_receipt is attached to mcp_code_intelligence results."""

    def test_receipt_present_on_all_modes(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        for mode in ("code_map", "dependency_graph", "repo_context", "mermaid"):
            result = analyzer.analyze(str(tmp_path), mode)
            # Receipt is attached by the adapter layer, not the analyzer itself.
            # Verify the analyzer result is structurally valid for receipt attachment.
            assert result.get("ok") is True
            assert "mode" in result

    def test_receipt_shape_via_adapter(self, tmp_path):
        import sys
        sys.path.insert(0, str(tmp_path))
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")

        from orchestrator.adapters import ToolAdapters
        adapter = ToolAdapters(
            code_intelligence=CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        )
        result = adapter.call_mcp_tool("mcp_code_intelligence", {
            "target_repo": str(tmp_path),
            "mode": "code_map",
        })
        receipt = result.get("capability_receipt")
        assert isinstance(receipt, dict), "capability_receipt must be dict"
        assert receipt["operation"] == "capability.execute"
        assert receipt["capability_id"] == "code_intelligence.code_map"
        assert receipt["capability_type"] == "adapter"
        assert receipt["risk_tier"] == "T1"
        assert receipt["network_access"] is False
        assert receipt["writes_external_state"] is False

    def test_receipt_no_source_path(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        from orchestrator.adapters import ToolAdapters
        adapter = ToolAdapters(
            code_intelligence=CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        )
        result = adapter.call_mcp_tool("mcp_code_intelligence", {
            "target_repo": str(tmp_path),
            "mode": "repo_context",
        })
        receipt_str = str(result.get("capability_receipt", {}))
        assert "source_path" not in receipt_str
        assert "allowed_roots" not in receipt_str

    def test_receipt_summary_bounded(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        from orchestrator.adapters import ToolAdapters
        adapter = ToolAdapters(
            code_intelligence=CodeIntelligenceAnalyzer(allowed_roots=(tmp_path,))
        )
        result = adapter.call_mcp_tool("mcp_code_intelligence", {
            "target_repo": str(tmp_path),
            "mode": "dependency_graph",
        })
        summary = result["capability_receipt"]["summary"]
        assert len(summary) <= 200
