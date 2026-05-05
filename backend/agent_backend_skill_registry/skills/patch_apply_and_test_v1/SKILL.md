# Patch apply and test v1

Apply only an already approved unified diff. This skill must refuse any request to infer and apply changes from natural language.

## Required gates
- User approval present.
- Diff approval present.
- Guardrail check passed.
- Target repo matches approved record.

## Execution discipline
- Create or preserve rollback artifact before mutation.
- Apply exactly the approved diff.
- Run only declared tests unless operator explicitly approves more.
- Do not commit.
- Do not push.
- Do not deploy.

## Output
Return applied files, bounded test logs, pass/fail status, rollback artifact, audit state, and next action.
