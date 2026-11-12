"""Refuse the git hook bypass, deterministically, at the door.

Founder, 2026-11-12: "no agenbt can do that ever again i nee string mathyematic al
gyabatees and i need to knwohow you plan to prove it".

THE HOLE THIS CLOSES
--------------------
`.githooks/pre-commit` in idp is healthy: it runs `ruff format` on staged Python and
APPLIES the fix, not just checks it. Measured 2026-11-12, a file containing
`x = {1,3,2}` was staged and committed, and the hook rewrote it to `x = {1, 2, 3}`
before the commit landed. The gate was never broken.

What was broken is that an agent can skip it. `git commit --no-verify` and
`git -c core.hooksPath=/dev/null commit` both bypass `.githooks/pre-commit` entirely.
An agent (this one) did exactly that on a stale belief that ruff was not installed;
ruff 0.15.18 was installed. The Gemini inbound bridge then reached CI unformatted and
fast-gate failed three jobs. That is AGENTS.md R3 -- "deterministic checks run late
(CI) instead of at write time" -- and R10, agents dragging a pipeline through manual
re-runs because the local door was skipped.

THE ALGEBRA
-----------
This module reads a command string and decides one boolean. No judgement, no model,
no network. The same input always gives the same answer, and anyone can re-derive it.

    TOKEN        := shlex.split(command)                  # argv, quotes honoured
    SEGMENT      := TOKEN split on shell separators (&& || ; | & \\n)
    HEAD         := first token of a segment whose basename is git/gh, looking past
                    any leading VAR=value env assignment

    COMMIT_FAMILY := {commit, merge, cherry-pick, revert, am, rebase, tag, push}
                     # `push` because a bypassed commit that is then pushed is the
                     # same defect one step later.

    HOOK_HOK   := "--no-verify" in argv[HEAD+1:]
                  | "-n" in argv[HEAD+1:] only when the verb is `commit`, the one
                    verb where git spells --no-verify as -n.
                    `cherry-pick`/`revert` spell -n as --no-commit, so they are
                    NOT a bypass; on `push`, -n is --dry-run.
                  # --no-gpg-sign is NOT a bypass: signing is not verification.

    PATH_HOK   := an argv token equal to core.hooksPath / core.hookspath
                  | a token matching core\\.hooksPath\\s*=\\s*\\S      (the = form)
                  | a token matching -c\\s*core\\.hooksPath            (the joined form)
                  # covers ["-c", "core.hooksPath=/dev/null"] and "-ccore.hooksPath=/x"

    ENV_HOK    := a leading VAR=value whose VAR is GIT_CONFIG_GLOBAL or GIT_CONFIG_SYSTEM
                  assigned to /dev/null
                  # the observed bypass: it hides the global hooksPath, so hooks stop

    REFUSE <=> exists a SEGMENT with a git HEAD
               AND a COMMIT_FAMILY verb in that segment
               AND (HOOK_HOK OR PATH_HOK OR ENV_HOK in that segment)

Accepting is the default and must stay cheap: a gate that refuses correct work is an
outage (AGENTS.md section 12). `git commit -m "fix the --no-verify note"` must PASS --
there the dangerous string sits inside a message value, not in an argv token.

WHAT THIS DOES NOT COVER, NAMED RATHER THAN HIDDEN
-------------------------------------------------
A human typing the bypass into their own terminal. This module sits in the executor,
which every agent on this machine goes through (AGENTS.md section 7). It cannot
mediate a shell it never sees. That residue is closed by the second layer: CI refuses
a commit that carries no hook-written trailer.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterable

GIT_HEADS = {"git", "git.exe"}

# Verbs after which a commit is produced or shipped, so pre-commit hooks are due.
COMMIT_FAMILY = {
    "commit",
    "merge",
    "cherry-pick",
    "revert",
    "am",
    "rebase",
    "tag",
    "push",
}

# `-n` is a bypass ONLY on the verbs where git itself spells --no-verify that way.
# Measured 2026-11-12 from `git <verb> -h`:
#   commit       -n, --no-verify
#   cherry-pick  -n, --no-commit
#   revert       -n, --no-commit
#   merge        (no -n short form documented)
#   am           (no -n short form documented)
# So `-n` is a bypass on `commit` alone. Treating it as one elsewhere refused
# `git cherry-pick -n`, which keeps the hooks and is the ordinary way to stage a
# pick -- a false refusal on correct work is an outage (AGENTS.md section 12), and
# it bit this very session while landing this file.
NO_VERIFY_SHORT = {"commit"}

HOOK_HOKS = {"--no-verify"}
HOOK_PATH_NAMES = {"core.hookspath"}  # compared lowercased
HOOK_PATH_INLINE = re.compile(r"core\.hooksPath\s*=\s*\S", re.IGNORECASE)
HOOK_PATH_JOINED = re.compile(r"(?:^|\s)-c\s*core\.hooksPath", re.IGNORECASE)
ENV_HOKS = {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"}

SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}

# Flags that consume the NEXT token, so it is a value and neither a verb nor a hook token.
VALUE_FLAGS = {
    "-m",
    "--message",
    "-F",
    "--file",
    "-C",
    "--reuse-message",
    "--author",
    "--date",
    "-t",
    "--template",
    "-S",
    "--gpg-sign",
}


def _segments(tokens: list[str]) -> list[list[str]]:
    """Split argv on shell separators so `cd x && git commit --no-verify` is caught."""
    out: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in SEPARATORS:
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    if current:
        out.append(current)
    return out


def _head_index(segment: list[str]) -> int | None:
    """Index of the git invocation, looking past a leading VAR=value env assignment."""
    for index, token in enumerate(segment):
        base = token.rsplit("/", 1)[-1]
        if base in GIT_HEADS:
            return index
        if index == 0 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
            continue
    return None


def _env_hok(segment: list[str], head: int) -> bool:
    """`GIT_CONFIG_GLOBAL=/dev/null git commit` hides the repo's hooks path."""
    for token in segment[: head + 1]:
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", token)
        if (
            match
            and match.group(1) in ENV_HOKS
            and match.group(2).strip() in {"/dev/null", ""}
        ):
            return True
    return False


def _verbs_and_hooks(segment: list[str], head: int) -> tuple[set[str], bool, bool]:
    """Return (verbs seen, hook-hok seen, hookspath-hok seen) for one segment."""
    verbs: set[str] = set()
    hook_hok = False
    path_hok = False
    skip_next = False
    for token in segment[head + 1 :]:
        if skip_next:
            skip_next = False
            continue
        if token in VALUE_FLAGS:
            skip_next = True
            continue
        if token in HOOK_HOKS:
            hook_hok = True
            continue
        # Short-option cluster: git accepts `-nm "msg"` as `--no-verify -m "msg"`, so a
        # single-dash token whose cluster contains `n` is the same bypass spelled shorter.
        # Checked against HOOK_HOK_VERBS so `cherry-pick -n` (--no-commit) is not swept in.
        if (
            token.startswith("-")
            and not token.startswith("--")
            and len(token) > 2
            and "n" in token[1:].split("=")[0]
            and (verbs & NO_VERIFY_SHORT)
        ):
            hook_hok = True
            continue
        if token.startswith("-c") and len(token) > 2:
            if token[2:].lower().split("=")[0] in HOOK_PATH_NAMES:
                path_hok = True
            continue
        # A bare "-c" carries no value of its own; the next token is its argument and is
        # handled by the HOOK_PATH_NAMES test below. Not a credential: S105 is a false
        # positive on a flag name.
        if token == "-c":  # noqa: S105
            continue
        lowered = token.lower()
        if lowered.split("=")[0] in HOOK_PATH_NAMES:
            path_hok = True
            continue
        if HOOK_PATH_INLINE.search(token) or HOOK_PATH_JOINED.search(token):
            path_hok = True
            continue
        if not token.startswith("-"):
            verbs.add(lowered)
    return verbs, hook_hok, path_hok


def bypass_reason(command: str) -> str | None:
    """Return why `command` is a hook bypass, or None when it is not.

    Pure: no filesystem, no subprocess, no clock, no randomness.
    """
    if not command or not command.strip():
        return None
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        # An unbalanced quote cannot be classified. The shell itself will reject it,
        # so treating it as a bypass would refuse work that never runs anyway.
        return None

    for segment in _segments(tokens):
        head = _head_index(segment)
        if head is None:
            continue
        verbs, hook_hok, path_hok = _verbs_and_hooks(segment, head)
        if not (verbs & COMMIT_FAMILY):
            continue
        if _env_hok(segment, head):
            return (
                "GIT_CONFIG_GLOBAL=/dev/null hides the repo's hooks path, so pre-commit "
                "never runs (AGENTS.md section 9 R3)"
            )
        if path_hok:
            return (
                "core.hooksPath is being redirected away from .githooks, so pre-commit "
                "never runs (AGENTS.md section 9 R3)"
            )
        if hook_hok:
            return (
                "--no-verify skips .githooks/pre-commit, the write-time ruff format/lint "
                "gate; CI then fails later (AGENTS.md section 9 R3)"
            )
        if "-n" in segment[head + 1 :] and (verbs & NO_VERIFY_SHORT):
            return (
                "-n is --no-verify here and skips .githooks/pre-commit "
                "(AGENTS.md section 9 R3)"
            )
    return None


def is_bypass(command: str) -> bool:
    """True when this command would skip the repo's hooks."""
    return bypass_reason(command) is not None


def classify(lines: Iterable[str]) -> tuple[int, list[str]]:
    """Score a labelled corpus of `REFUSE <cmd>` / `PASS <cmd>` lines.

    Returns (misclassified_count, detail_lines). Zero is the only passing score.
    """
    misclassified = 0
    detail: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expect, _, command = line.partition(" ")
        command = command.strip()
        want = expect.upper() == "REFUSE"
        got = is_bypass(command)
        if got != want:
            misclassified += 1
            verdict = "REFUSE" if got else "PASS"
            detail.append(f"MISCLASSIFIED want={expect} got={verdict} :: {command}")
    return misclassified, detail
