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
