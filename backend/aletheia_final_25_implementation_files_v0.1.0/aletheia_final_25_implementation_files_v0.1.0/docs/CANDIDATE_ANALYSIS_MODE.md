# Candidate analysis mode

Candidate analysis is deterministic and service-internal in this bundle.

## Inputs

- objective
- target_repo
- logs
- failing_test_output
- manifest_csv
- workspace_summary
- rag_context
- max_candidates

## Scoring rules

- tokenize objective/logs/failing output
- ignore stopwords and weak planning words
- score direct path/token matches
- score filename/stem matches
- score symbol/function/class matches when manifest data provides them
- score test seam proximity
- score package/module proximity
- score provided semantic context hits
- penalize generated files, bundles, venvs, node_modules, dist/build, `.git`, caches

Stable ordering:

1. score descending
2. evidence count descending
3. path lexical ascending

## Constraints

- No LLM calls.
- No Chroma calls unless context is already provided.
- No arbitrary file reads.
- No mutation.
