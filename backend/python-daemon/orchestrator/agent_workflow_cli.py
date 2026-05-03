from __future__ import annotations

import argparse

from .agent_workflow import WorkflowRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Run opt-in deterministic Agent Workflow Controller.")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--profile", default="safe")
    args = parser.parse_args()

    prompt = f"Objective: {args.objective}\nTarget repo: {args.target_repo}\nProfile: {args.profile}"
    state, response = WorkflowRunner().run(
        prompt,
        objective=args.objective,
        target_repo=args.target_repo,
        profile=args.profile,
    )
    final_status = "partial" if state.errors or any(todo.get("status") == "blocked" for todo in state.todos) else "complete"
    print(f"run_id: {state.run_id}")
    print(f"final_status: {final_status}")
    print(f"summary: {response}")
    print(f"artifact_paths: {sorted(state.artifacts.values())}")
    print(state.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
