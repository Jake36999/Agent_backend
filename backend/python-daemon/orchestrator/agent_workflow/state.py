from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state_dir() -> Path:
    agent_state = os.getenv("ALETHEIA_AGENT_STATE_DIR")
    if agent_state:
        return Path(agent_state).expanduser().resolve()
    base_state = os.getenv("ALETHEIA_STATE_DIR")
    if base_state:
        return Path(base_state).expanduser().resolve() / "agent_workflows"
    return (Path.cwd() / ".aletheia_state" / "agent_workflows").resolve()


@dataclass
class WorkflowState:
    run_id: str
    created_at: str
    user_prompt: str
    goal: str = ""
    phase: str = "PLAN"
    todos: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    reasoning_policy: dict[str, Any] = field(default_factory=dict)
    skill_registry_db_path: str = ""
    skill_registry_root: str = ""
    verified_skill_count: int = 0
    selector_candidate_scores: list[dict[str, Any]] = field(default_factory=list)
    selected_skill: dict[str, Any] | None = None
    warnings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    final_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["todos"] = [dict(item) for item in self.todos]
        data["artifacts"] = dict(self.artifacts)
        data["tool_results"] = [dict(item) for item in self.tool_results]
        data["reasoning_policy"] = dict(self.reasoning_policy)
        data["skill_registry_db_path"] = self.skill_registry_db_path
        data["skill_registry_root"] = self.skill_registry_root
        data["verified_skill_count"] = self.verified_skill_count
        data["selector_candidate_scores"] = [dict(item) for item in self.selector_candidate_scores]
        data["selected_skill"] = dict(self.selected_skill) if isinstance(self.selected_skill, dict) else None
        data["warnings"] = [dict(item) for item in self.warnings]
        data["errors"] = [dict(item) for item in self.errors]
        return data

    def save(self, state_dir: Path | None = None) -> Path:
        root = Path(state_dir) if state_dir is not None else default_state_dir()
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path
