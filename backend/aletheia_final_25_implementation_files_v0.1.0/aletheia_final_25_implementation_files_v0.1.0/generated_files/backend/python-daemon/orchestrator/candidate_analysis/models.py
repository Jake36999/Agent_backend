from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CandidateAnalysisInput:
    objective: str
    target_repo: str
    logs: str | None = None
    failing_test_output: str | None = None
    manifest_csv: str | None = None
    workspace_summary: str | None = None
    rag_context: str | None = None
    max_candidates: int = 10


@dataclass(frozen=True)
class RankedCandidate:
    rank: int
    path: str
    score: float
    confidence: float
    evidence: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    test_seams: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "path": self.path,
            "score": self.score,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "risk_notes": list(self.risk_notes),
            "test_seams": list(self.test_seams),
        }
