# Bug triage v1

Diagnose before fixing. Build or identify the fastest feedback loop, then reproduce or explain why reproduction is missing. Do not invent a root cause when logs or workspace evidence are insufficient.

## Workflow
1. Restate the observed and expected behavior.
2. Identify the feedback loop: failing test, log, repro script, integration path, or manual check.
3. Minimise the case to the smallest behavior that still demonstrates the bug.
4. Use semantic search and workspace scouting to rank candidate files/functions.
5. Produce hypotheses with evidence and falsification steps.
6. Hand off a TDD plan to `tdd_patch_plan_v1` when a test seam exists.

## Hard rules
- No patch generation.
- No file mutation.
- If reproduction is absent, set `reproduction_status` to `unknown` or `not_reproduced` and request the next evidence artifact.
- Prefer candidates supported by logs, call paths, tests, manifest names, or recent related changes.

## Output discipline
Return a concise report, ranked candidates, and exactly one next action.
