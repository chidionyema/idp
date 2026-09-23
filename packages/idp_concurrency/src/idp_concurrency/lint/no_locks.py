"""Forcing F1 — no `threading.Lock` / `RLock` / `Event` / `Semaphore` / `Condition`.

All shared-state coordination must go through `idp_concurrency.crdt_doc.CRDTDoc`
or `idp_concurrency.waitfree_queue.WaitFreeQueue`.

This is an AST visitor. Wire it in as a ruff plugin or call it from `bin/idp-ci`
as `python -m idp_concurrency.lint.no_locks <files...>`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_FROM_THREADING = {
    "Lock",
    "RLock",
    "Event",
    "Semaphore",
    "BoundedSemaphore",
    "Condition",
    "Barrier",
}

ALLOWED_PATHS = {
    "idp_concurrency/waitfree_queue.py",
    "idp_concurrency/lint/no_locks.py",
    "tests/",  # tests may use locks for determinism
}


class NoLocksVisitor(ast.NodeVisitor):
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []

    def _allowed(self) -> bool:
        return any(p in self.filepath for p in ALLOWED_PATHS)

    def report(self, node: ast.AST, msg: str) -> None:
        self.violations.append((node.lineno, msg))

    def visit_Import(self, node: ast.Import) -> None:
        if self._allowed():
            return
        for alias in node.names:
            if alias.name == "threading" or alias.name.startswith("threading."):
                self.report(
                    node,
                    f"Forcing F1: `import {alias.name}` is banned; "
                    f"use idp_concurrency.crdt_doc.CRDTDoc instead",
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._allowed() or node.module != "threading":
            return
        for alias in node.names:
            if alias.name in BANNED_FROM_THREADING:
                self.report(
                    node,
                    f"Forcing F1: `from threading import {alias.name}` "
                    f"is banned; use idp_concurrency.waitfree_queue.",
                )


def check_file(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(), filename=str(path))
    visitor = NoLocksVisitor(str(path))
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
