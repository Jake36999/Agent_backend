import unittest

from orchestrator.dag_runtime import topological_descendants


class DagRuntimeTests(unittest.TestCase):
    def test_orders_descendants_before_their_children(self):
        edges = [("root", "child"), ("child", "grandchild"), ("root", "sibling")]

        ordered = topological_descendants("root", edges)

        self.assertEqual(set(ordered), {"child", "grandchild", "sibling"})
        self.assertLess(ordered.index("child"), ordered.index("grandchild"))


if __name__ == "__main__":
    unittest.main()
