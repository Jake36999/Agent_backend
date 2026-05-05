from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.patching.git_guardrails import GitGuardrailsService
from orchestrator.patching.service import PatchGenerationService
from orchestrator.patching.validation import PatchValidationService


class PatchGenerationTests(unittest.TestCase):
    def test_patch_artifacts_migration_is_queue_only_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            bootstrap_databases(root)
            with closing(sqlite3.connect(root / "queue.db")) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                versions = [row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()]
            with closing(sqlite3.connect(root / "control.db")) as conn:
                control_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            self.assertIn("0006_patch_artifacts", versions)
            self.assertIn("patch_artifacts", tables)
            self.assertNotIn("patch_artifacts", control_tables)

    def test_patch_generation_writes_patch_outside_target_repo_and_stores_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            target = repo / "app.py"
            target.write_text("print('old')\n", encoding="utf-8")
            state = root / "state"
            bootstrap_databases(state)
            service = PatchGenerationService(state / "queue.db", state / "artifacts", allowed_roots=(repo,))

            result = service.create_patch_from_before_after(
                run_id="r1",
                project_id="p",
                project_scope_hash="scope",
                selected_skill_id="patch_generate_v1",
                target_repo=repo,
                changes=[{"rel_path": "app.py", "before": "print('old')\n", "after": "print('new')\n"}],
            )

            self.assertTrue(result["ok"])
            patch_path = Path(result["patch_artifact"]["patch_path"])
            self.assertFalse(repo.resolve() in patch_path.resolve().parents)
            self.assertTrue(patch_path.exists())
            with closing(sqlite3.connect(state / "queue.db")) as conn:
                row = conn.execute("SELECT patch_path, diff_sha256, affected_paths_json FROM patch_artifacts").fetchone()
            self.assertEqual(row[0], str(patch_path))
            self.assertEqual(result["patch_artifact"]["diff_sha256"], row[1])
            self.assertIn("app.py", row[2])
            patch_text = patch_path.read_text(encoding="utf-8")
            self.assertIn("--- a/app.py\n", patch_text)
            self.assertIn("+++ b/app.py\n", patch_text)
            self.assertIn("@@ -1 +1 @@\n", patch_text)

    def test_validation_rejects_unsafe_patch_headers_and_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            validator = PatchValidationService(allowed_roots=(repo,))

            cases = [
                "--- a/../secret.txt\n+++ b/../secret.txt\n@@ -1 +1 @@\n-a\n+b\n",
                "--- a/C:/tmp/x.txt\n+++ b/C:/tmp/x.txt\n@@ -1 +1 @@\n-a\n+b\n",
                "Binary files a/app.py and b/app.py differ\n",
                "--- a/final_handoff_bundle_1.py\n+++ b/final_handoff_bundle_1.py\n@@ -1 +1 @@\n-a\n+b\n",
                "--- a/local_tool_assist_outputs/x.py\n+++ b/local_tool_assist_outputs/x.py\n@@ -1 +1 @@\n-a\n+b\n",
                "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-a\n+b\n",
            ]
            for diff in cases:
                with self.subTest(diff=diff.splitlines()[0]):
                    result = validator.validate_unified_diff(diff, target_repo=repo, run_git_check=False)
                    self.assertFalse(result.ok)

    def test_git_check_uses_check_only_argv_shell_false_and_timeout(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))

            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            return Result()

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / "app.py").write_text("print('old')\n", encoding="utf-8")
            validator = PatchValidationService(allowed_roots=(repo,), subprocess_run=fake_run)
            diff = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-print('old')\n+print('new')\n"

            result = validator.validate_unified_diff(diff, target_repo=repo, run_git_check=True)

            self.assertTrue(result.ok)
            self.assertEqual(calls[0][0], ["git", "apply", "--check", "--", "-"])
            self.assertFalse(calls[0][1]["shell"])
            self.assertIn("timeout", calls[0][1])
            self.assertNotIn("--index", calls[0][0])
            self.assertNotIn("--cached", calls[0][0])
            self.assertNotIn("--3way", calls[0][0])

    def test_git_guardrails_block_mutation_and_allow_read_only(self):
        guardrails = GitGuardrailsService()

        for command in (["git", "push"], ["git", "reset", "--hard"], ["git", "clean", "-fd"], ["docker", "compose", "up"], ["npm", "install"], ["env"]):
            self.assertFalse(guardrails.check_command(command).allowed)
        for command in (["git", "status"], ["git", "diff"], ["git", "log"], ["git", "show"]):
            self.assertTrue(guardrails.check_command(command).allowed)


if __name__ == "__main__":
    unittest.main()
