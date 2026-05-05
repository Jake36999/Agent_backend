from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path

from orchestrator import admin
from orchestrator.active_partition.models import ActivePartition
from orchestrator.active_partition.repo import ActivePartitionRepository
from orchestrator.db_bootstrap import bootstrap_databases
from orchestrator.memory.repo import MemoryRepository
from orchestrator.memory.service import MemoryService
from orchestrator.patching.admin_service import PatchAdminService
from orchestrator.patching.audit import PatchAuditService
from orchestrator.patching.repo import PatchArtifactRepository
from orchestrator.patching.smoke import run_patch_flow_smoke


class FakeMemoryService:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def commit_memory(self, **kwargs):
        self.calls.append(kwargs)
        return dict(self.result)


class FakeChroma:
    def upsert_chunks(self, **kwargs):
        return {"chunks_indexed": len(kwargs["chunks"])}


def _cli_json(argv: list[str]) -> dict[str, object] | list[dict[str, object]]:
    out = io.StringIO()
    with redirect_stdout(out):
        admin.main(argv)
    return json.loads(out.getvalue())


class PatchAdminCliTests(unittest.TestCase):
    def test_smoke_harness_completes_apply_and_rollback_with_compact_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            allowed = root / "allowed"
            allowed.mkdir()
            bootstrap_databases(state)

            result = run_patch_flow_smoke(state_dir=state, allowed_root=allowed)

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "SMOKE_PASSED")
            self.assertTrue(result["rollback"]["ok"])
            self.assertEqual(result["post_restore_sha256"], result["original_sha256"])
            self.assertNotIn("old smoke", json.dumps(result))
            self.assertNotIn("new smoke", json.dumps(result))
            with closing(sqlite3.connect(state / "queue.db")) as conn:
                apply_runs = conn.execute("SELECT count(*) FROM patch_apply_runs").fetchone()[0]
                snapshots = conn.execute("SELECT count(*) FROM file_snapshots").fetchone()[0]
            self.assertEqual(apply_runs, 1)
            self.assertEqual(snapshots, 1)

    def test_smoke_harness_refuses_non_empty_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "real.py").write_text("do not touch\n", encoding="utf-8")
            bootstrap_databases(state)

            result = run_patch_flow_smoke(state_dir=state, allowed_root=root, target_repo_test_fixture=fixture)

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "POLICY_BLOCK")
            self.assertEqual((fixture / "real.py").read_text(encoding="utf-8"), "do not touch\n")

    def test_admin_commands_return_compact_json_without_raw_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            allowed = root / "allowed"
            allowed.mkdir()
            bootstrap_databases(state)
            smoke = run_patch_flow_smoke(state_dir=state, allowed_root=allowed)
            patch_id = str(smoke["patch_id"])
            apply_run_id = str(smoke["apply_run_id"])

            outputs = [
                _cli_json(["list-patch-artifacts", "--state-dir", str(state), "--limit", "5"]),
                _cli_json(["show-patch-artifact", "--state-dir", str(state), patch_id]),
                _cli_json(["list-patch-apply-runs", "--state-dir", str(state), "--limit", "5"]),
                _cli_json(["show-patch-apply-run", "--state-dir", str(state), apply_run_id]),
                _cli_json(["list-approvals", "--state-dir", str(state), "--limit", "5"]),
                _cli_json(["list-file-snapshots", "--state-dir", str(state), "--apply-run-id", apply_run_id]),
            ]
            text = json.dumps(outputs, sort_keys=True)

            self.assertIn(patch_id, text)
            self.assertIn(apply_run_id, text)
            self.assertNotIn("--- a/", text)
            self.assertNotIn("old smoke", text)
            self.assertNotIn("new smoke", text)
            self.assertNotIn("stdout_tail", text)
            self.assertNotIn("backup_contents", text)

    def test_rollback_verification_reports_missing_backup_and_restore_requires_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            allowed = root / "allowed"
            allowed.mkdir()
            bootstrap_databases(state)
            smoke = run_patch_flow_smoke(state_dir=state, allowed_root=allowed, restore_after_apply=False)
            apply_run_id = str(smoke["apply_run_id"])

            blocked = _cli_json(["restore-patch-run", "--state-dir", str(state), apply_run_id])
            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["status"], "CONFIRMATION_REQUIRED")

            snapshots = PatchArtifactRepository(state / "queue.db").list_file_snapshots(apply_run_id)
            Path(str(snapshots[0].backup_path)).unlink()
            verify = _cli_json(["verify-patch-rollback", "--state-dir", str(state), apply_run_id])

            self.assertFalse(verify["ok"])
            self.assertEqual(verify["status"], "SNAPSHOT_MISSING")
            self.assertNotIn("old smoke", json.dumps(verify))

    def test_audit_summary_and_memory_commit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            allowed = root / "allowed"
            allowed.mkdir()
            bootstrap_databases(state)
            active_repo = ActivePartitionRepository(state / "queue.db")
            active_repo.set_active_partition(
                ActivePartition("local-lmstudio", "project-1", "scope-1", None, None, "high", "test", "now")
            )
            memory = MemoryService(MemoryRepository(state / "queue.db"), active_repo, FakeChroma())  # type: ignore[arg-type]
            smoke = run_patch_flow_smoke(state_dir=state, allowed_root=allowed, memory_service=memory, restore_after_apply=False)

            summary = PatchAuditService(state / "queue.db").summary_for_apply_run(str(smoke["apply_run_id"]))

            self.assertEqual(summary["patch"]["patch_id"], smoke["patch_id"])
            self.assertEqual(summary["apply"]["apply_run_id"], smoke["apply_run_id"])
            self.assertEqual(summary["snapshot_count"], 1)
            self.assertEqual(summary["rollback_available"], True)
            self.assertEqual(summary["memory_commit_status"], "COMMITTED")
            self.assertEqual(summary["memory"]["index_status"], "indexed")
            self.assertNotIn("--- a/", json.dumps(summary))

    def test_memory_commit_skips_compactly_without_memory_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            allowed = root / "allowed"
            allowed.mkdir()
            bootstrap_databases(state)

            smoke = run_patch_flow_smoke(state_dir=state, allowed_root=allowed)

            self.assertEqual(smoke["memory_commit"]["status"], "SKIPPED")
            self.assertEqual(smoke["memory_commit"]["reason"], "memory_service_unavailable")

    def test_failure_diagnostics_are_bounded_and_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
            bootstrap_databases(state)

            result = PatchAdminService(state / "queue.db", state / "rollback").verify_rollback("missing")

            self.assertFalse(result["ok"])
            self.assertLess(len(json.dumps(result)), 1200)
            self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main()
