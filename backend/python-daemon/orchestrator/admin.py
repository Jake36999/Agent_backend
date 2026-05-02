from __future__ import annotations

import argparse
import json

from .config import RuntimeConfig
from .runtime import build_runtime


def main() -> None:
    parser = argparse.ArgumentParser(prog="aletheia-admin")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("health")
    subcommands.add_parser("show-config")
    reconcile = subcommands.add_parser("reconcile-project")
    reconcile.add_argument("project_id")
    dead = subcommands.add_parser("list-dead-letters")
    dead.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

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
