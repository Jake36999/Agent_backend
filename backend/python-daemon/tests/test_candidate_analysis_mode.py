from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from orchestrator.candidate_analysis.service import CandidateAnalysisService
from orchestrator.candidate_analysis.manifest import load_manifest_candidates


class CandidateAnalysisModeTests(unittest.TestCase):
    def test_active_partition_bug_selects_active_partition_service(self):
        manifest = "path\norchestrator/active_partition/service.py\norchestrator/ingest/service.py\n"

        result = CandidateAnalysisService().analyze(
            {
                "objective": "active partition returns old project",
                "target_repo": "backend",
                "logs": "mcp_get_active_partition wrong project",
                "manifest_csv": manifest,
            }
        )

        self.assertEqual(result["ranked_candidates"][0]["path"], "orchestrator/active_partition/service.py")

    def test_generated_bundle_files_are_penalized(self):
        manifest = "path\nbackend_bundle_20260504.py\norchestrator/chroma_manager.py\n"

        result = CandidateAnalysisService().analyze(
            {
                "objective": "stale search chroma manager",
                "target_repo": "backend",
                "manifest_csv": manifest,
            }
        )

        self.assertEqual(result["ranked_candidates"][0]["path"], "orchestrator/chroma_manager.py")

    def test_stable_ranking_uses_score_evidence_then_path(self):
        manifest = "path\nb/service.py\na/service.py\n"

        result = CandidateAnalysisService().analyze(
            {
                "objective": "service",
                "target_repo": "backend",
                "manifest_csv": manifest,
            }
        )

        self.assertEqual([item["path"] for item in result["ranked_candidates"]], ["a/service.py", "b/service.py"])

    def test_missing_manifest_returns_warn_with_missing_context(self):
        result = CandidateAnalysisService().analyze({"objective": "nothing", "target_repo": "backend"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "WARN")
        self.assertTrue(result["missing_context"])

    def test_tool_assist_manifest_shape_parses_abs_path_and_rel_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            source = repo / "orchestrator" / "active_partition" / "service.py"
            source.parent.mkdir(parents=True)
            source.write_text("class ActivePartitionService: pass\n", encoding="utf-8")
            manifest = Path(tmp) / "manifest.csv"
            manifest.write_text(
                "root,rel_path,abs_path,ext,size,mtime_iso,sha1\n"
                f"{repo},orchestrator/active_partition/service.py,{source},.py,1,2026-01-01T00:00:00Z,abc\n",
                encoding="utf-8",
            )

            result = load_manifest_candidates(manifest, repo)

            self.assertTrue(result.ok)
            self.assertEqual(result.candidates[0]["rel_path"], "orchestrator/active_partition/service.py")
            self.assertEqual(Path(result.candidates[0]["path"]), source.resolve())

    def test_manifest_parser_excludes_tool_assist_outputs_and_bundles(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            source = repo / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf-8")
            bundle = repo / "final_handoff_bundle_abc.py"
            bundle.write_text("bundle\n", encoding="utf-8")
            output = Path(tmp) / "local_tool_assist_outputs" / "sessions" / "s" / "intermediate" / "manifest_doctor.md"
            output.parent.mkdir(parents=True)
            output.write_text("doctor\n", encoding="utf-8")
            manifest = Path(tmp) / "manifest.csv"
            manifest.write_text(
                "root,rel_path,abs_path,ext,size,mtime_iso,sha1\n"
                f"{repo},src/app.py,{source},.py,1,2026-01-01T00:00:00Z,abc\n"
                f"{repo},final_handoff_bundle_abc.py,{bundle},.py,1,2026-01-01T00:00:00Z,def\n"
                f"{repo},reports/manifest_doctor.md,{output},.md,1,2026-01-01T00:00:00Z,ghi\n",
                encoding="utf-8",
            )

            result = load_manifest_candidates(manifest, repo)

            self.assertTrue(result.ok)
            self.assertEqual([item["rel_path"] for item in result.candidates], ["src/app.py"])

    def test_service_warns_without_artifact_fallback_when_manifest_missing(self):
        result = CandidateAnalysisService().analyze(
            {
                "objective": "rank likely files",
                "target_repo": "backend",
                "workspace_summary": "manifest_csv,C:/work/manifest.csv\nfinal_markdown,C:/work/final.md",
            }
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["ranked_candidates"], [])


if __name__ == "__main__":
    unittest.main()
