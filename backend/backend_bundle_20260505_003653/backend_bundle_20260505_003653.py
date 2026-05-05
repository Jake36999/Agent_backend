import yaml
# Workspace Bundle: backend
# Generated: 2026-05-05T00:36:53
# Compliance: os.scandir traversal; binary guard; PEM + entropy redaction; polyglot summaries

# Project Structure:
# backend/
#   |-- agent_backend_skill_registry/
#     |-- CHECKSUMS.json
#     |-- manifest.schema.json
#     |-- PACK_MANIFEST.json
#     |-- README.md
#     |-- SKILL_INDEX.json
#     |-- skills/
#       |-- architecture_review_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- bug_triage_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- candidate_analysis_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- conversation_summary_ingest_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- git_guardrails_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- patch_apply_and_test_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- patch_generate_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- refactor_plan_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- skill_crystallize_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#       |-- tdd_patch_plan_v1/
#         |-- example_input.json
#         |-- example_output.json
#         |-- skill.json
#         |-- SKILL.md
#     |-- TRUST_TIERS.md
#     |-- VALIDATION_REPORT.md
#   |-- Aletheia_BACKEND_README.md
#   |-- lmstudio_fastmcp_shim.py
#   |-- node-mcp/
#     |-- package.json
#     |-- src/
#       |-- bridge.mjs
#       |-- contracts.mjs
#       |-- server.mjs
#     |-- test/
#       |-- active-memory-contracts.test.mjs
#       |-- bridge-integration.test.mjs
#       |-- bridge.test.mjs
#       |-- contracts.test.mjs
#       |-- investigation-contracts.test.mjs
#       |-- run-tests.mjs
#       |-- scout-contract.test.mjs
#       |-- tool-manifest.test.mjs
#   |-- python-daemon/
#     |-- Invoke-AletheiaTool.ps1
#     |-- orchestrator/
#       |-- __init__.py
#       |-- active_partition/
#         |-- __init__.py
#         |-- mapper.py
#         |-- models.py
#         |-- repo.py
#         |-- service.py
#       |-- adapters.py
#       |-- admin.py
#       |-- agent_workflow/
#         |-- __init__.py
#         |-- bridge_client.py
#         |-- compaction.py
#         |-- mcp_tool.py
#         |-- policies.py
#         |-- runner.py
#         |-- state.py
#       |-- agent_workflow_cli.py
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
#       |-- memory/
#         |-- __init__.py
#         |-- models.py
#         |-- repo.py
#         |-- service.py
#       |-- observability.py
#       |-- ocr.py
#       |-- queue_repo.py
#       |-- recovery.py
#       |-- reroll.py
#       |-- runtime.py
#       |-- shell.py
#       |-- skills/
#         |-- __init__.py
#         |-- executor.py
#         |-- importer.py
#         |-- registry.py
#         |-- schema.py
#         |-- selection.py
#       |-- tool_assist_adapter.py
#       |-- worker.py
#     |-- pyproject.toml
#     |-- tests/
#       |-- test_active_memory_tools.py
#       |-- test_active_partition_mapper.py
#       |-- test_active_partition_repo.py
#       |-- test_agent_workflow.py
#       |-- test_approval.py
#       |-- test_bridge_server.py
#       |-- test_chroma_and_ingest.py
#       |-- test_dag_runtime.py
#       |-- test_db_and_dag.py
#       |-- test_epistemic_and_reroll.py
#       |-- test_execution_loop_adapters.py
#       |-- test_fastmcp_shim_tools.py
#       |-- test_hitl_and_shell.py
#       |-- test_memory_service.py
#       |-- test_processors_and_tools.py
#       |-- test_runtime_daemon.py
#       |-- test_skill_selection.py
#       |-- test_tool_assist_adapter.py
#   |-- README.md
#   |-- tool_manifest.json
#   |-- tool_manifest.schema.json

--- FILE: Aletheia_BACKEND_README.md ---
Size: 10755 bytes
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
Size: 6883 bytes
Summary: Headers: Aletheia Backend Runtime, Python Daemon, Node MCP Gateway, LM Studio embedding model readiness, Tool Manifest Scaffold, Admin CLI, Operations, Smoke Test, Tests, Production Constraints
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
  
  $env:TOOLSET_ROOT="C:\path\to\toolset-repo"
  $env:LTA_OUTPUT_ROOT="C:\path\to\project\.aletheia_state\tool_assist"  # optional
  python -m orchestrator.main
  ```
  
  The installed script entrypoint is also available as `aletheia-daemon`.
  Set the environment variables before starting the Python daemon. If you change PowerShell env vars after the daemon is already running, that existing process will keep using the values it started with.
  
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
  The investigation tools (`mcp_investigation_*`) are also exposed through `backend/lmstudio_fastmcp_shim.py` for this LM Studio topology.
  For normal LM Studio usage, prefer exposing only `mcp_agent_workflow_run` via `allowed_tools` so the model sees a smaller tool surface:
  
  ```json
  {
    "type": "plugin",
    "id": "mcp/aletheia-fastmcp-shim",
    "allowed_tools": ["mcp_agent_workflow_run"]
  }
  ```
  
  The lower-level `mcp_investigation_*`, active partition, and memory tools still exist for manual or debug use, but they are intentionally not the default LM Studio surface.
  
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
  The readiness check reads `ALETHEIA_LM_STUDIO_API_TOKEN` and the embedding model settings at daemon startup time, so update the environment before launching the daemon if those values change.= [REDACTED_HIGH_ENTROPY]
  
  ## Tool Manifest Scaffold
  
  The repo includes a minimal, auditable tool manifest scaffold in:
  
  - `backend/tool_manifest.json`
  - `backend/tool_manifest.schema.json`
  
  This manifest describes existing tool surfaces, dispatch routing, risk level, and LM Studio exposure policy. It is validation and documentation scaffolding only. It does not replace the Node contracts, FastMCP shim, or Python daemon adapters.
  
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
  
  ## Production Constraints
  
  No UI, watchers, legacy FastMCP runtime, ChatML routing, or non-HITL mutating file tools are part of this runtime.
  
  `ReadOnlySqliteAdapter` remains internal. Do not publish a SQLite MCP tool without a separate security review and strict public contract.

--- FILE: agent_backend_skill_registry/CHECKSUMS.json ---
Size: 5157 bytes
Summary: Keys: PACK_MANIFEST.json, README.md, SKILL_INDEX.json, TRUST_TIERS.md, VALIDATION_REPORT.md, manifest.schema.json, skills/architecture_review_v1/SKILL.md, skills/architecture_review_v1/example_input.json, skills/architecture_review_v1/example_output.json, skills/architecture_review_v1/skill.json
Content: |
  {
    "PACK_MANIFEST.json": "29e881a08a00edc8f766e7a2f7fbe87b11ab9ea4f397157558f0fed5c3563049",
    "README.md": "4bd3f4cfa04a0c9add79de46d7304e1de9e9005a8e8a9f66330a0da8cc7b950a",
    "SKILL_INDEX.json": "fe80e9409090f65dc47f117e90cbd20b5ffce8fc58e9d7b2700336542b4bfc30",
    "TRUST_TIERS.md": "5303a6065fe51cd586b1da5de8eb5c2e1f5a34e9fa3801b2e2da905528b4e8d1",
    "VALIDATION_REPORT.md": "9e3d0984b5ca31c51eeafd1d66241c7c984c15bea897bdb7a8cf84639b598a5f",
    "manifest.schema.json": "2e3b5644b7798be4c1fff666a200ab7d88a95a0e1da8735d44e148c47515092c",
    "skills/architecture_review_v1/SKILL.md": "32459e9c59295657beb8bff52f78010005155c5d790bdfe74e7a544d8b7e23c2",
    "skills/architecture_review_v1/example_input.json": "b1de818e0ca46ad43b635592b0fddf874056f975041f32dae8003df42f33729e",
    "skills/architecture_review_v1/example_output.json": "1357287393f0306c9f95f882de1e4e04efc2af07918f87d68a57aacbe9e5a72f",
    "skills/architecture_review_v1/skill.json": "b1df6ba0a2598b2c83ad23b7303a872e115baafa0a6b78db8af592d981bb850c",
    "skills/bug_triage_v1/SKILL.md": "24721e4562085128e75a3ff93c2b513e435d469ebc108dbca0cb6e91319a9c3f",
    "skills/bug_triage_v1/example_input.json": "a1e4e137ba76fd3f725b0879605d159207be358056bc43e9df1b63e6d4f33adb",
    "skills/bug_triage_v1/example_output.json": "ba9117e36c031b16c4147106d737099d1a10b5e0341ce3af67cac7d67f0bb4af",
    "skills/bug_triage_v1/skill.json": "e46f64cc8025ecc2258830593167a54dfb67040db48344331f2a77de87535ce3",
    "skills/candidate_analysis_v1/SKILL.md": "ae93854347d1d4ed9856a9a6d925d08f98d629d23ab1ee038a10d7b2309be4eb",
    "skills/candidate_analysis_v1/example_input.json": "2962c8530908c1504f9e69b7b053ec7cb1a03d8ccd63b3eb5c96d9c0dd7646b5",
    "skills/candidate_analysis_v1/example_output.json": "d5aa583362be2258b16b8ffd7a0c89d3742cd40f480ac0726c22411eeccaa6fb",
    "skills/candidate_analysis_v1/skill.json": "47f8732a2929f12f3618e2b9af3428b0531b43a99b19bed479b3d7b34c3047c0",
    "skills/conversation_summary_ingest_v1/SKILL.md": "7094aa9a8fe6a79e90ff27a5ddf72c28af3d4a59e70552582ad55c12b3bffc89",
    "skills/conversation_summary_ingest_v1/example_input.json": "613acd29df79b65c36a99cb778abc0621330ebdf3cd8381d448dd31a4c53281b",
    "skills/conversation_summary_ingest_v1/example_output.json": "7ea903e8993e23baa975ecb3aa2ff355cf3b112fb32507751859b47f900ec41e",
    "skills/conversation_summary_ingest_v1/skill.json": "45a553cccfa6bae827919ba373d8e45259411e2c9a0fbadf8f6568e0c817f8cb",
    "skills/git_guardrails_v1/SKILL.md": "f2094ec7059e7ac7efdb59e2228608386b835861183108ff7c20525810d7524a",
    "skills/git_guardrails_v1/example_input.json": "5d0020f433312305d312f2f573a6d52483e13b805884d3ed7c435300662a233f",
    "skills/git_guardrails_v1/example_output.json": "55703a499d4bfa25d7b60408040f8e3275368e93b3c6f6149afdb2e978c3ed6d",
    "skills/git_guardrails_v1/skill.json": "a546715b4885f16ac0a4f35e9559ba0b8acc385e6ec3d1ca09d03dd5e915221b",
    "skills/patch_apply_and_test_v1/SKILL.md": "370eba9b755df22a720d48422ec71a513560cab341346108a558507205539e4e",
    "skills/patch_apply_and_test_v1/example_input.json": "68480b0a97adf2565f61bc7d61c230a3094c158586437f29b1fc471adb0651db",
    "skills/patch_apply_and_test_v1/example_output.json": "34f588cbeb7424ce5ae3a8a51439dcaf8504c5e7f64c7d786505df92341e5834",
    "skills/patch_apply_and_test_v1/skill.json": "3c5b2570d5efb0ddaf9f3ed4941cec73f1280e09b5b2484088bb44eb0cacb719",
    "skills/patch_generate_v1/SKILL.md": "d8fba82cdcfeb12c684d8e979a3e292d3a62b4d770f1d3b0152af0abe498d07e",
    "skills/patch_generate_v1/example_input.json": "eb488643246b985f9108070470a3ddbc0410c02ba0274be1cf6582cf4402349e",
    "skills/patch_generate_v1/example_output.json": "9bb4b40d34df0979007838bb0c076fb0035515f330c3d5c928ee1b2bb26bda62",
    "skills/patch_generate_v1/skill.json": "dce7998e57244db7f2f3951af6d39c10992ebeb271ffd3d5ea285f9631b894ad",
    "skills/refactor_plan_v1/SKILL.md": "6fa22345f507140552e5d3509d9eaa2fc3897666915302e6e9702520248ed57f",
    "skills/refactor_plan_v1/example_input.json": "13ddb52ae12481292cbd71bec10b1cd76211deb7575eb35a73e3d559802b0248",
    "skills/refactor_plan_v1/example_output.json": "cb03a39dfdb415697b37315332e6667387c059cb03f494c54ad4b36abac7b7f8",
    "skills/refactor_plan_v1/skill.json": "ffb6d5973571acae94a1c04700691b2d80a65b18fec1ba7d1910baebc473d28f",
    "skills/skill_crystallize_v1/SKILL.md": "13e4ab0451f573a21d09c472d09948fa1fd1b2d42193eef12c6977c9fae1f0bb",
    "skills/skill_crystallize_v1/example_input.json": "a687c4b268799b149dd7140f20d61608f1318e400f69fa5fa9837fdd4e8e437c",
    "skills/skill_crystallize_v1/example_output.json": "1aa8246550e9f690d4cdd7c87e4464cab4f645ef7678bb4ff21ffe51cbd69c19",
    "skills/skill_crystallize_v1/skill.json": "5de32517719ac9bee81bf466a3bd610f11ad8970342e1a5c6d1c57444a28180a",
    "skills/tdd_patch_plan_v1/SKILL.md": "1e2bc269fd963bf4bd5c09d09bafaef5b47b3e376f68773cf152295fad1270ea",
    "skills/tdd_patch_plan_v1/example_input.json": "dc4e3b65e0c387665fc9a11e6cd68eeb458ff645f69fd1faf077a015b3fbdb02",
    "skills/tdd_patch_plan_v1/example_output.json": "156720f60267e14c71ebfd194cfa883d2336421405097b562c4b542b3ccefcdc",
    "skills/tdd_patch_plan_v1/skill.json": "2e5871ab8d272d026befe6a1863e8027f62e2e9088a4ccc74cdbf29f9e103ee3"
  }

--- FILE: agent_backend_skill_registry/PACK_MANIFEST.json ---
Size: 2240 bytes
Summary: Keys: pack_id, version, target_runtime, generated_at, source_inspiration, compatibility, skills
Content: |
  {
    "pack_id": "agent_backend_core_skills_v1",
    "version": "0.1.0",
    "target_runtime": "agent_backend",
    "generated_at": "2026-05-04",
    "source_inspiration": [
      {
        "name": "mattpocock/skills",
        "use": "composable engineering workflows, diagnose/TDD/architecture/guardrails patterns"
      },
      {
        "name": "lsdefine/GenericAgent",
        "use": "layered memory, skill crystallisation, bounded recall inspiration with restricted permissions"
      }
    ],
    "compatibility": {
      "requires_metadata_first_importer": true,
      "requires_lazy_skill_md_loading": true,
      "requires_trust_tier_enforcement": true,
      "requires_approval_gate_for_t3": true,
      "requires_quarantine_for_invalid_manifests": true
    },
    "skills": [
      {
        "skill_id": "git_guardrails_v1",
        "version": "0.1.0",
        "risk_tier": "T4",
        "path": "skills/git_guardrails_v1"
      },
      {
        "skill_id": "bug_triage_v1",
        "version": "0.1.0",
        "risk_tier": "T1",
        "path": "skills/bug_triage_v1"
      },
      {
        "skill_id": "candidate_analysis_v1",
        "version": "0.1.0",
        "risk_tier": "T1",
        "path": "skills/candidate_analysis_v1"
      },
      {
        "skill_id": "architecture_review_v1",
        "version": "0.1.0",
        "risk_tier": "T1",
        "path": "skills/architecture_review_v1"
      },
      {
        "skill_id": "tdd_patch_plan_v1",
        "version": "0.1.0",
        "risk_tier": "T1",
        "path": "skills/tdd_patch_plan_v1"
      },
      {
        "skill_id": "refactor_plan_v1",
        "version": "0.1.0",
        "risk_tier": "T1",
        "path": "skills/refactor_plan_v1"
      },
      {
        "skill_id": "patch_generate_v1",
        "version": "0.1.0",
        "risk_tier": "T2",
        "path": "skills/patch_generate_v1"
      },
      {
        "skill_id": "patch_apply_and_test_v1",
        "version": "0.1.0",
        "risk_tier": "T3",
        "path": "skills/patch_apply_and_test_v1"
      },
      {
        "skill_id": "conversation_summary_ingest_v1",
        "version": "0.1.0",
        "risk_tier": "T1",
        "path": "skills/conversation_summary_ingest_v1"
      },
      {
        "skill_id": "skill_crystallize_v1",
        "version": "0.1.0",
        "risk_tier": "T2",
        "path": "skills/skill_crystallize_v1"
      }
    ]
  }

--- FILE: agent_backend_skill_registry/README.md ---
Size: 1456 bytes
Summary: Headers: Agent Backend Core Skill Pack v0.1.0, Contents, Design boundaries, Drop-in expectation
Content: |
  # Agent Backend Core Skill Pack v0.1.0
  
  This is a metadata-first, backend-native drop-in skill pack for `agent_backend`. It is designed for a headless Python/Node MCP runtime that validates strict manifests, selects skills by trigger/capability, lazy-loads `SKILL.md` only after selection, and enforces trust tiers before execution.
  
  ## Contents
  
  - `manifest.schema.json` - strict schema for every `skill.json`
  - `PACK_MANIFEST.json` - pack metadata and compatibility assumptions
  - `SKILL_INDEX.json` - flat selector index for fast matching
  - `TRUST_TIERS.md` - T1-T5 trust vocabulary
  - `skills/*/skill.json` - registry source of truth
  - `skills/*/SKILL.md` - lazy-loaded instruction payload
  - `skills/*/example_input.json` and `example_output.json`
  - `VALIDATION_REPORT.md` - generated validation status
  
  ## Design boundaries
  
  - No UI or frontend artifacts.
  - No autonomous git commit, push, deploy, or destructive filesystem operations.
  - Diff generation is separate from approved diff application.
  - Memory writes must be evidence-backed.
  - Skill crystallisation produces candidate skills only; activation requires human/backend approval.
  
  ## Drop-in expectation
  
  Place this folder under the configured local skill directory for `agent_backend`. The backend importer should load `skill.json`, validate it against `manifest.schema.json`, store the manifest in `skill_manifests`, and lazy-load `SKILL.md` only after the selector chooses a verified skill.

--- FILE: agent_backend_skill_registry/SKILL_INDEX.json ---
Size: 6144 bytes
Summary: Keys: index_version, generated_at, skills
Content: |
  {
    "index_version": "0.1.0",
    "generated_at": "2026-05-04",
    "skills": [
      {
        "skill_id": "git_guardrails_v1",
        "risk_tier": "T4",
        "trigger_terms": [
          "git push",
          "git reset",
          "git clean",
          "destructive command",
          "secret exposure",
          "broad filesystem operation",
          "commit",
          "deploy"
        ],
        "capabilities": [
          "trust_check",
          "git_guardrails",
          "command_policy",
          "risk_classification"
        ],
        "entrypoint": "skills/git_guardrails_v1/SKILL.md",
        "manifest": "skills/git_guardrails_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "bug_triage_v1",
        "risk_tier": "T1",
        "trigger_terms": [
          "triage bug",
          "investigate bug",
          "root cause",
          "failing test",
          "regression",
          "diagnose",
          "reproduction"
        ],
        "capabilities": [
          "bug_triage",
          "candidate_analysis",
          "tdd_planning",
          "root_cause_analysis"
        ],
        "entrypoint": "skills/bug_triage_v1/SKILL.md",
        "manifest": "skills/bug_triage_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "candidate_analysis_v1",
        "risk_tier": "T1",
        "trigger_terms": [
          "candidate analysis",
          "rank files",
          "likely files",
          "where to change",
          "file candidates",
          "function candidates"
        ],
        "capabilities": [
          "candidate_analysis",
          "workspace_ranking",
          "semantic_search",
          "deterministic_scoring"
        ],
        "entrypoint": "skills/candidate_analysis_v1/SKILL.md",
        "manifest": "skills/candidate_analysis_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "architecture_review_v1",
        "risk_tier": "T1",
        "trigger_terms": [
          "architecture review",
          "deep modules",
          "shallow modules",
          "coupling",
          "missing boundary",
          "testability",
          "refactor architecture"
        ],
        "capabilities": [
          "architecture_review",
          "module_deepening",
          "boundary_analysis",
          "testability_review"
        ],
        "entrypoint": "skills/architecture_review_v1/SKILL.md",
        "manifest": "skills/architecture_review_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "tdd_patch_plan_v1",
        "risk_tier": "T1",
        "trigger_terms": [
          "tdd plan",
          "red green refactor",
          "test first",
          "patch plan",
          "failing test",
          "vertical slice"
        ],
        "capabilities": [
          "tdd_planning",
          "test_strategy",
          "patch_planning",
          "vertical_slice"
        ],
        "entrypoint": "skills/tdd_patch_plan_v1/SKILL.md",
        "manifest": "skills/tdd_patch_plan_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "refactor_plan_v1",
        "risk_tier": "T1",
        "trigger_terms": [
          "refactor plan",
          "phased refactor",
          "architecture remediation",
          "technical debt plan",
          "rewrite plan"
        ],
        "capabilities": [
          "refactor_planning",
          "risk_planning",
          "test_strategy",
          "architecture_followup"
        ],
        "entrypoint": "skills/refactor_plan_v1/SKILL.md",
        "manifest": "skills/refactor_plan_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "patch_generate_v1",
        "risk_tier": "T2",
        "trigger_terms": [
          "generate patch",
          "unified diff",
          "patch only",
          "create diff",
          "do not apply"
        ],
        "capabilities": [
          "patch_generation",
          "diff_only",
          "audit_state",
          "guardrail_checked"
        ],
        "entrypoint": "skills/patch_generate_v1/SKILL.md",
        "manifest": "skills/patch_generate_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "patch_apply_and_test_v1",
        "risk_tier": "T3",
        "trigger_terms": [
          "apply approved patch",
          "run declared tests",
          "approved diff",
          "patch apply",
          "test approved patch"
        ],
        "capabilities": [
          "approved_patch_application",
          "test_execution",
          "rollback_artifact",
          "audit_state"
        ],
        "entrypoint": "skills/patch_apply_and_test_v1/SKILL.md",
        "manifest": "skills/patch_apply_and_test_v1/skill.json",
        "requires_user_approval": true,
        "requires_diff_approval": true
      },
      {
        "skill_id": "conversation_summary_ingest_v1",
        "risk_tier": "T1",
        "trigger_terms": [
          "summarize conversation to memory",
          "commit memory",
          "project memory",
          "conversation summary",
          "ingest summary"
        ],
        "capabilities": [
          "memory_ingest",
          "bounded_summary",
          "project_memory",
          "verification_filter"
        ],
        "entrypoint": "skills/conversation_summary_ingest_v1/SKILL.md",
        "manifest": "skills/conversation_summary_ingest_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      },
      {
        "skill_id": "skill_crystallize_v1",
        "risk_tier": "T2",
        "trigger_terms": [
          "crystallize skill",
          "write a skill",
          "turn workflow into skill",
          "candidate skill",
          "SOP manifest"
        ],
        "capabilities": [
          "skill_crystallization",
          "sop_extraction",
          "candidate_manifest",
          "human_activation_required"
        ],
        "entrypoint": "skills/skill_crystallize_v1/SKILL.md",
        "manifest": "skills/skill_crystallize_v1/skill.json",
        "requires_user_approval": false,
        "requires_diff_approval": false
      }
    ]
  }

--- FILE: agent_backend_skill_registry/TRUST_TIERS.md ---
Size: 1135 bytes
Summary: Headers: Trust tiers, T1, T2, T3, T4, T5, Required enforcement
Content: |
  # Trust tiers
  
  ## T1
  
  Read-only analysis, ranking, planning, review, and bounded summarisation. No diffs, no filesystem mutation, no shell execution.
  
  ## T2
  
  Artifact generation that may contain a proposed diff or candidate manifest, but must not apply changes or execute tests.
  
  ## T3
  
  Approved workspace mutation such as applying an already-approved diff and running declared tests. Requires user and diff approval.
  
  ## T4
  
  High-risk local/system actions, destructive filesystem operations, secret exposure risk, git history mutation, package/network mutation, or broad shell execution. Block or require explicit elevated approval.
  
  ## T5
  
  Deployment, production mutation, credential changes, irreversible destructive actions, or public release actions. Not allowed in this v1 pack.
  
  ## Required enforcement
  
  - T1 skills may read/search/scout and produce plans only.
  - T2 skills may produce artifacts such as unified diffs or candidate manifests, but cannot apply them.
  - T3 skills require approval and must preserve rollback artifacts.
  - T4/T5 actions are blocked or escalated; this v1 pack does not include direct T4/T5 executors.

--- FILE: agent_backend_skill_registry/VALIDATION_REPORT.md ---
Size: 2281 bytes
Summary: Headers: Validation report, git_guardrails_v1, bug_triage_v1, candidate_analysis_v1, architecture_review_v1, tdd_patch_plan_v1, refactor_plan_v1, patch_generate_v1, patch_apply_and_test_v1, conversation_summary_ingest_v1
Content: |
  # Validation report
  
  Generated: 2026-05-04
  
  ## git_guardrails_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T4
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## bug_triage_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T1
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## candidate_analysis_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T1
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## architecture_review_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T1
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## tdd_patch_plan_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T1
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## refactor_plan_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T1
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## patch_generate_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T2
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## patch_apply_and_test_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T3
  - Approval: {'requires_user_approval': True, 'requires_diff_approval': True}
  - Status: PASS
  
  ## conversation_summary_ingest_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T1
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## skill_crystallize_v1
  
  - Files: present
  - Strict input schema: yes
  - Strict output schema: yes
  - Risk tier: T2
  - Approval: {'requires_user_approval': False, 'requires_diff_approval': False}
  - Status: PASS
  
  ## Pack status
  
  PASS. All manifests include required fields, strict input/output object schemas, risk tier declarations, approval requirements, and example files.

--- FILE: agent_backend_skill_registry/manifest.schema.json ---
Size: 3303 bytes
Summary: Keys: $schema, title, type, additionalProperties, properties, required
Content: |
  {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "agent_backend skill manifest",
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "skill_id": {
        "type": "string",
        "pattern": "^[a-z][a-z0-9_]*_v[0-9]+$"
      },
      "version": {
        "type": "string",
        "pattern": "^\\d+\\.\\d+\\.\\d+$"
      },
      "name": {
        "type": "string",
        "minLength": 1
      },
      "description": {
        "type": "string",
        "minLength": 20
      },
      "triggers": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "minItems": 1
      },
      "capabilities": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "minItems": 1
      },
      "inputs_schema": {
        "type": "object"
      },
      "outputs_schema": {
        "type": "object"
      },
      "project_scope": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "minItems": 1
      },
      "memory_scope": {
        "type": "string",
        "enum": [
          "none",
          "project",
          "workspace",
          "session"
        ]
      },
      "tool_entrypoints": {
        "type": "array",
        "items": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "entrypoint_type": {
              "type": "string",
              "enum": [
                "instruction_only",
                "script",
                "workflow_mode"
              ]
            },
            "target": {
              "type": "string"
            }
          },
          "required": [
            "entrypoint_type",
            "target"
          ]
        },
        "minItems": 1
      },
      "allowed_tools": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "risk_tier": {
        "type": "string",
        "enum": [
          "T1",
          "T2",
          "T3",
          "T4",
          "T5"
        ]
      },
      "approval_requirements": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "requires_user_approval": {
            "type": "boolean"
          },
          "requires_diff_approval": {
            "type": "boolean"
          }
        },
        "required": [
          "requires_user_approval",
          "requires_diff_approval"
        ]
      },
      "test_commands": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "rollback_strategy": {
        "type": "string"
      },
      "artifacts_produced": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "examples": {
        "type": "array",
        "items": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "input": {
              "type": "object"
            },
            "output": {
              "type": "object"
            }
          },
          "required": [
            "input",
            "output"
          ]
        }
      }
    },
    "required": [
      "skill_id",
      "version",
      "name",
      "description",
      "triggers",
      "capabilities",
      "inputs_schema",
      "outputs_schema",
      "project_scope",
      "memory_scope",
      "tool_entrypoints",
      "allowed_tools",
      "risk_tier",
      "approval_requirements",
      "test_commands",
      "rollback_strategy",
      "artifacts_produced",
      "examples"
    ]
  }

--- FILE: agent_backend_skill_registry/skills/architecture_review_v1/SKILL.md ---
Size: 785 bytes
Summary: Headers: Architecture review v1, Inspect for, Deletion test, Hard rules
Content: |
  # Architecture review v1
  
  Review the codebase for architecture friction without changing code. Use deep-module thinking: prefer small interfaces that hide meaningful implementation detail.
  
  ## Inspect for
  - Shallow pass-through modules
  - Missing adapters or boundary seams
  - Coupling that makes tests or patches broad
  - Policy/executor mixing
  - Backend-only constraint violations
  - Risky mutation paths without trust gates
  
  ## Deletion test
  Ask: if this module disappeared, would complexity disappear or leak into callers? If complexity leaks, the module may be valuable. If nothing meaningful changes, it may be shallow.
  
  ## Hard rules
  - No UI/frontend recommendations.
  - No patch generation.
  - No filesystem mutation.
  - Output review findings and next refactor-planning action only.

--- FILE: agent_backend_skill_registry/skills/architecture_review_v1/example_input.json ---
Size: 215 bytes
Summary: Keys: objective, target_repo, workspace_summary
Content: |
  {
    "objective": "Review skill registry architecture before implementation.",
    "target_repo": "agent_backend",
    "workspace_summary": "orchestrator has agent_workflow, approval, memory, active_partition packages"
  }

--- FILE: agent_backend_skill_registry/skills/architecture_review_v1/example_output.json ---
Size: 1075 bytes
Summary: Keys: summary, deepening_opportunities, shallow_modules, missing_boundaries, adapter_candidates, deletion_test_results, testability_friction, priority_findings, next_action
Content: |
  {
    "summary": "Skill support should be isolated behind registry/importer/selector/executor seams.",
    "deepening_opportunities": [
      {
        "module": "orchestrator/skills/registry.py",
        "reason": "hide persistence/status rules behind a small API"
      }
    ],
    "shallow_modules": [],
    "missing_boundaries": [
      {
        "boundary": "skill selector vs executor",
        "risk": "selection policy may become coupled to mutation logic"
      }
    ],
    "adapter_candidates": [
      {
        "adapter": "SkillInstructionLoader",
        "purpose": "lazy-load SKILL.md only after selection"
      }
    ],
    "deletion_test_results": [
      {
        "candidate": "skills/executor.py",
        "result": "complexity would leak into workflow runner if absent"
      }
    ],
    "testability_friction": [
      {
        "issue": "approval gating must be injectable for unit tests"
      }
    ],
    "priority_findings": [
      {
        "priority": "P0",
        "finding": "split importer, selector, executor, and trust checker"
      }
    ],
    "next_action": "Create phased refactor plan for skills package."
  }

--- FILE: agent_backend_skill_registry/skills/architecture_review_v1/skill.json ---
Size: 4716 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "architecture_review_v1",
    "version": "0.1.0",
    "name": "Architecture review",
    "description": "Review backend architecture for coupling, shallow modules, missing seams, poor testability, and boundary violations; produce refactor opportunities without generating code or diffs.",
    "triggers": [
      "architecture review",
      "deep modules",
      "shallow modules",
      "coupling",
      "missing boundary",
      "testability",
      "refactor architecture"
    ],
    "capabilities": [
      "architecture_review",
      "module_deepening",
      "boundary_analysis",
      "testability_review"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "objective": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "workspace_summary": {
          "type": "string"
        },
        "domain_context": {
          "type": "string"
        },
        "known_pain_points": {
          "type": "string"
        }
      },
      "required": [
        "objective",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "deepening_opportunities": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "shallow_modules": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "missing_boundaries": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "adapter_candidates": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "deletion_test_results": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "testability_friction": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "priority_findings": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "priority_findings",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace"
    ],
    "risk_tier": "T1",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "architecture_report",
      "deepening_opportunity_list",
      "refactor_candidates"
    ],
    "examples": [
      {
        "input": {
          "objective": "Review skill registry architecture before implementation.",
          "target_repo": "agent_backend",
          "workspace_summary": "orchestrator has agent_workflow, approval, memory, active_partition packages"
        },
        "output": {
          "summary": "Skill support should be isolated behind registry/importer/selector/executor seams.",
          "deepening_opportunities": [
            {
              "module": "orchestrator/skills/registry.py",
              "reason": "hide persistence/status rules behind a small API"
            }
          ],
          "shallow_modules": [],
          "missing_boundaries": [
            {
              "boundary": "skill selector vs executor",
              "risk": "selection policy may become coupled to mutation logic"
            }
          ],
          "adapter_candidates": [
            {
              "adapter": "SkillInstructionLoader",
              "purpose": "lazy-load SKILL.md only after selection"
            }
          ],
          "deletion_test_results": [
            {
              "candidate": "skills/executor.py",
              "result": "complexity would leak into workflow runner if absent"
            }
          ],
          "testability_friction": [
            {
              "issue": "approval gating must be injectable for unit tests"
            }
          ],
          "priority_findings": [
            {
              "priority": "P0",
              "finding": "split importer, selector, executor, and trust checker"
            }
          ],
          "next_action": "Create phased refactor plan for skills package."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/bug_triage_v1/SKILL.md ---
Size: 1051 bytes
Summary: Headers: Bug triage v1, Workflow, Hard rules, Output discipline
Content: |
  # Bug triage v1
  
  Diagnose before fixing. Build or identify the fastest feedback loop, then reproduce or explain why reproduction is missing. Do not invent a root cause when logs or workspace evidence are insufficient.
  
  ## Workflow
  1. Restate the observed and expected behavior.
  2. Identify the feedback loop: failing test, log, repro script, integration path, or manual check.
  3. Minimise the case to the smallest behavior that still demonstrates the bug.
  4. Use semantic search and workspace scouting to rank candidate files/functions.
  5. Produce hypotheses with evidence and falsification steps.
  6. Hand off a TDD plan to `tdd_patch_plan_v1` when a test seam exists.
  
  ## Hard rules
  - No patch generation.
  - No file mutation.
  - If reproduction is absent, set `reproduction_status` to `unknown` or `not_reproduced` and request the next evidence artifact.
  - Prefer candidates supported by logs, call paths, tests, manifest names, or recent related changes.
  
  ## Output discipline
  Return a concise report, ranked candidates, and exactly one next action.

--- FILE: agent_backend_skill_registry/skills/bug_triage_v1/example_input.json ---
Size: 209 bytes
Summary: Keys: objective, target_repo, logs, failing_test_output
Content: |
  {
    "objective": "Investigate why semantic search returns stale chunks after a file edit.",
    "target_repo": "agent_backend",
    "logs": "search returns old content after reindex",
    "failing_test_output": ""
  }

--- FILE: agent_backend_skill_registry/skills/bug_triage_v1/example_output.json ---
Size: 1026 bytes
Summary: Keys: summary, feedback_loop, reproduction_status, minimized_case, ranked_hypotheses, likely_candidates, instrumentation_plan, regression_test_seam, tdd_handoff, next_action
Content: |
  {
    "summary": "Search appears to return stale vectors after reindex.",
    "feedback_loop": "Add or run an ingestion/search regression around edit -> ingest -> search.",
    "reproduction_status": "unknown",
    "minimized_case": "Single fixture file edited from phrase A to phrase B, then reindexed and searched for A/B.",
    "ranked_hypotheses": [
      {
        "rank": 1,
        "hypothesis": "stale Chroma vector records are not removed before upsert",
        "evidence": "symptom mentions old content after reindex"
      }
    ],
    "likely_candidates": [
      {
        "rank": 1,
        "path": "orchestrator/ingest/service.py",
        "reason": "likely owns reindex/delete lifecycle"
      }
    ],
    "instrumentation_plan": [
      {
        "step": "Log chunk ids deleted and upserted during force_reindex"
      }
    ],
    "regression_test_seam": "Ingestion service fixture test with changed file content.",
    "tdd_handoff": {
      "skill": "tdd_patch_plan_v1"
    },
    "next_action": "Create a RED test around stale search results after reindex."
  }

--- FILE: agent_backend_skill_registry/skills/bug_triage_v1/skill.json ---
Size: 4422 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "bug_triage_v1",
    "version": "0.1.0",
    "name": "Bug triage",
    "description": "Diagnose a bug or regression by building a feedback loop, reproducing/minimising the issue, ranking root-cause hypotheses, identifying likely files/functions, and handing off a TDD fix plan.",
    "triggers": [
      "triage bug",
      "investigate bug",
      "root cause",
      "failing test",
      "regression",
      "diagnose",
      "reproduction"
    ],
    "capabilities": [
      "bug_triage",
      "candidate_analysis",
      "tdd_planning",
      "root_cause_analysis"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "objective": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "logs": {
          "type": "string"
        },
        "failing_test_output": {
          "type": "string"
        },
        "observed_behavior": {
          "type": "string"
        },
        "expected_behavior": {
          "type": "string"
        }
      },
      "required": [
        "objective",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "feedback_loop": {
          "type": "string"
        },
        "reproduction_status": {
          "type": "string",
          "enum": [
            "reproduced",
            "not_reproduced",
            "partially_reproduced",
            "unknown"
          ]
        },
        "minimized_case": {
          "type": "string"
        },
        "ranked_hypotheses": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "likely_candidates": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "instrumentation_plan": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "regression_test_seam": {
          "type": "string"
        },
        "tdd_handoff": {
          "type": "object",
          "additionalProperties": true
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "likely_candidates",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace"
    ],
    "risk_tier": "T1",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "triage_report",
      "candidate_list",
      "tdd_plan"
    ],
    "examples": [
      {
        "input": {
          "objective": "Investigate why semantic search returns stale chunks after a file edit.",
          "target_repo": "agent_backend",
          "logs": "search returns old content after reindex",
          "failing_test_output": ""
        },
        "output": {
          "summary": "Search appears to return stale vectors after reindex.",
          "feedback_loop": "Add or run an ingestion/search regression around edit -> ingest -> search.",
          "reproduction_status": "unknown",
          "minimized_case": "Single fixture file edited from phrase A to phrase B, then reindexed and searched for A/B.",
          "ranked_hypotheses": [
            {
              "rank": 1,
              "hypothesis": "stale Chroma vector records are not removed before upsert",
              "evidence": "symptom mentions old content after reindex"
            }
          ],
          "likely_candidates": [
            {
              "rank": 1,
              "path": "orchestrator/ingest/service.py",
              "reason": "likely owns reindex/delete lifecycle"
            }
          ],
          "instrumentation_plan": [
            {
              "step": "Log chunk ids deleted and upserted during force_reindex"
            }
          ],
          "regression_test_seam": "Ingestion service fixture test with changed file content.",
          "tdd_handoff": {
            "skill": "tdd_patch_plan_v1"
          },
          "next_action": "Create a RED test around stale search results after reindex."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/candidate_analysis_v1/SKILL.md ---
Size: 707 bytes
Summary: Headers: Candidate analysis v1, Ranking policy, Output rules
Content: |
  # Candidate analysis v1
  
  Rank candidate files/functions deterministically. Treat the ranking as a decision aid, not a claim of certainty.
  
  ## Ranking policy
  Score candidates using only observable evidence:
  - Direct log/test name match
  - Symbol/path match from workspace scout
  - Semantic memory relevance
  - Ownership proximity to the failing behavior
  - Test seam availability
  - Risk/locality: prefer smaller, well-bounded candidates first
  
  ## Output rules
  - Provide top candidates with reason, evidence, and confidence.
  - Record missing context explicitly.
  - Do not generate patches.
  - Do not apply changes or run tests.
  - Use stable ordering: score descending, then evidence count, then path lexical order.

--- FILE: agent_backend_skill_registry/skills/candidate_analysis_v1/example_input.json ---
Size: 224 bytes
Summary: Keys: objective, target_repo, logs, workspace_summary
Content: |
  {
    "objective": "Find likely files for active partition selection bug.",
    "target_repo": "agent_backend",
    "logs": "mcp_get_active_partition returns old project",
    "workspace_summary": "active_partition package exists"
  }

--- FILE: agent_backend_skill_registry/skills/candidate_analysis_v1/example_output.json ---
Size: 702 bytes
Summary: Keys: summary, ranked_candidates, ranking_policy_applied, evidence, missing_context, next_action
Content: |
  {
    "summary": "The active partition package is the highest-probability area.",
    "ranked_candidates": [
      {
        "rank": 1,
        "path": "orchestrator/active_partition/service.py",
        "confidence": 0.86,
        "evidence": [
          "package name match",
          "tool behavior match"
        ]
      }
    ],
    "ranking_policy_applied": "score = direct_match + semantic_match + ownership + test_seam - blast_radius",
    "evidence": [
      {
        "source": "logs",
        "detail": "mcp_get_active_partition returns old project"
      }
    ],
    "missing_context": [
      {
        "item": "current failing test output"
      }
    ],
    "next_action": "Hand top candidates to bug_triage_v1 or tdd_patch_plan_v1."
  }

--- FILE: agent_backend_skill_registry/skills/candidate_analysis_v1/skill.json ---
Size: 3706 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "candidate_analysis_v1",
    "version": "0.1.0",
    "name": "Candidate analysis",
    "description": "Rank likely files, functions, modules, and tests from an objective, logs, workspace scout output, manifests, and project memory while keeping the ranking deterministic and evidence-backed.",
    "triggers": [
      "candidate analysis",
      "rank files",
      "likely files",
      "where to change",
      "file candidates",
      "function candidates"
    ],
    "capabilities": [
      "candidate_analysis",
      "workspace_ranking",
      "semantic_search",
      "deterministic_scoring"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "objective": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "logs": {
          "type": "string"
        },
        "manifest_summary": {
          "type": "string"
        },
        "workspace_summary": {
          "type": "string"
        },
        "rag_context": {
          "type": "string"
        }
      },
      "required": [
        "objective",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "ranked_candidates": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "ranking_policy_applied": {
          "type": "string"
        },
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "missing_context": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "ranked_candidates",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace"
    ],
    "risk_tier": "T1",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "candidate_ranking",
      "evidence_table",
      "missing_context_list"
    ],
    "examples": [
      {
        "input": {
          "objective": "Find likely files for active partition selection bug.",
          "target_repo": "agent_backend",
          "logs": "mcp_get_active_partition returns old project",
          "workspace_summary": "active_partition package exists"
        },
        "output": {
          "summary": "The active partition package is the highest-probability area.",
          "ranked_candidates": [
            {
              "rank": 1,
              "path": "orchestrator/active_partition/service.py",
              "confidence": 0.86,
              "evidence": [
                "package name match",
                "tool behavior match"
              ]
            }
          ],
          "ranking_policy_applied": "score = direct_match + semantic_match + ownership + test_seam - blast_radius",
          "evidence": [
            {
              "source": "logs",
              "detail": "mcp_get_active_partition returns old project"
            }
          ],
          "missing_context": [
            {
              "item": "current failing test output"
            }
          ],
          "next_action": "Hand top candidates to bug_triage_v1 or tdd_patch_plan_v1."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/conversation_summary_ingest_v1/SKILL.md ---
Size: 650 bytes
Summary: Headers: Conversation summary ingest v1, Write only when based on, Reject, Output
Content: |
  # Conversation summary ingest v1
  
  Convert verified conversation events into bounded project memory. Apply the rule: no execution, no memory.
  
  ## Write only when based on
  - successful tool result
  - explicit user decision
  - approved plan
  - completed workflow artifact
  - verified file/code state
  
  ## Reject
  - guesses
  - untested hypotheses
  - broad chat logs with no durable project value
  - transient PIDs, temp paths, timestamps unless needed for audit
  - secrets or credential-like values
  
  ## Output
  Return the memory candidate, verification basis, layer, removed volatile fields, and write_allowed. If write_allowed is false, do not call memory commit.

--- FILE: agent_backend_skill_registry/skills/conversation_summary_ingest_v1/example_input.json ---
Size: 242 bytes
Summary: Keys: conversation_events, target_repo, write_intent
Content: |
  {
    "conversation_events": [
      {
        "type": "user_decision",
        "content": "Use metadata-first skill manifests and lazy SKILL.md loading."
      }
    ],
    "target_repo": "agent_backend",
    "write_intent": "record architecture decision"
  }

--- FILE: agent_backend_skill_registry/skills/conversation_summary_ingest_v1/example_output.json ---
Size: 466 bytes
Summary: Keys: summary, memory_candidate, verification_basis, memory_layer, volatile_fields_removed, write_allowed, next_action
Content: |
  {
    "summary": "Record the accepted skill architecture decision.",
    "memory_candidate": {
      "category": "decision",
      "content": "agent_backend skills use metadata-first skill.json manifests and lazy SKILL.md loading after selector choice."
    },
    "verification_basis": "user_decision",
    "memory_layer": "project_decision",
    "volatile_fields_removed": [],
    "write_allowed": true,
    "next_action": "Commit bounded decision memory through mcp_commit_memory."
  }

--- FILE: agent_backend_skill_registry/skills/conversation_summary_ingest_v1/skill.json ---
Size: 3781 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "conversation_summary_ingest_v1",
    "version": "0.1.0",
    "name": "Conversation summary ingest",
    "description": "Distil verified conversation events into bounded project memory while rejecting guesses, volatile state, secrets, and unexecuted plans; writes only through approved memory tools.",
    "triggers": [
      "summarize conversation to memory",
      "commit memory",
      "project memory",
      "conversation summary",
      "ingest summary"
    ],
    "capabilities": [
      "memory_ingest",
      "bounded_summary",
      "project_memory",
      "verification_filter"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "conversation_events": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "target_repo": {
          "type": "string"
        },
        "project_id": {
          "type": "string"
        },
        "source_artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "write_intent": {
          "type": "string"
        }
      },
      "required": [
        "conversation_events",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "memory_candidate": {
          "type": "object",
          "additionalProperties": true
        },
        "verification_basis": {
          "type": "string",
          "enum": [
            "tool_result",
            "user_decision",
            "approved_plan",
            "completed_artifact",
            "none"
          ]
        },
        "memory_layer": {
          "type": "string",
          "enum": [
            "project_summary",
            "project_decision",
            "project_sop",
            "project_artifact",
            "none"
          ]
        },
        "volatile_fields_removed": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "write_allowed": {
          "type": "boolean"
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "memory_candidate",
        "write_allowed",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_commit_memory"
    ],
    "risk_tier": "T1",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "bounded_summary",
      "memory_record",
      "source_event_ids"
    ],
    "examples": [
      {
        "input": {
          "conversation_events": [
            {
              "type": "user_decision",
              "content": "Use metadata-first skill manifests and lazy SKILL.md loading."
            }
          ],
          "target_repo": "agent_backend",
          "write_intent": "record architecture decision"
        },
        "output": {
          "summary": "Record the accepted skill architecture decision.",
          "memory_candidate": {
            "category": "decision",
            "content": "agent_backend skills use metadata-first skill.json manifests and lazy SKILL.md loading after selector choice."
          },
          "verification_basis": "user_decision",
          "memory_layer": "project_decision",
          "volatile_fields_removed": [],
          "write_allowed": true,
          "next_action": "Commit bounded decision memory through mcp_commit_memory."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/git_guardrails_v1/SKILL.md ---
Size: 1112 bytes
Summary: Headers: Git guardrails v1, Block immediately, Require explicit elevated approval, Allow by default
Content: |
  # Git guardrails v1
  
  Use this as a backend trust-check policy, not as an execution workflow. Classify a proposed command/action before any executor or patch workflow may run.
  
  ## Block immediately
  - `git push`, `git push --force`, `git push --force-with-lease`
  - `git reset --hard`, `git clean`, `git branch -D`, destructive checkout/restore patterns
  - deployment, release, production mutation, credential rotation
  - broad filesystem mutation such as `rm -rf`, recursive delete, chmod/chown over broad roots
  - secret display, token printing, env dumping, private key access
  
  ## Require explicit elevated approval
  - package installation or dependency upgrade
  - database migration
  - network calls that alter remote systems
  - writing outside an approved workspace root
  - applying a diff through `patch_apply_and_test_v1`
  
  ## Allow by default
  - read-only git status/diff/log/show commands
  - workspace scout/search operations
  - diff generation without application
  
  Return `allow`, `require_approval`, or `block` with matched rule identifiers. Never transform a blocked command into an equivalent destructive command.

--- FILE: agent_backend_skill_registry/skills/git_guardrails_v1/example_input.json ---
Size: 151 bytes
Summary: Keys: proposed_action, target_repo, command_text, context
Content: |
  {
    "proposed_action": "run command",
    "target_repo": "agent_backend",
    "command_text": "git reset --hard HEAD~1",
    "context": "discard bad patch"
  }

--- FILE: agent_backend_skill_registry/skills/git_guardrails_v1/example_output.json ---
Size: 529 bytes
Summary: Keys: summary, decision, matched_rules, risk_tier, safe_alternative, violation_response, next_action
Content: |
  {
    "summary": "The command rewrites local state destructively.",
    "decision": "block",
    "matched_rules": [
      {
        "rule": "block_git_reset_hard",
        "pattern": "git reset --hard"
      }
    ],
    "risk_tier": "T4",
    "safe_alternative": "Use git diff/status and produce a rollback plan without executing destructive commands.",
    "violation_response": "Blocked: destructive git history/worktree mutation is not allowed.",
    "next_action": "Ask for a non-destructive rollback artifact or explicit manual operator action."
  }

--- FILE: agent_backend_skill_registry/skills/git_guardrails_v1/skill.json ---
Size: 3573 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "git_guardrails_v1",
    "version": "0.1.0",
    "name": "Git guardrails",
    "description": "Trust-check policy for blocking or escalating dangerous git, filesystem, secret, deployment, package, and broad shell operations before backend execution.",
    "triggers": [
      "git push",
      "git reset",
      "git clean",
      "destructive command",
      "secret exposure",
      "broad filesystem operation",
      "commit",
      "deploy"
    ],
    "capabilities": [
      "trust_check",
      "git_guardrails",
      "command_policy",
      "risk_classification"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "proposed_action": {
          "type": "string",
          "description": "User or model proposed command/action to check."
        },
        "target_repo": {
          "type": "string",
          "description": "Repository or workspace identifier."
        },
        "command_text": {
          "type": "string",
          "description": "Exact command or operation text when available."
        },
        "context": {
          "type": "string",
          "description": "Optional reason/context for the action."
        }
      },
      "required": [
        "proposed_action",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "decision": {
          "type": "string",
          "enum": [
            "allow",
            "require_approval",
            "block"
          ]
        },
        "matched_rules": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "risk_tier": {
          "type": "string",
          "enum": [
            "T1",
            "T2",
            "T3",
            "T4",
            "T5"
          ]
        },
        "safe_alternative": {
          "type": "string"
        },
        "violation_response": {
          "type": "string"
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "decision",
        "matched_rules",
        "risk_tier",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [],
    "risk_tier": "T4",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "blocked_command_patterns",
      "requires_approval_patterns",
      "safe_readonly_patterns",
      "violation_response_template"
    ],
    "examples": [
      {
        "input": {
          "proposed_action": "run command",
          "target_repo": "agent_backend",
          "command_text": "git reset --hard HEAD~1",
          "context": "discard bad patch"
        },
        "output": {
          "summary": "The command rewrites local state destructively.",
          "decision": "block",
          "matched_rules": [
            {
              "rule": "block_git_reset_hard",
              "pattern": "git reset --hard"
            }
          ],
          "risk_tier": "T4",
          "safe_alternative": "Use git diff/status and produce a rollback plan without executing destructive commands.",
          "violation_response": "Blocked: destructive git history/worktree mutation is not allowed.",
          "next_action": "Ask for a non-destructive rollback artifact or explicit manual operator action."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/patch_apply_and_test_v1/SKILL.md ---
Size: 643 bytes
Summary: Headers: Patch apply and test v1, Required gates, Execution discipline, Output
Content: |
  # Patch apply and test v1
  
  Apply only an already approved unified diff. This skill must refuse any request to infer and apply changes from natural language.
  
  ## Required gates
  - User approval present.
  - Diff approval present.
  - Guardrail check passed.
  - Target repo matches approved record.
  
  ## Execution discipline
  - Create or preserve rollback artifact before mutation.
  - Apply exactly the approved diff.
  - Run only declared tests unless operator explicitly approves more.
  - Do not commit.
  - Do not push.
  - Do not deploy.
  
  ## Output
  Return applied files, bounded test logs, pass/fail status, rollback artifact, audit state, and next action.

--- FILE: agent_backend_skill_registry/skills/patch_apply_and_test_v1/example_input.json ---
Size: 267 bytes
Summary: Keys: approved_diff, approved_diff_id, target_repo, test_commands, approval_record
Content: |
  {
    "approved_diff": "diff --git ...",
    "approved_diff_id": "diff-20260504-001",
    "target_repo": "agent_backend",
    "test_commands": [
      "python -m unittest tests.test_skill_schema -v"
    ],
    "approval_record": {
      "user": "operator",
      "approved": true
    }
  }

--- FILE: agent_backend_skill_registry/skills/patch_apply_and_test_v1/example_output.json ---
Size: 613 bytes
Summary: Keys: summary, approved_diff_id, applied_files, test_logs, test_status, rollback_artifact, audit_state, next_action
Content: |
  {
    "summary": "Approved diff applied and tests passed.",
    "approved_diff_id": "diff-20260504-001",
    "applied_files": [
      "backend/python-daemon/orchestrator/skills/schema.py"
    ],
    "test_logs": [
      {
        "command": "python -m unittest tests.test_skill_schema -v",
        "status": "passed",
        "tail": "OK"
      }
    ],
    "test_status": "passed",
    "rollback_artifact": ".aletheia_state/rollback/diff-20260504-001.patch",
    "audit_state": {
      "risk_tier": "T3",
      "approval_verified": true,
      "committed": false,
      "pushed": false
    },
    "next_action": "Report results; do not commit or push."
  }

--- FILE: agent_backend_skill_registry/skills/patch_apply_and_test_v1/skill.json ---
Size: 3836 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "patch_apply_and_test_v1",
    "version": "0.1.0",
    "name": "Patch apply and test",
    "description": "Apply an already approved unified diff and run declared tests through the backend approval gate; refuses unapproved natural-language mutation requests.",
    "triggers": [
      "apply approved patch",
      "run declared tests",
      "approved diff",
      "patch apply",
      "test approved patch"
    ],
    "capabilities": [
      "approved_patch_application",
      "test_execution",
      "rollback_artifact",
      "audit_state"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "approved_diff": {
          "type": "string"
        },
        "approved_diff_id": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "test_commands": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "approval_record": {
          "type": "object",
          "additionalProperties": true
        }
      },
      "required": [
        "approved_diff",
        "target_repo",
        "approval_record"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "approved_diff_id": {
          "type": "string"
        },
        "applied_files": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "test_logs": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "test_status": {
          "type": "string",
          "enum": [
            "passed",
            "failed",
            "not_run"
          ]
        },
        "rollback_artifact": {
          "type": "string"
        },
        "audit_state": {
          "type": "object",
          "additionalProperties": true
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "applied_files",
        "test_status",
        "audit_state",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_agent_workflow_run"
    ],
    "risk_tier": "T3",
    "approval_requirements": {
      "requires_user_approval": true,
      "requires_diff_approval": true
    },
    "test_commands": [],
    "rollback_strategy": "restore rollback artifact produced before applying approved diff",
    "artifacts_produced": [
      "applied_files",
      "test_logs",
      "rollback_artifact",
      "audit_record"
    ],
    "examples": [
      {
        "input": {
          "approved_diff": "diff --git ...",
          "approved_diff_id": "diff-20260504-001",
          "target_repo": "agent_backend",
          "test_commands": [
            "python -m unittest tests.test_skill_schema -v"
          ],
          "approval_record": {
            "user": "operator",
            "approved": true
          }
        },
        "output": {
          "summary": "Approved diff applied and tests passed.",
          "approved_diff_id": "diff-20260504-001",
          "applied_files": [
            "backend/python-daemon/orchestrator/skills/schema.py"
          ],
          "test_logs": [
            {
              "command": "python -m unittest tests.test_skill_schema -v",
              "status": "passed",
              "tail": "OK"
            }
          ],
          "test_status": "passed",
          "rollback_artifact": ".aletheia_state/rollback/diff-20260504-001.patch",
          "audit_state": {
            "risk_tier": "T3",
            "approval_verified": true,
            "committed": false,
            "pushed": false
          },
          "next_action": "Report results; do not commit or push."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/patch_generate_v1/SKILL.md ---
Size: 764 bytes
Summary: Headers: Patch generate v1, Required inputs, Guardrail precheck, Output rules
Content: |
  # Patch generate v1
  
  Generate a proposed unified diff only. Do not apply it. Do not run tests. Do not commit or push.
  
  ## Required inputs
  - Objective
  - Target repo
  - TDD/refactor plan
  - Candidate files or sufficient workspace evidence
  
  ## Guardrail precheck
  Use `git_guardrails_v1` policy vocabulary. If the requested change implies destructive action, deployment, secret access, broad shell execution, or git mutation, block or escalate instead of producing a diff.
  
  ## Output rules
  - Return a valid unified diff in `unified_diff`.
  - List affected files.
  - List test commands that should be run after approval.
  - Include audit state: source plan, guardrail result, risk tier, and whether approval is required for application.
  - Never claim the patch was applied.

--- FILE: agent_backend_skill_registry/skills/patch_generate_v1/example_input.json ---
Size: 291 bytes
Summary: Keys: objective, target_repo, tdd_plan, candidate_files
Content: |
  {
    "objective": "Add strict manifest validation test.",
    "target_repo": "agent_backend",
    "tdd_plan": {
      "red_steps": [
        {
          "step": "test invalid manifest quarantined"
        }
      ]
    },
    "candidate_files": [
      {
        "path": "orchestrator/skills/schema.py"
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/patch_generate_v1/example_output.json ---
Size: 822 bytes
Summary: Keys: summary, unified_diff, affected_files, test_commands, guardrail_checks, audit_state, next_action
Content: |
  {
    "summary": "Generated a diff proposal only.",
    "unified_diff": "diff --git a/backend/python-daemon/orchestrator/skills/schema.py b/backend/python-daemon/orchestrator/skills/schema.py\n--- a/backend/python-daemon/orchestrator/skills/schema.py\n+++ b/backend/python-daemon/orchestrator/skills/schema.py\n@@ -0,0 +1,2 @@\n+class SkillManifestError(ValueError):\n+    pass\n",
    "affected_files": [
      "backend/python-daemon/orchestrator/skills/schema.py"
    ],
    "test_commands": [
      "python -m unittest tests.test_skill_schema -v"
    ],
    "guardrail_checks": [
      {
        "rule": "diff_only",
        "decision": "allow"
      }
    ],
    "audit_state": {
      "risk_tier": "T2",
      "applied": false,
      "requires_approval_for_apply": true
    },
    "next_action": "Present diff for approval before patch_apply_and_test_v1."
  }

--- FILE: agent_backend_skill_registry/skills/patch_generate_v1/skill.json ---
Size: 4036 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "patch_generate_v1",
    "version": "0.1.0",
    "name": "Patch generate",
    "description": "Generate a unified diff from an approved objective and TDD/refactor plan without applying it, running tests, committing, pushing, or performing filesystem mutation.",
    "triggers": [
      "generate patch",
      "unified diff",
      "patch only",
      "create diff",
      "do not apply"
    ],
    "capabilities": [
      "patch_generation",
      "diff_only",
      "audit_state",
      "guardrail_checked"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "objective": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "tdd_plan": {
          "type": "object",
          "additionalProperties": true
        },
        "candidate_files": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "guardrail_context": {
          "type": "object",
          "additionalProperties": true
        }
      },
      "required": [
        "objective",
        "target_repo",
        "tdd_plan"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "unified_diff": {
          "type": "string"
        },
        "affected_files": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "test_commands": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "guardrail_checks": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "audit_state": {
          "type": "object",
          "additionalProperties": true
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "unified_diff",
        "affected_files",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace",
      "mcp_agent_workflow_run"
    ],
    "risk_tier": "T2",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "unified_diff",
      "affected_files",
      "test_commands",
      "audit_record"
    ],
    "examples": [
      {
        "input": {
          "objective": "Add strict manifest validation test.",
          "target_repo": "agent_backend",
          "tdd_plan": {
            "red_steps": [
              {
                "step": "test invalid manifest quarantined"
              }
            ]
          },
          "candidate_files": [
            {
              "path": "orchestrator/skills/schema.py"
            }
          ]
        },
        "output": {
          "summary": "Generated a diff proposal only.",
          "unified_diff": "diff --git a/backend/python-daemon/orchestrator/skills/schema.py b/backend/python-daemon/orchestrator/skills/schema.py\n--- a/backend/python-daemon/orchestrator/skills/schema.py\n+++ b/backend/python-daemon/orchestrator/skills/schema.py\n@@ -0,0 +1,2 @@\n+class SkillManifestError(ValueError):\n+    pass\n",
          "affected_files": [
            "backend/python-daemon/orchestrator/skills/schema.py"
          ],
          "test_commands": [
            "python -m unittest tests.test_skill_schema -v"
          ],
          "guardrail_checks": [
            {
              "rule": "diff_only",
              "decision": "allow"
            }
          ],
          "audit_state": {
            "risk_tier": "T2",
            "applied": false,
            "requires_approval_for_apply": true
          },
          "next_action": "Present diff for approval before patch_apply_and_test_v1."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/refactor_plan_v1/SKILL.md ---
Size: 390 bytes
Summary: Headers: Refactor plan v1, Rules
Content: |
  # Refactor plan v1
  
  Plan a refactor in small phases. Preserve current behavior and keep every phase independently testable.
  
  ## Rules
  - No code changes.
  - No diff generation.
  - No apply/test execution.
  - Every phase needs purpose, files/modules, test command, rollback note, and approval boundary if mutation will follow.
  - Prefer seam extraction and adapter isolation over broad rewrites.

--- FILE: agent_backend_skill_registry/skills/refactor_plan_v1/example_input.json ---
Size: 225 bytes
Summary: Keys: objective, target_repo, architecture_review
Content: |
  {
    "objective": "Plan skills package implementation.",
    "target_repo": "agent_backend",
    "architecture_review": {
      "priority_findings": [
        {
          "finding": "split importer selector executor"
        }
      ]
    }
  }

--- FILE: agent_backend_skill_registry/skills/refactor_plan_v1/example_output.json ---
Size: 862 bytes
Summary: Keys: summary, refactor_objective, phases, risk_register, test_strategy, rollback_notes, approval_points, next_action
Content: |
  {
    "summary": "Implement skills package behind narrow seams.",
    "refactor_objective": "Add metadata-first skills without coupling to workflow runner internals.",
    "phases": [
      {
        "phase": 1,
        "name": "schema and validation",
        "tests": [
          "test_skill_schema"
        ]
      }
    ],
    "risk_register": [
      {
        "risk": "selector loads SKILL.md too early",
        "mitigation": "test lazy loading"
      }
    ],
    "test_strategy": [
      {
        "command": "python -m unittest discover -s tests -v",
        "purpose": "default suite remains green"
      }
    ],
    "rollback_notes": "Remove orchestrator/skills package and migration if validation fails before integration.",
    "approval_points": [
      {
        "point": "before patch_apply_and_test implementation"
      }
    ],
    "next_action": "Use patch_generate_v1 to create Phase 1 diff only."
  }

--- FILE: agent_backend_skill_registry/skills/refactor_plan_v1/skill.json ---
Size: 3984 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "refactor_plan_v1",
    "version": "0.1.0",
    "name": "Refactor plan",
    "description": "Turn architecture review findings or a refactor objective into a phased backend-safe plan with tests, rollback notes, and approval points; no code or diff generation.",
    "triggers": [
      "refactor plan",
      "phased refactor",
      "architecture remediation",
      "technical debt plan",
      "rewrite plan"
    ],
    "capabilities": [
      "refactor_planning",
      "risk_planning",
      "test_strategy",
      "architecture_followup"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "objective": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "architecture_review": {
          "type": "object",
          "additionalProperties": true
        },
        "constraints": {
          "type": "string"
        }
      },
      "required": [
        "objective",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "refactor_objective": {
          "type": "string"
        },
        "phases": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "risk_register": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "test_strategy": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "rollback_notes": {
          "type": "string"
        },
        "approval_points": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "phases",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace"
    ],
    "risk_tier": "T1",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "refactor_plan",
      "risk_register",
      "test_strategy"
    ],
    "examples": [
      {
        "input": {
          "objective": "Plan skills package implementation.",
          "target_repo": "agent_backend",
          "architecture_review": {
            "priority_findings": [
              {
                "finding": "split importer selector executor"
              }
            ]
          }
        },
        "output": {
          "summary": "Implement skills package behind narrow seams.",
          "refactor_objective": "Add metadata-first skills without coupling to workflow runner internals.",
          "phases": [
            {
              "phase": 1,
              "name": "schema and validation",
              "tests": [
                "test_skill_schema"
              ]
            }
          ],
          "risk_register": [
            {
              "risk": "selector loads SKILL.md too early",
              "mitigation": "test lazy loading"
            }
          ],
          "test_strategy": [
            {
              "command": "python -m unittest discover -s tests -v",
              "purpose": "default suite remains green"
            }
          ],
          "rollback_notes": "Remove orchestrator/skills package and migration if validation fails before integration.",
          "approval_points": [
            {
              "point": "before patch_apply_and_test implementation"
            }
          ],
          "next_action": "Use patch_generate_v1 to create Phase 1 diff only."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/skill_crystallize_v1/SKILL.md ---
Size: 763 bytes
Summary: Headers: Skill crystallize v1, Evidence requirements, Draft requirements, Activation rule
Content: |
  # Skill crystallize v1
  
  Draft a candidate skill from a successful workflow. Do not activate it. Do not mark it verified. Do not import it into the registry.
  
  ## Evidence requirements
  A candidate skill must cite source run artifacts such as completed outputs, accepted user decisions, passed tests, or verified tool results.
  
  ## Draft requirements
  - skill_id
  - version
  - name
  - description
  - triggers
  - capabilities
  - strict input/output schemas
  - project_scope
  - memory_scope
  - tool entrypoints
  - allowed tools
  - risk tier
  - approval requirements
  - rollback strategy
  - artifacts produced
  - example input/output
  
  ## Activation rule
  Always set `requires_human_activation` to true. The backend importer may quarantine or verify later, but this skill may only draft.

--- FILE: agent_backend_skill_registry/skills/skill_crystallize_v1/example_input.json ---
Size: 265 bytes
Summary: Keys: source_run_summary, target_repo, reusable_pattern, proposed_skill_id
Content: |
  {
    "source_run_summary": "Repeated successful triage process for stale vector bugs.",
    "target_repo": "agent_backend",
    "reusable_pattern": "reproduce stale search, rank ingest candidates, create TDD regression",
    "proposed_skill_id": "stale_vector_triage_v1"
  }

--- FILE: agent_backend_skill_registry/skills/skill_crystallize_v1/example_output.json ---
Size: 643 bytes
Summary: Keys: summary, candidate_skill_id, source_run_artifacts, reusable_pattern, activation_risk_tier, requires_human_activation, proposed_skill_json, proposed_skill_md, next_action
Content: |
  {
    "summary": "Drafted a candidate skill from a verified repeated workflow.",
    "candidate_skill_id": "stale_vector_triage_v1",
    "source_run_artifacts": [
      {
        "artifact": "triage_report",
        "verified": true
      }
    ],
    "reusable_pattern": "Use edit -> reindex -> search loop to diagnose stale vector bugs.",
    "activation_risk_tier": "T1",
    "requires_human_activation": true,
    "proposed_skill_json": {
      "skill_id": "stale_vector_triage_v1",
      "version": "0.1.0"
    },
    "proposed_skill_md": "# Stale vector triage v1\n\nDraft instructions...",
    "next_action": "Submit candidate for human review and backend validation."
  }

--- FILE: agent_backend_skill_registry/skills/skill_crystallize_v1/skill.json ---
Size: 3972 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "skill_crystallize_v1",
    "version": "0.1.0",
    "name": "Skill crystallize",
    "description": "Turn a successful, evidence-backed workflow into a candidate skill manifest and SKILL.md draft; never verifies, imports, enables, or activates the skill automatically.",
    "triggers": [
      "crystallize skill",
      "write a skill",
      "turn workflow into skill",
      "candidate skill",
      "SOP manifest"
    ],
    "capabilities": [
      "skill_crystallization",
      "sop_extraction",
      "candidate_manifest",
      "human_activation_required"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "source_run_summary": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "successful_artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "reusable_pattern": {
          "type": "string"
        },
        "proposed_skill_id": {
          "type": "string"
        }
      },
      "required": [
        "source_run_summary",
        "target_repo",
        "reusable_pattern"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "candidate_skill_id": {
          "type": "string"
        },
        "source_run_artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "reusable_pattern": {
          "type": "string"
        },
        "activation_risk_tier": {
          "type": "string",
          "enum": [
            "T1",
            "T2",
            "T3",
            "T4",
            "T5"
          ]
        },
        "requires_human_activation": {
          "type": "boolean"
        },
        "proposed_skill_json": {
          "type": "object",
          "additionalProperties": true
        },
        "proposed_skill_md": {
          "type": "string"
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "candidate_skill_id",
        "requires_human_activation",
        "proposed_skill_json",
        "proposed_skill_md",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace"
    ],
    "risk_tier": "T2",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "candidate_skill_json",
      "candidate_skill_md",
      "activation_rationale"
    ],
    "examples": [
      {
        "input": {
          "source_run_summary": "Repeated successful triage process for stale vector bugs.",
          "target_repo": "agent_backend",
          "reusable_pattern": "reproduce stale search, rank ingest candidates, create TDD regression",
          "proposed_skill_id": "stale_vector_triage_v1"
        },
        "output": {
          "summary": "Drafted a candidate skill from a verified repeated workflow.",
          "candidate_skill_id": "stale_vector_triage_v1",
          "source_run_artifacts": [
            {
              "artifact": "triage_report",
              "verified": true
            }
          ],
          "reusable_pattern": "Use edit -> reindex -> search loop to diagnose stale vector bugs.",
          "activation_risk_tier": "T1",
          "requires_human_activation": true,
          "proposed_skill_json": {
            "skill_id": "stale_vector_triage_v1",
            "version": "0.1.0"
          },
          "proposed_skill_md": "# Stale vector triage v1\n\nDraft instructions...",
          "next_action": "Submit candidate for human review and backend validation."
        }
      }
    ]
  }

--- FILE: agent_backend_skill_registry/skills/tdd_patch_plan_v1/SKILL.md ---
Size: 536 bytes
Summary: Headers: TDD patch plan v1, Rules, Output
Content: |
  # TDD patch plan v1
  
  Plan only. Produce a vertical-slice RED/GREEN/REFACTOR sequence.
  
  ## Rules
  - Start with one failing behavior test.
  - Prefer public interfaces and tool contracts over private implementation tests.
  - Do not plan broad speculative test suites.
  - Do not refactor while RED.
  - Do not generate a diff.
  - Do not apply changes or run tests.
  
  ## Output
  Specify the public interface under test, the first behavior slice, RED steps, GREEN steps, refactor-after-green steps, declared test commands, non-goals, and next action.

--- FILE: agent_backend_skill_registry/skills/tdd_patch_plan_v1/example_input.json ---
Size: 262 bytes
Summary: Keys: objective, target_repo, candidate_files, known_test_commands
Content: |
  {
    "objective": "Fix stale chunks after reindex.",
    "target_repo": "agent_backend",
    "candidate_files": [
      {
        "path": "orchestrator/ingest/service.py"
      }
    ],
    "known_test_commands": [
      "python -m unittest tests.test_chroma_and_ingest -v"
    ]
  }

--- FILE: agent_backend_skill_registry/skills/tdd_patch_plan_v1/example_output.json ---
Size: 898 bytes
Summary: Keys: summary, public_interface_under_test, behavior_slices, red_steps, green_steps, refactor_after_green, declared_test_commands, non_goals, next_action
Content: |
  {
    "summary": "Plan one regression around edit -> reindex -> search.",
    "public_interface_under_test": "mcp_ingest_target + mcp_semantic_search behavior",
    "behavior_slices": [
      {
        "slice": "single changed fixture file no longer returns old phrase"
      }
    ],
    "red_steps": [
      {
        "step": "Add failing unit/integration test asserting old phrase disappears after reindex"
      }
    ],
    "green_steps": [
      {
        "step": "Remove stale chunk/vector records before inserting changed chunks"
      }
    ],
    "refactor_after_green": [
      {
        "step": "Extract stale cleanup helper if deletion logic duplicates directory ingestion"
      }
    ],
    "declared_test_commands": [
      "python -m unittest tests.test_chroma_and_ingest -v"
    ],
    "non_goals": [
      {
        "item": "No broad Chroma rebuild feature in this patch"
      }
    ],
    "next_action": "Pass plan to patch_generate_v1."
  }

--- FILE: agent_backend_skill_registry/skills/tdd_patch_plan_v1/skill.json ---
Size: 4516 bytes
Summary: Keys: skill_id, version, name, description, triggers, capabilities, inputs_schema, outputs_schema, project_scope, memory_scope
Content: |
  {
    "skill_id": "tdd_patch_plan_v1",
    "version": "0.1.0",
    "name": "TDD patch plan",
    "description": "Convert bug triage, candidate files, and objectives into a vertical-slice RED/GREEN/REFACTOR plan using public behavior seams and declared tests only.",
    "triggers": [
      "tdd plan",
      "red green refactor",
      "test first",
      "patch plan",
      "failing test",
      "vertical slice"
    ],
    "capabilities": [
      "tdd_planning",
      "test_strategy",
      "patch_planning",
      "vertical_slice"
    ],
    "inputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "objective": {
          "type": "string"
        },
        "target_repo": {
          "type": "string"
        },
        "triage_report": {
          "type": "object",
          "additionalProperties": true
        },
        "candidate_files": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "known_test_commands": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "objective",
        "target_repo"
      ]
    },
    "outputs_schema": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": {
          "type": "string"
        },
        "public_interface_under_test": {
          "type": "string"
        },
        "behavior_slices": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "red_steps": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "green_steps": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "refactor_after_green": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "declared_test_commands": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "non_goals": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "next_action": {
          "type": "string"
        }
      },
      "required": [
        "summary",
        "red_steps",
        "green_steps",
        "next_action"
      ]
    },
    "project_scope": [
      "*"
    ],
    "memory_scope": "project",
    "tool_entrypoints": [
      {
        "entrypoint_type": "instruction_only",
        "target": "SKILL.md"
      }
    ],
    "allowed_tools": [
      "mcp_get_active_partition",
      "mcp_semantic_search_active",
      "mcp_scout_workspace"
    ],
    "risk_tier": "T1",
    "approval_requirements": {
      "requires_user_approval": false,
      "requires_diff_approval": false
    },
    "test_commands": [],
    "rollback_strategy": "none",
    "artifacts_produced": [
      "tdd_plan",
      "test_strategy",
      "declared_test_commands"
    ],
    "examples": [
      {
        "input": {
          "objective": "Fix stale chunks after reindex.",
          "target_repo": "agent_backend",
          "candidate_files": [
            {
              "path": "orchestrator/ingest/service.py"
            }
          ],
          "known_test_commands": [
            "python -m unittest tests.test_chroma_and_ingest -v"
          ]
        },
        "output": {
          "summary": "Plan one regression around edit -> reindex -> search.",
          "public_interface_under_test": "mcp_ingest_target + mcp_semantic_search behavior",
          "behavior_slices": [
            {
              "slice": "single changed fixture file no longer returns old phrase"
            }
          ],
          "red_steps": [
            {
              "step": "Add failing unit/integration test asserting old phrase disappears after reindex"
            }
          ],
          "green_steps": [
            {
              "step": "Remove stale chunk/vector records before inserting changed chunks"
            }
          ],
          "refactor_after_green": [
            {
              "step": "Extract stale cleanup helper if deletion logic duplicates directory ingestion"
            }
          ],
          "declared_test_commands": [
            "python -m unittest tests.test_chroma_and_ingest -v"
          ],
          "non_goals": [
            {
              "item": "No broad Chroma rebuild feature in this patch"
            }
          ],
          "next_action": "Pass plan to patch_generate_v1."
        }
      }
    ]
  }

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
Size: 13198 bytes
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
      name: "mcp_commit_memory",
      description: "Commit a bounded memory record to the active LM Studio partition.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          category: {
            type: "string",
            enum: ["architecture", "decision", "summary", "bug_fix", "preference", "artifact"],
          },
          content: { type: "string", minLength: 10, maxLength: 8000 },
          confidence_score: { type: "number", minimum: 0.0, maximum: 1.0, default: 1.0 },
          metadata: { type: "object", additionalProperties: true },
        },
        required: ["category", "content"],
      },
    },
    {
      name: "mcp_agent_workflow_run",
      description: "Run the deterministic LM Studio-facing workflow controller.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          objective: { type: "string", minLength: 1 },
          target_repo: { type: "string", minLength: 1 },
          profile: { type: "string", enum: ["safe"], default: "safe" },
          allow_ingest: { type: "boolean", default: false },
          include_report_preview: { type: "boolean", default: false },
          use_model_phases: { type: "boolean", default: false },
        },
        required: ["objective", "target_repo"],
      },
    },
    {
      name: "mcp_get_active_partition",
      description: "Return the current active LM Studio partition from SQLite state.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {},
      },
    },
    {
      name: "mcp_investigation_start",
      description: "Start a safe external ToolSet investigation session.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          objective: { type: "string", minLength: 1 },
          target_repo: { type: "string", minLength: 1 },
          profile: { type: "string", enum: ["safe"] },
        },
        required: ["objective", "target_repo"],
      },
    },
    {
      name: "mcp_investigation_filemap",
      description: "Build constrained file map summaries for an investigation session.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          session_path: { type: "string", minLength: 1 },
          profile: { type: "string", enum: ["safe"] },
        },
        required: ["session_path"],
      },
    },
    {
      name: "mcp_investigation_validate_manifest",
      description: "Validate a ToolSet investigation manifest.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          session_path: { type: "string", minLength: 1 },
        },
        required: ["session_path"],
      },
    },
    {
      name: "mcp_investigation_read_report",
      description: "Read bounded investigation report content from ToolSet artifacts.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          session_path: { type: "string", minLength: 1 },
          artifact_key: { type: "string", enum: ["manifest_csv", "manifest_health_json", "manifest_doctor_json", "manifest_doctor_md", "command_lint_json", "slicer_json", "slicer_md", "final_markdown", "final_python_bundle", "archive_yaml"] },
          max_chars: { type: "integer", minimum: 1, maximum: 12000 },
        },
        required: ["session_path", "artifact_key"],
      },
    },
    {
      name: "mcp_investigation_compile_handoff",
      description: "Compile investigation handoff metadata and artifact paths.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          session_path: { type: "string", minLength: 1 },
        },
        required: ["session_path"],
      },
    },
    {
      name: "mcp_list_memory_projects",
      description: "List known LM Studio memory projects from SQLite state.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {},
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
      name: "mcp_semantic_search_active",
      description: "Run semantic search within the active LM Studio partition only.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          query: { type: "string", minLength: 1 },
          k: { type: "integer", minimum: 1, maximum: 50, default: 8 },
        },
        required: ["query"],
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
      name: "mcp_set_active_partition",
      description: "Set the active LM Studio partition from a conversation path.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          conversation_path: { type: "string", minLength: 1 },
        },
        required: ["conversation_path"],
      },
    },
    {
      name: "mcp_set_active_project_manual",
      description: "Manually override the active LM Studio project for admin/debug use.",
      strict: true,
      inputSchema: {
        $schema: DRAFT7,
        type: "object",
        additionalProperties: false,
        properties: {
          project_id: { type: "string", minLength: 1 },
          display_name: { type: "string", minLength: 1 },
        },
        required: ["project_id"],
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
    const result = validateObject(contract.inputSchema, args ?? {}, "");
    if (!result.ok) {
      return result;
    }
    if (name === "mcp_set_active_partition") {
      const hasConversation = typeof args?.conversation_path === "string" && args.conversation_path.length > 0;
      if (!hasConversation) {
        return {
          ok: false,
          error: "schema_validation_failed",
          details: [{ path: "", keyword: "required", message: "conversation_path is required" }],
        };
      }
    }
    return result;
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
        if (schema.maxLength !== undefined && value.length > schema.maxLength) {
          details.push({ path, keyword: "maxLength", message: `length must be <= [REDACTED_HIGH_ENTROPY]
        }
        if (schema.pattern && !(new RegExp(schema.pattern).test(value))) {
          details.push({ path, keyword: "pattern", message: `must match ${schema.pattern}` });
        }
        if (schema.enum && !schema.enum.includes(value)) {
          details.push({ path, keyword= [REDACTED_HIGH_ENTROPY]
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
    if (schema.type === "number") {
      if (typeof value !== "number" || Number.isNaN(value)) {
        details.push({ path, keyword: "type", message: "must be number" });
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

--- FILE: node-mcp/test/active-memory-contracts.test.mjs ---
Size: 2902 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import { test } from "node:test";
  
  import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";
  
  const EXPECTED = [
    "mcp_agent_workflow_run",
    "mcp_commit_memory",
    "mcp_get_active_partition",
    "mcp_list_memory_projects",
    "mcp_semantic_search_active",
    "mcp_set_active_partition",
    "mcp_set_active_project_manual",
  ];
  
  test("active memory contracts exist and are strict", () => {
    for (const name of EXPECTED) {
      const contract = CONTRACTS.find((item) => item.name === name);
      assert.ok(contract, `missing contract ${name}`);
      assert.equal(contract.strict, true);
      assert.equal(contract.inputSchema.additionalProperties, false);
    }
  });
  
  test("active search contract does not expose project_id", () => {
    const contract = CONTRACTS.find((item) => item.name === "mcp_semantic_search_active");
    assert.ok(contract);
    assert.equal(Object.hasOwn(contract.inputSchema.properties, "project_id"), false);
    assert.equal(validateToolInput("mcp_semantic_search_active", { project_id: "p", query: "q" }).ok, false);
  });
  
  test("workflow contract exists, is strict, and rejects unknown fields", () => {
    const contract = CONTRACTS.find((item) => item.name === "mcp_agent_workflow_run");
    assert.ok(contract);
    assert.equal(contract.strict, true);
    assert.equal(contract.inputSchema.additionalProperties, false);
    assert.equal(
      validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "C:/tmp", unexpected: true }).ok,
      false
    );
    assert.equal(
      validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "C:/tmp", profile: "safe" }).ok,
      true
    );
  });
  
  test("commit memory enforces category enum and content minimum length", () => {
    assert.equal(validateToolInput("mcp_commit_memory", { category: "unknown", content: "abcdefghijkl" }).ok, false);
    assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "short" }).ok, false);
    assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content" }).ok, true);
    assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content", confidence_score: "bad" }).ok, false);
    assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content", confidence_score: -0.1 }).ok, false);
    assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content", confidence_score: 1.1 }).ok, false);
  });
  
  test("set active partition requires conversation_path only", () => {
    assert.equal(validateToolInput("mcp_set_active_partition", {}).ok, false);
    assert.equal(validateToolInput("mcp_set_active_partition", { conversation_path: "C:/tmp/chat.json" }).ok, true);
    assert.equal(validateToolInput("mcp_set_active_partition", { project_id: "p" }).ok, false);
  });

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

--- FILE: node-mcp/test/investigation-contracts.test.mjs ---
Size: 2363 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import { test } from "node:test";
  
  import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";
  
  const TOOL_NAMES = [
    "mcp_investigation_start",
    "mcp_investigation_filemap",
    "mcp_investigation_validate_manifest",
    "mcp_investigation_read_report",
    "mcp_investigation_compile_handoff",
  ];
  
  test("investigation contracts exist", () => {
    for (const name of TOOL_NAMES) {
      assert.ok(CONTRACTS.find((contract) => contract.name === name));
    }
  });
  
  test("investigation contracts enforce required fields and reject unknowns", () => {
    assert.equal(validateToolInput("mcp_investigation_start", { target_repo: "x" }).ok, false);
    assert.equal(validateToolInput("mcp_investigation_filemap", {}).ok, false);
    assert.equal(validateToolInput("mcp_investigation_filemap", { session_path: "s", profile: "unsafe" }).ok, false);
    assert.equal(validateToolInput("mcp_investigation_validate_manifest", {}).ok, false);
    assert.equal(validateToolInput("mcp_investigation_read_report", { session_path: "s" }).ok, false);
    assert.equal(validateToolInput("mcp_investigation_read_report", { session_path= [REDACTED_HIGH_ENTROPY]
    assert.equal(validateToolInput("mcp_investigation_read_report", { session_path= [REDACTED_HIGH_ENTROPY]
    assert.equal(validateToolInput("mcp_investigation_compile_handoff", {}).ok, false);
  
    const unknown = validateToolInput("mcp_investigation_start", { objective: "o", target_repo: "r", extra: true });
    assert.equal(unknown.ok, false);
    assert.match(JSON.stringify(unknown.details), /additionalProperties/);
  });
  
  test("investigation contracts accept valid payloads", () => {
    assert.equal(validateToolInput("mcp_investigation_start", { objective: "o", target_repo: "r", profile: "safe" }).ok, true);
    assert.equal(validateToolInput("mcp_investigation_filemap", { session_path: "s", profile: "safe" }).ok, true);
    assert.equal(validateToolInput("mcp_investigation_validate_manifest", { session_path: "s" }).ok, true);
    assert.equal(validateToolInput("mcp_investigation_read_report", { session_path= [REDACTED_HIGH_ENTROPY]
    assert.equal(validateToolInput("mcp_investigation_compile_handoff", { session_path: "s" }).ok, true);
  });

--- FILE: node-mcp/test/run-tests.mjs ---
Size: 263 bytes
Summary: (none)
Content: |
  import "./contracts.test.mjs";
  import "./bridge.test.mjs";
  import "./scout-contract.test.mjs";
  import "./bridge-integration.test.mjs";
  import "./investigation-contracts.test.mjs";
  import "./active-memory-contracts.test.mjs";
  import "./tool-manifest.test.mjs";

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

--- FILE: node-mcp/test/tool-manifest.test.mjs ---
Size: 3242 bytes
Summary: (none)
Content: |
  import assert from "node:assert/strict";
  import { readFileSync } from "node:fs";
  import { resolve } from "node:path";
  import { fileURLToPath } from "node:url";
  import { test } from "node:test";
  
  import { CONTRACTS } from "../src/contracts.mjs";
  
  const manifestPath = resolve(fileURLToPath(new URL(".", import.meta.url)), "..", "..", "tool_manifest.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  
  function toolById(toolId) {
    return manifest.tools.find((tool) => tool.tool_id === toolId);
  }
  
  test("manifest entries cover public Node contracts and use valid scaffold fields", () => {
    const contractNames = new Set(CONTRACTS.map((contract) => contract.name));
    const manifestNames = new Set(manifest.tools.map((tool) => tool.tool_id));
  
    for (const name of contractNames) {
      assert.ok(manifestNames.has(name), `missing manifest entry for ${name}`);
    }
  
    for (const tool of manifest.tools) {
      assert.equal(typeof tool.tool_id, "string");
      assert.equal(typeof tool.display_name, "string");
      assert.equal(typeof tool.description, "string");
      assert.equal(typeof tool.input_schema, "object");
      assert.equal(typeof tool.dispatcher, "string");
      assert.equal(Array.isArray(tool.surfaces), true);
      assert.equal(typeof tool.default_exposed_to_lmstudio, "boolean");
      assert.equal(typeof tool.risk_level, "string");
      assert.equal(typeof tool.requires_active_partition, "boolean");
      assert.equal(typeof tool.requires_allowed_root, "boolean");
      assert.equal(typeof tool.version, "string");
      assert.ok(["read_only", "write_memory", "write_files", "admin"].includes(tool.risk_level));
      for (const surface of tool.surfaces) {
        assert.ok(["node-mcp", "fastmcp", "python-daemon", "internal"].includes(surface));
      }
      if (tool.tool_id === "mcp_agent_workflow_run") {
        assert.equal(tool.default_exposed_to_lmstudio, true);
        assert.ok(tool.output_schema);
      } else {
        assert.equal(tool.default_exposed_to_lmstudio, false);
      }
      if (tool.tool_id === "mcp_set_active_project_manual") {
        assert.equal(tool.default_exposed_to_lmstudio, false);
        assert.equal(tool.internal_only, true);
      }
    }
  });
  
  test("manifest only contains tools that are in contracts or explicitly internal", () => {
    const contractNames = new Set(CONTRACTS.map((contract) => contract.name));
    for (const tool of manifest.tools) {
      const inContracts = contractNames.has(tool.tool_id);
      const internalOnly = tool.internal_only === true;
      const internalSurfaceOnly = Array.isArray(tool.surfaces) && tool.surfaces.every((surface) => surface === "python-daemon" || surface === "internal");
      assert.ok(inContracts || internalOnly || internalSurfaceOnly, `tool ${tool.tool_id} must exist in contracts or be internal`);
    }
  });
  
  test("workflow manifest output schema is compact", () => {
    const workflow = toolById("mcp_agent_workflow_run");
    assert.ok(workflow);
    assert.equal(workflow.output_schema.type, "object");
    assert.equal(workflow.output_schema.additionalProperties, false);
    assert.deepEqual(workflow.output_schema.required, ["ok", "status", "summary", "artifacts"]);
    assert.equal(workflow.output_schema.properties.error.type.includes("null"), true);
  });

--- FILE: python-daemon/Invoke-AletheiaTool.ps1 ---
Size: 870 bytes
Summary: (none)
Content: |
  ﻿function Invoke-AletheiaTool {
    param(
      [Parameter(Mandatory=$true)][string]$ToolName,
      [Parameter(Mandatory=$true)][hashtable]$Args,
      [int]$Id = 1,
      [int]$TimeoutMs = 240000
    )
  
    $client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 8765)
    $stream = $client.GetStream()
    $stream.ReadTimeout = $TimeoutMs
    $stream.WriteTimeout = $TimeoutMs
  
    $writer = [System.IO.StreamWriter]::new($stream)
    $reader = [System.IO.StreamReader]::new($stream)
    $writer.NewLine = "`n"
    $writer.AutoFlush = $true
  
    try {
      $req = @{
        jsonrpc = "2.0"
        id = $Id
        method = "tools.call"
        params = @{
          toolName = $ToolName
          args = $Args
        }
      } | ConvertTo-Json -Depth 20 -Compress
  
      $writer.WriteLine($req)
      $line = $reader.ReadLine()
      return ($line | ConvertFrom-Json)
    }
    finally {
      $client.Close()
    }
  }

--- FILE: python-daemon/orchestrator/__init__.py ---
Size: 45 bytes
Summary: 
Content: |
  """Aletheia authoritative daemon package."""

--- FILE: python-daemon/orchestrator/agent_workflow/__init__.py ---
Size: 45 bytes
Summary: 
Content: |
  """Deterministic agent workflow helpers."""

--- FILE: python-daemon/orchestrator/skills/__init__.py ---
Size: 0 bytes
Summary: 
Content: |

--- FILE: python-daemon/pyproject.toml ---
Size: 460 bytes
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
    "jsonschema",
  ]
  
  [project.optional-dependencies]
  ocr = []
  live = []
  
  [project.scripts]
  aletheia-daemon = "orchestrator.main:main"
  aletheia-admin = "orchestrator.admin:main"
  
  [tool.pytest.ini_options]
  pythonpath = ["."]

--- FILE: tool_manifest.json ---
Size: 15448 bytes
Summary: Keys: version, tools
Content: |
  {
    "version": "0.1.0",
    "tools": [
      {
        "tool_id": "mcp_agent_workflow_run",
        "display_name": "Agent workflow run",
        "description": "Run the deterministic LM Studio-facing workflow controller.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "objective": { "type": "string", "minLength": 1 },
            "target_repo": { "type": "string", "minLength": 1 },
            "profile": { "type": "string", "enum": ["safe"], "default": "safe" },
            "allow_ingest": { "type": "boolean", "default": false },
            "include_report_preview": { "type": "boolean", "default": false },
            "use_model_phases": { "type": "boolean", "default": false }
          },
          "required": ["objective", "target_repo"]
        },
        "output_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "ok": { "type": "boolean" },
            "status": { "type": "string" },
            "run_id": { "type": "string" },
            "summary": { "type": "string" },
            "artifacts": { "type": "object" },
            "state_path": { "type": "string" },
            "error": { "type": ["object", "null"] }
          },
          "required": ["ok", "status", "summary", "artifacts"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": true,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": true,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_commit_memory",
        "display_name": "Commit active memory",
        "description": "Commit a bounded memory record to the active LM Studio partition.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "category": {
              "type": "string",
              "enum": ["architecture", "decision", "summary", "bug_fix", "preference", "artifact"]
            },
            "content": { "type": "string", "minLength": 10, "maxLength": 8000 },
            "confidence_score": { "type": "number", "minimum": 0.0, "maximum": 1.0, "default": 1.0 },
            "metadata": { "type": "object", "additionalProperties": true }
          },
          "required": ["category", "content"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "write_memory",
        "requires_active_partition": true,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_extract_image",
        "display_name": "Extract image text",
        "description": "Run OCR fallback against non-selectable text content.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "absolute_path": { "type": "string", "minLength": 1 },
            "page": { "type": "integer", "minimum": 1 },
            "region": {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "x": { "type": "integer", "minimum": 0 },
                "y": { "type": "integer", "minimum": 0 },
                "width": { "type": "integer", "minimum": 1 },
                "height": { "type": "integer", "minimum": 1 }
              },
              "required": ["x", "y", "width", "height"]
            }
          },
          "required": ["absolute_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": true,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_get_active_partition",
        "display_name": "Get active partition",
        "description": "Return the current active LM Studio partition from SQLite state.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {}
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_ingest_target",
        "display_name": "Ingest target",
        "description": "Route a local file to the ingestion pipeline by MIME type.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "project_id": { "type": "string", "minLength": 1 },
            "absolute_path": { "type": "string", "minLength": 1 },
            "mime_type": { "type": "string", "minLength": 1 },
            "force_reindex": { "type": "boolean", "default": false }
          },
          "required": ["project_id", "absolute_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "write_files",
        "requires_active_partition": false,
        "requires_allowed_root": true,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_investigation_compile_handoff",
        "display_name": "Compile investigation handoff",
        "description": "Compile investigation handoff metadata and artifact paths.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": { "session_path": { "type": "string", "minLength": 1 } },
          "required": ["session_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_investigation_filemap",
        "display_name": "Investigation file map",
        "description": "Build constrained file map summaries for an investigation session.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "session_path": { "type": "string", "minLength": 1 },
            "profile": { "type": "string", "enum": ["safe"], "default": "safe" }
          },
          "required": ["session_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_investigation_read_report",
        "display_name": "Read investigation report",
        "description": "Read bounded investigation report content from ToolSet artifacts.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "session_path": { "type": "string", "minLength": 1 },
            "artifact_key": {
              "type": "string",
              "enum": ["manifest_csv", "manifest_health_json", "manifest_doctor_json", "manifest_doctor_md", "command_lint_json", "slicer_json", "slicer_md", "final_markdown", "final_python_bundle", "archive_yaml"]
            },
            "max_chars": { "type": "integer", "minimum": 1, "maximum": 12000 }
          },
          "required": ["session_path", "artifact_key"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_investigation_start",
        "display_name": "Start investigation",
        "description": "Start a safe external ToolSet investigation session.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "objective": { "type": "string", "minLength": 1 },
            "target_repo": { "type": "string", "minLength": 1 },
            "profile": { "type": "string", "enum": ["safe"], "default": "safe" }
          },
          "required": ["objective", "target_repo"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": true,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_investigation_validate_manifest",
        "display_name": "Validate investigation manifest",
        "description": "Validate a ToolSet investigation manifest.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": { "session_path": { "type": "string", "minLength": 1 } },
          "required": ["session_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_list_memory_projects",
        "display_name": "List memory projects",
        "description": "List known LM Studio memory projects from SQLite state.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {}
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_scout_workspace",
        "display_name": "Scout workspace",
        "description": "Return a deterministic read-only workspace scout without indexing vectors.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "project_id": { "type": "string", "minLength": 1 },
            "absolute_path": { "type": "string", "minLength": 1 },
            "max_files": { "type": "integer", "minimum": 1, "maximum": 5000, "default": 500 },
            "include_summaries": { "type": "boolean", "default": true }
          },
          "required": ["project_id", "absolute_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": true,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_semantic_search",
        "display_name": "Semantic search",
        "description": "Run cosine similarity search inside an isolated project namespace.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "project_id": { "type": "string", "minLength": 1 },
            "query": { "type": "string", "minLength": 1 },
            "k": { "type": "integer", "minimum": 1, "maximum": 50, "default": 8 }
          },
          "required": ["project_id", "query"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_semantic_search_active",
        "display_name": "Active semantic search",
        "description": "Search only the active LM Studio memory partition.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "query": { "type": "string", "minLength": 1 },
            "k": { "type": "integer", "minimum": 1, "maximum": 50, "default": 8 }
          },
          "required": ["query"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": true,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_set_active_partition",
        "display_name": "Set active partition",
        "description": "Set the active LM Studio partition from a conversation path.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "conversation_path": { "type": "string", "minLength": 1 }
          },
          "required": ["conversation_path"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "write_memory",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_set_active_project_manual",
        "display_name": "Manual active project override",
        "description": "Manually override the active LM Studio project for admin/debug use.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "project_id": { "type": "string", "minLength": 1 },
            "display_name": { "type": "string", "minLength": 1 }
          },
          "required": ["project_id"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["python-daemon", "internal"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "admin",
        "requires_active_partition": false,
        "requires_allowed_root": false,
        "internal_only": true,
        "version": "0.1.0"
      },
      {
        "tool_id": "mcp_verify_integrity",
        "display_name": "Verify integrity",
        "description": "Verify a file against expected metadata and cryptographic hashes.",
        "input_schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "absolute_path": { "type": "string", "minLength": 1 },
            "expected_sha256": { "type": "string", "pattern": "^[a-fA-F0-9]{64}$" },
            "expected_metadata_hash": { "type": "string", "minLength": 1 }
          },
          "required": ["absolute_path", "expected_sha256", "expected_metadata_hash"]
        },
        "dispatcher": "python-daemon:ToolAdapters.call_mcp_tool",
        "surfaces": ["node-mcp", "fastmcp", "python-daemon"],
        "default_exposed_to_lmstudio": false,
        "risk_level": "read_only",
        "requires_active_partition": false,
        "requires_allowed_root": true,
        "version": "0.1.0"
      }
    ]
  }

--- FILE: tool_manifest.schema.json ---
Size: 1712 bytes
Summary: Keys: $schema, type, additionalProperties, required, properties
Content: |
  {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": false,
    "required": ["version", "tools"],
    "properties": {
      "version": { "type": "string", "minLength": 1 },
      "tools": {
        "type": "array",
        "items": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "tool_id",
            "display_name",
            "description",
            "input_schema",
            "dispatcher",
            "surfaces",
            "default_exposed_to_lmstudio",
            "risk_level",
            "requires_active_partition",
            "requires_allowed_root",
            "version"
          ],
          "properties": {
            "tool_id": { "type": "string", "minLength": 1 },
            "display_name": { "type": "string", "minLength": 1 },
            "description": { "type": "string", "minLength": 1 },
            "input_schema": { "type": "object" },
            "output_schema": { "type": "object" },
            "dispatcher": { "type": "string", "minLength": 1 },
            "surfaces": {
              "type": "array",
              "items": { "type": "string", "enum": ["node-mcp", "fastmcp", "python-daemon", "internal"] },
              "minItems": 1
            },
            "default_exposed_to_lmstudio": { "type": "boolean" },
            "risk_level": { "type": "string", "enum": ["read_only", "write_memory", "write_files", "admin"] },
            "requires_active_partition": { "type": "boolean" },
            "requires_allowed_root": { "type": "boolean" },
            "version": { "type": "string", "minLength": 1 },
            "notes": { "type": "string" },
            "internal_only": { "type": "boolean" }
          }
        }
      }
    }
  }

--- FILE: python-daemon/orchestrator/agent_workflow/compaction.py ---
Size: 1329 bytes
Summary: Functions: compact_tool_result
Content: |
  from __future__ import annotations
  
  from typing import Any
  
  
  def compact_tool_result(
      tool_name: str,
      raw: dict[str, Any],
      max_chars: int = 2000,
      include_content: bool = False,
  ) -> dict[str, Any]:
      payload = raw if isinstance(raw, dict) else {}
      artifacts_raw = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
      artifacts = {str(key): str(value) for key, value in artifacts_raw.items() if value is not None}
      top_candidates_raw = payload.get("top_candidates") if isinstance(payload.get("top_candidates"), list) else []
      summary = str(payload.get("summary") or payload.get("message") or payload.get("status") or tool_name)[:1000]
      compact: dict[str, Any] = {
          "ok": bool(payload.get("ok", False)),
          "status": str(payload.get("status", "ERROR")),
          "summary": summary,
          "artifacts": artifacts,
          "top_candidates": top_candidates_raw[:10],
          "recommended_next_tool": str(payload.get("recommended_next_tool", "")),
          "content_omitted": True,
      }
      if include_content and isinstance(payload.get("content"), str):
          content = str(payload["content"])
          compact["content_preview"] = content[: max(1, int(max_chars))]
          compact["content_omitted"] = len(content) > max(1, int(max_chars))
      return compact

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

--- FILE: python-daemon/tests/test_fastmcp_shim_tools.py ---
Size: 958 bytes
Summary: Classes: FastMcpShimTests; Functions: test_investigation_tools_are_declared
Content: |
  from pathlib import Path
  import unittest
  
  
  class FastMcpShimTests(unittest.TestCase):
      def test_investigation_tools_are_declared(self):
          shim_path = Path(__file__).resolve().parents[2] / "lmstudio_fastmcp_shim.py"
          source = shim_path.read_text(encoding="utf-8")
          for signature in [
              "def mcp_investigation_start(",
              "def mcp_investigation_filemap(",
              "def mcp_investigation_validate_manifest(",
              "def mcp_investigation_read_report(",
              "def mcp_investigation_compile_handoff(",
              "def mcp_agent_workflow_run(",
              "def mcp_set_active_partition(",
              "def mcp_set_active_project_manual(",
          ]:
              self.assertIn(signature, source)
  
          self.assertIn(
              'Recommended LM Studio exposure is allowed_tools = ["mcp_agent_workflow_run"].',
              source,
          )
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/tests/test_skill_selection.py ---
Size: 2219 bytes
Summary: Classes: SkillSelectionTests; Functions: test_selects_bug_triage_for_regression_even_when_tdd_plan_requested, test_selects_patch_generate_for_unified_diff_only
Content: |
  import unittest
  
  from orchestrator.skills.selection import select_skill
  
  
  class SkillSelectionTests(unittest.TestCase):
      def test_selects_bug_triage_for_regression_even_when_tdd_plan_requested(self):
          manifests = [
              {
                  "skill_id": "bug_triage_v1",
                  "triggers": ["triage bug", "regression", "diagnose"],
                  "capabilities": ["bug_triage", "tdd_planning"],
                  "risk_tier": "T1",
              },
              {
                  "skill_id": "refactor_plan_v1",
                  "triggers": ["refactor plan", "technical debt plan", "rewrite plan"],
                  "capabilities": ["refactor_planning"],
                  "risk_tier": "T1",
              },
              {
                  "skill_id": "tdd_patch_plan_v1",
                  "triggers": ["tdd plan", "patch plan", "failing test"],
                  "capabilities": ["tdd_planning"],
                  "risk_tier": "T1",
              },
          ]
  
          selected = select_skill(
              "Triage this regression: semantic search returns stale chunks after reindex. Produce a TDD plan only.",
              manifests,
          )
  
          self.assertEqual(selected["selected_skill_id"], "bug_triage_v1")
  
      def test_selects_patch_generate_for_unified_diff_only(self):
          manifests = [
              {
                  "skill_id": "patch_generate_v1",
                  "triggers": ["generate patch", "unified diff", "patch only", "create diff", "do not apply"],
                  "capabilities": ["patch_generation", "diff_only"],
                  "risk_tier": "T2",
              },
              {
                  "skill_id": "patch_apply_and_test_v1",
                  "triggers": ["apply approved patch", "run declared tests", "approved diff"],
                  "capabilities": ["approved_patch_application", "test_execution"],
                  "risk_tier": "T3",
              },
          ]
  
          selected = select_skill(
              "Generate a unified diff only. Do not apply it.",
              manifests,
          )
  
          self.assertEqual(selected["selected_skill_id"], "patch_generate_v1")
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: python-daemon/orchestrator/active_partition/models.py ---
Size: 2987 bytes
Summary: Classes: MemoryProject, ActivePartition, PartitionMappingResult, NullPartitionResult; Functions: to_dict, to_dict, to_dict, to_dict
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass, field
  from typing import Any
  
  
  @dataclass(frozen=True)
  class MemoryProject:
      project_id: str
      project_scope_hash: str
      source: str
      display_name: str
      lmstudio_folder_relpath: str | None
      allowed_roots_json: list[str] = field(default_factory=list)
      rag_enabled: bool = True
      created_at: str = ""
      last_seen_at: str = ""
  
      def to_dict(self) -> dict[str, Any]:
          return {
              "project_id": self.project_id,
              "project_scope_hash": self.project_scope_hash,
              "source": self.source,
              "display_name": self.display_name,
              "lmstudio_folder_relpath": self.lmstudio_folder_relpath,
              "allowed_roots_json": list(self.allowed_roots_json),
              "rag_enabled": self.rag_enabled,
              "created_at": self.created_at,
              "last_seen_at": self.last_seen_at,
          }
  
  
  @dataclass(frozen=True)
  class ActivePartition:
      client_id: str
      active_project_id: str | None
      active_project_scope_hash: str | None
      active_conversation_id: str | None
      conversation_path: str | None
      confidence: str
      source_event: str
      updated_at: str
  
      def to_dict(self) -> dict[str, Any]:
          return {
              "client_id": self.client_id,
              "active_project_id": self.active_project_id,
              "active_project_scope_hash": self.active_project_scope_hash,
              "active_conversation_id": self.active_conversation_id,
              "conversation_path": self.conversation_path,
              "confidence": self.confidence,
              "source_event": self.source_event,
              "updated_at": self.updated_at,
          }
  
  
  @dataclass(frozen=True)
  class PartitionMappingResult:
      ok: bool
      status: str
      message: str
      conversation_id: str
      folder_relpath: str
      project_id: str
      project_scope_hash: str
      conversation_path: str
  
      def to_dict(self) -> dict[str, Any]:
          return {
              "ok": self.ok,
              "status": self.status,
              "message": self.message,
              "conversation_id": self.conversation_id,
              "folder_relpath": self.folder_relpath,
              "project_id": self.project_id,
              "project_scope_hash": self.project_scope_hash,
              "conversation_path": self.conversation_path,
          }
  
  
  @dataclass(frozen=True)
  class NullPartitionResult:
      ok: bool = False
      status: str = "NO_ACTIVE_PARTITION"
      message: str = "No active partition available."
      conversation_id: str | None = None
      folder_relpath: str | None = None
      conversation_path: str | None = None
  
      def to_dict(self) -> dict[str, Any]:
          return {
              "ok": self.ok,
              "status": self.status,
              "message": self.message,
              "conversation_id": self.conversation_id,
              "folder_relpath": self.folder_relpath,
              "conversation_path": self.conversation_path,
          }

--- FILE: python-daemon/orchestrator/agent_workflow/policies.py ---
Size: 2721 bytes
Summary: Functions: reasoning_policy, validate_tool
Content: |
  from __future__ import annotations
  
  import os
  from typing import Any
  
  
  ALLOWED_TOOLS = {
      "mcp_agent_workflow_run",
      "mcp_commit_memory",
      "mcp_extract_image",
      "mcp_get_active_partition",
      "mcp_ingest_target",
      "mcp_investigation_compile_handoff",
      "mcp_investigation_filemap",
      "mcp_investigation_read_report",
      "mcp_investigation_start",
      "mcp_investigation_validate_manifest",
      "mcp_list_memory_projects",
      "mcp_scout_workspace",
      "mcp_semantic_search",
      "mcp_semantic_search_active",
      "mcp_set_active_partition",
      "mcp_set_active_project_manual",
      "mcp_verify_integrity",
  }
  
  RAW_SHELL_TOOLS = {"sh", "bash", "shell", "exec", "python"}
  
  REQUIRED_ARGS = {
      "mcp_agent_workflow_run": ("objective", "target_repo"),
      "mcp_commit_memory": ("category", "content"),
      "mcp_ingest_target": ("project_id", "absolute_path"),
      "mcp_investigation_compile_handoff": ("session_path",),
      "mcp_investigation_filemap": ("session_path",),
      "mcp_investigation_read_report": ("session_path", "artifact_key"),
      "mcp_investigation_start": ("objective", "target_repo"),
      "mcp_investigation_validate_manifest": ("session_path",),
      "mcp_semantic_search": ("project_id", "query"),
      "mcp_semantic_search_active": ("query",),
      "mcp_set_active_partition": ("conversation_path",),
      "mcp_set_active_project_manual": ("project_id",),
      "mcp_scout_workspace": ("project_id", "absolute_path"),
      "mcp_verify_integrity": ("absolute_path", "expected_sha256", "expected_metadata_hash"),
  }
  
  
  def reasoning_policy() -> dict[str, str]:
      return {
          "PLAN": os.getenv("ALETHEIA_AGENT_REASONING_PLAN", "low"),
          "ACT": os.getenv("ALETHEIA_AGENT_REASONING_ACT", "off"),
          "CHECK": os.getenv("ALETHEIA_AGENT_REASONING_CHECK", "low"),
          "SYNTHESIZE": os.getenv("ALETHEIA_AGENT_REASONING_SYNTHESIZE", "low"),
          "FINAL": os.getenv("ALETHEIA_AGENT_REASONING_FINAL", "off"),
      }
  
  
  def validate_tool(tool_name: str, args: dict[str, Any], allow_ingest: bool = False) -> tuple[bool, str]:
      if tool_name in RAW_SHELL_TOOLS:
          return False, f"raw shell tool rejected: {tool_name}"
      if tool_name not in ALLOWED_TOOLS:
          return False, f"tool not allowlisted: {tool_name}"
      if not isinstance(args, dict):
          return False, "tool arguments must be an object"
      if tool_name == "mcp_ingest_target" and not allow_ingest:
          return False, "mcp_ingest_target is blocked unless ingest is explicitly allowed"
  
      required = REQUIRED_ARGS.get(tool_name, ())
      missing = [name for name in required if name not in args]
      if missing:
          return False, f"missing required args: {', '.join(missing)}"
      return True, ""

--- FILE: python-daemon/orchestrator/memory/__init__.py ---
Size: 145 bytes
Summary: 
Content: |
  from .models import MemoryCommitRequest, MemoryRecord, MemorySearchResult
  from .repo import MemoryRepository
  from .service import MemoryService

--- FILE: python-daemon/orchestrator/memory/models.py ---
Size: 1841 bytes
Summary: Classes: MemoryCommitRequest, MemoryRecord, MemorySearchResult; Functions: to_dict
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass, field
  from typing import Any
  
  
  ALLOWED_MEMORY_TYPES = {
      "architecture",
      "decision",
      "summary",
      "bug_fix",
      "preference",
      "artifact",
  }
  
  
  @dataclass(frozen=True)
  class MemoryCommitRequest:
      category: str
      content: str
      confidence_score: float = 1.0
      metadata: dict[str, Any] = field(default_factory=dict)
  
  
  @dataclass(frozen=True)
  class MemoryRecord:
      memory_id: str
      project_id: str
      project_scope_hash: str
      memory_type: str
      source: str
      content: str
      content_sha1: str
      metadata_json: dict[str, Any] = field(default_factory=dict)
      confidence_score: float = 1.0
      created_at: str = ""
      index_status: str = "pending"
      indexed_at: str | None = None
      index_error: str | None = None
  
      def to_dict(self) -> dict[str, Any]:
          return {
              "memory_id": self.memory_id,
              "project_id": self.project_id,
              "project_scope_hash": self.project_scope_hash,
              "memory_type": self.memory_type,
              "source": self.source,
              "content": self.content,
              "content_sha1": self.content_sha1,
              "metadata_json": dict(self.metadata_json),
              "confidence_score": self.confidence_score,
              "created_at": self.created_at,
              "index_status": self.index_status,
              "indexed_at": self.indexed_at,
              "index_error": self.index_error,
          }
  
  
  @dataclass(frozen=True)
  class MemorySearchResult:
      memory_id: str
      project_id: str
      project_scope_hash: str
      memory_type: str
      source: str
      content: str
      content_sha1: str
      metadata_json: dict[str, Any] = field(default_factory=dict)
      confidence_score: float = 1.0
      created_at: str = ""
      distance: float | None = None

--- FILE: python-daemon/orchestrator/skills/selection.py ---
Size: 5563 bytes
Summary: Functions: tokens, meaningful_tokens, phrase_present, score_manifest, select_skill
Content: |
  from __future__ import annotations
  
  import re
  from typing import Any
  
  STOPWORDS = {
      "a",
      "an",
      "and",
      "as",
      "by",
      "do",
      "for",
      "from",
      "in",
      "into",
      "of",
      "on",
      "only",
      "or",
      "the",
      "this",
      "to",
      "with",
      "plan",
      "produce",
      "create",
      "write",
  }
  
  INTENT_HINTS: dict[str, set[str]] = {
      "bug_triage_v1": {
          "bug",
          "regression",
          "triage",
          "diagnose",
          "root",
          "cause",
          "failing",
          "failure",
          "stale",
          "broken",
          "reproduce",
          "reproduction",
      },
      "candidate_analysis_v1": {
          "candidate",
          "candidates",
          "rank",
          "likely",
          "files",
          "functions",
          "where",
          "change",
      },
      "tdd_patch_plan_v1": {
          "tdd",
          "red",
          "green",
          "refactor",
          "test",
          "tests",
          "failing",
          "vertical",
          "slice",
      },
      "patch_generate_v1": {
          "generate",
          "patch",
          "diff",
          "unified",
          "do",
          "not",
          "apply",
      },
      "patch_apply_and_test_v1": {
          "apply",
          "approved",
          "patch",
          "diff",
          "run",
          "tests",
      },
      "architecture_review_v1": {
          "architecture",
          "review",
          "coupling",
          "boundary",
          "boundaries",
          "modules",
          "testability",
      },
      "refactor_plan_v1": {
          "refactor",
          "refactoring",
          "technical",
          "debt",
          "phased",
          "rewrite",
          "remediation",
      },
      "conversation_summary_ingest_v1": {
          "conversation",
          "summary",
          "summarize",
          "memory",
          "commit",
          "ingest",
      },
      "skill_crystallize_v1": {
          "crystallize",
          "skill",
          "sop",
          "manifest",
          "candidate",
      },
      "git_guardrails_v1": {
          "git",
          "push",
          "commit",
          "reset",
          "clean",
          "destructive",
          "secret",
          "deploy",
      },
  }
  
  
  def tokens(text: str) -> set[str]:
      return set(re.findall(r"[a-z0-9_]+", text.lower()))
  
  
  def meaningful_tokens(text: str) -> set[str]:
      return {token for token in tokens(text) if token not in STOPWORDS and len(token) > 1}
  
  
  def phrase_present(phrase: str, objective_l: str) -> bool:
      return phrase.lower() in objective_l
  
  
  def score_manifest(objective: str, manifest: dict[str, Any]) -> dict[str, Any]:
      objective_l = objective.lower()
      objective_tokens = meaningful_tokens(objective)
  
      trigger_hits: list[str] = []
      capability_hits: list[str] = []
      intent_hits: list[str] = []
  
      score = 0
  
      for trigger in manifest.get("triggers", []):
          trigger_l = trigger.lower()
          trigger_tokens = meaningful_tokens(trigger)
  
          if phrase_present(trigger_l, objective_l):
              trigger_hits.append(trigger)
              score += 8
              continue
  
          if not trigger_tokens:
              continue
  
          overlap = trigger_tokens.intersection(objective_tokens)
          overlap_ratio = len(overlap) / max(1, len(trigger_tokens))
  
          # Require a strong partial trigger match. This prevents weak words like
          # "plan" from making "refactor plan" win every planning objective.
          if len(overlap) >= 2 and overlap_ratio >= 0.67:
              trigger_hits.append(trigger)
              score += 4
  
      for capability in manifest.get("capabilities", []):
          capability_tokens = meaningful_tokens(capability.replace("_", " "))
          overlap = capability_tokens.intersection(objective_tokens)
          if capability.lower() in objective_l:
              capability_hits.append(capability)
              score += 4
          elif capability_tokens and len(overlap) >= 2:
              capability_hits.append(capability)
              score += 2
  
      skill_id = manifest["skill_id"]
      for hint in INTENT_HINTS.get(skill_id, set()):
          if hint in objective_tokens:
              intent_hits.append(hint)
  
      score += len(intent_hits)
  
      # Small, explicit bias: if the objective asks to triage/diagnose a regression,
      # prefer bug_triage over downstream planning skills.
      if skill_id == "bug_triage_v1" and {"triage", "regression"}.intersection(objective_tokens):
          score += 6
  
      # If the objective says "TDD plan" but also says "triage/regression",
      # keep TDD as a candidate but do not let generic "plan" dominate.
      if skill_id == "tdd_patch_plan_v1" and "tdd" in objective_tokens:
          score += 4
  
      return {
          "skill_id": skill_id,
          "score": score,
          "trigger_hits": trigger_hits,
          "capability_hits": capability_hits,
          "intent_hits": sorted(intent_hits),
          "risk_tier": manifest["risk_tier"],
      }
  
  
  def select_skill(objective: str, manifests: list[dict[str, Any]]) -> dict[str, Any] | None:
      ranked = [score_manifest(objective, manifest) for manifest in manifests]
      ranked = [candidate for candidate in ranked if candidate["score"] > 0]
      ranked.sort(key=lambda item: (-item["score"], item["risk_tier"], item["skill_id"]))
  
      if not ranked:
          return None
  
      return {
          "selected_skill_id": ranked[0]["skill_id"],
          "candidate_analysis": ranked[:5],
      }

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

--- FILE: python-daemon/orchestrator/active_partition/__init__.py ---
Size: 221 bytes
Summary: 
Content: |
  from .mapper import PartitionMapper
  from .models import ActivePartition, MemoryProject, NullPartitionResult, PartitionMappingResult
  from .repo import ActivePartitionRepository
  from .service import ActivePartitionService

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

--- FILE: python-daemon/orchestrator/skills/executor.py ---
Size: 1885 bytes
Summary: Classes: SkillPolicyError; Functions: enforce_manifest_policy, load_skill_instructions, build_skill_context
Content: |
  from __future__ import annotations
  
  from pathlib import Path
  from typing import Any
  
  from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
  
  class SkillPolicyError(ValueError):
      pass
  
  def enforce_manifest_policy(manifest: dict[str, Any]) -> None:
      for tool_name in manifest.get("allowed_tools", []):
          if tool_name not in ALLOWED_TOOLS:
              raise SkillPolicyError(f"skill allows unknown tool: {tool_name}")
  
      risk_tier = manifest["risk_tier"]
      approvals = manifest["approval_requirements"]
  
      if risk_tier == "T3":
          if approvals.get("requires_user_approval") is not True:
              raise SkillPolicyError("T3 skill requires user approval")
          if approvals.get("requires_diff_approval") is not True:
              raise SkillPolicyError("T3 skill requires diff approval")
  
  def load_skill_instructions(manifest: dict[str, Any]) -> str:
      source_path = Path(manifest["source_path"])
      skill_dir = source_path.parent
  
      for entrypoint in manifest.get("tool_entrypoints", []):
          if entrypoint["entrypoint_type"] == "instruction_only":
              target = skill_dir / entrypoint["target"]
              return target.read_text(encoding="utf-8")
  
      raise SkillPolicyError("no instruction_only entrypoint found")
  
  def build_skill_context(manifest: dict[str, Any], *, include_instructions: bool = True) -> dict[str, Any]:
      enforce_manifest_policy(manifest)
  
      context = {
          "skill_id": manifest["skill_id"],
          "risk_tier": manifest["risk_tier"],
          "allowed_tools": manifest.get("allowed_tools", []),
          "approval_requirements": manifest["approval_requirements"],
          "artifacts_produced": manifest.get("artifacts_produced", []),
      }
  
      if include_instructions:
          context["instructions"] = load_skill_instructions(manifest)
  
      return context

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
Size: 4589 bytes
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
      lmstudio_conversations_dir: Path
      enable_lmstudio_watcher: bool
      active_partition_null_policy: str
      active_partition_settle_ms: int
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
      skill_registry_root: Path | None
  
      @classmethod
      def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeConfig":
          env = env or os.environ
          project_root = Path(env.get("ALETHEIA_PROJECT_ROOT", Path.cwd())).resolve()
          project_id = env.get("ALETHEIA_PROJECT_ID", project_root.name)
          state_dir = Path(env.get("ALETHEIA_STATE_DIR", project_root / ".aletheia_state")).resolve()
          allowed_roots_raw = env.get("ALETHEIA_ALLOWED_ROOTS", str(project_root))
          allowed_roots = tuple(Path(part).resolve() for part in allowed_roots_raw.split(";") if part.strip())
          user_profile = Path(env.get("USERPROFILE", str(Path.home()))).expanduser()
          lmstudio_conversations_dir = Path(
              env.get("ALETHEIA_LMSTUDIO_CONVERSATIONS_DIR", str(user_profile / ".lmstudio" / "conversations"))
          ).expanduser().resolve()
          enable_lmstudio_watcher = env.get("ALETHEIA_ENABLE_LMSTUDIO_WATCHER", "false").lower() == "true"
          active_partition_null_policy = env.get("ALETHEIA_ACTIVE_PARTITION_NULL_POLICY", "deny")
          active_partition_settle_ms = int(env.get("ALETHEIA_ACTIVE_PARTITION_SETTLE_MS", "750"))
          enable_admin_bridge = env.get("ALETHEIA_ENABLE_ADMIN_BRIDGE", "false").lower() == "true"
          lm_studio_base_url = env.get("ALETHEIA_LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
          lm_studio_api_base_url = env.get(
              "ALETHEIA_LM_STUDIO_API_BASE_URL",
              lm_studio_base_url.rstrip("/").replace("/v1", "/api/v1") if "/v1" in lm_studio_base_url else "http= [REDACTED_HIGH_ENTROPY]
          )
          lm_studio_api_token = [REDACTED_HIGH_ENTROPY]
          auto_load_embedding_model = env.get("ALETHEIA_AUTO_LOAD_EMBEDDING_MODEL", "true").lower() == "true"
          
          skill_registry_root_raw = env.get("ALETHEIA_SKILL_REGISTRY_ROOT")
          skill_registry_root = Path(skill_registry_root_raw).resolve() if skill_registry_root_raw else None
          
          return cls(
              project_root=project_root,
              project_id=project_id,
              state_dir=state_dir,
              allowed_roots=allowed_roots or (project_root,),
              lmstudio_conversations_dir=lmstudio_conversations_dir,
              enable_lmstudio_watcher=enable_lmstudio_watcher,
              active_partition_null_policy=active_partition_null_policy,
              active_partition_settle_ms=active_partition_settle_ms,
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
              skill_registry_root=skill_registry_root,
          )

--- FILE: python-daemon/orchestrator/db_bootstrap.py ---
Size: 10435 bytes
Summary: Functions: _queue_migration_0003, bootstrap_databases, _apply_migrations
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
  
  
  QUEUE_MIGRATION_0002 = """
  PRAGMA journal_mode = WAL;
  PRAGMA synchronous = NORMAL;
  PRAGMA busy_timeout = 5000;
  PRAGMA foreign_keys = ON;
  
  CREATE TABLE IF NOT EXISTS memory_projects (
    project_id TEXT NOT NULL,
    project_scope_hash TEXT NOT NULL PRIMARY KEY,= [REDACTED_HIGH_ENTROPY]
    source TEXT NOT NULL,
    display_name TEXT NOT NULL,
    lmstudio_folder_relpath TEXT,
    allowed_roots_json TEXT NOT NULL DEFAULT '[]',
    rag_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_memory_projects_project_id
    ON memory_projects(project_id);
  
  CREATE TABLE IF NOT EXISTS active_partitions (
    client_id TEXT NOT NULL PRIMARY KEY,
    active_project_id TEXT,
    active_project_scope_hash TEXT,
    active_conversation_id TEXT,
    conversation_path TEXT,
    confidence TEXT NOT NULL,
    source_event TEXT NOT NULL,
    updated_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_active_partitions_scope_hash
    ON active_partitions(active_project_scope_hash);
  
  CREATE TABLE IF NOT EXISTS conversation_events (
    event_id TEXT NOT NULL PRIMARY KEY,
    project_scope_hash TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_conversation_events_project_scope_hash
    ON conversation_events(project_scope_hash);
  
  CREATE INDEX IF NOT EXISTS idx_conversation_events_session_id
    ON conversation_events(session_id);
  
  CREATE TABLE IF NOT EXISTS memory_records (
    memory_id TEXT NOT NULL PRIMARY KEY,
    project_id TEXT NOT NULL,
    project_scope_hash TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha1 TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    confidence_score REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_memory_records_project_scope_hash
    ON memory_records(project_scope_hash);
  
  CREATE INDEX IF NOT EXISTS idx_memory_records_memory_type
    ON memory_records(memory_type);
  
  CREATE INDEX IF NOT EXISTS idx_memory_records_project_scope_type
    ON memory_records(project_scope_hash, memory_type);
  """
  
  
  def _queue_migration_0003(conn: sqlite3.Connection) -> None:
      existing = {row[1] for row in conn.execute("PRAGMA table_info(memory_records)").fetchall()}
      if "index_status" not in existing:
          conn.execute("ALTER TABLE memory_records ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'")
      if "indexed_at" not in existing:
          conn.execute("ALTER TABLE memory_records ADD COLUMN indexed_at TEXT")
      if "index_error" not in existing:
          conn.execute("ALTER TABLE memory_records ADD COLUMN index_error TEXT")
      conn.execute(
          "CREATE INDEX IF NOT EXISTS idx_memory_records_index_status ON memory_records(index_status)"
      )
  
  
  QUEUE_MIGRATION_0004 = """
  PRAGMA journal_mode = WAL;
  PRAGMA synchronous = NORMAL;
  PRAGMA busy_timeout = 5000;
  PRAGMA foreign_keys = ON;
  
  CREATE TABLE IF NOT EXISTS skill_manifests (
    skill_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    project_scope_hash TEXT,
    manifest_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('verified', 'quarantined', 'disabled')),
    source_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  ) STRICT, WITHOUT ROWID;
  
  CREATE INDEX IF NOT EXISTS idx_skill_manifests_status
  ON skill_manifests(status);
  
  CREATE INDEX IF NOT EXISTS idx_skill_manifests_project_scope_hash
  ON skill_manifests(project_scope_hash);
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
  
  
  QUEUE_MIGRATIONS = (
      ("0001_initial", QUEUE_MIGRATION_0001),
      ("0002_active_partition_memory", QUEUE_MIGRATION_0002),
      ("0003_memory_index_state", None),
      ("0004_skill_manifests", QUEUE_MIGRATION_0004),  # noqa: F821
  )
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
          if version == "0003_memory_index_state":
              _queue_migration_0003(conn)
          else:
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

--- FILE: python-daemon/orchestrator/skills/schema.py ---
Size: 2102 bytes
Summary: Classes: SkillManifestError; Functions: load_json, validate_skill_manifest, _validate_backend_policy
Content: |
  from __future__ import annotations
  
  import json
  from pathlib import Path
  from typing import Any
  
  from jsonschema import Draft7Validator
  
  class SkillManifestError(ValueError):
      pass
  
  def load_json(path: Path) -> dict[str, Any]:
      return json.loads(path.read_text(encoding="utf-8"))
  
  def validate_skill_manifest(manifest_path: Path, registry_root: Path) -> dict[str, Any]:
      manifest = load_json(manifest_path)
      schema = load_json(registry_root / "manifest.schema.json")
  
      Draft7Validator.check_schema(schema)
      validator = Draft7Validator(schema)
      errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))
  
      if errors:
          messages = [
              f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
              for error in errors
          ]
          raise SkillManifestError("; ".join(messages))
  
      _validate_backend_policy(manifest, manifest_path)
      return manifest
  
  def _validate_backend_policy(manifest: dict[str, Any], manifest_path: Path) -> None:
      for schema_key in ("inputs_schema", "outputs_schema"):
          schema = manifest[schema_key]
          if schema.get("type") != "object":
              raise SkillManifestError(f"{schema_key} must be object schema")
          if schema.get("additionalProperties") is not False:
              raise SkillManifestError(f"{schema_key} must set additionalProperties=false")
  
      for entrypoint in manifest.get("tool_entrypoints", []):
          if entrypoint["entrypoint_type"] == "instruction_only":
              target = manifest_path.parent / entrypoint["target"]
              if not target.exists():
                  raise SkillManifestError(f"missing instruction target: {target}")
  
      if manifest["risk_tier"] == "T3":
          approvals = manifest["approval_requirements"]
          if approvals.get("requires_user_approval") is not True:
              raise SkillManifestError("T3 skills require user approval")
          if approvals.get("requires_diff_approval") is not True:
              raise SkillManifestError("T3 skills require diff approval")

--- FILE: python-daemon/tests/test_active_partition_mapper.py ---
Size: 2372 bytes
Summary: Classes: ActivePartitionMapperTests; Functions: test_folder_path_maps_to_deterministic_project_id_and_scope_hash, test_nested_folders_produce_distinct_partitions, test_root_level_conversation_requires_project_folder
Content: |
  from __future__ import annotations
  
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.active_partition.mapper import PartitionMapper
  
  
  class ActivePartitionMapperTests(unittest.TestCase):
      def test_folder_path_maps_to_deterministic_project_id_and_scope_hash(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp) / "conversations"
              folder = root / "testing folder 2"
              folder.mkdir(parents=True)
              conversation = folder / "chat.conversation.json"
              conversation.write_text("{}", encoding="utf-8")
  
              result1 = PartitionMapper(root).map(conversation)
              result2 = PartitionMapper(root).map(conversation)
  
              self.assertTrue(result1.ok)
              self.assertEqual(result1.project_id, "lmstudio-testing-folder-2")
              self.assertEqual(result1.project_scope_hash, result2.project_scope_hash)
  
      def test_nested_folders_produce_distinct_partitions(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp) / "conversations"
              nested_a = root / "client-a" / "backend-debug"
              nested_b = root / "client-a" / "backend-debug-v2"
              nested_a.mkdir(parents=True)
              nested_b.mkdir(parents=True)
              path_a = nested_a / "chat.conversation.json"
              path_b = nested_b / "chat.conversation.json"
              path_a.write_text("{}", encoding="utf-8")
              path_b.write_text("{}", encoding="utf-8")
  
              result_a = PartitionMapper(root).map(path_a)
              result_b = PartitionMapper(root).map(path_b)
  
              self.assertTrue(result_a.ok)
              self.assertTrue(result_b.ok)
              self.assertNotEqual(result_a.project_id, result_b.project_id)
              self.assertNotEqual(result_a.project_scope_hash, result_b.project_scope_hash)
  
      def test_root_level_conversation_requires_project_folder(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp) / "conversations"
              root.mkdir(parents=True)
              conversation = root / "chat.conversation.json"
              conversation.write_text("{}", encoding="utf-8")
  
              result = PartitionMapper(root).map(conversation)
  
              self.assertFalse(result.ok)
              self.assertEqual(result.status, "NEEDS_PROJECT_FOLDER")

--- FILE: python-daemon/orchestrator/active_partition/mapper.py ---
Size: 2356 bytes
Summary: Classes: PartitionMapper; Functions: __init__, map, _project_id_from_relpath
Content: |
  from __future__ import annotations
  
  import hashlib
  import json
  import re
  from pathlib import Path
  
  from .models import NullPartitionResult, PartitionMappingResult
  
  
  class PartitionMapper:
      def __init__(self, lmstudio_conversations_root: str | Path) -> None:
          self.lmstudio_conversations_root = Path(lmstudio_conversations_root).expanduser().resolve()
  
      def map(self, conversation_json_path: str | Path) -> PartitionMappingResult | NullPartitionResult:
          conversation_path = Path(conversation_json_path).expanduser().resolve()
          if not conversation_path.is_relative_to(self.lmstudio_conversations_root):
              return NullPartitionResult(
                  status="POLICY_BLOCK",
                  message="Conversation path must be under the configured LM Studio conversations root.",
                  conversation_path=str(conversation_path),
              )
          conversation_id = conversation_path.stem
          folder_relpath = conversation_path.parent.relative_to(self.lmstudio_conversations_root)
          folder_relpath_text = "" if str(folder_relpath) in {"", "."} else folder_relpath.as_posix()
          if not folder_relpath_text:
              return NullPartitionResult(
                  status="NEEDS_PROJECT_FOLDER",
                  message="Move this chat into an LM Studio folder to enable persistent project memory.",
                  conversation_id=conversation_id,
                  folder_relpath="",
                  conversation_path=str(conversation_path),
              )
          project_id = self._project_id_from_relpath(folder_relpath_text)
          project_scope_hash = hashlib.sha1(
              json.dumps({"project_id": project_id}, sort_keys= [REDACTED_HIGH_ENTROPY]
          ).hexdigest()
          return PartitionMappingResult(
              ok=True,
              status="MAPPED",
              message="Conversation mapped to active partition.",
              conversation_id=conversation_id,
              folder_relpath=folder_relpath_text,
              project_id=project_id,
              project_scope_hash=project_scope_hash,
              conversation_path=str(conversation_path),
          )
  
      def _project_id_from_relpath(self, folder_relpath: str) -> str:
          normalized = re.sub(r"[^a-z0-9]+", "-", folder_relpath.lower()).strip("-")
          return f"lmstudio-{normalized or 'project'}"

--- FILE: python-daemon/orchestrator/agent_workflow_cli.py ---
Size: 1710 bytes
Summary: Functions: main
Content: |
  from __future__ import annotations
  
  import argparse
  import json
  import sys
  from pathlib import Path
  
  from .agent_workflow.mcp_tool import run_agent_workflow
  
  
  def main(argv: list[str] | None = None) -> int:
      parser = argparse.ArgumentParser(description="Run the deterministic Aletheia agent workflow.")
      parser.add_argument("--objective", required=True)
      parser.add_argument("--target-repo", required=True)
      parser.add_argument("--profile", default="safe")
      parser.add_argument("--allow-ingest", action="store_true", default=False)
      parser.add_argument("--include-report-preview", action="store_true", default=False)
      parser.add_argument("--use-model-phases", action="store_true", default=False)
      parser.add_argument("--state-dir", type=Path)
      args = parser.parse_args(argv)
  
      result = run_agent_workflow(
          objective=args.objective,
          target_repo=args.target_repo,
          profile=args.profile,
          allow_ingest=args.allow_ingest,
          include_report_preview=args.include_report_preview,
          use_model_phases=args.use_model_phases,
          state_dir=args.state_dir,
      )
  
      artifact_paths = []
      for value in (result.get("artifacts") or {}).values():
          if isinstance(value, str) and value not in artifact_paths:
              artifact_paths.append(value)
  
      print(f"run_id: {result.get('run_id', '')}")
      print(f"final_status: {result.get('status', '')}")
      print(f"summary: {result.get('summary', '')}")
      print(f"artifact_paths: {json.dumps(artifact_paths, ensure_ascii=False)}")
      print(result.get("state_path", ""))
      return 0 if result.get("ok", False) else 1
  
  
  if __name__ == "__main__":
      raise SystemExit(main(sys.argv[1:]))

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

--- FILE: python-daemon/orchestrator/skills/importer.py ---
Size: 1657 bytes
Summary: Classes: SkillImporter; Functions: __init__, import_all
Content: |
  from __future__ import annotations
  
  import json
  from pathlib import Path
  from typing import Any
  
  from .registry import SkillRegistry
  from .schema import SkillManifestError, validate_skill_manifest
  
  class SkillImporter:
      def __init__(self, registry_root: Path, registry: SkillRegistry) -> None:
          self.registry_root = Path(registry_root)
          self.registry = registry
  
      def import_all(self) -> dict[str, Any]:
          skills_dir = self.registry_root / "skills"
          report: dict[str, Any] = {
              "ok": True,
              "verified": [],
              "quarantined": [],
              "registry_root": str(self.registry_root),
          }
  
          if not skills_dir.exists():
              report["ok"] = False
              report["error"] = f"skills directory not found: {skills_dir}"
              return report
  
          for manifest_path in sorted(skills_dir.glob("*/skill.json")):
              skill_id = manifest_path.parent.name
              raw = None
  
              try:
                  raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                  manifest = validate_skill_manifest(manifest_path, self.registry_root)
                  self.registry.upsert_verified(manifest, manifest_path)
                  report["verified"].append(manifest["skill_id"])
  
              except Exception as exc:
                  report["ok"] = False
                  self.registry.quarantine(skill_id, manifest_path, str(exc), raw)
                  report["quarantined"].append({
                      "skill_id": skill_id,
                      "reason": str(exc),
                  })
  
          return report

--- FILE: python-daemon/orchestrator/tool_assist_adapter.py ---
Size: 7580 bytes
Summary: Classes: ToolAssistAdapterError, ToolAssistAdapter; Functions: __init__, __init__, _error, _normalize, _load_backend_api, _session_allowed, _policy_block, _invoke, investigation_start, investigation_filemap, investigation_validate_manifest, investigation_read_report, investigation_compile_handoff
Content: |
  from __future__ import annotations
  
  import importlib
  import os
  import sys
  from pathlib import Path
  from typing import Any
  _UNSET = object()
  
  class ToolAssistAdapterError(RuntimeError):
      def __init__(self, code: str, message: str) -> None:
          super().__init__(message)
          self.code = code
          self.message = message
  
  
  class ToolAssistAdapter:
      def __init__(self, toolset_root: str | None | object = _UNSET, lta_output_root: str | None = None) -> None:
          if toolset_root is _UNSET:
              configured_root = os.getenv("TOOLSET_ROOT")
          else:
              configured_root = toolset_root
  
          self.toolset_root = (
              Path(configured_root).expanduser().resolve()
              if configured_root
              else None
          )
          self.lta_output_root = lta_output_root or os.getenv("LTA_OUTPUT_ROOT")
          self._backend_api: Any | None = None
  
      def _error(self, code: str, summary: str, status: str = "ERROR") -> dict[str, Any]:
          return {
              "ok": False,
              "status": status,
              "summary": summary,
              "artifacts": {},
              "top_candidates": [],
              "recommended_next_tool": "",
              "error": {"code": code, "message": summary},
          }
  
      def _normalize(self, response: Any, include_content_chars: int | None = None) -> dict[str, Any]:
          if not isinstance(response, dict):
              return self._error("toolset_call_failed", "ToolSet returned a non-object response.")
          raw_artifacts = response.get("artifacts") if isinstance(response.get("artifacts"), dict) else {}
          artifacts = {str(k): str(v) for k, v in raw_artifacts.items() if isinstance(k, str) and isinstance(v, str)}
          raw_candidates = response.get("top_candidates") if isinstance(response.get("top_candidates"), list) else []
          summary = str(response.get("summary", ""))[:2000]
          normalized: dict[str, Any] = {
              "ok": bool(response.get("ok", False)),
              "status": str(response.get("status", "ERROR")),
              "summary": summary,
              "artifacts": artifacts,
              "top_candidates": raw_candidates[:10],
              "recommended_next_tool": str(response.get("recommended_next_tool", "")),
          }
          raw_error = response.get("error")
          if isinstance(raw_error, dict):
              normalized["error"] = {
                  "code": str(raw_error.get("code", "toolset_error")),
                  "message": str(raw_error.get("message", summary))[:2000],
              }
          elif isinstance(raw_error, str):
              normalized["error"] = {"code": "toolset_error", "message": raw_error[:2000]}
  
          if include_content_chars is not None and isinstance(response.get("content"), str):
              normalized["content"] = response["content"][: max(1, include_content_chars)]
          return normalized
  
      def _load_backend_api(self) -> Any:
          if self._backend_api is not None:
              return self._backend_api
          if self.toolset_root is None:
              raise ToolAssistAdapterError("missing_toolset_root", "TOOLSET_ROOT is required for investigation tools.")
          if not self.toolset_root.exists():
              raise ToolAssistAdapterError("toolset_root_not_found", f"TOOLSET_ROOT does not exist: {self.toolset_root}")
          pkg_root = self.toolset_root / "local_tool_assist_mcp"
          if not pkg_root.exists():
              raise ToolAssistAdapterError("toolset_layout_invalid", "TOOLSET_ROOT must contain local_tool_assist_mcp.")
          if str(self.toolset_root) not in sys.path:
              sys.path.insert(0, str(self.toolset_root))
          try:
              self._backend_api = importlib.import_module("local_tool_assist_mcp.backend_api")
          except ModuleNotFoundError as exc:
              if exc.name == "local_tool_assist_mcp.backend_api":
                  raise ToolAssistAdapterError(
                      "missing_backend_api",
                      "ToolSet is missing local_tool_assist_mcp/backend_api.py; add this stable API module in ToolSet.",
                  ) from exc
              raise
          return self._backend_api
  
      def _session_allowed(self, session_path: str) -> bool:
          path = Path(session_path).expanduser().resolve()
          if self.lta_output_root:
              root = Path(self.lta_output_root).expanduser().resolve()
              return path == root or root in path.parents
          if self.toolset_root is not None and self.toolset_root.exists():
              root = (self.toolset_root / "local_tool_assist_outputs").resolve()
              return path == root or root in path.parents
          return True
  
      def _policy_block(self) -> dict[str, Any]:
          msg = "session_path is outside the configured Tool Assist output root."
          return {
              "ok": False,
              "status": "POLICY_BLOCK",
              "summary": msg,
              "artifacts": {},
              "top_candidates": [],
              "recommended_next_tool": "",
              "error": {"code": "session_path_outside_output_root", "message": msg},
          }
  
      def _invoke(self, method_name: str, include_content_chars: int | None = None, **kwargs: Any) -> dict[str, Any]:
          try:
              backend_api = self._load_backend_api()
              method = getattr(backend_api, method_name, None)
              if method is None:
                  raise ToolAssistAdapterError("missing_backend_api_method", f"ToolSet backend_api missing method: {method_name}")
              return self._normalize(method(**kwargs), include_content_chars=include_content_chars)
          except ToolAssistAdapterError as exc:
              return self._error(exc.code, exc.message)
          except Exception as exc:
              return self._error("toolset_call_failed", f"ToolSet call failed: {exc}")
  
      def investigation_start(self, objective: str, target_repo: str, profile: str = "safe") -> dict[str, Any]:
          kwargs = {"objective": objective, "target_repo": target_repo, "profile": profile}
          if self.lta_output_root:
              kwargs["output_root"] = self.lta_output_root
          return self._invoke("create_session", **kwargs)
  
      def investigation_filemap(self, session_path: str, profile: str = "safe") -> dict[str, Any]:
          if not self._session_allowed(session_path):
              return self._policy_block()
          return self._invoke("scan_directory", session_path=session_path, profile=profile)
  
      def investigation_validate_manifest(self, session_path: str) -> dict[str, Any]:
          if not self._session_allowed(session_path):
              return self._policy_block()
          return self._invoke("validate_manifest", session_path=session_path)
  
      def investigation_read_report(self, session_path: str, artifact_key: str, max_chars: int = [REDACTED_HIGH_ENTROPY]
          if not self._session_allowed(session_path):
              return self._policy_block()
          capped_chars = max(1, min(int(max_chars), 12000))
          return self._invoke(
              "read_report",
              session_path=session_path,
              artifact_key=artifact_key,
              max_chars=capped_chars,
              include_content_chars=capped_chars,
          )
  
      def investigation_compile_handoff(self, session_path: str) -> dict[str, Any]:
          if not self._session_allowed(session_path):
              return self._policy_block()
          return self._invoke("compile_handoff_report", session_path=session_path)

--- FILE: python-daemon/orchestrator/agent_workflow/state.py ---
Size: 2177 bytes
Summary: Classes: WorkflowState; Functions: utc_now_iso, default_state_dir, to_dict, save
Content: |
  from __future__ import annotations
  
  import json
  import os
  from dataclasses import asdict, dataclass, field
  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any
  
  
  def utc_now_iso() -> str:
      return datetime.now(timezone.utc).isoformat()
  
  
  def default_state_dir() -> Path:
      agent_state = os.getenv("ALETHEIA_AGENT_STATE_DIR")
      if agent_state:
          return Path(agent_state).expanduser().resolve()
      base_state = os.getenv("ALETHEIA_STATE_DIR")
      if base_state:
          return Path(base_state).expanduser().resolve() / "agent_workflows"
      return (Path.cwd() / ".aletheia_state" / "agent_workflows").resolve()
  
  
  @dataclass
  class WorkflowState:
      run_id: str
      created_at: str
      user_prompt: str
      goal: str = ""
      phase: str = "PLAN"
      todos: list[dict[str, Any]] = field(default_factory=list)
      artifacts: dict[str, str] = field(default_factory=dict)
      tool_results: list[dict[str, Any]] = field(default_factory=list)
      reasoning_policy: dict[str, Any] = field(default_factory=dict)
      selected_skill: dict[str, Any] | None = None
      warnings: list[dict[str, Any]] = field(default_factory=list)
      errors: list[dict[str, Any]] = field(default_factory=list)
      final_summary: str = ""
  
      def to_dict(self) -> dict[str, Any]:
          data = asdict(self)
          data["todos"] = [dict(item) for item in self.todos]
          data["artifacts"] = dict(self.artifacts)
          data["tool_results"] = [dict(item) for item in self.tool_results]
          data["reasoning_policy"] = dict(self.reasoning_policy)
          data["selected_skill"] = dict(self.selected_skill) if isinstance(self.selected_skill, dict) else None
          data["warnings"] = [dict(item) for item in self.warnings]
          data["errors"] = [dict(item) for item in self.errors]
          return data
  
      def save(self, state_dir: Path | None = None) -> Path:
          root = Path(state_dir) if state_dir is not None else default_state_dir()
          root.mkdir(parents=True, exist_ok=True)
          path = root / f"{self.run_id}.json"
          path.write_text(json.dumps(self.to_dict(), indent= [REDACTED_HIGH_ENTROPY]
          return path

--- FILE: python-daemon/orchestrator/lm_studio_manager.py ---
Size: 6988 bytes
Summary: Classes: LMStudioManagerError, LMStudioModel, LMStudioManagerConfig, LMStudioManager; Functions: __init__, _logger, _headers, list_models, find_model, connection_summary, get_loaded_instances, is_model_loaded, ensure_embedding_model_loaded
Content: |
  from __future__ import annotations
  
  import logging
  import threading
  from dataclasses import dataclass
  from dataclasses import field
  from typing import Any, Callable
  import requests
  
  
  class LMStudioManagerError(ValueError):
      pass
  
  
  @dataclass(frozen=True)
  class LMStudioModel:
      key: str
      type: str
      state: str | None = None
      loaded_instances: list[dict[str, Any]] = field(default_factory=list)
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
          self._embedding_load_lock = threading.Lock()
  
      @property
      def _logger(self) -> logging.Logger:
          return logging.getLogger(__name__)
  
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
                  loaded_instances = item.get("loaded_instances") or []
                  models.append(
                      LMStudioModel(
                          key=key,
                          type=item.get("type", "unknown"),
                          state=item.get("state"),
                          loaded_instances=[dict(instance) for instance in loaded_instances if isinstance(instance, dict)],
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
  
      def connection_summary(self) -> dict[str, Any]:
          return {
              "api_base_url": self.config.api_base_url,
              "token_present": bool(self.config.api_token),
              "request_timeout_seconds": self.config.request_timeout_seconds,
          }
  
      def get_loaded_instances(self, model_key: str) -> list[dict[str, Any]]:
          model = self.find_model(model_key)
          if model is None:
              raise LMStudioManagerError(f"embedding model not found in LM Studio: {model_key}")
          return list(model.loaded_instances or [])
  
      def is_model_loaded(self, model_key: str) -> bool:
          model = self.find_model(model_key)
          if model is None:
              return False
          return bool(model.loaded_instances) or model.state in {"loaded", "running", "ready"}
  
      def ensure_embedding_model_loaded(self, model_key: str) -> None:
          with self._embedding_load_lock:
              model = self.find_model(model_key)
              if model is None:
                  raise LMStudioManagerError(f"embedding model not found in LM Studio: {model_key}")
              if model.type not in {"embedding", "embeddings"}:
                  raise LMStudioManagerError(f"configured embedding model is not an embedding model: {model_key} (type: {model.type})")
  
              loaded_instances = list(model.loaded_instances or [])
              loaded_count = len(loaded_instances)
              self._logger.debug(
                  "LM Studio embedding readiness check model=%s loaded_instances=%d token_present=%s",
                  model_key,
                  loaded_count,
                  bool(self.config.api_token),
              )
              if loaded_count > 1:
                  self._logger.warning(
                      "LM Studio embedding model %s has multiple loaded instances (%d); skipping reload",
                      model_key,
                      loaded_count,
                  )
              if loaded_count > 0 or model.state in {"loaded", "running", "ready"}:
                  self._logger.debug(
                      "LM Studio embedding readiness skipped model=%s loaded_instances=%d",
                      model_key,
                      loaded_count,
                  )
                  return
  
              self._logger.debug(
                  "LM Studio embedding readiness loading model=%s loaded_instances=%d",
                  model_key,
                  loaded_count,
              )
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

--- FILE: python-daemon/orchestrator/memory/repo.py ---
Size: 5677 bytes
Summary: Classes: MemoryRepository; Functions: _dict, __init__, _conn, insert_memory_record, update_memory_index_state, list_memory_records, list_memory_records_for_reindex, _row_to_record
Content: |
  from __future__ import annotations
  
  import json
  import sqlite3
  from contextlib import closing
  from pathlib import Path
  from typing import Any
  
  from .models import MemoryRecord
  
  
  def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
      if row is None:
          return None
      return {key: row[key] for key in row.keys()}
  
  
  class MemoryRepository:
      def __init__(self, queue_db: Path) -> None:
          self.queue_db = Path(queue_db)
  
      def _conn(self) -> sqlite3.Connection:
          conn = sqlite3.connect(self.queue_db)
          conn.row_factory = sqlite3.Row
          conn.execute("PRAGMA busy_timeout = 5000")
          conn.execute("PRAGMA foreign_keys = ON")
          return conn
  
      def insert_memory_record(self, record: MemoryRecord) -> None:
          with closing(self._conn()) as conn:
              conn.execute(
                  """
                  INSERT OR REPLACE INTO memory_records (
                    memory_id, project_id, project_scope_hash, memory_type, source,
                    content, content_sha1, metadata_json, confidence_score, created_at,
                    index_status, indexed_at, index_error
                  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                  """,
                  (
                      record.memory_id,
                      record.project_id,
                      record.project_scope_hash,
                      record.memory_type,
                      record.source,
                      record.content,
                      record.content_sha1,
                      json.dumps(record.metadata_json, sort_keys=True),
                      record.confidence_score,
                      record.created_at,
                      record.index_status,
                      record.indexed_at,
                      record.index_error,
                  ),
              )
              conn.commit()
  
      def update_memory_index_state(
          self,
          memory_id: str,
          status: str,
          *,
          indexed_at: str | None = None,
          index_error: str | None = None,
      ) -> None:
          if status not in {"pending", "indexed", "failed"}:
              raise ValueError(f"invalid memory index status: {status}")
          with closing(self._conn()) as conn:
              conn.execute(
                  """
                  UPDATE memory_records
                  SET index_status = ?, indexed_at = ?, index_error = ?
                  WHERE memory_id = ?
                  """,
                  (status, indexed_at, index_error, memory_id),
              )
              conn.commit()
  
      def list_memory_records(self, project_scope_hash: str, limit: int = 50) -> list[MemoryRecord]:
          with closing(self._conn()) as conn:
              rows = conn.execute(
                  """
                  SELECT *
                  FROM memory_records
                  WHERE project_scope_hash = ?
                  ORDER BY created_at DESC
                  LIMIT ?
                  """,
                  (project_scope_hash, max(1, min(int(limit), 200))),
              ).fetchall()
          records: list[MemoryRecord] = []
          for row in rows:
              item = _dict(row)
              if item is None:
                  continue
              records.append(
                  MemoryRecord(
                      memory_id=str(item["memory_id"]),
                      project_id=str(item["project_id"]),
                      project_scope_hash=str(item["project_scope_hash"]),
                      memory_type=str(item["memory_type"]),
                      source=str(item["source"]),
                      content=str(item["content"]),
                      content_sha1=str(item["content_sha1"]),
                      metadata_json=json.loads(item["metadata_json"]) if item["metadata_json"] else {},
                      confidence_score=float(item["confidence_score"]),
                      created_at=str(item["created_at"]),
                      index_status=str(item.get("index_status", "pending")),
                      indexed_at=item.get("indexed_at"),
                      index_error=item.get("index_error"),
                  )
              )
          return records
  
      def list_memory_records_for_reindex(self, project_scope_hash: str | None = None, limit: int = 200) -> list[MemoryRecord]:
          sql = """
              SELECT *
              FROM memory_records
              WHERE index_status IN ('pending', 'failed')
          """
          params: list[Any] = []
          if project_scope_hash:
              sql += " AND project_scope_hash = ?"
              params.append(project_scope_hash)
          sql += " ORDER BY created_at ASC LIMIT ?"
          params.append(max(1, min(int(limit), 500)))
          with closing(self._conn()) as conn:
              rows = conn.execute(sql, params).fetchall()
          return [self._row_to_record(row) for row in rows]
  
      def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
          item = _dict(row)
          if item is None:
              raise ValueError("row is empty")
          return MemoryRecord(
              memory_id=str(item["memory_id"]),
              project_id=str(item["project_id"]),
              project_scope_hash=str(item["project_scope_hash"]),
              memory_type=str(item["memory_type"]),
              source=str(item["source"]),
              content=str(item["content"]),
              content_sha1=str(item["content_sha1"]),
              metadata_json=json.loads(item["metadata_json"]) if item["metadata_json"] else {},
              confidence_score=float(item["confidence_score"]),
              created_at=str(item["created_at"]),
              index_status=str(item.get("index_status", "pending")),
              indexed_at=item.get("indexed_at"),
              index_error=item.get("index_error"),
          )

--- FILE: python-daemon/orchestrator/skills/registry.py ---
Size: 4044 bytes
Summary: Classes: SkillRegistry; Functions: utc_now, __init__, _connect, upsert_verified, quarantine, list_verified, get_verified
Content: |
  from __future__ import annotations
  
  import json
  import sqlite3
  from contextlib import closing
  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any
  
  def utc_now() -> str:
      return datetime.now(timezone.utc).isoformat()
  
  class SkillRegistry:
      def __init__(self, queue_db_path: Path) -> None:
          self.queue_db_path = Path(queue_db_path)
  
      def _connect(self) -> sqlite3.Connection:
          conn = sqlite3.connect(self.queue_db_path)
          conn.row_factory = sqlite3.Row
          conn.execute("PRAGMA busy_timeout = 5000")
          return conn
  
      def upsert_verified(self, manifest: dict[str, Any], source_path: Path) -> None:
          now = utc_now()
          manifest_for_storage = dict(manifest)
          manifest_for_storage["source_path"] = str(source_path)
  
          with closing(self._connect()) as conn:
              conn.execute(
                  """
                  INSERT INTO skill_manifests (
                    skill_id, version, project_scope_hash, manifest_json,
                    status, source_path, created_at, updated_at
                  )
                  VALUES (?, ?, ?, ?, 'verified', ?, ?, ?)
                  ON CONFLICT(skill_id) DO UPDATE SET
                    version = excluded.version,
                    project_scope_hash = excluded.project_scope_hash,
                    manifest_json = excluded.manifest_json,
                    status = 'verified',
                    source_path = excluded.source_path,
                    updated_at = excluded.updated_at
                  """,
                  (
                      manifest["skill_id"],
                      manifest["version"],
                      None,
                      json.dumps(manifest_for_storage, sort_keys=True),
                      str(source_path),
                      now,
                      now,
                  ),
              )
              conn.commit()
  
      def quarantine(self, skill_id: str, source_path: Path, reason: str, raw: dict[str, Any] | None = None) -> None:
          now = utc_now()
          payload = {
              "manifest": raw or {},
              "quarantine_reason": reason,
          }
  
          with closing(self._connect()) as conn:
              conn.execute(
                  """
                  INSERT INTO skill_manifests (
                    skill_id, version, project_scope_hash, manifest_json,
                    status, source_path, created_at, updated_at
                  )
                  VALUES (?, ?, NULL, ?, 'quarantined', ?, ?, ?)
                  ON CONFLICT(skill_id) DO UPDATE SET
                    manifest_json = excluded.manifest_json,
                    status = 'quarantined',
                    source_path = excluded.source_path,
                    updated_at = excluded.updated_at
                  """,
                  (
                      skill_id,
                      (raw or {}).get("version", "0.0.0"),
                      json.dumps(payload, sort_keys=True),
                      str(source_path),
                      now,
                      now,
                  ),
              )
              conn.commit()
  
      def list_verified(self) -> list[dict[str, Any]]:
          with closing(self._connect()) as conn:
              rows = conn.execute(
                  """
                  SELECT manifest_json
                  FROM skill_manifests
                  WHERE status = 'verified'
                  ORDER BY skill_id ASC
                  """
              ).fetchall()
          return [json.loads(row["manifest_json"]) for row in rows]
  
      def get_verified(self, skill_id: str) -> dict[str, Any] | None:
          with closing(self._connect()) as conn:
              row = conn.execute(
                  """
                  SELECT manifest_json
                  FROM skill_manifests
                  WHERE skill_id = ? AND status = 'verified'
                  """,
                  (skill_id,),
              ).fetchone()
          return json.loads(row["manifest_json"]) if row else None

--- FILE: python-daemon/tests/test_active_partition_repo.py ---
Size: 2007 bytes
Summary: Classes: ActivePartitionRepositoryTests; Functions: test_active_partition_persists_in_sqlite
Content: |
  from __future__ import annotations
  
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.active_partition.models import ActivePartition, MemoryProject
  from orchestrator.active_partition.repo import ActivePartitionRepository
  from orchestrator.db_bootstrap import bootstrap_databases
  
  
  class ActivePartitionRepositoryTests(unittest.TestCase):
      def test_active_partition_persists_in_sqlite(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = ActivePartitionRepository(root / "queue.db")
              project = MemoryProject(
                  project_id="lmstudio-client-a-backend-debug",
                  project_scope_hash="scope-1",
                  source="manual_override",
                  display_name="client-a / backend-debug",
                  lmstudio_folder_relpath="client-a/backend-debug",
                  allowed_roots_json=[str(root)],
                  rag_enabled=True,
                  created_at="2026-01-01T00:00:00Z",
                  last_seen_at="2026-01-01T00:00:00Z",
              )
              repo.upsert_memory_project(project)
              partition = ActivePartition(
                  client_id="local-lmstudio",
                  active_project_id=project.project_id,
                  active_project_scope_hash=project.project_scope_hash,
                  active_conversation_id="chat",
                  conversation_path=str(root / "client-a" / "backend-debug" / "chat.conversation.json"),
                  confidence="high",
                  source_event="manual_override",
                  updated_at="2026-01-01T00:00:01Z",
              )
              repo.set_active_partition(partition)
  
              loaded = repo.get_active_partition()
              projects = repo.list_memory_projects()
  
              self.assertIsNotNone(loaded)
              self.assertEqual(loaded.active_project_scope_hash, "scope-1")
              self.assertEqual(projects[0].project_id, project.project_id)

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

--- FILE: python-daemon/tests/test_tool_assist_adapter.py ---
Size: 6412 bytes
Summary: Classes: ToolAssistAdapterTests; Functions: test_tool_adapters_default_has_tool_assist_without_env, test_missing_toolset_root_fails_clearly, test_missing_backend_api_fails_clearly, test_method_mapping_output_root_error_and_bounded_content, test_dispatch_missing_toolset_root_from_default_adapter, test_session_path_policy_block_and_allow
Content: |
  import os
  import sys
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.adapters import ToolAdapters
  from orchestrator.tool_assist_adapter import ToolAssistAdapter
  
  
  class ToolAssistAdapterTests(unittest.TestCase):
      def test_tool_adapters_default_has_tool_assist_without_env(self):
          previous = os.environ.pop("TOOLSET_ROOT", None)
          try:
              adapters = ToolAdapters()
              self.assertIsNotNone(adapters.tool_assist)
          finally:
              if previous is not None:
                  os.environ["TOOLSET_ROOT"] = previous
  
      def test_missing_toolset_root_fails_clearly(self):
          result = ToolAssistAdapter(toolset_root=None).investigation_start("obj", "repo")
          self.assertFalse(result["ok"])
          self.assertEqual(result["error"]["code"], "missing_toolset_root")
  
      def test_missing_backend_api_fails_clearly(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              (root / "local_tool_assist_mcp").mkdir()
              (root / "local_tool_assist_mcp" / "__init__.py").write_text("", encoding="utf-8")
              sys.modules.pop("local_tool_assist_mcp.backend_api", None)
              sys.modules.pop("local_tool_assist_mcp", None)
              result = ToolAssistAdapter(toolset_root=str(root)).investigation_start("obj", "repo")
          self.assertFalse(result["ok"])
          self.assertEqual(result["error"]["code"], "missing_backend_api")
  
      def test_method_mapping_output_root_error_and_bounded_content(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              outputs = root / "outputs"
              outputs.mkdir()
              session = outputs / "s1"
              session.mkdir()
              pkg = root / "local_tool_assist_mcp"
              pkg.mkdir()
              (pkg / "__init__.py").write_text("", encoding="utf-8")
              (pkg / "backend_api.py").write_text(
                  """
  CALLS=[]
  def create_session(objective, target_repo, profile='safe', output_root=None):
      CALLS.append(('create_session', output_root))
      return {'ok': True, 'status': 'PASS', 'summary': 'ok', 'artifacts': {'session_path': '/tmp/s'}, 'top_candidates': list(range(50)), 'recommended_next_tool': 'mcp_investigation_filemap'}
  def scan_directory(session_path, profile='safe'):
      CALLS.append(('scan_directory', None))
      return {'ok': True, 'status': 'PASS', 'summary': 'x'*5000, 'artifacts': {'a': '/tmp/a', 'b': 1}, 'error': {'code': 'upstream_warn', 'message': 'warn-msg'}}
  def validate_manifest(session_path):
      CALLS.append(('validate_manifest', None))
      return {'ok': False, 'status': 'WARN', 'summary': 'warn', 'error': 'string upstream err'}
  def read_report(session_path, artifact_key, max_chars=12000):
      CALLS.append(('read_report', None))
      return {'ok': True, 'status': 'PASS', 'summary': 'read', 'content': 'Y'*200}
  def compile_handoff_report(session_path):
      CALLS.append(('compile_handoff_report', None))
      return {'ok': True, 'status': 'COMPLETE', 'summary': 'done'}
  """,
                  encoding="utf-8",
              )
              sys.modules.pop("local_tool_assist_mcp.backend_api", None)
              sys.modules.pop("local_tool_assist_mcp", None)
              adapter = ToolAssistAdapter(toolset_root=str(root), lta_output_root=str(outputs))
              start = adapter.investigation_start("o", "r")
              filemap = adapter.investigation_filemap(str(session))
              validate = adapter.investigation_validate_manifest(str(session))
              read = adapter.investigation_read_report(str(session), "manifest_csv", 88)
              compile_result = adapter.investigation_compile_handoff(str(session))
              api = adapter._load_backend_api()
  
          self.assertEqual([name for name, _ in api.CALLS], [
              "create_session", "scan_directory", "validate_manifest", "read_report", "compile_handoff_report"
          ])
          self.assertEqual(api.CALLS[0][1], str(outputs))
          self.assertEqual(start["artifacts"], {"session_path": "/tmp/s"})
          self.assertEqual(len(start["top_candidates"]), 10)
          self.assertLessEqual(len(filemap["summary"]), 2000)
          self.assertEqual(filemap["artifacts"], {"a": "/tmp/a"})
          self.assertEqual(filemap["error"]["code"], "upstream_warn")
          self.assertEqual(validate["error"]["code"], "toolset_error")
          self.assertEqual(len(read["content"]), 88)
          self.assertEqual(compile_result["status"], "COMPLETE")
  
      def test_dispatch_missing_toolset_root_from_default_adapter(self):
          previous = os.environ.pop("TOOLSET_ROOT", None)
          try:
              result = ToolAdapters().call_mcp_tool("mcp_investigation_start", {"objective": "a", "target_repo": "b"})
          finally:
              if previous is not None:
                  os.environ["TOOLSET_ROOT"] = previous
          self.assertFalse(result["ok"])
          self.assertEqual(result["error"]["code"], "missing_toolset_root")
  
      def test_session_path_policy_block_and_allow(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              outputs = root / "outputs"
              outputs.mkdir()
              session = outputs / "inside"
              session.mkdir()
              outside = root / "outside"
              outside.mkdir()
              pkg = root / "local_tool_assist_mcp"
              pkg.mkdir()
              (pkg / "__init__.py").write_text("", encoding="utf-8")
              (pkg / "backend_api.py").write_text(
                  """
  def scan_directory(session_path, profile='safe'):
      return {'ok': True, 'status': 'PASS', 'summary': session_path}
  """,
                  encoding="utf-8",
              )
              sys.modules.pop("local_tool_assist_mcp.backend_api", None)
              sys.modules.pop("local_tool_assist_mcp", None)
              adapter = ToolAssistAdapter(toolset_root=str(root), lta_output_root=str(outputs))
  
              blocked = adapter.investigation_filemap(str(outside))
              allowed = adapter.investigation_filemap(str(session))
  
          self.assertEqual(blocked["status"], "POLICY_BLOCK")
          self.assertEqual(blocked["error"]["code"], "session_path_outside_output_root")
          self.assertTrue(allowed["ok"])
  
  
  if __name__ == "__main__":
      unittest.main()

--- FILE: lmstudio_fastmcp_shim.py ---
Size: 8656 bytes
Summary: Classes: BridgeCallError; Functions: as_pretty_json, error_payload, call_bridge, call_tool, mcp_scout_workspace, mcp_ingest_target, mcp_semantic_search, mcp_verify_integrity, mcp_extract_image, mcp_investigation_start, mcp_investigation_filemap, mcp_investigation_validate_manifest, mcp_investigation_read_report, mcp_investigation_compile_handoff, mcp_agent_workflow_run, mcp_set_active_partition, mcp_set_active_project_manual
Content: |
  from __future__ import annotations
  
  import json
  import os
  import socket
  import time
  import traceback
  from typing import Any
  
  from mcp.server.fastmcp import FastMCP
  
  mcp = FastMCP("Aletheia_Orchestrator_Shim")
  
  BRIDGE_HOST = os.environ.get("ALETHEIA_BRIDGE_HOST", "127.0.0.1")
  BRIDGE_PORT = int(os.environ.get("ALETHEIA_BRIDGE_PORT", "8765"))
  BRIDGE_TIMEOUT_SECONDS = float(os.environ.get("ALETHEIA_BRIDGE_TIMEOUT_SECONDS", "180"))
  MAX_RESPONSE_BYTES = int(os.environ.get("ALETHEIA_SHIM_MAX_RESPONSE_BYTES", "25000000"))
  
  
  class BridgeCallError(RuntimeError):
      """Raised internally when the local Aletheia daemon bridge rejects or fails a request."""
  
  
  def as_pretty_json(value: Any) -> str:
      return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
  
  
  def error_payload(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
      payload: dict[str, Any] = {
          "ok": False,
          "error": code,
          "message": str(message),
          "bridge": {
              "host": BRIDGE_HOST,
              "port": BRIDGE_PORT,
              "timeout_seconds": BRIDGE_TIMEOUT_SECONDS,
          },
      }
      if details:
          payload["details"] = details
      return payload
  
  
  def call_bridge(method: str, params: dict[str, Any]) -> dict[str, Any]:
      request = {
          "jsonrpc": "2.0",
          "id": int(time.time() * 1000),
          "method": method,
          "params": params,
      }
  
      try:
          with socket.create_connection(
              (BRIDGE_HOST, BRIDGE_PORT),
              timeout=BRIDGE_TIMEOUT_SECONDS,
          ) as sock:
              sock.settimeout(BRIDGE_TIMEOUT_SECONDS)
              payload = json.dumps(request, separators=(",", ":")) + "\n"
              sock.sendall(payload.encode("utf-8"))
  
              chunks: list[bytes] = []
              total = 0
              while True:
                  data = sock.recv(65536)
                  if not data:
                      break
                  chunks.append(data)
                  total += len(data)
  
                  if total > MAX_RESPONSE_BYTES:
                      raise BridgeCallError(
                          f"Aletheia bridge response exceeded {MAX_RESPONSE_BYTES} bytes"
                      )
  
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
          raise BridgeCallError(f"Aletheia bridge returned invalid JSON: {raw[:1000]}") from exc
  
      if "error" in response:
          raise BridgeCallError(as_pretty_json(response["error"]))
  
      result = response.get("result", {})
      if not isinstance(result, dict):
          return {"ok": True, "result": result}
      return result
  
  
  def call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
      try:
          return call_bridge(
              "tools.call",
              {
                  "toolName": tool_name,
                  "args": args,
              },
          )
      except BridgeCallError as exc:
          return error_payload(
              "bridge_call_failed",
              str(exc),
              details={"tool_name": tool_name, "args": args},
          )
      except Exception as exc:
          return error_payload(
              "shim_unhandled_exception",
              str(exc),
              details={
                  "tool_name": tool_name,
                  "args": args,
                  "traceback": traceback.format_exc(limit=5),
              },
          )
  
  
  @mcp.tool()
  def mcp_scout_workspace(
      project_id: str,
      absolute_path: str,
      max_files: int = 500,
      include_summaries: bool = True,
  ) -> str:
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
      args: dict[str, Any] = {"absolute_path": absolute_path}
      if page is not None:
          args["page"] = page
      if region is not None:
          args["region"] = region
  
      result = call_tool("mcp_extract_image", args)
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_investigation_start(objective: str, target_repo: str, profile: str = "safe") -> str:
      result = call_tool(
          "mcp_investigation_start",
          {"objective": objective, "target_repo": target_repo, "profile": profile},
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_investigation_filemap(session_path: str, profile: str = "safe") -> str:
      result = call_tool(
          "mcp_investigation_filemap",
          {"session_path": session_path, "profile": profile},
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_investigation_validate_manifest(session_path: str) -> str:
      result = call_tool("mcp_investigation_validate_manifest", {"session_path": session_path})
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_investigation_read_report(session_path: str, artifact_key: str, max_chars: int = 12000) -> str:
      result = call_tool(
          "mcp_investigation_read_report",
          {"session_path": session_path, "artifact_key": artifact_key, "max_chars": max_chars},
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_investigation_compile_handoff(session_path: str) -> str:
      result = call_tool("mcp_investigation_compile_handoff", {"session_path": session_path})
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_agent_workflow_run(
      objective: str,
      target_repo: str,
      profile: str = "safe",
      allow_ingest: bool = False,
      include_report_preview: bool = False,
      use_model_phases: bool = False,
  ) -> str:
      """
      target_repo must be the exact absolute local path to investigate. Do not infer, abbreviate, or invent target_repo. Recommended LM Studio exposure is allowed_tools = ["mcp_agent_workflow_run"].
      """
      result = call_tool(
          "mcp_agent_workflow_run",
          {
              "objective": objective,
              "target_repo": target_repo,
              "profile": profile,
              "allow_ingest": allow_ingest,
              "include_report_preview": include_report_preview,
              "use_model_phases": use_model_phases,
          },
      )
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_set_active_partition(conversation_path: str) -> str:
      result = call_tool("mcp_set_active_partition", {"conversation_path": conversation_path})
      return as_pretty_json(result)
  
  
  @mcp.tool()
  def mcp_set_active_project_manual(project_id: str, display_name: str | None = None) -> str:
      args: dict[str, Any] = {"project_id": project_id}
      if display_name is not None:
          args["display_name"] = display_name
      result = call_tool("mcp_set_active_project_manual", args)
      return as_pretty_json(result)
  
  
  if __name__ == "__main__":
      mcp.run(transport="stdio")

--- FILE: python-daemon/orchestrator/agent_workflow/runner.py ---
Size: 8750 bytes
Summary: Classes: WorkflowRunner; Functions: __init__, run, _build_plan, _clone_todo, _resolve_args, _merge_artifacts, _success_summary, _final_response
Content: |
  from __future__ import annotations
  
  import uuid
  from pathlib import Path
  from typing import Any
  
  from .bridge_client import TcpBridgeClient
  from .compaction import compact_tool_result
  from .policies import reasoning_policy
  from .state import WorkflowState, default_state_dir, utc_now_iso
  
  
  class WorkflowRunner:
      def __init__(
          self,
          lm_client: Any | None = None,
          bridge_client: TcpBridgeClient | None = None,
          allow_ingest: bool = False,
          *,
          state_dir: Path | None = None,
          max_steps: int | None = None,
          max_tool_result_chars: int | None = None,
      ) -> None:
          self.lm_client = lm_client
          self.bridge_client = bridge_client or TcpBridgeClient()
          self.allow_ingest = allow_ingest
          self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
          self.max_steps = int(max_steps or 8)
          self.max_tool_result_chars = int(max_tool_result_chars or 2000)
  
      def run(
          self,
          *,
          objective: str,
          target_repo: str,
          profile: str = "safe",
          allow_ingest: bool | None = None,
          include_report_preview: bool = False,
          use_model_phases: bool = False,
          selected_skill: dict[str, Any] | None = None,
          skill_warnings: list[dict[str, Any]] | None = None,
      ) -> tuple[WorkflowState, dict[str, Any]]:
          state = WorkflowState(
              run_id=str(uuid.uuid4()),
              created_at=utc_now_iso(),
              user_prompt=f"objective={objective}; target_repo={target_repo}; profile={profile}",
              goal=objective,
              reasoning_policy=reasoning_policy(),
              selected_skill=selected_skill,
              warnings=list(skill_warnings or []),
          )
  
          plan = self._build_plan(objective, target_repo, profile)
          if len(plan) > self.max_steps:
              state.phase = "FINAL"
              state.final_summary = "Workflow blocked: plan exceeds the configured maximum step count."
              state.errors.append(
                  {
                      "code": "plan_too_long",
                      "message": state.final_summary,
                  }
              )
              state_path = state.save(self.state_dir)
              return state, self._final_response(state, state_path, ok=False, status="POLICY_BLOCK")
  
          state.todos = [self._clone_todo(todo) for todo in plan]
          state_path = state.save(self.state_dir)
          session_path = ""
  
          for todo in state.todos:
              state.phase = "ACT"
              todo["status"] = "active"
              state_path = state.save(self.state_dir)
              raw_result = self.bridge_client.call_tool(todo["tool_name"], self._resolve_args(todo["args"], session_path))
              compact = compact_tool_result(
                  todo["tool_name"],
                  raw_result,
                  max_chars=self.max_tool_result_chars,
                  include_content=include_report_preview and todo["tool_name"] == "mcp_investigation_read_report",
              )
              state.tool_results.append(compact)
              self._merge_artifacts(state.artifacts, compact.get("artifacts", {}))
  
              state.phase = "SUMMARISE_TOOL_RESULT"
              todo["status"] = "done" if compact["ok"] else "blocked"
              state_path = state.save(self.state_dir)
  
              state.phase = "CHECK"
              state_path = state.save(self.state_dir)
  
              if not compact["ok"]:
                  state.errors.append(
                      {
                          "code": compact.get("error", {}).get("code", "tool_failed")
                          if isinstance(compact.get("error"), dict)
                          else "tool_failed",
                          "message": compact.get("summary", "Tool execution failed."),
                      }
                  )
                  state.phase = "FINAL"
                  state.final_summary = compact.get("summary", "Workflow blocked.")
                  state_path = state.save(self.state_dir)
                  return state, self._final_response(state, state_path, ok=False, status=str(compact.get("status", "ERROR")))
  
              if todo["tool_name"] == "mcp_investigation_start":
                  session_path = str(state.artifacts.get("session_path") or session_path)
  
              if todo["tool_name"] == "mcp_investigation_compile_handoff":
                  state.phase = "SYNTHESIZE"
                  state.final_summary = self._success_summary(state)
                  state_path = state.save(self.state_dir)
                  state.phase = "FINAL"
                  state_path = state.save(self.state_dir)
                  return state, self._final_response(state, state_path, ok=True, status="COMPLETE")
  
          state.phase = "SYNTHESIZE"
          state.final_summary = self._success_summary(state)
          state_path = state.save(self.state_dir)
          state.phase = "FINAL"
          state_path = state.save(self.state_dir)
          return state, self._final_response(state, state_path, ok=True, status="COMPLETE")
  
      def _build_plan(self, objective: str, target_repo: str, profile: str) -> list[dict[str, Any]]:
          return [
              {
                  "id": "start_investigation",
                  "status": "pending",
                  "description": "Create a Tool Assist session",
                  "tool_name": "mcp_investigation_start",
                  "args": {
                      "objective": objective,
                      "target_repo": target_repo,
                      "profile": profile,
                  },
              },
              {
                  "id": "filemap",
                  "status": "pending",
                  "description": "Build the file map for the investigation session",
                  "tool_name": "mcp_investigation_filemap",
                  "args": {
                      "session_path": "${session_path}",
                      "profile": profile,
                  },
              },
              {
                  "id": "validate_manifest",
                  "status": "pending",
                  "description": "Validate the manifest output",
                  "tool_name": "mcp_investigation_validate_manifest",
                  "args": {
                      "session_path": "${session_path}",
                  },
              },
              {
                  "id": "read_report",
                  "status": "pending",
                  "description": "Read a bounded report preview",
                  "tool_name": "mcp_investigation_read_report",
                  "args": {
                      "session_path": "${session_path}",
                      "artifact_key": "manifest_doctor_md",
                      "max_chars": self.max_tool_result_chars,
                  },
              },
              {
                  "id": "compile_handoff",
                  "status": "pending",
                  "description": "Compile the final handoff artifacts",
                  "tool_name": "mcp_investigation_compile_handoff",
                  "args": {
                      "session_path": "${session_path}",
                  },
              },
          ]
  
      def _clone_todo(self, todo: dict[str, Any]) -> dict[str, Any]:
          return {
              "id": todo["id"],
              "status": todo["status"],
              "description": todo["description"],
              "tool_name": todo["tool_name"],
              "args": dict(todo["args"]),
          }
  
      def _resolve_args(self, args: dict[str, Any], session_path: str) -> dict[str, Any]:
          resolved: dict[str, Any] = {}
          for key, value in args.items():
              if value == "${session_path}":
                  resolved[key] = session_path
              else:
                  resolved[key] = value
          return resolved
  
      def _merge_artifacts(self, merged: dict[str, str], artifacts: dict[str, Any]) -> None:
          for key, value in artifacts.items():
              if isinstance(key, str) and value is not None:
                  merged.setdefault(key, str(value))
  
      def _success_summary(self, state: WorkflowState) -> str:
          return "Workflow complete. Generated session, manifest, validation, handoff, and archive artifacts."
  
      def _final_response(self, state: WorkflowState, state_path: Path, *, ok: bool, status: str) -> dict[str, Any]:
          artifacts = dict(state.artifacts)
          artifacts["selected_skill"] = state.selected_skill
          return {
              "ok": ok,
              "status": status,
              "run_id": state.run_id,
              "summary": state.final_summary or self._success_summary(state),
              "artifacts": artifacts,
              "state_path": str(state_path),
              "error": None if ok else (state.errors[-1] if state.errors else {"code": "workflow_failed", "message": "Workflow failed."}),
          }

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

--- FILE: python-daemon/orchestrator/active_partition/repo.py ---
Size: 6769 bytes
Summary: Classes: ActivePartitionRepository; Functions: _now, _dict, __init__, _conn, upsert_memory_project, list_memory_projects, set_active_partition, get_active_partition, clear_active_partition, record_conversation_event, _row_to_memory_project
Content: |
  from __future__ import annotations
  
  import json
  import sqlite3
  import uuid
  from contextlib import closing
  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any
  
  from .models import ActivePartition, MemoryProject
  
  
  def _now() -> str:
      return datetime.now(timezone.utc).isoformat()
  
  
  def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
      if row is None:
          return None
      return {key: row[key] for key in row.keys()}
  
  
  class ActivePartitionRepository:
      def __init__(self, queue_db: Path) -> None:
          self.queue_db = Path(queue_db)
  
      def _conn(self) -> sqlite3.Connection:
          conn = sqlite3.connect(self.queue_db)
          conn.row_factory = sqlite3.Row
          conn.execute("PRAGMA busy_timeout = 5000")
          conn.execute("PRAGMA foreign_keys = ON")
          return conn
  
      def upsert_memory_project(self, project: MemoryProject) -> None:
          with closing(self._conn()) as conn:
              conn.execute(
                  """
                  INSERT INTO memory_projects (
                    project_id, project_scope_hash, source, display_name, lmstudio_folder_relpath,
                    allowed_roots_json, rag_enabled, created_at, last_seen_at
                  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                  ON CONFLICT(project_scope_hash) DO UPDATE SET
                    project_id = excluded.project_id,
                    source = excluded.source,
                    display_name = excluded.display_name,
                    lmstudio_folder_relpath = excluded.lmstudio_folder_relpath,
                    allowed_roots_json = excluded.allowed_roots_json,
                    rag_enabled = excluded.rag_enabled,
                    last_seen_at = excluded.last_seen_at
                  """,
                  (
                      project.project_id,
                      project.project_scope_hash,
                      project.source,
                      project.display_name,
                      project.lmstudio_folder_relpath,
                      json.dumps(project.allowed_roots_json, sort_keys=True),
                      1 if project.rag_enabled else 0,
                      project.created_at or _now(),
                      project.last_seen_at or _now(),
                  ),
              )
              conn.commit()
  
      def list_memory_projects(self) -> list[MemoryProject]:
          with closing(self._conn()) as conn:
              rows = conn.execute(
                  "SELECT * FROM memory_projects ORDER BY last_seen_at DESC, created_at DESC, project_id ASC"
              ).fetchall()
          return [self._row_to_memory_project(row) for row in rows if row is not None]
  
      def set_active_partition(self, partition: ActivePartition) -> None:
          with closing(self._conn()) as conn:
              conn.execute(
                  """
                  INSERT INTO active_partitions (
                    client_id, active_project_id, active_project_scope_hash, active_conversation_id,
                    conversation_path, confidence, source_event, updated_at
                  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                  ON CONFLICT(client_id) DO UPDATE SET
                    active_project_id = excluded.active_project_id,
                    active_project_scope_hash = excluded.active_project_scope_hash,
                    active_conversation_id = excluded.active_conversation_id,
                    conversation_path = excluded.conversation_path,
                    confidence = excluded.confidence,
                    source_event = excluded.source_event,
                    updated_at = excluded.updated_at
                  """,
                  (
                      partition.client_id,
                      partition.active_project_id,
                      partition.active_project_scope_hash,
                      partition.active_conversation_id,
                      partition.conversation_path,
                      partition.confidence,
                      partition.source_event,
                      partition.updated_at,
                  ),
              )
              conn.commit()
  
      def get_active_partition(self, client_id: str = "local-lmstudio") -> ActivePartition | None:
          with closing(self._conn()) as conn:
              row = conn.execute("SELECT * FROM active_partitions WHERE client_id = ?", (client_id,)).fetchone()
          result = _dict(row)
          if result is None:
              return None
          return ActivePartition(
              client_id=str(result["client_id"]),
              active_project_id=result.get("active_project_id"),
              active_project_scope_hash=result.get("active_project_scope_hash"),
              active_conversation_id=result.get("active_conversation_id"),
              conversation_path=result.get("conversation_path"),
              confidence=str(result["confidence"]),
              source_event=str(result["source_event"]),
              updated_at=str(result["updated_at"]),
          )
  
      def clear_active_partition(self, client_id: str = "local-lmstudio") -> None:
          with closing(self._conn()) as conn:
              conn.execute("DELETE FROM active_partitions WHERE client_id = ?", (client_id,))
              conn.commit()
  
      def record_conversation_event(
          self,
          project_scope_hash: str,
          session_id: str,
          role: str,
          content_json: dict[str, Any],
          token_count: int = 0,
          timestamp: str | None = None,
      ) -> None:
          with closing(self._conn()) as conn:
              conn.execute(
                  """
                  INSERT INTO conversation_events (
                    event_id, project_scope_hash, session_id, role, content_json, token_count, timestamp
                  ) VALUES (?, ?, ?, ?, ?, ?, ?)
                  """,
                  (
                      str(uuid.uuid4()),
                      project_scope_hash,
                      session_id,
                      role,
                      json.dumps(content_json, sort_keys=True),
                      int(token_count),
                      timestamp or _now(),
                  ),
              )
              conn.commit()
  
      def _row_to_memory_project(self, row: sqlite3.Row) -> MemoryProject:
          allowed_roots = json.loads(row["allowed_roots_json"]) if row["allowed_roots_json"] else []
          return MemoryProject(
              project_id=str(row["project_id"]),
              project_scope_hash=str(row["project_scope_hash"]),
              source=str(row["source"]),
              display_name=str(row["display_name"]),
              lmstudio_folder_relpath=row["lmstudio_folder_relpath"],
              allowed_roots_json=[str(value) for value in allowed_roots],
              rag_enabled=bool(row["rag_enabled"]),
              created_at=str(row["created_at"]),
              last_seen_at=str(row["last_seen_at"]),
          )

--- FILE: python-daemon/orchestrator/active_partition/service.py ---
Size: 5167 bytes
Summary: Classes: ActivePartitionServiceError, ActivePartitionService; Functions: _now, __init__, to_dict, __init__, set_active_from_conversation_path, set_active_project, get_active_partition, list_memory_projects, _project_scope_hash
Content: |
  from __future__ import annotations
  
  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any
  
  from .mapper import PartitionMapper
  from .models import ActivePartition, MemoryProject
  from .repo import ActivePartitionRepository
  
  
  def _now() -> str:
      return datetime.now(timezone.utc).isoformat()
  
  
  class ActivePartitionServiceError(RuntimeError):
      def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
          super().__init__(message)
          self.code = code
          self.message = message
          self.details = details or {}
  
      def to_dict(self) -> dict[str, Any]:
          payload = {"code": self.code, "message": self.message}
          if self.details:
              payload["details"] = self.details
          return payload
  
  
  class ActivePartitionService:
      def __init__(
          self,
          repo: ActivePartitionRepository,
          *,
          conversations_root: Path,
          client_id: str = "local-lmstudio",
          allowed_roots: tuple[Path, ...] | None = None,
      ) -> None:
          self.repo = repo
          self.mapper = PartitionMapper(conversations_root)
          self.client_id = client_id
          self.allowed_roots = tuple(root.resolve() for root in (allowed_roots or (conversations_root,)))
  
      def set_active_from_conversation_path(self, conversation_json_path: str, source_event: str = "manual_override") -> ActivePartition:
          mapping = self.mapper.map(conversation_json_path)
          if not mapping.ok:
              raise ActivePartitionServiceError(
                  mapping.status,
                  mapping.message,
                  details=mapping.to_dict(),
              )
          project = MemoryProject(
              project_id=mapping.project_id,
              project_scope_hash=mapping.project_scope_hash,
              source="lmstudio_folder",
              display_name=mapping.folder_relpath.replace("/", " / "),
              lmstudio_folder_relpath=mapping.folder_relpath,
              allowed_roots_json=[str(root) for root in self.allowed_roots],
              rag_enabled=True,
              created_at=_now(),
              last_seen_at=_now(),
          )
          self.repo.upsert_memory_project(project)
          partition = ActivePartition(
              client_id=self.client_id,
              active_project_id=project.project_id,
              active_project_scope_hash=project.project_scope_hash,
              active_conversation_id=mapping.conversation_id,
              conversation_path=mapping.conversation_path,
              confidence="high",
              source_event=source_event,
              updated_at=_now(),
          )
          self.repo.set_active_partition(partition)
          self.repo.record_conversation_event(
              project_scope_hash=project.project_scope_hash,
              session_id=mapping.conversation_id,
              role="system",
              content_json={
                  "event": "active_partition_mapped",
                  "conversation_path": mapping.conversation_path,
                  "folder_relpath": mapping.folder_relpath,
                  "project_id": project.project_id,
              },
          )
          return partition
  
      def set_active_project(self, project_id: str, display_name: str | None = None) -> ActivePartition:
          normalized_display_name = display_name or project_id
          stable_scope_hash = self._project_scope_hash(project_id)
          project = MemoryProject(
              project_id=project_id,
              project_scope_hash=stable_scope_hash,
              source="manual_override",
              display_name=normalized_display_name,
              lmstudio_folder_relpath=None,
              allowed_roots_json=[str(root) for root in self.allowed_roots],
              rag_enabled=True,
              created_at=_now(),
              last_seen_at=_now(),
          )
          self.repo.upsert_memory_project(project)
          partition = ActivePartition(
              client_id=self.client_id,
              active_project_id=project_id,
              active_project_scope_hash=stable_scope_hash,
              active_conversation_id=None,
              conversation_path=None,
              confidence="high",
              source_event="manual_override",
              updated_at=_now(),
          )
          self.repo.set_active_partition(partition)
          self.repo.record_conversation_event(
              project_scope_hash=stable_scope_hash,
              session_id=project_id,
              role="system",
              content_json={
                  "event": "manual_active_project_override",
                  "project_id": project_id,
                  "display_name": normalized_display_name,
              },
          )
          return partition
  
      def get_active_partition(self) -> ActivePartition | None:
          return self.repo.get_active_partition(self.client_id)
  
      def list_memory_projects(self) -> list[MemoryProject]:
          return self.repo.list_memory_projects()
  
      def _project_scope_hash(self, project_id: str) -> str:
          import hashlib
          import json
  
          return hashlib.sha1(
              json.dumps({"project_id": project_id}, sort_keys= [REDACTED_HIGH_ENTROPY]
          ).hexdigest()

--- FILE: python-daemon/orchestrator/agent_workflow/bridge_client.py ---
Size: 4685 bytes
Summary: Classes: TcpBridgeClient; Functions: __init__, call_tool, _error, _build_auth_envelope
Content: |
  from __future__ import annotations
  
  import json
  import hashlib
  import hmac
  import os
  import socket
  import time
  import uuid
  from typing import Any
  
  
  class TcpBridgeClient:
      def __init__(
          self,
          host: str | None = None,
          port: int | None = None,
          timeout: float = 30.0,
          max_response_bytes: int | None = None,
      ) -> None:
          self.host = host or os.getenv("ALETHEIA_BRIDGE_HOST", "127.0.0.1")
          self.port = int(port or os.getenv("ALETHEIA_BRIDGE_PORT", "8765"))
          self.timeout = float(timeout)
          self.max_response_bytes = int(max_response_bytes or os.getenv("ALETHEIA_SHIM_MAX_RESPONSE_BYTES", "25000000"))
          self.shared_secret = [REDACTED_HIGH_ENTROPY]
  
      def call_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
          request: dict[str, Any] = {
              "jsonrpc": "2.0",
              "id": 1,
              "method": "tools.call",
              "params": {
                  "toolName": tool_name,
                  "args": args,
              },
          }
          if self.shared_secret:
              request["params"]["auth"] = self._build_auth_envelope(request, self.shared_secret)
  
          try:
              with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                  sock.settimeout(self.timeout)
                  payload = json.dumps(request, separators=(",", ":")) + "\n"
                  sock.sendall(payload.encode("utf-8"))
  
                  chunks: list[bytes] = []
                  total = 0
                  while True:
                      try:
                          data = sock.recv(65536)
                      except socket.timeout:
                          return self._error("bridge_call_failed", f"bridge_call_failed: timeout waiting for {tool_name}")
                      if not data:
                          break
                      chunks.append(data)
                      total += len(data)
                      if total > self.max_response_bytes:
                          return self._error(
                              "bridge_call_failed",
                              f"bridge_call_failed: bridge response exceeded {self.max_response_bytes} bytes",
                          )
                      if b"\n" in data:
                          break
          except OSError as exc:
              return self._error("bridge_call_failed", f"bridge_call_failed: {exc}")
  
          raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
          if not raw:
              return self._error("bridge_call_failed", "bridge_call_failed: empty bridge response")
  
          try:
              response = json.loads(raw)
          except json.JSONDecodeError as exc:
              return self._error("bridge_call_failed", f"bridge_call_failed: invalid JSON response ({exc})")
  
          if not isinstance(response, dict):
              return self._error("bridge_call_failed", "bridge_call_failed: bridge returned a non-object response")
  
          if "error" in response:
              error = response.get("error")
              if isinstance(error, dict):
                  message = str(error.get("message", "bridge error"))
                  code = str(error.get("code", "bridge_error"))
              else:
                  message = str(error)
                  code = "bridge_error"
              return self._error(code, f"bridge_call_failed: {message}")
  
          result = response.get("result")
          if isinstance(result, dict):
              return result
          return {"ok": True, "status": "OK", "summary": "Bridge call completed.", "result": result, "artifacts": {}}
  
      def _error(self, code: str, summary: str) -> dict[str, Any]:
          return {
              "ok": False,
              "status": "ERROR",
              "summary": summary,
              "artifacts": {},
              "error": {"code": code, "message": summary},
          }
  
      def _build_auth_envelope(
          self,
          message: dict[str, Any],
          shared_secret: str,
          *,
          timestamp: str | None = None,
          nonce: str | None = None,
      ) -> dict[str, str]:
          timestamp = timestamp or str(int(time.time()))
          nonce = nonce or str(uuid.uuid4())
          sanitized = json.loads(json.dumps(message, sort_keys=True, separators=(",", ":")))
          params = dict(sanitized.get("params") or {})
          params.pop("auth", None)
          sanitized["params"] = params
          payload = [REDACTED_HIGH_ENTROPY]
          signature = [REDACTED_HIGH_ENTROPY]
          return {"timestamp": timestamp, "signature": signature, "nonce": nonce}

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

--- FILE: python-daemon/orchestrator/agent_workflow/mcp_tool.py ---
Size: 6900 bytes
Summary: Functions: _allowed_roots_from_env, _invalid_target_repo, validate_target_repo, _compact_selected_skill, _load_selected_skill_metadata, run_agent_workflow
Content: |
  from __future__ import annotations
  
  import os
  from pathlib import Path
  from typing import Any
  
  from .bridge_client import TcpBridgeClient
  from .runner import WorkflowRunner
  from .state import default_state_dir
  from orchestrator.skills.importer import SkillImporter
  from orchestrator.skills.registry import SkillRegistry
  from orchestrator.skills.selection import select_skill
  
  
  def _allowed_roots_from_env() -> tuple[Path, ...]:
      raw = os.getenv("ALETHEIA_ALLOWED_ROOTS", "").strip()
      if not raw:
          return tuple()
      roots = [Path(part).expanduser().resolve() for part in raw.split(";") if part.strip()]
      return tuple(roots)
  
  
  def _invalid_target_repo(message: str) -> dict[str, Any]:
      return {
          "ok": False,
          "status": "POLICY_BLOCK",
          "summary": "target_repo must be an existing absolute path under an allowed root.",
          "run_id": "",
          "artifacts": {},
          "state_path": "",
          "error": {"code": "invalid_target_repo", "message": message},
      }
  
  
  def validate_target_repo(target_repo: str, allowed_roots: tuple[Path, ...] | None = None) -> tuple[bool, str, Path | None]:
      path = Path(target_repo).expanduser()
      if not path.is_absolute():
          return False, f"target_repo must be absolute: {target_repo}", None
      resolved = path.resolve()
      if not resolved.exists():
          return False, f"target_repo does not exist: {resolved}", None
      roots = tuple(root.resolve() for root in (allowed_roots if allowed_roots is not None else _allowed_roots_from_env()))
      if roots and not any(resolved == root or root in resolved.parents for root in roots):
          return False, f"target_repo must be under an allowed root: {resolved}", None
      return True, "", resolved
  
  
  def _compact_selected_skill(manifests: list[dict[str, Any]], selection: dict[str, Any] | None) -> dict[str, Any] | None:
      if not selection:
          return None
  
      selected_skill_id = selection.get("selected_skill_id")
      manifest = next((item for item in manifests if item.get("skill_id") == selected_skill_id), None)
      evidence = next(
          (item for item in selection.get("candidate_analysis", []) if item.get("skill_id") == selected_skill_id),
          None,
      )
      if manifest is None:
          return None
  
      compact: dict[str, Any] = {
          "skill_id": selected_skill_id,
          "risk_tier": manifest.get("risk_tier"),
          "capabilities": list(manifest.get("capabilities") or []),
          "source": "skill_registry",
          "instruction_loaded": False,
      }
      if evidence:
          compact["evidence"] = {
              key: evidence.get(key)
              for key in ("score", "trigger_hits", "capability_hits", "intent_hits")
              if key in evidence
          }
      return compact
  
  
  def _load_selected_skill_metadata(objective: str, *, state_dir: Path | None = None, skill_registry_root: Path | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
      warnings: list[dict[str, Any]] = []
      base_state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
      queue_db_path = base_state_dir / "queue.db"
  
      try:
          registry = SkillRegistry(queue_db_path)
          manifests = registry.list_verified()
          import_report: dict[str, Any] | None = None
          if not manifests and skill_registry_root is not None:
              importer = SkillImporter(Path(skill_registry_root), registry)
              import_report = importer.import_all()
              manifests = registry.list_verified()
          if not manifests:
              warnings.append(
                  {
                      "code": "skill_registry_empty",
                      "source": "skill_registry",
                      "message": "No verified skill manifests were available.",
                      **(
                          {
                              "import_report": {
                                  "ok": bool(import_report.get("ok")),
                                  "verified_count": len(import_report.get("verified") or []),
                                  "quarantined_count": len(import_report.get("quarantined") or []),
                              }
                          }
                          if import_report is not None
                          else {}
                      ),
                  }
              )
              return None, warnings
  
          selection = select_skill(objective, manifests)
          return _compact_selected_skill(manifests, selection), warnings
      except Exception as exc:
          warnings.append(
              {
                  "code": "skill_registry_unavailable",
                  "source": "skill_registry",
                  "message": str(exc)[:200],
              }
          )
          return None, warnings
  
  
  def run_agent_workflow(
      *,
      objective: str,
      target_repo: str,
      profile: str = "safe",
      allow_ingest: bool = False,
      include_report_preview: bool = False,
      use_model_phases: bool = False,
      bridge_client: TcpBridgeClient | None = None,
      state_dir: Path | None = None,
      allowed_roots: tuple[Path, ...] | None = None,
      skill_registry_root: Path | None = None,
      max_steps: int | None = None,
      max_tool_result_chars: int | None = None,
  ) -> dict[str, Any]:
      if profile != "safe":
          return {
              "ok": False,
              "status": "POLICY_BLOCK",
              "summary": "profile must be safe for this workflow.",
              "run_id": "",
              "artifacts": {},
              "state_path": "",
              "error": {"code": "unsupported_profile", "message": "profile must be safe"},
          }
  
      valid, message, resolved = validate_target_repo(target_repo, allowed_roots)
      if not valid or resolved is None:
          return _invalid_target_repo(message)
  
      selected_skill, skill_warnings = _load_selected_skill_metadata(
          objective,
          state_dir=state_dir,
          skill_registry_root=skill_registry_root,
      )
  
      runner = WorkflowRunner(
          bridge_client=bridge_client or TcpBridgeClient(),
          allow_ingest=allow_ingest,
          state_dir=state_dir,
          max_steps=max_steps,
          max_tool_result_chars=max_tool_result_chars,
      )
      try:
          _, response = runner.run(
              objective=objective,
              target_repo=str(resolved),
              profile=profile,
              allow_ingest=allow_ingest,
              include_report_preview=include_report_preview,
              use_model_phases=use_model_phases,
              selected_skill=selected_skill,
              skill_warnings=skill_warnings,
          )
          return response
      except Exception as exc:
          return {
              "ok": False,
              "status": "ERROR",
              "summary": "Workflow execution failed.",
              "run_id": "",
              "artifacts": {},
              "state_path": "",
              "error": {"code": "workflow_runner_failed", "message": str(exc)[:2000]},
          }

--- FILE: python-daemon/orchestrator/chroma_manager.py ---
Size: 9670 bytes
Summary: Classes: ChromaAdapterError, ChromaConfig, ChromaManager; Functions: __init__, project_scope_hash, switch_project, _resolve_scope_hash, embed_text, upsert_chunks, search, delete_chunks, rebuild_from_chunks, _chunk_id, _normalize_results
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
  
      def _resolve_scope_hash(
          self,
          project_id: str,
          project_params: dict[str, Any] | None = None,
          project_scope_hash: str | None = None,
      ) -> str:
          if project_scope_hash:
              if project_scope_hash != self._active_scope_hash:
                  self.embed_text.cache_clear()
                  self._active_scope_hash = project_scope_hash
              return project_scope_hash
          return self.switch_project(project_id, project_params)
  
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
          project_scope_hash: str | None = None,
      ) -> dict[str, Any]:
          scope_hash = self._resolve_scope_hash(project_id, project_params, project_scope_hash)
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
          project_scope_hash: str | None = None,
      ) -> list[dict[str, Any]]:
          if k < 1 or k > 50:
              raise ChromaAdapterError("k must be between 1 and 50")
          scope_hash = self._resolve_scope_hash(project_id, project_params, project_scope_hash)
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
  
      def delete_chunks(
          self,
          *,
          project_id: str,
          absolute_path: str,
          project_params: dict[str, Any] | None = None,
          project_scope_hash: str | None = None,
      ) -> None:
          scope_hash = self._resolve_scope_hash(project_id, project_params, project_scope_hash)
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
  
      def rebuild_from_chunks(
          self,
          project_id: str,
          chunks: list[dict[str, Any]],
          *,
          project_scope_hash: str | None = None,
      ) -> dict[str, Any]:
          return self.upsert_chunks(project_id=project_id, chunks=chunks, project_scope_hash=project_scope_hash)
  
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

--- FILE: python-daemon/orchestrator/memory/service.py ---
Size: 7870 bytes
Summary: Classes: MemoryService; Functions: _now, __init__, commit_memory, rebuild_memory_index_for_project, semantic_search_active, _error
Content: |
  from __future__ import annotations
  
  import hashlib
  import json
  import uuid
  from datetime import datetime, timezone
  from typing import Any
  
  from ..active_partition.repo import ActivePartitionRepository
  from ..chroma_manager import ChromaAdapterError, ChromaManager
  from .models import ALLOWED_MEMORY_TYPES, MemoryRecord
  from .repo import MemoryRepository
  
  
  def _now() -> str:
      return datetime.now(timezone.utc).isoformat()
  
  
  class MemoryService:
      def __init__(
          self,
          repo: MemoryRepository,
          active_repo: ActivePartitionRepository,
          chroma: ChromaManager,
          *,
          client_id: str = "local-lmstudio",
      ) -> None:
          self.repo = repo
          self.active_repo = active_repo
          self.chroma = chroma
          self.client_id = client_id
  
      def commit_memory(
          self,
          category: str,
          content: str,
          confidence_score: float = 1.0,
          metadata: dict[str, Any] | None = None,
      ) -> dict[str, Any]:
          if category not in ALLOWED_MEMORY_TYPES:
              return self._error("invalid_category", f"Unsupported memory category: {category}", status="POLICY_BLOCK")
          bounded_content = content[:8000]
          if len(bounded_content.strip()) < 10:
              return self._error("content_too_short", "Memory content must be at least 10 characters.", status="POLICY_BLOCK")
          active = self.active_repo.get_active_partition(self.client_id)
          if active is None or not active.active_project_id or not active.active_project_scope_hash:
              return self._error(
                  "no_active_partition",
                  "No active partition is available. Set an LM Studio folder first.",
                  status="NO_ACTIVE_PARTITION",
              )
          memory_id = str(uuid.uuid4())
          content_sha1 = hashlib.sha1(bounded_content.encode("utf-8")).hexdigest()
          record = MemoryRecord(
              memory_id=memory_id,
              project_id=active.active_project_id,
              project_scope_hash=active.active_project_scope_hash,
              memory_type=category,
              source="memory_record",
              content=bounded_content,
              content_sha1=content_sha1,
              metadata_json=dict(metadata or {}),
              confidence_score=float(confidence_score),
              created_at=_now(),
              index_status="pending",
          )
          self.repo.insert_memory_record(record)
          chroma_metadata = {
              **dict(metadata or {}),
              "project_id": active.active_project_id,
              "project_scope_hash": active.active_project_scope_hash,
              "memory_id": memory_id,
              "memory_type": category,
              "source": "memory_record",
              "confidence_score": float(confidence_score),
          }
          try:
              chroma_result = self.chroma.upsert_chunks(
                  project_id=active.active_project_id,
                  project_scope_hash=active.active_project_scope_hash,
                  chunks=[
                      {
                          "chunk_id": memory_id,
                          "content": bounded_content,
                          "metadata": chroma_metadata,
                      }
                  ],
              )
              self.repo.update_memory_index_state(
                  memory_id,
                  "indexed",
                  indexed_at=_now(),
                  index_error=None,
              )
          except Exception as exc:
              index_error = str(exc)[:2000]
              self.repo.update_memory_index_state(
                  memory_id,
                  "failed",
                  indexed_at=None,
                  index_error=index_error,
              )
              failure = self._error("chroma_index_failed", f"Memory indexed in SQLite but Chroma indexing failed: {exc}")
              failure["memory_id"] = memory_id
              failure["index_status"] = "failed"
              return failure
          return {
              "ok": True,
              "status": "COMMITTED",
              "summary": "Memory committed to the active partition.",
              "memory_id": memory_id,
              "project_id": active.active_project_id,
              "project_scope_hash": active.active_project_scope_hash,
              "index_status": "indexed",
              "artifacts": {"memory_id": memory_id},
              "chroma": chroma_result,
          }
  
      def rebuild_memory_index_for_project(self, project_scope_hash: str, limit: int = 200) -> dict[str, Any]:
          records = self.repo.list_memory_records_for_reindex(project_scope_hash, limit)
          indexed = 0
          failed = 0
          for record in records:
              metadata = {
                  **dict(record.metadata_json),
                  "project_id": record.project_id,
                  "project_scope_hash": record.project_scope_hash,
                  "memory_id": record.memory_id,
                  "memory_type": record.memory_type,
                  "source": "memory_record",
                  "confidence_score": float(record.confidence_score),
              }
              try:
                  self.chroma.upsert_chunks(
                      project_id=record.project_id,
                      project_scope_hash=record.project_scope_hash,
                      chunks=[
                          {
                              "chunk_id": record.memory_id,
                              "content": record.content,
                              "metadata": metadata,
                          }
                      ],
                  )
                  self.repo.update_memory_index_state(record.memory_id, "indexed", indexed_at=_now(), index_error=None)
                  indexed += 1
              except Exception as exc:
                  self.repo.update_memory_index_state(
                      record.memory_id,
                      "failed",
                      indexed_at=None,
                      index_error=str(exc)[:2000],
                  )
                  failed += 1
          return {
              "ok": failed == 0,
              "status": "COMPLETE" if failed == 0 else "WARN",
              "summary": f"Reindexed {indexed} memory records; {failed} failed.",
              "indexed": indexed,
              "failed": failed,
              "project_scope_hash": project_scope_hash,
          }
  
      def semantic_search_active(self, query: str, k: int = 8) -> dict[str, Any]:
          if not query.strip():
              return self._error("invalid_query", "Query must not be empty.", status="POLICY_BLOCK")
          if k < 1 or k > 50:
              return self._error("invalid_k", "k must be between 1 and 50.", status="POLICY_BLOCK")
          active = self.active_repo.get_active_partition(self.client_id)
          if active is None or not active.active_project_id or not active.active_project_scope_hash:
              return self._error(
                  "no_active_partition",
                  "No active partition is available. Set an LM Studio folder first.",
                  status="NO_ACTIVE_PARTITION",
              )
          try:
              results = self.chroma.search(
                  active.active_project_id,
                  query,
                  k,
                  project_scope_hash=active.active_project_scope_hash,
              )
          except ChromaAdapterError as exc:
              return self._error("chroma_search_failed", f"Active memory search failed: {exc}")
          return {
              "ok": True,
              "status": "OK",
              "summary": f"Found {len(results)} active memory results.",
              "results": results,
              "artifacts": {},
              "active_partition": active.to_dict(),
          }
  
      def _error(self, code: str, summary: str, *, status: str = "ERROR") -> dict[str, Any]:
          return {
              "ok": False,
              "status": status,
              "summary": summary,
              "artifacts": {},
              "error": {"code": code, "message": summary},
          }

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

--- FILE: python-daemon/orchestrator/main.py ---
Size: 1896 bytes
Summary: Functions: maybe_import_skills, main
Content: |
  from __future__ import annotations
  
  import asyncio
  
  from .bridge_server import serve_tcp_bridge
  from .config import RuntimeConfig
  from .observability import configure_logging
  import logging
  from pathlib import Path
  
  from .runtime import build_runtime
  from .worker import DaemonWorker
  
  from orchestrator.skills.importer import SkillImporter
  from orchestrator.skills.registry import SkillRegistry
  
  
  def maybe_import_skills(config: RuntimeConfig) -> dict | None:
      if not config.skill_registry_root:
          return None
  
      registry_root = Path(config.skill_registry_root)
      # queue.db is located in the root state directory
      registry = SkillRegistry(config.state_dir / "queue.db")
      return SkillImporter(registry_root, registry).import_all()
  
  
  async def amain() -> None:
      config = RuntimeConfig.from_env()
      configure_logging(config.log_level)
      
      # Import skills but do not fail daemon on validation error
      import_report = maybe_import_skills(config)
      if import_report:
          logging.getLogger("aletheia").info(f"Skill import report: {import_report}")
          
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

--- FILE: python-daemon/tests/test_memory_service.py ---
Size: 8515 bytes
Summary: Classes: FakeResponse, FakeCollection, FakeChromaClient, MemoryServiceTests, BrokenCollection, BrokenChromaClient; Functions: __init__, raise_for_status, json, __init__, upsert, query, __init__, get_or_create_collection, test_commit_memory_stores_bounded_record_and_indexes_project_scope, test_commit_memory_marks_failed_when_chroma_upsert_fails_and_can_reindex, test_semantic_search_active_requires_active_partition, test_semantic_search_active_injects_active_scope_filter, upsert, __init__
Content: |
  from __future__ import annotations
  
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.active_partition.models import ActivePartition
  from orchestrator.active_partition.repo import ActivePartitionRepository
  from orchestrator.chroma_manager import ChromaConfig, ChromaManager
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.memory.models import MemoryRecord
  from orchestrator.memory.repo import MemoryRepository
  from orchestrator.memory.service import MemoryService
  
  
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
  
      def upsert(self, **kwargs):
          self.upserts.append(kwargs)
  
      def query(self, **kwargs):
          self.queries.append(kwargs)
          return {
              "ids": [["memory-1"]],
              "documents": [["memory result"]],
              "metadatas": [[{"project_scope_hash": kwargs["where"]["project_scope_hash"]}]],
              "distances": [[0.1]],
          }
  
  
  class FakeChromaClient:
      def __init__(self):
          self.collection = FakeCollection()
  
      def get_or_create_collection(self, name):
          return self.collection
  
  
  class MemoryServiceTests(unittest.TestCase):
      def test_commit_memory_stores_bounded_record_and_indexes_project_scope(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              active_repo.set_active_partition(
                  ActivePartition(
                      client_id="local-lmstudio",
                      active_project_id="lmstudio-client-a-backend-debug",
                      active_project_scope_hash="scope-1",
                      active_conversation_id="chat",
                      conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                      confidence="high",
                      source_event="manual_override",
                      updated_at="2026-01-01T00:00:01Z",
                  )
              )
              chroma = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                  chroma_client=FakeChromaClient(),
              )
              service = MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma)
  
              result = service.commit_memory(
                  "decision",
                  "This is a bounded memory record for the active partition." * 200,
                  metadata={"source_note": "unit-test"},
              )
              records = MemoryRepository(root / "queue.db").list_memory_records("scope-1")
  
              self.assertTrue(result["ok"])
              self.assertLessEqual(len(records[0].content), 8000)
              self.assertEqual(chroma.collection.upserts[0]["metadatas"][0]["project_scope_hash"], "scope-1")
              self.assertEqual(chroma.collection.upserts[0]["metadatas"][0]["source"], "memory_record")
              self.assertEqual(records[0].index_status, "indexed")
              self.assertIsNotNone(records[0].indexed_at)
  
      def test_commit_memory_marks_failed_when_chroma_upsert_fails_and_can_reindex(self):
          class BrokenCollection(FakeCollection):
              def upsert(self, **kwargs):
                  raise RuntimeError("vector store unavailable")
  
          class BrokenChromaClient(FakeChromaClient):
              def __init__(self):
                  self.collection = BrokenCollection()
  
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              active_repo.set_active_partition(
                  ActivePartition(
                      client_id="local-lmstudio",
                      active_project_id="lmstudio-client-a-backend-debug",
                      active_project_scope_hash="scope-1",
                      active_conversation_id="chat",
                      conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                      confidence="high",
                      source_event="manual_override",
                      updated_at="2026-01-01T00:00:01Z",
                  )
              )
              failing = MemoryService(
                  MemoryRepository(root / "queue.db"),
                  active_repo,
                  ChromaManager(
                      ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                      http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                      chroma_client=BrokenChromaClient(),
                  ),
              )
  
              failed = failing.commit_memory("decision", "This content is long enough to store.", metadata={"source_note": "unit-test"})
              failed_record = MemoryRepository(root / "queue.db").list_memory_records("scope-1")[0]
  
              self.assertFalse(failed["ok"])
              self.assertEqual(failed["index_status"], "failed")
              self.assertEqual(failed_record.index_status, "failed")
              self.assertIsNotNone(failed_record.index_error)
  
              recovering = MemoryService(
                  MemoryRepository(root / "queue.db"),
                  active_repo,
                  ChromaManager(
                      ChromaConfig(chroma_path=root / "chroma-retry", auto_load_embedding_model=False),
                      http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                      chroma_client=FakeChromaClient(),
                  ),
              )
              repaired = recovering.rebuild_memory_index_for_project("scope-1")
              refreshed = MemoryRepository(root / "queue.db").list_memory_records("scope-1")[0]
  
              self.assertEqual(repaired["indexed"], 1)
              self.assertEqual(refreshed.index_status, "indexed")
  
      def test_semantic_search_active_requires_active_partition(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              chroma = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                  chroma_client=FakeChromaClient(),
              )
              service = MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma)
  
              result = service.semantic_search_active("hello")
  
              self.assertFalse(result["ok"])
              self.assertEqual(result["status"], "NO_ACTIVE_PARTITION")
  
      def test_semantic_search_active_injects_active_scope_filter(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              active_repo.set_active_partition(
                  ActivePartition(
                      client_id="local-lmstudio",
                      active_project_id="lmstudio-client-a-backend-debug",
                      active_project_scope_hash="scope-1",
                      active_conversation_id="chat",
                      conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                      confidence="high",
                      source_event="manual_override",
                      updated_at="2026-01-01T00:00:01Z",
                  )
              )
              fake_client = FakeChromaClient()
              chroma = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                  chroma_client=fake_client,
              )
              service = MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma)
  
              result = service.semantic_search_active("hello")
  
              self.assertTrue(result["ok"])
              self.assertEqual(fake_client.collection.queries[0]["where"], {"project_scope_hash": "scope-1"})

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

--- FILE: python-daemon/tests/test_active_memory_tools.py ---
Size: 9966 bytes
Summary: Classes: FakeResponse, FakeCollection, FakeChromaClient, ActiveMemoryToolTests; Functions: __init__, raise_for_status, json, __init__, upsert, query, __init__, get_or_create_collection, test_mcp_get_active_partition_returns_persisted_partition, test_mcp_semantic_search_active_requires_partition_and_uses_scope, test_mcp_commit_memory_persists_record_and_indexes_scope, test_mcp_set_active_partition_accepts_only_conversation_path, test_mcp_set_active_project_manual_updates_partition
Content: |
  from __future__ import annotations
  
  import tempfile
  import unittest
  from pathlib import Path
  
  from orchestrator.active_partition.models import ActivePartition
  from orchestrator.active_partition.repo import ActivePartitionRepository
  from orchestrator.active_partition.service import ActivePartitionService
  from orchestrator.adapters import ToolAdapters
  from orchestrator.chroma_manager import ChromaConfig, ChromaManager
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.memory.repo import MemoryRepository
  from orchestrator.memory.service import MemoryService
  
  
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
  
      def upsert(self, **kwargs):
          self.upserts.append(kwargs)
  
      def query(self, **kwargs):
          self.queries.append(kwargs)
          return {
              "ids": [["memory-1"]],
              "documents": [["memory result"]],
              "metadatas": [[{"project_scope_hash": kwargs["where"]["project_scope_hash"]}]],
              "distances": [[0.1]],
          }
  
  
  class FakeChromaClient:
      def __init__(self):
          self.collection = FakeCollection()
  
      def get_or_create_collection(self, name):
          return self.collection
  
  
  class ActiveMemoryToolTests(unittest.TestCase):
      def test_mcp_get_active_partition_returns_persisted_partition(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              active_repo.set_active_partition(
                  ActivePartition(
                      client_id="local-lmstudio",
                      active_project_id="lmstudio-client-a-backend-debug",
                      active_project_scope_hash="scope-1",
                      active_conversation_id="chat",
                      conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                      confidence="high",
                      source_event="manual_override",
                      updated_at="2026-01-01T00:00:01Z",
                  )
              )
              adapters = ToolAdapters(
                  active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations"),
                  memory_service=MemoryService(
                      MemoryRepository(root / "queue.db"),
                      active_repo,
                      ChromaManager(
                          ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                          http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                          chroma_client=FakeChromaClient(),
                      ),
                  ),
              )
  
              result = adapters.call_mcp_tool("mcp_get_active_partition", {})
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["partition"]["active_project_scope_hash"], "scope-1")
  
      def test_mcp_semantic_search_active_requires_partition_and_uses_scope(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              fake_client = FakeChromaClient()
              chroma = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                  chroma_client=fake_client,
              )
              adapters = ToolAdapters(
                  active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations"),
                  memory_service=MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma),
              )
  
              missing = adapters.call_mcp_tool("mcp_semantic_search_active", {"query": "hello"})
              active_repo.set_active_partition(
                  ActivePartition(
                      client_id="local-lmstudio",
                      active_project_id="lmstudio-client-a-backend-debug",
                      active_project_scope_hash="scope-1",
                      active_conversation_id="chat",
                      conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                      confidence="high",
                      source_event="manual_override",
                      updated_at="2026-01-01T00:00:01Z",
                  )
              )
              result = adapters.call_mcp_tool("mcp_semantic_search_active", {"query": "hello", "k": 3})
  
              self.assertEqual(missing["status"], "NO_ACTIVE_PARTITION")
              self.assertTrue(result["ok"])
              self.assertEqual(fake_client.collection.queries[0]["where"], {"project_scope_hash": "scope-1"})
  
      def test_mcp_commit_memory_persists_record_and_indexes_scope(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              active_repo.set_active_partition(
                  ActivePartition(
                      client_id="local-lmstudio",
                      active_project_id="lmstudio-client-a-backend-debug",
                      active_project_scope_hash="scope-1",
                      active_conversation_id="chat",
                      conversation_path=str(root / "conversations" / "client-a" / "backend-debug" / "chat.json"),
                      confidence="high",
                      source_event="manual_override",
                      updated_at="2026-01-01T00:00:01Z",
                  )
              )
              fake_client = FakeChromaClient()
              chroma = ChromaManager(
                  ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                  http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                  chroma_client=fake_client,
              )
              adapters = ToolAdapters(
                  active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations"),
                  memory_service=MemoryService(MemoryRepository(root / "queue.db"), active_repo, chroma),
              )
  
              result = adapters.call_mcp_tool(
                  "mcp_commit_memory",
                  {
                      "category": "decision",
                      "content": "This is a bounded memory record for the active partition.",
                      "metadata": {"source_note": "unit-test"},
                  },
              )
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["project_scope_hash"], "scope-1")
              self.assertEqual(fake_client.collection.upserts[0]["metadatas"][0]["project_scope_hash"], "scope-1")
  
      def test_mcp_set_active_partition_accepts_only_conversation_path(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              conversations = root / "conversations" / "client-a" / "backend-debug"
              conversations.mkdir(parents=True)
              conversation = conversations / "chat.conversation.json"
              conversation.write_text("{}", encoding="utf-8")
              adapters = ToolAdapters(
                  active_partition=ActivePartitionService(ActivePartitionRepository(root / "queue.db"), conversations_root=root / "conversations", allowed_roots=(root,)),
                  memory_service=MemoryService(
                      MemoryRepository(root / "queue.db"),
                      ActivePartitionRepository(root / "queue.db"),
                      ChromaManager(
                          ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                          http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                          chroma_client=FakeChromaClient(),
                      ),
                  ),
              )
  
              blocked = adapters.call_mcp_tool("mcp_set_active_partition", {"project_id": "p"})
              result = adapters.call_mcp_tool("mcp_set_active_partition", {"conversation_path": str(conversation)})
  
              self.assertEqual(blocked["status"], "POLICY_BLOCK")
              self.assertTrue(result["ok"])
              self.assertEqual(result["partition"]["active_project_id"], "lmstudio-client-a-backend-debug")
  
      def test_mcp_set_active_project_manual_updates_partition(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              active_repo = ActivePartitionRepository(root / "queue.db")
              adapters = ToolAdapters(
                  active_partition=ActivePartitionService(active_repo, conversations_root=root / "conversations", allowed_roots=(root,)),
                  memory_service=MemoryService(
                      MemoryRepository(root / "queue.db"),
                      active_repo,
                      ChromaManager(
                          ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                          http_post=lambda **_: FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
                          chroma_client=FakeChromaClient(),
                      ),
                  ),
              )
  
              result = adapters.call_mcp_tool(
                  "mcp_set_active_project_manual",
                  {"project_id": "lmstudio-client-a-backend-debug", "display_name": "client-a / backend-debug"},
              )
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["partition"]["active_project_id"], "lmstudio-client-a-backend-debug")

--- FILE: python-daemon/orchestrator/adapters.py ---
Size: 19673 bytes
Summary: Classes: AdapterFailure, SemanticMemoryAdapter, OCRProvider, WorkspaceScoutAdapter, ActivePartitionAdapter, FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters; Functions: search, ingest_target, extract_image_text, scout, get_active_partition, set_active_from_conversation_path, set_active_project, list_memory_projects, __init__, _resolve, read_file, read_file_snippet, list_directory, package_directory, verify_integrity, __init__, _resolve, query, __init__, call_mcp_tool
Content: |
  from __future__ import annotations
  
  import hashlib
  import json
  import os
  import sqlite3
  from pathlib import Path
  from typing import Any, Protocol
  
  from .active_partition.models import ActivePartition, MemoryProject
  from .active_partition.service import ActivePartitionService, ActivePartitionServiceError
  from .agent_workflow.mcp_tool import run_agent_workflow
  from .memory.service import MemoryService
  from .tool_assist_adapter import ToolAssistAdapter
  
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
  
  
  class ActivePartitionAdapter(Protocol):
      def get_active_partition(self) -> ActivePartition | None:
          ...
  
      def set_active_from_conversation_path(self, conversation_json_path: str, source_event: str = "manual_override") -> ActivePartition:
          ...
  
      def set_active_project(self, project_id: str, display_name: str | None = None) -> ActivePartition:
          ...
  
      def list_memory_projects(self) -> list[MemoryProject]:
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
          tool_assist: ToolAssistAdapter | None = None,
          active_partition: ActivePartitionService | None = None,
          memory_service: MemoryService | None = None,
          allowed_roots: tuple[Path, ...] | None = None,
          skill_registry_root: Path | None = None,
      ) -> None:
          self.semantic_memory = semantic_memory
          self.file_tools = file_tools
          self.sqlite_tools = sqlite_tools
          self.workspace_scout = workspace_scout
          self.ocr_provider = ocr_provider
          self.tool_assist = tool_assist or ToolAssistAdapter()
          self.active_partition = active_partition
          self.memory_service = memory_service
          self.allowed_roots = tuple(root.resolve() for root in (allowed_roots or ()))
          self.skill_registry_root = Path(skill_registry_root).resolve() if skill_registry_root is not None else None
  
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
              if tool_name == "mcp_get_active_partition":
                  if self.active_partition is None:
                      raise AdapterFailure("active partition service is not configured")
                  partition = self.active_partition.get_active_partition()
                  if partition is None:
                      return {
                          "ok": False,
                          "status": "NO_ACTIVE_PARTITION",
                          "summary": "No active partition is available.",
                          "artifacts": {},
                          "error": {"code": "no_active_partition", "message": "No active partition is available."},
                      }
                  return {"ok": True, "status": "OK", "summary": "Active partition loaded.", "partition": partition.to_dict(), "artifacts": {}}
              if tool_name == "mcp_set_active_partition":
                  if self.active_partition is None:
                      raise AdapterFailure("active partition service is not configured")
                  if "project_id" in args:
                      return {
                          "ok": False,
                          "status": "POLICY_BLOCK",
                          "summary": "mcp_set_active_partition accepts only conversation_path.",
                          "artifacts": {},
                          "error": {"code": "invalid_active_partition_input", "message": "mcp_set_active_partition accepts only conversation_path."},
                      }
                  try:
                      if not args.get("conversation_path"):
                          return {
                              "ok": False,
                              "status": "POLICY_BLOCK",
                              "summary": "conversation_path is required.",
                              "artifacts": {},
                              "error": {"code": "missing_active_partition_input", "message": "conversation_path is required."},
                          }
                      partition = self.active_partition.set_active_from_conversation_path(
                          str(args["conversation_path"]),
                          str(args.get("source_event", "manual_override")),
                      )
                  except ActivePartitionServiceError as exc:
                      return {
                          "ok": False,
                          "status": exc.code,
                          "summary": exc.message,
                          "artifacts": {},
                          "error": exc.to_dict(),
                      }
                  return {"ok": True, "status": "OK", "summary": "Active partition updated.", "partition": partition.to_dict(), "artifacts": {}}
              if tool_name == "mcp_set_active_project_manual":
                  if self.active_partition is None:
                      raise AdapterFailure("active partition service is not configured")
                  if "project_id" not in args:
                      return {
                          "ok": False,
                          "status": "POLICY_BLOCK",
                          "summary": "project_id is required.",
                          "artifacts": {},
                          "error": {"code": "missing_active_project_id", "message": "project_id is required."},
                      }
                  try:
                      partition = self.active_partition.set_active_project(
                          str(args["project_id"]),
                          display_name=args.get("display_name"),
                      )
                  except ActivePartitionServiceError as exc:
                      return {
                          "ok": False,
                          "status": exc.code,
                          "summary": exc.message,
                          "artifacts": {},
                          "error": exc.to_dict(),
                      }
                  return {"ok": True, "status": "OK", "summary": "Active project override updated.", "partition": partition.to_dict(), "artifacts": {}}
              if tool_name == "mcp_list_memory_projects":
                  if self.active_partition is None:
                      raise AdapterFailure("active partition service is not configured")
                  projects = [project.to_dict() for project in self.active_partition.list_memory_projects()]
                  return {"ok": True, "status": "OK", "summary": f"Loaded {len(projects)} memory projects.", "projects": projects, "artifacts": {}}
              if tool_name == "mcp_semantic_search_active":
                  if self.memory_service is None:
                      raise AdapterFailure("memory service is not configured")
                  return self.memory_service.semantic_search_active(str(args["query"]), int(args.get("k", 8)))
              if tool_name == "mcp_commit_memory":
                  if self.memory_service is None:
                      raise AdapterFailure("memory service is not configured")
                  metadata = args.get("metadata")
                  if metadata is not None and not isinstance(metadata, dict):
                      raise AdapterFailure("metadata must be an object")
                  return self.memory_service.commit_memory(
                      str(args["category"]),
                      str(args["content"]),
                      float(args.get("confidence_score", 1.0)),
                      metadata=metadata,
                  )
              if tool_name == "mcp_agent_workflow_run":
                  objective = args.get("objective")
                  target_repo = args.get("target_repo")
                  if not isinstance(objective, str) or not isinstance(target_repo, str):
                      return {
                          "ok": False,
                          "status": "POLICY_BLOCK",
                          "summary": "objective and target_repo are required.",
                          "artifacts": {},
                          "error": {"code": "missing_workflow_input", "message": "objective and target_repo are required."},
                      }
                  return run_agent_workflow(
                      objective=objective,
                      target_repo=target_repo,
                      profile=str(args.get("profile", "safe")),
                      allow_ingest=bool(args.get("allow_ingest", False)),
                      include_report_preview=bool(args.get("include_report_preview", False)),
                      use_model_phases=bool(args.get("use_model_phases", False)),
                      allowed_roots=self.allowed_roots if self.allowed_roots else None,
                      skill_registry_root=self.skill_registry_root,
                  )
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
              if tool_name == "mcp_investigation_start":
                  if self.tool_assist is None:
                      raise AdapterFailure("tool assist adapter is not configured")
                  return self.tool_assist.investigation_start(
                      str(args["objective"]),
                      str(args["target_repo"]),
                      str(args.get("profile", "safe")),
                  )
              if tool_name == "mcp_investigation_filemap":
                  if self.tool_assist is None:
                      raise AdapterFailure("tool assist adapter is not configured")
                  return self.tool_assist.investigation_filemap(
                      str(args["session_path"]),
                      str(args.get("profile", "safe")),
                  )
              if tool_name == "mcp_investigation_validate_manifest":
                  if self.tool_assist is None:
                      raise AdapterFailure("tool assist adapter is not configured")
                  return self.tool_assist.investigation_validate_manifest(str(args["session_path"]))
              if tool_name == "mcp_investigation_read_report":
                  if self.tool_assist is None:
                      raise AdapterFailure("tool assist adapter is not configured")
                  return self.tool_assist.investigation_read_report(
                      str(args["session_path"]),
                      str(args["artifact_key"]),
                      int(args.get("max_chars", 12000)),
                  )
              if tool_name == "mcp_investigation_compile_handoff":
                  if self.tool_assist is None:
                      raise AdapterFailure("tool assist adapter is not configured")
                  return self.tool_assist.investigation_compile_handoff(str(args["session_path"]))
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

--- FILE: python-daemon/tests/test_processors_and_tools.py ---
Size: 9703 bytes
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

--- FILE: python-daemon/tests/test_agent_workflow.py ---
Size: 15088 bytes
Summary: Classes: FakeBridgeClient, FakeCollection, FakeChromaClient, FakeSkillRegistry, WorkflowToolTests; Functions: __init__, call_tool, upsert, query, __init__, get_or_create_collection, __init__, list_verified, test_invalid_target_repo_is_blocked_before_state_is_created, test_nonexistent_or_outside_target_repo_is_blocked, test_workflow_run_returns_compact_state_and_response, test_tool_adapter_calls_workflow_helper_once, test_workflow_selects_bug_triage_skill_metadata, test_workflow_selects_candidate_analysis_skill_metadata, test_workflow_selects_refactor_plan_skill_metadata, test_workflow_sets_selected_skill_null_when_no_manifest_matches, test_workflow_records_registry_warning_when_registry_fails
Content: |
  from __future__ import annotations
  
  import json
  import tempfile
  import unittest
  from pathlib import Path
  from unittest.mock import patch
  
  from orchestrator.agent_workflow.mcp_tool import run_agent_workflow
  from orchestrator.adapters import ToolAdapters
  from orchestrator.active_partition.models import ActivePartition
  from orchestrator.active_partition.repo import ActivePartitionRepository
  from orchestrator.chroma_manager import ChromaConfig, ChromaManager
  from orchestrator.db_bootstrap import bootstrap_databases
  from orchestrator.memory.repo import MemoryRepository
  from orchestrator.memory.service import MemoryService
  from orchestrator.active_partition.service import ActivePartitionService
  
  
  class FakeBridgeClient:
      def __init__(self):
          self.calls: list[tuple[str, dict[str, object]]] = []
  
      def call_tool(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
          self.calls.append((tool_name, dict(args)))
          if tool_name == "mcp_investigation_start":
              return {
                  "ok": True,
                  "status": "PASS",
                  "summary": "session started",
                  "artifacts": {
                      "session_path": "C:/work/session.yaml",
                      "session_yaml": "C:/work/session.yaml",
                  },
              }
          if tool_name == "mcp_investigation_filemap":
              return {
                  "ok": True,
                  "status": "PASS",
                  "summary": "file map complete",
                  "artifacts": {"manifest_csv": "C:/work/manifest.csv"},
              }
          if tool_name == "mcp_investigation_validate_manifest":
              return {
                  "ok": True,
                  "status": "PASS",
                  "summary": "manifest validated",
                  "artifacts": {"manifest_health_json": "C:/work/manifest-health.json", "manifest_doctor_json": "C:/work/manifest-doctor.json"},
              }
          if tool_name == "mcp_investigation_read_report":
              return {
                  "ok": True,
                  "status": "PASS",
                  "summary": "report read",
                  "content": "X" * 5000,
                  "artifacts": {"manifest_doctor_md": "C:/work/manifest-doctor.md"},
              }
          if tool_name == "mcp_investigation_compile_handoff":
              return {
                  "ok": True,
                  "status": "COMPLETE",
                  "summary": "handoff complete",
                  "artifacts": {
                      "final_markdown": "C:/work/final.md",
                      "final_python_bundle": "C:/work/final.py",
                      "archive_yaml": "C:/work/archive.yaml",
                  },
              }
          return {"ok": False, "status": "ERROR", "summary": f"unexpected tool {tool_name}", "artifacts": {}}
  
  
  class FakeCollection:
      def upsert(self, **kwargs):
          return None
  
      def query(self, **kwargs):
          return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
  
  
  class FakeChromaClient:
      def __init__(self):
          self.collection = FakeCollection()
  
      def get_or_create_collection(self, name):
          return self.collection
  
  
  class FakeSkillRegistry:
      def __init__(self, queue_db_path, manifests=None, *, fail=False):
          self.queue_db_path = Path(queue_db_path)
          self.manifests = list(manifests or [])
          self.fail = fail
          self.list_calls = 0
  
      def list_verified(self):
          self.list_calls += 1
          if self.fail:
              raise RuntimeError("skill registry unavailable")
          return list(self.manifests)
  
  
  BUG_TRIAGE_MANIFESTS = [
      {
          "skill_id": "bug_triage_v1",
          "triggers": ["triage bug", "regression", "diagnose"],
          "capabilities": ["bug_triage", "candidate_analysis", "tdd_planning", "root_cause_analysis"],
          "risk_tier": "T1",
      },
      {
          "skill_id": "candidate_analysis_v1",
          "triggers": ["candidate analysis", "rank files", "likely files"],
          "capabilities": ["candidate_analysis", "file_ranking"],
          "risk_tier": "T1",
      },
      {
          "skill_id": "refactor_plan_v1",
          "triggers": ["refactor plan", "technical debt plan", "rewrite plan"],
          "capabilities": ["refactor_planning"],
          "risk_tier": "T1",
      },
  ]
  
  
  class WorkflowToolTests(unittest.TestCase):
      def test_invalid_target_repo_is_blocked_before_state_is_created(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "states"
              result = run_agent_workflow(
                  objective="Investigate backend",
                  target_repo="backend-orchestrator-repo",
                  profile="safe",
                  state_dir=state_dir,
                  allowed_roots=(root,),
                  bridge_client=FakeBridgeClient(),
              )
  
              self.assertFalse(result["ok"])
              self.assertEqual(result["status"], "POLICY_BLOCK")
              self.assertEqual(result["error"]["code"], "invalid_target_repo")
              self.assertFalse(state_dir.exists())
  
      def test_nonexistent_or_outside_target_repo_is_blocked(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "states"
              outside = root.parent / "outside-workspace"
              outside.mkdir(exist_ok=True)
              missing = root / "missing-workspace"
  
              missing_result = run_agent_workflow(
                  objective="Investigate backend",
                  target_repo=str(missing),
                  profile="safe",
                  state_dir=state_dir,
                  allowed_roots=(root,),
                  bridge_client=FakeBridgeClient(),
              )
              outside_result = run_agent_workflow(
                  objective="Investigate backend",
                  target_repo=str(outside),
                  profile="safe",
                  state_dir=state_dir,
                  allowed_roots=(root,),
                  bridge_client=FakeBridgeClient(),
              )
  
              self.assertEqual(missing_result["error"]["code"], "invalid_target_repo")
              self.assertEqual(outside_result["error"]["code"], "invalid_target_repo")
  
      def test_workflow_run_returns_compact_state_and_response(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "agent-workflows"
              result = run_agent_workflow(
                  objective="Investigate backend",
                  target_repo=str(root),
                  profile="safe",
                  state_dir=state_dir,
                  allowed_roots=(root,),
                  bridge_client=FakeBridgeClient(),
              )
              state_path = Path(result["state_path"])
              state = json.loads(state_path.read_text(encoding="utf-8"))
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["status"], "COMPLETE")
              self.assertNotIn("C:/work/", result["summary"])
              self.assertTrue(state_path.exists())
              self.assertEqual(state["phase"], "FINAL")
              self.assertEqual(state["tool_results"][3]["content_omitted"], True)
              self.assertNotIn("content", state["tool_results"][3])
              self.assertEqual(state["tool_results"][3]["summary"], "report read")
              self.assertEqual(state["artifacts"]["session_path"], "C:/work/session.yaml")
              self.assertEqual(result["artifacts"]["session_yaml"], "C:/work/session.yaml")
              self.assertIn("manifest_csv", result["artifacts"])
              self.assertIn("manifest_health_json", result["artifacts"])
              self.assertIn("manifest_doctor_json", result["artifacts"])
              self.assertIn("manifest_doctor_md", result["artifacts"])
              self.assertIn("final_markdown", result["artifacts"])
              self.assertIn("final_python_bundle", result["artifacts"])
              self.assertIn("archive_yaml", result["artifacts"])
              self.assertNotIn("[", result["summary"])
  
      def test_tool_adapter_calls_workflow_helper_once(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              bootstrap_databases(root)
              repo = ActivePartitionRepository(root / "queue.db")
              active = ActivePartitionService(repo, conversations_root=root / "conversations", allowed_roots=(root,))
              memory = MemoryService(
                  MemoryRepository(root / "queue.db"),
                  repo,
                  ChromaManager(
                      ChromaConfig(chroma_path=root / "chroma", auto_load_embedding_model=False),
                      chroma_client=FakeChromaClient(),
                  ),
              )
              adapters = ToolAdapters(active_partition=active, memory_service=memory, allowed_roots=(root,))
  
              with patch("orchestrator.adapters.run_agent_workflow") as mocked:
                  mocked.return_value = {"ok": True, "status": "COMPLETE", "run_id": "r1", "summary": "done", "artifacts": {}, "state_path": "state.json", "error": None}
                  result = adapters.call_mcp_tool(
                      "mcp_agent_workflow_run",
                      {"objective": "Investigate", "target_repo": str(root), "profile": "safe"},
                  )
  
              self.assertTrue(result["ok"])
              self.assertEqual(mocked.call_count, 1)
  
      def test_workflow_selects_bug_triage_skill_metadata(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "agent-workflows"
              with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                  with patch("orchestrator.agent_workflow.mcp_tool.SkillImporter.import_all") as mocked_import:
                      mocked_import.side_effect = AssertionError("SKILL.md import should not run during metadata-only selection")
                      result = run_agent_workflow(
                          objective="Triage this regression in the backend and identify the root cause.",
                          target_repo=str(root),
                          profile="safe",
                          state_dir=state_dir,
                          allowed_roots=(root,),
                          bridge_client=FakeBridgeClient(),
                      )
  
              state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
              selected = result["artifacts"]["selected_skill"]
  
              self.assertTrue(result["ok"])
              self.assertEqual(selected["skill_id"], "bug_triage_v1")
              self.assertEqual(selected["source"], "skill_registry")
              self.assertFalse(selected["instruction_loaded"])
              self.assertEqual(state["selected_skill"]["skill_id"], "bug_triage_v1")
              self.assertFalse(state.get("warnings"))
  
      def test_workflow_selects_candidate_analysis_skill_metadata(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "agent-workflows"
              with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                  result = run_agent_workflow(
                      objective="Rank candidate files for the likely fix location.",
                      target_repo=str(root),
                      profile="safe",
                      state_dir=state_dir,
                      allowed_roots=(root,),
                      bridge_client=FakeBridgeClient(),
                  )
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["artifacts"]["selected_skill"]["skill_id"], "candidate_analysis_v1")
              self.assertIn("capabilities", result["artifacts"]["selected_skill"])
  
      def test_workflow_selects_refactor_plan_skill_metadata(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "agent-workflows"
              with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, BUG_TRIAGE_MANIFESTS)):
                  result = run_agent_workflow(
                      objective="Create a refactor plan for the service layer.",
                      target_repo=str(root),
                      profile="safe",
                      state_dir=state_dir,
                      allowed_roots=(root,),
                      bridge_client=FakeBridgeClient(),
                  )
  
              self.assertTrue(result["ok"])
              self.assertEqual(result["artifacts"]["selected_skill"]["skill_id"], "refactor_plan_v1")
  
      def test_workflow_sets_selected_skill_null_when_no_manifest_matches(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "agent-workflows"
              with patch(
                  "orchestrator.agent_workflow.mcp_tool.SkillRegistry",
                  lambda queue_db_path: FakeSkillRegistry(
                      queue_db_path,
                      [
                          {
                              "skill_id": "architecture_review_v1",
                              "triggers": ["architecture review"],
                              "capabilities": ["architecture_review"],
                              "risk_tier": "T1",
                          }
                      ],
                  ),
              ):
                  result = run_agent_workflow(
                      objective="Draft a release note for the team.",
                      target_repo=str(root),
                      profile="safe",
                      state_dir=state_dir,
                      allowed_roots=(root,),
                      bridge_client=FakeBridgeClient(),
                  )
  
              state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
  
              self.assertTrue(result["ok"])
              self.assertIsNone(result["artifacts"]["selected_skill"])
              self.assertIsNone(state["selected_skill"])
  
      def test_workflow_records_registry_warning_when_registry_fails(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              state_dir = root / "agent-workflows"
              with patch("orchestrator.agent_workflow.mcp_tool.SkillRegistry", lambda queue_db_path: FakeSkillRegistry(queue_db_path, fail=True)):
                  result = run_agent_workflow(
                      objective="Investigate a backend bug report.",
                      target_repo=str(root),
                      profile="safe",
                      state_dir=state_dir,
                      allowed_roots=(root,),
                      bridge_client=FakeBridgeClient(),
                  )
  
              state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
  
              self.assertTrue(result["ok"])
              self.assertIsNone(result["artifacts"]["selected_skill"])
              self.assertTrue(state["warnings"])
              self.assertEqual(state["warnings"][0]["source"], "skill_registry")

--- FILE: python-daemon/orchestrator/runtime.py ---
Size: 4656 bytes
Summary: Classes: RuntimeComponents; Functions: build_runtime, health, reconcile_project, dead_letters, close
Content: |
  from __future__ import annotations
  
  from dataclasses import dataclass
  
  from .adapters import FileToolAdapter, ReadOnlySqliteAdapter, ToolAdapters
  from .active_partition.repo import ActivePartitionRepository
  from .active_partition.service import ActivePartitionService
  from .bridge_server import BridgeSecurity
  from .chroma_manager import ChromaConfig, ChromaManager
  from .config import RuntimeConfig
  from .memory.repo import MemoryRepository
  from .memory.service import MemoryService
  from .tool_assist_adapter import ToolAssistAdapter
  from .db_bootstrap import bootstrap_databases
  from .execution_loop import ExecutionLoop
  from .ingest.processors import WorkspaceScout
  from .ingest.processors import PdfProcessorAdapter
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
      active_partition_repo = ActivePartitionRepository(repo.queue_db)
      memory_repo = MemoryRepository(repo.queue_db)
      active_partition = ActivePartitionService(
          active_partition_repo,
          conversations_root=config.lmstudio_conversations_dir,
          allowed_roots=config.allowed_roots,
      )
      memory_service = MemoryService(memory_repo, active_partition_repo, chroma)
      file_tools = FileToolAdapter(config.allowed_roots)
      sqlite_tools = ReadOnlySqliteAdapter(config.allowed_roots)
      scout = WorkspaceScout(config.allowed_roots)
      shell_adapter = ShellAdapter(config.allowed_roots)
      ocr_provider = CommandOCRProvider(shell_adapter=shell_adapter, command=config.ocr_command) if config.ocr_command else None
      pdf_processor = PdfProcessorAdapter(ocr_provider=ocr_provider)
      ingest = IngestTargetService(repo, chroma, allowed_roots=config.allowed_roots, pdf_processor=pdf_processor)
      tool_adapters = ToolAdapters(
          semantic_memory=ingest,
          file_tools=file_tools,
          sqlite_tools=sqlite_tools,
          workspace_scout=scout,
          ocr_provider=ocr_provider,
          tool_assist=ToolAssistAdapter(),
          active_partition=active_partition,
          memory_service=memory_service,
          allowed_roots=config.allowed_roots,
          skill_registry_root=config.skill_registry_root,
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

--- FILE: python-daemon/tests/test_runtime_daemon.py ---
Size: 22304 bytes
Summary: Classes: FakeToolAdapters, RuntimeDaemonTests, FakeResponseForLMStudio, LMStudioManagerTests, Internal, Internal; Functions: __init__, call_mcp_tool, test_runtime_config_loads_paths_and_bridge_from_env, test_runtime_config_project_id_override, test_build_runtime_bootstraps_components_and_databases, test_runtime_wires_ocr_provider_into_pdf_ingest, test_worker_executes_payload_tool_and_completes_task, test_worker_registers_and_heartbeats_process_registry, test_worker_dead_letters_invalid_task_payload, test_lease_recovery_releases_expired_leases, test_migrations_record_initial_version_and_reject_unknown_future_version, test_invalid_task_transition_is_rejected_and_valid_transition_is_audited, test_bridge_rejects_oversized_or_unauthorized_requests, test_bridge_accepts_hmac_auth_and_rejects_unknown_methods, test_bridge_includes_nonce_in_auth_and_prevents_replay, test_bridge_admin_gating_blocks_daemon_methods_when_disabled, test_bridge_admin_gating_allows_daemon_methods_when_enabled, test_bridge_admin_gating_blocks_daemon_methods_when_shared_secret_none, test_nonce_cache_bounds_entries, test_internal_health_and_dead_letter_methods_are_available, test_operator_readme_exists, test_runtime_config_defaults_embedding_model_to_correct_lm_studio_key, __init__, raise_for_status, json, test_connection_summary_reports_token_presence_without_leaking_token, test_list_models_accepts_models_and_data_keys, test_ensure_embedding_model_loaded_rejects_non_embedding_model, test_ensure_embedding_model_loaded_loads_unloaded_model, test_ensure_embedding_model_loaded_skips_when_exact_loaded_instance_present, test_ensure_embedding_model_loaded_skips_when_suffixed_loaded_instance_present, test_ensure_embedding_model_loaded_warns_on_multiple_loaded_instances, test_concurrent_ensure_embedding_model_loaded_calls_only_load_once, test_401_from_list_models_gives_clear_token_error, get, get, get, post, get, post, get, post, get, post, get, post, worker, get, health, health, dead_letters
Content: |
  import json
  import sqlite3
  import tempfile
  import unittest
  from collections import deque
  from contextlib import closing
  from pathlib import Path
  import threading
  import time
  
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
  
      def test_runtime_wires_ocr_provider_into_pdf_ingest(self):
          with tempfile.TemporaryDirectory() as tmp:
              root = Path(tmp)
              config = RuntimeConfig.from_env(
                  {
                      "ALETHEIA_PROJECT_ROOT": str(root),
                      "ALETHEIA_STATE_DIR": str(root / "state"),
                      "ALETHEIA_ALLOWED_ROOTS": str(root),
                      "ALETHEIA_CHROMA_PATH": str(root / "chroma"),
                      "ALETHEIA_OCR_COMMAND": "ocr-binary",
                  }
              )
  
              runtime = build_runtime(config)
  
              try:
                  self.assertIsNotNone(runtime.ingest.pdf_processor.ocr_provider)
                  self.assertIs(runtime.ingest.pdf_processor.ocr_provider, runtime.tool_adapters.ocr_provider)
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
                  self.assertEqual(
                      [row[0] for row in rows],
                      [
                          "0001_initial",
                          "0002_active_partition_memory",
                          "0003_memory_index_state",
                          "0004_skill_manifests",
                      ],
                  )
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
      def test_connection_summary_reports_token_presence_without_leaking_token(self):
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
  
          with_token = LMStudioManager(LMStudioManagerConfig(api_token="super-secret"))
          without_token = LMStudioManager(LMStudioManagerConfig())
  
          self.assertTrue(with_token.connection_summary()["token_present"])
          self.assertFalse(without_token.connection_summary()["token_present"])
          self.assertNotIn("super-secret", json.dumps(with_token.connection_summary()))= [REDACTED_HIGH_ENTROPY]
  
      def test_list_models_accepts_models_and_data_keys(self):
          calls = []
          def get(url, headers=None, timeout=None):
              calls.append((url, headers))
              return FakeResponseForLMStudio({"models": [{"key": "model1", "type": "embedding", "state": "loaded", "loaded_instances": [{"id": "model1"}]}]})
  
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
              return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "state": "unloaded", "loaded_instances": []}]})
  
          def post(url, json=None, **kwargs):
              post_calls.append((url, json))
              return FakeResponseForLMStudio({})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)
  
          manager.ensure_embedding_model_loaded("embed-model")
  
          self.assertEqual(len(post_calls), 1)
          self.assertEqual(post_calls[0][0], "http= [REDACTED_HIGH_ENTROPY]
          self.assertEqual(post_calls[0][1], {"model": "embed-model"})
  
      def test_ensure_embedding_model_loaded_skips_when_exact_loaded_instance_present(self):
          post_calls = []
  
          def get(url, **kwargs):
              return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "loaded_instances": [{"id": "embed-model"}], "state": "loaded"}]})
  
          def post(url, **kwargs):
              post_calls.append(url)
              return FakeResponseForLMStudio({})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)
  
          manager.ensure_embedding_model_loaded("embed-model")
  
          self.assertEqual(post_calls, [])
  
      def test_ensure_embedding_model_loaded_skips_when_suffixed_loaded_instance_present(self):
          post_calls = []
  
          def get(url, **kwargs):
              return FakeResponseForLMStudio({"models": [{"key": "embed-model", "type": "embedding", "loaded_instances": [{"id": "embed-model:4"}], "state": "loaded"}]})
  
          def post(url, **kwargs):
              post_calls.append(url)
              return FakeResponseForLMStudio({})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)
  
          manager.ensure_embedding_model_loaded("embed-model")
  
          self.assertEqual(post_calls, [])
  
      def test_ensure_embedding_model_loaded_warns_on_multiple_loaded_instances(self):
          post_calls = []
  
          def get(url, **kwargs):
              return FakeResponseForLMStudio({
                  "models": [
                      {
                          "key": "embed-model",
                          "type": "embedding",
                          "loaded_instances": [{"id": "embed-model"}, {"id": "embed-model:2"}],
                          "state": "loaded",
                      }
                  ]
              })
  
          def post(url, **kwargs):
              post_calls.append(url)
              return FakeResponseForLMStudio({})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)
  
          with self.assertLogs("orchestrator.lm_studio_manager", level="WARNING") as logs:
              manager.ensure_embedding_model_loaded("embed-model")
  
          self.assertEqual(post_calls, [])
          self.assertTrue(any("multiple loaded instances" in line for line in logs.output))
  
      def test_concurrent_ensure_embedding_model_loaded_calls_only_load_once(self):
          state = {"loaded": False, "get_calls": 0, "post_calls": 0}
          state_lock = threading.Lock()
  
          def get(url, **kwargs):
              with state_lock:
                  state["get_calls"] += 1
                  call_number = state["get_calls"]
                  loaded = state["loaded"]
              if call_number == 1:
                  time.sleep(0.05)
              payload = {
                  "models": [
                      {
                          "key": "embed-model",
                          "type": "embedding",
                          "state": "loaded" if loaded else "unloaded",
                          "loaded_instances": [{"id": "embed-model"}] if loaded else [],
                      }
                  ]
              }
              return FakeResponseForLMStudio(payload)
  
          def post(url, json=None, **kwargs):
              with state_lock:
                  state["post_calls"] += 1
                  state["loaded"] = True
              return FakeResponseForLMStudio({})
  
          from orchestrator.lm_studio_manager import LMStudioManager, LMStudioManagerConfig
          manager = LMStudioManager(LMStudioManagerConfig(), http_get=get, http_post=post)
  
          errors: list[BaseException] = []
  
          def worker():
              try:
                  manager.ensure_embedding_model_loaded("embed-model")
              except BaseException as exc:
                  errors.append(exc)
  
          threads = [threading.Thread(target=worker) for _ in range(2)]
          for thread in threads:
              thread.start()
          for thread in threads:
              thread.join()
  
          self.assertEqual(state["post_calls"], 1)
          self.assertEqual(errors, [])
  
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
