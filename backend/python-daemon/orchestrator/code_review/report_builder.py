from __future__ import annotations

from typing import Any

from .models import CodeReviewReport

_ARCH_CAP = 8000
_MMD_CAP = 12000
_SUMMARY_CAP = 6000
_NEXT_ACTIONS_CAP = 4000
_INDEX_CAP = 2000
_TRUNCATION_MARKER = "\n...[truncated]"


def _bounded(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _artifact_from_outputs(
    step_outputs: dict[str, dict[str, Any]],
    *step_ids: str,
    key: str,
) -> str:
    """Return first non-empty artifact value found across the given step IDs."""
    for sid in step_ids:
        v = step_outputs.get(sid, {}).get("artifacts", {}).get(key) or ""
        if v:
            return str(v)
    return ""


def _extract_repo_context(step_outputs: dict[str, dict[str, Any]]) -> str:
    return _artifact_from_outputs(step_outputs, "repo_context", key="repo_context_md")


def _extract_mermaid(step_outputs: dict[str, dict[str, Any]]) -> str:
    return _artifact_from_outputs(step_outputs, "mermaid", key="dependency_graph_mmd")


def _extract_dependency_counts(step_outputs: dict[str, dict[str, Any]]) -> str:
    return _artifact_from_outputs(
        step_outputs, "dependency_graph", key="dependency_graph_summary"
    )


def _extract_code_map_summary(step_outputs: dict[str, dict[str, Any]]) -> str:
    return _artifact_from_outputs(step_outputs, "repo_context", "code_map", key="code_map_summary")


def _build_architecture_overview(
    target_repo: str,
    repo_context: str,
    code_map_summary: str,
) -> str:
    repo_name = target_repo.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or target_repo
    parts = [
        f"# Architecture Overview: {repo_name}",
        "",
        "> **Analysis type:** read-only. No files were modified.",
        "",
    ]
    if code_map_summary:
        parts += ["## Repository Scale", "", code_map_summary, ""]
    if repo_context:
        parts += ["## Repository Context", "", repo_context, ""]
    return _bounded("\n".join(parts), _ARCH_CAP)


def _build_summary_md(
    target_repo: str,
    repo_context: str,
    graph_counts: str,
    mmd_present: bool,
    receipts: list[str],
) -> str:
    repo_name = target_repo.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or target_repo
    parts = [
        f"# Code Review Summary: {repo_name}",
        "",
        "**No files modified. Read-only analysis.**",
        "",
    ]
    if repo_context:
        preview = repo_context[:600].rstrip()
        parts += ["## Repository Context (preview)", "", preview, ""]
    if graph_counts:
        parts += ["## Dependency Graph", "", graph_counts, ""]
    if mmd_present:
        parts += ["## Mermaid Diagram", "", "Artifact: `dependency_graph_mmd`", ""]
    if receipts:
        parts += ["## Capability Receipts", ""]
        for r in receipts:
            parts.append(f"- {r}")
        parts.append("")
    return _bounded("\n".join(parts), _SUMMARY_CAP)


def _build_next_actions_yaml(
    graph_counts: str,
    repo_context: str,
    code_map_summary: str,
) -> str:
    has_graph = bool(graph_counts)
    has_large_files = "lines" in code_map_summary if code_map_summary else False

    items: list[str] = []
    if has_large_files:
        items.append("  - inspect_large_files: candidate follow-up — review files with high line counts")
    if has_graph:
        items.append("  - inspect_high_fan_in_modules: candidate follow-up — modules with many incoming edges")
        items.append("  - inspect_external_dependencies: candidate follow-up — review external dependency list")
    items.append("  - identify_test_coverage_gaps: candidate follow-up — check for test directory presence")
    items.append("  - review_dependency_graph_edges: candidate follow-up — inspect modules with many outgoing links")

    lines = [
        "# Suggested follow-up actions (deterministic — not LLM-generated critique)",
        "suggested_followups:",
    ] + items
    return _bounded("\n".join(lines), _NEXT_ACTIONS_CAP)


def _build_artifact_index(artifact_keys: list[str]) -> dict[str, str]:
    return {k: k for k in artifact_keys}


def build_code_review_report(
    *,
    target_repo: str,
    step_outputs: dict[str, dict[str, Any]],
    pipeline_receipt: dict[str, Any] | None = None,
) -> CodeReviewReport:
    repo_context = _extract_repo_context(step_outputs)
    graph_counts = _extract_dependency_counts(step_outputs)
    mermaid_diagram = _extract_mermaid(step_outputs)
    code_map_summary = _extract_code_map_summary(step_outputs)

    receipts: list[str] = []
    if pipeline_receipt:
        cid = pipeline_receipt.get("capability_id", "")
        tier = pipeline_receipt.get("risk_tier", "")
        receipts.append(f"{cid} [{tier}]")

    architecture_overview_md = _build_architecture_overview(
        target_repo, repo_context, code_map_summary
    )
    dependency_graph_mmd = _bounded(mermaid_diagram or "graph TD\n  %% no dependency data", _MMD_CAP)
    code_review_summary_md = _build_summary_md(
        target_repo, repo_context, graph_counts, bool(mermaid_diagram), receipts
    )
    next_actions_yaml = _build_next_actions_yaml(graph_counts, repo_context, code_map_summary)

    artifact_keys = [
        "architecture_overview_md",
        "dependency_graph_mmd",
        "code_review_summary_md",
        "next_actions_yaml",
    ]
    artifact_index = _build_artifact_index(artifact_keys)

    return CodeReviewReport(
        architecture_overview_md=architecture_overview_md,
        dependency_graph_mmd=dependency_graph_mmd,
        code_review_summary_md=code_review_summary_md,
        next_actions_yaml=next_actions_yaml,
        artifact_index=artifact_index,
    )
