from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath

from .models import DependencyEdge

_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"]*?\s+from\s+)?|require\s*\(\s*)['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_JS_DYNAMIC_RE = re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""")


def _lang(rel_path: str) -> str:
    ext = rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
    if ext == "py":
        return "python"
    if ext in ("js", "mjs", "jsx"):
        return "javascript"
    if ext in ("ts", "tsx"):
        return "typescript"
    return ""


def _py_module_map(all_rel_paths: list[str]) -> dict[str, str]:
    """Map dotted module name → rel_path for all Python files."""
    m: dict[str, str] = {}
    for rp in all_rel_paths:
        if not rp.endswith(".py"):
            continue
        parts = rp.replace("\\", "/").split("/")
        if parts[-1] == "__init__.py":
            key = ".".join(parts[:-1])
        else:
            key = ".".join(parts)[:-3]  # strip .py
        m[key] = rp
    return m


def _resolve_py_absolute(module: str, module_map: dict[str, str]) -> str | None:
    """Try to find the longest prefix of `module` that matches a known file."""
    candidate = module
    while candidate:
        if candidate in module_map:
            return module_map[candidate]
        idx = candidate.rfind(".")
        if idx < 0:
            break
        candidate = candidate[:idx]
    return None


def _package_dir(from_rel: str, level: int) -> str:
    """Return the anchor directory for a relative import at `level` from `from_rel`.

    level=1 → current package dir (parent of the file)
    level=2 → grandparent, etc.
    """
    parts = from_rel.replace("\\", "/").split("/")
    anchor = parts[:-level]
    return "/".join(anchor)


def _resolve_py_relative(module: str, level: int, from_rel: str) -> str | None:
    """Resolve a relative Python import with a non-None module to a rel_path candidate."""
    anchor = _package_dir(from_rel, level)
    sub = module.replace(".", "/")
    base = f"{anchor}/{sub}" if anchor else sub
    return base + ".py"


def extract_python_edges(
    source: str, rel_path: str, module_map: dict[str, str], known_paths: set[str]
) -> list[DependencyEdge]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    edges: list[DependencyEdge] = []
    seen: set[tuple[str, str]] = set()

    def _add(target: str, kind: str, is_ext: bool) -> None:
        key = (rel_path, target)
        if key not in seen:
            seen.add(key)
            edges.append(DependencyEdge(source=rel_path, target=target, kind=kind, is_external=is_ext))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_py_absolute(alias.name, module_map)
                if resolved and resolved in known_paths and resolved != rel_path:
                    _add(resolved, "import", False)
                elif resolved is None:
                    _add(alias.name.split(".")[0], "import", True)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                if node.module:
                    # e.g. from .utils import helper  →  resolve .utils
                    candidate = _resolve_py_relative(node.module, node.level, rel_path)
                    if candidate in known_paths and candidate != rel_path:
                        _add(candidate, "from_import", False)
                    else:
                        pkg = candidate[: -len(".py")] + "/__init__.py"
                        if pkg in known_paths and pkg != rel_path:
                            _add(pkg, "from_import", False)
                else:
                    # e.g. from . import models, utils  →  resolve each name
                    anchor = _package_dir(rel_path, node.level)
                    for alias in node.names:
                        base = f"{anchor}/{alias.name}" if anchor else alias.name
                        for suffix in (".py", "/__init__.py"):
                            target = base + suffix
                            if target in known_paths and target != rel_path:
                                _add(target, "from_import", False)
                                break
            elif node.module:
                resolved = _resolve_py_absolute(node.module, module_map)
                if resolved and resolved in known_paths and resolved != rel_path:
                    _add(resolved, "from_import", False)
                elif resolved is None:
                    _add(node.module.split(".")[0], "from_import", True)

    return edges


def extract_js_edges(
    source: str, rel_path: str, known_paths: set[str]
) -> list[DependencyEdge]:
    edges: list[DependencyEdge] = []
    seen: set[tuple[str, str]] = set()
    base_dir = "/".join(rel_path.replace("\\", "/").split("/")[:-1])

    def _add(target: str, kind: str, is_ext: bool) -> None:
        key = (rel_path, target)
        if key not in seen:
            seen.add(key)
            edges.append(DependencyEdge(source=rel_path, target=target, kind=kind, is_external=is_ext))

    raw_specifiers = [m.group(1) for m in _JS_IMPORT_RE.finditer(source)]
    raw_specifiers += [m.group(1) for m in _JS_DYNAMIC_RE.finditer(source)]

    for spec in raw_specifiers:
        if spec.startswith("."):
            # Relative import — resolve to a rel_path
            joined = str(PurePosixPath(base_dir) / spec) if base_dir else spec
            # Try common extensions in order
            resolved = None
            for suffix in ("", ".js", ".mjs", ".ts", ".tsx", "/index.js", "/index.ts"):
                candidate = (joined + suffix).lstrip("/")
                if candidate in known_paths and candidate != rel_path:
                    resolved = candidate
                    break
            if resolved:
                _add(resolved, "import", False)
            # if unresolvable, skip (don't add unknown relative paths as external)
        else:
            # Package import — first path segment is the package name
            pkg = spec.split("/")[0].lstrip("@")
            if spec.startswith("@"):
                pkg = "/".join(spec.split("/")[:2])
            _add(pkg, "import", True)

    return edges


class DependencyExtractor:
    def __init__(self, all_rel_paths: list[str]) -> None:
        self._module_map = _py_module_map(all_rel_paths)
        self._known_paths = set(all_rel_paths)

    def extract(self, rel_path: str, source: str) -> list[DependencyEdge]:
        lang = _lang(rel_path)
        if lang == "python":
            return extract_python_edges(source, rel_path, self._module_map, self._known_paths)
        if lang in ("javascript", "typescript"):
            return extract_js_edges(source, rel_path, self._known_paths)
        return []
