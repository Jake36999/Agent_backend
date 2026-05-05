# Acceptance checklist

## Required commands

```powershell
cd "C:\Users\jakem\Documents\New project\backend\python-daemon"
python -m unittest discover -s tests -v
```

Run this only if Node contracts are deliberately modified:

```powershell
cd "C:\Users\jakem\Documents\New project\backend\node-mcp"
node test\run-tests.mjs
```

## Expected no-live requirements

- Unit tests must not require LM Studio.
- Unit tests must not require a Chroma server.
- Unit tests must not require a real user conversation folder.
- Unit tests should use temp dirs, fakes, and mocks.

## ActivePartitionWatcher acceptance

- Watcher disabled by default.
- Newest nested `*.conversation.json` maps to an active project.
- Root-level conversation files return `NEEDS_PROJECT_FOLDER` and do not overwrite the active project.
- Outside-root conversation paths return `POLICY_BLOCK`.
- Settle logic avoids acting on unstable files.
- No conversation JSON parsing.

## Snapshot memory acceptance

- `snapshot_records` exists in `queue.db`.
- Workflow snapshots store compact metadata only.
- Snapshot indexing is skipped cleanly without active project scope.
- Chroma failures mark records failed with bounded error.
- Responses remain compact.

## Conversation summary ingestion acceptance

- Explicit user decisions can become bounded decision memory.
- Completed workflow artifacts can become artifact/summary memory.
- Untested hypotheses are rejected.
- Secret-like content is blocked or redacted and not committed.
- `commit_if_allowed` commits only when allowed.

## Candidate analysis acceptance

- Deterministic, no LLM calls.
- No file mutation.
- Generated bundles, venvs, node_modules, build/dist, caches, and `.git` are penalized.
- Stable ordering: score desc, evidence count desc, path lexical asc.

## Patching acceptance

- T2 patch generation stores patch artifacts only; it does not apply changes or run tests.
- T3 patch apply/test requires approval and rollback snapshots.
- Dangerous test commands are blocked.
- No git commit, git push, deploy, Docker mutation, or dependency installation.
- Rollback restores original file contents without destructive git commands.
