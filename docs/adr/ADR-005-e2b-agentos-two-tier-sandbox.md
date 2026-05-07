# ADR-005: Two-tier sandbox: agentOS lightweight, E2B heavyweight

**Status:** Accepted
**Date:** 2026-05-06

## Context

Some tasks need fast, lightweight isolation (config transforms, small scripts). Others require full package environments (data science, builds). A single sandbox tier cannot serve both efficiently.

## Decision

Use agentOS-style V8/WASM for quick isolation and E2B for package-heavy execution. Neither owns orchestration.

## Consequences

- `SandboxRouter` dispatches based on task payload analysis.
- File mutations are blocked unless T2/T3 approval exists.
- Orchestrator remains outside both sandboxes; they are execution targets only.
