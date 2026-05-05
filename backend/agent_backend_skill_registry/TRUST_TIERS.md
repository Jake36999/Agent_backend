# Trust tiers

## T1

Read-only analysis, ranking, planning, review, and bounded summarisation. No diffs, no filesystem mutation, no shell execution.

## T2

Artifact generation that may contain a proposed diff or candidate manifest, but must not apply changes or execute tests.

## T3

Approved workspace mutation such as applying an already-approved diff and running declared tests. Requires user and diff approval.

## T4

High-risk local/system actions, destructive filesystem operations, secret exposure risk, git history mutation, package/network mutation, or broad shell execution. Block or require explicit elevated approval.

## T5

Deployment, production mutation, credential changes, irreversible destructive actions, or public release actions. Not allowed in this v1 pack.

## Required enforcement

- T1 skills may read/search/scout and produce plans only.
- T2 skills may produce artifacts such as unified diffs or candidate manifests, but cannot apply them.
- T3 skills require approval and must preserve rollback artifacts.
- T4/T5 actions are blocked or escalated; this v1 pack does not include direct T4/T5 executors.
