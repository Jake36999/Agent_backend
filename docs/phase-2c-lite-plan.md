# Phase 2C-lite — Capability Execution Receipts

**Status:** Planned — not started  
**Gate:** Must complete manual smoke tests from post-merge checklist first.

---

## Objective

Attach a structured, bounded `CapabilityExecutionReceipt` to every
`mcp_code_intelligence` result and to pipeline-run artifacts. Provides
observability into what ran, at what risk tier, and under what authorization —
without adding new public MCP tools or DB migrations.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| `CapabilityExecutionReceipt` model | Full policy enforcement |
| Attach to `mcp_code_intelligence` results | Sandbox execution |
| Attach to pipeline-run artifacts | Composio/external integrations |
| Bounding receipts before storage | DB-backed pipeline definitions |
| Unit tests for receipt model and attachment | `code_review.yaml` activation |
| — | Deep research skill |

**No new public MCP tools.**  
**No DB migration unless unavoidable** (and clearly justified in a follow-up note).

---

## Receipt Shape

```python
@dataclass(frozen=True)
class CapabilityExecutionReceipt:
    capability_id: str        # e.g. "code_intelligence.repo_context"
    capability_type: str      # "adapter" | "pipeline" | "skill"
    risk_tier: str            # "T1" | "T2" | "T3" | "T4"
    authorized: bool
    network_access: bool
    writes_external_state: bool
    approval_id: str | None
    artifact_refs: tuple[str, ...]   # artifact keys produced
    summary: str              # one sentence, max 200 chars
```

Serialized as JSON-safe dict (all fields primitive or list of strings).
`summary` capped at 200 chars, `artifact_refs` capped at 20 entries.

### Example — code_intelligence.repo_context

```json
{
  "capability_id": "code_intelligence.repo_context",
  "capability_type": "adapter",
  "risk_tier": "T1",
  "authorized": true,
  "network_access": false,
  "writes_external_state": false,
  "approval_id": null,
  "artifact_refs": [],
  "summary": "Executed read-only repo_context analysis."
}
```

### Example — pipeline.investigation

```json
{
  "capability_id": "pipeline.investigation",
  "capability_type": "pipeline",
  "risk_tier": "T2",
  "authorized": true,
  "network_access": false,
  "writes_external_state": false,
  "approval_id": null,
  "artifact_refs": ["session_path", "manifest_doctor_md"],
  "summary": "Executed investigation pipeline (5 steps, all complete)."
}
```

---

## Risk Tiers

| Tier | Meaning |
|------|---------|
| T1 | Read-only, local, no side effects |
| T2 | Read-write local state (SQLite, workspace) |
| T3 | External network access |
| T4 | Requires explicit human approval |

`mcp_code_intelligence` is T1 (read-only, path-safety enforced).  
`pipeline.investigation` is T2 (writes session state to disk via ToolAssist).  
`pipeline.patch_plan` is T2-T3 depending on patch apply configuration.

---

## Files to Touch

1. **New model** — `orchestrator/capabilities/receipt.py`  
   `CapabilityExecutionReceipt` dataclass + `compact_receipt()` serializer.

2. **Code intelligence adapter** — `orchestrator/adapters.py`  
   After a successful `mcp_code_intelligence` dispatch, attach receipt to the
   result dict under `"capability_receipt"`.

3. **WorkflowRunner** — `orchestrator/agent_workflow/runner.py`  
   After `_record_binding_trace()`, attach a pipeline receipt to
   `state.artifacts["pipeline_receipt"]`.

4. **Tests**  
   - `test_capability_receipt.py` — model, compact, bounding
   - Add assertions in `test_pipeline_integration.py` for receipt presence

---

## Constraints

- Receipt must not exceed 2 KB serialized.
- `artifact_refs` max 20 entries; each ref max 120 chars.
- `summary` max 200 chars.
- No new `mcp_*` function exposed to the Node gateway.
- No new SQLite table (receipts are ephemeral, stored only in the run result).

---

## Start Condition

Do not start until:
1. Manual smoke tests from post-merge checklist are confirmed passing.
2. `mcp_code_intelligence` mode decision (public vs internal) is resolved.
3. `patch_plan.yaml` `${session_path}` migration is assessed (low priority,
   but track before adding more pipeline templates).
