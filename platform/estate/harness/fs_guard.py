"""
platform/estate/harness/fs_guard.py
Enforces the Read/Patch boundary inside estate-execute before any shell command runs.

Scope: this guards commands estate-execute dispatches on behalf of an agent (the one
execution boundary, AGENTS.md section 7). It does not and cannot reach a human's own
shell, and it is a heuristic text filter -- not a sandbox -- so it is one layer, not the
only layer: bin/estate-read and bin/estate-patch are the real doors (receipt-gated,
AST-checked); this module exists so an agent cannot simply route around them with a raw
shell redirect in the same command string.

WHAT THIS IS APPLIED TO (measured and changed 2026-10-31). The executor applies it to the
agent-supplied content only: the values that reach the shell through a raw <<var>> slot.
An intent's own step text is estate-authored code that reaches the shell through a claim
and a lane, and it was being judged as if an agent had typed it: 103 of the 451 installed
intent steps matched a banned pattern and the estate's canonical doors refused THEMSELVES
-- pr-list (its own redirect to a temp file), agent-invoke (its own payload write) and
lane-submit (its own push log) each failed with "REFUSED: RAW_WRITE_REDIRECT_BANNED". The
boundary's job is to stop an AGENT routing around bin/estate-read / bin/estate-patch, not
to stop the estate from running its own doors. The patterns and this API are unchanged;
where the executor applies them changed (platform/estate/bin/estate-execute,
interpolate_parts).

Found live (not in a unit test) on the first real round trip through estate-execute:
a legitimate `bin/estate-patch` invocation piping a SEARCH/REPLACE payload whose
*replacement text* contained `if used >= limit:` was refused as a RAW_WRITE_REDIRECT, because
the original pattern scanned the whole command string for a bare `>` with no notion of
quoting -- a `>` inside a single-quoted printf payload has no shell effect at all, but the
regex could not tell the difference between that and a real redirect. Any patch touching a
comparison operator or a heredoc-looking string inside its own payload would have hit this.
_strip_quoted removes quoted spans before the redirect/cat/tail patterns run, since a
character that cannot reach the shell is not a redirect this layer needs to refuse.
"""

import re

_SINGLE_QUOTED = re.compile(r"'[^']*'")
_DOUBLE_QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')


def _strip_quoted(cmd: str) -> str:
    """The command with the contents of every quoted span removed, so a shell metacharacter
    that only appears inside quotes (and therefore never reaches the shell as an operator)
    cannot trip a pattern meant to catch one that does."""
    cmd = _SINGLE_QUOTED.sub("''", cmd)
    cmd = _DOUBLE_QUOTED.sub('""', cmd)
    return cmd


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
    scan_target = _strip_quoted(stripped)
    for pattern, reason in FORBIDDEN_PATTERNS:
        if pattern.search(scan_target):
            return False, reason
    return True, "OK"
