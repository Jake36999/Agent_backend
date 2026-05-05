# Snapshot memory

Snapshot memory records compact workflow results after `mcp_agent_workflow_run`.

## Table

`snapshot_records` lives in `queue.db`, not `control.db`.

It stores compact fields such as run id, selected skill JSON, artifact paths, summary, and index status.

## Compact metadata policy

Do not store by default:

- full report bodies
- raw manifest CSV contents
- raw conversation JSON
- full Python bundles
- full chat logs

Store only bounded summaries and artifact paths.

## Chroma indexing

When an active project scope exists, index compact text such as:

```text
Workflow snapshot: <summary>. Artifacts: archive_yaml=..., manifest_csv=..., final_markdown=...
```

Metadata includes:

- `source=snapshot_record`
- `snapshot_id`
- `run_id`
- `project_id`
- `project_scope_hash`
- artifact path keys when present

If indexing fails, the SQLite record remains the source of truth and `index_status=failed` with bounded `index_error`.
