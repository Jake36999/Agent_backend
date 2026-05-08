from __future__ import annotations

import pytest

from orchestrator.capabilities.receipt import (
    CapabilityExecutionReceipt,
    build_receipt,
    compact_receipt,
)


class TestBuildReceipt:
    def test_minimal_valid_receipt(self):
        r = build_receipt(
            capability_id="code_intelligence.repo_context",
            capability_type="adapter",
            risk_tier="T1",
            summary="ok",
        )
        assert isinstance(r, CapabilityExecutionReceipt)
        assert r.operation == "capability.execute"
        assert r.capability_id == "code_intelligence.repo_context"
        assert r.risk_tier == "T1"
        assert r.authorized is True
        assert r.network_access is False
        assert r.writes_external_state is False
        assert r.approval_id is None

    def test_invalid_risk_tier_raises(self):
        with pytest.raises(ValueError, match="risk_tier"):
            build_receipt(capability_id="x", capability_type="adapter", risk_tier="T9")

    def test_invalid_capability_type_raises(self):
        with pytest.raises(ValueError, match="capability_type"):
            build_receipt(capability_id="x", capability_type="unknown", risk_tier="T1")

    def test_summary_capped_at_200_chars(self):
        r = build_receipt(
            capability_id="x", capability_type="adapter", risk_tier="T1",
            summary="s" * 300,
        )
        assert len(r.summary) == 200

    def test_artifact_refs_capped_at_20(self):
        r = build_receipt(
            capability_id="x", capability_type="adapter", risk_tier="T1",
            artifact_refs=[f"ref_{i}" for i in range(30)],
        )
        assert len(r.artifact_refs) == 20

    def test_each_artifact_ref_capped_at_120_chars(self):
        r = build_receipt(
            capability_id="x", capability_type="adapter", risk_tier="T1",
            artifact_refs=["a" * 200],
        )
        assert len(r.artifact_refs[0]) == 120

    def test_capability_id_capped_at_120_chars(self):
        r = build_receipt(
            capability_id="x" * 200, capability_type="adapter", risk_tier="T1",
        )
        assert len(r.capability_id) == 120

    def test_t1_read_only_fields(self):
        r = build_receipt(
            capability_id="code_intelligence.code_map",
            capability_type="adapter",
            risk_tier="T1",
        )
        assert r.network_access is False
        assert r.writes_external_state is False
        assert r.approval_id is None

    def test_pipeline_t2_writes_external_state(self):
        r = build_receipt(
            capability_id="pipeline.investigation",
            capability_type="pipeline",
            risk_tier="T2",
            writes_external_state=True,
        )
        assert r.writes_external_state is True
        assert r.risk_tier == "T2"


class TestCompactReceipt:
    def _receipt(self, **kwargs) -> CapabilityExecutionReceipt:
        defaults = dict(capability_id="x", capability_type="adapter", risk_tier="T1")
        defaults.update(kwargs)
        return build_receipt(**defaults)

    def test_compact_returns_dict_with_required_keys(self):
        d = compact_receipt(self._receipt())
        required = {
            "operation", "capability_id", "capability_type", "risk_tier", "status",
            "authorized", "network_access", "writes_external_state",
            "approval_id", "artifact_refs", "summary",
        }
        assert required.issubset(d.keys())

    def test_operation_is_capability_execute(self):
        d = compact_receipt(self._receipt())
        assert d["operation"] == "capability.execute"

    def test_no_source_path_in_compact(self):
        r = self._receipt(capability_id="code_intelligence.code_map", artifact_refs=["result_key"])
        d = compact_receipt(r)
        serialized = str(d)
        assert "source_path" not in serialized
        assert "allowed_roots" not in serialized

    def test_artifact_refs_is_list(self):
        r = self._receipt(artifact_refs=["a", "b"])
        d = compact_receipt(r)
        assert isinstance(d["artifact_refs"], list)
        assert d["artifact_refs"] == ["a", "b"]

    def test_compact_is_json_serializable(self):
        import json
        r = self._receipt(
            capability_id="pipeline.investigation",
            capability_type="pipeline",
            risk_tier="T2",
            writes_external_state=True,
            artifact_refs=["session_path"],
            summary="Executed investigation pipeline (5 steps, 5 complete).",
        )
        d = compact_receipt(r)
        payload = json.dumps(d)
        assert "capability.execute" in payload
