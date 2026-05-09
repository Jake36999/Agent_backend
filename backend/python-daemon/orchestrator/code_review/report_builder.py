from __future__ import annotations

import json
from typing import Any

from .heuristics import CodeReviewHeuristics, extract_heuristics
from .models import CodeReviewReport

_ARCH_CAP = 10000
_MMD_CAP = 12000
_SUMMARY_CAP = 8000
_NEXT_ACTIONS_CAP = 6000
_HEURISTICS_CAP = 6000
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
    return _artifact_from_outputs(step_outputs, "dependency_graph", key="dependency_graph_summary")


def _extract_code_map_summary(step_outputs: dict[str, dict[str, Any]]) -> str:
    return _artifact_from_outputs(step_outputs, "repo_context", "code_map", key="code_map_summary")


def _yaml_item(id: str, signal: str, reason: str, file: str | None = None) -> str:
    safe_reason = reason.replace('"', '\\"')
    lines = [f"  - id: {id}", f"    signal: {signal}"]
    if file:
        safe_file = file.replace('"', '\\"')
        lines.append(f'    file: "{safe_file}"')
    lines.append(f'    reason: "{safe_reason}"')
    return "\n".join(lines)


def _build_architecture_overview(
    target_repo: str,
    repo_context: str,
    code_map_summary: str,
    heuristics: CodeReviewHeuristics,
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

    if heuristics.test_directories:
        dirs_str = ", ".join(f"`{d}`" for d in heuristics.test_directories[:5])
        parts += [f"**Test directories:** {dirs_str}", ""]
    if heuristics.likely_entrypoints:
        eps_str = ", ".join(f"`{ep}`" for ep in heuristics.likely_entrypoints[:5])
        parts += [f"**Likely entrypoints:** {eps_str}", ""]

    if heuristics.largest_files:
        parts += ["## Largest Files (by line count)", ""]
        for fs in heuristics.largest_files[:10]:
            parts.append(f"- `{fs.path}` — {fs.line_count:,} lines")
        parts.append("")

    if repo_context:
        parts += ["## Repository Context", "", repo_context, ""]

    return _bounded("\n".join(parts), _ARCH_CAP)


def _build_summary_md(
    target_repo: str,
    repo_context: str,
    graph_counts: str,
    mmd_present: bool,
    receipts: list[str],
    heuristics: CodeReviewHeuristics,
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

    if heuristics.highest_fan_in:
        parts += ["## High Fan-in Modules", ""]
        for ds in heuristics.highest_fan_in[:5]:
            parts.append(f"- `{ds.path}` — imported by {ds.count} module(s)")
        parts.append("")
    if heuristics.highest_fan_out:
        parts += ["## High Fan-out Modules", ""]
        for ds in heuristics.highest_fan_out[:5]:
            parts.append(f"- `{ds.path}` — imports {ds.count} internal module(s)")
        parts.append("")
    if heuristics.orphan_files:
        parts += [f"**Orphan files (no detected edges):** {len(heuristics.orphan_files)}", ""]
    if heuristics.external_dependencies:
        ext_preview = ", ".join(f"`{d}`" for d in heuristics.external_dependencies[:10])
        parts += [f"**External dependencies:** {ext_preview}", ""]
    if heuristics.todo_fixme_counts:
        total = sum(t.count for t in heuristics.todo_fixme_counts)
        parts += [
            f"**TODO/FIXME markers:** {total} across {len(heuristics.todo_fixme_counts)} file(s)",
            "",
        ]

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
    heuristics: CodeReviewHeuristics,
) -> str:
    items: list[str] = []

    for fs in heuristics.largest_files[:3]:
        items.append(_yaml_item(
            "inspect_large_file", "large_file",
            f"Large file — {fs.line_count:,} lines. candidate follow-up for module split.",
            file=fs.path,
        ))
    for ds in heuristics.highest_fan_in[:3]:
        items.append(_yaml_item(
            "inspect_high_fan_in", "high_fan_in",
            f"Imported by {ds.count} internal module(s) — candidate follow-up for coupling review.",
            file=ds.path,
        ))
    for ds in heuristics.highest_fan_out[:2]:
        items.append(_yaml_item(
            "inspect_high_fan_out", "high_fan_out",
            f"Imports {ds.count} internal module(s) — candidate follow-up for cohesion review.",
            file=ds.path,
        ))
    for ts in heuristics.todo_fixme_counts[:3]:
        kinds_str = ", ".join(ts.kinds)
        items.append(_yaml_item(
            "review_todos", "todo_fixme",
            f"Contains {ts.count} TODO/FIXME marker(s) ({kinds_str}) — candidate follow-up.",
            file=ts.path,
        ))
    if heuristics.test_directories:
        items.append(_yaml_item(
            "review_test_coverage", "test_directory_present",
            "Test directories detected — candidate follow-up for coverage review.",
        ))
    else:
        items.append(_yaml_item(
            "add_test_directory", "no_test_directory",
            "No test directory detected — candidate follow-up.",
        ))
    if heuristics.external_dependencies:
        deps_preview = ", ".join(heuristics.external_dependencies[:5])
        items.append(_yaml_item(
            "inspect_external_dependencies", "external_deps",
            f"External dependencies include: {deps_preview} — candidate follow-up.",
        ))

    if not items:
        has_graph = bool(graph_counts)
        has_large_files = "lines" in code_map_summary if code_map_summary else False
        if has_large_files:
            items.append(_yaml_item("inspect_large_files", "large_file",
                                    "candidate follow-up — review files with high line counts"))
        if has_graph:
            items.append(_yaml_item("inspect_high_fan_in_modules", "high_fan_in",
                                    "candidate follow-up — modules with many incoming edges"))
            items.append(_yaml_item("inspect_external_dependencies", "external_deps",
                                    "candidate follow-up — review external dependency list"))
        items.append(_yaml_item("identify_test_coverage_gaps", "generic",
                                "candidate follow-up — check for test directory presence"))
        items.append(_yaml_item("review_dependency_graph_edges", "graph_edges",
                                "candidate follow-up — inspect modules with many outgoing links"))

    lines = [
        "# Suggested follow-up actions (deterministic — not LLM-generated critique)",
        "suggested_followups:",
    ] + items
    return _bounded("\n".join(lines), _NEXT_ACTIONS_CAP)


def _build_heuristics_json(heuristics: CodeReviewHeuristics) -> str:
    data = {
        "largest_files": [{"path": f.path, "line_count": f.line_count} for f in heuristics.largest_files],
        "highest_fan_in": [{"path": d.path, "count": d.count} for d in heuristics.highest_fan_in],
        "highest_fan_out": [{"path": d.path, "count": d.count} for d in heuristics.highest_fan_out],
        "orphan_files": list(heuristics.orphan_files),
        "external_dependencies": list(heuristics.external_dependencies),
        "todo_fixme_counts": [
            {"path": t.path, "count": t.count, "kinds": list(t.kinds)}
            for t in heuristics.todo_fixme_counts
        ],
        "test_directories": list(heuristics.test_directories),
        "likely_entrypoints": list(heuristics.likely_entrypoints),
    }
    return _bounded(json.dumps(data, indent=2), _HEURISTICS_CAP)


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
    heuristics = extract_heuristics(step_outputs)

    receipts: list[str] = []
    if pipeline_receipt:
        cid = pipeline_receipt.get("capability_id", "")
        tier = pipeline_receipt.get("risk_tier", "")
        receipts.append(f"{cid} [{tier}]")

    architecture_overview_md = _build_architecture_overview(
        target_repo, repo_context, code_map_summary, heuristics
    )
    dependency_graph_mmd = _bounded(mermaid_diagram or "graph TD\n  %% no dependency data", _MMD_CAP)
    code_review_summary_md = _build_summary_md(
        target_repo, repo_context, graph_counts, bool(mermaid_diagram), receipts, heuristics
    )
    next_actions_yaml = _build_next_actions_yaml(
        graph_counts, repo_context, code_map_summary, heuristics
    )
    heuristics_json = _build_heuristics_json(heuristics)

    artifact_keys = [
        "architecture_overview_md",
        "dependency_graph_mmd",
        "code_review_summary_md",
        "next_actions_yaml",
        "heuristics_json",
    ]
    artifact_index = _build_artifact_index(artifact_keys)

    return CodeReviewReport(
        architecture_overview_md=architecture_overview_md,
        dependency_graph_mmd=dependency_graph_mmd,
        code_review_summary_md=code_review_summary_md,
        next_actions_yaml=next_actions_yaml,
        heuristics_json=heuristics_json,
        artifact_index=artifact_index,
    )
