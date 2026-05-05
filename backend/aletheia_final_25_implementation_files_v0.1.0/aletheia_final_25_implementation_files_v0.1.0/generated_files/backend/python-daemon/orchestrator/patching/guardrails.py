from __future__ import annotations

import re

BLOCKED_COMMAND_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\b",
    r"\brm\s+-rf\b",
    r"\bdel\s+/s\b",
    r"\bdeploy\b",
    r"\bdocker\b",
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\benv\b.*\bdump\b",
]


def check_diff_generation() -> list[dict[str, object]]:
    return [{"rule": "diff_only", "decision": "allow", "message": "Diff generation only; no apply/test/commit/push."}]


def validate_test_command(command: list[str] | str) -> tuple[bool, str]:
    text = " ".join(command) if isinstance(command, list) else str(command)
    for pattern in BLOCKED_COMMAND_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return False, f"blocked dangerous test command pattern: {pattern}"
    return True, ""
