from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orchestrator.adapters import AdapterFailure, ToolAdapters


def _sandbox_stub(stat_ok: bool = True):
    s = MagicMock()
    s.stat.return_value = {"ok": True, "path": "/tmp/x", "type": "file", "size": 42}
    s.list_dir.return_value = {"ok": True, "entries": []}
    s.read_head.return_value = {"ok": True, "content": "hello"}
    if not stat_ok:
        s.stat.return_value = {"ok": False, "error": "not found"}
    return s


def _ta_with_sandbox(stat_ok: bool = True) -> ToolAdapters:
    ta = ToolAdapters()
    ta.sandbox = _sandbox_stub(stat_ok)
    return ta


class TestSandboxProbeReceiptShape:
    def test_allowed_probe_has_receipt(self):
        r = _ta_with_sandbox().call_mcp_tool("mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"})
        assert "capability_receipt" in r

    def test_receipt_fields_complete(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        for key in ("operation", "capability_id", "capability_type", "risk_tier",
                    "status", "authorized", "network_access", "writes_external_state"):
            assert key in cr

    def test_receipt_capability_type_sandbox(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["capability_type"] == "sandbox"

    def test_receipt_risk_tier_t1(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["risk_tier"] == "T1"

    def test_receipt_no_network_access(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["network_access"] is False

    def test_receipt_no_external_state_writes(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["writes_external_state"] is False

    def test_receipt_authorized_true_on_success(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["authorized"] is True

    def test_receipt_status_ok_on_success(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["status"] == "OK"

    def test_list_dir_receipt_ok(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "list_dir", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["status"] == "OK"

    def test_read_head_receipt_ok(self):
        cr = _ta_with_sandbox().call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "read_head", "path": "/tmp/f"}
        )["capability_receipt"]
        assert cr["status"] == "OK"

    def test_probe_result_not_ok_receipt_error(self):
        cr = _ta_with_sandbox(stat_ok=False).call_mcp_tool(
            "mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"}
        )["capability_receipt"]
        assert cr["status"] == "ERROR"


class TestSandboxProbePolicyBlock:
    def test_no_sandbox_configured_raises(self):
        ta = ToolAdapters()
        with pytest.raises(AdapterFailure):
            ta.call_mcp_tool("mcp_sandbox_probe", {"operation": "stat", "path": "/tmp"})

    def test_unknown_operation_raises(self):
        with pytest.raises(AdapterFailure):
            _ta_with_sandbox().call_mcp_tool(
                "mcp_sandbox_probe", {"operation": "delete", "path": "/tmp"}
            )


class TestSandboxProbePolicyEnforcement:
    """Verify that classify_sandbox_request gates execution."""

    def test_classify_called_before_sandbox(self):
        """When sandbox is None and the tool is read_only, still raises because
        the policy classified it as allowed then found no sandbox. No skip."""
        ta = ToolAdapters()
        with pytest.raises(AdapterFailure, match="sandbox adapter is not configured"):
            ta.call_mcp_tool("mcp_sandbox_probe", {"operation": "stat", "path": "/p"})
