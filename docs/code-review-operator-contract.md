# Code Review Operator Contract

> **Version:** 0.2.0  
> **Pipeline ID:** `code_review`  
> **Public surface:** `mcp_agent_workflow_run`  
> **Status:** stable

## Invocation

```json
{
  "tool": "mcp_agent_workflow_run",
  "args": {
    "objective": "Review the repository for architecture signals and notable patterns.",
    "target_repo": "/absolute/path/to/repo",
    "pipeline_id": "code_review"
  }
}
```

`target_repo` must resolve inside `ALETHEIA_ALLOWED_ROOTS`. No other `pipeline_vars` are required for `code_review`; the compiler fills runtime vars automatically.

## Artifact Index

All artifacts appear inside `response.artifacts`. File-backed artifacts contain an absolute path string pointing to `{state_dir}/{run_id}/{filename}`.

| Key | Type | Description |
|-----|------|-------------|
| `pipeline_id` | string | Always `"code_review"` |
| `compiled_step_count` | integer (as string) | Number of plan steps compiled |
| `architecture_overview_md` | file path | `architecture_overview.md` — repo scale, entrypoints, largest files |
| `dependency_graph_mmd` | file path | `dependency_graph.mmd` — Mermaid diagram of module edges |
| `code_review_summary_md` | file path | `code_review_summary.md` — fan-in/out, orphans, TODO density, receipts |
| `next_actions_yaml` | file path | `next_actions.yaml` — deterministic follow-up suggestions |
| `heuristics_json` | file path | `heuristics.json` — raw heuristics data (largest files, fan counts, etc.) |
| `code_review_report_index` | JSON string (≤2000 chars) | Compact index: `{key: {path, sha256, bytes}}` for each artifact above |
| `pipeline_receipt` | JSON object | `CapabilityExecutionReceipt` for the pipeline run |
| `binding_trace` | JSON object | Step ID → list of artifact keys produced |
| `review_draft_md` | file path | `review_draft.md` — LM-assisted draft (**only** when `ALETHEIA_ENABLE_REVIEW_DRAFTING=true` and `lm_client` injected) |
| `review_drafting_receipt` | JSON object | Drafting decision receipt (always present when `pipeline_id == "code_review"`) |

### Artifact file layout

```
{state_dir}/
  {run_id}/
    architecture_overview.md        ≤ 64 KB
    dependency_graph.mmd            ≤ 64 KB
    code_review_summary.md          ≤ 64 KB
    next_actions.yaml               ≤ 64 KB
    heuristics.json                 ≤ 64 KB
    code_review_artifacts_manifest.json   sha256 index of the above
    review_draft.md                 ≤ 64 KB  (conditional)
```

All filenames are fixed — no user-controlled path segments.

## Receipt Schemas

### `pipeline_receipt`

```json
{
  "operation": "capability.execute",
  "capability_id": "pipeline.code_review",
  "capability_type": "pipeline",
  "risk_tier": "T2",
  "status": "OK",
  "authorized": true,
  "network_access": false,
  "writes_external_state": true,
  "approval_id": null,
  "artifact_refs": ["<up to 20 step artifact keys>"],
  "summary": "Executed code_review pipeline (N steps, N complete)."
}
```

### `review_drafting_receipt`

```json
{
  "operation": "capability.execute",
  "capability_id": "review_drafting.lm_assisted",
  "capability_type": "adapter",
  "risk_tier": "T3",
  "status": "OK | SKIPPED | ERROR",
  "authorized": true | false,
  "network_access": true,
  "writes_external_state": false,
  "approval_id": null,
  "artifact_refs": ["review_draft_md"],
  "summary": "..."
}
```

`status` values:
- `OK` — draft generated and persisted
- `SKIPPED` — drafting disabled or wrong pipeline or no `lm_client`
- `ERROR` — `lm_client` raised or returned empty output; deterministic artifacts are unaffected

## Failure Modes

| `status` | `error.code` | Cause |
|----------|--------------|-------|
| `POLICY_BLOCK` | `capability_policy_block` | Pipeline quarantined or disabled in registry |
| `POLICY_BLOCK` | `plan_too_long` | Compiled plan exceeds `max_steps` |
| `POLICY_BLOCK` | `binding_resolution_failed` | A step's `bind:` reference was unresolvable |
| `ERROR` | `tool_execution_failed` | An internal MCP tool raised an exception |
| `ERROR` | `tool_failed` | A step returned `ok: false` |

When any step fails the runner halts and returns the step's error in `response.error`. Artifacts produced by steps that ran before the failure are still included in `response.artifacts`.

## Deterministic guarantees

- All file writes target `{state_dir}/{run_id}/` — never the target repository.
- No shell commands are executed against the target repository.
- No external network calls are made by the deterministic pipeline. (`review_draft_md` optionally calls a local `lm_client`.)
- Heuristics are computed from `mcp_code_intelligence` output only — not from raw file reads.
- `next_actions_yaml` content is fully deterministic from heuristics; it is not LLM-generated.

## Sample response shape

```json
{
  "ok": true,
  "status": "COMPLETE",
  "run_id": "3f2a...",
  "summary": "Workflow complete. Generated session, manifest, validation, handoff, and archive artifacts.",
  "artifacts": {
    "pipeline_id": "code_review",
    "compiled_step_count": "4",
    "architecture_overview_md": "/state/3f2a.../architecture_overview.md",
    "dependency_graph_mmd": "/state/3f2a.../dependency_graph.mmd",
    "code_review_summary_md": "/state/3f2a.../code_review_summary.md",
    "next_actions_yaml": "/state/3f2a.../next_actions.yaml",
    "heuristics_json": "/state/3f2a.../heuristics.json",
    "code_review_report_index": "{\"architecture_overview_md\":{\"path\":\"architecture_overview.md\",\"sha256\":\"...\",\"bytes\":1234}}",
    "pipeline_receipt": {"operation": "capability.execute", "...": "..."},
    "review_drafting_receipt": {"operation": "capability.execute", "status": "SKIPPED", "...": "..."}
  },
  "state_path": "/state/3f2a....json",
  "error": null
}
```
