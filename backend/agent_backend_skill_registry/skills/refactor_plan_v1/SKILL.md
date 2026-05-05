# Refactor plan v1

Plan a refactor in small phases. Preserve current behavior and keep every phase independently testable.

## Rules
- No code changes.
- No diff generation.
- No apply/test execution.
- Every phase needs purpose, files/modules, test command, rollback note, and approval boundary if mutation will follow.
- Prefer seam extraction and adapter isolation over broad rewrites.
