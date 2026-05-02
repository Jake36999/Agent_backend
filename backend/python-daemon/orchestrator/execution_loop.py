from __future__ import annotations

from typing import Any

from .adapters import AdapterFailure, ToolAdapters
from .epistemic import EpistemicPolicy, EpistemicSignals
from .queue_repo import QueueRepository
from .reroll import ValidationFailure


class ExecutionLoop:
    def __init__(
        self,
        repo: QueueRepository,
        *,
        policy: EpistemicPolicy | None = None,
        max_rerolls: int = 2,
        tool_adapters: ToolAdapters | None = None,
    ) -> None:
        self.repo = repo
        self.policy = policy or EpistemicPolicy()
        self.max_rerolls = max_rerolls
        self.tool_adapters = tool_adapters or ToolAdapters()

    def score_before_routing(
        self,
        task_id: str,
        signals: EpistemicSignals,
        *,
        base_score: float,
        depth: int,
    ) -> dict[str, Any]:
        score = self.policy.score(signals, base_score=base_score, depth=depth)
        self.repo.update_scores(task_id, score.slr_score, score.depth_penalty, score.final_score)
        return {
            "slr_score": score.slr_score,
            "depth_penalty": score.depth_penalty,
            "final_score": score.final_score,
            "decision": score.decision,
        }

    def handle_validation_failure(self, task_id: str, failure: ValidationFailure) -> dict[str, str]:
        failure_text = failure.schema_failure_text()
        constraint = f"Negative constraint: avoid payload rejected by schema: {failure_text}"
        reroll_count = self.repo.add_negative_constraint(task_id, constraint)
        if reroll_count > self.max_rerolls:
            self.repo.dead_letter(
                task_id,
                "schema_validation_failed: reroll_limit_exhausted",
                {"failure": failure_text, "reroll_count": reroll_count},
            )
            return {"action": "dead_letter", "context": constraint}
        return {"action": "reroll", "context": constraint}

    def execute_tool_for_task(self, task_id: str, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.tool_adapters.call_mcp_tool(tool_name, args)
        except AdapterFailure as exc:
            failure = ValidationFailure(
                tool_name=tool_name,
                details=[{"path": "/", "message": str(exc), "kind": "adapter_failure"}],
            )
            reroll = self.handle_validation_failure(task_id, failure)
            return {
                "ok": False,
                "error": "adapter_failure",
                "message": str(exc),
                "reroll": reroll,
            }
