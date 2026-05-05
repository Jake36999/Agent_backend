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
