from __future__ import annotations

import unittest

from orchestrator.memory.conversation_summary import ConversationSummaryIngestor


class FakeMemory:
    def __init__(self):
        self.calls = []

    def commit_memory(self, **kwargs):
        self.calls.append(kwargs)
        return {"ok": True, "status": "COMMITTED", "memory_id": "m1"}


class ConversationSummaryIngestTests(unittest.TestCase):
    def test_explicit_user_decision_becomes_decision_memory(self):
        result = ConversationSummaryIngestor().build_memory_candidate(
            conversation_events=[{"type": "user_decision", "content": "Use metadata-first skills."}],
            target_repo="backend",
            write_intent="record decision",
        )

        self.assertTrue(result["write_allowed"])
        self.assertEqual(result["memory_candidate"]["category"], "decision")

    def test_untested_hypothesis_is_rejected(self):
        result = ConversationSummaryIngestor().build_memory_candidate(
            conversation_events=[{"type": "hypothesis", "content": "Maybe X."}]
        )

        self.assertFalse(result["write_allowed"])

    def test_secret_and_env_dump_content_is_blocked(self):
        result = ConversationSummaryIngestor().build_memory_candidate(
            conversation_events=[{"type": "user_decision", "content": "API_TOKEN=abcdef1234567890"}]
        )

        self.assertFalse(result["write_allowed"])

    def test_raw_chat_log_is_blocked(self):
        result = ConversationSummaryIngestor().build_memory_candidate(
            conversation_events=[{"type": "raw_chat_log", "content": "user: hello\nassistant: response"}]
        )

        self.assertFalse(result["write_allowed"])

    def test_commit_only_when_allowed(self):
        ingestor = ConversationSummaryIngestor()
        memory = FakeMemory()
        candidate = ingestor.build_memory_candidate(
            conversation_events=[{"type": "user_decision", "content": "Keep selector internal."}]
        )

        result = ingestor.commit_if_allowed(candidate_result=candidate, memory_service=memory)

        self.assertTrue(result["ok"])
        self.assertEqual(len(memory.calls), 1)


if __name__ == "__main__":
    unittest.main()
