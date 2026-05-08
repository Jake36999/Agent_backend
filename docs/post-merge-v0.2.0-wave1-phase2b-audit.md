# Post-merge Audit — v0.2.0 Wave 1 + Phase 2B

**Date:** 2026-05-08  
**Verification run:** 2026-05-08  
**Auditor:** Claude Sonnet 4.6 (automated review)

---

## Merged Commits (master as of `80ead5a`)

| SHA | Description |
|-----|-------------|
| `500b794` | Harden Wave 1 public MCP surface and pipeline security (Rounds 1-3) |
| `334179e` | Hotfix: commit missing code_intelligence module and skill registry stubs |
| `867543b` | Add Phase 2B: declarative pipeline output bindings |
| `2d07641` | Harden error compaction, add Phase 2B plan doc and CLAUDE.md binding notes |
| `c7dc1d6` | Add post-merge audit doc and Phase 2C-lite plan |

All five commits confirmed present in `origin/master` (`80ead5a`).  
Tag: `v0.2.0-wave1-pipeline-bindings`

---

## Automated Verification Results (2026-05-08)

| Check | Result |
|-------|--------|
| `python -m pytest -v` | **264 passed**, 12 subtests — all green |
| `python -c "from orchestrator.runtime import build_runtime"` | **OK** |
| `npm test` | **25 passed** — all green |
| `git ls-files orchestrator/code_intelligence` | **5 files** tracked |
| `git ls-files orchestrator/pipeline` | **9 files** tracked (compiler, loader, models, 2 active templates, schema, 2 example templates) |
| `docs/phase-2b-output-bindings.md` | **present** |
| `docs/phase-2c-lite-plan.md` | **present** |

---

## Public MCP Tools — Decision

**`mcp_code_intelligence` is confirmed public, T1 read-only.**

No new public MCP tools added by Phase 2B or the hotfix. `mcp_pipeline_run`
remains absent from public contracts.

All 25 Node contract tests pass. Tool manifest and contract counts are in sync.

---

## Changes by Area

### code_intelligence package (hotfix `334179e`)

Previously: `runtime.py` imported `CodeIntelligenceAnalyzer` but the package
was never committed. Fresh checkouts failed on daemon startup.

Now tracked in git:
- `__init__.py`
- `analyzer.py` — 4 modes: `code_map`, `dependency_graph`, `repo_context`, `mermaid`
- `dependency_extractor.py`, `mermaid_formatter.py`, `models.py`

`from orchestrator.runtime import build_runtime` imports cleanly.

### Pipeline output bindings (`867543b`)

`investigation.yaml` migrated to `bind:` YAML syntax (v1.1.0). `patch_plan.yaml`
retains `${session_path}` via `ALLOWED_UNRESOLVED_VARS` — **deprecated, migrate
before next major release.**

Enforcement:
- Load-time: deep paths rejected, malformed `bind:` blocks rejected
- Compile-time: `depends_on` membership, topological order, no self-reference
- Runtime: missing bound value → `POLICY_BLOCK` / `binding_resolution_failed`,
  executor never called with unresolved sentinel
- `binding_trace` recorded in `state.artifacts` on every run

### Error compaction hardening (`2d07641`)

`_compact_error()` bounds all error dicts before workflow state storage:
`code` ≤ 120 chars, `message` ≤ 1000 chars, extra fields dropped.
`binding_resolution_failed` code survives compaction intact.

---

## Manual Smoke Test Status

**Pending** — requires running daemon with `ALETHEIA_ALLOWED_ROOTS` set.

| Test | Status | Notes |
|------|--------|-------|
| `mcp_agent_workflow_run` (no pipeline_id) | Pending | Verify no pipeline artifacts |
| `mcp_agent_workflow_run` (pipeline_id="investigation") | Pending | Verify binding_trace, no sentinel in state |
| `mcp_code_intelligence` mode=code_map | Pending | Verify path-safety, no writes |
| `mcp_code_intelligence` mode=dependency_graph | Pending | Verify max_edges cap |
| `mcp_code_intelligence` mode=repo_context | Pending | Verify max_chars cap |
| `mcp_code_intelligence` mode=mermaid | Pending | Verify bounded output |
| `mcp_list_capabilities` | Pending | Verify source_path not exposed |

Phase 2C-lite implementation begins after these are confirmed.

---

## Known Deferred Items

| Item | Status |
|------|--------|
| `patch_plan.yaml` `${session_path}` migration | Deferred — low risk while deprecated |
| Capability Execution Receipts | Phase 2C-lite — planned, not started |
| Sandbox execution (E2b/AgentOS) | Deferred — ADR-005 |
| Composio external skill layer | Deferred — ADR-004 |
| DB-backed pipeline definitions | Deferred |
| Full capability policy enforcement | Deferred |
| `code_review.yaml` activation | Deferred |
| Deep research | Deferred |

---

## Next Phase

Phase 2C-lite — Capability Execution Receipts. See [`docs/phase-2c-lite-plan.md`](phase-2c-lite-plan.md).  
Start condition: manual smoke tests above must be confirmed passing first.
