from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import RuntimeConfig
from .patching.admin_service import PatchAdminService
from .patching.smoke import run_patch_flow_smoke
from .runtime import build_runtime


def _add_state_dir(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-dir", type=Path)


def _patch_admin(args: argparse.Namespace, config: RuntimeConfig) -> PatchAdminService:
    state_dir = Path(args.state_dir).resolve() if args.state_dir else config.state_dir
    return PatchAdminService(state_dir / "queue.db", state_dir / "rollback")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aletheia-admin")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("health")
    subcommands.add_parser("show-config")
    reconcile = subcommands.add_parser("reconcile-project")
    reconcile.add_argument("project_id")
    dead = subcommands.add_parser("list-dead-letters")
    dead.add_argument("--limit", type=int, default=50)
    smoke = subcommands.add_parser("smoke-patch-flow")
    _add_state_dir(smoke)
    smoke.add_argument("--allowed-root", type=Path, required=True)
    smoke.add_argument("--target-repo-test-fixture", type=Path)
    list_artifacts = subcommands.add_parser("list-patch-artifacts")
    _add_state_dir(list_artifacts)
    list_artifacts.add_argument("--limit", type=int, default=50)
    show_artifact = subcommands.add_parser("show-patch-artifact")
    _add_state_dir(show_artifact)
    show_artifact.add_argument("patch_id")
    list_apply = subcommands.add_parser("list-patch-apply-runs")
    _add_state_dir(list_apply)
    list_apply.add_argument("--limit", type=int, default=50)
    show_apply = subcommands.add_parser("show-patch-apply-run")
    _add_state_dir(show_apply)
    show_apply.add_argument("apply_run_id")
    list_approvals = subcommands.add_parser("list-approvals")
    _add_state_dir(list_approvals)
    list_approvals.add_argument("--limit", type=int, default=50)
    list_snapshots = subcommands.add_parser("list-file-snapshots")
    _add_state_dir(list_snapshots)
    list_snapshots.add_argument("--apply-run-id", required=True)
    verify = subcommands.add_parser("verify-patch-rollback")
    _add_state_dir(verify)
    verify.add_argument("apply_run_id")
    restore = subcommands.add_parser("restore-patch-run")
    _add_state_dir(restore)
    restore.add_argument("apply_run_id")
    restore.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)

    config = RuntimeConfig.from_env()
    if args.command == "show-config":
        print(
            json.dumps(
                {
                    "project_root": str(config.project_root),
                    "state_dir": str(config.state_dir),
                    "allowed_roots": [str(root) for root in config.allowed_roots],
                    "chroma_path": str(config.chroma_path),
                    "bridge_host": config.bridge_host,
                    "bridge_port": config.bridge_port,
                    "ocr_enabled": config.ocr_command is not None,
                },
                sort_keys=True,
            )
        )
        return

    if args.command == "smoke-patch-flow":
        state_dir = Path(args.state_dir).resolve() if args.state_dir else config.state_dir
        payload = run_patch_flow_smoke(
            state_dir=state_dir,
            allowed_root=args.allowed_root,
            target_repo_test_fixture=args.target_repo_test_fixture,
        )
        print(json.dumps(payload, sort_keys=True))
        return
    if args.command == "list-patch-artifacts":
        print(json.dumps(_patch_admin(args, config).list_patch_artifacts(args.limit), sort_keys=True))
        return
    if args.command == "show-patch-artifact":
        print(json.dumps(_patch_admin(args, config).show_patch_artifact(args.patch_id), sort_keys=True))
        return
    if args.command == "list-patch-apply-runs":
        print(json.dumps(_patch_admin(args, config).list_patch_apply_runs(args.limit), sort_keys=True))
        return
    if args.command == "show-patch-apply-run":
        print(json.dumps(_patch_admin(args, config).show_patch_apply_run(args.apply_run_id), sort_keys=True))
        return
    if args.command == "list-approvals":
        print(json.dumps(_patch_admin(args, config).list_approvals(args.limit), sort_keys=True))
        return
    if args.command == "list-file-snapshots":
        print(json.dumps(_patch_admin(args, config).list_file_snapshots(args.apply_run_id), sort_keys=True))
        return
    if args.command == "verify-patch-rollback":
        print(json.dumps(_patch_admin(args, config).verify_rollback(args.apply_run_id), sort_keys=True))
        return
    if args.command == "restore-patch-run":
        print(json.dumps(_patch_admin(args, config).restore_patch_run(args.apply_run_id, confirm=args.confirm), sort_keys=True))
        return

    runtime = build_runtime(config)
    try:
        if args.command == "health":
            payload = runtime.health()
        elif args.command == "reconcile-project":
            payload = runtime.reconcile_project(args.project_id)
        elif args.command == "list-dead-letters":
            payload = runtime.dead_letters(args.limit)
        else:
            raise SystemExit(f"unknown command: {args.command}")
        print(json.dumps(payload, sort_keys=True))
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
