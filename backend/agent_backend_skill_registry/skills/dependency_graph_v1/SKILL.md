# Dependency Graph v1

Use `mcp_code_intelligence` with `mode: "dependency_graph"` or `mode: "mermaid"` to extract import relationships.

## When to use

- Identifying circular dependencies
- Understanding module coupling before a refactor
- Generating architecture diagrams for review
- Finding the blast radius of a change

## Parameters

- `target_repo` (required) — absolute path to the repository root.
- `mode` (required) — `dependency_graph` for raw adjacency list, `mermaid` for diagram.
- `focus_paths` — restrict to specific subdirectories to reduce graph size.
- `max_edges` — cap edge count (default 500). Set lower for large repos to avoid truncation.

## Output interpretation

### dependency_graph
- `nodes` — internal files that appear in at least one edge
- `edges` — `{source, target, kind, is_external}` — `is_external: true` edges are package imports
- `truncated` — if true, increase `focus_paths` specificity or reduce `max_files`

### mermaid
- Ready to paste into any Mermaid renderer
- External package nodes are excluded from the diagram automatically
- Node IDs are sanitized (slashes/dots become underscores); labels preserve the original path

## Language support

- Python: `ast` module — `import`, `from ... import`, relative imports (`from . import foo`)
- JavaScript/TypeScript: regex on `import`/`require` — resolves relative specifiers to file paths
- Other languages: not parsed for edges, but included in `code_map` metadata
