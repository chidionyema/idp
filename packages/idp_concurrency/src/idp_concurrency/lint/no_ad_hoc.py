"""Forcing F4 — protocol coordination across agents requires a TLA+ spec.

A `.tla` file must exist alongside any code that crosses an agent boundary
(orchestrator + planner, two replicas, etc.). The spec is checked by
`bin/tlc-check`; the build fails if it counterexamples.

This rule scans a directory tree and verifies that each file containing
cross-agent coordination primitives (`idp_concurrency.task_scope`,
`idp_concurrency.ORSet`, etc.) has a sibling `.tla` file in a `specs/`
directory or next to the source.

This is a directory-level visitor. Run from CI:
    python -m idp_concurrency.lint.no_ad_hoc src/
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Symbols that imply "cross-agent coordination" — every file using them
# needs a sibling .tla.
CROSS_AGENT_SYMBOLS = {
    "ORSet",
    "TracedClient",
    "MerkleLog",
    "WaitFreeQueue",
}

ALLOWED_PATHS = {
    "idp_concurrency/",
    "idp_concurrency/lint/",
    "tests/",
}


def _imports_cross_agent_symbols(path: Path) -> bool:
    """True if `path` imports anything from the cross-agent symbol set."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("idp_concurrency"):
                for alias in node.names:
                    if alias.name in CROSS_AGENT_SYMBOLS:
                        return True
    return False


def _has_sibling_tla(path: Path) -> bool:
    """A specs/<basename>.tla file exists somewhere reachable from `path`."""
    base = path.stem
    for candidate in [
        path.parent / "specs" / f"{base}.tla",
        path.parent.parent / "specs" / f"{base}.tla",
    ]:
        if candidate.exists():
            return True
    return False


def check_tree(root: Path) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for path in root.rglob("*.py"):
        rel = str(path)
        if any(allowed in rel for allowed in ALLOWED_PATHS):
            continue
        if _imports_cross_agent_symbols(path) and not _has_sibling_tla(path):
            violations.append(
                (
                    str(path),
                    "Forcing F4: cross-agent coordination imports found, "
                    "but no specs/<basename>.tla sibling. "
                    "Add a TLA+ spec checked by `bin/tlc-check`.",
                )
            )
    return violations


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m idp_concurrency.lint.no_ad_hoc <root>", file=sys.stderr)
        return 2
    failures = 0
    for arg in argv[1:]:
        for path, msg in check_tree(Path(arg)):
            print(f"{path}: {msg}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
