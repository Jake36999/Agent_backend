# Aletheia Backend Orchestrator

Aletheia is a local backend daemon for deterministic agentic orchestration. It uses a Python authority process, a narrow Node.js MCP stdio gateway, SQLite for durable runtime state, and ChromaDB for rebuildable semantic vector search.

The runtime is intentionally backend-only. It does not include a browser UI, web dashboard, legacy FastMCP server, ChatML conversation router, file watcher, training pipeline, or unapproved filesystem mutation tools.

## Runtime architecture

```text
LLM / MCP client
  -> Node MCP gateway
  -> JSON-RPC bridge
  -> Python daemon
  -> ToolAdapters
  -> SQLite / Chroma / filesystem-safe adapters
```

### Process roles

- **Python daemon**: authoritative runtime. Owns configuration, queue state, worker execution, migrations, process registry, HITL state, ingestion, semantic memory, OCR adapter wiring, and admin CLI internals.
- **Node MCP gateway**: narrow stdio-facing MCP layer. Validates public tool schemas and forwards JSON-RPC calls to the Python daemon.
- **SQLite**: canonical structural state and rebuild manifest. Stores tasks, leases, process registry, task events, files, chunks, ingestion runs, approvals, and dead letters.
- **ChromaDB**: rebuildable vector index. Chroma is not the source of truth; SQLite chunk records are.
- **LM Studio**: local OpenAI-compatible embedding endpoint.

## Repository layout

```text
backend/
  README.md
  node-mcp/
    package.json
    src/
      bridge.mjs
      contracts.mjs
      server.mjs
    test/
      bridge-integration.test.mjs
      bridge.test.mjs
      contracts.test.mjs
      run-tests.mjs
      scout-contract.test.mjs
  python-daemon/
    pyproject.toml
    orchestrator/
      adapters.py
      admin.py
      approval.py
      bridge_server.py
      chroma_manager.py
      config.py
      dag_runtime.py
      db_bootstrap.py
      epistemic.py
      execution_loop.py
      hitl.py
      main.py
      observability.py
      ocr.py
      queue_repo.py
      recovery.py
      reroll.py
      runtime.py
      shell.py
      worker.py
      ingest/
        processors.py
        service.py
    tests/
```

## Public MCP tools

The public Node MCP surface is intentionally limited to these tools:

| Tool | Purpose |
|---|---|
| `mcp_ingest_target` | Index a file or directory into SQLite chunk manifests and Chroma vectors. |
| `mcp_semantic_search` | Search within a project-scoped semantic memory. |
| `mcp_scout_workspace` | Return deterministic workspace tree, summaries, skipped-file stats, and package hash without vector indexing. |
| `mcp_verify_integrity` | Verify SHA-256 and metadata hash through read-only file tools. |
| `mcp_extract_image` | Optional OCR extraction through configured command provider. |

`ReadOnlySqliteAdapter` remains internal. Do not expose a public SQLite MCP tool without a separate security review and a strict public contract.

## Security model

### Bridge auth

The Python bridge supports per-request HMAC authentication when `ALETHEIA_BRIDGE_SECRET` is set.

The auth envelope includes:

```json
{
  "timestamp": "...",
  "nonce": "...",
  "signature": "..."
}
```

The signature payload is:

```text
timestamp + "." + nonce + "." + canonical_json(request_without_auth)
```

The bridge rejects stale timestamps, missing auth fields, bad signatures, and replayed nonces. Nonce storage is bounded to prevent unbounded memory growth.

### Admin bridge methods

Internal daemon JSON-RPC methods are gated separately from public MCP tools:

- `daemon.health`
- `daemon.reconcile_project`
- `daemon.dead_letters`

These methods are available only when:

```text
ALETHEIA_ENABLE_ADMIN_BRIDGE=true
ALETHEIA_BRIDGE_SECRET is configured
HMAC auth is valid
```

The admin CLI calls Python internals directly and does not expose filesystem mutation tools.

## Environment variables

### Required for normal local runtime

```powershell
$env:ALETHEIA_PROJECT_ROOT="C:\path\to\project"
$env:ALETHEIA_STATE_DIR="C:\path\to\project\.aletheia_state"
$env:ALETHEIA_ALLOWED_ROOTS="C:\path\to\project"
$env:ALETHEIA_CHROMA_PATH="C:\path\to\project\.aletheia_state\chroma"
$env:ALETHEIA_LM_STUDIO_BASE_URL="http://localhost:1234/v1"
$env:ALETHEIA_EMBEDDING_MODEL="nomic-ai/nomic-embed-text-v1.5-GGUF"
$env:ALETHEIA_PROJECT_ID="my-project"
$env:ALETHEIA_BRIDGE_HOST="127.0.0.1"
$env:ALETHEIA_BRIDGE_PORT="8765"
$env:ALETHEIA_BRIDGE_SECRET="replace-with-local-random-secret"
$env:ALETHEIA_APPROVAL_SECRET="replace-with-local-random-secret"
```

### Optional

```powershell
$env:ALETHEIA_ENABLE_ADMIN_BRIDGE="false"
$env:ALETHEIA_OCR_COMMAND="C:\path\to\ocr-command.exe"
$env:ALETHEIA_LOG_LEVEL="INFO"
$env:ALETHEIA_WORKER_ID="aletheia-worker-1"
$env:ALETHEIA_LEASE_SECONDS="60"
$env:ALETHEIA_IDLE_SLEEP_SECONDS="0.25"
```

### Node MCP bridge

```powershell
$env:ALETHEIA_PYTHON_BRIDGE="tcp://127.0.0.1:8765"
$env:ALETHEIA_BRIDGE_SECRET="replace-with-local-random-secret"
```

## Setup

### Python daemon

From `backend/python-daemon`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

If your environment does not install optional runtime dependencies automatically, install the needed local runtime packages for Chroma, HTTP calls, and PDF processing according to `pyproject.toml` and your local deployment needs.

### Node MCP gateway

From `backend/node-mcp`:

```powershell
node test\run-tests.mjs
```

The Node gateway currently uses built-in Node modules only unless future changes add dependencies.

## Running the backend

### Start LM Studio

Start LM Studio and load an embedding model compatible with the configured `ALETHEIA_EMBEDDING_MODEL`. The daemon expects an OpenAI-compatible embeddings endpoint at:

```text
http://localhost:1234/v1/embeddings
```

### Start Python daemon

From `backend/python-daemon`:

```powershell
python -m orchestrator.main
```

Or, if installed as a script:

```powershell
aletheia-daemon
```

### Start Node MCP gateway

From the repository root or from `backend/node-mcp`:

```powershell
node backend\node-mcp\src\server.mjs
```

Point your MCP client at this Node stdio process.

## Admin CLI

From `backend/python-daemon`, with the environment configured:

```powershell
aletheia-admin show-config
aletheia-admin health
aletheia-admin reconcile-project my-project
aletheia-admin list-dead-letters --limit 25
```

Admin CLI operations are for local operator diagnostics and recovery. They are not public MCP tools.

## Controlled smoke test

Use a tiny disposable fixture before ingesting real project directories.

1. Create a fixture directory:

   ```powershell
   mkdir C:\tmp\aletheia_fixture
   Set-Content C:\tmp\aletheia_fixture\sample.txt "Aletheia smoke test semantic memory fixture."
   ```

2. Set runtime environment:

   ```powershell
   $env:ALETHEIA_PROJECT_ROOT="C:\tmp\aletheia_fixture"
   $env:ALETHEIA_STATE_DIR="C:\tmp\aletheia_fixture\.aletheia_state"
   $env:ALETHEIA_ALLOWED_ROOTS="C:\tmp\aletheia_fixture"
   $env:ALETHEIA_CHROMA_PATH="C:\tmp\aletheia_fixture\.aletheia_state\chroma"
   $env:ALETHEIA_PROJECT_ID="aletheia-fixture"
   $env:ALETHEIA_BRIDGE_SECRET="replace-with-local-random-secret"
   $env:ALETHEIA_APPROVAL_SECRET="replace-with-local-random-secret"
   $env:ALETHEIA_PYTHON_BRIDGE="tcp://127.0.0.1:8765"
   ```

3. Start LM Studio with embeddings enabled.
4. Start the Python daemon.
5. Start the Node MCP gateway.
6. From your MCP client, call:

   ```text
   mcp_scout_workspace(project_id="aletheia-fixture", absolute_path="C:\tmp\aletheia_fixture")
   mcp_ingest_target(project_id="aletheia-fixture", absolute_path="C:\tmp\aletheia_fixture\sample.txt")
   mcp_semantic_search(project_id="aletheia-fixture", query="semantic memory fixture")
   ```

7. Edit `sample.txt`, re-run `mcp_ingest_target`, and confirm stale content does not appear in search.
8. Run:

   ```powershell
   aletheia-admin health
   aletheia-admin reconcile-project aletheia-fixture
   aletheia-admin list-dead-letters --limit 25
   ```

The smoke test is successful when scout, ingest, search, reconcile, and dead-letter inspection complete without unexpected errors.

## Tests

### Python

```powershell
cd backend\python-daemon
python -m unittest discover -s tests -v
```

Latest reported post-hardening result:

```text
56 tests passing
0 failures
```

### Node

```powershell
cd backend\node-mcp
node test\run-tests.mjs
```

Latest reported post-hardening result:

```text
9 tests passing
0 failures
```

Live integration tests that require LM Studio, real Chroma state, PDF/OCR binaries, or external MCP clients should be opt-in and must not run in the default unit suite.

## Operational notes

- SQLite migrations run automatically on daemon startup through `bootstrap_databases`.
- Unknown future schema versions should fail startup clearly.
- `queue.db` stores task and ingestion state.
- `control.db` stores worker/process/dead-letter operational state.
- Worker heartbeats and leases are recoverable through repository recovery primitives.
- Failed vector upserts should remain rebuildable from SQLite chunk content.
- Chroma can be rebuilt with `aletheia-admin reconcile-project`.

## Production constraints

Do not add the following to this runtime without a separate architecture review:

- browser UI or dashboard
- Flask/FastAPI/Next.js/web server control plane
- legacy FastMCP runtime server
- ChatML prompt routing
- model training or fine-tuning pipeline
- file watchers
- public SQLite query MCP tool
- filesystem write/delete/create tools outside HITL approval
- speculative or narrative subsystems unrelated to backend orchestration

## Git hygiene

Before committing, check:

```powershell
git status
```

Commit source files and docs only. Do not commit runtime databases, Chroma stores, logs, generated bundles, cache directories, virtual environments, or local secrets.
