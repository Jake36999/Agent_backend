# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Aletheia — a local-first MCP-compatible agentic orchestrator. Python daemon handles state, memory, tool dispatch, and workflow execution. Node.js gateway provides strict JSON Schema contract validation and forwards to the daemon via TCP JSON-RPC with optional HMAC-SHA256 auth.

## Commands

### Python daemon (from `backend/python-daemon/`)
```bash
pip install -e .                           # editable install
python -m pytest -v                        # full test suite
python -m pytest tests/test_foo.py -v      # single file
python -m pytest tests/test_foo.py::Class::test_method -v  # single test
```

### Node MCP gateway (from `backend/node-mcp/`)
```bash
npm install
npm test                                   # runs node test/run-tests.mjs
```

### Running the daemon
```bash
ALETHEIA_ALLOWED_ROOTS="/path/to/repos" aletheia-daemon
```

## Architecture

```
LM Studio / MCP Client
  └─ Node MCP Gateway (stdio JSON-RPC 2.0)
       └─ TCP Bridge (HMAC-SHA256 auth, single-line JSON-RPC)
            └─ Python Daemon (asyncio TCP server, port 8765)
                 ├─ ToolAdapters.call_mcp_tool()  ← central dispatch
                 ├─ SQLite (WAL, STRICT) ← queue, state, approvals, memory
                 └─ ChromaDB ← vector embeddings per project scope
```

All tool invocations flow: **Node contract validation → bridge → `call_mcp_tool(tool_name, args)` → adapter method → result dict**.

## Adding a New MCP Tool (5 files)

1. **Contract** — `backend/node-mcp/src/contracts.mjs`: Add JSON Schema Draft-7 entry with `strict: true`, `additionalProperties: false`
2. **Adapter branch** — `backend/python-daemon/orchestrator/adapters.py`: Add `if tool_name == "mcp_..."` branch in `call_mcp_tool()`
3. **Policy** — `backend/python-daemon/orchestrator/agent_workflow/policies.py`: Add to `ALLOWED_TOOLS` set and `REQUIRED_ARGS` dict
4. **Manifest** — `backend/tool_manifest.json`: Add entry with `risk_level`, `surfaces`, `requires_allowed_root`, etc.
5. **Runtime wiring** — `backend/python-daemon/orchestrator/runtime.py`: Construct adapter in `build_runtime()`, pass to `ToolAdapters`

The Node test suite asserts every contract has a matching manifest entry and vice versa — if you add a contract without a manifest entry (or the reverse), tests will fail.

## SQLite Migrations

Defined in `backend/python-daemon/orchestrator/db_bootstrap.py`. Pattern:

- String constants (`QUEUE_MIGRATION_0008 = """..."""`) or functions for ALTER TABLE
- Registered in `QUEUE_MIGRATIONS` tuple at bottom of file
- Applied once via `schema_migrations` table; daemon calls `bootstrap_databases()` on startup
- The migration test in `test_runtime_daemon.py` hardcodes the expected migration list — update it when adding migrations

Tables use `STRICT, WITHOUT ROWID` where appropriate. Foreign keys are enforced.

> **Local dev note (Round 2):** If you ran the daemon before Round 2 was merged, migration `0009_capability_registry` is recorded in your `schema_migrations` table but the key was renumbered to `0008_capability_registry`. The daemon will fail on startup with "unsupported future migrations". Fix: `DELETE FROM schema_migrations WHERE migration_id = '0009_capability_registry';` in your local `queue.db`, then restart.

## Path Safety

`FileToolAdapter._resolve(path)` validates all filesystem access against `ALETHEIA_ALLOWED_ROOTS` (semicolon-separated). Any path that resolves outside allowed roots raises `AdapterFailure`. This pattern is reused by SQLite adapter, workspace scout, patch services, and ingest.

## Key Subsystems

- **ToolAdapters** (`adapters.py`): Central dispatch for all MCP tools. Every tool is a branch in `call_mcp_tool()`.
- **WorkflowRunner** (`agent_workflow/runner.py`): Iterates a plan list of `{id, status, description, tool_name, args}` dicts. Compacts every tool result before storing in state.
- **Pipeline Compiler** (`pipeline/`): YAML templates → validated `PipelineDefinition` → compiled plan list → existing WorkflowRunner loop. Templates live in `pipeline/templates/*.yaml`.
- **Capability Registry** (`capabilities/`): SQLite-backed registry for backend capabilities (adapters, sandbox providers, indexers, pipeline templates, integration providers). Separate from SkillRegistry — skills stay in their own registry.
- **SkillRegistry** (`skills/`): Loads skill manifests from `agent_backend_skill_registry/skills/*/skill.json`. Selection scoring uses trigger phrases, capability match, and intent keywords.
- **Active Partition**: Tracks which LM Studio conversation is in focus. Scopes memory commits and searches to a project.
- **Bridge Security** (`bridge_server.py`): HMAC-SHA256 with nonce dedup (4096-entry LRU) and 300s timestamp tolerance.

## Conventions

- Python daemon uses `dataclass(frozen=True)` for models and config
- All timestamps are UTC ISO 8601
- Env vars are prefixed `ALETHEIA_`
- New `ToolAdapters.__init__()` params default to `None` for backward compatibility
- Node contracts use JSON Schema Draft-7 with `additionalProperties: false`
- Tool manifest `risk_level` values: `read_only`, `write_memory`, `write_files`, `admin`
