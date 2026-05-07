from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CapabilityType(Enum):
    ADAPTER = "adapter"
    SANDBOX_PROVIDER = "sandbox_provider"
    INDEXER = "indexer"
    PIPELINE_TEMPLATE = "pipeline_template"
    INTEGRATION_PROVIDER = "integration_provider"


VALID_RISK_TIERS = {"T1", "T2", "T3", "T4", "T5"}
VALID_STATUSES = {"verified", "quarantined", "disabled"}


@dataclass(frozen=True)
class CapabilityManifest:
    capability_id: str
    capability_type: CapabilityType
    version: str
    name: str
    description: str
    risk_tier: str
    requires_approval: bool = False
    network_access: bool = False
    writes_external_state: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "verified"
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "capability_type": self.capability_type.value,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "risk_tier": self.risk_tier,
            "requires_approval": self.requires_approval,
            "network_access": self.network_access,
            "writes_external_state": self.writes_external_state,
            "metadata": self.metadata,
            "status": self.status,
            "source_path": self.source_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityManifest:
        return cls(
            capability_id=str(data["capability_id"]),
            capability_type=CapabilityType(data["capability_type"]),
            version=str(data["version"]),
            name=str(data.get("name", data["capability_id"])),
            description=str(data.get("description", "")),
            risk_tier=str(data["risk_tier"]),
            requires_approval=bool(data.get("requires_approval", False)),
            network_access=bool(data.get("network_access", False)),
            writes_external_state=bool(data.get("writes_external_state", False)),
            metadata=dict(data.get("metadata", {})),
            status=str(data.get("status", "verified")),
            source_path=data.get("source_path"),
        )
