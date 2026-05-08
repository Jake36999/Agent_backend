from __future__ import annotations

import re

from .models import DependencyGraph

_SAFE_ID = re.compile(r"[^a-zA-Z0-9]")


def _node_id(path: str) -> str:
    return _SAFE_ID.sub("_", path)


def format_mermaid(graph: DependencyGraph, *, max_nodes: int = 80) -> str:
    """Render a DependencyGraph as a Mermaid flowchart string."""
    # Limit to internal nodes only; external deps clutter diagrams
    internal_nodes = sorted(graph.nodes)[:max_nodes]
    internal_set = set(internal_nodes)

    lines = ["graph TD"]
    for node in internal_nodes:
        nid = _node_id(node)
        label = node.replace('"', "'")
        lines.append(f'  {nid}["{label}"]')

    seen: set[tuple[str, str]] = set()
    for edge in graph.edges:
        if edge.is_external:
            continue
        if edge.source not in internal_set or edge.target not in internal_set:
            continue
        key = (_node_id(edge.source), _node_id(edge.target))
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  {_node_id(edge.source)} --> {_node_id(edge.target)}")

    return "\n".join(lines)
