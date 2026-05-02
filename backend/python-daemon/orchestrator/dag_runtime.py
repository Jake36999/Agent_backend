from __future__ import annotations

from graphlib import TopologicalSorter


def topological_descendants(root_task_id: str, edges: list[tuple[str, str]]) -> list[str]:
    descendants = _collect_descendants(root_task_id, edges)
    sorter = TopologicalSorter()
    for node in descendants:
        sorter.add(node)
    for parent, child in edges:
        if child not in descendants:
            continue
        if parent == root_task_id:
            sorter.add(child)
        elif parent in descendants:
            sorter.add(child, parent)
    return [node for node in sorter.static_order() if node in descendants]


def _collect_descendants(root_task_id: str, edges: list[tuple[str, str]]) -> set[str]:
    children_by_parent: dict[str, list[str]] = {}
    for parent, child in edges:
        children_by_parent.setdefault(parent, []).append(child)
    seen: set[str] = set()
    stack = list(children_by_parent.get(root_task_id, []))
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(children_by_parent.get(node, []))
    return seen
