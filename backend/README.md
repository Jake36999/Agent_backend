# Aletheia Backend Runtime

The runtime has two processes:

- Python daemon: state authority, SQLite queue/control DBs, Chroma access, worker loop, bridge server, recovery, HITL, and adapters.
- Node MCP gateway: stdio MCP contracts only, with strict schema validation and forwarding to Python.

## Python Daemon

Set the runtime environment, then start the daemon:

```powershell
$env:ALETHEIA_PROJECT_ROOT="C:\path\to\project"
$env:ALETHEIA_STATE_DIR="C:\path\to\project\.aletheia_state"
$env:ALETHEIA_ALLOWED_ROOTS="C:\path\to\project"
$env:ALETHEIA_CHROMA_PATH="C:\path\to\project\.aletheia_state\chroma"
$env:ALETHEIA_LM_STUDIO_BASE_URL="http://localhost:1234/v1"
$env:ALETHEIA_EMBEDDING_MODEL="nomic-ai/nomic-embed-text-v1.5-GGUF"
$env:ALETHEIA_BRIDGE_HOST="127.0.0.1"
$env:ALETHEIA_BRIDGE_PORT="8765"
$env:ALETHEIA_BRIDGE_SECRET="change-me"
$env:ALETHEIA_PROJECT_ID="my-project"  # defaults to project root name
$env:ALETHEIA_ENABLE_ADMIN_BRIDGE="false"  # enable daemon.* admin methods
$env:ALETHEIA_APPROVAL_SECRET="approval-secret"

$env:TOOLSET_ROOT="C:\path\to\toolset-repo"
$env:LTA_OUTPUT_ROOT="C:\path\to\project\.aletheia_state\tool_assist"  # optional
python -m orchestrator.main
```

The installed script entrypoint is also available as `aletheia-daemon`.

## Node MCP Gateway

Point the Node gateway at the Python bridge:

```powershell
$env:ALETHEIA_PYTHON_BRIDGE="tcp://127.0.0.1:8765"
$env:ALETHEIA_BRIDGE_SECRET="change-me"
node backend\node-mcp\src\server.mjs
```

When LM Studio is used in the current supported topology, it goes through the FastMCP shim:

LM Studio -> backend/lmstudio_fastmcp_shim.py -> Python daemon TCP bridge -> ToolAdapters

The Node MCP gateway remains the generic strict stdio gateway, while the FastMCP shim is the currently verified LM Studio adapter.
The investigation tools (`mcp_investigation_*`) are also exposed through `backend/lmstudio_fastmcp_shim.py` for this LM Studio topology.

The Node process validates public tool schemas and forwards tool calls with a per-request HMAC auth envelope.

For normal LM Studio agent runs, prefer exposing the compact high-level workflow tool instead of the full investigation tool set:

```json
{
  "type": "plugin",
  "id": "mcp/aletheia-fastmcp-shim",
  "allowed_tools": ["mcp_agent_workflow_run"]
}
```

LM Studio's native `/api/v1/chat` integrations support `allowed_tools` for plugin and ephemeral MCP servers. Keeping only `mcp_agent_workflow_run` visible reduces prompt pressure and lets the backend deterministic workflow controller perform bounded Tool Assist execution. The lower-level `mcp_investigation_*` tools remain available for manual debugging and direct smoke tests.

## LM Studio embedding model readiness

The daemon automatically manages LM Studio embedding model loading:

- **Embedding model**: `text-embedding-nomic-embed-text-v1.5` (default)
- **Chat model**: Can remain loaded separately (e.g., DeepSeek/Qwen)
- **Auto-loading**: Enabled by default; checks and loads embedding model before embedding requests
- **API endpoints**: Uses `/api/v1/models` for inspection/loading, `/v1/embeddings` for generation

Environment variables:

```powershell
$env:ALETHEIA_EMBEDDING_MODEL="text-embedding-nomic-embed-text-v1.5"
$env:ALETHEIA_LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"
$env:ALETHEIA_LM_STUDIO_API_BASE_URL="http://127.0.0.1:1234/api/v1"
$env:ALETHEIA_LM_STUDIO_API_TOKEN=""  # optional for auth
$env:ALETHEIA_AUTO_LOAD_EMBEDDING_MODEL="true"
```

The daemon will attempt to load the embedding model if not already loaded, providing clear errors for auth/model issues.

## Admin CLI

```powershell
aletheia-admin show-config
aletheia-admin health
aletheia-admin reconcile-project my-project
aletheia-admin list-dead-letters --limit 25
```

The admin CLI calls Python internals directly. It does not expose filesystem mutation tools.

## Operations

- Bootstrap happens automatically on daemon start through `bootstrap_databases`.
- Database migrations are recorded in `schema_migrations`.
- Ingestion is exposed by `mcp_ingest_target`; unchanged files are skipped, changed files are reindexed, and deleted files are removed during directory ingestion.
- Search is exposed by `mcp_semantic_search` and is always scoped by `project_scope_hash`.
- Workspace scouting is exposed by `mcp_scout_workspace`.

- External investigation flow is exposed by:
  1. `mcp_investigation_start`
  2. `mcp_investigation_filemap`
  3. `mcp_investigation_validate_manifest`
  4. `mcp_investigation_read_report`
  5. `mcp_investigation_compile_handoff`
- Investigation tools return compact summaries and artifact paths only; memory mutation still goes through `mcp_ingest_target`.
- Tool Assist remains an external dependency loaded from `TOOLSET_ROOT` (not vendored into this backend).
- Failed vector upserts are recoverable with `aletheia-admin reconcile-project`.
- Dead letters are stored in `control.db` and can be inspected with `aletheia-admin list-dead-letters`.
- Do not ingest generated extraction bundles or directories such as `New project_bundle_*`, `*_bundle*.py`, or `*_bundle*.yaml`.
- Worker heartbeats and process state are stored in `process_registry`.

## Smoke Test

1. Start LM Studio with embeddings model loaded.
2. Set environment variables as above.
3. Start Python daemon: `python -m orchestrator.main`
4. In another terminal, start Node gateway: `node backend\node-mcp\src\server.mjs`
5. Test tool call: use MCP client to call `mcp_scout_workspace` with `project_id` and `absolute_path`.
6. If admin enabled, test `daemon.health` method.

## Tests

```powershell
cd backend\python-daemon
python -m unittest discover -s tests -v

cd ..\node-mcp
node test\run-tests.mjs
```

Live integration tests that require LM Studio, real Chroma state, PDF/OCR binaries, or external MCP clients should be opt-in and must not run in the default unit suite.

## Agent Workflow Controller Scaffold (Opt-in)

The Python daemon includes an opt-in deterministic workflow controller for Tool Assist investigations. It does not replace the existing MCP tools, the daemon TCP bridge, or the LM Studio FastMCP shim. It is a separate local runner for operators who want bounded model reasoning around deterministic backend tool execution.

LM Studio can invoke the workflow in one MCP call through `mcp_agent_workflow_run`. For MCP/FastMCP calls, the defaults are deterministic:

- `allow_ingest=false`
- `include_report_preview=false`
- `use_model_phases=false`

This avoids nested model-calls-model behavior when the caller is already LM Studio. Set `use_model_phases=true` only for explicit operator-controlled experiments.

Example:

```powershell
cd backend\python-daemon
python -m orchestrator.agent_workflow_cli `
  --objective "Smoke test Tool Assist from backend agent workflow" `
  --target-repo "C:\path\to\project\backend\python-daemon\orchestrator" `
  --profile safe
```

The v1 phase loop is:

```text
PLAN -> ACT -> SUMMARISE_TOOL_RESULT -> CHECK -> SYNTHESIZE -> FINAL
```

Only `PLAN`, `SYNTHESIZE`, and `FINAL` call the model. `ACT` executes the active todo through the existing `tools.call` bridge path, and `CHECK` is a deterministic state transition. Tool results are compacted before being written to workflow state; large report bodies, manifests, stdout/stderr, and raw backend JSON are omitted by default. `mcp_investigation_read_report` only stores capped content previews when a todo explicitly requests `include_content: true`.

Configuration:

```powershell
$env:ALETHEIA_AGENT_API_MODE="native"  # native uses /api/v1/chat; compatible uses /v1/chat/completions
$env:ALETHEIA_AGENT_CHAT_URL="http://127.0.0.1:1234/api/v1/chat"
$env:ALETHEIA_AGENT_MODEL="your-lm-studio-model"
$env:ALETHEIA_LM_STUDIO_API_TOKEN=""
$env:ALETHEIA_AGENT_REASONING_PLAN="low"
$env:ALETHEIA_AGENT_REASONING_ACT="off"
$env:ALETHEIA_AGENT_REASONING_CHECK="low"  # reserved for future hybrid CHECK; v1 CHECK is deterministic
$env:ALETHEIA_AGENT_REASONING_SYNTHESIZE="low"
$env:ALETHEIA_AGENT_REASONING_FINAL="off"
$env:ALETHEIA_AGENT_MAX_STEPS="8"
$env:ALETHEIA_AGENT_MAX_TOOL_RESULT_CHARS="2000"
$env:ALETHEIA_AGENT_STATE_DIR="C:\path\to\project\.aletheia_state\agent_workflows"
```

The default LM Studio mode is native `/api/v1/chat` for phase reasoning control. Set `ALETHEIA_AGENT_API_MODE=compatible` when using OpenAI-compatible `/v1/chat/completions` structured-output behavior. If LM Studio rejects the native `reasoning` field, the workflow retries that request once without `reasoning` and records the fallback in state.

Ingestion remains gated: `mcp_ingest_target` is blocked unless the runner is explicitly constructed with `allow_ingest=True` and the validated todo also marks ingestion as allowed. This workflow does not directly change LM Studio's normal built-in tool-calling behavior unless the operator uses this external controller flow.

## Production Constraints

No UI, watchers, legacy FastMCP runtime, ChatML routing, or non-HITL mutating file tools are part of this runtime.

`ReadOnlySqliteAdapter` remains internal. Do not publish a SQLite MCP tool without a separate security review and strict public contract.
