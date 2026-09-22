"""Forcing F3 — bare `httpx` / `aiohttp` / `requests` / `urllib` are banned.

All HTTP I/O must go through `idp_concurrency.tracer.TracedClient`.

This is an AST visitor. Wire it in as a ruff plugin or call it from `bin/idp-ci`
as `python -m idp_concurrency.lint.no_untraced <files...>`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_MODULES = {
    "httpx",
    "aiohttp",
    "requests",
    "urllib",
    "urllib3",
}

ALLOWED_PATHS = {
    "idp_concurrency/lint/no_untraced.py",
    "idp_concurrency/tracer.py",
    "tests/",
}

ALLOWED_BASENAMES = {
    "tracer.py",  # the only file allowed to import httpx
}


class NoUntracedVisitor(ast.NodeVisitor):
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []

    def _allowed(self) -> bool:
        from pathlib import Path as _P

        name = _P(self.filepath).name
        if name in ALLOWED_BASENAMES:
            return True
        return any(p in self.filepath for p in ALLOWED_PATHS)

    def report(self, node: ast.AST, msg: str) -> None:
        self.violations.append((node.lineno, msg))

    def visit_Import(self, node: ast.Import) -> None:
        if self._allowed():
            return
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in BANNED_MODULES:
                self.report(
                    node,
                    f"Forcing F3: `import {alias.name}` is banned; "
                    "use idp_concurrency.tracer.TracedClient",
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._allowed() or node.module is None:
            return
        top = node.module.split(".")[0]
        if top in BANNED_MODULES:
            self.report(
                node,
                f"Forcing F3: `from {node.module} import ...` is banned; "
                "use idp_concurrency.tracer.TracedClient",
            )


def check_file(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(), filename=str(path))
    visitor = NoUntracedVisitor(str(path))
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
