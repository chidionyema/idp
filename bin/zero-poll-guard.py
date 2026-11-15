#!/usr/bin/env python3
"""zero-poll-guard -- I-8090 (idp#8057 REQ-012): mechanical refusal of synchronous polling.

R10 was measured, not felt: 133 poll incidents in 24h and 498 distinct command
forms for one question (docs/diagnoses/2026-11-11-reactive-wakeup-signaling-gap.md,
bin/lane-where). The positive replacements shipped the same day -- bin/estate-wait
(event-driven join), bin/lane-where (exit-code verdicts), Greenlane convergence.
PR #8161 relapsed on 2026-11-15 with a 14-iteration `gh pr view + sleep` loop,
because nothing REFUSED the poll at the boundary. This guard is that refusal.

Verdicts:
  exit 0   ALLOW  -- not a poll: batch loops over remote writes, plain reads,
                     local loops, daemons on their own files (diff-scan's job)
  exit 78  REFUSE -- a poll. The harness hook refuses BEFORE spawning the shell.
  exit 1   REFUSE -- diff mode (idp-ci rung): the diff introduces polling.

Refusal semantics, deterministic:
  1. Blocking watch/wait verbs: gh run watch, gh pr checks --watch,
     kubectl wait, kubectl rollout status, kubectl get -w. These block a whole
     agent turn on remote state; the estate answer is push-and-stop.
  2. Convergence-polling shell loop: any for/while/until body that reads remote
     status AND (sleeps OR breaks on a state word). Measured disease.
  3. Allowed: loop bodies that only WRITE remotely (batch, no sleep), loops
     with no remote status read, single one-shot reads.
Stateful (only when ESTATE_LEASE_ID is set -- no lease, no tax, R14):
  4. One remote status read per (lease, target, head sha). A re-read at the
     same head is refused; a new head resets it. A greenlane dispatch marks the
     lease handed-off; reads after handoff are refused (push-and-stop).

Usage:
  python3 bin/zero-poll-guard.py -- <command words...>   # pre-exec gate
  python3 bin/zero-poll-guard.py --scan-diff [<base>]    # idp-ci rung
  python3 bin/zero-poll-guard.py --selftest              # falsifier smoke
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

EX_OK, EX_REFUSE, EX_FAIL = 0, 78, 1

RE_WATCH = re.compile(
    r"\bgh\s+run\s+watch\b"
    r"|\bgh\s+(?:pr|run)\s+\S+(?:\s+\S+)*\s--watch\b"
    r"|\bkubectl\s+(?:wait\b|rollout\s+status\b)"
    r"|\bkubectl\s+get\b[^|;&]*?(?:\s-w\b|\s--watch\b)",
    re.IGNORECASE,
)
RE_LOOP_HEAD = re.compile(r"\b(?:for|while|until)\b")
RE_READ = re.compile(
    r"\bgh\s+(?:pr|run)\s+(?:view|checks|status|list)\b"
    r"|\bgh\s+(?:api|search)\b(?!.*(?:-X|--method)\s+(?:POST|PUT|PATCH|DELETE))"
    r"|\b(?:curl|wget)\b(?![^\n]*(?:-X\s|--request\s|-d\s|--data\b))"
    r"|\bkubectl\s+(?:get|describe)\b",
    re.IGNORECASE,
)
RE_WRITE = re.compile(
    r"(?:-X|--method)\s+(?:POST|PUT|PATCH|DELETE)\b|\b(?:gh\s+api|curl|wget)\b[^\n]*\s(?:-d|--data|-f|--form)\b",
    re.IGNORECASE,
)
RE_SLEEP = re.compile(r"\bsleep\s+[0-9]|sleep\s+\$|usleep\b", re.IGNORECASE)
RE_BREAK = re.compile(r"\bbreak\b")
RE_STATE_WORD = re.compile(
    r"\b(?:MERGED|CLOSED|success(?:ful)?|complete[d]?|ready|SUCCEEDED|deployed|passed|green)\b",
    re.IGNORECASE,
)
RE_UNTIL = re.compile(r"^\s*until\b|\buntil\s+(?:gh|kubectl|curl|\[)", re.IGNORECASE)
RE_TARGET_PR = re.compile(
    r"\bgh\s+(?:pr\s+)?(?:view|checks)\s+(?:#)?(\d+)", re.IGNORECASE
)
RE_TARGET_RUN = re.compile(r"\bgh\s+run\s+(?:view|watch)\s+(\d+)", re.IGNORECASE)
RE_TARGET_API = re.compile(
    r"repos/[\w.-]+/[\w.-]+/(?:pulls|actions/runs|commits)/(\w+)", re.IGNORECASE
)
RE_HANDOFF = re.compile(
    r"actions/workflows/[\w.-]+/dispatches|\blane-submit\b|\bbin/shift-left-land\b|\bgreenlane\b.*dispatch",
    re.IGNORECASE,
)
EXEMPT_FILES = {"bin/zero-poll-guard.py", "tests/test_zero_poll.py"}
SCAN_CODE_PREFIXES = ("bin/", "platform/", "greenlane/", "scripts/", "src/", ".github/")


def loop_bodies(cmd: str) -> list[str]:
    """Every do...done span, with the loop CONDITION prepended (an `until gh pr
    checks ... do` poll hides its read in the condition, not the body)."""
    bodies: list[str] = []
    for m in re.finditer(r"\bdo\b", cmd):
        cond = cmd[max(0, m.start() - 200) : m.start()].rstrip().rstrip(";")
        cond = cond.rsplit(";", 1)[-1] if ";" in cond else cond
        depth, i, start = 1, m.end(), m.end()
        while i < len(cmd) and depth:
            tok = re.match(r"\b(?:do|done)\b", cmd[i:])
            if tok:
                depth += 1 if tok.group(0) == "do" else -1
                if not depth:
                    bodies.append(cond + cmd[start:i])
                i += tok.end()
            else:
                i += 1
    return bodies


def classify(cmd: str) -> dict:
    """Deterministic verdict on one command string."""
    if RE_WATCH.search(cmd):
        m = RE_WATCH.search(cmd)
        return {
            "verdict": "REFUSE",
            "rule": "WATCH_WAIT",
            "why": f"blocking watch/wait verb refuses the turn: {m.group(0)!r}",
        }
    for body in loop_bodies(cmd):
        if not RE_READ.search(body):
            continue
        if RE_WRITE.search(body) and not RE_READ.search(RE_WRITE.sub("", body)):
            continue  # batch loop over remote writes; a courtesy sleep is a throttle, not a poll
        sleep = RE_SLEEP.search(body)
        conv = RE_UNTIL.search(body) or (
            RE_BREAK.search(body) and RE_STATE_WORD.search(body)
        )
        if sleep and conv:
            return {
                "verdict": "REFUSE",
                "rule": "POLL_LOOP",
                "why": "loop reads remote status, sleeps and breaks on state",
                "evidence": body[:120],
            }
        if sleep:
            return {
                "verdict": "REFUSE",
                "rule": "POLL_LOOP",
                "why": "loop reads remote status and sleeps",
                "evidence": body[:120],
            }
        if conv:
            return {
                "verdict": "REFUSE",
                "rule": "POLL_LOOP",
                "why": "loop reads remote status and breaks on state convergence",
                "evidence": body[:120],
            }
    return {"verdict": "ALLOW", "rule": None, "why": "not a poll"}


def _state_db() -> str:
    d = os.path.expanduser("~/.estate/zero-poll")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "turn-state.sqlite")


def _target(cmd: str) -> str:
    for rex in (RE_TARGET_PR, RE_TARGET_RUN, RE_TARGET_API):
        m = rex.search(cmd)
        if m:
            return f"{m.lastindex and m.group(1)}@{rex.pattern[:12]}"
    return "remote-status"


def stateful_gate(cmd: str, lease: str, head: str) -> dict:
    """One remote status read per (lease, target, head); revoked after handoff.
    No lease id -> no state, no tax (R14)."""
    import sqlite3

    conn = sqlite3.connect(_state_db())
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS turns ("
            "lease TEXT, head TEXT, target TEXT, hits INT, revoked INT DEFAULT 0,"
            "PRIMARY KEY (lease, head, target))"
        )
        if conn.execute(
            "SELECT revoked FROM turns WHERE lease=? AND revoked=1 LIMIT 1", (lease,)
        ).fetchone():
            return {
                "verdict": "REFUSE",
                "rule": "LEASE_HANDOFF",
                "why": "lease handed off to the queue; push-and-stop",
            }
        verdict = classify(cmd)
        if verdict["verdict"] != "ALLOW":
            return verdict
        if not RE_READ.search(cmd):
            return verdict
        tgt = _target(cmd)
        row = conn.execute(
            "SELECT hits FROM turns WHERE lease=? AND head=? AND target=?",
            (lease, head, tgt),
        ).fetchone()
        if row and row[0] >= 1:
            return {
                "verdict": "REFUSE",
                "rule": "CROSS_TURN_REPEAT",
                "why": f"second status read of {tgt} at head {head[:8]} "
                "with no new commit; use estate-wait or stop",
            }
        conn.execute(
            "INSERT INTO turns (lease, head, target, hits) VALUES (?,?,?,1) "
            "ON CONFLICT(lease, head, target) DO UPDATE SET hits=hits+1",
            (lease, head, tgt),
        )
        conn.commit()
        return verdict
    finally:
        conn.close()


def note_handoff(cmd: str, lease: str) -> bool:
    """A greenlane dispatch or lane-submit marks the lease handed off."""
    import sqlite3

    if not RE_HANDOFF.search(cmd):
        return False
    conn = sqlite3.connect(_state_db())
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS turns ("
            "lease TEXT, head TEXT, target TEXT, hits INT, revoked INT DEFAULT 0,"
            "PRIMARY KEY (lease, head, target))"
        )
        conn.execute(
            "INSERT OR REPLACE INTO turns (lease, head, target, hits, revoked) "
            "VALUES (?, '', 'GREENLANE_HANDOFF', 1, 1)",
            (lease,),
        )
        conn.commit()
    finally:
        conn.close()
    return True


def _git(*args: str) -> str:
    argv = ["git", *args]
    return subprocess.run(  # noqa: S603 -- fixed binary, list argv, no shell, no user input
        argv, capture_output=True, text=True
    ).stdout


def guard(cmd: str) -> dict:
    lease = os.environ.get("ESTATE_LEASE_ID", "").strip()
    if not lease:
        return classify(cmd)
    head = os.environ.get("ESTATE_HEAD_SHA", "").strip()
    if not head:
        head = _git("rev-parse", "HEAD").strip() or "no-git"
    note_handoff(cmd, lease)
    return stateful_gate(cmd, lease, head)


def _added_lines() -> tuple[str, list[tuple[str, list[str]]]]:
    staged = _git("diff", "--cached", "--unified=0")
    if staged.strip():
        mode = "staged"
        diff = staged
    else:
        base = os.environ.get("IDP_CI_BASE", "")
        mode = f"{base}...HEAD" if base else "HEAD"
        diff = (
            _git("diff", "--unified=0", f"{base}...HEAD")
            if base
            else _git("show", "--format=", "--unified=0", "HEAD")
        )
    files: dict[str, list[str]] = {}
    cur = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:].strip()
        elif line.startswith("+") and not line.startswith("+++") and cur:
            files.setdefault(cur, []).append(line[1:])
    return mode, list(files.items())


def scan_diff() -> list[str]:
    """Polling constructs introduced by this diff (idp-ci rung)."""
    mode, files = _added_lines()
    hits: list[str] = []
    for path, lines in files:
        if not path.startswith(SCAN_CODE_PREFIXES) or path in EXEMPT_FILES:
            continue
        text = "\n".join(lines)
        verdict = classify(text)
        if verdict["verdict"] == "REFUSE":
            hits.append(f"{path}: [{verdict['rule']}] {verdict['why']}")
        if re.search(r"\bsetInterval\s*\(", text):
            hits.append(f"{path}: [JS_SET_INTERVAL] browser polling timer")
        if (
            re.search(r"\btime\.sleep\s*\(", text)
            and re.search(r"\bwhile\b.*:\s*$|while\s+True", text, re.MULTILINE)
            and RE_READ.search(text)
        ):
            hits.append(f"{path}: [PY_SLEEP_POLL] while + time.sleep + remote read")
    if hits:
        print(
            f"FAIL  zeropoll  {len(hits)} polling construct(s) introduced ({mode}):",
            file=sys.stderr,
        )
        for h in hits:
            print(f"  {h}", file=sys.stderr)
    return hits


# FALSIFIERS -- known-bad must be refused, known-good must pass (R2). tests/
# carries the full pytest suite; this smoke runs both directions standalone so
# the gate can never claim green from a scanner that failed to launch.
FALSIFIERS_BAD = [
    "for i in $(seq 1 14); do S=$(gh pr view 8161 --json state); "
    'case "$S" in MERGED:*) break;; esac; sleep 15; done',
    "gh run watch 12948192",
    "kubectl rollout status deployment/pennyd -w",
    "until gh pr checks 8161 | grep -q success; do sleep 30; done",
    "while true; do gh api repos/o/r/actions/runs/1; sleep 60; done",
]
FALSIFIERS_GOOD = [
    "for n in 690 689 688; do gh api -X PATCH repos/o/r/code-scanning/alerts/$n "
    "-f state=dismissed; done",
    "for f in $(git diff --name-only); do ruff check $f; done",
    "gh pr view 8161 --json state,mergeStateStatus",
    'while read -r line; do echo "$line"; done < notes.txt',
]


def selftest() -> int:
    bad = [(c, classify(c)) for c in FALSIFIERS_BAD]
    good = [(c, classify(c)) for c in FALSIFIERS_GOOD]
    failed = [c for c, v in bad if v["verdict"] != "REFUSE"]
    failed += [c for c, v in good if v["verdict"] != "ALLOW"]
    for c, v in bad:
        print(
            f"{'ok  ' if v['verdict'] == 'REFUSE' else 'FAIL'} refuse: "
            f"{v['rule']}: {c[:60]}"
        )
    for c, v in good:
        print(f"{'ok  ' if v['verdict'] == 'ALLOW' else 'FAIL'} allow: {c[:60]}")
    return EX_FAIL if failed else EX_OK


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return selftest()
    if argv and argv[0] == "--scan-diff":
        return EX_FAIL if scan_diff() else EX_OK
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        print(__doc__)
        return EX_FAIL
    verdict = guard(" ".join(argv))
    if verdict["verdict"] == "REFUSE":
        print(json.dumps({"refused": True, **verdict}), file=sys.stderr)
        return EX_REFUSE
    print(json.dumps({"allowed": True, "rule": verdict["rule"]}))
    return EX_OK


if __name__ == "__main__":
    sys.exit(main())
