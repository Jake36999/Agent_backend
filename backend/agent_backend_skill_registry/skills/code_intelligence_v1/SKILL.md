# Code Intelligence v1

Use `mcp_code_intelligence` to analyze a target repository.

## Mode selection

- `code_map` — file inventory with language, size, line count. Use first to understand scope.
- `repo_context` — bounded text summary (default 8000 chars) for injecting into LLM context.
- `dependency_graph` — inter-file import edges. Use when analyzing coupling or call paths.
- `mermaid` — renders the dependency graph as a Mermaid `graph TD` diagram.

## Parameters

- `target_repo` (required) — absolute path to the repository root.
- `mode` (required) — one of the four modes above.
- `focus_paths` — list of subdirectory prefixes to restrict analysis (e.g. `["src/", "lib/"]`).
- `max_files` — cap file traversal (default 500, max 2000). Use with `focus_paths` for large repos.
- `max_chars` — cap `repo_context` output length (default 8000).

## Workflow

1. Call with `mode: "repo_context"` to get a bounded codebase summary.
2. Call with `mode: "code_map"` to enumerate files and language breakdown.
3. Use results to inform candidate analysis, patch planning, or architecture review.

## Constraints

- Read-only. No files are written or modified.
- Only analyzes files within `ALETHEIA_ALLOWED_ROOTS`.
- Python and JavaScript/TypeScript files get import analysis; other languages get metadata only.
