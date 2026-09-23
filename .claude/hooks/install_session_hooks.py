#!/usr/bin/env python3
"""Wire this repo's Claude Code session hooks into the user's settings.json.

WHY (founder, 2026-09-21, verbatim): "the first thing you mist do is ensure claude code
is using the full token optimiaton suite esle lcaude code is not wprking on this
platform". "Ensure" cannot mean an edit somebody once made by hand on one laptop — that
is the human-at-a-laptop assumption R4 rules out. A fresh clone or a fresh machine has to
arrive at the same enforcement without anybody remembering to do it, so this runs from
`bin/idp-install-hooks` alongside the git-hook wiring.

It wires exactly two hooks, both of which live in this repo:

  PreToolUse / matcher "Bash" -> pre_bash_token_gate.py   refuses raw shell (exit 2)
  Stop       / matcher ""     -> after_agent_turn.py      reports what the turn spent

MERGE, NEVER REPLACE. `~/.claude/settings.json` is the user's own configuration and on
this machine already carries ~20 estate guards across five events. This script appends to
the matching `hooks[]` array and touches nothing else; a settings file it cannot parse is
left exactly as it is, because a clobbered settings.json silently disables every guard in
it. Idempotent: a second run from the same clone reports `ok` and writes nothing.

ONE ENTRY PER HOOK, NOT ONE PER CLONE. This estate has many checkouts of idp, and the
rule-guard sends every task into a throwaway worktree under ~/Documents/code/wt-*. If the
installer appended a fresh entry per clone, running it from a worktree would leave a hook
command pointing into that worktree, and `git worktree remove` would then make every Bash
call in every session fail on a missing file. So an existing entry for the same hook
filename is REPOINTED at this clone rather than duplicated: at most one entry per hook
survives, and it always names a path that exists.

A LINKED WORKTREE NEVER OWNS THE WIRING. The repoint above is the right answer between
two ordinary clones, and the wrong one for a wt-* worktree that exists for an afternoon:
it would drag the live hooks into a directory about to be deleted. A linked worktree
(its `.git` is a file, not a directory) therefore reports what it would have done and
changes nothing. The main checkout keeps the wiring.
"""

from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (event, matcher, hook path relative to the repo root, timeout seconds)
WANTED = [
    ("PreToolUse", "Bash", ".claude/hooks/pre_bash_token_gate.py", 10),
    ("Stop", "", ".claude/hooks/after_agent_turn.py", 15),
]


def is_linked_worktree(repo: str) -> bool:
    """True when `repo` is a `git worktree add` tree rather than a clone.

    Git writes a `.git` FILE holding a gitdir: pointer in a linked worktree, and a `.git`
    DIRECTORY in a normal clone. No subprocess needed, and it stays correct when git is
    not on PATH.
    """
    return os.path.isfile(os.path.join(repo, ".git"))


def settings_path() -> str:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(config_dir, "settings.json")


def _group(event_groups: list, matcher: str) -> dict:
    """The group for this matcher, created at the end of the list when absent."""
    for group in event_groups:
        if isinstance(group, dict) and group.get("matcher") == matcher:
            return group
    group = {"matcher": matcher, "hooks": []}
    event_groups.append(group)
    return group


def wire(settings: dict) -> list[str]:
    """Merge the wanted hooks into `settings`. Returns one report line per hook."""
    report = []
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings.json has a 'hooks' key that is not an object")
    for event, matcher, rel, timeout in WANTED:
        command = f"python3 {os.path.join(REPO, rel)}"
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"settings.json hooks.{event} is not a list")
        group = _group(groups, matcher)
        entries = group.setdefault("hooks", [])
        existing = None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # Match on the hook's path within a clone, so another checkout's copy of the
            # same hook is repointed here instead of being left beside this one.
            if str(entry.get("command", "")).endswith(rel):
                existing = entry
                break
        if existing is None:
            entries.append({"type": "command", "command": command, "timeout": timeout})
            report.append(f"ok    claude  {event}/{matcher or '*'} WIRED: {rel}")
        elif existing.get("command") == command:
            report.append(
                f"ok    claude  {event}/{matcher or '*'} already wired: {rel}"
            )
        else:
            was = existing["command"]
            existing["command"] = command
            existing.setdefault("timeout", timeout)
            report.append(
                f"ok    claude  {event}/{matcher or '*'} REPOINTED: {rel}\n"
                f"        was: {was}"
            )
    return report


def main() -> int:
    if is_linked_worktree(REPO):
        print("ok    claude  session hooks not wired from a worktree (the main")
        print("        checkout owns them; a wt-* path would dangle on removal)")
        return 0

    path = settings_path()
    if not os.path.exists(path):
        # No settings file is not a failure: this machine may run Claude Code with
        # defaults, or not run it at all (LAW 38 — a fence a correct machine cannot
        # satisfy is an outage). Write a fresh one holding only our two hooks.
        settings: dict = {}
    else:
        try:
            with open(path) as f:
                settings = json.load(f)
        except Exception as exc:  # noqa: BLE001
            # Refuse rather than overwrite: a settings.json we cannot parse is one we
            # must not rewrite, or every guard already in it disappears.
            print(f"FAIL  claude  cannot parse {path}: {exc}", file=sys.stderr)
            print(
                "        fix the JSON and re-run bin/idp-install-hooks", file=sys.stderr
            )
            return 1
        if not isinstance(settings, dict):
            print(f"FAIL  claude  {path} is not a JSON object", file=sys.stderr)
            return 1

    before = json.dumps(settings, sort_keys=True)
    try:
        report = wire(settings)
    except ValueError as exc:
        print(f"FAIL  claude  {exc}", file=sys.stderr)
        return 1
    after = json.dumps(settings, sort_keys=True)

    if before != after:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".idp-tmp"
        with open(tmp, "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)

    for line in report:
        print(line)
    if before != after:
        print("        open /hooks once (or restart Claude Code) to load them in a")
        print("        session that was already running when this ran.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
