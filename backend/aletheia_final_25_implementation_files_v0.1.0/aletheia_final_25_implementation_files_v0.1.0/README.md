# Aletheia final 25 implementation files v0.1.0

This package contains implementation-ready backend files and patch fragments for the final system-expansion layer of `agent_backend`.

It does not modify the repository directly. Copy the generated files into the repo, review/apply the patch fragments, then run the acceptance tests.

## Contents

- `generated_files/` - complete new backend Python modules to copy into the repo.
- `patch_fragments/` - reviewable patch fragments for existing files.
- `tests/` - unit tests to copy into `backend/python-daemon/tests/`.
- `docs/` - implementation notes for the new services.
- `FILE_MANIFEST.json` - package manifest with repo target paths.
- `IMPLEMENTATION_ORDER.md` - recommended integration order.
- `ACCEPTANCE_CHECKLIST.md` - validation checklist and commands.

## Copy strategy

From the unzipped package root, copy files from `generated_files/backend/...` into the same repo-relative paths under your `backend/` repo. For example:

```text
generated_files/backend/python-daemon/orchestrator/active_partition/watcher.py
-> backend/python-daemon/orchestrator/active_partition/watcher.py
```

Copy files from `tests/python-daemon/tests/` into:

```text
backend/python-daemon/tests/
```

Then review and apply patch fragments from `patch_fragments/` manually or with your preferred patch workflow.

## Patch fragments to review

- `db_bootstrap.patch` - adds queue.db tables for snapshots, patch artifacts, and rollback snapshots.
- `config.patch` - adds optional watcher-related config fields.
- `runtime.patch` - constructs optional services and watcher.
- `main.patch` - runs optional watcher task with clean shutdown.
- `agent_workflow_runner.patch` - routes selected skill metadata, candidate analysis, snapshot memory, summary ingestion, and patch services.
- `agent_workflow_state.patch` - adds optional selected-skill and artifact fields.
- `agent_workflow_mcp_tool.patch` - preserves compact MCP response while surfacing new artifact IDs.
- `adapters.patch` - optional adapter wiring notes.

## What this package deliberately excludes

- No frontend, UI, dashboard, or web server.
- No new public MCP tools for individual skills.
- No public SQLite query tool.
- No arbitrary shell executor.
- No git commit, git push, deploy, Docker mutation, or dependency installation.
- No runtime databases, Chroma state, logs, venvs, caches, or local secrets.
- No LM Studio conversation JSON parsing in v1; only folder/path metadata is used.
- No LMStudioManager duplicate-load changes; that item is assumed already fixed.

## Acceptance commands

After copying files and applying reviewed patches:

```powershell
cd "C:\Users\jakem\Documents\New project\backend\python-daemon"
python -m unittest discover -s tests -v
```

Run Node tests only if you deliberately changed Node contracts:

```powershell
cd "C:\Users\jakem\Documents\New project\backend\node-mcp"
node test\run-tests.mjs
```

The unit tests in this package are designed to avoid live LM Studio, live Chroma server, real user conversation folders, or real user state.
