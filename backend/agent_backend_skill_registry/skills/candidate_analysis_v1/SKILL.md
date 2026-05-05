# Candidate analysis v1

Rank candidate files/functions deterministically. Treat the ranking as a decision aid, not a claim of certainty.

## Ranking policy
Score candidates using only observable evidence:
- Direct log/test name match
- Symbol/path match from workspace scout
- Semantic memory relevance
- Ownership proximity to the failing behavior
- Test seam availability
- Risk/locality: prefer smaller, well-bounded candidates first

## Output rules
- Provide top candidates with reason, evidence, and confidence.
- Record missing context explicitly.
- Do not generate patches.
- Do not apply changes or run tests.
- Use stable ordering: score descending, then evidence count, then path lexical order.
