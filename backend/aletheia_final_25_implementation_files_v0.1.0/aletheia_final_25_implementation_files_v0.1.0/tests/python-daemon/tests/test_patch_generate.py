import tempfile
import unittest
from pathlib import Path

from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.patching.service import PatchGenerationService
from orchestrator.patching.diff import DiffValidationError


class PatchGenerateTests(unittest.TestCase):
    def test_valid_diff_creates_patch_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            repo = root / "repo"
            repo.mkdir()
            diff = "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -0,0 +1 @@\n+print('x')\n"
            result = PatchGenerationService(root / "queue.db").create_patch_artifact(
                objective="change", target_repo=repo, unified_diff=diff, selected_skill_id="patch_generate_v1",
                project_id="p", project_scope_hash="s", run_id="r", test_commands=[])
            self.assertEqual(result["status"], "generated")
            self.assertFalse(result["audit_state"]["applied"])

    def test_outside_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            diff = "diff --git a/../x b/../x\n--- a/../x\n+++ b/../x\n@@ -0,0 +1 @@\n+x\n"
            with self.assertRaises(DiffValidationError):
                PatchGenerationService(root / "queue.db").create_patch_artifact(objective="x", target_repo=root, unified_diff=diff, selected_skill_id=None, project_id=None, project_scope_hash=None, run_id=None, test_commands=[])

    def test_env_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            diff = "diff --git a/.env b/.env\n--- a/.env\n+++ b/.env\n@@ -0,0 +1 @@\n+x\n"
            with self.assertRaises(DiffValidationError):
                PatchGenerationService(root / "queue.db").create_patch_artifact(objective="x", target_repo=root, unified_diff=diff, selected_skill_id=None, project_id=None, project_scope_hash=None, run_id=None, test_commands=[])


if __name__ == "__main__":
    unittest.main()
