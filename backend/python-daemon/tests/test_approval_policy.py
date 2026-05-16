from __future__ import annotations

import pytest

from orchestrator.approvals.models import ApprovalDecision, ApprovalReceipt, ApprovalRequirement
from orchestrator.approvals.policy import (
    build_approval_receipt,
    evaluate_approval_requirement,
)


def _req(
    capability_id: str = "test.capability",
    risk_tier: str = "T1",
    writes_files: bool = False,
    network_access: bool = False,
    writes_external_state: bool = False,
) -> ApprovalRequirement:
    return ApprovalRequirement(
        capability_id=capability_id,
        risk_tier=risk_tier,
        reason="test",
        requested_action="test_action",
        writes_files=writes_files,
        network_access=network_access,
        writes_external_state=writes_external_state,
    )


class TestNotRequired:
    def test_t1_readonly_not_required(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1"))
        assert d.allowed is True
        assert d.status == "NOT_REQUIRED"

    def test_t2_readonly_not_required(self):
        d = evaluate_approval_requirement(_req(risk_tier="T2"))
        assert d.allowed is True
        assert d.status == "NOT_REQUIRED"

    def test_reason_nonempty(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1"))
        assert d.reason

    def test_approval_id_none_when_not_required(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1"))
        assert d.approval_id is None


class TestPendingApproval:
    def test_t3_requires_pending(self):
        d = evaluate_approval_requirement(_req(risk_tier="T3"))
        assert d.allowed is False
        assert d.status == "PENDING_APPROVAL"

    def test_t4_requires_pending(self):
        d = evaluate_approval_requirement(_req(risk_tier="T4"))
        assert d.allowed is False
        assert d.status == "PENDING_APPROVAL"

    def test_network_access_t1_requires_pending(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1", network_access=True))
        assert d.allowed is False
        assert d.status == "PENDING_APPROVAL"

    def test_writes_external_state_t1_requires_pending(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1", writes_external_state=True))
        assert d.allowed is False
        assert d.status == "PENDING_APPROVAL"

    def test_writes_files_t2_requires_pending(self):
        d = evaluate_approval_requirement(_req(risk_tier="T2", writes_files=True))
        assert d.allowed is False
        assert d.status == "PENDING_APPROVAL"

    def test_reason_contains_tier(self):
        d = evaluate_approval_requirement(_req(risk_tier="T3"))
        assert "T3" in d.reason

    def test_reason_contains_network_hint(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1", network_access=True))
        assert "network" in d.reason.lower()

    def test_reason_contains_files_hint(self):
        d = evaluate_approval_requirement(_req(risk_tier="T2", writes_files=True))
        assert "file" in d.reason.lower()

    def test_approval_id_none_when_pending(self):
        d = evaluate_approval_requirement(_req(risk_tier="T3"))
        assert d.approval_id is None


class TestApprovalModels:
    def test_requirement_frozen(self):
        req = _req()
        with pytest.raises((AttributeError, TypeError)):
            req.risk_tier = "T4"  # type: ignore[misc]

    def test_decision_frozen(self):
        d = evaluate_approval_requirement(_req(risk_tier="T1"))
        with pytest.raises((AttributeError, TypeError)):
            d.allowed = False  # type: ignore[misc]

    def test_receipt_to_dict_has_required_keys(self):
        req = _req(risk_tier="T3")
        decision = evaluate_approval_requirement(req)
        receipt = build_approval_receipt(req, decision)
        d = receipt.to_dict()
        assert set(d.keys()) >= {"capability_id", "status", "allowed", "reason", "approval_id", "risk_tier"}

    def test_receipt_reflects_decision(self):
        req = _req(risk_tier="T1")
        decision = evaluate_approval_requirement(req)
        receipt = build_approval_receipt(req, decision)
        assert receipt.allowed is True
        assert receipt.status == "NOT_REQUIRED"
        assert receipt.risk_tier == "T1"

    def test_receipt_pending_not_allowed(self):
        req = _req(risk_tier="T4")
        decision = evaluate_approval_requirement(req)
        receipt = build_approval_receipt(req, decision)
        assert receipt.allowed is False
        assert receipt.status == "PENDING_APPROVAL"
