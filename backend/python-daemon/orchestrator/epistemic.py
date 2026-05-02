from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EpistemicSignals:
    logic_signal: float
    sycophancy_signal: float


@dataclass(frozen=True)
class EpistemicScore:
    slr_score: float
    depth_penalty: float
    final_score: float
    decision: str


@dataclass(frozen=True)
class EpistemicPolicy:
    minor_threshold: float = 0.22
    major_threshold: float = 0.35
    depth_penalty: float = 1.35

    def score(self, signals: EpistemicSignals, *, base_score: float, depth: int) -> EpistemicScore:
        slr_score = signals.sycophancy_signal / max(signals.logic_signal, 1e-6)
        penalty = depth * self.depth_penalty
        final_score = base_score - penalty
        if slr_score >= self.major_threshold:
            decision = "identity_freeze"
        elif slr_score >= self.minor_threshold:
            decision = "reroll"
        else:
            decision = "route"
        return EpistemicScore(
            slr_score=slr_score,
            depth_penalty=penalty,
            final_score=final_score,
            decision=decision,
        )
