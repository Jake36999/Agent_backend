import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.patching.service import PatchGenerationService
from orchestrator.patching.apply import PatchApplyService
from orchestrator.patching.guardrails import validate_test_command


class PatchApplyAndTestTests(unittest.TestCase):
    def test_rejects_unapproved_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = root / "repo"; repo.mkdir()
            (repo / "a.txt").write_text("old\n")
            subprocess.run(["git", "init"], cwd=repo, capture_output=True)
            diff = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
            patch = PatchGenerationService(root / "queue.db").create_patch_artifact(objective="x", target_repo=repo, unified_diff=diff, selected_skill_id="patch_generate_v1", project_id=None, project_scope_hash=None, run_id=None, test_commands=[])
            result = PatchApplyService(root / "queue.db", root / "rollback", allowed_roots=[root]).apply_approved_patch_and_test(patch_id=patch["patch_id"], target_repo=repo, approval_record={"approved": False})
            self.assertEqual(result["status"], "PENDING_APPROVAL")

    def test_blocks_dangerous_test_command(self):
        ok, reason = validate_test_command("git push origin main")
        self.assertFalse(ok)
        self.assertIn("blocked", reason)


if __name__ == "__main__":
    unittest.main()
