import yaml
# Workspace Bundle: backend
# Generated: 2026-05-02T21:20:01
# Compliance: os.scandir traversal; binary guard; PEM + entropy redaction; polyglot summaries

# Project Structure:
# backend/
#   |-- Aletheia_BACKEND_README.md
#   |-- lmstudio_fastmcp_shim.py
#   |-- node-mcp/
#     |-- package.json
#     |-- src/
#       |-- bridge.mjs
#       |-- contracts.mjs
#       |-- server.mjs
#     |-- test/
#       |-- bridge-integration.test.mjs
#       |-- bridge.test.mjs
#       |-- contracts.test.mjs
#       |-- run-tests.mjs
#       |-- scout-contract.test.mjs
#   |-- python-daemon/
#     |-- orchestrator/
#       |-- __init__.py
#       |-- adapters.py
#       |-- admin.py
#       |-- approval.py
#       |-- bridge_server.py
#       |-- chroma_manager.py
#       |-- config.py
#       |-- dag_runtime.py
#       |-- db_bootstrap.py
#       |-- epistemic.py
#       |-- execution_loop.py
#       |-- hitl.py
#       |-- ingest/
#         |-- __init__.py
#         |-- processors.py
#         |-- service.py
#       |-- lm_studio_manager.py
#       |-- main.py
#       |-- observability.py
#       |-- ocr.py
#       |-- queue_repo.py
#       |-- recovery.py
#       |-- reroll.py
#       |-- runtime.py
#       |-- shell.py
#       |-- worker.py
#     |-- pyproject.toml
#     |-- tests/
#       |-- test_approval.py
#       |-- test_bridge_server.py
#       |-- test_chroma_and_ingest.py
#       |-- test_dag_runtime.py
#       |-- test_db_and_dag.py
#       |-- test_epistemic_and_reroll.py
#       |-- test_execution_loop_adapters.py
#       |-- test_hitl_and_shell.py
#       |-- test_processors_and_tools.py
#       |-- test_runtime_daemon.py
#   |-- README.md

--- FILE: Aletheia_BACKEND_README.md ---
Size: 10402 bytes
Summary: Headers: Aletheia Backend Orchestrator, Runtime architecture, Process roles, Repository layout, Public MCP tools, Ingestion hygiene, Security model, Bridge auth, Admin bridge methods, Environment variables
Content: |
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
  - **LM Studio FastMCP shim**: current LM Studio integration uses `lmstudio_fastmcp_shim.py` into the Python daemon TCP bridge rather than the generic Node stdio gateway.
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
  
  ## Ingestion hygiene
  
  Avoid ingesting generated extraction bundles and directories such as `New project_bundle_*`, `*_bundle*.py`, or `*_bundle*.yaml` to prevent pollution of the semantic index.
  
  ## Security model
  
  ### Bridge auth
  
  The Python bridge supports per-request HMAC authentication when `ALETHEIA_BRIDGE_SECRET` is set.= [REDACTED_HIGH_ENTROPY]
  
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
  $env:ALETHEIA_BRIDGE_SECRET= [REDACTED_HIGH_ENTROPY]
  $env:ALETHEIA_APPROVAL_SECRET= [REDACTED_HIGH_ENTROPY]
  ```
  
  ### Optional
  
  ```powershell
  $env:ALETHEIA_ENABLE_ADMIN_BRIDGE="false"
  $env:ALETHEIA_OCR_COMMAND="C:\path\to\ocr-command.exe"
  $env:ALETHEIA_LOG_LEVEL="INFO"
  $env:ALETHEIA_WORKER_ID="aletheia-worker-1"
  $env:ALETHEIA_LEASE_SECONDS="60"
  $env:ALETHEIA_IDLE_SLEEP_SECONDS="0.25"
  $env:ALETHEIA_LM_STUDIO_API_BASE_URL= [REDACTED_HIGH_ENTROPY]
  $env:ALETHEIA_LM_STUDIO_API_TOKEN= [REDACTED_HIGH_ENTROPY]
  $env:ALETHEIA_AUTO_LOAD_EMBEDDING_MODEL="true"
  ```
  
  ### Node MCP bridge
  
  ```powershell
  $env:ALETHEIA_PYTHON_BRIDGE="tcp://127.0.0.1:8765"
  $env:ALETHEIA_BRIDGE_SECRET= [REDACTED_HIGH_ENTROPY]
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
     $env:ALETHEIA_BRIDGE_SECRET= [REDACTED_HIGH_ENTROPY]
     $env:ALETHEIA_APPROVAL_SECRET= [REDACTED_HIGH_ENTROPY]
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

--- FILE: README.md ---
Size: 4802 bytes
Summary: Headers: Aletheia Backend Runtime, Python Daemon, Node MCP Gateway, LM Studio embedding model readiness, Admin CLI, Operations, Smoke Test, Tests, Production Constraints
Content: |
  # Aletheia Backend Runtime
  
  The runtime has two processes:
  
  - Python daemon= [REDACTED_HIGH_ENTROPY]
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
  $env:ALETHEIA_BRIDGE_SECRET= [REDACTED_HIGH_ENTROPY]
  $env:ALETHEIA_PROJECT_ID="my-project"  # defaults to project root name
  $env:ALETHEIA_ENABLE_ADMIN_BRIDGE="false"  # enable daemon.* admin methods
  $env:ALETHEIA_APPROVAL_SECRET= [REDACTED_HIGH_ENTROPY]
  python -m orchestrator.main
  ```
  
  The installed script entrypoint is also available as `aletheia-daemon`.
  
  ## Node MCP Gateway
  
  Point the Node gateway at the Python bridge:
  
  ```powershell
  $env:ALETHEIA_PYTHON_BRIDGE="tcp://127.0.0.1:8765"
  $env:ALETHEIA_BRIDGE_SECRET= [REDACTED_HIGH_ENTROPY]
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
  $env:ALETHEIA_LM_STUDIO_API_BASE_URL= [REDACTED_HIGH_ENTROPY]
  $env:ALETHEIA_LM_STUDIO_API_TOKEN= [REDACTED_HIGH_ENTROPY]
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

--- FILE: node-mcp/package.json ---
Size: 153 bytes
Summary: Keys: name, version, type, private, scripts
Content: |
  {
    "name": "aletheia-node-mcp",
    "version": "0.1.0",
    "type": "module",
    "private": true,
    "scripts": {
      "test": "node test/run-tests.mjs"
    }
  }

--- FILE: node-mcp/src/bridge.mjs ---
Size: 3240 bytes
Summary: (none)
Content: |
  import net from "node:net";
  import crypto from "node:crypto";
  
  export function makeJsonRpcRequest(method, params, id = 1) {
    return { jsonrpc: "2.0", id, method, params };
  }
  
  export async function bridgeCall(toolName, args, transport = null, options = {}) {
    const sharedSecret = [REDACTED_HIGH_ENTROPY]
    const params = { toolName, args };
    const request = makeJsonRpcRequest("tools.call", params, Date.now());
    if (sharedSecret) {
      request.params.auth = buildAuthEnvelope(request, sharedSecret);
    }
    if (transport) {
      const response = await transport(request);
      return response?.result ?? response;
    }
    const bridgePath = options.bridgePath ?? process.env.ALETHEIA_PYTHON_BRIDGE;
    if (!bridgePath) {
      throw new Error("ALETHEIA_PYTHON_BRIDGE is required for runtime bridge calls");
    }
    return sendJsonRpcLine(bridgePath, request, options.timeoutMs);
  }
  
  export function stableStringify(value) {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(",")}]`;
    return `{${Object.keys(value).sort().map((key) = [REDACTED_HIGH_ENTROPY]
  }
  
  export function buildAuthEnvelope(request, sharedSecret, timestamp = [REDACTED_HIGH_ENTROPY]
    const sanitized = JSON.parse(JSON.stringify(request));
    if (sanitized.params && typeof sanitized.params === "object") {
      delete sanitized.params.auth;
    }
    const payload = `${timestamp}.${nonce}.${stableStringify(sanitized)}`;
    const signature = [REDACTED_HIGH_ENTROPY]
    return { timestamp, signature, nonce };
  }
  
  export function connectNamedPipe(path) {
    if (path.startsWith("tcp://")) {
      const url = new URL(path);
      return net.createConnection({ host: url.hostname, port: Number(url.port) });
    }
    return net.createConnection(path);
  }
  
  export function sendJsonRpcLine(path, request, timeoutMs = 30000) {
    return new Promise((resolve, reject) => {
      const socket = connectNamedPipe(path);
      let buffer = "";
      let settled = false;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        socket.destroy();
        reject(new Error(`Python bridge request timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      function finish(fn, value) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        fn(value);
      }
      socket.setEncoding("utf8");
      socket.on("error", (error) => finish(reject, error));
      socket.on("connect", () => {
        socket.write(JSON.stringify(request) + "\n");
      });
      socket.on("data", (chunk) => {
        buffer += chunk;
        const newline = buffer.indexOf("\n");
        if (newline < 0) return;
        const line = buffer.slice(0, newline).trim();
        socket.end();
        try {
          const response = JSON.parse(line);
          if (response.error) {
            finish(reject, new Error(response.error.message || "Python bridge error"));
            return;
          }
          finish(resolve, response.result);
        } catch (error) {
          finish(reject, error);
        }
      });
    });
  }

--- FILE: node-mcp/src/contracts.mjs ---
Size: 6124 bytes
Summary: (none)
Content: |
  const DRAFT7 = "http://json-schema.org/draft-07/schema#";
  
  export const CONTRACTS = [
    {
      name: "mcp_extract_image",
      description: "Run OCR fallback against non-selectable text content.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          absolute_path: { type: "string", minLength: 1 },
          page: { type: "integer", minimum: 1 },
          region: {
            type: "object",
            additionalProperties: false,
            properties: {
              x: { type: "integer", minimum: 0 },
              y: { type: "integer", minimum: 0 },
              width: { type: "integer", minimum: 1 },
              height: { type: "integer", minimum: 1 },
            },
            required: ["x", "y", "width", "height"],
          },
        },
        required: ["absolute_path"],
      },
    },
    {
      name: "mcp_ingest_target",
      description: "Route a local file to PDFProcessor or CodebaseProcessor by MIME type.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          project_id: { type: "string", minLength: 1 },
          absolute_path: { type: "string", minLength: 1 },
          mime_type: { type: "string", minLength: 1 },
          force_reindex: { type: "boolean", default: false },
        },
        required: ["project_id", "absolute_path"],
      },
    },
    {
      name: "mcp_semantic_search",
      description: "Run cosine similarity search inside an isolated project namespace.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          project_id: { type: "string", minLength: 1 },
          query: { type: "string", minLength: 1 },
          k: { type: "integer", minimum: 1, maximum: 50, default: 8 },
        },
        required: ["project_id", "query"],
      },
    },
    {
      name: "mcp_scout_workspace",
      description: "Return a deterministic read-only workspace scout without indexing vectors.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          project_id: { type: "string", minLength: 1 },
          absolute_path: { type: "string", minLength: 1 },
          max_files: { type: "integer", minimum: 1, maximum: 5000, default: 500 },
          include_summaries: { type: "boolean", default: true },
        },
        required: ["project_id", "absolute_path"],
      },
    },
    {
      name: "mcp_verify_integrity",
      description: "Verify a file against expected metadata and cryptographic hashes.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          absolute_path: { type: "string", minLength: 1 },
          expected_sha256: { type: "string", pattern: "^[a-fA-F0-9]{64}$" },
          expected_metadata_hash: { type: "string", minLength: 1 },
        },
        required: ["absolute_path", "expected_sha256", "expected_metadata_hash"],
      },
    },
  ].sort((a, b) => a.name.localeCompare(b.name));
  
  export function findContract(name) {
    return CONTRACTS.find((contract) => contract.name === name);
  }
  
  export function validateToolInput(name, args) {
    const contract = findContract(name);
    if (!contract) {
      return { ok: false, error: "unknown_tool", details: [{ message: `Unknown tool: ${name}` }] };
    }
    return validateObject(contract.inputSchema, args ?? {}, "");
  }
  
  function validateObject(schema, value, path) {
    const details = [];
    if (schema.type === "object") {
      if (!value || typeof value !== "object" || Array.isArray(value)) {
        return { ok= [REDACTED_HIGH_ENTROPY]
      }
      const properties = schema.properties ?? {};
      for (const required of schema.required ?? []) {
        if (!Object.hasOwn(value, required)) {
          details.push({ path: joinPath(path, required), keyword: "required", message: `${required} is required` });
        }
      }
      if (schema.additionalProperties === false) {
        for (const key of Object.keys(value)) {
          if (!Object.hasOwn(properties, key)) {
            details.push({ path= [REDACTED_HIGH_ENTROPY]
          }
        }
      }
      for (const [key, childSchema] of Object.entries(properties)) {
        if (Object.hasOwn(value, key)) {
          details.push(...validateValue(childSchema, value[key], joinPath(path, key)));
        }
      }
    }
    return details.length === 0
      ? { ok: true }
      : { ok: false, error: "schema_validation_failed", details };
  }
  
  function validateValue(schema, value, path) {
    if (schema.type === "object") {
      return validateObject(schema, value, path).details ?? [];
    }
    const details = [];
    if (schema.type === "string") {
      if (typeof value !== "string") {
        details.push({ path, keyword: "type", message: "must be string" });
      } else {
        if (schema.minLength && value.length < schema.minLength) {
          details.push({ path, keyword: "minLength", message: `length must be >= [REDACTED_HIGH_ENTROPY]
        }
        if (schema.pattern && !(new RegExp(schema.pattern).test(value))) {
          details.push({ path, keyword: "pattern", message: `must match ${schema.pattern}` });
        }
      }
    }
    if (schema.type === "boolean" && typeof value !== "boolean") {
      details.push({ path, keyword: "type", message: "must be boolean" });
    }
    if (schema.type === "integer") {
      if (!Number.isInteger(value)) {
        details.push({ path, keyword: "type", message: "must be integer" });
      } else {
        if (schema.minimum !== undefined && value < schema.minimum) {
          details.push({ path, keyword: "minimum", message: `must be >= [REDACTED_HIGH_ENTROPY]
        }
        if (schema.maximum !== undefined && value > schema.maximum) {
          details.push({ path, keyword: "maximum", message: `must be <= ${schema.maximum}` });
        }
      }
    }
    return details;
  }
  
  function joinPath(prefix, key) {
    return `${prefix}/${key}`;
  }

--- FILE: node-mcp/src/server.mjs ---
Size: 2109 bytes
Summary: (none)
Content: |
  import { stdin, stdout, stderr } from "node:process";
  
  import { bridgeCall } from "./bridge.mjs";
  import { CONTRACTS, validateToolInput } from "./contracts.mjs";
  
  export async function makeToolResult(name, args, bridge = bridgeCall) {
    const validation = validateToolInput(name, args);
    if (!validation.ok) {
      return {
        isError: true,
        content: [{ type: "text", text: JSON.stringify(validation) }],
        structuredContent: { ok: false, ...validation },
      };
    }
    const result = await bridge(name, args);
    return {
      isError: result?.ok === false,
      content: [{ type: "text", text: JSON.stringify(result) }],
      structuredContent: result,
    };
  }
  
  export function listTools() {
    return CONTRACTS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema }));
  }
  
  export async function handleJsonRpc(message, bridge = bridgeCall) {
    if (message.method === "initialize") {
      return { jsonrpc: "2.0", id: message.id, result: { protocolVersion: "2025-06-18", serverInfo: { name: "aletheia-orchestrator", version: "0.1.0" } } };
    }
    if (message.method === "tools/list") {
      return { jsonrpc: "2.0", id: message.id, result: { tools: listTools() } };
    }
    if (message.method === "tools/call") {
      const name = message.params?.name;
      const args = message.params?.arguments ?? {};
      return { jsonrpc: "2.0", id: message.id, result: await makeToolResult(name, args, bridge) };
    }
    return { jsonrpc: "2.0", id: message.id, error: { code: -32601, message: "Method not found" } };
  }
  
  export async function serveStdio() {
    let buffer = "";
    stdin.setEncoding("utf8");
    stdin.on("data", async (chunk) => {
      buffer += chunk;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const response = await handleJsonRpc(JSON.parse(line));
          stdout.write(`${JSON.stringify(response)}\n`);
        } catch (error) {
          stderr.write(`${String(error)}\n`);
        }
      }
    });
  }
  
  if (import.meta.url === `file://${process.argv[1]}`) {
    serveStdio();
  }

--- FILE: node-mcp/test/bridge-integration.test.mjs ---
Size: 3886 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import net from "node:net";
  import { test } from "node:test";
  
  import { bridgeCall, buildAuthEnvelope } from "../src/bridge.mjs";= [REDACTED_HIGH_ENTROPY]
  import { makeToolResult } from "../src/server.mjs";
  
  test("default bridge refuses runtime stub mode without a Python bridge path", async () => {
    const previous = process.env.ALETHEIA_PYTHON_BRIDGE;
    delete process.env.ALETHEIA_PYTHON_BRIDGE;
    await assert.rejects(() => bridgeCall("mcp_scout_workspace", { project_id: "p" }), /ALETHEIA_PYTHON_BRIDGE/);
    if (previous !== undefined) process.env.ALETHEIA_PYTHON_BRIDGE = previous;
  });
  
  test("tools call reaches Python JSON-RPC bridge path", async () => {
    const seen = [];
    const server = net.createServer((socket) => {
      let buffer = "";
      socket.on("data", (chunk) => {
        buffer += chunk.toString("utf8");
        const line = buffer.split(/\r?\n/)[0];
        if (!line) return;
        const request = JSON.parse(line);
        seen.push(request);
        socket.write(JSON.stringify({
          jsonrpc: "2.0",
          id: request.id,
          result: { ok: true, python: true, params: request.params },
        }) + "\n");
      });
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    const path = `tcp://127.0.0.1:${address.port}`;
    const previous = process.env.ALETHEIA_PYTHON_BRIDGE;
    process.env.ALETHEIA_PYTHON_BRIDGE = path;
    try {
      const result = await makeToolResult("mcp_scout_workspace", { project_id: "p", absolute_path: "C:/x" });
      assert.equal(result.isError, false);
      assert.equal(result.structuredContent.python, true);
      assert.equal(seen[0].method, "tools.call");
      assert.equal(seen[0].params.toolName, "mcp_scout_workspace");
    } finally {
      if (previous === undefined) delete process.env.ALETHEIA_PYTHON_BRIDGE;
      else process.env.ALETHEIA_PYTHON_BRIDGE = previous;
      await new Promise((resolve) => server.close(resolve));
    }
  });
  
  test("bridge rejects with a clear timeout error", async () => {
    const server = net.createServer((socket) => {
      socket.on("data", () => {
        // Hold the connection open without responding.
      });
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    try {
      await assert.rejects(
        () => bridgeCall(
          "mcp_scout_workspace",
          { project_id: "p" },
          null,
          { bridgePath: `tcp://127.0.0.1:${address.port}`, timeoutMs: 20 },
        ),
        /Python bridge request timed out/,
      );
    } finally {
      await new Promise((resolve) => server.close(resolve));
    }
  });
  
  test("bridge includes configured HMAC auth envelope in JSON-RPC params", async () = [REDACTED_HIGH_ENTROPY]
    const seen = [];
    const server = net.createServer((socket) => {
      socket.on("data", (chunk) => {
        const request = JSON.parse(chunk.toString("utf8").split(/\r?\n/)[0]);
        seen.push(request);
        socket.write(JSON.stringify({ jsonrpc: "2.0", id: request.id, result: { ok: true } }) + "\n");
      });
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    const previous = [REDACTED_HIGH_ENTROPY]
    process.env.ALETHEIA_BRIDGE_SECRET = [REDACTED_HIGH_ENTROPY]
    try {
      await bridgeCall("mcp_scout_workspace", { project_id: "p" }, null, {
        bridgePath: `tcp://127.0.0.1:${address.port}`,
        timeoutMs: 1000,
      });
      assert.equal(typeof seen[0].params.auth.timestamp, "string");
      assert.equal(typeof seen[0].params.auth.signature, "string");
      assert.equal(typeof seen[0].params.auth.nonce, "string");
      assert.match(seen[0].params.auth.signature, /^[a-f0-9]{64}$/);= [REDACTED_HIGH_ENTROPY]
    } finally {
      if (previous = [REDACTED_HIGH_ENTROPY]
      else process.env.ALETHEIA_BRIDGE_SECRET = previous;
      await new Promise((resolve) => server.close(resolve));
    }
  });

--- FILE: node-mcp/test/bridge.test.mjs ---
Size: 932 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import { test } from "node:test";
  
  import { makeToolResult } from "../src/server.mjs";
  
  test("invalid tool input is returned as a model-observable error result", async () => {
    const result = await makeToolResult("mcp_semantic_search", { project_id: "p" }, async () => {
      throw new Error("bridge should not run");
    });
  
    assert.equal(result.isError, true);
    assert.equal(result.structuredContent.ok, false);
    assert.equal(result.structuredContent.error, "schema_validation_failed");
  });
  
  test("valid tool input is forwarded to bridge", async () => {
    const result = await makeToolResult("mcp_semantic_search", { project_id: "p", query: "q" }, async (name, args) => {
      return { ok: true, name, args };
    });
  
    assert.equal(result.isError, false);
    assert.equal(result.structuredContent.name, "mcp_semantic_search");
    assert.equal(result.structuredContent.args.query, "q");
  });

--- FILE: node-mcp/test/contracts.test.mjs ---
Size: 960 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import { test } from "node:test";
  
  import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";
  
  test("contracts are deterministic and strict host metadata is outside input schema", () => {
    const names = CONTRACTS.map((contract) => contract.name);
    assert.deepEqual(names, [...names].sort());
    for (const contract of CONTRACTS) {
      assert.equal(contract.strict, true);
      assert.equal(contract.inputSchema.additionalProperties, false);
      assert.equal(Object.hasOwn(contract.inputSchema, "strict"), false);
    }
  });
  
  test("schema validation returns structured exact failures", () => {
    const result = validateToolInput("mcp_semantic_search", { project_id: "p", extra: true });
  
    assert.equal(result.ok, false);
    assert.equal(result.error, "schema_validation_failed");
    assert.match(JSON.stringify(result.details), /query/);
    assert.match(JSON.stringify(result.details), /additionalProperties/);
  });

--- FILE: node-mcp/test/run-tests.mjs ---
Size: 135 bytes
Summary: (none)
Content: |
  import "./contracts.test.mjs";
  import "./bridge.test.mjs";
  import "./scout-contract.test.mjs";
  import "./bridge-integration.test.mjs";

--- FILE: node-mcp/test/scout-contract.test.mjs ---
Size: 744 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import { test } from "node:test";
  
  import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";
  
  test("mcp_scout_workspace contract is strict and validates expected payload", () => {
    const contract = CONTRACTS.find((item) => item.name === "mcp_scout_workspace");
  
    assert.ok(contract);
    assert.equal(contract.inputSchema.additionalProperties, false);
    assert.equal(validateToolInput("mcp_scout_workspace", { project_id: "p", absolute_path: "C:/x" }).ok, true);
    const invalid = validateToolInput("mcp_scout_workspace", { project_id: "p", absolute_path: "C:/x", extra: true });
    assert.equal(invalid.ok, false);
    assert.match(JSON.stringify(invalid.details), /additionalProperties/);
  });

--- FILE: python-daemon/orchestrator/__init__.py ---
Size: 45 bytes
Summary: 
Content: |
  """Aletheia authoritative daemon package."""

--- FILE: python-daemon/pyproject.toml ---
Size: 444 bytes
Summary: (none)
Content: |
  [project]
  name = "aletheia-orchestrator"
  version = "0.1.0"
  requires-python = ">=3.11"
  description = "Authoritative Python daemon for the Aletheia agentic orchestrator."
  dependencies = [
    "chromadb",
    "requests",
    "PyMuPDF",
    "PyYAML",
  ]
  
  [project.optional-dependencies]
  ocr = []
  live = []
  
  [project.scripts]
  aletheia-daemon = "orchestrator.main:main"
  aletheia-admin = "orchestrator.admin:main"
  
  [tool.pytest.ini_options]
  pythonpath = ["."]

--- FILE: python-daemon/orchestrator/dag_runtime.py ---
Size: 1124 bytes
Summary: Functions: topological_descendants, _collect_descendants
Content: |
  from __future__ import annotations
  
  from graphlib import TopologicalSorter
  
  
  def topological_descendants(root_task_id: str, edges: list[tuple[str, str]]) -> list[str]:
      descendants = _collect_descendants(root_task_id, edges)
      sorter = TopologicalSorter()
      for node in descendants:
          sorter.add(node)
      for parent, child in edges:
          if child not in descendants:
              continue
          if parent == root_task_id:
              sorter.add(child)
          elif parent in descendants:
              sorter.add(child, parent)
      return [node for node in sorter.static_order() if node in descendants]
  
  
  def _collect_descendants(root_task_id: str, edges: list[tuple[str, str]]) -> set[str]:
      children_by_parent: dict[str, list[str]] = {}
      for parent, child in edges:
          children_by_parent.setdefault(parent, []).append(child)
      seen: set[str] = set()
      stack = list(children_by_parent.get(root_task_id, []))
      while stack:
          node = stack.pop()
          if node in seen:
              continue
          seen.add(node)
          stack.extend(children_by_parent.get(node, []))
      return seen

--- FILE: python-daemon/orchestrator/epistemic.py ---
Size: 1115 bytes
Summary: Classes: EpistemicSignals, EpistemicScore, EpistemicPolicy; Functions: score
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass
  
  
  @dataclass(frozen=True)
  class EpistemicSignals:
      logic_signal: float
      sycophancy_signal: float
  
  
  @dataclass(frozen=True)
  class EpistemicScore:
      slr_score: float
      depth_penalty: float
      final_score: float
      decision: str
  
  
  @dataclass(frozen=True)
  class EpistemicPolicy:
      minor_threshold: float = 0.22
      major_threshold: float = 0.35
      depth_penalty: float = 1.35
  
      def score(self, signals: EpistemicSignals, *, base_score: float, depth: int) -> EpistemicScore:
          slr_score = signals.sycophancy_signal / max(signals.logic_signal, 1e-6)
          penalty = depth * self.depth_penalty
          final_score = base_score - penalty
          if slr_score >= self.major_threshold:
              decision = "identity_freeze"
          elif slr_score >= self.minor_threshold:
              decision = "reroll"
          else:
              decision = "route"
          return EpistemicScore(
              slr_score=slr_score,
              depth_penalty=penalty,
              final_score=final_score,
              decision=decision,
          )

--- FILE: python-daemon/orchestrator/ingest/__init__.py ---
Size: 322 bytes
Summary: 
Content: |
  from .processors import DocumentChunk, MetadataAdapter, SemanticSlicerAdapter, TextProcessorAdapter, WorkspaceScout
  from .service import IngestTargetService
  
  __all__ = [
      "DocumentChunk",
      "IngestTargetService",
      "MetadataAdapter",
      "SemanticSlicerAdapter",
      "TextProcessorAdapter",
      "WorkspaceScout",
  ]

--- FILE: python-daemon/tests/test_dag_runtime.py ---
Size: 525 bytes
Summary: Classes: DagRuntimeTests; Functions: test_orders_descendants_before_their_children
Content: |
  import unittest
  
  from orchestrator.dag_runtime import topological_descendants
  
  
  class DagRuntimeTests(unittest.TestCase):
      def test_orders_descendants_before_their_children(self):
          edges = [("root", "child"), ("child", "grandchild"), ("root", "sibling")]
  
          ordered = topological_descendants("root", edges)
  
          self.assertEqual(set(ordered), {"child", "grandchild", "sibling"})
          self.assertLess(ordered.index("child"), ordered.index("grandchild"))
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/tests/test_bridge_server.py ---
Size: 872 bytes
Summary: Classes: FakeAdapters, BridgeServerTests; Functions: call_mcp_tool, test_tools_call_reaches_python_tool_adapters
Content: |
  import unittest
  
  from orchestrator.adapters import ToolAdapters
  from orchestrator.bridge_server import handle_json_rpc
  
  
  class FakeAdapters(ToolAdapters):
      def call_mcp_tool(self, tool_name, args):
          return {"ok": True, "tool_name": tool_name, "args": args}
  
  
  class BridgeServerTests(unittest.TestCase):
      def test_tools_call_reaches_python_tool_adapters(self):
          response = handle_json_rpc(
              {
                  "jsonrpc": "2.0",
                  "id": 7,
                  "method": "tools.call",
                  "params": {"toolName": "mcp_scout_workspace", "args": {"project_id": "p"}},
              },
              FakeAdapters(),
          )
  
          self.assertEqual(response["result"]["tool_name"], "mcp_scout_workspace")
          self.assertEqual(response["result"]["args"], {"project_id": "p"})
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/orchestrator/hitl.py ---
Size: 1360 bytes
Summary: Classes: ApprovalGate; Functions: __init__, _event
Content: |
  from __future__ import annotations
  
  import asyncio
  import hmac
  
  from .queue_repo import QueueRepository
  
  
  class ApprovalGate:
      def __init__(self, repo: QueueRepository, secret: bytes) -> None:
          self.repo = repo
          self.secret = secret
          self._events: dict[str, asyncio.Event] = {}
  
      def _event(self, task_id: str) -> asyncio.Event:
          if task_id not in self._events:
              self._events[task_id] = asyncio.Event()
          return self._events[task_id]
  
      async def wait_for_approval(self, task_id: str, *, timeout: float | None = None) -> None:
          task = self.repo.get_task(task_id)
          if task["state"] != "PENDING_APPROVAL":
              return
          await asyncio.wait_for(self._event(task_id).wait(), timeout=timeout)
  
      async def authorize(self, task_id: str, authorization_hash: str, diff_bytes: bytes) -> bool:
          expected = hmac.digest(self.secret, diff_bytes, "sha256").hex()
          if not hmac.compare_digest(expected, authorization_hash):
              return False
          self.repo.approve_task(task_id, "stdin-or-socket")
          self._event(task_id).set()
          return True
  
      async def reject(self, task_id: str, *, decided_by: str, reason: str) -> list[str]:
          pruned = self.repo.reject_approval(task_id, decided_by, reason)
          self._event(task_id).set()
          return pruned

--- FILE: python-daemon/orchestrator/lm_studio_manager.py ---
Size: 4574 bytes
Summary: Classes: LMStudioManagerError, LMStudioModel, LMStudioManagerConfig, LMStudioManager; Functions: __init__, _headers, list_models, find_model, ensure_embedding_model_loaded
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass
  from typing import Any, Callable
  import requests
  
  
  class LMStudioManagerError(ValueError):
      pass
  
  
  @dataclass(frozen=True)
  class LMStudioModel:
      key: str
      type: str
      state: str | None = None
      raw: dict[str, Any] | None = None
  
  
  @dataclass(frozen=True)
  class LMStudioManagerConfig:
      api_base_url: str = "http://127.0.0.1:1234/api/v1"
      api_token: str | None = None
      request_timeout_seconds: float = 30.0
  
  
  class LMStudioManager:
      def __init__(
          self,
          config: LMStudioManagerConfig,
          *,
          http_get: Callable[..., Any] = requests.get,
          http_post: Callable[..., Any] = requests.post,
      ) -> None:
          self.config = config
          self.http_get = http_get
          self.http_post = http_post
  
      def _headers(self) -> dict[str, str]:
          headers = {"Content-Type": "application/json"}
          if self.config.api_token:
              headers["Authorization"] = f"Bearer {self.config.api_token}"
          return headers
  
      def list_models(self) -> list[LMStudioModel]:
          try:
              response = self.http_get(
                  url=f"{self.config.api_base_url.rstrip('/')}/models",
                  headers=self._headers(),
                  timeout=self.config.request_timeout_seconds,
              )
              response.raise_for_status()
              data = response.json()
              models_data = data.get("models") or data.get("data") or []
              models = []
              for item in models_data:
                  key = item.get("key") or item.get("id")
                  if not key:
                      continue
                  models.append(
                      LMStudioModel(
                          key=key,
                          type=item.get("type", "unknown"),
                          state=item.get("state"),
                          raw=item,
                      )
                  )
              return models
          except requests.HTTPError as exc:
              if exc.response.status_code == 401:
                  raise LMStudioManagerError(
                      "LM Studio API rejected request; set ALETHEIA_LM_STUDIO_API_TOKEN or disable LM Studio API auth."
                  ) from exc
              raise LMStudioManagerError(f"LM Studio API request failed: {exc}") from exc
          except Exception as exc:
              raise LMStudioManagerError(f"LM Studio API request failed: {exc}") from exc
  
      def find_model(self, model_key: str) -> LMStudioModel | None:
          models = self.list_models()
          for model in models:
              if model.key == model_key:
                  return model
          return None
  
      def ensure_embedding_model_loaded(self, model_key: str) -> None:
          model = self.find_model(model_key)
          if model is None:
              raise LMStudioManagerError(f"embedding model not found in LM Studio: {model_key}")
          if model.type not in {"embedding", "embeddings"}:
              raise LMStudioManagerError(f"configured embedding model is not an embedding model: {model_key} (type: {model.type})")
          if model.state in {"loaded", "running", "ready"}:
              return
          payload = {"model": model_key}
          try:
              response = self.http_post(
                  url=f"{self.config.api_base_url.rstrip('/')}/models/load",
                  json=payload,
                  headers=self._headers(),
                  timeout=self.config.request_timeout_seconds,
              )
              if response.status_code == 400:
                  # Retry with model_key
                  payload = {"model_key": model_key}
                  response = self.http_post(
                      url=f"{self.config.api_base_url.rstrip('/')}/models/load",
                      json=payload,
                      headers=self._headers(),
                      timeout=self.config.request_timeout_seconds,
                  )
              response.raise_for_status()
          except requests.HTTPError as exc:
              if exc.response.status_code == 401:
                  raise LMStudioManagerError(
                      "LM Studio API rejected request; set ALETHEIA_LM_STUDIO_API_TOKEN or disable LM Studio API auth."
                  ) from exc
              raise LMStudioManagerError(f"failed to load embedding model {model_key}: {exc}") from exc
          except Exception as exc:
              raise LMStudioManagerError(f"failed to load embedding model {model_key}: {exc}") from exc

--- FILE: python-daemon/orchestrator/reroll.py ---
Size: 496 bytes
Summary: Classes: ValidationFailure; Functions: schema_failure_text
Content: |
  from __future__ import annotations
  
  import json
  from dataclasses import dataclass
  from typing import Any
  
  
  @dataclass(frozen=True)
  class ValidationFailure(Exception):
      tool_name: str
      details: list[dict[str, Any]]
  
      def schema_failure_text(self) -> str:
          return json.dumps(
              {
                  "tool_name": self.tool_name,
                  "error": "schema_validation_failed",
                  "details": self.details,
              },
              sort_keys=True,
          )

--- FILE: python-daemon/tests/test_approval.py ---
Size: 1242 bytes
Summary: Classes: ApprovalTests; Functions: test_builds_and_verifies_hmac_approval_envelope, test_md5_novelty_is_canonical_and_not_security_hash
Content: |
  import hashlib
  import hmac
  import unittest
  
  from orchestrator.approval import (
      build_approval_envelope,
      md5_novelty_hex,
      sha256_hex,
      verify_approval,
  )
  
  
  class ApprovalTests(unittest.TestCase):
      def test_builds_and_verifies_hmac_approval_envelope(self):
          secret = b"approval-secret"
          diff = b"change"
  
          envelope = build_approval_envelope(secret, b"base", b"proposed", diff)
  
          self.assertEqual(envelope.base_snapshot_sha256, hashlib.sha256(b"base").hexdigest())
          self.assertEqual(envelope.proposed_snapshot_sha256, hashlib.sha256(b"proposed").hexdigest())
          self.assertEqual(envelope.diff_sha256, sha256_hex(diff))
          self.assertEqual(envelope.diff_hmac_sha256, hmac.digest(secret, diff, "sha256").hex())= [REDACTED_HIGH_ENTROPY]
          self.assertTrue(verify_approval(secret, diff, envelope.diff_hmac_sha256))
          self.assertFalse(verify_approval(secret, b"tampered", envelope.diff_hmac_sha256))
  
      def test_md5_novelty_is_canonical_and_not_security_hash(self):
          first = md5_novelty_hex({"b": 2, "a": 1})
          second = md5_novelty_hex({"a": 1, "b": 2})
  
          self.assertEqual(first, second)
          self.assertEqual(len(first), 32)
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/orchestrator/admin.py ---
Size: 1819 bytes
Summary: Functions: main
Content: |
  from __future__ import annotations
  
  import argparse
  import json
  
  from .config import RuntimeConfig
  from .runtime import build_runtime
  
  
  def main() -> None:
      parser = argparse.ArgumentParser(prog="aletheia-admin")
      subcommands = parser.add_subparsers(dest="command", required=True)
      subcommands.add_parser("health")
      subcommands.add_parser("show-config")
      reconcile = subcommands.add_parser("reconcile-project")
      reconcile.add_argument("project_id")
      dead = subcommands.add_parser("list-dead-letters")
      dead.add_argument("--limit", type=int, default=50)
      args = parser.parse_args()
  
      config = RuntimeConfig.from_env()
      if args.command == "show-config":
          print(
              json.dumps(
                  {
                      "project_root": str(config.project_root),
                      "state_dir": str(config.state_dir),
                      "allowed_roots": [str(root) for root in config.allowed_roots],
                      "chroma_path": str(config.chroma_path),
                      "bridge_host": config.bridge_host,
                      "bridge_port": config.bridge_port,
                      "ocr_enabled": config.ocr_command is not None,
                  },
                  sort_keys=True,
              )
          )
          return
  
      runtime = build_runtime(config)
      try:
          if args.command == "health":
              payload = runtime.health()
          elif args.command == "reconcile-project":
              payload = runtime.reconcile_project(args.project_id)
          elif args.command == "list-dead-letters":
              payload = runtime.dead_letters(args.limit)
          else:
              raise SystemExit(f"unknown command: {args.command}")
          print(json.dumps(payload, sort_keys=True))
      finally:
          runtime.close()
  
  
  if __name__ == "__main__":
      main()

--- FILE: python-daemon/orchestrator/config.py ---
Size: 3233 bytes
Summary: Classes: RuntimeConfig; Functions: from_env
Content: |
  from __future__ import annotations
  
  import os
  from dataclasses import dataclass
  from pathlib import Path
  from typing import Mapping
  
  
  @dataclass(frozen=True)
  class RuntimeConfig:
      project_root: Path
      project_id: str
      state_dir: Path
      allowed_roots: tuple[Path, ...]
      chroma_path: Path
      lm_studio_base_url: str
      lm_studio_api_base_url: str
      lm_studio_api_token: str | None
      embedding_model: str
      auto_load_embedding_model: bool
      bridge_host: str
      bridge_port: int
      bridge_shared_secret: str | None
      enable_admin_bridge: bool
      approval_secret: bytes
      ocr_command: str | None
      log_level: str
      worker_id: str
      lease_seconds: int
      idle_sleep_seconds: float
  
      @classmethod
      def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeConfig":
          env = env or os.environ
          project_root = Path(env.get("ALETHEIA_PROJECT_ROOT", Path.cwd())).resolve()
          project_id = env.get("ALETHEIA_PROJECT_ID", project_root.name)
          state_dir = Path(env.get("ALETHEIA_STATE_DIR", project_root / ".aletheia_state")).resolve()
          allowed_roots_raw = env.get("ALETHEIA_ALLOWED_ROOTS", str(project_root))
          allowed_roots = tuple(Path(part).resolve() for part in allowed_roots_raw.split(";") if part.strip())
          enable_admin_bridge = env.get("ALETHEIA_ENABLE_ADMIN_BRIDGE", "false").lower() == "true"
          lm_studio_base_url = env.get("ALETHEIA_LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
          lm_studio_api_base_url = env.get(
              "ALETHEIA_LM_STUDIO_API_BASE_URL",
              lm_studio_base_url.rstrip("/").replace("/v1", "/api/v1") if "/v1" in lm_studio_base_url else "http= [REDACTED_HIGH_ENTROPY]
          )
          lm_studio_api_token = [REDACTED_HIGH_ENTROPY]
          auto_load_embedding_model = env.get("ALETHEIA_AUTO_LOAD_EMBEDDING_MODEL", "true").lower() == "true"
          return cls(
              project_root=project_root,
              project_id=project_id,
              state_dir=state_dir,
              allowed_roots=allowed_roots or (project_root,),
              chroma_path=Path(env.get("ALETHEIA_CHROMA_PATH", state_dir / "chroma")).resolve(),
              lm_studio_base_url=lm_studio_base_url,
              lm_studio_api_base_url=lm_studio_api_base_url,
              lm_studio_api_token=lm_studio_api_token,
              embedding_model=env.get("ALETHEIA_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5"),
              auto_load_embedding_model=auto_load_embedding_model,
              bridge_host=env.get("ALETHEIA_BRIDGE_HOST", "127.0.0.1"),
              bridge_port=int(env.get("ALETHEIA_BRIDGE_PORT", "8765")),
              bridge_shared_secret= [REDACTED_HIGH_ENTROPY]
              enable_admin_bridge=enable_admin_bridge,
              approval_secret= [REDACTED_HIGH_ENTROPY]
              ocr_command=env.get("ALETHEIA_OCR_COMMAND"),
              log_level=env.get("ALETHEIA_LOG_LEVEL", "INFO"),
              worker_id=env.get("ALETHEIA_WORKER_ID", "aletheia-worker-1"),
              lease_seconds=int(env.get("ALETHEIA_LEASE_SECONDS", "60")),
              idle_sleep_seconds=float(env.get("ALETHEIA_IDLE_SLEEP_SECONDS", "0.25")),
          )

--- FILE: python-daemon/orchestrator/db_bootstrap.py ---
Size: 6547 bytes
Summary: Functions: bootstrap_databases, _apply_migrations
Content: |
  from __future__ import annotations
  
  from pathlib import Path
  from contextlib import closing
  from datetime import datetime, timezone
  import sqlite3
  
  
  QUEUE_MIGRATION_0001 = """
  PRAGMA journal_mode = WAL;
  PRAGMA synchronous = NORMAL;
  PRAGMA busy_timeout = 5000;
  PRAGMA foreign_keys = ON;
  
  CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('PLANNING', 'PENDING_APPROVAL', 'COMPLETED')),
    resolution TEXT NOT NULL CHECK (resolution IN ('ACTIVE', 'REJECTED', 'CASCADE_PRUNED')),
    parent_task_id TEXT,
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    slr_score REAL NOT NULL DEFAULT 0.0,
    depth_penalty REAL NOT NULL DEFAULT 0.0,
    final_score REAL NOT NULL DEFAULT 0.0,
    depth INTEGER NOT NULL DEFAULT 0,
    reroll_count INTEGER NOT NULL DEFAULT 0,
    negative_constraints_json TEXT NOT NULL DEFAULT '[]',
    novelty_md5 TEXT NOT NULL,
    lease_owner TEXT,
    lease_expires_at TEXT,
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    pruned_by_task_id TEXT,
    pruned_reason TEXT,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id)
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS task_edges (
    parent_task_id TEXT NOT NULL,
    child_task_id TEXT NOT NULL,
    PRIMARY KEY (parent_task_id, child_task_id),
    FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (child_task_id) REFERENCES tasks(task_id)
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS task_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    diff_sha256 TEXT NOT NULL,
    diff_hmac_sha256 TEXT NOT NULL,
    base_snapshot_sha256 TEXT NOT NULL,
    proposed_snapshot_sha256 TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('PENDING', 'APPROVED', 'REJECTED')),
    decided_by TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_tasks_ready
    ON tasks(project_id, created_at)
    WHERE state = 'PLANNING' AND resolution = 'ACTIVE' AND lease_owner IS NULL;
  
  CREATE INDEX IF NOT EXISTS idx_tasks_waiting_approval
    ON tasks(project_id, updated_at)
    WHERE state = 'PENDING_APPROVAL' AND resolution = 'ACTIVE';
  
  CREATE TABLE IF NOT EXISTS files (
    project_id TEXT NOT NULL,
    project_scope_hash TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    file_name TEXT NOT NULL,
    metadata_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_scope_hash, absolute_path)
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    project_scope_hash TEXT NOT NULL,
    target_path TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('RUNNING', 'COMPLETED', 'FAILED', 'FAILED_VECTOR_UPSERT', 'RECONCILED')),
    error TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    project_scope_hash TEXT NOT NULL,
    run_id TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    processor TEXT NOT NULL,
    content_sha1 TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id),
    FOREIGN KEY (project_scope_hash, absolute_path) REFERENCES files(project_scope_hash, absolute_path)= [REDACTED_HIGH_ENTROPY]
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_chunks_project_scope
    ON chunks(project_id, project_scope_hash, chunk_index);
  """
  
  
  CONTROL_MIGRATION_0001 = """
  PRAGMA journal_mode = WAL;
  PRAGMA synchronous = NORMAL;
  PRAGMA busy_timeout = 5000;
  PRAGMA foreign_keys = ON;
  
  CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS leases (
    lease_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE TABLE IF NOT EXISTS process_registry (
    pid INTEGER PRIMARY KEY,
    worker_id TEXT NOT NULL,
    command_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    heartbeat_at TEXT,
    status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'STALE', 'EXITED', 'ORPHANED')),
    exited_at TEXT,
    exit_code INTEGER,
    orphaned INTEGER NOT NULL DEFAULT 0
  ) STRICT;
  
  CREATE TABLE IF NOT EXISTS dead_letters (
    dead_letter_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  """
  
  
  QUEUE_MIGRATIONS = (("0001_initial", QUEUE_MIGRATION_0001),)
  CONTROL_MIGRATIONS = (("0001_initial", CONTROL_MIGRATION_0001),)
  
  
  def bootstrap_databases(root: Path) -> None:
      root.mkdir(parents=True, exist_ok=True)
      for db_name, migrations in (("queue.db", QUEUE_MIGRATIONS), ("control.db", CONTROL_MIGRATIONS)):
          with closing(sqlite3.connect(root / db_name)) as conn:
              _apply_migrations(conn, migrations)
              conn.commit()
  
  
  def _apply_migrations(conn: sqlite3.Connection, migrations: tuple[tuple[str, str], ...]) -> None:
      known = {version for version, _ in migrations}
      conn.execute(
          """
          CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
          ) STRICT, WITHOUT ROWID
          """
      )
      applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
      unknown = sorted(applied - known)
      if unknown:
          raise RuntimeError(f"database has unsupported future migrations: {', '.join(unknown)}")
      now = datetime.now(timezone.utc).isoformat()
      for version, script in migrations:
          if version in applied:
              continue
          conn.executescript(script)
          conn.execute(
              "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
              (version, now),
          )

--- FILE: python-daemon/orchestrator/observability.py ---
Size: 997 bytes
Summary: Classes: JsonFormatter; Functions: configure_logging, format
Content: |
  from __future__ import annotations
  
  import json
  import logging
  from datetime import datetime, timezone
  from typing import Any
  
  
  class JsonFormatter(logging.Formatter):
      def format(self, record: logging.LogRecord) -> str:
          payload: dict[str, Any] = {
              "ts": datetime.now(timezone.utc).isoformat(),
              "level": record.levelname,
              "logger": record.name,
              "message": record.getMessage(),
          }
          extra = getattr(record, "extra_fields", None)
          if isinstance(extra, dict):
              payload.update(extra)
          if record.exc_info:
              payload["exc_info"] = self.formatException(record.exc_info)
          return json.dumps(payload, sort_keys=True)
  
  
  def configure_logging(level: str) -> None:
      handler = logging.StreamHandler()
      handler.setFormatter(JsonFormatter())
      root = logging.getLogger()
      root.handlers.clear()
      root.addHandler(handler)
      root.setLevel(getattr(logging, level.upper(), logging.INFO))

--- FILE: python-daemon/orchestrator/ocr.py ---
Size: 1255 bytes
Summary: Classes: CommandOCRProvider; Functions: extract_image_text
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass
  from typing import Callable
  
  from .adapters import AdapterFailure
  from .shell import CommandSpec, ShellAdapter
  
  
  Runner = Callable[[str, list[str], float], str]
  
  
  @dataclass(frozen=True)
  class CommandOCRProvider:
      shell_adapter: ShellAdapter
      command: str
      timeout_seconds: float = 30.0
      runner: Runner | None = None
  
      def extract_image_text(self, absolute_path: str, page: int | None, region: dict[str, int] | None) -> str:
          args = [absolute_path]
          if page is not None:
              args.extend(["--page", str(page)])
          if region is not None:
              args.extend(["--region", ",".join(f"{key}= [REDACTED_HIGH_ENTROPY]
          try:
              if self.runner is not None:
                  return self.runner(self.command, args, self.timeout_seconds)
              spec = CommandSpec(
                  executable=self.command,
                  args=tuple(args),
                  timeout_seconds=self.timeout_seconds,
              )
              _, stdout, _ = self.shell_adapter.sync_run(spec)
              return stdout
          except Exception as exc:
              raise AdapterFailure(f"OCR extraction failed: {exc}") from exc

--- FILE: python-daemon/orchestrator/recovery.py ---
Size: 1328 bytes
Summary: Classes: RecoveryService; Functions: __init__, recover_once
Content: |
  from __future__ import annotations
  
  import os
  from datetime import datetime, timedelta, timezone
  
  from .queue_repo import QueueRepository
  from .shell import ZombieReaper
  
  
  class RecoveryService:
      def __init__(self, repo: QueueRepository, *, reaper: ZombieReaper | None = None) -> None:
          self.repo = repo
          self.reaper = reaper or ZombieReaper()
  
      def recover_once(self, *, lease_now: str | None = None, stale_after_seconds: int = 120) -> dict[str, int]:
          now = datetime.now(timezone.utc)
          released = self.repo.release_expired_leases(lease_now or now.isoformat())
          stale_before = (now - timedelta(seconds=stale_after_seconds)).isoformat()
          stale_workers = self.repo.mark_stale_workers(stale_before)
          reaped = 0
          for worker in self.repo.list_worker_status():
              if worker.get("status") not in {"RUNNING", "STALE"}:
                  continue
              result = self.reaper.reap_once(int(worker["pid"]))
              if result is not None:
                  waited_pid, status = result
                  self.repo.mark_worker_exited(waited_pid, os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else status)
                  reaped += 1
          return {"released_leases": released, "stale_workers": stale_workers, "reaped_processes": reaped}

--- FILE: lmstudio_fastmcp_shim.py ---
Size: 5360 bytes
Summary: Classes: BridgeCallError; Functions: call_bridge, call_tool, as_pretty_json, mcp_scout_workspace, mcp_ingest_target, mcp_semantic_search, mcp_verify_integrity, mcp_extract_image
Content: |
  from __future__ import annotations
  
  import json
  import os
  import socket
  from typing import Any
  
  from mcp.server.fastmcp import FastMCP
  
  mcp = FastMCP("Aletheia_Orchestrator_Shim")
  
  BRIDGE_HOST = os.environ.get("ALETHEIA_BRIDGE_HOST", "127.0.0.1")
  BRIDGE_PORT = int(os.environ.get("ALETHEIA_BRIDGE_PORT", "8765"))
  BRIDGE_TIMEOUT_SECONDS = float(os.environ.get("ALETHEIA_BRIDGE_TIMEOUT_SECONDS", "30"))
  
  
  class BridgeCallError(RuntimeError):
      """Raised when the local Aletheia daemon bridge rejects or fails a request."""
  
  
  def call_bridge(method: str, params: dict[str, Any]) -> dict[str, Any]:
      """
      Call the local Aletheia Python daemon JSON-RPC bridge.
  
      This shim intentionally uses the unauthenticated local bridge path.
      Run the daemon without ALETHEIA_BRIDGE_SECRET while using this version.= [REDACTED_HIGH_ENTROPY]
  
      Expected topology:
        LM Studio -> this FastMCP stdio shim -> 127.0.0.1:8765 -> Aletheia daemon
      """
      request = {
          "jsonrpc": "2.0",
          "id": 1,
          "method": method,
          "params": params,
      }
  
      try:
          with socket.create_connection(
              (BRIDGE_HOST, BRIDGE_PORT),
              timeout=BRIDGE_TIMEOUT_SECONDS,
          ) as sock:
              payload = json.dumps(request, separators=(",", ":")) + "\n"
              sock.sendall(payload.encode("utf-8"))
  
              chunks: list[bytes] = []
              while True:
                  data = sock.recv(65536)
                  if not data:
                      break
                  chunks.append(data)
                  if b"\n" in data:
                      break
      except OSError as exc:
          raise BridgeCallError(
              f"Could not connect to Aletheia bridge at {BRIDGE_HOST}:{BRIDGE_PORT}: {exc}"
          ) from exc
  
      raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
      if not raw:
          raise BridgeCallError("Aletheia bridge returned an empty response")
  
      try:
          response = json.loads(raw)
      except json.JSONDecodeError as exc:
          raise BridgeCallError(f"Aletheia bridge returned invalid JSON: {raw[:500]}") from exc
  
      if "error" in response:
          raise BridgeCallError(response["error"])
  
      result = response.get("result", {})
      if not isinstance(result, dict):
          return {"result": result}
      return result
  
  
  def call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
      """
      Forward an MCP tool call to the Aletheia daemon.
  
      The Python bridge expects params.toolName, not params.tool.
      It also accepts params.name, but toolName matches the backend test contract.
      """
      return call_bridge(
          "tools.call",
          {
              "toolName": tool_name,
              "args": args,
          },
      )
  
  
  def as_pretty_json(value: Any) -> str:
      return json.dumps(value, indent=2, ensure_ascii=False)
  
  
  @mcp.tool()
  def mcp_scout_workspace(
      project_id: str,
      absolute_path: str,
      max_files: int = 500,
      include_summaries: bool = True,
  ) -> str:
      """
      Inspect a workspace without indexing vectors.
  
      Use this before ingestion to confirm the path, skipped-file policy, and project shape.
      """
      result = call_tool(
          "mcp_scout_workspace",
          {
              "project_id": project_id,
              "absolute_path": absolute_path,
              "max_files": max_files,
              "include_summaries": include_summaries,
          },
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_ingest_target(
      project_id: str,
      absolute_path: str,
      mime_type: str | None = None,
      force_reindex: bool = False,
  ) -> str:
      """
      Index one file or directory into the Aletheia SQLite manifest and Chroma vector store.
      """
      args: dict[str, Any] = {
          "project_id": project_id,
          "absolute_path": absolute_path,
          "force_reindex": force_reindex,
      }
      if mime_type:
          args["mime_type"] = mime_type
  
      result = call_tool("mcp_ingest_target", args)
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_semantic_search(project_id: str, query: str, k: int = 8) -> str:
      """
      Search indexed semantic memory for a project.
      """
      result = call_tool(
          "mcp_semantic_search",
          {
              "project_id": project_id,
              "query": query,
              "k": k,
          },
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_verify_integrity(
      absolute_path: str,
      expected_sha256: str,
      expected_metadata_hash: str,
  ) -> str:
      """
      Verify file content and metadata hashes.
      """
      result = call_tool(
          "mcp_verify_integrity",
          {
              "absolute_path": absolute_path,
              "expected_sha256": expected_sha256,
              "expected_metadata_hash": expected_metadata_hash,
          },
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_extract_image(
      absolute_path: str,
      page: int | None = None,
      region: dict[str, int] | None = None,
  ) -> str:
      """
      Extract text from an image or non-selectable document region through the configured OCR provider.
      """
      args: dict[str, Any] = {"absolute_path": absolute_path}
      if page is not None:
          args["page"] = page
      if region is not None:
          args["region"] = region
  
      result = call_tool("mcp_extract_image", args)
      return as_pretty_json(result)
  
  
  if __name__ == "__main__":
      mcp.run(transport="stdio")

--- FILE: python-daemon/orchestrator/approval.py ---
Size: 1227 bytes
Summary: Classes: DiffApprovalEnvelope; Functions: sha256_hex, md5_novelty_hex, build_approval_envelope, verify_approval
Content: |
  from __future__ import annotations
  
  import hashlib
  import hmac
  import json
  from dataclasses import dataclass
  from typing import Any
  
  
  @dataclass(frozen=True)
  class DiffApprovalEnvelope:
      base_snapshot_sha256: str
      proposed_snapshot_sha256: str
      diff_sha256: str
      diff_hmac_sha256: str
  
  
  def sha256_hex(data: bytes) -> str:
      return hashlib.sha256(data).hexdigest()
  
  
  def md5_novelty_hex(payload: dict[str, Any]) -> str:
      canonical = [REDACTED_HIGH_ENTROPY]
      return hashlib.md5(canonical, usedforsecurity=False).hexdigest()
  
  
  def build_approval_envelope(
      secret: bytes,
      base_bytes: bytes,
      proposed_bytes: bytes,
      diff_bytes: bytes,
  ) -> DiffApprovalEnvelope:
      return DiffApprovalEnvelope(
          base_snapshot_sha256=sha256_hex(base_bytes),
          proposed_snapshot_sha256=sha256_hex(proposed_bytes),
          diff_sha256=sha256_hex(diff_bytes),
          diff_hmac_sha256=hmac.digest(secret, diff_bytes, "sha256").hex(),
      )
  
  
  def verify_approval(secret: bytes, diff_bytes: bytes, supplied_hmac_hex: str) -> bool:
      expected = hmac.digest(secret, diff_bytes, "sha256").hex()
      return hmac.compare_digest(expected, supplied_hmac_hex)

--- FILE: python-daemon/orchestrator/execution_loop.py ---
Size: 2599 bytes
Summary: Classes: ExecutionLoop; Functions: __init__, score_before_routing, handle_validation_failure, execute_tool_for_task
Content: |
  from __future__ import annotations
  
  from typing import Any
  
  from .adapters import AdapterFailure, ToolAdapters
  from .epistemic import EpistemicPolicy, EpistemicSignals
  from .queue_repo import QueueRepository
  from .reroll import ValidationFailure
  
  
  class ExecutionLoop:
      def __init__(
          self,
          repo: QueueRepository,
          *,
          policy: EpistemicPolicy | None = None,
          max_rerolls: int = 2,
          tool_adapters: ToolAdapters | None = None,
      ) -> None:
          self.repo = repo
          self.policy = policy or EpistemicPolicy()
          self.max_rerolls = max_rerolls
          self.tool_adapters = tool_adapters or ToolAdapters()
  
      def score_before_routing(
          self,
          task_id: str,
          signals: EpistemicSignals,
          *,
          base_score: float,
          depth: int,
      ) -> dict[str, Any]:
          score = self.policy.score(signals, base_score=base_score, depth=depth)
          self.repo.update_scores(task_id, score.slr_score, score.depth_penalty, score.final_score)
          return {
              "slr_score": score.slr_score,
              "depth_penalty": score.depth_penalty,
              "final_score": score.final_score,
              "decision": score.decision,
          }
  
      def handle_validation_failure(self, task_id: str, failure: ValidationFailure) -> dict[str, str]:
          failure_text = failure.schema_failure_text()
          constraint = f"Negative constraint: avoid payload rejected by schema: {failure_text}"
          reroll_count = self.repo.add_negative_constraint(task_id, constraint)
          if reroll_count > self.max_rerolls:
              self.repo.dead_letter(
                  task_id,
                  "schema_validation_failed: reroll_limit_exhausted",
                  {"failure": failure_text, "reroll_count": reroll_count},
              )
              return {"action": "dead_letter", "context": constraint}
          return {"action": "reroll", "context": constraint}
  
      def execute_tool_for_task(self, task_id: str, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
          try:
              return self.tool_adapters.call_mcp_tool(tool_name, args)
          except AdapterFailure as exc:
              failure = ValidationFailure(
                  tool_name=tool_name,
                  details=[{"path": "/", "message": str(exc), "kind": "adapter_failure"}],
              )
              reroll = self.handle_validation_failure(task_id, failure)
              return {
                  "ok": False,
                  "error": "adapter_failure",
                  "message": str(exc),
                  "reroll": reroll,
              }

--- FILE: python-daemon/orchestrator/main.py ---
Size: 1158 bytes
Summary: Functions: main
Content: |
  from __future__ import annotations
  
  import asyncio
  
  from .bridge_server import serve_tcp_bridge
  from .config import RuntimeConfig
  from .observability import configure_logging
  from .runtime import build_runtime
  from .worker import DaemonWorker
  
  
  async def amain() -> None:
      config = RuntimeConfig.from_env()
      configure_logging(config.log_level)
      runtime = build_runtime(config)
      bridge = await serve_tcp_bridge(
          config.bridge_host,
          config.bridge_port,
          runtime.tool_adapters,
          runtime.bridge_security,
          runtime,
      )
      stop_event = asyncio.Event()
      worker = DaemonWorker(
          runtime.repo,
          runtime.tool_adapters,
          project_id=config.project_id,
          worker_id=config.worker_id,
          lease_seconds=config.lease_seconds,
          idle_sleep_seconds=config.idle_sleep_seconds,
      )
      try:
          await asyncio.gather(bridge.serve_forever(), worker.run_forever(stop_event))
      finally:
          stop_event.set()
          bridge.close()
          await bridge.wait_closed()
          runtime.close()
  
  
  def main() -> None:
      asyncio.run(amain())
  
  
  if __name__ == "__main__":
      main()

--- FILE: python-daemon/tests/test_chroma_and_ingest.py ---
Size: 22529 bytes
Summary: Classes: FakeResponse, FakeCollection, FakeChromaClient, ChromaAndIngestTests, FakeLMStudioManager, LMStudioManagerTests, BrokenUpsertCollection, BrokenUpsertClient, BrokenOnceCollection, BrokenOnceClient, BrokenCollection, BrokenClient, Fake401Response; Functions: __init__, raise_for_status, json, __init__, upsert, _matches_where, delete, query, __init__, get_or_create_collection, test_embedding_payload_uses_lm_studio_model_and_nomic_prefix, test_search_enforces_project_scope_hash_where_filter, test_ingest_service_records_sqlite_manifest_and_upserts_chroma, test_file_manifest_key_allows_same_file_hash_in_multiple_project_scopes, test_force_reindex_removes_stale_sqlite_chunks_and_chroma_vectors, test_invalid_python_file_falls_back_to_text_chunking, test_unchanged_file_skips_reindex_without_force, test_changed_file_reindexes_without_force_and_removes_stale_chunks, test_directory_ingest_removes_deleted_file_manifests_and_vectors, test_rebuild_chroma_from_sqlite_chunk_store, test_delete_chunks_uses_chroma_compatible_and_filter, test_failed_vector_upsert_preserves_sqlite_chunks_for_reconciliation, test_rebuild_chroma_for_project_uses_rebuildable_chunks, test_chroma_failures_raise_formal_value_error, __init__, ensure_embedding_model_loaded, test_chroma_manager_calls_ensure_embedding_model_loaded_before_embedding, test_chroma_manager_includes_auth_header_when_token_configured, test_chroma_manager_raises_clear_error_on_401_from_embeddings, post, post, post, upsert, __init__, __init__, upsert, __init__, query, __init__, raise_for_status, json
Content: |
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.chroma_manager import ChromaAdapterError, ChromaConfig, ChromaManager
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.ingest.service import IngestTargetService
  from orchestrator.queue_repo import QueueRepository
  
  
  class FakeResponse:
      def __init__(self, payload):
          self.payload = payload
          self.status_code = 200
  
      def raise_for_status(self):
          return None
  
      def json(self):
          return self.payload
  
  
  class FakeCollection:
      def __init__(self):
          self.upserts = []
          self.queries = []
          self.deletes = []
          self.rows = {}
  
      def upsert(self, **kwargs):
          self.upserts.append(kwargs)
          for index, chunk_id in enumerate(kwargs["ids"]):
              self.rows[chunk_id] = {
                  "document": kwargs["documents"][index],
                  "metadata": kwargs["metadatas"][index],
                  "embedding": kwargs["embeddings"][index],
              }
  
      def _matches_where(self, metadata, where):
          """Check if metadata matches a where filter (supports Chroma $and and $eq operators)."""
          if "$and" in where:
              return all(self._matches_where(metadata, clause) for clause in where["$and"])
          for key, expected in where.items():
              if isinstance(expected, dict) and "$eq" in expected:
                  if metadata.get(key) != expected["$eq"]:
                      return False
              else:
                  if metadata.get(key) != expected:
                      return False
          return True
  
      def delete(self, **kwargs):
          self.deletes.append(kwargs)
          where = kwargs["where"]
          stale = [
              chunk_id
              for chunk_id, row in self.rows.items()
              if self._matches_where(row["metadata"], where)
          ]
          for chunk_id in stale:
              del self.rows[chunk_id]
  
      def query(self, **kwargs):
          self.queries.append(kwargs)
          where = kwargs["where"]
          matches = [
              (chunk_id, row)
              for chunk_id, row in self.rows.items()
              if self._matches_where(row["metadata"], where)
          ]
          if matches:
              return {
                  "ids": [[chunk_id for chunk_id, _ in matches]],
                  "documents": [[row["document"] for _, row in matches]],
                  "metadatas": [[row["metadata"] for _, row in matches]],
                  "distances": [[0.1 for _ in matches]],
              }
          scope_hash = where.get("project_scope_hash")
          if scope_hash is None and "$and" in where:
              for clause in where["$and"]:
                  if "project_scope_hash" in clause:
                      scope_hash = clause["project_scope_hash"].get("$eq")
                      break
          return {
              "ids": [["chunk-1"]],
              "documents": [["hello world"]],
              "metadatas": [[{"project_scope_hash": scope_hash}]],
              "distances": [[0.1]],
          }
  
  
  class FakeChromaClient:
      def __init__(self):
          self.collection = FakeCollection()
  
      def get_or_create_collection(self, name):
          self.name = name
          return self.collection
  
  
  class ChromaAndIngestTests(unittest.TestCase):
      def test_embedding_payload_uses_lm_studio_model_and_nomic_prefix(self):
          calls = []
  
          def post(url, json, headers=None, timeout=None):
              calls.append((url, json, headers, timeout))
              return FakeResponse({"data": [{"embedding": [1, 2, 3]}]})
  
          manager = ChromaManager(
              ChromaConfig(
                  chroma_path=Path("unused"),
                  lm_studio_base_url="http://lm/v1",
                  auto_load_embedding_model=False,
              ),
              http_post=post,
              chroma_client=FakeChromaClient(),
          )
  
          self.assertEqual(manager.embed_text("abc"), [1.0, 2.0, 3.0])
          self.assertEqual(calls[0][0], "http://lm/v1/embeddings")
          self.assertEqual(calls[0][1]["input"], "search_document: abc")
  
      def test_search_enforces_project_scope_hash_where_filter(self):
          fake_client = FakeChromaClient()
          manager = ChromaManager(
              ChromaConfig(chroma_path=Path("unused"), auto_load_embedding_model=False),
              http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1]}]}),
              chroma_client=fake_client,
          )
  
          results = manager.search("project-a", "hello", k=3)
  
          query = fake_client.collection.queries[0]
          self.assertEqual(query["where"], {"project_scope_hash": manager.project_scope_hash("project-a")})
          self.assertEqual(query["n_results"], 3)
          self.assertEqual(results[0]["content"], "hello world")
  
      def test_ingest_service_records_sqlite_manifest_and_upserts_chroma(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.py"
              source.write_text("def alpha():\n    return 1\n", encoding="utf-8")
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2, 0.3]}]}),
                  chroma_client=fake_client,
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              result = service.ingest_target("project-a", str(source))
  
              self.assertEqual(result["chunks_indexed"], 1)
              upsert = fake_client.collection.upserts[0]
              self.assertEqual(upsert["metadatas"][0]["project_id"], "project-a")
              self.assertEqual(upsert["metadatas"][0]["processor"], "semantic_slicer")
              chunks = repo.list_chunks("project-a")
              self.assertEqual(len(chunks), 1)
              self.assertEqual(chunks[0]["processor"], "semantic_slicer")
  
      def test_file_manifest_key_allows_same_file_hash_in_multiple_project_scopes(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("shared content", encoding="utf-8")
              repo = QueueRepository(root / "queue.db", root / "control.db")
  
              for project_id in ("project-a", "project-b"):
                  manager = ChromaManager(
                      ChromaConfig(chroma_path=root / f"chroma-{project_id}", auto_load_embedding_model=False),
                      http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                      chroma_client=FakeChromaClient(),
                  )
                  IngestTargetService(repo, manager, allowed_roots=(root,)).ingest_target(project_id, str(source))
  
              self.assertEqual(repo.count_file_manifests(), 2)
  
      def test_force_reindex_removes_stale_sqlite_chunks_and_chroma_vectors(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("old content that is long enough", encoding="utf-8")
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                  chroma_client=fake_client,
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              service.ingest_target("project-a", str(source))
              source.write_text("new content that replaces the old content", encoding="utf-8")
              service.ingest_target("project-a", str(source), force_reindex=True)
  
              chunks = repo.list_chunks("project-a")
              self.assertEqual(len(chunks), 1)
              self.assertIn("new content", chunks[0]["content"])
              results = manager.search("project-a", "content", k=10)
              self.assertEqual(len(results), 1)
              self.assertIn("new content", results[0]["content"])
              self.assertTrue(fake_client.collection.deletes)
  
      def test_invalid_python_file_falls_back_to_text_chunking(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "broken.py"
              source.write_text("def broken(:\n    pass\n", encoding="utf-8")
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                  chroma_client=fake_client,
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              result = service.ingest_target("project-a", str(source))
  
              self.assertEqual(result["chunks_indexed"], 1)
              chunks = repo.list_chunks("project-a")
              self.assertEqual(len(chunks), 1)
              self.assertEqual(chunks[0]["processor"], "text")
  
      def test_unchanged_file_skips_reindex_without_force(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("same content", encoding="utf-8")
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                  chroma_client=fake_client,
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              first = service.ingest_target("project-a", str(source))
              second = service.ingest_target("project-a", str(source))
  
              self.assertEqual(first["chunks_indexed"], 1)
              self.assertEqual(second["chunks_indexed"], 0)
              self.assertEqual(second["files_skipped"], 1)
              self.assertEqual(len(fake_client.collection.upserts), 1)
  
      def test_changed_file_reindexes_without_force_and_removes_stale_chunks(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("old content", encoding="utf-8")
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                  chroma_client=fake_client,
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              service.ingest_target("project-a", str(source))
              source.write_text("brand new content", encoding="utf-8")
              second = service.ingest_target("project-a", str(source))
  
              chunks = repo.list_chunks("project-a")
              self.assertEqual(second["chunks_indexed"], 1)
              self.assertEqual(len(chunks), 1)
              self.assertIn("brand new content", chunks[0]["content"])
              self.assertTrue(fake_client.collection.deletes)
  
      def test_directory_ingest_removes_deleted_file_manifests_and_vectors(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              first = root / "a.txt"
              second = root / "b.txt"
              first.write_text("alpha", encoding="utf-8")
              second.write_text("beta", encoding="utf-8")
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                  chroma_client=fake_client,
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              service.ingest_target("project-a", str(root))
              second.unlink()
              result = service.ingest_target("project-a", str(root))
  
              paths = {chunk["absolute_path"] for chunk in repo.list_chunks("project-a")}
              self.assertEqual(result["files_removed"], 1)
              self.assertEqual(paths, {str(first.resolve())})
  
      def test_rebuild_chroma_from_sqlite_chunk_store(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("rebuild me", encoding="utf-8")
              repo = QueueRepository(root / "queue.db", root / "control.db")
              first = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.4]}]}),
                  chroma_client=FakeChromaClient(),
              )
              service = IngestTargetService(repo, first, allowed_roots=(root,))
              service.ingest_target("project-a", str(source))
              rebuilt = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma2", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.5]}]}),
                  chroma_client=FakeChromaClient(),
              )
  
              result = rebuilt.rebuild_from_chunks("project-a", repo.chunks_for_rebuild("project-a"))
  
              self.assertEqual(result["chunks_indexed"], 1)
              self.assertEqual(rebuilt.search("project-a", "rebuild", k=5)[0]["content"], "rebuild me")
  
      def test_delete_chunks_uses_chroma_compatible_and_filter(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              fake_client = FakeChromaClient()
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.2]}]}),
                  chroma_client=fake_client,
              )
              scope_hash = manager.project_scope_hash("project-a")
              test_path = str((root / "test.py").resolve())
  
              manager.delete_chunks(project_id="project-a", absolute_path=test_path)
  
              self.assertEqual(len(fake_client.collection.deletes), 1)
              delete_call = fake_client.collection.deletes[0]
              where = delete_call["where"]
              self.assertEqual(set(where.keys()), {"$and"})
              self.assertEqual(len(where["$and"]), 2)
              clauses = where["$and"]
              self.assertTrue(any(clause.get("project_scope_hash", {}).get("$eq") == scope_hash for clause in clauses))
              self.assertTrue(any(clause.get("absolute_path", {}).get("$eq") == test_path for clause in clauses))
  
      def test_failed_vector_upsert_preserves_sqlite_chunks_for_reconciliation(self):
          class BrokenUpsertCollection(FakeCollection):
              def upsert(self, **kwargs):
                  raise RuntimeError("vector store unavailable")
  
          class BrokenUpsertClient(FakeChromaClient):
              def __init__(self):
                  self.collection = BrokenUpsertCollection()
  
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("keep this chunk", encoding="utf-8")
              repo = QueueRepository(root / "queue.db", root / "control.db")
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.6]}]}),
                  chroma_client=BrokenUpsertClient(),
              )
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              with self.assertRaises(ChromaAdapterError):
                  service.ingest_target("project-a", str(source))
  
              run = repo.latest_ingestion_run("project-a")
              self.assertEqual(run["state"], "FAILED_VECTOR_UPSERT")
              rebuildable = repo.list_rebuildable_chunks("project-a")
              self.assertEqual(len(rebuildable), 1)
              self.assertEqual(rebuildable[0]["content"], "keep this chunk")
  
      def test_rebuild_chroma_for_project_uses_rebuildable_chunks(self):
          class BrokenOnceCollection(FakeCollection):
              def __init__(self):
                  super().__init__()
                  self.fail = True
  
              def upsert(self, **kwargs):
                  if self.fail:
                      self.fail = False
                      raise RuntimeError("first upsert fails")
                  super().upsert(**kwargs)
  
          class BrokenOnceClient(FakeChromaClient):
              def __init__(self):
                  self.collection = BrokenOnceCollection()
  
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "sample.txt"
              source.write_text("restore me", encoding="utf-8")
              repo = QueueRepository(root / "queue.db", root / "control.db")
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.7]}]}),
                  chroma_client=BrokenOnceClient(),
              )
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
              with self.assertRaises(ChromaAdapterError):
                  service.ingest_target("project-a", str(source))
  
              result = service.rebuild_chroma_for_project("project-a")
  
              self.assertEqual(result["chunks_indexed"], 1)
              self.assertEqual(repo.latest_ingestion_run("project-a")["state"], "RECONCILED")
              self.assertEqual(manager.search("project-a", "restore", k=5)[0]["content"], "restore me")
  
      def test_chroma_failures_raise_formal_value_error(self):
          class BrokenCollection(FakeCollection):
              def query(self, **kwargs):
                  raise RuntimeError("chroma down")
  
          class BrokenClient(FakeChromaClient):
              def __init__(self):
                  self.collection = BrokenCollection()
  
          manager = ChromaManager(
              ChromaConfig(chroma_path=Path("unused"), auto_load_embedding_model=False),
              http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1]}]}),
              chroma_client=BrokenClient(),
          )
  
          with self.assertRaises(ChromaAdapterError):
              manager.search("project-a", "hello")
  
  
  class FakeLMStudioManager:
      def __init__(self):
          self.ensure_calls = []
  
      def ensure_embedding_model_loaded(self, model_key: str) -> None:
          self.ensure_calls.append(model_key)
  
  
  class LMStudioManagerTests(unittest.TestCase):
      def test_chroma_manager_calls_ensure_embedding_model_loaded_before_embedding(self):
          fake_manager = FakeLMStudioManager()
          manager = ChromaManager(
              ChromaConfig(chroma_path=Path("unused"), auto_load_embedding_model=True),
              http_post=lambda **_: FakeResponse({"data": [{"embedding": [1, 2, 3]}]}),
              chroma_client=FakeChromaClient(),
              lm_studio_manager=fake_manager,
          )
  
          result = manager.embed_text("test")
  
          self.assertEqual(result, [1.0, 2.0, 3.0])
          self.assertEqual(fake_manager.ensure_calls, ["text-embedding-nomic-embed-text-v1.5"])
  
      def test_chroma_manager_includes_auth_header_when_token_configured(self):
          calls = []
          def post(url, json, headers=None, timeout=None):
              calls.append((url, json, headers))
              return FakeResponse({"data": [{"embedding": [1, 2, 3]}]})
  
          manager = ChromaManager(
              ChromaConfig(
                  chroma_path=Path("unused"),
                  lm_studio_api_token="test-token",
                  auto_load_embedding_model=False,
              ),
              http_post=post,
              chroma_client=FakeChromaClient(),
          )
  
          result = manager.embed_text("test")
  
          self.assertEqual(result, [1.0, 2.0, 3.0])
          self.assertEqual(calls[0][2]["Authorization"], "Bearer test-token")
  
      def test_chroma_manager_raises_clear_error_on_401_from_embeddings(self):
          def post(url, json, headers=None, timeout=None):
              class Fake401Response:
                  status_code = 401
                  def raise_for_status(self):
                      raise Exception("401 Unauthorized")
                  def json(self):
                      return {}
              return Fake401Response()
  
          manager = ChromaManager(
              ChromaConfig(chroma_path=Path("unused"), auto_load_embedding_model=False),
              http_post=post,
              chroma_client=FakeChromaClient(),
          )
  
          with self.assertRaises(ChromaAdapterError) as cm:
              manager.embed_text("test")
  
          self.assertIn("LM Studio embeddings endpoint rejected request", str(cm.exception))
          self.assertIn("set ALETHEIA_LM_STUDIO_API_TOKEN", str(cm.exception))= [REDACTED_HIGH_ENTROPY]
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/tests/test_db_and_dag.py ---
Size: 2815 bytes
Summary: Classes: DbAndDagTests; Functions: setUp, tearDown, test_bootstrap_uses_wal_and_strict_tables, test_claim_ready_task_blocks_on_unfinished_parent, test_rejection_cascade_prunes_descendants_and_revokes_leases
Content: |
  import sqlite3
  import tempfile
  import unittest
  from contextlib import closing
  from pathlib import Path
  
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.queue_repo import QueueRepository
  
  
  class DbAndDagTests(unittest.TestCase):
      def setUp(self):
          self.tmp = tempfile.TemporaryDirectory()
          self.root = Path(self.tmp.name)
          bootstrap_databases(self.root)
          self.repo = QueueRepository(self.root / "queue.db", self.root / "control.db")
  
      def tearDown(self):
          self.tmp.cleanup()
  
      def test_bootstrap_uses_wal_and_strict_tables(self):
          with closing(sqlite3.connect(self.root / "queue.db")) as conn:
              mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
              self.assertEqual(mode.lower(), "wal")
              with self.assertRaises(sqlite3.IntegrityError):
                  conn.execute(
                      """
                      INSERT INTO tasks (
                        task_id, project_id, state, resolution, title, payload_json,
                        slr_score, depth_penalty, final_score, novelty_md5, created_at, updated_at
                      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                      """,
                      ("bad", "p", "NOT_A_STATE", "ACTIVE", "bad", "{}", 0.0, 0.0, 0.0, "x", "now", "now"),
                  )
  
      def test_claim_ready_task_blocks_on_unfinished_parent(self):
          self.repo.create_task("parent", "p", "Parent", {"tool": "a"}, depth=0)
          self.repo.create_task("child", "p", "Child", {"tool": "b"}, depth=1, parent_task_id="parent")
  
          claimed = self.repo.claim_ready_task("p", "worker", "2099-01-01T00:00:00Z")
  
          self.assertEqual(claimed["task_id"], "parent")
          self.assertIsNone(self.repo.claim_ready_task("p", "worker2", "2099-01-01T00:00:00Z"))
  
      def test_rejection_cascade_prunes_descendants_and_revokes_leases(self):
          self.repo.create_task("root", "p", "Root", {"tool": "a"}, depth=0)
          self.repo.create_task("child", "p", "Child", {"tool": "b"}, depth=1, parent_task_id="root")
          self.repo.create_task("grandchild", "p", "Grandchild", {"tool": "c"}, depth=2, parent_task_id="child")
          self.repo.claim_ready_task("p", "worker", "2099-01-01T00:00:00Z")
  
          pruned = self.repo.reject_and_prune("root", "human_rejected")
  
          self.assertEqual(pruned, ["child", "grandchild"])
          root = self.repo.get_task("root")
          child = self.repo.get_task("child")
          grandchild = self.repo.get_task("grandchild")
          self.assertEqual(root["resolution"], "REJECTED")
          self.assertEqual(child["resolution"], "CASCADE_PRUNED")
          self.assertEqual(grandchild["resolution"], "CASCADE_PRUNED")
          self.assertIsNone(root["lease_owner"])
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/tests/test_execution_loop_adapters.py ---
Size: 1312 bytes
Summary: Classes: FailingAdapters, ExecutionLoopAdapterTests; Functions: call_mcp_tool, test_adapter_failure_feeds_reroll_engine
Content: |
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.adapters import AdapterFailure, ToolAdapters
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.execution_loop import ExecutionLoop
  from orchestrator.queue_repo import QueueRepository
  
  
  class FailingAdapters(ToolAdapters):
      def call_mcp_tool(self, tool_name, args):
          raise AdapterFailure("adapter failed")
  
  
  class ExecutionLoopAdapterTests(unittest.TestCase):
      def test_adapter_failure_feeds_reroll_engine(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = QueueRepository(root / "queue.db", root / "control.db")
              repo.create_task("task", "p", "Task", {"tool": "mcp_semantic_search"}, depth=0)
              loop = ExecutionLoop(repo, max_rerolls=1, tool_adapters=FailingAdapters())
  
              result = loop.execute_tool_for_task("task", "mcp_semantic_search", {"project_id": "p", "query": "q"})
  
              self.assertFalse(result["ok"])
              self.assertEqual(result["error"], "adapter_failure")
              self.assertEqual(result["reroll"]["action"], "reroll")
              self.assertIn("adapter failed", result["reroll"]["context"])
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/orchestrator/adapters.py ---
Size: 9696 bytes
Summary: Classes: AdapterFailure, SemanticMemoryAdapter, OCRProvider, WorkspaceScoutAdapter, FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters; Functions: search, ingest_target, extract_image_text, scout, __init__, _resolve, read_file, read_file_snippet, list_directory, package_directory, verify_integrity, __init__, _resolve, query, __init__, call_mcp_tool
Content: |
  from __future__ import annotations
  
  import hashlib
  import json
  import os
  import sqlite3
  from pathlib import Path
  from typing import Any, Protocol
  
  import yaml
  
  
  class AdapterFailure(ValueError):
      pass
  
  
  class SemanticMemoryAdapter(Protocol):
      def search(self, project_id: str, query: str, k: int) -> list[dict[str, object]]:
          ...
  
      def ingest_target(
          self,
          project_id: str,
          absolute_path: str,
          *,
          mime_type: str | None = None,
          force_reindex: bool = False,
      ) -> dict[str, object]:
          ...
  
  
  class OCRProvider(Protocol):
      def extract_image_text(self, absolute_path: str, page: int | None, region: dict[str, int] | None) -> str:
          ...
  
  
  class WorkspaceScoutAdapter(Protocol):
      def scout(
          self,
          project_id: str,
          absolute_path: str,
          *,
          max_files: int = 500,
          include_summaries: bool = True,
      ) -> dict[str, Any]:
          ...
  
  
  class FileToolAdapter:
      def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
          self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
  
      def _resolve(self, path: str) -> Path:
          resolved = Path(path).resolve()
          if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
              raise AdapterFailure("path escapes allowed roots")
          return resolved
  
      def read_file(self, file_path: str) -> str:
          try:
              return self._resolve(file_path).read_text(encoding="utf-8", errors="replace")
          except AdapterFailure:
              raise
          except Exception as exc:
              raise AdapterFailure(f"read_file failed: {exc}") from exc
  
      def read_file_snippet(self, file_path: str, start_line: int, end_line: int) -> str:
          if start_line < 1 or end_line < start_line:
              raise AdapterFailure("invalid line range")
          lines = self.read_file(file_path).splitlines(keepends=True)
          return "".join(lines[start_line - 1:end_line])
  
      def list_directory(self, directory_path: str) -> list[str]:
          try:
              return sorted(os.listdir(self._resolve(directory_path)))
          except AdapterFailure:
              raise
          except Exception as exc:
              raise AdapterFailure(f"list_directory failed: {exc}") from exc
  
      def package_directory(self, directory_path: str) -> str:
          root = self._resolve(directory_path)
          tree: dict[str, Any] = {}
          try:
              for current, dirs, files in os.walk(root):
                  dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"})
                  rel_root = os.path.relpath(current, root)
                  subtree = tree
                  if rel_root != ".":
                      for part in rel_root.split(os.sep):
                          subtree = subtree.setdefault(part, {})
                  subtree["files"] = sorted(files)
              return yaml.dump(tree, sort_keys=False)
          except Exception as exc:
              raise AdapterFailure(f"package_directory failed: {exc}") from exc
  
      def verify_integrity(self, absolute_path: str, expected_sha256: str, expected_metadata_hash: str) -> dict[str, Any]:
          path = self._resolve(absolute_path)
          try:
              digest = hashlib.sha256(path.read_bytes()).hexdigest()
              stat = path.stat()
              metadata = {
                  "file_sha256": digest,
                  "file_name": path.name,
                  "absolute_path": str(path),
                  "size_bytes": stat.st_size,
                  "mtime_ns": stat.st_mtime_ns,
              }
              metadata_hash = hashlib.sha256(
                  json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
              ).hexdigest()
          except Exception as exc:
              raise AdapterFailure(f"verify_integrity failed: {exc}") from exc
          return {
              "ok": digest.lower() == expected_sha256.lower() and metadata_hash == expected_metadata_hash,
              "sha256": digest,
              "metadata_hash": metadata_hash,
              "metadata": metadata,
          }
  
  
  class ReadOnlySqliteAdapter:
      def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
          self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
  
      def _resolve(self, db_path: str) -> Path:
          resolved = Path(db_path).resolve()
          if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
              raise AdapterFailure("database path escapes allowed roots")
          return resolved
  
      def query(self, db_path: str, query: str, *, row_limit: int = 100) -> list[dict[str, Any]]:
          normalized = query.strip().lower()
          if ";" in query:
              raise AdapterFailure("semicolons are not allowed")
          if normalized.startswith("--") or normalized.startswith("/*"):
              raise AdapterFailure("leading comments are not allowed")
          if normalized.startswith("with"):
              raise AdapterFailure("WITH statements are not allowed")
          if not normalized.startswith("select"):
              raise AdapterFailure("only SELECT queries are allowed")
          forbidden = ("pragma", "attach", "detach", "insert", "update", "delete", "drop", "alter")
          if any(token in normalized.split() for token in forbidden):
              raise AdapterFailure("query contains a forbidden operation")
          if row_limit < 1 or row_limit > 1000:
              raise AdapterFailure("row_limit must be between 1 and 1000")
          uri = self._resolve(db_path).as_uri() + "?mode=ro"
          conn = sqlite3.connect(uri, uri=True)
          try:
              cursor = conn.execute(f"SELECT * FROM ({query}) LIMIT ?", (row_limit,))
              columns = [column[0] for column in cursor.description or []]
              return [dict(zip(columns, row)) for row in cursor.fetchall()]
          except Exception as exc:
              raise AdapterFailure(f"sqlite query failed: {exc}") from exc
          finally:
              conn.close()
  
  
  class ToolAdapters:
      def __init__(
          self,
          *,
          semantic_memory: SemanticMemoryAdapter | None = None,
          file_tools: FileToolAdapter | None = None,
          sqlite_tools: ReadOnlySqliteAdapter | None = None,
          workspace_scout: WorkspaceScoutAdapter | None = None,
          ocr_provider: OCRProvider | None = None,
      ) -> None:
          self.semantic_memory = semantic_memory
          self.file_tools = file_tools
          self.sqlite_tools = sqlite_tools
          self.workspace_scout = workspace_scout
          self.ocr_provider = ocr_provider
  
      def call_mcp_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
          try:
              if tool_name == "mcp_semantic_search":
                  if self.semantic_memory is None:
                      raise AdapterFailure("semantic memory adapter is not configured")
                  return {
                      "ok": True,
                      "results": self.semantic_memory.search(
                          str(args["project_id"]),
                          str(args["query"]),
                          int(args.get("k", 8)),
                      ),
                  }
              if tool_name == "mcp_ingest_target":
                  if self.semantic_memory is None:
                      raise AdapterFailure("semantic memory adapter is not configured")
                  return {
                      "ok": True,
                      "result": self.semantic_memory.ingest_target(
                          str(args["project_id"]),
                          str(args["absolute_path"]),
                          mime_type=args.get("mime_type"),
                          force_reindex=bool(args.get("force_reindex", False)),
                      ),
                  }
              if tool_name == "mcp_scout_workspace":
                  if self.workspace_scout is None:
                      raise AdapterFailure("workspace scout adapter is not configured")
                  return {
                      "ok": True,
                      "result": self.workspace_scout.scout(
                          str(args["project_id"]),
                          str(args["absolute_path"]),
                          max_files=int(args.get("max_files", 500)),
                          include_summaries=bool(args.get("include_summaries", True)),
                      ),
                  }
              if tool_name == "mcp_verify_integrity":
                  if self.file_tools is None:
                      raise AdapterFailure("file tools adapter is not configured")
                  return {
                      "ok": True,
                      "result": self.file_tools.verify_integrity(
                          str(args["absolute_path"]),
                          str(args["expected_sha256"]),
                          str(args["expected_metadata_hash"]),
                      ),
                  }
              if tool_name == "mcp_extract_image":
                  if self.ocr_provider is None:
                      raise AdapterFailure("OCR provider is not configured")
                  return {
                      "ok": True,
                      "text": self.ocr_provider.extract_image_text(
                          str(args["absolute_path"]),
                          args.get("page"),
                          args.get("region"),
                      ),
                  }
              raise AdapterFailure(f"unknown MCP tool: {tool_name}")
          except KeyError as exc:
              raise AdapterFailure(f"missing required argument: {exc}") from exc
          except ValueError as exc:
              if isinstance(exc, AdapterFailure):
                  raise
              raise AdapterFailure(str(exc)) from exc

--- FILE: python-daemon/orchestrator/shell.py ---
Size: 4697 bytes
Summary: Classes: CommandSpec, ShellExecutionError, ShellAdapter, ZombieReaper; Functions: __init__, _validate, sync_run, _run_subprocess_sync, reap_once
Content: |
  from __future__ import annotations
  
  import asyncio
  import os
  from dataclasses import dataclass, field
  from pathlib import Path
  from typing import Awaitable, Callable
  
  
  @dataclass(frozen=True)
  class CommandSpec:
      executable: str
      args: tuple[str, ...] = field(default_factory=tuple)
      cwd: str | None = None
      env: dict[str, str] = field(default_factory=dict)
      timeout_seconds: float = 60.0
      expected_exit_codes: tuple[int, ...] = (0,)
      mutates_filesystem: bool = False
  
  
  class ShellExecutionError(RuntimeError):
      pass
  
  
  Runner = Callable[[CommandSpec], Awaitable[tuple[int, bytes, bytes]]]
  
  
  class ShellAdapter:
      def __init__(self, allowed_roots: tuple[Path, ...], runner: Runner | None = None) -> None:
          self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
          self.runner = runner
  
      def _validate(self, spec: CommandSpec) -> None:
          if not spec.executable:
              raise ShellExecutionError("executable is required")
          forbidden = ["|", "&", ";", ">", "<"]
          if any(char in spec.executable for char in forbidden):
              raise ShellExecutionError("raw shell syntax is forbidden")
          for key, value in spec.env.items():
              if any(char in key for char in forbidden) or any(char in value for char in forbidden):
                  raise ShellExecutionError("raw shell syntax is forbidden in env")
          if spec.cwd is not None:
              cwd = Path(spec.cwd).resolve()
              if not any(cwd == root or root in cwd.parents for root in self.allowed_roots):
                  raise ShellExecutionError("cwd escapes allowed roots")
  
      async def run(self, spec: CommandSpec) -> tuple[int, str, str]:
          self._validate(spec)
          if self.runner is None:
              rc, stdout_b, stderr_b = await self._run_subprocess(spec)
          else:
              rc, stdout_b, stderr_b = await self.runner(spec)
          stdout = stdout_b.decode("utf-8", errors="replace")
          stderr = stderr_b.decode("utf-8", errors="replace")
          if rc not in spec.expected_exit_codes:
              raise ShellExecutionError(f"unexpected exit code={rc}: {stderr}")
          return rc, stdout, stderr
  
      def sync_run(self, spec: CommandSpec) -> tuple[int, str, str]:
          self._validate(spec)
          if self.runner is None:
              rc, stdout_b, stderr_b = self._run_subprocess_sync(spec)
          else:
              import asyncio
              try:
                  asyncio.get_running_loop()
              except RuntimeError:
                  rc, stdout_b, stderr_b = asyncio.run(self.runner(spec))
              else:
                  raise ShellExecutionError("async runner cannot be used from a running event loop")
          stdout = stdout_b.decode("utf-8", errors="replace")
          stderr = stderr_b.decode("utf-8", errors="replace")
          if rc not in spec.expected_exit_codes:
              raise ShellExecutionError(f"unexpected exit code={rc}: {stderr}")
          return rc, stdout, stderr
  
      def _run_subprocess_sync(self, spec: CommandSpec) -> tuple[int, bytes, bytes]:
          import subprocess
          try:
              completed = subprocess.run(
                  [spec.executable, *spec.args],
                  cwd=spec.cwd,
                  env=spec.env or None,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
                  timeout=spec.timeout_seconds,
                  check=False,
              )
          except subprocess.TimeoutExpired as exc:
              raise ShellExecutionError("command timed out") from exc
          return completed.returncode, completed.stdout, completed.stderr
  
      async def _run_subprocess(self, spec: CommandSpec) -> tuple[int, bytes, bytes]:
          proc = await asyncio.create_subprocess_exec(
              spec.executable,
              *spec.args,
              cwd=spec.cwd,
              env=spec.env or None,
              stdout=asyncio.subprocess.PIPE,
              stderr=asyncio.subprocess.PIPE,
          )
          try:
              stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=spec.timeout_seconds)
          except asyncio.TimeoutError as exc:
              proc.kill()
              await proc.communicate()
              raise ShellExecutionError("command timed out") from exc
          return proc.returncode if proc.returncode is not None else 0, stdout_b, stderr_b
  
  
  class ZombieReaper:
      def reap_once(self, pid: int) -> tuple[int, int] | None:
          if os.name == "nt" or pid <= 0 or not hasattr(os, "waitpid") or not hasattr(os, "WNOHANG"):
              return None
          waited_pid, status = os.waitpid(pid, os.WNOHANG)
          if waited_pid == 0:
              return None
          return waited_pid, status

--- FILE: python-daemon/tests/test_epistemic_and_reroll.py ---
Size: 2454 bytes
Summary: Classes: EpistemicAndRerollTests; Functions: setUp, tearDown, test_depth_penalty_is_applied_before_routing, test_major_slr_conflict_enters_identity_freeze, test_validation_failure_adds_negative_constraint_then_dead_letters_after_limit
Content: |
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.epistemic import EpistemicPolicy, EpistemicSignals
  from orchestrator.execution_loop import ExecutionLoop
  from orchestrator.queue_repo import QueueRepository
  from orchestrator.reroll import ValidationFailure
  
  
  class EpistemicAndRerollTests(unittest.TestCase):
      def setUp(self):
          self.tmp = tempfile.TemporaryDirectory()
          self.root = Path(self.tmp.name)
          bootstrap_databases(self.root)
          self.repo = QueueRepository(self.root / "queue.db", self.root / "control.db")
  
      def tearDown(self):
          self.tmp.cleanup()
  
      def test_depth_penalty_is_applied_before_routing(self):
          policy = EpistemicPolicy(depth_penalty=1.5)
          scored = policy.score(EpistemicSignals(logic_signal=10, sycophancy_signal=1), base_score=20.0, depth=3)
  
          self.assertEqual(scored.final_score, 15.5)
          self.assertEqual(scored.depth_penalty, 4.5)
          self.assertLess(scored.slr_score, 0.22)
          self.assertEqual(scored.decision, "route")
  
      def test_major_slr_conflict_enters_identity_freeze(self):
          policy = EpistemicPolicy()
          scored = policy.score(EpistemicSignals(logic_signal=2, sycophancy_signal=2), base_score=10.0, depth=0)
  
          self.assertGreaterEqual(scored.slr_score, 0.35)
          self.assertEqual(scored.decision, "identity_freeze")
  
      def test_validation_failure_adds_negative_constraint_then_dead_letters_after_limit(self):
          self.repo.create_task("task", "p", "Task", {"tool": "bad"}, depth=0)
          loop = ExecutionLoop(self.repo, max_rerolls=1)
  
          first = loop.handle_validation_failure(
              "task",
              ValidationFailure(tool_name="mcp_semantic_search", details=[{"path": "/query", "message": "required"}]),
          )
          second = loop.handle_validation_failure(
              "task",
              ValidationFailure(tool_name="mcp_semantic_search", details=[{"path": "/query", "message": "required"}]),
          )
  
          self.assertEqual(first["action"], "reroll")
          self.assertIn("Negative constraint", first["context"])
          self.assertEqual(second["action"], "dead_letter")
          dead_letters = self.repo.list_dead_letters()
          self.assertEqual(len(dead_letters), 1)
          self.assertIn("schema_validation_failed", dead_letters[0]["reason"])
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/orchestrator/ingest/service.py ---
Size: 8831 bytes
Summary: Classes: IngestTargetService; Functions: __init__, ingest_target, search, rebuild_chroma_for_project, _resolve, _ignored_file, _ignored_path_parts, _target_files, _process_file, _chunk_id
Content: |
  from __future__ import annotations
  
  import fnmatch
  import hashlib
  import json
  from pathlib import Path
  from typing import Any
  
  from ..chroma_manager import ChromaAdapterError, ChromaManager
  from ..queue_repo import QueueRepository
  from .processors import (
      DocumentChunk,
      IngestProcessorError,
      MetadataAdapter,
      PdfProcessorAdapter,
      SemanticSlicerAdapter,
      TextProcessorAdapter,
  )
  
  
  class IngestTargetService:
      python_exts = {".py"}
      ignored_directory_names = {
          ".git",
          "__pycache__",
          "node_modules",
          ".venv",
          "venv",
          ".cache",
          "output",
          "runs",
          "failed_workspaces",
          "unsloth_compiled_cache",
          ".venv_semantic",
          ".venv_training",
          ".mypy_cache",
          ".pytest_cache",
          "dist",
          "build",
      }
      ignored_file_suffixes = {
          ".db",
          ".sqlite",
          ".sqlite3",
          ".h5",
          ".hdf5",
          ".zip",
          ".tar",
          ".gz",
          ".7z",
          ".rar",
          ".png",
          ".jpg",
          ".jpeg",
          ".gif",
          ".webp",
          ".parquet",
      }
      ignored_file_patterns = (
          "*_bundle*.py",
          "*_bundle*.yaml",
          "*_Extraction.*",
          "agnostic_bundle*",
          "Data_Processing_Efficiency_Audit*",
          "DAG_Math_Logic_Extraction*",
      )
  
      def __init__(
          self,
          repo: QueueRepository,
          chroma: ChromaManager,
          *,
          allowed_roots: tuple[Path, ...],
          metadata: MetadataAdapter | None = None,
          text_processor: TextProcessorAdapter | None = None,
          pdf_processor: PdfProcessorAdapter | None = None,
          semantic_slicer: SemanticSlicerAdapter | None = None,
      ) -> None:
          self.repo = repo
          self.chroma = chroma
          self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
          self.metadata = metadata or MetadataAdapter()
          self.text_processor = text_processor or TextProcessorAdapter()
          self.pdf_processor = pdf_processor or PdfProcessorAdapter()
          self.semantic_slicer = semantic_slicer or SemanticSlicerAdapter()
  
      def ingest_target(
          self,
          project_id: str,
          absolute_path: str,
          *,
          mime_type: str | None = None,
          force_reindex: bool = False,
      ) -> dict[str, Any]:
          path = self._resolve(absolute_path)
          files = self._target_files(path)
          scope_hash = self.chroma.project_scope_hash(project_id)
          run_id = hashlib.sha1(f"{project_id}|{path}|{scope_hash}".encode("utf-8")).hexdigest()
          self.repo.start_ingestion_run(run_id, project_id, scope_hash, str(path))
          indexed = 0
          skipped = 0
          removed = 0
          try:
              current_paths = {str(file_path.resolve()) for file_path in files}
              if path.is_dir():
                  stale_paths = self.repo.file_paths_for_scope(scope_hash) - current_paths
                  for stale_path in sorted(stale_paths):
                      self.repo.delete_file_manifest(scope_hash, stale_path)
                      self.chroma.delete_chunks(project_id=project_id, absolute_path=stale_path)
                      removed += 1
              for file_path in files:
                  file_metadata = self.metadata.extract(file_path)
                  resolved_path = str(file_path.resolve())
                  previous = self.repo.file_manifest(scope_hash, resolved_path)
                  unchanged = previous is not None and previous["file_sha256"] == file_metadata["file_sha256"]
                  if unchanged and not force_reindex:
                      skipped += 1
                      continue
                  if force_reindex or previous is not None:
                      self.repo.delete_chunks_for_path(scope_hash, resolved_path)
                      self.chroma.delete_chunks(project_id=project_id, absolute_path=resolved_path)
                  chunks = self._process_file(file_path, mime_type)
                  if not chunks:
                      continue
                  chunk_payloads = []
                  for chunk in chunks:
                      metadata = {**file_metadata, **chunk.metadata}
                      metadata["project_id"] = project_id
                      metadata["project_scope_hash"] = scope_hash
                      metadata["absolute_path"] = str(file_path.resolve())
                      chunk_id = self._chunk_id(scope_hash, metadata, chunk.content)
                      chunk_payloads.append({"chunk_id": chunk_id, "content": chunk.content, "metadata": metadata})
                  self.repo.record_file_manifest(project_id, scope_hash, file_metadata)
                  self.repo.record_chunks(project_id, scope_hash, run_id, chunk_payloads)
                  try:
                      self.chroma.upsert_chunks(project_id=project_id, chunks=chunk_payloads)
                  except ChromaAdapterError as exc:
                      self.repo.finish_ingestion_run(run_id, "FAILED_VECTOR_UPSERT", str(exc))
                      raise
                  indexed += len(chunk_payloads)
              self.repo.finish_ingestion_run(run_id, "COMPLETED", None)
          except Exception as exc:
              try:
                  if self.repo.latest_ingestion_run(project_id)["state"] != "FAILED_VECTOR_UPSERT":
                      self.repo.finish_ingestion_run(run_id, "FAILED", str(exc))
              except KeyError:
                  self.repo.finish_ingestion_run(run_id, "FAILED", str(exc))
              raise
          return {
              "project_id": project_id,
              "project_scope_hash": scope_hash,
              "absolute_path": str(path),
              "chunks_indexed": indexed,
              "files_skipped": skipped,
              "files_removed": removed,
              "run_id": run_id,
          }
  
      def search(self, project_id: str, query: str, k: int) -> list[dict[str, object]]:
          return self.chroma.search(project_id, query, k)
  
      def rebuild_chroma_for_project(self, project_id: str) -> dict[str, Any]:
          chunks = self.repo.list_rebuildable_chunks(project_id)
          if not chunks:
              chunks = self.repo.chunks_for_rebuild(project_id)
          result = self.chroma.rebuild_from_chunks(project_id, chunks)
          self.repo.mark_rebuildable_runs_reconciled(project_id)
          return result
  
      def _resolve(self, target: str) -> Path:
          resolved = Path(target).resolve()
          if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
              raise ValueError("path escapes allowed roots")
          if not resolved.exists():
              raise ValueError(f"target does not exist: {target}")
          return resolved
  
      def _ignored_file(self, path: Path) -> bool:
          lower_name = path.name.lower()
          normalized = path.as_posix()
          return (
              path.suffix.lower() in self.ignored_file_suffixes
              or any(
                  fnmatch.fnmatch(path.name, pattern)
                  or fnmatch.fnmatch(normalized, pattern)
                  for pattern in self.ignored_file_patterns
              )
              or lower_name.endswith(".jsonl")
          )
  
      def _ignored_path_parts(self, path: Path) -> bool:
          return any(
              part in self.ignored_directory_names
              or fnmatch.fnmatch(part, "*_bundle_*")
              or fnmatch.fnmatch(part, "*_bundle*")
              for part in path.parts
          )
  
      def _target_files(self, target: Path) -> list[Path]:
          if target.is_file():
              return [target]
          return sorted(
              path
              for path in target.rglob("*")
              if path.is_file()
              and not self._ignored_path_parts(path)
              and not self._ignored_file(path)
          )
  
      def _process_file(self, path: Path, mime_type: str | None) -> list[DocumentChunk]:
          if path.suffix.lower() == ".pdf" or mime_type == "application/pdf":
              return self.pdf_processor.process_file(path)
          if path.suffix.lower() in self.python_exts:
              try:
                  chunks = self.semantic_slicer.process_file(path)
                  if chunks:
                      return chunks
              except IngestProcessorError:
                  return self.text_processor.process_file(path)
          return self.text_processor.process_file(path)
  
      def _chunk_id(self, scope_hash: str, metadata: dict[str, Any], content: str) -> str:
          material = {
              "scope": scope_hash,
              "path": metadata.get("absolute_path"),
              "chunk_index": metadata.get("chunk_index"),
              "processor": metadata.get("processor"),
              "content_sha1": hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest(),
          }
          return hashlib.sha1(json.dumps(material, sort_keys= [REDACTED_HIGH_ENTROPY]

--- FILE: python-daemon/orchestrator/chroma_manager.py ---
Size: 8621 bytes
Summary: Classes: ChromaAdapterError, ChromaConfig, ChromaManager; Functions: __init__, project_scope_hash, switch_project, embed_text, upsert_chunks, search, delete_chunks, rebuild_from_chunks, _chunk_id, _normalize_results
Content: |
  from __future__ import annotations
  
  import hashlib
  import json
  from dataclasses import dataclass
  from functools import lru_cache
  from pathlib import Path
  from typing import Any, Callable
  
  import chromadb
  import requests
  
  from .lm_studio_manager import LMStudioManager, LMStudioManagerConfig, LMStudioManagerError
  
  
  class ChromaAdapterError(ValueError):
      pass
  
  
  @dataclass(frozen=True)
  class ChromaConfig:
      chroma_path: Path
      collection_name: str = "aletheia_chunks"
      lm_studio_base_url: str = "http://localhost:1234/v1"
      lm_studio_api_base_url: str = [REDACTED_HIGH_ENTROPY]
      lm_studio_api_token: str | None = None
      embedding_model: str = "text-embedding-nomic-embed-text-v1.5"
      nomic_prefix: str = "search_document: "
      request_timeout_seconds: float = 30.0
      auto_load_embedding_model: bool = True
  
  
  class ChromaManager:
      def __init__(
          self,
          config: ChromaConfig,
          *,
          http_post: Callable[..., Any] = requests.post,
          chroma_client: Any | None = None,
          lm_studio_manager: LMStudioManager | None = None,
      ) -> None:
          self.config = config
          self.http_post = http_post
          self.client = chroma_client or chromadb.PersistentClient(path=str(config.chroma_path))
          self.collection = self.client.get_or_create_collection(name=config.collection_name)
          self._active_scope_hash: str | None = None
          if config.auto_load_embedding_model:
              self.lm_studio_manager = lm_studio_manager or LMStudioManager(
                  LMStudioManagerConfig(
                      api_base_url=config.lm_studio_api_base_url,
                      api_token=config.lm_studio_api_token,
                      request_timeout_seconds=config.request_timeout_seconds,
                  )
              )
          else:
              self.lm_studio_manager = None
  
      def project_scope_hash(self, project_id: str, params: dict[str, Any] | None = None) -> str:
          if not project_id:
              raise ChromaAdapterError("project_id is required")
          material = {"project_id": project_id, "params": params or {}}
          encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
          return hashlib.sha1(encoded).hexdigest()
  
      def switch_project(self, project_id: str, params: dict[str, Any] | None = None) -> str:
          scope_hash = self.project_scope_hash(project_id, params)
          if scope_hash != self._active_scope_hash:
              self.embed_text.cache_clear()
              self._active_scope_hash = scope_hash
          return scope_hash
  
      @lru_cache(maxsize=2048)
      def embed_text(self, text: str) -> list[float]:
          if not text or not text.strip():
              raise ChromaAdapterError("cannot embed empty text")
          if self.lm_studio_manager is not None:
              try:
                  self.lm_studio_manager.ensure_embedding_model_loaded(self.config.embedding_model)
              except LMStudioManagerError as exc:
                  raise ChromaAdapterError(f"LM Studio embedding model readiness failed: {exc}") from exc
          payload = {
              "input": f"{self.config.nomic_prefix}{text}",
              "model": self.config.embedding_model,
          }
          headers = {"Content-Type": "application/json"}
          if self.config.lm_studio_api_token:
              headers["Authorization"] = f"Bearer {self.config.lm_studio_api_token}"
          try:
              response = self.http_post(
                  url=f"{self.config.lm_studio_base_url.rstrip('/')}/embeddings",
                  json=payload,
                  headers=headers,
                  timeout=self.config.request_timeout_seconds,
              )
              if response.status_code == 401:
                  raise ChromaAdapterError(
                      "LM Studio embeddings endpoint rejected request; set ALETHEIA_LM_STUDIO_API_TOKEN or disable LM Studio API auth"
                  )
              response.raise_for_status()
              embedding = response.json()["data"][0]["embedding"]
          except ChromaAdapterError:
              raise
          except Exception as exc:
              raise ChromaAdapterError(f"embedding generation failed: {exc}") from exc
          if not isinstance(embedding, list) or not embedding:
              raise ChromaAdapterError("embedding response did not contain a vector")
          return [float(value) for value in embedding]
  
      def upsert_chunks(
          self,
          *,
          project_id: str,
          chunks: list[dict[str, Any]],
          project_params: dict[str, Any] | None = None,
      ) -> dict[str, Any]:
          scope_hash = self.switch_project(project_id, project_params)
          if not chunks:
              raise ChromaAdapterError("no chunks supplied")
  
          ids: list[str] = []
          documents: list[str] = []
          embeddings: list[list[float]] = []
          metadatas: list[dict[str, Any]] = []
  
          for chunk in chunks:
              content = str(chunk["content"])
              metadata = dict(chunk.get("metadata") or {})
              chunk_id = str(chunk.get("chunk_id") or self._chunk_id(scope_hash, metadata, content))
              metadata["project_id"] = project_id
              metadata["project_scope_hash"] = scope_hash
              ids.append(chunk_id)
              documents.append(content)
              embeddings.append(self.embed_text(content))
              metadatas.append(metadata)
  
          try:
              self.collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
          except Exception as exc:
              raise ChromaAdapterError(f"ChromaDB upsert failed: {exc}") from exc
  
          return {"project_id": project_id, "project_scope_hash": scope_hash, "chunks_indexed": len(ids)}
  
      def search(
          self,
          project_id: str,
          query: str,
          k: int = 8,
          project_params: dict[str, Any] | None = None,
      ) -> list[dict[str, Any]]:
          if k < 1 or k > 50:
              raise ChromaAdapterError("k must be between 1 and 50")
          scope_hash = self.switch_project(project_id, project_params)
          try:
              query_embedding = self.embed_text(query)
              results = self.collection.query(
                  query_embeddings=[query_embedding],
                  n_results=k,
                  where={"project_scope_hash": scope_hash},
                  include=["documents", "metadatas", "distances"],
              )
          except Exception as exc:
              raise ChromaAdapterError(f"ChromaDB query failed: {exc}") from exc
          return self._normalize_results(results)
  
      def delete_chunks(self, *, project_id: str, absolute_path: str, project_params: dict[str, Any] | None = None) -> None:
          scope_hash = self.switch_project(project_id, project_params)
          path = str(Path(absolute_path).resolve())
          try:
              self.collection.delete(
                  where={
                      "$and": [
                          {"project_scope_hash": {"$eq": scope_hash}},
                          {"absolute_path": {"$eq": path}},
                      ]
                  }
              )
          except Exception as exc:
              raise ChromaAdapterError(f"ChromaDB delete failed: {exc}") from exc
  
      def rebuild_from_chunks(self, project_id: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
          return self.upsert_chunks(project_id=project_id, chunks=chunks)
  
      def _chunk_id(self, scope_hash: str, metadata: dict[str, Any], content: str) -> str:
          material = {
              "scope": scope_hash,
              "source_path": metadata.get("absolute_path") or metadata.get("file_path"),
              "chunk_index": metadata.get("chunk_index"),
              "content_sha1": hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest(),
          }
          return hashlib.sha1(json.dumps(material, sort_keys= [REDACTED_HIGH_ENTROPY]
  
      def _normalize_results(self, results: dict[str, Any]) -> list[dict[str, Any]]:
          ids = (results.get("ids") or [[]])[0]
          docs = (results.get("documents") or [[]])[0]
          metas = (results.get("metadatas") or [[]])[0]
          distances = (results.get("distances") or [[]])[0]
          output: list[dict[str, Any]] = []
          for index, result_id in enumerate(ids):
              output.append(
                  {
                      "id": result_id,
                      "content": docs[index] if index < len(docs) else "",
                      "metadata": metas[index] if index < len(metas) else {},
                      "distance": distances[index] if index < len(distances) else None,
                  }
              )
          return output

--- FILE: python-daemon/orchestrator/worker.py ---
Size: 3352 bytes
Summary: Classes: DaemonWorker; Functions: __init__, wake, register_process, heartbeat, run_once
Content: |
  from __future__ import annotations
  
  import asyncio
  import json
  import logging
  import os
  from datetime import datetime, timedelta, timezone
  from typing import Any
  
  from .adapters import ToolAdapters
  from .execution_loop import ExecutionLoop
  from .queue_repo import QueueRepository
  
  LOGGER = logging.getLogger(__name__)
  
  
  class DaemonWorker:
      def __init__(
          self,
          repo: QueueRepository,
          tool_adapters: ToolAdapters,
          *,
          project_id: str,
          worker_id: str,
          lease_seconds: int = 60,
          idle_sleep_seconds: float = 0.25,
      ) -> None:
          self.repo = repo
          self.loop = ExecutionLoop(repo, tool_adapters=tool_adapters)
          self.project_id = project_id
          self.worker_id = worker_id
          self.lease_seconds = lease_seconds
          self.idle_sleep_seconds = idle_sleep_seconds
          self._wake_event = asyncio.Event()
  
      def wake(self) -> None:
          self._wake_event.set()
  
      def register_process(self, command: list[str] | None = None) -> None:
          self.repo.register_worker(self.worker_id, command or ["aletheia-daemon"], os.getpid())
  
      def heartbeat(self) -> None:
          self.repo.heartbeat_worker(self.worker_id, os.getpid())
  
      def run_once(self) -> dict[str, Any]:
          self.heartbeat()
          self.repo.release_expired_leases(datetime.now(timezone.utc).isoformat())
          lease_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=self.lease_seconds)).isoformat()
          task = self.repo.claim_ready_task(self.project_id, self.worker_id, lease_expires_at)
          if task is None:
              return {"ok": True, "idle": True}
          task_id = task["task_id"]
          LOGGER.info("worker_claimed_task", extra={"extra_fields": {"task_id": task_id, "project_id": self.project_id, "worker_id": self.worker_id}})
          try:
              payload = json.loads(task["payload_json"])
              tool_name = payload["tool"]
              args = payload.get("args", {})
              if not isinstance(tool_name, str) or not isinstance(args, dict):
                  raise ValueError("invalid task payload")
          except Exception as exc:
              self.repo.dead_letter(task_id, "invalid_task_payload", {"error": str(exc), "payload_json": task["payload_json"]})
              self.repo.complete_task(task_id)
              LOGGER.info("worker_dead_lettered_task", extra={"extra_fields": {"task_id": task_id, "reason": "invalid_task_payload"}})
              return {"ok": False, "task_id": task_id, "error": "invalid_task_payload"}
          result = self.loop.execute_tool_for_task(task_id, tool_name, args)
          if result.get("ok") is not False:
              self.repo.complete_task(task_id)
              LOGGER.info("worker_completed_task", extra={"extra_fields": {"task_id": task_id, "project_id": self.project_id}})
          return {"ok": result.get("ok", True), "task_id": task_id, "result": result}
  
      async def run_forever(self, stop_event: asyncio.Event) -> None:
          self.register_process()
          while not stop_event.is_set():
              result = self.run_once()
              if result.get("idle"):
                  try:
                      await asyncio.wait_for(self._wake_event.wait(), timeout=self.idle_sleep_seconds)
                  except asyncio.TimeoutError:
                      pass
                  self._wake_event.clear()

--- FILE: python-daemon/tests/test_hitl_and_shell.py ---
Size: 3468 bytes
Summary: Classes: HitlAndShellTests; Functions: test_zombie_reaper_returns_none_for_non_posix_platforms
Content: |
  import asyncio
  import hmac
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.approval import build_approval_envelope
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.hitl import ApprovalGate
  from orchestrator.queue_repo import QueueRepository
  from orchestrator.shell import CommandSpec, ShellAdapter, ShellExecutionError, ZombieReaper
  
  
  class HitlAndShellTests(unittest.IsolatedAsyncioTestCase):
      async def asyncSetUp(self):
          self.tmp = tempfile.TemporaryDirectory()
          self.root = Path(self.tmp.name)
          bootstrap_databases(self.root)
          self.repo = QueueRepository(self.root / "queue.db", self.root / "control.db")
  
      async def asyncTearDown(self):
          self.tmp.cleanup()
  
      async def test_pending_approval_blocks_until_valid_authorization_hash(self):
          secret = b"secret"
          diff = b"diff"
          envelope = build_approval_envelope(secret, b"base", b"proposed", diff)
          self.repo.create_task("task", "p", "Task", {"tool": "a"}, depth=0)
          self.repo.create_approval("approval", "task", envelope)
          gate = ApprovalGate(self.repo, secret)
  
          waiter = asyncio.create_task(gate.wait_for_approval("task", timeout=0.05))
          with self.assertRaises(asyncio.TimeoutError):
              await waiter
  
          bad = await gate.authorize("task", "not-valid", diff)
          self.assertFalse(bad)
          supplied = hmac.digest(secret, diff, "sha256").hex()
          good = await gate.authorize("task", supplied, diff)
  
          self.assertTrue(good)
          self.assertEqual(self.repo.get_task("task")["state"], "PLANNING")
  
      async def test_pending_approval_rejection_prunes_descendants(self):
          secret = b"secret"
          envelope = build_approval_envelope(secret, b"base", b"proposed", b"diff")
          self.repo.create_task("parent", "p", "Parent", {"tool": "a"}, depth=0)
          self.repo.create_task("child", "p", "Child", {"tool": "b"}, depth=1, parent_task_id="parent")
          self.repo.create_approval("approval", "parent", envelope)
          gate = ApprovalGate(self.repo, secret)
  
          pruned = await gate.reject("parent", decided_by="operator", reason="not safe")
  
          self.assertEqual(pruned, ["child"])
          self.assertEqual(self.repo.get_task("parent")["resolution"], "REJECTED")
          self.assertEqual(self.repo.get_task("child")["resolution"], "CASCADE_PRUNED")
  
      async def test_shell_rejects_raw_shell_syntax_and_runs_argument_arrays(self):
          seen = []
  
          async def fake_runner(spec):
              seen.append((spec.executable, spec.args, spec.cwd))
              return 0, b"ok\n", b""
  
          adapter = ShellAdapter((self.root,), runner=fake_runner)
  
          with self.assertRaises(ShellExecutionError):
              await adapter.run(CommandSpec("python", ("-c", "print(1)"), cwd=str(self.root), timeout_seconds=2, mutates_filesystem=False, env={"A": "B; rm"}))
  
          rc, stdout, stderr = await adapter.run(CommandSpec("python", ("-c", "print('ok')"), cwd=str(self.root)))
          self.assertEqual(rc, 0)
          self.assertEqual(stdout.strip(), "ok")
          self.assertEqual(stderr, "")
          self.assertEqual(seen, [("python", ("-c", "print('ok')"), str(self.root))])
  
      def test_zombie_reaper_returns_none_for_non_posix_platforms(self):
          reaper = ZombieReaper()
          result = reaper.reap_once(-1)
          self.assertIsNone(result)
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/orchestrator/bridge_server.py ---
Size: 6670 bytes
Summary: Classes: JsonRpcError, BridgeSecurity; Functions: line_too_large, json_rpc_result, json_rpc_error, canonical_json, signing_payload, build_auth_envelope, _authorized, handle_json_rpc
Content: |
  from __future__ import annotations
  
  import asyncio
  from collections import deque
  from dataclasses import dataclass, field
  import hashlib
  import hmac
  import json
  import logging
  import time
  from typing import Any
  
  from .adapters import AdapterFailure, ToolAdapters
  
  LOGGER = logging.getLogger(__name__)
  
  
  class JsonRpcError(ValueError):
      pass
  
  
  @dataclass(frozen=True)
  class BridgeSecurity:
      shared_secret: str | None = None
      max_line_bytes: int = 1_000_000
      timestamp_tolerance_seconds: int = 300
      allowed_methods: tuple[str, ...] = ("tools.call", "daemon.health", "daemon.reconcile_project", "daemon.dead_letters")
      enable_admin_bridge: bool = False
      nonce_cache: set[str] = field(default_factory=set)
  
  
  def line_too_large(line: bytes, security: BridgeSecurity) -> bool:
      return len(line) > security.max_line_bytes
  
  
  def json_rpc_result(request_id: str | int | None, result: Any) -> dict[str, Any]:
      return {"jsonrpc": "2.0", "id": request_id, "result": result}
  
  
  def json_rpc_error(request_id: str | int | None, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
      error: dict[str, Any] = {"code": code, "message": message}
      if data is not None:
          error["data"] = data
      return {"jsonrpc": "2.0", "id": request_id, "error": error}
  
  
  def canonical_json(value: Any) -> str:
      return json.dumps(value, sort_keys=True, separators=(",", ":"))
  
  
  def signing_payload(message: dict[str, Any], timestamp: str, nonce: str) -> bytes:
      sanitized = json.loads(canonical_json(message))
      params = dict(sanitized.get("params") or {})
      params.pop("auth", None)
      sanitized["params"] = params
      return f"{timestamp}.{nonce}.{canonical_json(sanitized)}".encode("utf-8")
  
  
  def build_auth_envelope(message: dict[str, Any], shared_secret: str, *, timestamp: str | None = [REDACTED_HIGH_ENTROPY]
      import uuid
      timestamp = timestamp or str(int(time.time()))
      nonce = nonce or str(uuid.uuid4())
      signature = hmac.new(
          shared_secret.encode("utf-8"),
          signing_payload(message, timestamp, nonce),
          hashlib.sha256,
      ).hexdigest()
      return {"timestamp": timestamp, "signature": signature, "nonce": nonce}
  
  
  def _authorized(message= [REDACTED_HIGH_ENTROPY]
      if security.shared_secret is None:
          return True
      auth = (message.get("params") or {}).get("auth")
      if not isinstance(auth, dict):
          return False
      timestamp = auth.get("timestamp")
      signature = auth.get("signature")
      nonce = auth.get("nonce")
      if not isinstance(timestamp, str) or not isinstance(signature, str) or not isinstance(nonce, str):
          return False
      if nonce in security.nonce_cache:
          return False
      try:
          ts = int(timestamp)
      except ValueError:
          return False
      if abs(int(time.time()) - ts) > security.timestamp_tolerance_seconds:
          return False
      expected = build_auth_envelope(message, security.shared_secret, timestamp=timestamp, nonce=nonce)["signature"]
      if not hmac.compare_digest(expected, signature):
          return False
      if len(security.nonce_cache) >= 4096:
          security.nonce_cache.clear()
      security.nonce_cache.add(nonce)
      return True
  
  
  def handle_json_rpc(
      message: dict[str, Any],
      tool_adapters: ToolAdapters,
      security: BridgeSecurity | None = None,
      internal_api: Any | None = None,
  ) -> dict[str, Any]:
      security = security or BridgeSecurity()
      request_id = message.get("id")
      if message.get("jsonrpc") != "2.0":
          return json_rpc_error(request_id, -32600, "Invalid Request")
      method = message.get("method")
      LOGGER.info("bridge_request", extra={"extra_fields": {"request_id": request_id, "method": method}})
      if method not in security.allowed_methods:
          return json_rpc_error(request_id, -32601, "Method not found")
      if method.startswith("daemon.") and (not security.enable_admin_bridge or security.shared_secret is None):
          return json_rpc_error(request_id, -32002, "Admin bridge disabled")
      if not _authorized(message, security):
          return json_rpc_error(request_id, -32001, "Unauthorized")
      params = message.get("params") or {}
      if method == "daemon.health":
          if internal_api is None:
              return json_rpc_error(request_id, -32601, "Method not found")
          return json_rpc_result(request_id, internal_api.health())
      if method == "daemon.reconcile_project":
          if internal_api is None:
              return json_rpc_error(request_id, -32601, "Method not found")
          project_id = params.get("project_id")
          if not isinstance(project_id, str):
              return json_rpc_error(request_id, -32602, "Invalid params")
          return json_rpc_result(request_id, internal_api.reconcile_project(project_id))
      if method == "daemon.dead_letters":
          if internal_api is None:
              return json_rpc_error(request_id, -32601, "Method not found")
          return json_rpc_result(request_id, internal_api.dead_letters(int(params.get("limit", 50))))
      tool_name = params.get("toolName") or params.get("name")
      args = params.get("args") or params.get("arguments") or {}
      if not isinstance(tool_name, str) or not isinstance(args, dict):
          return json_rpc_error(request_id, -32602, "Invalid params")
      try:
          return json_rpc_result(request_id, tool_adapters.call_mcp_tool(tool_name, args))
      except AdapterFailure as exc:
          return json_rpc_result(request_id, {"ok": False, "error": "adapter_failure", "message": str(exc)})
  
  
  async def serve_tcp_bridge(
      host: str,
      port: int,
      tool_adapters: ToolAdapters,
      security: BridgeSecurity | None = None,
      internal_api: Any | None = None,
  ) -> asyncio.AbstractServer:
      security = security or BridgeSecurity()
  
      async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
          try:
              line = await reader.readline()
              if line_too_large(line, security):
                  response = json_rpc_error(None, -32000, "Request too large")
                  writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                  await writer.drain()
                  return
              message = json.loads(line.decode("utf-8"))
              response = handle_json_rpc(message, tool_adapters, security, internal_api)
              writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
              await writer.drain()
          finally:
              writer.close()
              await writer.wait_closed()
  
      return await asyncio.start_server(handle_client, host, port)

--- FILE: python-daemon/orchestrator/ingest/processors.py ---
Size: 14585 bytes
Summary: Classes: IngestProcessorError, DocumentChunk, OCRProvider, MetadataAdapter, TextProcessorAdapter, PdfProcessorAdapter, SemanticSlicerAdapter, WorkspaceScout; Functions: extract_pdf_page_text, extract, file_sha256, __init__, process_file, process_text, __init__, process_file, process_file, _call_name, __init__, scout, _resolve, _ignored_path_parts, _ignored_file, _is_binary, _summary, _tree
Content: |
  from __future__ import annotations
  
  import ast
  import fnmatch
  import hashlib
  import json
  import mimetypes
  import os
  import re
  from dataclasses import dataclass
  from pathlib import Path
  from typing import Any, Protocol
  
  
  class IngestProcessorError(ValueError):
      pass
  
  
  @dataclass(frozen=True)
  class DocumentChunk:
      content: str
      metadata: dict[str, Any]
  
  
  class OCRProvider(Protocol):
      def extract_pdf_page_text(self, absolute_path: str, page_number: int) -> str:
          ...
  
  
  class MetadataAdapter:
      def extract(self, path: Path) -> dict[str, Any]:
          resolved = path.resolve()
          if not resolved.exists() or not resolved.is_file():
              raise IngestProcessorError(f"file does not exist: {path}")
          stat = resolved.stat()
          file_sha256 = self.file_sha256(resolved)
          metadata = {
              "file_sha256": file_sha256,
              "file_name": resolved.name,
              "absolute_path": str(resolved),
              "size_bytes": stat.st_size,
              "mtime_ns": stat.st_mtime_ns,
          }
          metadata["metadata_hash"] = hashlib.sha256(
              json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
          ).hexdigest()
          return metadata
  
      def file_sha256(self, path: Path) -> str:
          digest = hashlib.sha256()
          try:
              with path.open("rb") as handle:
                  for block in iter(lambda: handle.read(8192), b""):
                      digest.update(block)
          except Exception as exc:
              raise IngestProcessorError(f"hash generation failed: {exc}") from exc
          return digest.hexdigest()
  
  
  class TextProcessorAdapter:
      def __init__(self, *, chunk_size: int = 1500, chunk_overlap: int = 200) -> None:
          if chunk_overlap >= chunk_size:
              raise IngestProcessorError("chunk_overlap must be smaller than chunk_size")
          self.chunk_size = chunk_size
          self.chunk_overlap = chunk_overlap
  
      def process_file(self, path: Path) -> list[DocumentChunk]:
          try:
              raw_text = path.read_text(encoding="utf-8", errors="ignore")
          except Exception as exc:
              raise IngestProcessorError(f"text read failed: {exc}") from exc
          return self.process_text(raw_text, file_path=str(path.resolve()), file_name=path.name)
  
      def process_text(self, text: str, *, file_path: str, file_name: str) -> list[DocumentChunk]:
          if not text.strip():
              return []
          chunks: list[DocumentChunk] = []
          start = 0
          chunk_index = 0
          step = self.chunk_size - self.chunk_overlap
          while start < len(text):
              end = min(start + self.chunk_size, len(text))
              content = text[start:end]
              if chunk_index > 0 and len(content) <= self.chunk_overlap:
                  break
              chunks.append(
                  DocumentChunk(
                      content=content,
                      metadata={
                          "absolute_path": file_path,
                          "file_name": file_name,
                          "file_type": "text",
                          "processor": "text",
                          "page_number": 0,
                          "chunk_index": chunk_index,
                      },
                  )
              )
              start += step
              chunk_index += 1
          return chunks
  
  
  class PdfProcessorAdapter:
      def __init__(self, *, ocr_provider: OCRProvider | None = None, text_density_threshold: int = 50) -> None:
          self.ocr_provider = ocr_provider
          self.text_density_threshold = text_density_threshold
          self.text_fallback = TextProcessorAdapter()
  
      def process_file(self, path: Path) -> list[DocumentChunk]:
          try:
              import fitz
          except Exception as exc:
              raise IngestProcessorError("PDF ingestion requires PyMuPDF/fitz") from exc
          chunks: list[DocumentChunk] = []
          try:
              doc = fitz.open(path)
              for page_index, page in enumerate(doc, start=1):
                  raw_text = page.get_text()
                  if len(raw_text.strip()) < self.text_density_threshold and self.ocr_provider is not None:
                      ocr_text = self.ocr_provider.extract_pdf_page_text(str(path.resolve()), page_index)
                      if len(ocr_text.strip()) > len(raw_text.strip()):
                          raw_text = ocr_text
                  for chunk in self.text_fallback.process_text(
                      raw_text,
                      file_path=str(path.resolve()),
                      file_name=path.name,
                  ):
                      metadata = dict(chunk.metadata)
                      metadata["file_type"] = "pdf"
                      metadata["processor"] = "pdf"
                      metadata["page_number"] = page_index
                      chunks.append(DocumentChunk(chunk.content, metadata))
              doc.close()
          except Exception as exc:
              raise IngestProcessorError(f"PDF processing failed: {exc}") from exc
          return chunks
  
  
  class SemanticSlicerAdapter:
      def process_file(self, path: Path) -> list[DocumentChunk]:
          try:
              source = path.read_text(encoding="utf-8", errors="ignore")
              tree = ast.parse(source)
          except SyntaxError as exc:
              raise IngestProcessorError(f"syntax error at line {exc.lineno}: {exc.msg}") from exc
          except Exception as exc:
              raise IngestProcessorError(f"semantic slicing failed: {exc}") from exc
          lines = source.splitlines()
          chunks: list[DocumentChunk] = []
          rel_name = path.name
          for node in ast.walk(tree):
              if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                  continue
              start = int(getattr(node, "lineno", 1))
              end = int(getattr(node, "end_lineno", start))
              body = "\n".join(lines[start - 1:end])
              node_dump = ast.dump(node, annotate_fields=False, include_attributes=False)
              body_hash = hashlib.sha1(node_dump.encode("utf-8", errors="ignore")).hexdigest()[:10]
              calls = sorted(
                  {
                      self._call_name(child)
                      for child in ast.walk(node)
                      if isinstance(child, ast.Call) and self._call_name(child)
                  }
              )
              chunk_index = len(chunks)
              chunks.append(
                  DocumentChunk(
                      content=body,
                      metadata={
                          "absolute_path": str(path.resolve()),
                          "file_name": path.name,
                          "file_type": "code",
                          "processor": "semantic_slicer",
                          "chunk_index": chunk_index,
                          "symbol_name": node.name,
                          "symbol_type": type(node).__name__,
                          "start_line": start,
                          "end_line": end,
                          "slice_id": f"{rel_name}::{node.name}@{body_hash}",
                          "calls_json": json.dumps(calls),
                      },
                  )
              )
          return chunks
  
      def _call_name(self, node: ast.Call) -> str | None:
          if isinstance(node.func, ast.Name):
              return node.func.id
          if isinstance(node.func, ast.Attribute):
              return node.func.attr
          return None
  
  
  class WorkspaceScout:
      ignore_dirs = {
          ".git",
          "__pycache__",
          ".venv",
          "venv",
          "node_modules",
          ".idea",
          ".vscode",
          "dist",
          "build",
          "output",
          "runs",
          "failed_workspaces",
          "unsloth_compiled_cache",
          ".venv_semantic",
          ".venv_training",
          ".mypy_cache",
          ".pytest_cache",
      }
      ignore_file_patterns = (
          "*_bundle*.py",
          "*_bundle*.yaml",
          "*_Extraction.*",
          "agnostic_bundle*",
          "Data_Processing_Efficiency_Audit*",
          "DAG_Math_Logic_Extraction*",
      )
      ignore_exts = {
          ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".tiff",
          ".zip", ".gz", ".tar", ".tgz", ".bz2", ".xz", ".7z", ".rar",
          ".exe", ".dll", ".so", ".dylib", ".pdf", ".bin", ".class",
          ".pyc", ".sqlite", ".sqlite3", ".db", ".h5", ".hdf5", ".parquet",
      }
  
      def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
          self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
  
      def scout(
          self,
          project_id: str,
          absolute_path: str,
          *,
          max_files: int = 500,
          include_summaries: bool = True,
      ) -> dict[str, Any]:
          root = self._resolve(absolute_path)
          if not root.is_dir():
              raise IngestProcessorError("workspace scout target must be a directory")
          files: list[dict[str, Any]] = []
          skipped = 0
          skipped_details = {"ignored_extension": 0, "binary": 0, "oversize": 0, "errors": 0}
          for current, dirs, names in os.walk(root):
              dirs[:] = sorted(
                  d for d in dirs
                  if d not in self.ignore_dirs
                  and not d.startswith(".")
                  and not fnmatch.fnmatch(d, "*_bundle_*")
                  and not fnmatch.fnmatch(d, "*_bundle*")
              )
              for name in sorted(names):
                  path = Path(current) / name
                  if len(files) >= max_files:
                      skipped += 1
                      skipped_details["oversize"] += 1
                      continue
                  if path.suffix.lower() in self.ignore_exts:
                      skipped += 1
                      skipped_details["ignored_extension"] += 1
                      continue
                  if self._ignored_path_parts(path):
                      skipped += 1
                      skipped_details["ignored_extension"] += 1
                      continue
                  if self._ignored_file(path):
                      skipped += 1
                      skipped_details["ignored_extension"] += 1
                      continue
                  if path.stat().st_size > 1_500_000:
                      skipped += 1
                      skipped_details["oversize"] += 1
                      continue
                  if self._is_binary(path):
                      skipped += 1
                      skipped_details["binary"] += 1
                      continue
                  try:
                      raw = path.read_text(encoding="utf-8", errors="ignore")
                      rel = path.relative_to(root).as_posix()
                      entry: dict[str, Any] = {
                          "path": rel,
                          "size_bytes": path.stat().st_size,
                          "sha256": MetadataAdapter().file_sha256(path),
                      }
                      if include_summaries:
                          entry["summary"] = self._summary(path, raw)
                      files.append(entry)
                  except Exception:
                      skipped += 1
                      skipped_details["errors"] += 1
          files.sort(key=lambda item: item["path"])
          tree = self._tree(root, files)
          payload = {"project_id": project_id, "root": str(root), "tree": tree, "files": files, "skipped_count": skipped}
          package_hash = [REDACTED_HIGH_ENTROPY]
          return {
              "project_id": project_id,
              "absolute_path": str(root),
              "tree": tree,
              "file_count": len(files),
              "skipped_count": skipped,
              "files": files,
              "package_hash": package_hash,
              "skipped_details": skipped_details,
          }
  
      def _resolve(self, path: str) -> Path:
          resolved = Path(path).resolve()
          if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
              raise IngestProcessorError("path escapes allowed roots")
          return resolved
  
      def _ignored_path_parts(self, path: Path) -> bool:
          return any(
              part in self.ignore_dirs
              or fnmatch.fnmatch(part, "*_bundle_*")
              or fnmatch.fnmatch(part, "*_bundle*")
              for part in path.parts
          )
  
      def _ignored_file(self, path: Path) -> bool:
          lower_name = path.name.lower()
          normalized = path.as_posix()
          return (
              lower_name.endswith(".jsonl")
              or any(
                  fnmatch.fnmatch(path.name, pattern)
                  or fnmatch.fnmatch(normalized, pattern)
                  for pattern in self.ignore_file_patterns
              )
          )
  
      def _is_binary(self, path: Path, scan_bytes: int = 2048) -> bool:
          try:
              sample = path.read_bytes()[:scan_bytes]
          except Exception:
              return True
          if b"\x00" in sample:
              return True
          guess, _ = mimetypes.guess_type(str(path))
          return bool(guess and not guess.startswith(("text", "application")))
  
      def _summary(self, path: Path, raw: str) -> dict[str, Any]:
          if path.suffix.lower() == ".py":
              try:
                  tree = ast.parse(raw)
              except SyntaxError:
                  return {"syntax_valid": False}
              return {
                  "syntax_valid": True,
                  "functions": [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)][:20],
                  "classes": [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)][:20],
              }
          if path.suffix.lower() in {".md", ".markdown"}:
              return {"headers": re.findall(r"^#{1,3}\s+(.*)", raw, re.MULTILINE)[:20]}
          if path.suffix.lower() == ".json":
              try:
                  data = json.loads(raw)
                  return {"keys": list(data.keys())[:20] if isinstance(data, dict) else ["<array>"]}
              except json.JSONDecodeError:
                  return {"syntax_valid": False}
          return {}
  
      def _tree(self, root: Path, files: list[dict[str, Any]]) -> str:
          lines = [f"{root.name}/"]
          seen_dirs: set[str] = set()
          for entry in files:
              parts = Path(entry["path"]).parts
              for index, part in enumerate(parts[:-1]):
                  directory = str(Path(*parts[: index + 1]))
                  if directory not in seen_dirs:
                      lines.append(f"{'  ' * (index + 1)}|-- {part}/")
                      seen_dirs.add(directory)
              lines.append(f"{'  ' * len(parts)}|-- {parts[-1]}")
          return "\n".join(lines)

--- FILE: python-daemon/orchestrator/queue_repo.py ---
Size: 27829 bytes
Summary: Classes: QueueRepository; Functions: _now, _dict, hashlib_sha1, __init__, _queue, _control, create_task, _record_task_event, list_task_events, get_task, claim_ready_task, release_expired_leases, set_task_state, transition_task_state, complete_task, reject_and_prune, _descendants, create_approval, approve_task, reject_approval, update_scores, add_negative_constraint, dead_letter, list_dead_letters, start_ingestion_run, finish_ingestion_run, latest_ingestion_run, record_file_manifest, file_manifest, file_paths_for_scope, delete_file_manifest, record_chunks, list_chunks, delete_chunks_for_path, chunks_for_rebuild, list_rebuildable_chunks, mark_rebuildable_runs_reconciled, count_file_manifests, register_worker, heartbeat_worker, mark_stale_workers, list_worker_status, mark_worker_exited
Content: |
  from __future__ import annotations
  
  import json
  import os
  import sqlite3
  import uuid
  from contextlib import closing
  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any
  
  from .approval import DiffApprovalEnvelope, md5_novelty_hex
  from .dag_runtime import topological_descendants
  
  ALLOWED_TASK_TRANSITIONS = {
      ("PLANNING", "PENDING_APPROVAL"),
      ("PLANNING", "COMPLETED"),
      ("PENDING_APPROVAL", "PLANNING"),
      ("PENDING_APPROVAL", "COMPLETED"),
  }
  
  
  def _now() -> str:
      return datetime.now(timezone.utc).isoformat()
  
  
  def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
      if row is None:
          return None
      return {key: row[key] for key in row.keys()}
  
  
  class QueueRepository:
      def __init__(self, queue_db: Path, control_db: Path) -> None:
          self.queue_db = queue_db
          self.control_db = control_db
  
      def _queue(self) -> sqlite3.Connection:
          conn = sqlite3.connect(self.queue_db)
          conn.row_factory = sqlite3.Row
          conn.execute("PRAGMA busy_timeout = 5000")
          conn.execute("PRAGMA foreign_keys = ON")
          return conn
  
      def _control(self) -> sqlite3.Connection:
          conn = sqlite3.connect(self.control_db)
          conn.row_factory = sqlite3.Row
          conn.execute("PRAGMA busy_timeout = 5000")
          return conn
  
      def create_task(
          self,
          task_id: str,
          project_id: str,
          title: str,
          payload: dict[str, Any],
          *,
          depth: int,
          parent_task_id: str | None = None,
      ) -> None:
          now = _now()
          novelty = md5_novelty_hex(
              {
                  "tool": payload.get("tool"),
                  "arg_shape": sorted(payload.keys()),
                  "parent_task_id": parent_task_id,
                  "depth": depth,
              }
          )
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  INSERT INTO tasks (
                    task_id, project_id, state, resolution, parent_task_id, title, payload_json,
                    slr_score, depth_penalty, final_score, depth, novelty_md5, created_at, updated_at
                  ) VALUES (?, ?, 'PLANNING', 'ACTIVE', ?, ?, ?, 0.0, 0.0, 0.0, ?, ?, ?, ?)
                  """,
                  (task_id, project_id, parent_task_id, title, json.dumps(payload), depth, novelty, now, now),
              )
              if parent_task_id is not None:
                  conn.execute(
                      "INSERT INTO task_edges(parent_task_id, child_task_id) VALUES (?, ?)",
                      (parent_task_id, task_id),
                  )
              conn.commit()
  
      def _record_task_event(
          self,
          conn: sqlite3.Connection,
          task_id: str,
          event_type: str,
          details: dict[str, Any],
      ) -> None:
          conn.execute(
              """
              INSERT INTO task_events(event_id, task_id, event_type, details_json, created_at)
              VALUES (?, ?, ?, ?, ?)
              """,
              (str(uuid.uuid4()), task_id, event_type, json.dumps(details, sort_keys=True), _now()),
          )
  
      def list_task_events(self, task_id: str) -> list[dict[str, Any]]:
          with closing(self._queue()) as conn:
              rows = conn.execute(
                  "SELECT * FROM task_events WHERE task_id = ? ORDER BY created_at ASC",
                  (task_id,),
              ).fetchall()
          return [_dict(row) for row in rows if row is not None]
  
      def get_task(self, task_id: str) -> dict[str, Any]:
          with closing(self._queue()) as conn:
              row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
          result = _dict(row)
          if result is None:
              raise KeyError(task_id)
          return result
  
      def claim_ready_task(self, project_id: str, worker_id: str, lease_expires_at: str) -> dict[str, Any] | None:
          now = _now()
          conn = self._queue()
          try:
              conn.execute("BEGIN IMMEDIATE")
              row = conn.execute(
                  """
                  WITH next_task AS (
                      SELECT t.task_id
                      FROM tasks t
                      WHERE t.project_id = ?
                        AND t.state = 'PLANNING'
                        AND t.resolution = 'ACTIVE'
                        AND t.lease_owner IS NULL
                        AND NOT EXISTS (
                            SELECT 1
                            FROM task_edges e
                            JOIN tasks p ON p.task_id = e.parent_task_id
                            WHERE e.child_task_id = t.task_id
                              AND (p.state <> 'COMPLETED' OR p.resolution <> 'ACTIVE')
                        )
                      ORDER BY t.created_at ASC
                      LIMIT 1
                  )
                  UPDATE tasks
                  SET lease_owner = ?,
                      lease_expires_at = ?,
                      revision = revision + 1,
                      updated_at = ?
                  WHERE task_id IN (SELECT task_id FROM next_task)
                  RETURNING task_id, project_id, state, resolution, payload_json, revision
                  """,
                  (project_id, worker_id, lease_expires_at, now),
              ).fetchone()
              conn.commit()
              result = _dict(row)
          except Exception:
              conn.rollback()
              raise
          finally:
              conn.close()
          if result is not None:
              with closing(self._control()) as control:
                  control.execute(
                      """
                      INSERT INTO leases(lease_id, task_id, worker_id, acquired_at, expires_at, heartbeat_at)
                      VALUES (?, ?, ?, ?, ?, ?)
                      """,
                      (str(uuid.uuid4()), result["task_id"], worker_id, now, lease_expires_at, now),
                  )
                  control.commit()
          return result
  
      def release_expired_leases(self, now_iso: str) -> int:
          conn = self._queue()
          try:
              conn.execute("BEGIN IMMEDIATE")
              rows = conn.execute(
                  """
                  SELECT task_id
                  FROM tasks
                  WHERE lease_owner IS NOT NULL
                    AND lease_expires_at IS NOT NULL
                    AND lease_expires_at < ?
                  """,
                  (now_iso,),
              ).fetchall()
              task_ids = [row["task_id"] for row in rows]
              for task_id in task_ids:
                  conn.execute(
                      """
                      UPDATE tasks
                      SET lease_owner = NULL,
                          lease_expires_at = NULL,
                          updated_at = ?,
                          revision = revision + 1
                      WHERE task_id = ?
                      """,
                      (_now(), task_id),
                  )
              conn.commit()
          except Exception:
              conn.rollback()
              raise
          finally:
              conn.close()
          if task_ids:
              with closing(self._control()) as control:
                  for task_id in task_ids:
                      control.execute("DELETE FROM leases WHERE task_id = ?", (task_id,))
                  control.commit()
          return len(task_ids)
  
      def set_task_state(self, task_id: str, state: str) -> None:
          current = self.get_task(task_id)["state"]
          self.transition_task_state(task_id, current, state, reason="set_task_state")
  
      def transition_task_state(
          self,
          task_id: str,
          from_state: str,
          to_state: str,
          *,
          reason: str,
      ) -> None:
          if (from_state, to_state) not in ALLOWED_TASK_TRANSITIONS:
              raise ValueError(f"invalid task transition: {from_state} -> {to_state}")
          now = _now()
          with closing(self._queue()) as conn:
              row = conn.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
              if row is None:
                  raise KeyError(task_id)
              if row["state"] != from_state:
                  raise ValueError(f"task {task_id} is {row['state']}, not {from_state}")
              conn.execute(
                  "UPDATE tasks SET state = ?, updated_at = ?, revision = revision + 1 WHERE task_id = ?",
                  (to_state, now, task_id),
              )
              self._record_task_event(
                  conn,
                  task_id,
                  "state_transition",
                  {"from_state": from_state, "to_state": to_state, "reason": reason},
              )
              conn.commit()
  
      def complete_task(self, task_id: str) -> None:
          now = _now()
          with closing(self._queue()) as conn:
              row = conn.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
              if row is None:
                  raise KeyError(task_id)
              if (row["state"], "COMPLETED") not in ALLOWED_TASK_TRANSITIONS:
                  raise ValueError(f"invalid task transition: {row['state']} -> COMPLETED")
              conn.execute(
                  """
                  UPDATE tasks
                  SET state = 'COMPLETED', lease_owner = NULL, lease_expires_at = NULL,
                      completed_at = ?, updated_at = ?, revision = revision + 1
                  WHERE task_id = ?
                  """,
                  (now, now, task_id),
              )
              self._record_task_event(
                  conn,
                  task_id,
                  "state_transition",
                  {"from_state": row["state"], "to_state": "COMPLETED", "reason": "complete_task"},
              )
              conn.commit()
          with closing(self._control()) as conn:
              conn.execute("DELETE FROM leases WHERE task_id = ?", (task_id,))
              conn.commit()
  
      def reject_and_prune(self, task_id: str, reason: str) -> list[str]:
          descendants = self._descendants(task_id)
          now = _now()
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  UPDATE tasks
                  SET resolution = 'REJECTED', lease_owner = NULL, lease_expires_at = NULL,
                      pruned_reason = ?, updated_at = ?, revision = revision + 1
                  WHERE task_id = ?
                  """,
                  (reason, now, task_id),
              )
              self._record_task_event(
                  conn,
                  task_id,
                  "resolution_transition",
                  {"to_resolution": "REJECTED", "reason": reason},
              )
              for child_id in descendants:
                  conn.execute(
                      """
                      UPDATE tasks
                      SET resolution = 'CASCADE_PRUNED', lease_owner = NULL, lease_expires_at = NULL,
                          pruned_by_task_id = ?, pruned_reason = ?, updated_at = ?, revision = revision + 1
                      WHERE task_id = ? AND resolution = 'ACTIVE'
                      """,
                      (task_id, reason, now, child_id),
                  )
                  self._record_task_event(
                      conn,
                      child_id,
                      "resolution_transition",
                      {"to_resolution": "CASCADE_PRUNED", "pruned_by_task_id": task_id, "reason": reason},
                  )
              conn.commit()
          with closing(self._control()) as conn:
              for affected_id in [task_id, *descendants]:
                  conn.execute("DELETE FROM leases WHERE task_id = ?", (affected_id,))
              conn.commit()
          return descendants
  
      def _descendants(self, task_id: str) -> list[str]:
          with closing(self._queue()) as conn:
              rows = conn.execute(
                  """
                  WITH RECURSIVE descendants(parent_task_id, child_task_id) AS (
                      SELECT parent_task_id, child_task_id FROM task_edges WHERE parent_task_id = ?
                      UNION ALL
                      SELECT e.parent_task_id, e.child_task_id
                      FROM task_edges e
                      JOIN descendants d ON e.parent_task_id = d.child_task_id
                  )
                  SELECT parent_task_id, child_task_id FROM descendants
                  """,
                  (task_id,),
              ).fetchall()
          edges = [(row["parent_task_id"], row["child_task_id"]) for row in rows]
          return topological_descendants(task_id, edges)
  
      def create_approval(self, approval_id: str, task_id: str, envelope: DiffApprovalEnvelope) -> None:
          task = self.get_task(task_id)
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  INSERT INTO approvals (
                    approval_id, task_id, diff_sha256, diff_hmac_sha256,
                    base_snapshot_sha256, proposed_snapshot_sha256, decision, created_at
                  ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
                  """,
                  (
                      approval_id,
                      task_id,
                      envelope.diff_sha256,
                      envelope.diff_hmac_sha256,
                      envelope.base_snapshot_sha256,
                      envelope.proposed_snapshot_sha256,
                      _now(),
                  ),
              )
              conn.commit()
          self.transition_task_state(task_id, task["state"], "PENDING_APPROVAL", reason="approval_created")
  
      def approve_task(self, task_id: str, decided_by: str) -> None:
          now = _now()
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  UPDATE approvals
                  SET decision = 'APPROVED', decided_by = ?, decided_at = ?
                  WHERE task_id = ? AND decision = 'PENDING'
                  """,
                  (decided_by, now, task_id),
              )
              conn.commit()
          self.transition_task_state(task_id, "PENDING_APPROVAL", "PLANNING", reason="approval_approved")
  
      def reject_approval(self, task_id: str, decided_by: str, reason: str) -> list[str]:
          now = _now()
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  UPDATE approvals
                  SET decision = 'REJECTED', decided_by = ?, decided_at = ?
                  WHERE task_id = ? AND decision = 'PENDING'
                  """,
                  (decided_by, now, task_id),
              )
              conn.commit()
          return self.reject_and_prune(task_id, reason)
  
      def update_scores(self, task_id: str, slr_score: float, depth_penalty: float, final_score: float) -> None:
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  UPDATE tasks
                  SET slr_score = ?, depth_penalty = ?, final_score = ?, updated_at = ?
                  WHERE task_id = ?
                  """,
                  (slr_score, depth_penalty, final_score, _now(), task_id),
              )
              conn.commit()
  
      def add_negative_constraint(self, task_id: str, constraint: str) -> int:
          task = self.get_task(task_id)
          constraints = json.loads(task["negative_constraints_json"])
          constraints.append(constraint)
          reroll_count = int(task["reroll_count"]) + 1
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  UPDATE tasks
                  SET negative_constraints_json = ?, reroll_count = ?, lease_owner = NULL,
                      lease_expires_at = NULL, updated_at = ?, revision = revision + 1
                  WHERE task_id = ?
                  """,
                  (json.dumps(constraints), reroll_count, _now(), task_id),
              )
              conn.commit()
          return reroll_count
  
      def dead_letter(self, task_id: str, reason: str, payload: dict[str, Any]) -> None:
          with closing(self._control()) as conn:
              conn.execute(
                  """
                  INSERT INTO dead_letters(dead_letter_id, task_id, reason, payload_json, created_at)
                  VALUES (?, ?, ?, ?, ?)
                  """,
                  (str(uuid.uuid4()), task_id, reason, json.dumps(payload), _now()),
              )
              conn.commit()
  
      def list_dead_letters(self, limit: int = 100) -> list[dict[str, Any]]:
          with closing(self._control()) as conn:
              rows = conn.execute(
                  "SELECT * FROM dead_letters ORDER BY created_at DESC LIMIT ?",
                  (max(1, min(int(limit), 1000)),),
              ).fetchall()
          return [_dict(row) for row in rows if row is not None]
  
      def start_ingestion_run(self, run_id: str, project_id: str, project_scope_hash: str, target_path: str) -> None:
          now = _now()
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  INSERT OR REPLACE INTO ingestion_runs(
                    run_id, project_id, project_scope_hash, target_path, state, error, started_at, finished_at
                  ) VALUES (?, ?, ?, ?, 'RUNNING', NULL, ?, NULL)
                  """,
                  (run_id, project_id, project_scope_hash, target_path, now),
              )
              conn.commit()
  
      def finish_ingestion_run(self, run_id: str, state: str, error: str | None) -> None:
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  UPDATE ingestion_runs
                  SET state = ?, error = ?, finished_at = ?
                  WHERE run_id = ?
                  """,
                  (state, error, _now(), run_id),
              )
              conn.commit()
  
      def latest_ingestion_run(self, project_id: str) -> dict[str, Any]:
          with closing(self._queue()) as conn:
              row = conn.execute(
                  """
                  SELECT *
                  FROM ingestion_runs
                  WHERE project_id = ?
                  ORDER BY started_at DESC
                  LIMIT 1
                  """,
                  (project_id,),
              ).fetchone()
          result = _dict(row)
          if result is None:
              raise KeyError(project_id)
          return result
  
      def record_file_manifest(self, project_id: str, project_scope_hash: str, metadata: dict[str, Any]) -> None:
          with closing(self._queue()) as conn:
              conn.execute(
                  """
                  INSERT OR REPLACE INTO files(
                    project_id, project_scope_hash, absolute_path, file_sha256, file_name,
                    metadata_hash, size_bytes, mtime_ns, updated_at
                  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                  """,
                  (
                      project_id,
                      project_scope_hash,
                      metadata["absolute_path"],
                      metadata["file_sha256"],
                      metadata["file_name"],
                      metadata["metadata_hash"],
                      int(metadata["size_bytes"]),
                      int(metadata["mtime_ns"]),
                      _now(),
                  ),
              )
              conn.commit()
  
      def file_manifest(self, project_scope_hash: str, absolute_path: str) -> dict[str, Any] | None:
          with closing(self._queue()) as conn:
              row = conn.execute(
                  """
                  SELECT *
                  FROM files
                  WHERE project_scope_hash = ? AND absolute_path = ?
                  """,
                  (project_scope_hash, absolute_path),
              ).fetchone()
          return _dict(row)
  
      def file_paths_for_scope(self, project_scope_hash: str) -> set[str]:
          with closing(self._queue()) as conn:
              rows = conn.execute(
                  "SELECT absolute_path FROM files WHERE project_scope_hash = ?",
                  (project_scope_hash,),
              ).fetchall()
          return {str(row["absolute_path"]) for row in rows}
  
      def delete_file_manifest(self, project_scope_hash: str, absolute_path: str) -> int:
          with closing(self._queue()) as conn:
              conn.execute(
                  "DELETE FROM chunks WHERE project_scope_hash = ? AND absolute_path = ?",
                  (project_scope_hash, absolute_path),
              )
              cursor = conn.execute(
                  "DELETE FROM files WHERE project_scope_hash = ? AND absolute_path = ?",
                  (project_scope_hash, absolute_path),
              )
              conn.commit()
              return cursor.rowcount
  
      def record_chunks(
          self,
          project_id: str,
          project_scope_hash: str,
          run_id: str,
          chunks: list[dict[str, Any]],
      ) -> None:
          now = _now()
          with closing(self._queue()) as conn:
              for chunk in chunks:
                  metadata = dict(chunk.get("metadata") or {})
                  content = str(chunk["content"])
                  conn.execute(
                      """
                      INSERT OR REPLACE INTO chunks(
                        chunk_id, project_id, project_scope_hash, run_id, file_sha256, absolute_path,
                        chunk_index, processor, content_sha1, content, metadata_json, created_at
                      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                      """,
                      (
                          chunk["chunk_id"],
                          project_id,
                          project_scope_hash,
                          run_id,
                          metadata["file_sha256"],
                          metadata["absolute_path"],
                          int(metadata.get("chunk_index", 0)),
                          str(metadata.get("processor", "unknown")),
                          hashlib_sha1(content),
                          content,
                          json.dumps(metadata, sort_keys=True),
                          now,
                      ),
                  )
              conn.commit()
  
      def list_chunks(self, project_id: str) -> list[dict[str, Any]]:
          with closing(self._queue()) as conn:
              rows = conn.execute(
                  "SELECT * FROM chunks WHERE project_id = ? ORDER BY chunk_index ASC, chunk_id ASC",
                  (project_id,),
              ).fetchall()
          return [_dict(row) for row in rows if row is not None]
  
      def delete_chunks_for_path(self, project_scope_hash: str, absolute_path: str) -> int:
          with closing(self._queue()) as conn:
              cursor = conn.execute(
                  "DELETE FROM chunks WHERE project_scope_hash = ? AND absolute_path = ?",
                  (project_scope_hash, absolute_path),
              )
              conn.commit()
              return cursor.rowcount
  
      def chunks_for_rebuild(self, project_id: str) -> list[dict[str, Any]]:
          with closing(self._queue()) as conn:
              rows = conn.execute(
                  """
                  SELECT chunk_id, project_id, project_scope_hash, absolute_path, chunk_index,
                         processor, content, metadata_json
                  FROM chunks
                  WHERE project_id = ?
                  ORDER BY absolute_path ASC, chunk_index ASC
                  """,
                  (project_id,),
              ).fetchall()
          payloads = []
          for row in rows:
              item = _dict(row)
              if item is None:
                  continue
              payloads.append(
                  {
                      "chunk_id": item["chunk_id"],
                      "content": item["content"],
                      "metadata": json.loads(item["metadata_json"]),
                  }
              )
          return payloads
  
      def list_rebuildable_chunks(self, project_id: str) -> list[dict[str, Any]]:
          with closing(self._queue()) as conn:
              rows = conn.execute(
                  """
                  SELECT c.chunk_id, c.project_id, c.project_scope_hash, c.absolute_path, c.chunk_index,
                         c.processor, c.content, c.metadata_json
                  FROM chunks c
                  JOIN ingestion_runs r ON r.run_id = c.run_id
                  WHERE c.project_id = ?
                    AND r.state IN ('FAILED_VECTOR_UPSERT', 'FAILED')
                  ORDER BY c.absolute_path ASC, c.chunk_index ASC
                  """,
                  (project_id,),
              ).fetchall()
          payloads = []
          for row in rows:
              item = _dict(row)
              if item is None:
                  continue
              payloads.append(
                  {
                      "chunk_id": item["chunk_id"],
                      "content": item["content"],
                      "metadata": json.loads(item["metadata_json"]),
                  }
              )
          return payloads
  
      def mark_rebuildable_runs_reconciled(self, project_id: str) -> int:
          with closing(self._queue()) as conn:
              cursor = conn.execute(
                  """
                  UPDATE ingestion_runs
                  SET state = 'RECONCILED',
                      error = NULL,
                      finished_at = ?
                  WHERE project_id = ?
                    AND state IN ('FAILED_VECTOR_UPSERT', 'FAILED')
                  """,
                  (_now(), project_id),
              )
              conn.commit()
              return cursor.rowcount
  
      def count_file_manifests(self) -> int:
          with closing(self._queue()) as conn:
              return int(conn.execute("SELECT COUNT(*) FROM files").fetchone()[0])
  
      def register_worker(self, worker_id: str, command: list[str], pid: int | None = None) -> None:
          now = _now()
          with closing(self._control()) as conn:
              conn.execute(
                  """
                  INSERT OR REPLACE INTO process_registry(
                    pid, worker_id, command_json, started_at, heartbeat_at, status, exited_at, exit_code, orphaned
                  ) VALUES (?, ?, ?, ?, ?, 'RUNNING', NULL, NULL, 0)
                  """,
                  (pid if pid is not None else os.getpid(), worker_id, json.dumps(command), now, now),
              )
              conn.commit()
  
      def heartbeat_worker(self, worker_id: str, pid: int | None = None) -> None:
          with closing(self._control()) as conn:
              conn.execute(
                  """
                  UPDATE process_registry
                  SET heartbeat_at = ?, status = 'RUNNING'
                  WHERE worker_id = ? AND pid = ?
                  """,
                  (_now(), worker_id, pid if pid is not None else os.getpid()),
              )
              conn.execute(
                  "UPDATE leases SET heartbeat_at = ? WHERE worker_id = ?",
                  (_now(), worker_id),
              )
              conn.commit()
  
      def mark_stale_workers(self, stale_before_iso: str) -> int:
          with closing(self._control()) as conn:
              cursor = conn.execute(
                  """
                  UPDATE process_registry
                  SET status = 'STALE'
                  WHERE status = 'RUNNING'
                    AND heartbeat_at IS NOT NULL
                    AND heartbeat_at < ?
                  """,
                  (stale_before_iso,),
              )
              conn.commit()
              return cursor.rowcount
  
      def list_worker_status(self) -> list[dict[str, Any]]:
          with closing(self._control()) as conn:
              rows = conn.execute(
                  "SELECT * FROM process_registry ORDER BY started_at ASC"
              ).fetchall()
          return [_dict(row) for row in rows if row is not None]
  
      def mark_worker_exited(self, pid: int, exit_code: int) -> None:
          with closing(self._control()) as conn:
              conn.execute(
                  """
                  UPDATE process_registry
                  SET status = 'EXITED', exited_at = ?, exit_code = ?
                  WHERE pid = ?
                  """,
                  (_now(), exit_code, pid),
              )
              conn.commit()
  
  
  def hashlib_sha1(text: str) -> str:
      import hashlib
  
      return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

--- FILE: python-daemon/orchestrator/runtime.py ---
Size: 3578 bytes
Summary: Classes: RuntimeComponents; Functions: build_runtime, health, reconcile_project, dead_letters, close
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass
  
  from .adapters import FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters
  from .bridge_server import BridgeSecurity
  from .chroma_manager import ChromaConfig, ChromaManager
  from .config import RuntimeConfig
  from .db_bootstrap import bootstrap_databases
  from .execution_loop import ExecutionLoop
  from .ingest.processors import WorkspaceScout
  from .ingest.service import IngestTargetService
  from .ocr import CommandOCRProvider
  from .queue_repo import QueueRepository
  from .shell import ShellAdapter
  
  
  @dataclass(frozen=True)
  class RuntimeComponents:
      config: RuntimeConfig
      repo: QueueRepository
      chroma: ChromaManager
      ingest: IngestTargetService
      tool_adapters: ToolAdapters
      execution_loop: ExecutionLoop
      bridge_security: BridgeSecurity
  
      def health(self) -> dict[str, object]:
          return {
              "ok": True,
              "queue_db": str(self.config.state_dir / "queue.db"),
              "control_db": str(self.config.state_dir / "control.db"),
              "bridge_host": self.config.bridge_host,
              "bridge_port": self.config.bridge_port,
              "workers": self.repo.list_worker_status(),
              "allowed_roots": [str(root) for root in self.config.allowed_roots],
          }
  
      def reconcile_project(self, project_id: str) -> dict[str, object]:
          return self.ingest.rebuild_chroma_for_project(project_id)
  
      def dead_letters(self, limit: int = 50) -> list[dict[str, object]]:
          return self.repo.list_dead_letters(limit)
  
      def close(self) -> None:
          system = getattr(getattr(self.chroma, "client", None), "_system", None)
          stop = getattr(system, "stop", None)
          if callable(stop):
              stop()
  
  
  def build_runtime(config: RuntimeConfig) -> RuntimeComponents:
      config.state_dir.mkdir(parents=True, exist_ok=True)
      config.chroma_path.mkdir(parents=True, exist_ok=True)
      for root in config.allowed_roots:
          root.mkdir(parents=True, exist_ok=True)
      bootstrap_databases(config.state_dir)
      repo = QueueRepository(config.state_dir / "queue.db", config.state_dir / "control.db")
      chroma = ChromaManager(
          ChromaConfig(
              chroma_path=config.chroma_path,
              lm_studio_base_url=config.lm_studio_base_url,
              lm_studio_api_base_url=config.lm_studio_api_base_url,
              lm_studio_api_token=config.lm_studio_api_token,
              embedding_model=config.embedding_model,
              auto_load_embedding_model=config.auto_load_embedding_model,
          )
      )
      ingest = IngestTargetService(repo, chroma, allowed_roots=config.allowed_roots)
      file_tools = FileToolAdapter(config.allowed_roots)
      sqlite_tools = ReadOnlySqliteAdapter(config.allowed_roots)
      scout = WorkspaceScout(config.allowed_roots)
      shell_adapter = ShellAdapter(config.allowed_roots)
      ocr_provider = CommandOCRProvider(shell_adapter=shell_adapter, command=config.ocr_command) if config.ocr_command else None
      tool_adapters = ToolAdapters(
          semantic_memory=ingest,
          file_tools=file_tools,
          sqlite_tools=sqlite_tools,
          workspace_scout=scout,
          ocr_provider=ocr_provider,
      )
      return RuntimeComponents(
          config=config,
          repo=repo,
          chroma=chroma,
          ingest=ingest,
          tool_adapters=tool_adapters,
          execution_loop=ExecutionLoop(repo, tool_adapters=tool_adapters),
          bridge_security=BridgeSecurity(shared_secret=config.bridge_shared_secret, enable_admin_bridge=config.enable_admin_bridge),
      )

--- FILE: python-daemon/tests/test_processors_and_tools.py ---
Size: 9484 bytes
Summary: Classes: ProcessorAndToolTests, FakeResponseForTools, FakeChromaClientForTools, FakeScout, Collection; Functions: test_text_processor_uses_deterministic_overlap, test_semantic_slicer_emits_stable_function_chunks, test_metadata_adapter_hashes_files, test_workspace_scout_is_deterministic_and_reports_skips, test_file_tools_enforce_allowed_roots_and_verify_integrity, test_shell_adapter_sync_run_uses_subprocess, test_read_only_sqlite_rejects_non_select, test_read_only_sqlite_applies_row_limit, test_js_and_ts_fall_back_to_text_chunking, test_tool_adapters_route_scout_workspace_and_sqlite, test_ocr_disabled_and_enabled_adapter_paths, test_sqlite_adapter_rejects_comments_with_hidden_writes_and_with_statements, __init__, raise_for_status, json, get_or_create_collection, runner, scout, upsert
Content: |
  import sqlite3
  import sys
  import tempfile
  import unittest
  from contextlib import closing
  from pathlib import Path
  
  from orchestrator.adapters import AdapterFailure, FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters
  from orchestrator.chroma_manager import ChromaConfig, ChromaManager
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.ingest.processors import MetadataAdapter, SemanticSlicerAdapter, TextProcessorAdapter, WorkspaceScout
  from orchestrator.ingest.service import IngestTargetService
  from orchestrator.queue_repo import QueueRepository
  from orchestrator.ocr import CommandOCRProvider
  from orchestrator.shell import CommandSpec, ShellAdapter
  
  
  class ProcessorAndToolTests(unittest.TestCase):
      def test_text_processor_uses_deterministic_overlap(self):
          processor = TextProcessorAdapter(chunk_size=5, chunk_overlap=2)
          chunks = processor.process_text("abcdefghij", file_path="a.txt", file_name="a.txt")
  
          self.assertEqual([chunk.content for chunk in chunks], ["abcde", "defgh", "ghij"])
          self.assertEqual(chunks[1].metadata["chunk_index"], 1)
  
      def test_semantic_slicer_emits_stable_function_chunks(self):
          with tempfile.TemporaryDirectory() as tmp:
              path = Path(tmp) / "sample.py"
              path.write_text("import os\n\ndef alpha(x):\n    return x + 1\n", encoding="utf-8")
  
              chunks = SemanticSlicerAdapter().process_file(path)
  
              self.assertEqual(len(chunks), 1)
              self.assertEqual(chunks[0].metadata["processor"], "semantic_slicer")
              self.assertEqual(chunks[0].metadata["symbol_name"], "alpha")
              self.assertIn("sample.py::alpha@", chunks[0].metadata["slice_id"])
  
      def test_metadata_adapter_hashes_files(self):
          with tempfile.TemporaryDirectory() as tmp:
              path = Path(tmp) / "a.txt"
              path.write_text("abc", encoding="utf-8")
  
              metadata = MetadataAdapter().extract(path)
  
              self.assertEqual(metadata["file_name"], "a.txt")
              self.assertEqual(len(metadata["file_sha256"]), 64)
              self.assertEqual(len(metadata["metadata_hash"]), 64)
  
      def test_workspace_scout_is_deterministic_and_reports_skips(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              (root / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
              (root / "image.png").write_bytes(b"\x00")
              (root / "cache.db").write_bytes(b"sqlite bytes")
              (root / "paper.pdf").write_bytes(b"%PDF")
              (root / "model.h5").write_bytes(b"heavy")
              bundle_dir = root / "New project_bundle_123"
              bundle_dir.mkdir()
              (bundle_dir / "generated_bundle.py").write_text("print('skip')\n", encoding="utf-8")
  
              first = WorkspaceScout(allowed_roots=(root,)).scout("project-a", str(root), include_summaries=True)
              second = WorkspaceScout(allowed_roots=(root,)).scout("project-a", str(root), include_summaries=True)
  
              self.assertEqual(first["package_hash"], second["package_hash"])
              self.assertEqual(first["file_count"], 1)
              self.assertGreaterEqual(first["skipped_count"], 4)
              self.assertGreaterEqual(first["skipped_details"]["ignored_extension"], 4)
  
      def test_file_tools_enforce_allowed_roots_and_verify_integrity(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              path = root / "a.txt"
              path.write_text("abc", encoding="utf-8")
              tools = FileToolAdapter((root,))
              expected = MetadataAdapter().extract(path)
  
              self.assertEqual(tools.read_file_snippet(str(path), 1, 1), "abc")
              result = tools.verify_integrity(str(path), expected["file_sha256"], expected["metadata_hash"])
              self.assertTrue(result["ok"])
  
              with self.assertRaises(AdapterFailure):
                  tools.read_file(str(Path(tmp).parent / "outside.txt"))
  
      def test_shell_adapter_sync_run_uses_subprocess(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              shell = ShellAdapter((root,))
              spec = CommandSpec(
                  executable=sys.executable,
                  args=("-c", "print('ok')"),
                  cwd=str(root),
              )
              rc, stdout, stderr = shell.sync_run(spec)
  
              self.assertEqual(rc, 0)
              self.assertIn("ok", stdout)
              self.assertEqual(stderr, "")
  
      def test_read_only_sqlite_rejects_non_select(self):
          with tempfile.TemporaryDirectory() as tmp:
              db = Path(tmp) / "data.db"
              with closing(sqlite3.connect(db)) as conn:
                  conn.execute("CREATE TABLE items(id INTEGER)")
                  conn.execute("INSERT INTO items(id) VALUES (1)")
                  conn.commit()
  
              adapter = ReadOnlySqliteAdapter((Path(tmp),))
  
              self.assertEqual(adapter.query(str(db), "SELECT id FROM items", row_limit=1)[0]["id"], 1)
              with self.assertRaises(AdapterFailure):
                  adapter.query(str(db), "DELETE FROM items")
              with self.assertRaises(AdapterFailure):
                  adapter.query(str(db), "SELECT id FROM items; SELECT id FROM items")
  
      def test_read_only_sqlite_applies_row_limit(self):
          with tempfile.TemporaryDirectory() as tmp:
              db = Path(tmp) / "data.db"
              with closing(sqlite3.connect(db)) as conn:
                  conn.execute("CREATE TABLE items(id INTEGER)")
                  conn.executemany("INSERT INTO items(id) VALUES (?)", [(1,), (2,), (3,)])
                  conn.commit()
  
              rows = ReadOnlySqliteAdapter((Path(tmp),)).query(str(db), "SELECT id FROM items ORDER BY id", row_limit=2)
  
              self.assertEqual([row["id"] for row in rows], [1, 2])
  
      def test_js_and_ts_fall_back_to_text_chunking(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              source = root / "app.ts"
              source.write_text("export const value = 1;\n", encoding="utf-8")
              manager = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponseForTools({"data": [{"embedding": [0.1]}]}),
                  chroma_client=FakeChromaClientForTools(),
              )
              repo = QueueRepository(root / "queue.db", root / "control.db")
              service = IngestTargetService(repo, manager, allowed_roots=(root,))
  
              service.ingest_target("project-a", str(source))
  
              self.assertEqual(repo.list_chunks("project-a")[0]["processor"], "text")
  
      def test_tool_adapters_route_scout_workspace_and_sqlite(self):
          class FakeScout:
              def scout(self, project_id, absolute_path, max_files=500, include_summaries=True):
                  return {"project_id": project_id, "absolute_path": absolute_path, "max_files": max_files}
  
          adapters = ToolAdapters(workspace_scout=FakeScout())
  
          result = adapters.call_mcp_tool(
              "mcp_scout_workspace",
              {"project_id": "p", "absolute_path": "x", "max_files": 2},
          )
  
          self.assertTrue(result["ok"])
          self.assertEqual(result["result"]["max_files"], 2)
  
      def test_ocr_disabled_and_enabled_adapter_paths(self):
          with self.assertRaises(AdapterFailure):
              ToolAdapters().call_mcp_tool("mcp_extract_image", {"absolute_path": "x"})
  
          calls = []
  
          def runner(command, args, timeout):
              calls.append((command, args, timeout))
              return "detected text"
  
          with tempfile.TemporaryDirectory() as tmp:
              shell = ShellAdapter((Path(tmp),))
              provider = CommandOCRProvider(shell_adapter=shell, command="ocr-bin", runner=runner)
              result = ToolAdapters(ocr_provider=provider).call_mcp_tool(
                  "mcp_extract_image",
                  {"absolute_path": "image.png", "page": 2, "region": {"x": 1}},
              )
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["text"], "detected text")
              self.assertEqual(calls[0][0], "ocr-bin")
  
      def test_sqlite_adapter_rejects_comments_with_hidden_writes_and_with_statements(self):
          with tempfile.TemporaryDirectory() as tmp:
              db = Path(tmp) / "data.db"
              with closing(sqlite3.connect(db)) as conn:
                  conn.execute("CREATE TABLE items(id INTEGER)")
                  conn.execute("INSERT INTO items(id) VALUES (1)")
                  conn.commit()
  
              adapter = ReadOnlySqliteAdapter((Path(tmp),))
  
              with self.assertRaises(AdapterFailure):
                  adapter.query(str(db), "-- comment\nSELECT id FROM items")
              with self.assertRaises(AdapterFailure):
                  adapter.query(str(db), "WITH rows AS (SELECT id FROM items) SELECT id FROM rows")
  
  
  if __name__ == "__main__":
      unittest.main()
  
  
  class FakeResponseForTools:
      def __init__(self, payload, status_code=200):
          self.payload = payload
          self.status_code = status_code
  
      def raise_for_status(self):
          return None
  
      def json(self):
          return self.payload
  
  class FakeChromaClientForTools:
      def get_or_create_collection(self, name):
          class Collection:
              def upsert(self, **kwargs):
                  return None
  
          return Collection()

--- FILE: python-daemon/tests/test_runtime_daemon.py ---
Size: 15888 bytes
Summary: Classes: FakeToolAdapters, RuntimeDaemonTests, FakeResponseForLMStudio, LMStudioManagerTests, Internal, Internal; Functions: __init__, call_mcp_tool, test_runtime_config_loads_paths_and_bridge_from_env, test_runtime_config_project_id_override, test_build_runtime_bootstraps_components_and_databases, test_worker_executes_payload_tool_and_completes_task, test_worker_registers_and_heartbeats_process_registry, test_worker_dead_letters_invalid_task_payload, test_lease_recovery_releases_expired_leases, test_migrations_record_initial_version_and_reject_unknown_future_version, test_invalid_task_transition_is_rejected_and_valid_transition_is_audited, test_bridge_rejects_oversized_or_unauthorized_requests, test_bridge_accepts_hmac_auth_and_rejects_unknown_methods, test_bridge_includes_nonce_in_auth_and_prevents_replay, test_bridge_admin_gating_blocks_daemon_methods_when_disabled, test_bridge_admin_gating_allows_daemon_methods_when_enabled, test_bridge_admin_gating_blocks_daemon_methods_when_shared_secret_none, test_nonce_cache_bounds_entries, test_internal_health_and_dead_letter_methods_are_available, test_operator_readme_exists, test_runtime_config_defaults_embedding_model_to_correct_lm_studio_key, __init__, raise_for_status, json, test_list_models_accepts_models_and_data_keys, test_ensure_embedding_model_loaded_rejects_non_embedding_model, test_ensure_embedding_model_loaded_loads_unloaded_model, test_401_from_list_models_gives_clear_token_error, get, get, get, post, get, health, health, dead_letters
Content: |
  import json
  import sqlite3
  import tempfile
  import unittest
  from collections import deque
  from contextlib import closing
  from pathlib import Path
  
  from orchestrator.adapters import ToolAdapters
  from orchestrator.bridge_server import BridgeSecurity, build_auth_envelope, handle_json_rpc, line_too_large
  from orchestrator.config import RuntimeConfig
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.queue_repo import QueueRepository
  from orchestrator.runtime import build_runtime
  from orchestrator.worker import DaemonWorker
  
  
  class FakeToolAdapters(ToolAdapters):
      def __init__(self):
          super().__init__()
          self.calls = []
  
      def call_mcp_tool(self, tool_name, args):
          self.calls.append((tool_name, args))
          return {"ok": True, "tool_name": tool_name, "args": args}
  
  
  class RuntimeDaemonTests(unittest.TestCase):
      def test_runtime_config_loads_paths_and_bridge_from_env(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              config = RuntimeConfig.from_env(
                  {
                      "ALETHEIA_PROJECT_ROOT": str(root),
                      "ALETHEIA_STATE_DIR": str(root / "state"),
                      "ALETHEIA_ALLOWED_ROOTS": f"{root};{root / 'other'}",
                      "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                      "ALETHEIA_LM_STUDIO_BASE_URL": "http://lm/v1",
                      "ALETHEIA_EMBEDDING_MODEL": "model",
                      "ALETHEIA_BRIDGE_HOST": "127.0.0.1",
                      "ALETHEIA_BRIDGE_PORT": "4567",
                      "ALETHEIA_APPROVAL_SECRET": "secret",
                  }
              )
  
              self.assertEqual(config.project_root, root.resolve())
              self.assertEqual(config.project_id, root.name)
              self.assertEqual(config.enable_admin_bridge, False)
              self.assertEqual(config.bridge_host, "127.0.0.1")
              self.assertEqual(config.bridge_port, 4567)
  
      def test_runtime_config_project_id_override(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              config = RuntimeConfig.from_env(
                  {
                      "ALETHEIA_PROJECT_ROOT": str(root),
                      "ALETHEIA_PROJECT_ID": "custom-id",
                      "ALETHEIA_ENABLE_ADMIN_BRIDGE": "true",
                  }
              )
              self.assertEqual(config.project_id, "custom-id")
              self.assertEqual(config.enable_admin_bridge, True)
  
      def test_build_runtime_bootstraps_components_and_databases(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              config = RuntimeConfig.from_env(
                  {
                      "ALETHEIA_PROJECT_ROOT": str(root),
                      "ALETHEIA_STATE_DIR": str(root / "state"),
                      "ALETHEIA_ALLOWED_ROOTS": str(root),
                      "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                  }
              )
  
              runtime = build_runtime(config)
  
              try:
                  self.assertTrue((root / "state" / "queue.db").exists())
                  self.assertIsNotNone(runtime.tool_adapters.semantic_memory)
                  self.assertIsNotNone(runtime.tool_adapters.workspace_scout)
                  self.assertIs(runtime.execution_loop.repo, runtime.repo)
              finally:
                  runtime.close()
  
      def test_worker_executes_payload_tool_and_completes_task(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = QueueRepository(root / "queue.db", root / "control.db")
              adapters = FakeToolAdapters()
              payload = {"tool": "mcp_scout_workspace", "args": {"project_id": "p", "absolute_path": str(root)}}
              repo.create_task("task", "p", "Task", payload, depth=0)
              worker = DaemonWorker(repo, adapters, project_id="p", worker_id="w")
  
              result = worker.run_once()
  
              self.assertEqual(result["task_id"], "task")
              self.assertEqual(repo.get_task("task")["state"], "COMPLETED")
              self.assertEqual(adapters.calls, [("mcp_scout_workspace", payload["args"])])
  
      def test_worker_registers_and_heartbeats_process_registry(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = QueueRepository(root / "queue.db", root / "control.db")
              worker = DaemonWorker(repo, FakeToolAdapters(), project_id="p", worker_id="w")
  
              worker.register_process(["aletheia-daemon"])
              worker.heartbeat()
  
              rows = repo.list_worker_status()
              self.assertEqual(rows[0]["worker_id"], "w")
              self.assertEqual(rows[0]["status"], "RUNNING")
              self.assertIsNotNone(rows[0]["heartbeat_at"])
  
      def test_worker_dead_letters_invalid_task_payload(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = QueueRepository(root / "queue.db", root / "control.db")
              repo.create_task("task", "p", "Task", {"args": {}}, depth=0)
              worker = DaemonWorker(repo, FakeToolAdapters(), project_id="p", worker_id="w")
  
              result = worker.run_once()
  
              self.assertEqual(result["error"], "invalid_task_payload")
              self.assertEqual(len(repo.list_dead_letters()), 1)
  
      def test_lease_recovery_releases_expired_leases(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = QueueRepository(root / "queue.db", root / "control.db")
              repo.create_task("task", "p", "Task", {"tool": "x", "args": {}}, depth=0)
              repo.claim_ready_task("p", "w", "2000-01-01T00:00:00+00:00")
  
              released = repo.release_expired_leases("2026-01-01T00:00:00+00:00")
  
              self.assertEqual(released, 1)
              self.assertIsNone(repo.get_task("task")["lease_owner"])
  
      def test_migrations_record_initial_version_and_reject_unknown_future_version(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              with closing(sqlite3.connect(root / "queue.db")) as conn:
                  rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
                  self.assertEqual([row[0] for row in rows], ["0001_initial"])
                  conn.execute(
                      "INSERT INTO schema_migrations(version, applied_at) VALUES ('9999_future', 'now')"
                  )
                  conn.commit()
  
              with self.assertRaises(RuntimeError):
                  bootstrap_databases(root)
  
      def test_invalid_task_transition_is_rejected_and_valid_transition_is_audited(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = QueueRepository(root / "queue.db", root / "control.db")
              repo.create_task("task", "p", "Task", {"tool": "x", "args": {}}, depth=0)
  
              with self.assertRaises(ValueError):
                  repo.transition_task_state("task", "COMPLETED", "PLANNING", reason="bad")
  
              repo.transition_task_state("task", "PLANNING", "PENDING_APPROVAL", reason="needs_human")
  
              events = repo.list_task_events("task")
              self.assertEqual(events[-1]["event_type"], "state_transition")
              self.assertEqual(json.loads(events[-1]["details_json"])["to_state"], "PENDING_APPROVAL")
  
      def test_bridge_rejects_oversized_or_unauthorized_requests(self):
          security = BridgeSecurity(shared_secret="secret", max_line_bytes=10)
          self.assertTrue(line_too_large(b"01234567890", security))
  
          response = handle_json_rpc(
              {
                  "jsonrpc": "2.0",
                  "id": 1,
                  "method": "tools.call",
                  "params": {"toolName": "x", "args": {}, "auth": {"timestamp": "0", "signature": "wrong"}},
              },
              FakeToolAdapters(),
              security,
          )
  
          self.assertEqual(response["error"]["code"], -32001)
  
      def test_bridge_accepts_hmac_auth_and_rejects_unknown_methods(self):
          security = BridgeSecurity(shared_secret="secret")
          message = {"jsonrpc": "2.0", "id": 1, "method": "tools.call", "params": {"toolName": "x", "args": {}}}
          message["params"]["auth"] = build_auth_envelope(message, "secret")
  
          response = handle_json_rpc(message, FakeToolAdapters(), security)
          missing = handle_json_rpc({"jsonrpc": "2.0", "id": 2, "method": "daemon.delete"}, FakeToolAdapters(), security)
  
          self.assertEqual(response["result"]["tool_name"], "x")
          self.assertEqual(missing["error"]["code"], -32601)
  
      def test_bridge_includes_nonce_in_auth_and_prevents_replay(self):
          security = BridgeSecurity(shared_secret="secret", nonce_cache=set())
          message = {"jsonrpc": "2.0", "id": 1, "method": "tools.call", "params": {"toolName": "x", "args": {}}}
          message["params"]["auth"] = build_auth_envelope(message, "secret")
  
          response1 = handle_json_rpc(message, FakeToolAdapters(), security)
          self.assertEqual(response1["result"]["tool_name"], "x")
  
          response2 = handle_json_rpc(message, FakeToolAdapters(), security)
          self.assertEqual(response2["error"]["code"], -32001)
  
      def test_bridge_admin_gating_blocks_daemon_methods_when_disabled(self):
          security = BridgeSecurity(shared_secret="secret", enable_admin_bridge=False)
          message = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
          message["params"]["auth"] = build_auth_envelope(message, "secret")
  
          response = handle_json_rpc(message, FakeToolAdapters(), security)
  
          self.assertEqual(response["error"]["code"], -32002)
  
      def test_bridge_admin_gating_allows_daemon_methods_when_enabled(self):
          class Internal:
              def health(self):
                  return {"ok": True}
  
          security = BridgeSecurity(shared_secret="secret", enable_admin_bridge=True)
          message = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
          message["params"]["auth"] = build_auth_envelope(message, "secret")
  
          response = handle_json_rpc(message, FakeToolAdapters(), security, internal_api=Internal())
  
          self.assertEqual(response["result"]["ok"], True)
  
      def test_bridge_admin_gating_blocks_daemon_methods_when_shared_secret_none(self):
          security = BridgeSecurity(shared_secret=None, enable_admin_bridge=True)
          message = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
  
          response = handle_json_rpc(message, FakeToolAdapters(), security)
  
          self.assertEqual(response["error"]["code"], -32002)
  
      def test_nonce_cache_bounds_entries(self):
          security = BridgeSecurity(shared_secret="secret")
          # Simulate adding 4097 nonces
          for i in range(4097):
              nonce = f"nonce-{i}"
              message = {"jsonrpc": "2.0", "id": 1, "method": "tools.call", "params": {"toolName": "x", "args": {}}}
              message["params"]["auth"] = build_auth_envelope(message, "secret", nonce=nonce)
              handle_json_rpc(message, FakeToolAdapters(), security)
          
          self.assertLessEqual(len(security.nonce_cache), 4096)
          self.assertIn("nonce-4096", security.nonce_cache)  # Last one added
  
      def test_internal_health_and_dead_letter_methods_are_available(self):
          class Internal:
              def health(self):
                  return {"ok": True}
  
              def dead_letters(self, limit=50):
                  return [{"task_id": "t"}][:limit]
  
          security = BridgeSecurity(shared_secret="secret", enable_admin_bridge=True)
          health_msg = {"jsonrpc": "2.0", "id": 1, "method": "daemon.health", "params": {}}
          health_msg["params"]["auth"] = build_auth_envelope(health_msg, "secret")
          dead_msg = {"jsonrpc": "2.0", "id": 2, "method": "daemon.dead_letters", "params": {"limit": 1}}
          dead_msg["params"]["auth"] = build_auth_envelope(dead_msg, "secret")
  
          health = handle_json_rpc(health_msg, FakeToolAdapters(), security, internal_api=Internal())
          dead = handle_json_rpc(dead_msg, FakeToolAdapters(), security, internal_api=Internal())
  
          self.assertEqual(health["result"], {"ok": True})
          self.assertEqual(dead["result"][0]["task_id"], "t")
  
      def test_operator_readme_exists(self):
          self.assertTrue((Path.cwd().parent / "README.md").exists())
  
      def test_runtime_config_defaults_embedding_model_to_correct_lm_studio_key(self):
          config = RuntimeConfig.from_env({})
          self.assertEqual(config.embedding_model, "text-embedding-nomic-embed-text-v1.5")
  
  
  class FakeResponseForLMStudio:
      def __init__(self, payload):
          self.payload = payload
          self.status_code = 200
  
      def raise_for_status(self):
          pass
  
      def json(self):
          return self.payload
  
  
  class LMStudioManagerTests(unittest.TestCase):
      def test_list_models_accepts_models_and_data_keys(self):
          calls = []
          def get(url, headers=None, timeout=None):
              calls.append((url, headers))
              return FakeResponseForLMStudio({"models": [{"key": "model1", "type": "embedding", "state": "loaded"}]})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get)
  
          models = manager.list_models()
  
          self.assertEqual(len(models), 1)
          self.assertEqual(models[0].key, "model1")
          self.assertEqual(models[0].type, "embedding")
  
      def test_ensure_embedding_model_loaded_rejects_non_embedding_model(self):
          def get(url, **kwargs):
              return FakeResponseForLMStudio({"models": [{"key": "chat-model", "type": "chat"}]})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig, LMStudioManagerError
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get)
  
          with self.assertRaises(LMStudioManagerError) as cm:
              manager.ensure_embedding_model_loaded("chat-model")
  
          self.assertIn("not an embedding model", str(cm.exception))
  
      def test_ensure_embedding_model_loaded_loads_unloaded_model(self):
          get_calls = []
          post_calls = []
          def get(url, **kwargs):
              get_calls.append(url)
              return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "state": "unloaded"}]})
  
          def post(url, json=None, **kwargs):
              post_calls.append((url, json))
              return FakeResponseForLMStudio({})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)
  
          manager.ensure_embedding_model_loaded("embed-model")
  
          self.assertEqual(len(post_calls), 1)
          self.assertEqual(post_calls[0][0], "http= [REDACTED_HIGH_ENTROPY]
          self.assertEqual(post_calls[0][1], {"model": "embed-model"})
  
      def test_401_from_list_models_gives_clear_token_error(self):
          import requests
          def get(url, **kwargs):
              raise requests.HTTPError(response=type('Response', (), {'status_code': 401})())
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig, LMStudioManagerError
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get)
  
          with self.assertRaises(LMStudioManagerError) as cm:
              manager.list_models()
  
          self.assertIn("set ALETHEIA_LM_STUDIO_API_TOKEN", str(cm.exception))= [REDACTED_HIGH_ENTROPY]
  
  
  if __name__ == "__main__":
      unittest.main()
