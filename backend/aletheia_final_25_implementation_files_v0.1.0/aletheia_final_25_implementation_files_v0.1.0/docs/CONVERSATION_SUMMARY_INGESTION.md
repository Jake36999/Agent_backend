# Conversation summary ingestion

`ConversationSummaryIngestor` implements `conversation_summary_ingest_v1` policy deterministically.

## Write allowed only when based on

- successful tool result
- explicit user decision
- approved plan
- completed workflow artifact
- verified file/code state

## Reject

- guesses
- untested hypotheses
- raw chat logs with no durable project value
- transient PIDs/temp paths/timestamps unless needed for audit
- secrets or credential-like values

## Secret handling

The ingestor blocks obvious private keys, token-like key/value pairs, and env dumps. Blocked content is not committed.

## Memory categories

- `decision`
- `summary`
- `architecture`
- `bug_fix`
- `preference`
- `artifact`

No public MCP tool is added. The service is intended for internal use after verified workflows/snapshots.
