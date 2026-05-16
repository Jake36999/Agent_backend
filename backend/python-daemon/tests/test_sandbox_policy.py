from __future__ import annotations

import pytest

from orchestrator.sandbox.policy import (
    SandboxDecision,
    _KNOWN_RISK_LEVELS,
    classify_sandbox_request,
)


class TestVerdictTable:
    """read_only / write_memory → allow in safe; write_files → require_approval; admin → block."""

    def test_read_only_safe_allows(self):
        d = classify_sandbox_request("mcp_code_intelligence", {}, "safe")
        assert d.verdict == "allow"
        assert d.allowed is True
        assert d.risk_tier == "T1"

    def test_write_memory_safe_allows(self):
        d = classify_sandbox_request("mcp_commit_memory", {}, "safe")
        assert d.verdict == "allow"
        assert d.risk_tier == "T2"

    def test_write_files_safe_requires_approval(self):
        d = classify_sandbox_request("mcp_ingest_target", {}, "safe")
        assert d.verdict == "require_approval"
        assert d.allowed is False
        assert d.risk_tier == "T3"

    def test_admin_safe_blocks(self):
        d = classify_sandbox_request("mcp_set_active_project_manual", {}, "safe")
        assert d.verdict == "block"
        assert d.allowed is False
        assert d.risk_tier == "T4"

    def test_write_files_trusted_allows(self):
        d = classify_sandbox_request("mcp_ingest_target", {}, "trusted")
        assert d.verdict == "allow"
        assert d.allowed is True

    def test_admin_trusted_requires_approval(self):
        d = classify_sandbox_request("mcp_set_active_project_manual", {}, "trusted")
        assert d.verdict == "require_approval"

    def test_read_only_trusted_allows(self):
        d = classify_sandbox_request("mcp_sandbox_probe", {}, "trusted")
        assert d.verdict == "allow"


class TestUnknownInputs:
    def test_unknown_tool_blocks(self):
        d = classify_sandbox_request("mcp_nonexistent_xyz", {})
        assert d.verdict == "block"
        assert d.risk_tier == "UNKNOWN"
        assert "unknown tool" in d.reason

    def test_unknown_profile_treated_as_safe(self):
        # write_files in unknown profile → safe → require_approval
        d = classify_sandbox_request("mcp_ingest_target", {}, "god_mode")
        assert d.verdict == "require_approval"

    def test_explicit_risk_level_overrides_lookup(self):
        # Force a write_files verdict for a normally read_only tool
        d = classify_sandbox_request("mcp_code_intelligence", {}, "safe", risk_level="write_files")
        assert d.verdict == "require_approval"
        assert d.risk_tier == "T3"

    def test_explicit_unknown_risk_level_blocks(self):
        d = classify_sandbox_request("mcp_code_intelligence", {}, "safe", risk_level="super_write")
        assert d.verdict == "block"
        assert d.risk_tier == "UNKNOWN"


class TestDecisionFields:
    def test_tool_name_preserved(self):
        d = classify_sandbox_request("mcp_scout_workspace", {})
        assert d.tool_name == "mcp_scout_workspace"

    def test_requires_root_passed_through(self):
        d = classify_sandbox_request("mcp_scout_workspace", {}, requires_root=True)
        assert d.requires_root is True

    def test_requires_root_default_false(self):
        d = classify_sandbox_request("mcp_scout_workspace", {})
        assert d.requires_root is False

    def test_reason_nonempty(self):
        d = classify_sandbox_request("mcp_code_intelligence", {}, "safe")
        assert d.reason

    def test_dataclass_frozen(self):
        d = classify_sandbox_request("mcp_code_intelligence", {}, "safe")
        with pytest.raises((AttributeError, TypeError)):
            d.verdict = "block"  # type: ignore[misc]


class TestKnownRiskLevelsRegistry:
    def test_sandbox_probe_is_read_only(self):
        assert _KNOWN_RISK_LEVELS["mcp_sandbox_probe"] == "read_only"

    def test_agent_workflow_is_read_only(self):
        assert _KNOWN_RISK_LEVELS["mcp_agent_workflow_run"] == "read_only"

    def test_ingest_is_write_files(self):
        assert _KNOWN_RISK_LEVELS["mcp_ingest_target"] == "write_files"

    def test_admin_tool_is_admin(self):
        assert _KNOWN_RISK_LEVELS["mcp_set_active_project_manual"] == "admin"
