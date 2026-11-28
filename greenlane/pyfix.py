"""Deterministic repairs for the ruff rules ruff itself cannot fix (the estate Python standard).

The estate standard is `ruff check --select E9,F,B,S` plus `ruff format` (bin/idp-python-strict).
Ruff fixes F401 and formatting on its own. It does not fix S101 (`assert` outside tests) or B007
(unused loop variable), so every agent that wrote an `assert` paid a red lane and a loop. These two
repairs are mechanical, so the machine makes them, in the same pre-CI pass that already formats.

Pure functions over source text. Nothing here executes the candidate. A repair that cannot be made
safely is skipped, never guessed: the lane then fails exactly as before and no worse.
"""

from __future__ import annotations

import ast
from pathlib import PurePosixPath

# Same per-file allowance the estate gate applies (bin/idp-python-strict PER_FILE): S101 is how
# pytest asserts, and a file that declares the allowance itself has said so on purpose.
_NOQA_MARK = "ruff: noqa: S101"


def _assert_allowed(path: str, text: str) -> bool:
    p = PurePosixPath(path)
    name = p.name
    return (
        p.parts[:1] == ("tests",)
        or name.startswith("test_")
        or name.endswith("_test.py")
        or _NOQA_MARK in text
    )


def asserts_to_raises(text: str, path: str = "") -> str:
    """`assert c, m` becomes `if not (c): raise AssertionError(m)`: same check, survives python -O.

    Only a statement that owns its whole line(s) is rewritten. `if x: assert y` and `assert a; b`
    are left alone, because replacing them in place would change the program's shape.
    """
    if _assert_allowed(path, text):
        return text
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    lines = text.splitlines(keepends=True)
    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert) or node.end_lineno is None:
            continue
        first = lines[node.lineno - 1]
        last = lines[node.end_lineno - 1]
        indent = first[: node.col_offset]
        if indent.strip() or not first[node.col_offset :].startswith("assert"):
            continue  # shares its line with another statement or a compound header
        tail = last.encode()[node.end_col_offset or 0 :].decode().strip()
        if tail and not tail.startswith("#"):
            continue  # `assert a; other()`
        test = ast.get_source_segment(text, node.test)
        if test is None:
            continue
        raised = "AssertionError"
        if node.msg is not None:
            msg = ast.get_source_segment(text, node.msg)
            if msg is None:
                continue
            raised = f"AssertionError({msg})"
        comment = f"  {tail}" if tail else ""
        edits.append(
            (
                node.lineno,
                node.end_lineno,
                f"{indent}if not ({test}):{comment}\n{indent}    raise {raised}\n",
            )
        )
    for start, end, new in sorted(edits, reverse=True):
        lines[start - 1 : end] = [new]
    out = "".join(lines)
    return out if _parses(out) else text


def _scope_of(tree: ast.AST, loop: ast.AST) -> ast.AST:
    """The innermost function (or the module) that contains `loop`."""
    best: ast.AST = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if any(child is loop for child in ast.walk(node)):
                best = node
    return best


def _read_after_loop(scope: ast.AST, loop: ast.For | ast.AsyncFor, name: str) -> bool:
    """True when `name` is read after the loop and before anything rebinds it in that scope."""
    end = loop.end_lineno or loop.lineno
    rebind = min(
        (
            n.lineno
            for n in ast.walk(scope)
            if isinstance(n, ast.Name)
            and n.id == name
            and isinstance(n.ctx, ast.Store)
            and n.lineno > end
        ),
        default=None,
    )
    return any(
        isinstance(n, ast.Name)
        and n.id == name
        and isinstance(n.ctx, ast.Load)
        and n.lineno > end
        and (rebind is None or n.lineno <= rebind)
        for n in ast.walk(scope)
    )


def unused_loop_vars(text: str) -> str:
    """Rename a `for NAME in ...` target the loop never reads to `_NAME` (B007).

    Skipped when the name is read anywhere in the loop (body or else), or read after the loop
    before something rebinds it: Python keeps the loop variable alive after the loop, and a rename
    would break that read.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    lines = text.splitlines(keepends=True)
    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        target = node.target
        if not isinstance(target, ast.Name) or target.id.startswith("_"):
            continue
        name = target.id
        inside = [*node.body, *node.orelse]
        if any(
            isinstance(n, ast.Name) and n.id == name
            for stmt in inside
            for n in ast.walk(stmt)
        ):
            continue
        if _read_after_loop(_scope_of(tree, node), node, name):
            continue
        edits.append((target.lineno, target.col_offset, name))
    for lineno, col, name in sorted(edits, reverse=True):
        line = lines[lineno - 1]
        head = line.encode()[:col].decode()
        rest = line.encode()[col:].decode()
        if rest.startswith(name):
            lines[lineno - 1] = head + "_" + rest
    out = "".join(lines)
    return out if _parses(out) else text


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
    except SyntaxError:
        return False
    return True


def repair(text: str, path: str = "") -> str:
    """Every deterministic repair, in order. Idempotent: a second pass changes nothing."""
    return unused_loop_vars(asserts_to_raises(text, path))
