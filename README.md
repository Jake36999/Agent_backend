# Agent_backend

[![License](https://img.shields.io/github/license/Jake36999/Agent_backend)](LICENSE)
[![Python](https://img.shields.io/badge/Python-backend-blue)](#technology-stack)
[![Node.js](https://img.shields.io/badge/Node.js-MCP%20gateway-green)](#technology-stack)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-local%20runtime-purple)](#lm-studio-api-setup)

**Agent_backend** is the backend runtime for the Aletheia agentic orchestrator stack: a local-first, MCP-compatible control plane for tool-calling agents, semantic memory, project-scoped retrieval, and deterministic execution governance.

v1 integrates the Python backend daemon, Node MCP gateway, JSON-RPC bridge, queue/runtime primitives, LM Studio embedding support, and early epistemic validation layers.

---

## Table of Contents

* [Project Overview](#project-overview)
* [What This Stack Does](#what-this-stack-does)
* [Architecture](#architecture)
* [Technology Stack](#technology-stack)
* [Repository Layout](#repository-layout)
* [Runtime Model](#runtime-model)
* [MCP Tools](#mcp-tools)
* [Getting Started](#getting-started)

  * [Prerequisites](#prerequisites)
  * [LM Studio API Setup](#lm-studio-api-setup)
  * [Environment Variables](#environment-variables)
  * [Running the Backend Daemon](#running-the-backend-daemon)
  * [Running the Node MCP Gateway](#running-the-node-mcp-gateway)
  * [Testing the Bridge](#testing-the-bridge)
  * [Testing Embeddings](#testing-embeddings)
* [Development Workflow](#development-workflow)
* [Security Notes](#security-notes)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)

---

## Project Overview

Aletheia is designed to evolve a legacy passive RAG pipeline into a stateful agentic runtime.

Traditional RAG systems retrieve context outside the model and inject it into a prompt. This project instead exposes retrieval, ingestion, validation, and execution controls as structured tools. The model can call those tools through an MCP-style JSON-RPC boundary, while the backend daemon remains responsible for validation, state management, filesystem safety, queue control, and memory isolation.

The result is a local orchestration layer for agents running through tools such as LM Studio or Claude-compatible MCP clients.

---

## What This Stack Does

* Runs a local Python daemon for orchestration and state management.
* Exposes a Node.js MCP gateway for tool-compatible clients.
* Provides a direct TCP JSON-RPC bridge for local tool invocation.
* Supports LM Studio embedding models and OpenAI-compatible endpoints.
* Ingests files into project-scoped semantic memory.
* Uses ChromaDB-style vector retrieval for semantic search.
* Preserves structured state through SQLite-backed queue/runtime components.
* Enforces strict tool contracts before execution.
* Supports reroll and validation patterns for malformed tool calls.
* Provides early DAG/runtime governance for multi-step agent workflows.

---

## Architecture

```text
+---------------------------+
| Local LLM Client          |
| LM Studio / Claude / Tool |
+-------------+-------------+
              |
              | MCP / JSON-RPC tool call
              v
+-------------+-------------+
| Node MCP Gateway          |
| backend/node-mcp          |
+-------------+-------------+
              |
              | TCP bridge / local RPC
              v
+-------------+-------------+
| Python Backend Daemon     |
| backend/python-daemon     |
+------+------+-------------+
       |      |
       |      +----------------------+
       |                             |
       v                             v
+------+-------------+       +-------+-------------+
| Runtime State      |       | Semantic Memory     |
| SQLite / Queue     |       | Chroma / Embeddings |
+--------------------+       +---------------------+
       |
       v
+------+-------------+
| Project Filesystem |
| Allowed Roots Only |
+--------------------+
```

### Core Components

| Component                | Path                                     | Purpose                                                                                        |
| ------------------------ | ---------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Python daemon            | `backend/python-daemon/orchestrator/`    | Main runtime loop, queue control, DAG execution, approval gates, bridge server, shell helpers. |
| Node MCP gateway         | `backend/node-mcp/src/`                  | MCP-facing gateway, contracts, bridge client, server wrapper.                                  |
| Legacy RAG pipeline      | `Ingest_pipeline_V4r/`                   | Existing ingestion, PDF/code processing, metadata extraction, embeddings, retrieval logic.     |
| Workspace bundle tooling | `my_mcp_platform_root-1/standard_tools/` | Filesystem, database, analysis, scouting, and packaging utilities.                             |
| Project state            | `.aletheia/`                             | Local runtime state, Chroma store, logs, and generated artifacts.                              |

---

## Technology Stack

* **Python** — daemon, runtime governance, ingestion, queue/state management.
* **Node.js** — MCP gateway and contract validation boundary.
* **LM Studio** — local model and embedding server.
* **ChromaDB** — vector memory / semantic retrieval.
* **SQLite** — deterministic local queue and runtime state.
* **JSON-RPC 2.0** — tool-call transport contract.
* **PowerShell / pwsh** — local Windows-friendly development and smoke testing.

---

## Runtime Model

The orchestrator is built around a few core ideas:

### 1. Tool Calls Are Contracts

The model does not directly mutate the filesystem or memory stores. It emits structured JSON-RPC tool calls. The gateway validates those calls before the Python daemon executes them.

### 2. SQLite Is the Runtime Source of Truth

Agent messages, execution state, approvals, queue items, and tool-call lifecycle events are persisted locally. This allows the daemon to recover after crashes or restarts.

### 3. Vector Memory Is Project-Scoped

Embeddings and retrieved chunks are bound to a project identifier. This prevents cross-project memory bleed when switching between repositories or workspaces.

### 4. Retrieval Is Active, Not Passive

The model can decide when it needs context and call semantic search directly, rather than always receiving injected RAG context.

### 5. Governance Happens at Runtime

The backend includes early support for DAG execution, reroll handling, approval gates, shell hardening, and epistemic validation. The goal is to keep autonomous loops bounded, observable, and recoverable.

---

## MCP Tools

The stack is designed around the following MCP-style tool surface:

| Tool                   | Purpose                                                                                |
| ---------------------- | -------------------------------------------------------------------------------------- |
| `mcp_ingest_target`    | Ingest a file or directory into project-scoped memory.                                 |
| `mcp_semantic_search`  | Search the active memory partition for relevant context.                               |
| `mcp_verify_integrity` | Verify file hashes and detect whether content changed before reindexing.               |
| `mcp_extract_image`    | Fallback OCR/image extraction path for documents that cannot be parsed as normal text. |

Tool calls are expected to follow JSON-RPC 2.0:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools.call",
  "params": {
    "toolName": "mcp_semantic_search",
    "args": {
      "project_id": "aletheia",
      "query": "How does the bridge server invoke tools?",
      "limit": 5
    }
  }
}
```

---

## Getting Started

### Prerequisites

Install the following locally:

* Python 3.11+
* Node.js 20+
* LM Studio
* A local embedding model loaded in LM Studio
* Optional: PowerShell Core (`pwsh`) for cross-platform shell consistency

Recommended Python setup:

```powershell
cd "C:\Users\jakem\Documents\New project\backend\python-daemon"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Recommended Node setup:

```powershell
cd "C:\Users\jakem\Documents\New project\backend\node-mcp"
npm install
```

---

## LM Studio API Setup

> Important: Do not commit API tokens. Keep local startup commands in a personal file such as `backend\start-local-daemon.ps1`, and make sure it is ignored by Git.

### Step 1 — Obtain an LM Studio API Token

In LM Studio, open:

```text
Developer / Server Settings / API Authentication
```

Copy your API token. LM Studio documentation commonly refers to it as `LM_API_TOKEN`.

### Step 2 — Test Your Token Manually

```powershell
$env:LM_API_TOKEN="PASTE_YOUR_LM_STUDIO_TOKEN_HERE"

$headers = @{
  Authorization = "Bearer $env:LM_API_TOKEN"
}

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:1234/api/v1/models" `
  -Headers $headers |
  ConvertTo-Json -Depth 10
```

Expected result: a JSON response listing available models.

### Step 3 — Find the Embedding Model Key

```powershell
$models = Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:1234/api/v1/models" `
  -Headers $headers

$models.models |
  Where-Object { $_.type -eq "embedding" -or $_.type -eq "embeddings" } |
  Select-Object key, display_name, type, loaded_instances, max_context_length |
  Format-List
```

Look for a key like:

```text
text-embedding-nomic-embed-text-v1.5
```

Use the exact key returned by your server.

### Step 4 — Load the Embedding Model

```powershell
$embeddingModel = "PASTE_EXACT_EMBEDDING_MODEL_KEY_HERE"

$body = @{
  model = $embeddingModel
  context_length = 2048
  echo_load_config = $true
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:1234/api/v1/models/load" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 10
```

Expected result: the model reports as loaded.

### Step 5 — Test Embeddings Directly

Try the OpenAI-compatible endpoint first:

```powershell
$body = @{
  model = $embeddingModel
  input = "search_document: Aletheia smoke test"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:1234/v1/embeddings" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 4
```

If `/v1/embeddings` fails, try:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:1234/api/v0/embeddings" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 4
```

If `/api/v0/embeddings` works but `/v1/embeddings` does not, set:

```powershell
$env:ALETHEIA_LM_STUDIO_BASE_URL="http://127.0.0.1:1234/api/v0"
```

---

## Environment Variables

Set these values before running the daemon. Replace paths and tokens with your own local values.

```powershell
$env:LM_API_TOKEN="PASTE_YOUR_LM_STUDIO_TOKEN_HERE"

$env:ALETHEIA_PROJECT_ROOT="C:\Users\jakem\Documents\New project"
$env:ALETHEIA_PROJECT_ID="aletheia"
$env:ALETHEIA_ALLOWED_ROOTS="C:\Users\jakem\Documents\New project"

$env:ALETHEIA_STATE_DIR="C:\Users\jakem\Documents\New project\.aletheia"
$env:ALETHEIA_CHROMA_PATH="C:\Users\jakem\Documents\New project\.aletheia\chroma"

$env:ALETHEIA_LM_STUDIO_API_TOKEN=$env:LM_API_TOKEN
$env:ALETHEIA_LM_STUDIO_API_BASE_URL="http://127.0.0.1:1234/api/v1"
$env:ALETHEIA_LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"

$env:ALETHEIA_EMBEDDING_MODEL="PASTE_EXACT_EMBEDDING_MODEL_KEY_HERE"
$env:ALETHEIA_AUTO_LOAD_EMBEDDING_MODEL="true"

$env:ALETHEIA_BRIDGE_HOST="127.0.0.1"
$env:ALETHEIA_BRIDGE_PORT="8765"
$env:ALETHEIA_ENABLE_ADMIN_BRIDGE="false"

Remove-Item Env:\ALETHEIA_BRIDGE_SECRET -ErrorAction SilentlyContinue
```

### Environment Variable Reference

| Variable                          | Purpose                                                           |
| --------------------------------- | ----------------------------------------------------------------- |
| `ALETHEIA_PROJECT_ROOT`           | Root workspace the daemon is allowed to operate in.               |
| `ALETHEIA_PROJECT_ID`             | Active memory partition identifier.                               |
| `ALETHEIA_ALLOWED_ROOTS`          | Filesystem safety boundary for local tool calls.                  |
| `ALETHEIA_STATE_DIR`              | Runtime state directory.                                          |
| `ALETHEIA_CHROMA_PATH`            | Local vector store path.                                          |
| `ALETHEIA_LM_STUDIO_API_TOKEN`    | Token used for LM Studio API authentication.                      |
| `ALETHEIA_LM_STUDIO_API_BASE_URL` | LM Studio model-management API base URL.                          |
| `ALETHEIA_LM_STUDIO_BASE_URL`     | LM Studio inference/embedding API base URL.                       |
| `ALETHEIA_EMBEDDING_MODEL`        | Exact embedding model key from LM Studio.                         |
| `ALETHEIA_BRIDGE_HOST`            | TCP bridge bind host.                                             |
| `ALETHEIA_BRIDGE_PORT`            | TCP bridge bind port.                                             |
| `ALETHEIA_ENABLE_ADMIN_BRIDGE`    | Enables or disables admin bridge behavior. Keep false by default. |

---

## Running the Backend Daemon

```powershell
cd "C:\Users\jakem\Documents\New project\backend\python-daemon"
python -m orchestrator.main
```

Expected result: the daemon starts and listens on the configured bridge host and port.

---

## Running the Node MCP Gateway

```powershell
cd "C:\Users\jakem\Documents\New project\backend\node-mcp"
npm start
```

If the package does not define `npm start`, run the server entrypoint directly:

```powershell
node .\src\server.mjs
```

---

## Testing the Bridge

From a second PowerShell window:

```powershell
$client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 8765)
$stream = $client.GetStream()
$stream.ReadTimeout = 180000
$stream.WriteTimeout = 180000
$writer = [System.IO.StreamWriter]::new($stream)
$reader = [System.IO.StreamReader]::new($stream)
$writer.NewLine = "`n"
$writer.AutoFlush = $true

$req = @{
  jsonrpc = "2.0"
  id = 1
  method = "tools.list"
  params = @{}
} | ConvertTo-Json -Depth 10 -Compress

$writer.WriteLine($req)
$reader.ReadLine()
$client.Close()
```

Expected result: a JSON-RPC response listing registered tools.

---

## Testing Embeddings

Test direct bridge ingest from a second PowerShell window:

```powershell
$client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 8765)
$stream = $client.GetStream()
$stream.ReadTimeout = 180000
$stream.WriteTimeout = 180000
$writer = [System.IO.StreamWriter]::new($stream)
$reader = [System.IO.StreamReader]::new($stream)
$writer.NewLine = "`n"
$writer.AutoFlush = $true

$req = @{
  jsonrpc = "2.0"
  id = 2
  method = "tools.call"
  params = @{
    toolName = "mcp_ingest_target"
    args = @{
      project_id = "aletheia"
      absolute_path = "C:\Users\jakem\Documents\New project\backend\README.md"
      force_reindex = $true
    }
  }
} | ConvertTo-Json -Depth 10 -Compress

$writer.WriteLine($req)
$reader.ReadLine()
$client.Close()
```

Expected result:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "ok": true
  }
}
```

---

## Development Workflow

### Python Tests

```powershell
cd "C:\Users\jakem\Documents\New project\backend\python-daemon"
pytest
```

### Node Tests

```powershell
cd "C:\Users\jakem\Documents\New project\backend\node-mcp"
npm test
```

If no package script exists, run the bundled test runner:

```powershell
node .\test\run-tests.mjs
```

### Recommended Commit Hygiene

Before opening a pull request:

```powershell
pytest
npm test
```

Also verify that no local secrets or startup scripts are staged:

```powershell
git status
git diff --cached
```

---

## Security Notes

* Never commit LM Studio tokens, bridge secrets, `.env` files, or local startup scripts.
* Keep `ALETHEIA_ALLOWED_ROOTS` narrow. Do not point it at your entire user directory or drive root.
* Keep `ALETHEIA_ENABLE_ADMIN_BRIDGE=false` unless you are actively developing admin-only bridge tools.
* Treat every model-generated tool call as untrusted until it passes schema validation.
* Prefer read-only operations by default. Require explicit approval for destructive filesystem actions.
* Keep local Chroma and state directories out of Git.

Recommended `.gitignore` additions:

```gitignore
# Local runtime state
.aletheia/
**/.aletheia/

# Local secrets and startup scripts
.env
*.env
backend/start-local-daemon.ps1
backend/start-local-daemon.sh

# Python / Node artifacts
__pycache__/
*.pyc
node_modules/
dist/
build/

# Local databases and vector stores
*.sqlite
*.sqlite3
chroma/
```

---

## Roadmap

* [ ] Harden MCP tool schemas with strict `additionalProperties: false` contracts.
* [ ] Add first-class project switching and memory partition controls.
* [ ] Add automatic file integrity checks before reindexing.
* [ ] Add watchdog-based ingestion for selected local directories.
* [ ] Add response payload caps and pagination for large retrieval results.
* [ ] Expand HITL approval flow for write, delete, and shell actions.
* [ ] Add runtime telemetry TTL cleanup for failed workspaces.
* [ ] Add richer bridge health checks and daemon recovery tests.
* [ ] Add LM Studio `mcp.json` registration example.
* [ ] Publish architecture docs under `/docs`.

---

## Contributing

Contributions, issues, and feature requests are welcome.

1. Fork the repository.

2. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature
   ```

3. Commit your changes:

   ```bash
   git commit -am "Add your feature"
   ```

4. Push to your branch:

   ```bash
   git push origin feature/your-feature
   ```

5. Open a pull request.

Please review [CONTRIBUTING.md](CONTRIBUTING.md) if available.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Notes

This repository is under active development. The runtime is intended for local-first experimentation with agentic orchestration, MCP-compatible tooling, and project-scoped memory systems.

The safest default mode is conservative: validate every tool call, constrain filesystem access, keep secrets out of Git, and treat runtime state as disposable unless explicitly persisted.
