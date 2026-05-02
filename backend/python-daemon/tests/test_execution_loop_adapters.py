import tempfile
import unittest
from pathlib import Path

from orchestrator.adapters import AdapterFailure, ToolAdapters
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.execution_loop import ExecutionLoop
from orchestrator.queue_repo import QueueRepository


class FailingAdapters(ToolAdapters):
    def call_mcp_tool(self, tool_name, args):
        raise AdapterFailure("adapter failed")


class ExecutionLoopAdapterTests(unittest.TestCase):
    def test_adapter_failure_feeds_reroll_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = QueueRepository(root / "queue.db", root / "control.db")
            repo.create_task("task", "p", "Task", {"tool": "mcp_semantic_search"}, depth=0)
            loop = ExecutionLoop(repo, max_rerolls=1, tool_adapters=FailingAdapters())

            result = loop.execute_tool_for_task("task", "mcp_semantic_search", {"project_id": "p", "query": "q"})

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "adapter_failure")
            self.assertEqual(result["reroll"]["action"], "reroll")
            self.assertIn("adapter failed", result["reroll"]["context"])


if __name__ == "__main__":
    unittest.main()
