from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

_DRAFT_CAP = 8000
_PROMPT_CAP = 12000
_TRUNCATION_MARKER = "\n...[truncated]"


@runtime_checkable
class LMClient(Protocol):
    def complete(self, prompt: str, *, max_tokens: int = 2048) -> str: ...


def _bounded(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def build_review_prompt(
    *,
    architecture_overview: str,
    code_review_summary: str,
    heuristics_json: str,
    next_actions_yaml: str,
    target_repo: str,
) -> str:
    repo_name = target_repo.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or target_repo
    prompt = f"""\
You are reviewing the repository "{repo_name}". Below are deterministic analysis artifacts.
Write a concise engineering review draft (markdown). Focus on:
1. Key architectural observations (from the overview and dependency data)
2. Noteworthy signals (high fan-in/fan-out, large files, TODO density)
3. Suggested areas for deeper inspection (from the next-actions list)

Constraints:
- Do NOT claim bugs, vulnerabilities, or security issues unless directly evident from the data.
- Use neutral language: "candidate for review", "noteworthy signal", "warrants inspection".
- Keep the draft under 3000 words.
- Do NOT repeat raw data — summarize and interpret.

---
## Architecture Overview
{_bounded(architecture_overview, 3000)}

---
## Code Review Summary
{_bounded(code_review_summary, 2500)}

---
## Heuristics (JSON)
{_bounded(heuristics_json, 3000)}

---
## Suggested Follow-ups
{_bounded(next_actions_yaml, 2000)}
"""
    return _bounded(prompt, _PROMPT_CAP)


def draft_review(
    *,
    lm_client: Any,
    architecture_overview: str,
    code_review_summary: str,
    heuristics_json: str,
    next_actions_yaml: str,
    target_repo: str,
    max_tokens: int = 2048,
) -> str | None:
    if lm_client is None:
        return None
    prompt = build_review_prompt(
        architecture_overview=architecture_overview,
        code_review_summary=code_review_summary,
        heuristics_json=heuristics_json,
        next_actions_yaml=next_actions_yaml,
        target_repo=target_repo,
    )
    try:
        raw = lm_client.complete(prompt, max_tokens=max_tokens)
    except Exception:
        return None
    if not isinstance(raw, str) or not raw.strip():
        return None
    return _bounded(raw.strip(), _DRAFT_CAP)
