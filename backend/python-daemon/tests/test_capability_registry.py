from __future__ import annotations

import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import pytest

from orchestrator.capabilities.models import CapabilityManifest, CapabilityType
from orchestrator.capabilities.registry import CapabilityRegistry
from orchestrator.capabilities.schema import CapabilitySchemaError, validate_capability_manifest
from orchestrator.capabilities.policy import enforce_capability_policy, CapabilityPolicyError
from orchestrator.db_bootstrap import bootstrap_databases


@pytest.fixture
def db_path(tmp_path):
    bootstrap_databases(tmp_path)
    return tmp_path / "queue.db"


@pytest.fixture
def registry(db_path):
    return CapabilityRegistry(db_path)


def _sample_manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="test.adapter.v1",
        capability_type=CapabilityType.ADAPTER,
        version="1.0.0",
        name="Test Adapter",
        description="A test adapter",
        risk_tier="T1",
    )
    defaults.update(overrides)
    return CapabilityManifest(**defaults)


class TestCapabilityRegistry:
    def test_upsert_and_get(self, registry):
        manifest = _sample_manifest()
        registry.upsert(manifest)
        loaded = registry.get("test.adapter.v1")
        assert loaded is not None
        assert loaded.capability_id == "test.adapter.v1"
        assert loaded.capability_type == CapabilityType.ADAPTER
        assert loaded.version == "1.0.0"
        assert loaded.risk_tier == "T1"

    def test_upsert_overwrites_existing(self, registry):
        registry.upsert(_sample_manifest(version="1.0.0"))
        registry.upsert(_sample_manifest(version="2.0.0"))
        loaded = registry.get("test.adapter.v1")
        assert loaded.version == "2.0.0"

    def test_get_nonexistent_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_list_all(self, registry):
        registry.upsert(_sample_manifest(capability_id="a"))
        registry.upsert(_sample_manifest(capability_id="b"))
        all_caps = registry.list_all()
        assert len(all_caps) == 2
        assert {c.capability_id for c in all_caps} == {"a", "b"}

    def test_list_by_type(self, registry):
        registry.upsert(_sample_manifest(capability_id="adapter1", capability_type=CapabilityType.ADAPTER))
        registry.upsert(_sample_manifest(capability_id="pipeline1", capability_type=CapabilityType.PIPELINE_TEMPLATE))
        adapters = registry.list_all(capability_type=CapabilityType.ADAPTER)
        assert len(adapters) == 1
        assert adapters[0].capability_id == "adapter1"

    def test_list_by_status(self, registry):
        registry.upsert(_sample_manifest(capability_id="a", status="verified"))
        registry.upsert(_sample_manifest(capability_id="b", status="quarantined"))
        verified = registry.list_all(status="verified")
        assert len(verified) == 1
        assert verified[0].capability_id == "a"

    def test_quarantine(self, registry):
        registry.upsert(_sample_manifest())
        result = registry.quarantine("test.adapter.v1", "safety concern")
        assert result is True
        loaded = registry.get("test.adapter.v1")
        assert loaded.status == "quarantined"

    def test_disable_and_enable(self, registry):
        registry.upsert(_sample_manifest())
        registry.disable("test.adapter.v1")
        assert registry.get("test.adapter.v1").status == "disabled"
        registry.enable("test.adapter.v1")
        assert registry.get("test.adapter.v1").status == "verified"

    def test_delete(self, registry):
        registry.upsert(_sample_manifest())
        assert registry.delete("test.adapter.v1") is True
        assert registry.get("test.adapter.v1") is None

    def test_delete_nonexistent_returns_false(self, registry):
        assert registry.delete("nonexistent") is False

    def test_to_dict_roundtrip(self):
        manifest = _sample_manifest(metadata={"key": "value"})
        data = manifest.to_dict()
        restored = CapabilityManifest.from_dict(data)
        assert restored.capability_id == manifest.capability_id
        assert restored.metadata == {"key": "value"}


class TestCapabilitySchema:
    def test_valid_manifest_passes(self):
        data = _sample_manifest().to_dict()
        errors = validate_capability_manifest(data)
        assert errors == []

    def test_missing_fields_detected(self):
        errors = validate_capability_manifest({})
        assert any("missing required fields" in e for e in errors)

    def test_invalid_risk_tier_detected(self):
        data = _sample_manifest().to_dict()
        data["risk_tier"] = "INVALID"
        errors = validate_capability_manifest(data)
        assert any("risk_tier" in e for e in errors)

    def test_invalid_type_detected(self):
        data = _sample_manifest().to_dict()
        data["capability_type"] = "invalid_type"
        errors = validate_capability_manifest(data)
        assert any("capability_type" in e for e in errors)

    def test_invalid_status_detected(self):
        data = _sample_manifest().to_dict()
        data["status"] = "bad_status"
        errors = validate_capability_manifest(data)
        assert any("status" in e for e in errors)


class TestCapabilityPolicy:
    def test_verified_t1_passes(self):
        enforce_capability_policy(_sample_manifest())

    def test_quarantined_raises(self):
        manifest = _sample_manifest(status="quarantined")
        with pytest.raises(CapabilityPolicyError, match="quarantined"):
            enforce_capability_policy(manifest)

    def test_disabled_raises(self):
        manifest = _sample_manifest(status="disabled")
        with pytest.raises(CapabilityPolicyError, match="disabled"):
            enforce_capability_policy(manifest)

    def test_t3_without_approval_raises(self):
        manifest = _sample_manifest(risk_tier="T3", requires_approval=False)
        with pytest.raises(CapabilityPolicyError, match="requires_approval"):
            enforce_capability_policy(manifest)

    def test_t3_with_approval_passes(self):
        manifest = _sample_manifest(risk_tier="T3", requires_approval=True)
        enforce_capability_policy(manifest)

    def test_writes_external_without_approval_raises(self):
        manifest = _sample_manifest(writes_external_state=True, requires_approval=False)
        with pytest.raises(CapabilityPolicyError, match="writes external state"):
            enforce_capability_policy(manifest)

    def test_writes_external_with_approval_passes(self):
        manifest = _sample_manifest(writes_external_state=True, requires_approval=True)
        enforce_capability_policy(manifest)

    def test_t4_without_approval_raises(self):
        manifest = _sample_manifest(risk_tier="T4", requires_approval=False)
        with pytest.raises(CapabilityPolicyError, match="requires_approval"):
            enforce_capability_policy(manifest)

    def test_t5_without_approval_raises(self):
        manifest = _sample_manifest(risk_tier="T5", requires_approval=False)
        with pytest.raises(CapabilityPolicyError, match="requires_approval"):
            enforce_capability_policy(manifest)

    def test_t4_with_approval_passes(self):
        manifest = _sample_manifest(risk_tier="T4", requires_approval=True)
        enforce_capability_policy(manifest)

    def test_t2_without_approval_passes(self):
        manifest = _sample_manifest(risk_tier="T2", requires_approval=False)
        enforce_capability_policy(manifest)
