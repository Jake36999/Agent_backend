# Post-merge Audit — v0.2.0 Wave 1 + Phase 2B

**Date:** 2026-05-08  
**Auditor:** Claude Sonnet 4.6 (automated review)

---

## Merged Commits

| SHA | Description |
|-----|-------------|
| `500b794` | Harden Wave 1 public MCP surface and pipeline security (Rounds 1-3) |
| `334179e` | Hotfix: commit missing code_intelligence module and skill registry stubs |
| `867543b` | Add Phase 2B: declarative pipeline output bindings |
| `2d07641` | Harden error compaction, add Phase 2B plan doc and CLAUDE.md binding notes |

**Master merge point:** `778f35e` (PR #1 — Wave 1 Round 1-3 only)  
**Pending merge:** commits `334179e`, `867543b`, `2d07641` (hotfix + Phase 2B) — PR open.

---

## Test Counts

| Suite | Count | Status |
|-------|-------|--------|
| Python (`python -m pytest -v`) | 264 passed, 12 subtests | All green |
| Node (`npm test`) | 25 passed | All green |

---

## Public MCP Tools — Changes

**No new public MCP tools added by Phase 2B or the hotfix.**

`mcp_pipeline_run` remains absent from public contracts (confirmed by
`mcp_pipeline_run is not in public contracts` Node test).

The only entry point for pipeline execution remains `mcp_agent_workflow_run`
with the `pipeline_id` + `pipeline_vars` parameters added in Wave 1.

All 25 Node contract tests pass. Tool manifest and contract counts are in sync.

---

## Changes by Area

### code_intelligence package (hotfix `334179e`)

Previously: `runtime.py` imported `CodeIntelligenceAnalyzer` but the package
was never committed. Any fresh checkout would fail on daemon startup.

Now: `orchestrator/code_intelligence/` is fully tracked in git:
- `__init__.py`
- `analyzer.py` — 4 modes: `code_map`, `dependency_graph`, `repo_context`, `mermaid`
- `dependency_extractor.py`
- `mermaid_formatter.py`
- `models.py`

`from orchestrator.runtime import build_runtime` imports cleanly.

### Pipeline output bindings (`867543b`)

`investigation.yaml` migrated from `${session_path}` special-case to explicit
`bind:` YAML syntax (version bumped to `1.1.0`).

`patch_plan.yaml` retains `${session_path}` — backward compatible via
`ALLOWED_UNRESOLVED_VARS`. **Deprecated; migrate before next major release.**

New enforcement:
- Bindings validated at load time (deep paths rejected) and compile time
  (`depends_on` membership, topological order, no self-reference)
- Missing bound values at runtime produce `POLICY_BLOCK` /
  `binding_resolution_failed` — executor never receives an unresolved sentinel
- `binding_trace` recorded in `state.artifacts` on every run

### Error compaction hardening (`2d07641`)

`compact_tool_result` previously passed the raw `error` dict through unchanged.
`_compact_error()` now normalizes before storing in workflow state:
- `code` capped at 120 chars
- `message` capped at 1000 chars
- All extra fields (stack traces, internal state) dropped

`binding_resolution_failed` code survives compaction intact.

---

## Known Deferred Items

| Item | Reason deferred |
|------|-----------------|
| `patch_plan.yaml` `${session_path}` migration | Requires coordinated update; low risk while deprecated |
| `mcp_code_intelligence` public/internal status | Phase 2A decision pending |
| Capability Execution Receipts (Phase 2C-lite) | Next phase — see `docs/phase-2c-lite-receipts.md` when written |
| Sandbox execution (E2b/AgentOS) | ADR-005 captures intent; not started |
| Composio external skill layer | ADR-004 captures intent; not started |
| DB-backed pipeline definitions | Not started |
| Full capability policy enforcement | Not started |

---

## Smoke Test Status

Manual smoke tests (items 4-6 from post-merge checklist) require a running
daemon with a valid `ALETHEIA_ALLOWED_ROOTS` target. These must be run by a
human operator:

- `mcp_agent_workflow_run` without `pipeline_id` — verify legacy plan path
- `mcp_agent_workflow_run` with `pipeline_id="investigation"` — verify binding_trace,
  session_path resolved, no `__binding__` sentinel in state
- `mcp_code_intelligence` modes: `code_map`, `dependency_graph`, `repo_context`, `mermaid`
- `mcp_list_capabilities`

Until these are run, the workflow runtime remains in a **brief freeze** — no
Phase 2C implementation should start.

---

## Next Phase

See [`docs/phase-2c-lite-plan.md`](phase-2c-lite-plan.md) (to be written after
smoke tests pass) for Capability Execution Receipts scope.
