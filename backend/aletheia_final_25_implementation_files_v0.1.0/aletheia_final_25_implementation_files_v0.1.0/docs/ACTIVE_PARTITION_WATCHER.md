# ActivePartitionWatcher

`ActivePartitionWatcher` is an optional dependency-free polling watcher for LM Studio conversation folders.

## Environment variables

- `ALETHEIA_LMSTUDIO_CONVERSATIONS_DIR` - root folder to scan recursively for `*.conversation.json`.
- `ALETHEIA_ENABLE_LMSTUDIO_WATCHER=false` - disabled by default.
- `ALETHEIA_ACTIVE_PARTITION_SETTLE_MS=750` - file size/mtime settle delay.

## Behavior

- Disabled unless explicitly enabled in config/runtime.
- Scans recursively for newest modified `*.conversation.json`.
- Does not parse conversation JSON.
- Uses file path/folder only.
- Delegates mapping to `ActivePartitionService.set_active_from_conversation_path`.
- Root-level conversations should return `NEEDS_PROJECT_FOLDER` and not set active project.
- Outside-root paths return `POLICY_BLOCK`.

## Statuses

- `OK`
- `NO_CONVERSATIONS_FOUND`
- `UNSTABLE`
- `UNCHANGED`
- `NEEDS_PROJECT_FOLDER`
- `POLICY_BLOCK`
- `CONVERSATIONS_ROOT_NOT_FOUND`
