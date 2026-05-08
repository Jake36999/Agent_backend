from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CodeReviewReport:
    architecture_overview_md: str   # <= 8000 chars
    dependency_graph_mmd: str       # <= 12000 chars
    code_review_summary_md: str     # <= 6000 chars
    next_actions_yaml: str          # <= 4000 chars
    artifact_index: dict[str, str]  # key -> artifact key name, <= 2000 chars serialized
