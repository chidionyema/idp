"""
platform/estate/harness/fs_guard.py
Enforces the Read/Patch boundary inside estate-execute before any shell command runs.

Scope: this guards commands estate-execute dispatches on behalf of an agent (the one
execution boundary, AGENTS.md section 7). It does not and cannot reach a human's own
shell, and it is a heuristic text filter -- not a sandbox -- so it is one layer, not the
only layer: bin/estate-read and bin/estate-patch are the real doors (receipt-gated,
AST-checked); this module exists so an agent cannot simply route around them with a raw
shell redirect in the same command string.
"""

import re

FORBIDDEN_PATTERNS = [
    (
        re.compile(r"(?:^|[;&|]\s*)(?:cat|head|tail|less|more)\s+([^\s|;&>]+)"),
        "RAW_READ_BANNED: Direct file reads via cat/head/tail are banned. Use `bin/estate-read <path> --lines START:END`.",
    ),
    (
        re.compile(r"(?:^|\s)(?:sed\s+-i|perl\s+-pi|awk\s+-i\s+inplace)\b"),
        "INPLACE_STREAM_EDIT_BANNED: Use `bin/estate-patch <path> --receipt <READ_RECEIPT>`.",
    ),
    (
        re.compile(
            r"(?:>>?|<<\s*['\"]?\w+['\"]?|\btee\b)\s*(?!\s*/dev/null\b)([^\s;&|]+)"
        ),
        "RAW_WRITE_REDIRECT_BANNED: Shell file overwrites and appends (> / >> / << / tee) are banned. Use `bin/estate-patch`.",
    ),
    (
        re.compile(r"\b(?:AGENTS\.md|docs/NEXT\.md|docs/FOUNDER\.md)\b"),
        "STALE_MARKDOWN_ACCESS_BANNED: Direct access to static markdown rule/plan files is blocked. Query the timestamped memory ledger.",
    ),
]

ALLOWED_PREFIXES = (
    "bin/estate-read",
    "bin/estate-patch",
    "git status",
    "git diff",
    "git log",
    "git commit",
    "git push",
    "bin/idp-ci",
    "pytest",
)


def check_command_allowed(cmd: str) -> tuple[bool, str]:
    """Returns (allowed, reason). `reason` is "OK" when allowed, otherwise the exact
    FORBIDDEN_PATTERNS message naming the door to use instead."""
    stripped = cmd.strip()
    if any(stripped.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return True, "OK"
    for pattern, reason in FORBIDDEN_PATTERNS:
        if pattern.search(stripped):
            return False, reason
    return True, "OK"
