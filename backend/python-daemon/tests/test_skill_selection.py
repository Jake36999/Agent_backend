import unittest

from orchestrator.skills.selection import select_skill


class SkillSelectionTests(unittest.TestCase):
    def test_selects_bug_triage_for_regression_even_when_tdd_plan_requested(self):
        manifests = [
            {
                "skill_id": "bug_triage_v1",
                "triggers": ["triage bug", "regression", "diagnose"],
                "capabilities": ["bug_triage", "tdd_planning"],
                "risk_tier": "T1",
            },
            {
                "skill_id": "refactor_plan_v1",
                "triggers": ["refactor plan", "technical debt plan", "rewrite plan"],
                "capabilities": ["refactor_planning"],
                "risk_tier": "T1",
            },
            {
                "skill_id": "tdd_patch_plan_v1",
                "triggers": ["tdd plan", "patch plan", "failing test"],
                "capabilities": ["tdd_planning"],
                "risk_tier": "T1",
            },
        ]

        selected = select_skill(
            "Triage this regression: semantic search returns stale chunks after reindex. Produce a TDD plan only.",
            manifests,
        )

        self.assertEqual(selected["selected_skill_id"], "bug_triage_v1")

    def test_selects_patch_generate_for_unified_diff_only(self):
        manifests = [
            {
                "skill_id": "patch_generate_v1",
                "triggers": ["generate patch", "unified diff", "patch only", "create diff", "do not apply"],
                "capabilities": ["patch_generation", "diff_only"],
                "risk_tier": "T2",
            },
            {
                "skill_id": "patch_apply_and_test_v1",
                "triggers": ["apply approved patch", "run declared tests", "approved diff"],
                "capabilities": ["approved_patch_application", "test_execution"],
                "risk_tier": "T3",
            },
        ]

        selected = select_skill(
            "Generate a unified diff only. Do not apply it.",
            manifests,
        )

        self.assertEqual(selected["selected_skill_id"], "patch_generate_v1")


if __name__ == "__main__":
    unittest.main()