# ADR-004: Composio is the external API skill layer, not runtime

**Status:** Accepted
**Date:** 2026-05-06

## Context

Composio/Rube provides connectors for hundreds of external APIs. Integrating it as core orchestration would create tight coupling and security concerns.

## Decision

Composio/Rube is used as an external app connector behind adapters, not as core orchestration.

## Consequences

- All external integrations declare `risk_tier`, `requires_approval`, `network_access`, `writes_external_state`.
- Composio actions are wrapped by ToolAdapters and subject to the same approval gates as any other tool.
- Connector catalog can grow without modifying the orchestrator.
