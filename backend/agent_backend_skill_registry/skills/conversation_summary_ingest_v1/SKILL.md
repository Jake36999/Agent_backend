# Conversation summary ingest v1

Convert verified conversation events into bounded project memory. Apply the rule: no execution, no memory.

## Write only when based on
- successful tool result
- explicit user decision
- approved plan
- completed workflow artifact
- verified file/code state

## Reject
- guesses
- untested hypotheses
- broad chat logs with no durable project value
- transient PIDs, temp paths, timestamps unless needed for audit
- secrets or credential-like values

## Output
Return the memory candidate, verification basis, layer, removed volatile fields, and write_allowed. If write_allowed is false, do not call memory commit.
