# ADR-002: YAML pipelines compile into existing QueueRepository

**Status:** Accepted
**Date:** 2026-05-06

## Context

UltraRAG-style YAML pipeline definitions offer a declarative way to express multi-step workflows. A new scheduler was considered but rejected in favor of the existing task queue.

## Decision

Pipeline definitions are compiled into the existing task queue format, not a new scheduler.

## Consequences

- `PipelineCompiler` produces the same `list[dict]` structure `WorkflowRunner` already iterates.
- No new scheduling infrastructure is introduced.
- YAML validation happens at compile time; runtime uses proven queue mechanics.
