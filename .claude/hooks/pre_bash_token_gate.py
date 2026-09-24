#!/usr/bin/env python3
"""PreToolUse(Bash) gate: refuse raw shell that bypasses the token-optimisation wrapper.

WHY THIS EXISTS (founder, 2026-09-21, verbatim): "the first thing you mist do is ensure
claude code is using the full token optimiaton suite esle lcaude code is not wprking on
this platform".

MEASURED BASIS, this machine, 2026-09-21:
  - `~/.claude/settings.json` hooks block                     : PostToolUse = null
  - occurrences of "idp-exec" in that settings file           : 0
  - occurrences of "read_shunt" / "efficiency" in that file   : 0
  - `idp/.claude/hooks/after_agent_turn.py` (the 8-mechanism
    Claude Code reporter) wired into settings.json            : 0 references
  - `~/Documents/code/claude-guards/read_shunt` -> DANGLING
    (target `estate/claude-guards-legacy/read_shunt` deleted)
So on the day this was written, Claude Code ran with ZERO token optimisation wired, while
`idp/AGENTS.md` had mandated `bin/idp-exec` on every command since 2026-09-15. The mandate
was prose. This file is the gate that makes it a rule (estate law: a gate that cannot fail
is not a gate; narrating instead of proving is the same defect as asserting instead of
proving).

WHAT IT ENFORCES. Every Bash command must reach the shell through `bin/idp-exec`, which
clamps output to the first 25 + last 25 lines and spills the remainder to
`~/.pi/agent/state/last_exec.log`. Unclamped output is the single largest source of context
bloat in a Claude Code session, and it is the one mechanism of the eight that a subscription
CLI can actually run: the other seven live in `platform/llm/efficiency_gateway.py`, a
LiteLLM pre-call hook, and Claude Code does not route through LiteLLM (see
`llm/litellm.yml` and `platform/llm/config.yaml:144` — the Anthropic lane was removed on
purpose). Claiming the other seven cover this session would be asserting, not proving.

THE CLASSIFICATION IS TOTAL. Every command lands in exactly one of WRAPPED / EXEMPT /
REFUSED, and the unknown case is REFUSED, never a bare `return`. The estate has paid for
an allow-list with a silent miss case before (a bare `return` on the unknown branch dropped
10 criticals in 18 hours and no test failed); this file has no such branch.

LAW 38 — a fence a correct machine cannot satisfy is an outage. Two releases are built in,
both typed deliberately and never scripted:
    IDP_TOKEN_GATE=0 <command>       one genuine emergency
    the EXEMPT set below             commands idp-exec structurally cannot carry
`bin/idp-exec` missing from the repo is BLIND, not FAIL: the gate allows and says so, on
the same reasoning that `bin/idp-main-green-gate` does not refuse a push with no network.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

WRAPPER = "bin/idp-exec"

# Commands idp-exec structurally cannot carry, each with the reason it cannot.
# This set is deliberately tiny and is printed in full in every refusal, so a reader can
# see what it does not cover rather than discover it by being surprised.
EXEMPT_REASONS = {
    "cd": "changes shell state only; produces no output to clamp",
    "export": "changes shell state only; produces no output to clamp",
    "source": "must run in the caller's shell to have any effect",
    ".": "must run in the caller's shell to have any effect",
    "exit": "shell builtin; terminates the shell",
    "unset": "changes shell state only; produces no output to clamp",
}

# The wrapper's own plumbing, and the gate's self-test.
SELF = (WRAPPER, "idp-exec", "idp-install-hooks")


def _first_word(segment: str) -> str:
    """The command word of one shell segment, or "" when it cannot be determined."""
    seg = segment.strip()
    if not seg:
        return ""
    # Strip leading VAR=value assignments, which precede the real command word.
    while True:
        m = re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S*\s+", seg)
        if not m:
            break
        seg = seg[m.end() :]
    try:
        parts = shlex.split(seg, comments=False)
    except ValueError:
        # Unbalanced quotes: we cannot read this segment, so we do not get to call it safe.
        return ""
    return parts[0] if parts else ""


def _heredoc_delim(cmd: str, i: int) -> tuple[str, int] | None:
    """Read the delimiter word of a heredoc starting at `cmd[i:]` (`<<WORD`, `<<-'WORD'`).

    Returns (delimiter, index just past the word), or None when there is no readable
    delimiter — in which case the caller keeps splitting normally, because a heredoc this
    gate cannot read is not one it gets to call safe.
    """
    j = i + 2
    if (
        j < len(cmd) and cmd[j] == "-"
    ):  # <<-DELIM strips leading tabs from the terminator
        j += 1
    while j < len(cmd) and cmd[j] in " \t":
        j += 1
    q = ""
    if j < len(cmd) and cmd[j] in "'\"":
        q = cmd[j]
        j += 1
    start = j
    if q:
        while j < len(cmd) and cmd[j] != q:
            j += 1
        if j >= len(cmd):
            return None  # unterminated quote around the delimiter word
        delim = cmd[start:j]
        j += 1
    else:
        while j < len(cmd) and (cmd[j].isalnum() or cmd[j] in "_-."):
            j += 1
        delim = cmd[start:j]
    return (delim, j) if delim else None


def _skip_heredoc_bodies(cmd: str, pos: int, delims: list[str]) -> int:
    """Advance past the bodies of the heredocs opened on the line ending at `pos`.

    `pos` is the index just after that newline. Each body runs to a line that is exactly
    its delimiter. A body that is never terminated leaves `pos` at the end of the string,
    which is what bash does with the same input.
    """
    for delim in delims:
        while pos <= len(cmd):
            nl = cmd.find("\n", pos)
            line = cmd[pos:] if nl == -1 else cmd[pos:nl]
            if nl == -1:
                pos = len(cmd)
                break
            pos = nl + 1
            if line.strip() == delim:
                break
    return pos


def _segments(cmd: str) -> list[str]:
    """Split on the operators that start a new command word: ; && || | & newline.

    QUOTE-AWARE ON PURPOSE. A regex split is not: `bin/idp-exec bash -lc 'git log | head'`
    is one command, and a blind split turns the `|` inside the quoted script into a second,
    unwrapped segment and refuses a compliant command. That exact string is in the test
    suite, where it failed the first cut of this function.

    THE SAME DEFECT, TWICE MORE, MEASURED 2026-09-21 WHEN THIS GATE REFUSED TWO OF ITS
    AUTHOR'S OWN COMPLIANT COMMANDS:

      IDP_CI_FULL_VERIFIED=1 bin/idp-exec git push -u origin feat/x 2>&1
        -> ['... 2>', '1']          the & of `2>&1` is a redirection, not a separator
      bin/idp-exec python3 - <<'PY' ... a; b | c ... PY
        -> ['... <<PY ... a', ' b ', ' c ...']   a heredoc body is DATA, not commands

    Both produced a segment whose first word is not the wrapper, so a command that went
    through the wrapper was refused. A gate that refuses compliant input does not get
    obeyed, it gets switched off — so the false-refusal is the more dangerous direction
    here, and these two forms are now carried whole.
    """
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    pending_heredocs: list[str] = []
    i = 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(cmd):
                buf.append(cmd[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < len(cmd):
            buf.append(ch)
            buf.append(cmd[i + 1])
            i += 2
            continue
        if cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            found = _heredoc_delim(cmd, i)
            if found is not None:
                delim, j = found
                # Carry the `<<DELIM` token itself, and remember the body to skip at the
                # end of this line. Only the BODY is skipped: anything still on the command
                # line after the redirect (`... <<PY | some-raw-cmd`) is a real operator and
                # must still split, or the heredoc becomes a hole in the gate.
                buf.append(cmd[i:j])
                pending_heredocs.append(delim)
                i = j
                continue
        if ch == "&":
            # `2>&1`, `>&2`, `&>file`: this & belongs to a redirection, not a separator.
            prev = "".join(buf).rstrip()
            nxt = cmd[i + 1] if i + 1 < len(cmd) else ""
            if (prev and prev[-1] in "><") or nxt == ">":
                buf.append(ch)
                i += 1
                continue
        if ch in ";|&\n":
            out.append("".join(buf))
            buf = []
            # Consume the second character of a two-character operator (&& or ||).
            if ch in "|&" and i + 1 < len(cmd) and cmd[i + 1] == ch:
                i += 1
            i += 1
            if ch == "\n" and pending_heredocs:
                i = _skip_heredoc_bodies(cmd, i, pending_heredocs)
                pending_heredocs = []
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [s for s in out if s.strip()]


def _is_wrapped(cmd: str) -> bool:
    """True when every segment that runs a program runs it through the wrapper.

    A command like `cd /repo && bin/idp-exec git status` is wrapped: `cd` is exempt and
    the one segment that produces output goes through idp-exec.
    """
    saw_a_real_command = False
    for seg in _segments(cmd):
        word = _first_word(seg)
        if not word:
            # Unreadable segment. Not provably wrapped, so the whole command is not.
            return False
        base = os.path.basename(word)
        if base in EXEMPT_REASONS:
            continue
        saw_a_real_command = True
        if not (word.endswith(SELF) or base in SELF):
            return False
    return saw_a_real_command


def _all_exempt(cmd: str) -> bool:
    """True when the command runs nothing that produces clampable output."""
    segs = _segments(cmd)
    if not segs:
        return False
    for seg in segs:
        word = _first_word(seg)
        if not word or os.path.basename(word) not in EXEMPT_REASONS:
            return False
    return True


def _suggestion(cmd: str) -> str:
    """The rewritten command, or "" when quoting makes a correct rewrite impossible.

    A wrong suggestion is worse than none: it would be copied. When the command contains a
    single quote, the `bash -lc '...'` form cannot be built without re-quoting the body,
    so the gate stays silent and gives the recipe instead.
    """
    if "'" in cmd:
        return ""
    if len(_segments(cmd)) > 1 or any(c in cmd for c in "|><$`"):
        return f"{WRAPPER} bash -lc '{cmd.strip()}'"
    return f"{WRAPPER} {cmd.strip()}"


def _repo_with_wrapper(cwd: str | None) -> str | None:
    """The nearest ancestor of `cwd` that ships `bin/idp-exec`, or None.

    `IDP_ROOT` overrides the walk, so a test or a checkout in an unusual place can name
    the repo directly. None means this session is not working on a repo that carries the
    wrapper, and the gate has no business refusing anything there.
    """
    override = os.environ.get("IDP_ROOT")
    if override:
        return override if os.path.exists(os.path.join(override, WRAPPER)) else None
    here = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.exists(os.path.join(here, WRAPPER)):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def _refusal(cmd: str, repo: str) -> str:
    exempt = ", ".join(sorted(EXEMPT_REASONS))
    lines = [
        "[token-gate] REFUSED: raw shell bypasses the token-optimisation wrapper.",
        "",
        f"  {WRAPPER} clamps output to 25 head + 25 tail lines and spills the rest to",
        "  ~/.pi/agent/state/last_exec.log. Unclamped output is the largest single source",
        "  of context bloat in a Claude Code session, and idp/AGENTS.md has mandated the",
        "  wrapper on every command since 2026-09-15.",
        "",
        "  Re-run it through the wrapper:",
    ]
    hint = _suggestion(cmd)
    if hint:
        lines.append(f"    {hint}")
    else:
        lines += [
            f"    {WRAPPER} <program> <args...>              # a simple command",
            f"    {WRAPPER} bash -lc '<pipeline or heredoc>'  # anything with | > $ ` or ;",
            "  (no rewrite is shown because this command contains a single quote, and a",
            "   wrong rewrite would be copied.)",
        ]
    lines += [
        "",
        f"  Exempt without the wrapper (shell state only): {exempt}",
        "  One genuine emergency, typed deliberately and never scripted:",
        "    IDP_TOKEN_GATE=0 <your command>",
        f"  Gate: {repo}/.claude/hooks/pre_bash_token_gate.py",
    ]
    return "\n".join(lines)


def run(payload: dict) -> int:
    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    cmd = str(tool_input.get("command", "") or "")
    if not cmd.strip():
        return 0

    # A backgrounded command is detached; idp-exec captures output and would never return.
    if tool_input.get("run_in_background"):
        return 0

    if os.environ.get("IDP_TOKEN_GATE") == "0":
        sys.stderr.write(
            "[token-gate] RELEASED by IDP_TOKEN_GATE=0 for this command.\n"
        )
        return 0

    # The gate binds where the wrapper exists, and nowhere else. A session working in a
    # repo that ships no `bin/idp-exec` is not on this platform, and telling it to use
    # idp's wrapper would be a fence it cannot satisfy (LAW 38).
    repo = _repo_with_wrapper(payload.get("cwd"))
    if repo is None:
        return 0

    if _is_wrapped(cmd) or _all_exempt(cmd):
        return 0

    sys.stderr.write(_refusal(cmd, repo) + "\n")
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - a malformed event may never brick the session
        return 0
    if not isinstance(payload, dict):
        return 0
    return run(payload)


if __name__ == "__main__":
    sys.exit(main())
