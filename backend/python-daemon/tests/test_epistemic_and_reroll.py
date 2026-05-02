import tempfile
import unittest
from pathlib import Path

from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.epistemic import EpistemicPolicy, EpistemicSignals
from orchestrator.execution_loop import ExecutionLoop
from orchestrator.queue_repo import QueueRepository
from orchestrator.reroll import ValidationFailure


class EpistemicAndRerollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        bootstrap_databases(self.root)
        self.repo = QueueRepository(self.root / "queue.db", self.root / "control.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_depth_penalty_is_applied_before_routing(self):
        policy = EpistemicPolicy(depth_penalty=1.5)
        scored = policy.score(EpistemicSignals(logic_signal=10, sycophancy_signal=1), base_score=20.0, depth=3)

        self.assertEqual(scored.final_score, 15.5)
        self.assertEqual(scored.depth_penalty, 4.5)
        self.assertLess(scored.slr_score, 0.22)
        self.assertEqual(scored.decision, "route")

    def test_major_slr_conflict_enters_identity_freeze(self):
        policy = EpistemicPolicy()
        scored = policy.score(EpistemicSignals(logic_signal=2, sycophancy_signal=2), base_score=10.0, depth=0)

        self.assertGreaterEqual(scored.slr_score, 0.35)
        self.assertEqual(scored.decision, "identity_freeze")

    def test_validation_failure_adds_negative_constraint_then_dead_letters_after_limit(self):
        self.repo.create_task("task", "p", "Task", {"tool": "bad"}, depth=0)
        loop = ExecutionLoop(self.repo, max_rerolls=1)

        first = loop.handle_validation_failure(
            "task",
            ValidationFailure(tool_name="mcp_semantic_search", details=[{"path": "/query", "message": "required"}]),
        )
        second = loop.handle_validation_failure(
            "task",
            ValidationFailure(tool_name="mcp_semantic_search", details=[{"path": "/query", "message": "required"}]),
        )

        self.assertEqual(first["action"], "reroll")
        self.assertIn("Negative constraint", first["context"])
        self.assertEqual(second["action"], "dead_letter")
        dead_letters = self.repo.list_dead_letters()
        self.assertEqual(len(dead_letters), 1)
        self.assertIn("schema_validation_failed", dead_letters[0]["reason"])


if __name__ == "__main__":
    unittest.main()
