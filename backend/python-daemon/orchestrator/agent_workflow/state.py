from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_state_dir() -> Path:
    explicit = os.getenv("ALETHEIA_AGENT_STATE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    state_root = os.getenv("ALETHEIA_STATE_DIR")
    if state_root:
        return Path(state_root).expanduser() / "agent_workflows"
    return Path(".aletheia_state") / "agent_workflows"


@dataclass
class WorkflowState:
    run_id: str
    created_at: str
    user_prompt: str
    goal: str = ""
    phase: str = "PLAN"
    todos: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    reasoning_policy: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    final_summary: str = ""
    path: str = ""

    @classmethod
    def create(cls, user_prompt: str) -> "WorkflowState":
        run_id = uuid.uuid4().hex
        path = default_state_dir() / f"{run_id}.json"
        return cls(run_id=run_id, created_at=utc_now_iso(), user_prompt=user_prompt, path=str(path))

    def save(self) -> None:
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8")
