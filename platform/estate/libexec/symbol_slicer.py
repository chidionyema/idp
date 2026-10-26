#!/usr/bin/env python3
"""symbol_slicer.py — Micro-Token FR-1: send the touched symbols, never raw files.

The review pipeline's Tier 2 used to paste `diff[:4000]` into the LLM prompt: a raw byte
cap that cuts mid-function and carries none of the enclosing symbol. This module replaces
that with syntax-aware slices: for every file the diff touches, the current source of the
touched function or class, plus the file's remaining top-level signatures as callee
context, packed into dense tagged text under a byte budget.

Syntax-aware without dependencies: Python by indent (exact block bounds), brace languages
by brace matching. When `tree_sitter` and `tree_sitter_python` are importable they are
used for precise Python spans instead; the module never requires them, so CI needs no new
wheel and the fallback path is always exercised by tests.

Append-stability note (efficiency_gateway law): a slice decision must depend only on the
bytes it is given, never on call history — this module is a pure function of (diff, files),
so it composes with the cache-safe chain.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable

MAX_DEFAULT_BYTES = 4000

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@ ?(.*)$", re.MULTILINE)
_FILE_RE = re.compile(r"^\+\+\+ b/(.+?)\s*$", re.MULTILINE)
_PY_DEF_RE = re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)|^(\s*)class\s+(\w+)")
_CALLABLE_HINT_RE = re.compile(r"([A-Za-z_]\w*)")
_STOPWORDS = {
    "def",
    "class",
    "func",
    "fn",
    "const",
    "async",
    "import",
    "from",
    "return",
    "self",
    "None",
    "True",
    "False",
    "if",
    "else",
    "elif",
    "for",
    "while",
    "try",
}


# --------------------------------------------------------------------------- diff parsing


def touched(diff_text: str) -> list[dict]:
    """Files a unified diff touches, with the symbol hints each hunk carries.

    A hunk's trailing context line usually names the enclosing def/class for Python;
    that hint plus the added/removed lines' identifiers are what the extractor aims at.
    """
    files: list[dict] = []
    current: dict | None = None
    for line in diff_text.splitlines():
        m = _FILE_RE.match(line)
        if m:
            current = {"path": m.group(1), "hunks": [], "identifiers": set()}
            files.append(current)
            continue
        if current is None:
            continue
        h = _HUNK_RE.match(line)
        if h:
            current["hunks"].append(
                {"new_start": int(h.group(1)), "hint": (h.group(3) or "").strip()}
            )
            if h.group(3):
                for ident in _CALLABLE_HINT_RE.findall(h.group(3)):
                    if ident not in _STOPWORDS:
                        current["identifiers"].add(ident)
            continue
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            for ident in _CALLABLE_HINT_RE.findall(line):
                current["identifiers"].add(ident)
    return [f for f in files if f["hunks"] or f["identifiers"]]


# --------------------------------------------------------------------------- extraction


def _py_block_bounds(src: str, start_line: int) -> tuple[int, int]:
    """Exact [start, end) line span of the indented block opening at start_line (0-based)."""
    lines = src.splitlines()
    open_line = lines[start_line]
    indent = len(open_line) - len(open_line.lstrip())
    end = start_line + 1
    while end < len(lines):
        cur = lines[end]
        if cur.strip() and (len(cur) - len(cur.lstrip())) <= indent:
            break
        end += 1
    while end > start_line + 1 and not lines[end - 1].strip():
        end -= 1
    return start_line, end


def _py_find(src: str, name: str) -> tuple[int, int] | None:
    for i, line in enumerate(src.splitlines()):
        m = _PY_DEF_RE.match(line)
        if m and name in (m.group(2), m.group(4)):
            s, e = _py_block_bounds(src, i)
            return s, e
    return None


def _brace_block_bounds(src: str, start_line: int) -> tuple[int, int]:
    """Line span of the brace block that opens at or after start_line."""
    lines = src.splitlines()
    depth = 0
    opened = False
    end = start_line
    for i in range(start_line, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
        end = i + 1
        if opened and depth <= 0:
            break
    return start_line, min(end, len(lines))


_BRACED_DEF = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*="
    r"|class\s+(\w+)|(?:public|private|protected|func|fn)\s+(\w+))"
)


def _braced_find(src: str, name: str) -> tuple[int, int] | None:
    for i, line in enumerate(src.splitlines()):
        m = _BRACED_DEF.match(line)
        if m and name in (m.group(1), m.group(2), m.group(3), m.group(4)):
            s, e = _brace_block_bounds(src, i)
            return s, e
    return None


def _ts_python_span(src: str, name: str) -> tuple[int, int] | None:
    """tree-sitter span when the wheels are importable; None otherwise (never raises)."""
    try:
        import tree_sitter_python  # type: ignore
        from tree_sitter import Language, Parser  # type: ignore
    except Exception:
        return None
    try:
        parser = Parser(Language(tree_sitter_python.language()))
        tree = parser.parse(src.encode())
        found: list[tuple[int, int]] = []

        def visit(node) -> None:  # noqa: ANN001 - a tree_sitter Node
            if node.type in ("function_definition", "class_definition"):
                ident = node.child_by_field_name("name")
                if ident is not None and src[ident.start_byte : ident.end_byte] == name:
                    start_line = src[: node.start_byte].count("\n") + 1
                    end_line = src[: node.end_byte].count("\n") + 1
                    found.append((start_line, end_line))
                return
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        if not found:
            return None
        s, e = found[0]
        return s - 1, e
    except Exception:
        return None


def lang_of(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "javascript",
        ".tsx": "javascript",
        ".go": "braced",
        ".rs": "braced",
        ".java": "braced",
        ".c": "braced",
        ".h": "braced",
        ".cpp": "braced",
    }.get(ext, "unknown")


def extract_symbol(src: str, lang: str, name: str) -> str | None:
    """The current source of callable/class `name`, or None when absent."""
    span = None
    if lang == "python":
        span = _ts_python_span(src, name) or _py_find(src, name)
    elif lang in ("javascript", "braced"):
        span = _braced_find(src, name)
    if not span:
        return None
    s, e = span
    return "\n".join(src.splitlines()[s:e])


def top_signatures(src: str, lang: str, limit: int = 12) -> list[str]:
    """One signature line per top-level callable/class — the callee context."""
    out: list[str] = []
    for line in src.splitlines():
        if (
            lang == "python"
            and _PY_DEF_RE.match(line)
            and (len(line) - len(line.lstrip())) == 0
        ):
            out.append(line.rstrip())
        elif lang in ("javascript", "braced") and _BRACED_DEF.match(line):
            stripped = line.strip()
            if stripped.startswith(
                (
                    "export",
                    "function",
                    "class",
                    "const",
                    "func",
                    "fn",
                    "public",
                    "private",
                )
            ):
                out.append(stripped)
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- assembly


def slice_for_diff(
    diff_text: str,
    read_file: Callable[[str], str | None],
    max_bytes: int = MAX_DEFAULT_BYTES,
) -> str:
    """Dense tagged context for everything a diff touches, under `max_bytes`.

    Per touched file: the touched symbol's current body, then the file's other
    top-level signatures. Files that no longer resolve are skipped; the caller
    falls back to the raw diff when the result is empty.
    """
    parts: list[str] = []
    used = 0
    for f in touched(diff_text):
        lang = lang_of(f["path"])
        src = read_file(f["path"])
        if src is None:
            continue
        file_parts: list[str] = []
        hints = [h["hint"] for h in f["hunks"] if h["hint"]] + sorted(f["identifiers"])
        seen: set[str] = set()
        sliced_any = False
        for hint in hints:
            for ident in re.findall(r"[A-Za-z_]\w{2,}", hint):
                if ident in seen or ident in _STOPWORDS:
                    continue
                seen.add(ident)
                body = extract_symbol(src, lang, ident)
                if body and len(body) < max_bytes:
                    file_parts.append(f'<symbol name="{ident}">\n{body}\n</symbol>')
                    sliced_any = True
                    break
        sigs = top_signatures(src, lang)
        sig_block = "\n".join(sigs)
        if sliced_any or sig_block:
            inner = "\n".join(file_parts)
            sig_tag = f"<signatures>\n{sig_block}\n</signatures>" if sig_block else ""
            piece = (
                f'<file path="{f["path"]}" lang="{lang}">\n{inner}\n{sig_tag}\n</file>'
            )
            if used + len(piece) > max_bytes and parts:
                break
            parts.append(piece)
            used += len(piece) + 1
    return "\n".join(parts)


def content_hash(text: str) -> str:
    """Stable key for a slice decision (the gateway's once-per-hash rule)."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]
