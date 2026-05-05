# Patch generate v1

Generate a proposed unified diff only. Do not apply it. Do not run tests. Do not commit or push.

## Required inputs
- Objective
- Target repo
- TDD/refactor plan
- Candidate files or sufficient workspace evidence

## Guardrail precheck
Use `git_guardrails_v1` policy vocabulary. If the requested change implies destructive action, deployment, secret access, broad shell execution, or git mutation, block or escalate instead of producing a diff.

## Output rules
- Return a valid unified diff in `unified_diff`.
- List affected files.
- List test commands that should be run after approval.
- Include audit state: source plan, guardrail result, risk tier, and whether approval is required for application.
- Never claim the patch was applied.
