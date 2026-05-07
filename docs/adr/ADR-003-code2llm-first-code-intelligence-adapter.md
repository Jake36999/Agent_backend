# ADR-003: code2llm is the first code intelligence backend

**Status:** Accepted
**Date:** 2026-05-06

## Context

Code intelligence (map, context, call graph, evolution tracking) is needed for repository-aware agent tasks. code2llm provides these outputs in a format suitable for LLM consumption.

## Decision

Use code2llm-style outputs (map, context, call graph, evolution) as the initial code intelligence adapter.

## Consequences

- `code_intelligence/` module is read-only and returns bounded summaries only.
- No write-back or code modification via this path.
- Adapter interface allows future backends to replace code2llm without changing consumers.
