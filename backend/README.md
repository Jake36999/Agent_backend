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

The Node process validates public tool schemas and forwards tool calls with a per-request HMAC auth envelope.

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

## Production Constraints

No UI, watchers, legacy FastMCP runtime, ChatML routing, or non-HITL mutating file tools are part of this runtime.

`ReadOnlySqliteAdapter` remains internal. Do not publish a SQLite MCP tool without a separate security review and strict public contract.
