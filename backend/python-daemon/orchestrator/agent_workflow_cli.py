from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent_workflow.mcp_tool import run_agent_workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic Aletheia agent workflow.")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--profile", default="safe")
    parser.add_argument("--allow-ingest", action="store_true", default=False)
    parser.add_argument("--include-report-preview", action="store_true", default=False)
    parser.add_argument("--use-model-phases", action="store_true", default=False)
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args(argv)

    result = run_agent_workflow(
        objective=args.objective,
        target_repo=args.target_repo,
        profile=args.profile,
        allow_ingest=args.allow_ingest,
        include_report_preview=args.include_report_preview,
        use_model_phases=args.use_model_phases,
        state_dir=args.state_dir,
    )

    artifact_paths = []
    for value in (result.get("artifacts") or {}).values():
        if isinstance(value, str) and value not in artifact_paths:
            artifact_paths.append(value)

    print(f"run_id: {result.get('run_id', '')}")
    print(f"final_status: {result.get('status', '')}")
    print(f"summary: {result.get('summary', '')}")
    print(f"artifact_paths: {json.dumps(artifact_paths, ensure_ascii=False)}")
    print(result.get("state_path", ""))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
