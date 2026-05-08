# Phase 2B — Declarative Pipeline Output Bindings

**Status:** Implemented and merged (commit 867543b)  
**Branch:** claude/dreamy-dhawan-5797b6

---

## Summary

Replaces the hard-coded `${session_path}` special-case with a generic, typed
output-binding system. Steps declare what they produce (`outputs`) and consume
upstream results via an explicit `bind:` YAML tag. The existing
`WorkflowRunner` loop is reused without a new public MCP tool or DB migration.

---

## Core Model — ArgBinding

```python
@dataclass(frozen=True)
class ArgBinding:
    from_step: str   # step_id of the producing step
    path: str        # shallow dot-path, e.g. "artifacts.session_path"
```

Added to `orchestrator/pipeline/models.py`. `PipelineStep` gains an `outputs`
field (`dict[str, str]`) mapping local alias to binding path.

---

## YAML Syntax — `bind:` tag

```yaml
args:
  session_path:
    bind:
      from_step: start_investigation
      path: artifacts.session_path
```

`bind:` is the only recognized wrapper. A plain dict with `from_step`/`path`
keys is treated as a normal dict arg, not a binding.

Allowed path prefixes: `artifacts`, `result`, `error`, `status`, `summary`.
Deep paths (more than one dot) are rejected at load time.

---

## Load-time Validation (`loader.py`)

`_parse_arg_value()` converts `{bind: {from_step, path}}` to `ArgBinding`.
Rejects:
- Any `bind:` block missing `from_step` or `path`
- Paths that don't match `^(artifacts|result|error|status|summary)\.[A-Za-z_][A-Za-z0-9_]*$`

---

## Compile-time Validation (`compiler.py`)

`_validate_bindings()` enforces, for every `ArgBinding` in `args_template`:

1. `from_step` exists in the pipeline
2. `from_step` is not the step itself (no self-reference)
3. `from_step` precedes the consumer in topological order
4. `from_step` is explicitly listed in `depends_on` of the consumer step

`_serialize_args()` converts `ArgBinding` to a JSON-safe sentinel:

```python
{"__binding__": True, "from_step": "...", "path": "..."}
```

---

## Runtime Resolution (`runner.py`)

The run loop maintains `step_outputs: dict[str, dict]` keyed by `step_id`.
After each step, the compacted result is recorded there.

Before calling `executor.call_tool()`:
1. `_resolve_args()` scans args for `__binding__: True` sentinels.
2. `_resolve_binding()` does a shallow two-segment path lookup into `step_outputs`.
3. If any binding is missing, the step fails closed:
   - `ok=False`, `status=POLICY_BLOCK`, `error.code=binding_resolution_failed`
   - The executor is **never called** with an unresolved sentinel.

---

## Fail-closed Guarantee

No `{"__binding__": True, ...}` object ever reaches `executor.call_tool()`.
A missing bound value immediately produces `POLICY_BLOCK` and halts the run.

---

## Error Payload Bounding (`compaction.py`)

`_compact_error()` normalizes all error dicts before storing in workflow state:

```python
def _compact_error(error: Any) -> dict[str, str] | None:
    if not isinstance(error, dict):
        return None
    return {
        "code": str(error.get("code", ""))[:120],
        "message": str(error.get("message", ""))[:1000],
    }
```

Extra fields (stack traces, internal state) are dropped. `code` and `message`
survive intact.

---

## investigation.yaml — Migrated

`investigation.yaml` bumped to `v1.1.0`. All steps that consume `session_path`
use `bind:` syntax. `start_investigation` declares:

```yaml
outputs:
  session_path: artifacts.session_path
```

All consumer steps list `start_investigation` in `depends_on`.

## patch_plan.yaml — Backward Compatible

`patch_plan.yaml` retains `${session_path}` strings. These survive compilation
via `ALLOWED_UNRESOLVED_VARS = frozenset({"session_path"})` and are resolved
at runtime by the existing legacy path in `_resolve_args`. The `${session_path}`
form is deprecated and will be removed after `patch_plan.yaml` is migrated.

---

## No Public MCP Tool Additions

Phase 2B adds zero public MCP tools. The Node contract test
`mcp_pipeline_run is not in public contracts` continues to pass.

## No DB Migrations

No schema changes. All binding state is ephemeral within the run loop.

---

## Test Coverage

| Suite | Tests added |
|-------|-------------|
| `TestArgBindingLoader` | 6 — load-time parsing and rejection |
| `TestArgBindingCompiler` | 7 — compile-time validation |
| `TestCompactError` | 6 — error bounding and passthrough |
| `TestPipelineOutputBindings` | 5 — end-to-end runner binding resolution |

Total: 264 Python tests passing (was 258 before `_compact_error` tests).
25 Node contract tests passing, no regressions.

---

## Next Phase

**Phase 2C-lite — Capability Execution Receipts**

Scope:
- No new public MCP tools
- No DB migration unless clearly necessary
- Add `CapabilityExecutionReceipt` model
- Emit receipts for `mcp_code_intelligence` and pipeline execution
- Include: risk tier, authorization status, network access, `writes_external_state`, `approval_id`, artifact refs
