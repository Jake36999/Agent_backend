from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.sandbox.local_adapter import LocalSandboxAdapter, SandboxError


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def adapter(root: Path) -> LocalSandboxAdapter:
    return LocalSandboxAdapter((root,))


class TestStat:
    def test_stat_existing_file(self, adapter: LocalSandboxAdapter, root: Path):
        f = root / "hello.txt"
        f.write_text("hi", encoding="utf-8")
        result = adapter.stat(str(f))
        assert result["ok"] is True
        assert result["is_file"] is True
        assert result["is_dir"] is False
        assert result["size_bytes"] == 2

    def test_stat_existing_dir(self, adapter: LocalSandboxAdapter, root: Path):
        d = root / "subdir"
        d.mkdir()
        result = adapter.stat(str(d))
        assert result["ok"] is True
        assert result["is_dir"] is True

    def test_stat_missing_returns_not_found(self, adapter: LocalSandboxAdapter, root: Path):
        result = adapter.stat(str(root / "nope.txt"))
        assert result["ok"] is False
        assert result["status"] == "NOT_FOUND"

    def test_stat_escaping_root_raises(self, adapter: LocalSandboxAdapter, tmp_path: Path):
        outside = tmp_path.parent / "secret.txt"
        outside.write_text("secret", encoding="utf-8")
        with pytest.raises(SandboxError, match="allowed roots"):
            adapter.stat(str(outside))


class TestListDir:
    def test_lists_directory_entries(self, adapter: LocalSandboxAdapter, root: Path):
        (root / "a.py").write_text("", encoding="utf-8")
        (root / "b.py").write_text("", encoding="utf-8")
        result = adapter.list_dir(str(root))
        assert result["ok"] is True
        assert "a.py" in result["entries"]
        assert "b.py" in result["entries"]

    def test_list_dir_sorted(self, adapter: LocalSandboxAdapter, root: Path):
        for name in ["z.py", "a.py", "m.py"]:
            (root / name).write_text("", encoding="utf-8")
        result = adapter.list_dir(str(root))
        assert result["entries"] == sorted(result["entries"])

    def test_max_entries_cap(self, adapter: LocalSandboxAdapter, root: Path):
        for i in range(10):
            (root / f"f{i}.py").write_text("", encoding="utf-8")
        result = adapter.list_dir(str(root), max_entries=3)
        assert len(result["entries"]) == 3
        assert result["truncated"] is True
        assert result["total_available"] == 10

    def test_not_a_dir_returns_error(self, adapter: LocalSandboxAdapter, root: Path):
        f = root / "file.txt"
        f.write_text("x", encoding="utf-8")
        result = adapter.list_dir(str(f))
        assert result["ok"] is False
        assert result["status"] == "NOT_A_DIRECTORY"

    def test_escape_raises(self, adapter: LocalSandboxAdapter, tmp_path: Path):
        with pytest.raises(SandboxError):
            adapter.list_dir(str(tmp_path.parent))


class TestReadHead:
    def test_reads_file_content(self, adapter: LocalSandboxAdapter, root: Path):
        f = root / "data.txt"
        f.write_text("hello world", encoding="utf-8")
        result = adapter.read_head(str(f))
        assert result["ok"] is True
        assert result["content"] == "hello world"

    def test_respects_max_bytes(self, adapter: LocalSandboxAdapter, root: Path):
        f = root / "big.txt"
        f.write_bytes(b"A" * 200)
        result = adapter.read_head(str(f), max_bytes=10)
        assert result["ok"] is True
        assert result["bytes_read"] == 10
        assert result["truncated"] is True

    def test_not_a_file_returns_error(self, adapter: LocalSandboxAdapter, root: Path):
        result = adapter.read_head(str(root))
        assert result["ok"] is False
        assert result["status"] == "NOT_A_FILE"

    def test_missing_file_returns_not_a_file(self, adapter: LocalSandboxAdapter, root: Path):
        result = adapter.read_head(str(root / "gone.txt"))
        assert result["ok"] is False

    def test_escape_raises(self, adapter: LocalSandboxAdapter, tmp_path: Path):
        with pytest.raises(SandboxError):
            adapter.read_head(str(tmp_path.parent / "secret"))

    def test_binary_content_decoded_with_replacement(self, adapter: LocalSandboxAdapter, root: Path):
        f = root / "bin.dat"
        f.write_bytes(bytes(range(256)))
        result = adapter.read_head(str(f), max_bytes=256)
        assert result["ok"] is True
        assert isinstance(result["content"], str)


class TestAdapterInToolAdapters:
    def test_mcp_sandbox_probe_stat(self, tmp_path: Path):
        from orchestrator.adapters import ToolAdapters
        f = tmp_path / "probe.txt"
        f.write_text("hi", encoding="utf-8")
        adapter = LocalSandboxAdapter((tmp_path,))
        ta = ToolAdapters(sandbox=adapter)
        result = ta.call_mcp_tool("mcp_sandbox_probe", {"path": str(f), "operation": "stat"})
        assert result["ok"] is True
        assert result["is_file"] is True

    def test_mcp_sandbox_probe_list_dir(self, tmp_path: Path):
        from orchestrator.adapters import ToolAdapters
        (tmp_path / "x.py").write_text("", encoding="utf-8")
        adapter = LocalSandboxAdapter((tmp_path,))
        ta = ToolAdapters(sandbox=adapter)
        result = ta.call_mcp_tool("mcp_sandbox_probe", {"path": str(tmp_path), "operation": "list_dir"})
        assert result["ok"] is True
        assert "x.py" in result["entries"]

    def test_mcp_sandbox_probe_read_head(self, tmp_path: Path):
        from orchestrator.adapters import ToolAdapters
        f = tmp_path / "r.txt"
        f.write_text("content", encoding="utf-8")
        adapter = LocalSandboxAdapter((tmp_path,))
        ta = ToolAdapters(sandbox=adapter)
        result = ta.call_mcp_tool("mcp_sandbox_probe", {"path": str(f), "operation": "read_head"})
        assert result["ok"] is True
        assert "content" in result["content"]

    def test_mcp_sandbox_probe_missing_raises(self, tmp_path: Path):
        from orchestrator.adapters import AdapterFailure, ToolAdapters
        ta = ToolAdapters()
        with pytest.raises(AdapterFailure, match="sandbox adapter"):
            ta.call_mcp_tool("mcp_sandbox_probe", {"path": str(tmp_path), "operation": "stat"})

    def test_mcp_sandbox_probe_unknown_operation_raises(self, tmp_path: Path):
        from orchestrator.adapters import AdapterFailure, ToolAdapters
        adapter = LocalSandboxAdapter((tmp_path,))
        ta = ToolAdapters(sandbox=adapter)
        with pytest.raises(AdapterFailure, match="unknown sandbox operation"):
            ta.call_mcp_tool("mcp_sandbox_probe", {"path": str(tmp_path), "operation": "write"})
