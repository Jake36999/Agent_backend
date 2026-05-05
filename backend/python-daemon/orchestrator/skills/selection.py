from __future__ import annotations

import re
from typing import Any

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "by",
    "do",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "only",
    "or",
    "the",
    "this",
    "to",
    "with",
    "plan",
    "produce",
    "create",
    "write",
}

INTENT_HINTS: dict[str, set[str]] = {
    "bug_triage_v1": {
        "bug",
        "regression",
        "triage",
        "diagnose",
        "root",
        "cause",
        "failing",
        "failure",
        "stale",
        "broken",
        "reproduce",
        "reproduction",
    },
    "candidate_analysis_v1": {
        "candidate",
        "candidates",
        "rank",
        "likely",
        "files",
        "functions",
        "where",
        "change",
    },
    "tdd_patch_plan_v1": {
        "tdd",
        "red",
        "green",
        "refactor",
        "test",
        "tests",
        "failing",
        "vertical",
        "slice",
    },
    "patch_generate_v1": {
        "generate",
        "patch",
        "diff",
        "unified",
        "do",
        "not",
        "apply",
    },
    "patch_apply_and_test_v1": {
        "apply",
        "approved",
        "patch",
        "diff",
        "run",
        "tests",
    },
    "architecture_review_v1": {
        "architecture",
        "review",
        "coupling",
        "boundary",
        "boundaries",
        "modules",
        "testability",
    },
    "refactor_plan_v1": {
        "refactor",
        "refactoring",
        "technical",
        "debt",
        "phased",
        "rewrite",
        "remediation",
    },
    "conversation_summary_ingest_v1": {
        "conversation",
        "summary",
        "summarize",
        "memory",
        "commit",
        "ingest",
    },
    "skill_crystallize_v1": {
        "crystallize",
        "skill",
        "sop",
        "manifest",
        "candidate",
    },
    "git_guardrails_v1": {
        "git",
        "push",
        "commit",
        "reset",
        "clean",
        "destructive",
        "secret",
        "deploy",
    },
}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def meaningful_tokens(text: str) -> set[str]:
    return {token for token in tokens(text) if token not in STOPWORDS and len(token) > 1}


def phrase_present(phrase: str, objective_l: str) -> bool:
    return phrase.lower() in objective_l


def score_manifest(objective: str, manifest: dict[str, Any]) -> dict[str, Any]:
    objective_l = objective.lower()
    objective_tokens = meaningful_tokens(objective)

    trigger_hits: list[str] = []
    capability_hits: list[str] = []
    intent_hits: list[str] = []

    score = 0

    for trigger in manifest.get("triggers", []):
        trigger_l = trigger.lower()
        trigger_tokens = meaningful_tokens(trigger)

        if phrase_present(trigger_l, objective_l):
            trigger_hits.append(trigger)
            score += 8
            continue

        if not trigger_tokens:
            continue

        overlap = trigger_tokens.intersection(objective_tokens)
        overlap_ratio = len(overlap) / max(1, len(trigger_tokens))

        # Require a strong partial trigger match. This prevents weak words like
        # "plan" from making "refactor plan" win every planning objective.
        if len(overlap) >= 2 and overlap_ratio >= 0.67:
            trigger_hits.append(trigger)
            score += 4

    for capability in manifest.get("capabilities", []):
        capability_tokens = meaningful_tokens(capability.replace("_", " "))
        overlap = capability_tokens.intersection(objective_tokens)
        if capability.lower() in objective_l:
            capability_hits.append(capability)
            score += 4
        elif capability_tokens and len(overlap) >= 2:
            capability_hits.append(capability)
            score += 2

    skill_id = manifest["skill_id"]
    for hint in INTENT_HINTS.get(skill_id, set()):
        if hint in objective_tokens:
            intent_hits.append(hint)

    score += len(intent_hits)

    # Small, explicit bias: if the objective asks to triage/diagnose a regression,
    # prefer bug_triage over downstream planning skills.
    if skill_id == "bug_triage_v1" and {"triage", "regression"}.intersection(objective_tokens):
        score += 6

    # If the objective says "TDD plan" but also says "triage/regression",
    # keep TDD as a candidate but do not let generic "plan" dominate.
    if skill_id == "tdd_patch_plan_v1" and "tdd" in objective_tokens:
        score += 4

    return {
        "skill_id": skill_id,
        "score": score,
        "trigger_hits": trigger_hits,
        "capability_hits": capability_hits,
        "intent_hits": sorted(intent_hits),
        "risk_tier": manifest["risk_tier"],
    }


def select_skill(objective: str, manifests: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = [score_manifest(objective, manifest) for manifest in manifests]
    ranked = [candidate for candidate in ranked if candidate["score"] > 0]
    ranked.sort(key=lambda item: (-item["score"], item["risk_tier"], item["skill_id"]))

    if not ranked:
        return None

    return {
        "selected_skill_id": ranked[0]["skill_id"],
        "candidate_analysis": ranked[:5],
    }