# ADR-001: Agent_backend remains the runtime authority

**Status:** Accepted
**Date:** 2026-05-06

## Context

Multiple external repositories (DeerFlow, UltraRAG, etc.) were evaluated during v0.2.0 upgrade planning. Each offers orchestration patterns that overlap with agent_backend.

## Decision

No external repository replaces the orchestrator. External repos provide design patterns and components only.

## Consequences

- All new modules wire through existing `ToolAdapters.call_mcp_tool()` dispatch and SQLite state machine.
- Pattern adoption is selective: we mimic designs, harvest components, or integrate APIs -- never cede control flow.
- Upgrade path stays incremental; no big-bang rewrites.
