from __future__ import annotations

import pytest

from orchestrator.integrations.models import (
    COMPOSIO_CAPABILITY,
    RUBE_CAPABILITY,
    KNOWN_INTEGRATION_TYPES,
    _bounded_params,
)
from orchestrator.integrations.policy import classify_integration_request
from orchestrator.integrations.adapters import (
    ComposioAdapter,
    RubeAdapter,
    IntegrationError,
    get_adapter,
)


# ---------------------------------------------------------------------------
# Models / constants
# ---------------------------------------------------------------------------

class TestCapabilityDescriptors:
    def test_composio_is_t4(self):
        assert COMPOSIO_CAPABILITY["risk_tier"] == "T4"

    def test_composio_requires_approval(self):
        assert COMPOSIO_CAPABILITY["requires_approval"] is True

    def test_composio_writes_external_state(self):
        assert COMPOSIO_CAPABILITY["writes_external_state"] is True

    def test_composio_disabled_by_default(self):
        assert COMPOSIO_CAPABILITY["status"] == "disabled"

    def test_rube_is_t4(self):
        assert RUBE_CAPABILITY["risk_tier"] == "T4"

    def test_rube_disabled_by_default(self):
        assert RUBE_CAPABILITY["status"] == "disabled"

    def test_known_types_contains_composio_and_rube(self):
        assert "composio" in KNOWN_INTEGRATION_TYPES
        assert "rube" in KNOWN_INTEGRATION_TYPES


class TestBoundedParams:
    def test_string_values_truncated(self):
        result = _bounded_params({"key_name": "x" * 500})
        assert len(result["key_name"]) <= 200

    def test_sensitive_keys_redacted(self):
        for sensitive in ("api_key", "secret", "token", "password", "auth"):
            result = _bounded_params({sensitive: "my-secret-value"})
            assert result[sensitive] == "[redacted]"

    def test_non_string_passed_through(self):
        result = _bounded_params({"count": 42, "flag": True})
        assert result["count"] == 42
        assert result["flag"] is True

    def test_max_params_capped(self):
        big = {f"p{i}": str(i) for i in range(50)}
        result = _bounded_params(big)
        assert len(result) <= 20

    def test_non_sensitive_string_preserved(self):
        result = _bounded_params({"repo": "my-repo", "mode": "dry_run"})
        assert result["repo"] == "my-repo"


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class TestClassifyIntegrationRequest:
    def test_dry_run_composio_allowed(self):
        d = classify_integration_request("composio", "send_email", dry_run=True)
        assert d.allowed is True
        assert d.verdict == "allow"
        assert d.risk_tier == "T2"
        assert d.dry_run is True

    def test_dry_run_rube_allowed(self):
        d = classify_integration_request("rube", "create_ticket", dry_run=True)
        assert d.allowed is True
        assert d.risk_tier == "T2"

    def test_live_composio_blocked(self):
        d = classify_integration_request("composio", "send_email", dry_run=False)
        assert d.allowed is False
        assert d.verdict == "block"
        assert d.risk_tier == "T4"

    def test_live_rube_blocked(self):
        d = classify_integration_request("rube", "create_ticket", dry_run=False)
        assert d.allowed is False
        assert d.risk_tier == "T4"

    def test_unknown_integration_blocked(self):
        d = classify_integration_request("zapier", "trigger", dry_run=True)
        assert d.allowed is False
        assert d.verdict == "block"
        assert d.risk_tier == "UNKNOWN"
        assert "unknown" in d.reason

    def test_reason_nonempty(self):
        d = classify_integration_request("composio", "x", dry_run=True)
        assert d.reason

    def test_integration_type_preserved(self):
        d = classify_integration_request("rube", "x", dry_run=True)
        assert d.integration_type == "rube"

    def test_dry_run_field_preserved(self):
        d = classify_integration_request("composio", "x", dry_run=True)
        assert d.dry_run is True

    def test_profile_does_not_affect_dry_run_verdict(self):
        for profile in ("safe", "trusted", "god_mode"):
            d = classify_integration_request("composio", "x", dry_run=True, profile=profile)
            assert d.allowed is True


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

class TestComposioAdapter:
    def test_dry_run_returns_ok(self):
        r = ComposioAdapter().invoke("send_email", {"to": "test@example.com"}, dry_run=True)
        assert r["ok"] is True
        assert r["dry_run"] is True

    def test_would_call_contains_action(self):
        r = ComposioAdapter().invoke("send_email", {}, dry_run=True)
        assert "composio.send_email" in r["would_call"]

    def test_integration_type_in_result(self):
        r = ComposioAdapter().invoke("x", {}, dry_run=True)
        assert r["integration_type"] == "composio"

    def test_params_preview_present(self):
        r = ComposioAdapter().invoke("x", {"mode": "fast"}, dry_run=True)
        assert "params_preview" in r
        assert r["params_preview"]["mode"] == "fast"

    def test_dry_run_note_present(self):
        r = ComposioAdapter().invoke("x", {}, dry_run=True)
        assert "no external call" in r["note"]

    def test_live_invocation_raises(self):
        with pytest.raises(IntegrationError, match="not yet enabled"):
            ComposioAdapter().invoke("x", {}, dry_run=False)

    def test_action_truncated_at_cap(self):
        long_action = "a" * 200
        r = ComposioAdapter().invoke(long_action, {}, dry_run=True)
        assert len(r["would_call"]) < 200

    def test_sensitive_params_redacted(self):
        r = ComposioAdapter().invoke("x", {"api_key": "secret123"}, dry_run=True)
        assert r["params_preview"]["api_key"] == "[redacted]"


class TestRubeAdapter:
    def test_dry_run_returns_ok(self):
        r = RubeAdapter().invoke("create_ticket", {"title": "Bug"}, dry_run=True)
        assert r["ok"] is True
        assert r["dry_run"] is True

    def test_would_call_contains_action(self):
        r = RubeAdapter().invoke("create_ticket", {}, dry_run=True)
        assert "rube.create_ticket" in r["would_call"]

    def test_live_invocation_raises(self):
        with pytest.raises(IntegrationError, match="not yet enabled"):
            RubeAdapter().invoke("x", {}, dry_run=False)

    def test_integration_type_in_result(self):
        r = RubeAdapter().invoke("x", {}, dry_run=True)
        assert r["integration_type"] == "rube"


class TestGetAdapter:
    def test_returns_composio_adapter(self):
        assert isinstance(get_adapter("composio"), ComposioAdapter)

    def test_returns_rube_adapter(self):
        assert isinstance(get_adapter("rube"), RubeAdapter)

    def test_unknown_raises(self):
        with pytest.raises(IntegrationError, match="no adapter"):
            get_adapter("zapier")


# ---------------------------------------------------------------------------
# ToolAdapters integration
# ---------------------------------------------------------------------------

class TestMcpIntegrationInvokeDispatch:
    def _ta(self):
        from orchestrator.adapters import ToolAdapters
        return ToolAdapters()

    def test_dry_run_composio_allowed(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "composio",
            "action": "send_email",
            "dry_run": True,
        })
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert "integration_receipt" in result

    def test_dry_run_rube_allowed(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "rube",
            "action": "create_ticket",
            "dry_run": True,
        })
        assert result["ok"] is True

    def test_live_composio_policy_blocked(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "composio",
            "action": "send_email",
            "dry_run": False,
        })
        assert result["ok"] is False
        assert result["status"] == "POLICY_BLOCK"
        assert "integration_receipt" in result

    def test_unknown_integration_policy_blocked(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "zapier",
            "action": "trigger",
            "dry_run": True,
        })
        assert result["ok"] is False
        assert result["status"] == "POLICY_BLOCK"

    def test_receipt_has_expected_fields(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "composio",
            "action": "x",
            "dry_run": True,
        })
        r = result["integration_receipt"]
        assert r["operation"] == "capability.execute"
        assert r["capability_type"] == "integration"
        assert r["risk_tier"] == "T2"
        assert r["authorized"] is True
        assert r["writes_external_state"] is False

    def test_blocked_receipt_not_authorized(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "composio",
            "action": "x",
            "dry_run": False,
        })
        r = result["integration_receipt"]
        assert r["authorized"] is False
        assert r["status"] == "POLICY_BLOCK"

    def test_params_forwarded(self):
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "composio",
            "action": "x",
            "params": {"subject": "Hello"},
            "dry_run": True,
        })
        assert result["params_preview"]["subject"] == "Hello"

    def test_default_dry_run_is_true(self):
        # omitting dry_run defaults to True
        result = self._ta().call_mcp_tool("mcp_integration_invoke", {
            "integration_type": "composio",
            "action": "x",
        })
        assert result["ok"] is True


class TestReceiptCapabilityType:
    def test_integration_is_valid_capability_type(self):
        from orchestrator.capabilities.receipt import build_receipt
        r = build_receipt(
            capability_id="integration.composio",
            capability_type="integration",
            risk_tier="T2",
            status="OK",
            authorized=True,
            network_access=False,
            writes_external_state=False,
            summary="dry-run test",
        )
        assert r.capability_type == "integration"

    def test_unknown_type_still_raises(self):
        from orchestrator.capabilities.receipt import build_receipt
        with pytest.raises(ValueError, match="capability_type"):
            build_receipt(
                capability_id="x",
                capability_type="external_magic",
                risk_tier="T1",
            )
