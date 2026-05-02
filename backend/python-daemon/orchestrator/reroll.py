from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationFailure(Exception):
    tool_name: str
    details: list[dict[str, Any]]

    def schema_failure_text(self) -> str:
        return json.dumps(
            {
                "tool_name": self.tool_name,
                "error": "schema_validation_failed",
                "details": self.details,
            },
            sort_keys=True,
        )
