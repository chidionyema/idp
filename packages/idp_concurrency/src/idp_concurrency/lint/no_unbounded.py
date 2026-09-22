"""Forcing F2 — `asyncio.create_task()` is banned outside a TaskGroup.

Every concurrent unit of work must enter through `idp_concurrency.task_scope.task_scope`
so cancellation has a boundary.

This is an AST visitor. Wire it in as a ruff plugin or call it from `bin/idp-ci`
as `python -m idp_concurrency.lint.no_unbounded <files...>`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_CALLS = {
    ("asyncio", "create_task"),
    ("asyncio", "ensure_future"),
    ("asyncio", "gather"),  # gather() outside a scope has no cancel boundary
}

ALLOWED_PATHS = {
    "idp_concurrency/task_scope.py",
    "idp_concurrency/lint/no_unbounded.py",
    "tests/",
}


def _call_name(node: ast.Call) -> tuple[str, str] | None:
    """Return (module, attr) for `mod.attr(...)` calls, else None."""
    f = node.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f.value.id, f.attr
    return None


def _is_inside_task_group(node: ast.AST, tree: ast.AST) -> bool:
    """Walk up the tree to find an enclosing `async with` whose manager is
    `idp_concurrency.task_scope.task_scope(...)` or `anyio.create_task_group()`.
    """
    # Build a parent map
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    cur: ast.AST | None = parents.get(id(node))
    while cur is not None:
        if isinstance(cur, ast.AsyncWith):
            for item in cur.items:
                ctx = item.context_expr
                if _is_task_group_manager(ctx):
                    return True
        cur = parents.get(id(cur))
    return False


def _is_task_group_manager(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        name = _call_name(node)
        if name and name[1] in {"create_task_group", "task_scope"}:
            return True
        if name and name[1] == "task_scope" and name[0] == "task_scope":
            return True
    if isinstance(node, ast.Attribute):
        # `task_scope.task_scope(...)` qualifies
        if isinstance(node.value, ast.Name):
            return True
    return False


class NoUnboundedVisitor(ast.NodeVisitor):
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []

    def _allowed(self) -> bool:
        return any(p in self.filepath for p in ALLOWED_PATHS)

    def report(self, node: ast.AST, msg: str) -> None:
        self.violations.append((node.lineno, msg))

    def visit_Call(self, node: ast.Call) -> None:
        if self._allowed():
            return
        name = _call_name(node)
        if name and name in BANNED_CALLS:
            tree = ast.Module(body=list(ast.walk(ast.parse(""))), type_ignores=[])
            # Find the enclosing module by walking parents via the visitor's
            # already-visited tree. We piggyback on the AST passed to check_file.
            if not _has_enclosing_task_group(node, self._tree):
                self.report(
                    node,
                    f"Forcing F2: `{name[0]}.{name[1]}()` must be inside "
                    "`async with idp_concurrency.task_scope.task_scope():`",
                )
        self.generic_visit(node)

    def visit(self, node: ast.AST) -> None:  # noqa: D401
        # Capture the tree for parent-walk checks.
        self._tree = node
        super().visit(node)


def _has_enclosing_task_group(node: ast.AST, tree: ast.AST) -> bool:
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    cur: ast.AST | None = parents.get(id(node))
    while cur is not None:
        if isinstance(cur, ast.AsyncWith):
            for item in cur.items:
                if _is_task_group_manager(item.context_expr):
                    return True
        cur = parents.get(id(cur))
    return False


def check_file(path: Path) -> list[tuple[int, str]]:
    src = path.read_text()
    tree = ast.parse(src, filename=str(path))
    visitor = NoUnboundedVisitor(str(path))
    visitor.visit(tree)
    return visitor.violations


def main(argv: list[str]) -> int:
    failures = 0
    for arg in argv[1:]:
        p = Path(arg)
        if not p.exists():
            continue
        for line, msg in check_file(p):
            print(f"{p}:{line}: {msg}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
