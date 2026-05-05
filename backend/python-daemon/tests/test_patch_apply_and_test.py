from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from orchestrator.adapters import ToolAdapters
from orchestrator.agent_workflow.mcp_tool import run_agent_workflow
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.patching.apply import PatchApplyService
from orchestrator.patching.repo import PatchArtifactRepository
from orchestrator.patching.rollback import RollbackRestoreService
from orchestrator.patching.service import PatchGenerationService
from orchestrator.patching.test_runner import DeclaredTestRunner


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)


def _create_patch(state: Path, repo: Path, rel_path: str = "app.py", before: str = "old\n", after: str = "new\n") -> dict[str, object]:
    service = PatchGenerationService(state / "queue.db", state / "patch_artifacts", allowed_roots=(repo,))
    return service.create_patch_from_before_after(
        run_id="run-1",
        project_id="project-1",
        project_scope_hash="scope-1",
        selected_skill_id="patch_generate_v1",
        target_repo=repo,
        changes=[{"rel_path": rel_path, "before": before, "after": after}],
    )["patch_artifact"]


def _approve(state: Path, patch: dict[str, object], *, approved: bool = True, diff_sha256: str | None = None, tests: list[list[str]] | None = None) -> str:
    repo = PatchArtifactRepository(state / "queue.db")
    approval_id = f"approval-{uuid.uuid4().hex}"
    repo.insert_approval_record(
        {
            "approval_id": approval_id,
            "patch_id": patch["patch_id"],
            "run_id": "run-1",
            "project_id": "project-1",
            "project_scope_hash": "scope-1",
            "target_repo": patch["target_repo"],
            "approved": approved,
            "approved_by": "operator",
            "approved_at": "2026-05-05T00:00:00+00:00",
            "approval_scope": "single_patch",
            "approved_diff_sha256": diff_sha256 or patch["diff_sha256"],
            "declared_tests_json": tests or [],
            "created_at": "2026-05-05T00:00:00+00:00",
            "notes": "test approval",
        }
    )
    return approval_id


class PatchApplyAndTestTests(unittest.TestCase):
    def test_0007_migration_is_queue_only_and_creates_only_round_three_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_databases(root)
            bootstrap_databases(root)

            with closing(sqlite3.connect(root / "queue.db")) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                versions = [row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()]
            with closing(sqlite3.connect(root / "control.db")) as conn:
                control_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            self.assertIn("0007_patch_apply_approvals", versions)
            self.assertTrue({"approval_records", "file_snapshots", "patch_apply_runs"}.issubset(tables))
            self.assertFalse({"approval_records", "file_snapshots", "patch_apply_runs"}.intersection(control_tables))

    def test_internal_apply_requires_approval_and_matching_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            _init_git(repo)
            (repo / "app.py").write_text("old\n", encoding="utf-8")
            state = root / "state"
            bootstrap_databases(state)
            patch_artifact = _create_patch(state, repo)
            service = PatchApplyService(state / "queue.db", state / "rollback", allowed_roots=(repo,))

            missing = service.apply_approved_patch(patch_id=str(patch_artifact["patch_id"]), approval_id="missing", target_repo=repo)
            rejected_id = _approve(state, patch_artifact, approved=False)
            rejected = service.apply_approved_patch(patch_id=str(patch_artifact["patch_id"]), approval_id=rejected_id, target_repo=repo)
            mismatch_id = _approve(state, patch_artifact, diff_sha256="0" * 64)
            mismatch = service.apply_approved_patch(patch_id=str(patch_artifact["patch_id"]), approval_id=mismatch_id, target_repo=repo)

            self.assertEqual(missing["status"], "APPROVAL_NOT_FOUND")
            self.assertEqual(rejected["status"], "PENDING_APPROVAL")
            self.assertEqual(mismatch["status"], "APPROVAL_HASH_MISMATCH")
            self.assertEqual((repo / "app.py").read_text(encoding="utf-8"), "old\n")

    def test_patch_file_hash_mismatch_blocks_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            _init_git(repo)
            (repo / "app.py").write_text("old\n", encoding="utf-8")
            state = root / "state"
            bootstrap_databases(state)
            patch_artifact = _create_patch(state, repo)
            Path(str(patch_artifact["patch_path"])).write_text("tampered\n", encoding="utf-8")
            approval_id = _approve(state, patch_artifact)

            result = PatchApplyService(state / "queue.db", state / "rollback", allowed_roots=(repo,)).apply_approved_patch(
                patch_id=str(patch_artifact["patch_id"]),
                approval_id=approval_id,
                target_repo=repo,
            )

            self.assertEqual(result["status"], "PATCH_HASH_MISMATCH")
            self.assertEqual((repo / "app.py").read_text(encoding="utf-8"), "old\n")

    def test_successful_apply_snapshots_before_mutation_and_restores_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            _init_git(repo)
            target = repo / "app.py"
            original = b"old\n"
            target.write_bytes(original)
            state = root / "state"
            bootstrap_databases(state)
            patch_artifact = _create_patch(state, repo)
            approval_id = _approve(state, patch_artifact)

            result = PatchApplyService(state / "queue.db", state / "rollback", allowed_roots=(repo,)).apply_approved_patch(
                patch_id=str(patch_artifact["patch_id"]),
                approval_id=approval_id,
                target_repo=repo,
            )

            self.assertTrue(result["ok"])
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
            with closing(sqlite3.connect(state / "queue.db")) as conn:
                rows = conn.execute("SELECT target_path, pre_apply_sha256, backup_path, created_target FROM file_snapshots").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], str(target.resolve()))
            self.assertEqual(rows[0][1], _sha256(original))
            self.assertTrue(Path(rows[0][2]).exists())
            self.assertEqual(rows[0][3], 0)

            restore = RollbackRestoreService(state / "queue.db", state / "rollback").restore_apply_run(str(result["apply_run_id"]))

            self.assertTrue(restore["ok"])
            self.assertEqual(target.read_bytes(), original)

    def test_new_file_rollback_deletes_only_recorded_created_file_under_target_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            _init_git(repo)
            survivor = repo / "survivor.txt"
            survivor.write_text("keep\n", encoding="utf-8")
            state = root / "state"
            bootstrap_databases(state)
            patch_artifact = _create_patch(state, repo, rel_path="created.txt", before="", after="created\n")
            approval_id = _approve(state, patch_artifact)

            result = PatchApplyService(state / "queue.db", state / "rollback", allowed_roots=(repo,)).apply_approved_patch(
                patch_id=str(patch_artifact["patch_id"]),
                approval_id=approval_id,
                target_repo=repo,
            )
            restore = RollbackRestoreService(state / "queue.db", state / "rollback").restore_apply_run(str(result["apply_run_id"]))

            self.assertTrue(result["ok"])
            self.assertTrue(restore["ok"])
            self.assertFalse((repo / "created.txt").exists())
            self.assertTrue(survivor.exists())

    def test_unsafe_targets_and_symlink_mutation_are_denied(self):
        unsafe_diffs = [
            "--- a/../secret.txt\n+++ b/../secret.txt\n@@ -1 +1 @@\n-old\n+new\n",
            "--- a/C:/tmp/x.txt\n+++ b/C:/tmp/x.txt\n@@ -1 +1 @@\n-old\n+new\n",
            "Binary files a/app.py and b/app.py differ\n",
            "--- a/final_handoff_bundle_1.py\n+++ b/final_handoff_bundle_1.py\n@@ -1 +1 @@\n-old\n+new\n",
            "--- a/local_tool_assist_outputs/x.py\n+++ b/local_tool_assist_outputs/x.py\n@@ -1 +1 @@\n-old\n+new\n",
            "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-old\n+new\n",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            _init_git(repo)
            state = root / "state"
            bootstrap_databases(state)
            service = PatchApplyService(state / "queue.db", state / "rollback", allowed_roots=(repo,))
            for diff in unsafe_diffs:
                with self.subTest(header=diff.splitlines()[0]):
                    result = service.validate_patch_text(diff, target_repo=repo)
                    self.assertFalse(result.ok)

            (repo / "real.txt").write_text("old\n", encoding="utf-8")
            (repo / "link.txt").symlink_to(repo / "real.txt")
            result = service.validate_patch_text(
                "--- a/link.txt\n+++ b/link.txt\n@@ -1 +1 @@\n-old\n+new\n",
                target_repo=repo,
            )
            self.assertFalse(result.ok)
            self.assertIn("symlink", result.error or "")

    def test_declared_tests_require_argv_arrays_shell_false_timeout_and_bounded_tails(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))

            class Result:
                returncode = 1
                stdout = "O" * 100
                stderr = "E" * 100

            return Result()

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            runner = DeclaredTestRunner(subprocess_run=fake_run, timeout_seconds=7, tail_chars=10)

            with self.assertRaises(ValueError):
                runner.run(target_repo=repo, commands=["python -m unittest"])
            with self.assertRaises(ValueError):
                runner.run(target_repo=repo, commands=[["python", "-m", "unittest", ";", "rm", "-rf", "."]])
            with self.assertRaises(ValueError):
                runner.run(target_repo=repo, commands=[["git", "push"]])

            result = runner.run(target_repo=repo, commands=[["python", "-m", "unittest", "tests.test_x", "-v"]])

            self.assertEqual(calls[0][0], ["python", "-m", "unittest", "tests.test_x", "-v"])
            self.assertFalse(calls[0][1]["shell"])
            self.assertEqual(calls[0][1]["timeout"], 7)
            self.assertEqual(result[0]["stdout_tail"], "O" * 10)
            self.assertEqual(result[0]["stderr_tail"], "E" * 10)

    def test_public_workflow_cannot_trigger_patch_apply_or_expand_public_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            (repo / "app.py").write_text("old\n", encoding="utf-8")
            state_dir = root / "states"

            adapters = ToolAdapters(allowed_roots=(root,))
            with patch("orchestrator.adapters.run_agent_workflow") as mocked:
                mocked.return_value = {"ok": True, "status": "COMPLETE", "summary": "done", "run_id": "r", "artifacts": {}, "state_path": "s", "error": None}
                adapters.call_mcp_tool(
                    "mcp_agent_workflow_run",
                    {
                        "objective": "Apply approved patch",
                        "target_repo": str(repo),
                        "profile": "safe",
                        "patch_apply_request": {"patch_id": "p", "approval_id": "a"},
                    },
                )

            self.assertNotIn("patch_apply_request", mocked.call_args.kwargs)
            with open(Path(__file__).resolve().parents[2] / "node-mcp" / "src" / "contracts.mjs", encoding="utf-8") as fh:
                contracts = fh.read()
            with open(Path(__file__).resolve().parents[2] / "lmstudio_fastmcp_shim.py", encoding="utf-8") as fh:
                shim = fh.read()
            self.assertNotIn("patch_apply_request", contracts)
            self.assertNotIn("patch_apply_request", shim)
            self.assertEqual((repo / "app.py").read_text(encoding="utf-8"), "old\n")

    def test_no_raw_source_diff_logs_or_backup_contents_are_stored_inline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            _init_git(repo)
            source = "SECRET_SOURCE_BODY\n"
            (repo / "app.py").write_text(source, encoding="utf-8")
            state = root / "state"
            bootstrap_databases(state)
            patch_artifact = _create_patch(state, repo, before=source, after="changed\n")
            approval_id = _approve(state, patch_artifact, tests=[["python", "-m", "unittest"]])

            PatchApplyService(state / "queue.db", state / "rollback", allowed_roots=(repo,)).apply_approved_patch(
                patch_id=str(patch_artifact["patch_id"]),
                approval_id=approval_id,
                target_repo=repo,
            )
            with closing(sqlite3.connect(state / "queue.db")) as conn:
                dump = "\n".join(str(row) for row in conn.iterdump())

            self.assertNotIn("SECRET_SOURCE_BODY", dump)
            self.assertNotIn("-SECRET_SOURCE_BODY", dump)
            self.assertNotIn("changed", dump)


if __name__ == "__main__":
    unittest.main()
