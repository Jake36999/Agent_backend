import unittest

from orchestrator.candidate_analysis.service import CandidateAnalysisService


class CandidateAnalysisModeTests(unittest.TestCase):
    def test_active_partition_bug_selects_active_partition_service(self):
        manifest = "path\norchestrator/active_partition/service.py\norchestrator/ingest/service.py\n"
        result = CandidateAnalysisService().analyze({
            "objective": "active partition returns old project",
            "target_repo": "backend",
            "logs": "mcp_get_active_partition wrong project",
            "manifest_csv": manifest,
        })
        self.assertEqual(result["ranked_candidates"][0]["path"], "orchestrator/active_partition/service.py")

    def test_generated_bundle_files_are_penalized(self):
        manifest = "path\nbackend_bundle_20260504.py\norchestrator/chroma_manager.py\n"
        result = CandidateAnalysisService().analyze({
            "objective": "stale search chroma manager",
            "target_repo": "backend",
            "manifest_csv": manifest,
        })
        self.assertEqual(result["ranked_candidates"][0]["path"], "orchestrator/chroma_manager.py")

    def test_missing_manifest_returns_ok_with_missing_context(self):
        result = CandidateAnalysisService().analyze({"objective": "nothing", "target_repo": "backend"})
        self.assertTrue(result["ok"])
        self.assertTrue(result["missing_context"])


if __name__ == "__main__":
    unittest.main()
