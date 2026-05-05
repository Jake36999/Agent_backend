# Implementation order

1. Apply `patch_fragments/db_bootstrap.patch`.
2. Add `generated_files/backend/python-daemon/orchestrator/active_partition/watcher.py`.
3. Add snapshot memory files under `generated_files/backend/python-daemon/orchestrator/memory/`.
4. Add `generated_files/backend/python-daemon/orchestrator/memory/conversation_summary.py`.
5. Add the deterministic candidate analysis package under `generated_files/backend/python-daemon/orchestrator/candidate_analysis/`.
6. Add the T2 patching package files under `generated_files/backend/python-daemon/orchestrator/patching/`.
7. Add the T3 patch apply/test files under `generated_files/backend/python-daemon/orchestrator/patching/`.
8. Apply runtime/main/runner/state/MCP-tool patch fragments in this order:
   - `config.patch`
   - `runtime.patch`
   - `main.patch`
   - `agent_workflow_state.patch`
   - `agent_workflow_runner.patch`
   - `agent_workflow_mcp_tool.patch`
   - `adapters.patch` only if needed by your current adapter layout
9. Add generated tests from `tests/python-daemon/tests/`.
10. Run Python tests.
11. Run Node tests only if Node contracts are modified.

## Integration notes

- Keep `mcp_agent_workflow_run` as the preferred public entry point.
- Do not expose every skill as a public MCP tool.
- Keep services dependency-injected. Runtime/config may read env; core services should receive Paths/repos/adapters.
- Keep all new tool responses compact.
- Treat patch application as T3 and approval-gated.
