# Patching trust flow

## T2 patch_generate

T2 generation creates a patch artifact only.

Allowed:

- validate unified diff text
- parse affected files
- store patch artifact in SQLite
- return patch id, affected files, test commands, and audit state

Not allowed:

- applying the patch
- running tests
- committing
- pushing
- deploying

## T3 patch_apply_and_test

T3 requires:

- existing patch artifact
- explicit approval record
- exact approved diff hash if approval integration supports it
- allowed-root validation
- rollback snapshots before mutation
- declared test commands only

## Rollback design

Rollback snapshots copy original affected file contents into `.aletheia_state/rollback/<patch_id>/...` and record hashes in `file_snapshots`.

Rollback restores from snapshot files, not destructive git commands.

## Blocked T4/T5 actions

- git commit
- git push
- git reset --hard
- git clean
- deployment
- Docker mutation
- dependency installation
- broad filesystem deletes
- credential mutation/exposure
