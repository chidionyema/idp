#!/usr/bin/env python3
"""The Stop-hook door: every real session gets graded by D1 (PRM) and D2 (budget) the moment
it ends, with no one having to remember to run bin/idp-prm or bin/idp-budget by hand.

Ticket: docs/tickets/2026-09-14-reasoning-gateway.md. Before this file, D1/D2/D3 only ran two
ways: against their own two CI fixtures (rules.yaml, `planes: [ci]`) on every push, and against
whatever a person typed `bin/idp-prm --grade <path>` for by hand. Neither path ever touched a
real session unless someone remembered to point a gate at it -- and bin/idp-prm/idp-budget's own
"sweep the estate" bare-invocation case (R43, R38) read `~/.pi/agent/sessions`, a store that
stopped being written months before this ticket existed (fixed alongside this file, same commit:
bin/epistemic_firewall.py and bin/trajectory_lock.py's `_estate_sessions()` now also read
`~/.claude/projects`, where the Claude Code CLI actually writes one line per turn).

This is the other half: Claude Code's own Stop hook fires `transcript_path` at us on stdin after
every turn a session ends on. We grade THAT file directly -- the session that just happened, not
a historical sweep -- with the same two gates, no new logic (R43: idp-prm and idp-budget are
imported, not reimplemented).

Report, never block (R38's own convention, extended here on purpose): a step near the start of a
long session that already got fixed by step 40 would re-trip PRM every single Stop otherwise,
turning a real gate into a nuisance nobody can silence. So the verdict is written to
`~/.pi/agent/reasoning-gateway/<session_id>.json` and this always exits 0. The honest limit:
nothing here stops a bad step from landing -- it makes every real session's PRM/budget verdict
sit on disk where a person (or a future Backstage page reading the same file, the way
mcp/plugins/estate_sessions.py already reads the catalogue's own session rows) can see it without
running anything. The UI door for that surface does not exist yet; this is the write side of it.

  reasoning_gateway_hook.py --hook       what settings.json runs on Stop (reads hook JSON on stdin)
  reasoning_gateway_hook.py --report [N] the last N session verdicts, newest first (default 10)
  reasoning_gateway_hook.py --self-test  prove it
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent
LEDGER_DIR = Path.home() / ".pi" / "agent" / "reasoning-gateway"


def _run_gate(script: str, args: list[str]) -> dict:
    proc = subprocess.run(  # noqa: S603 -- fixed argv (this interpreter, a script under bin/), no shell
        [sys.executable, str(BIN / script), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {"exit": proc.returncode, "stdout": proc.stdout.strip()}


def grade(transcript_path: str) -> dict:
    p = Path(transcript_path)
    if not p.is_file():
        return {"blind": f"{p} does not exist"}
    return {
        "transcript": str(p),
        "prm": _run_gate("prm_grader.py", ["--grade", str(p)]),
        "budget": _run_gate("budget_governor.py", ["--run", str(p)]),
    }


def record(session_id: str, verdict: dict) -> Path:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    out = LEDGER_DIR / f"{session_id}.json"
    out.write_text(json.dumps(verdict, indent=2) + "\n")
    return out


def cmd_hook() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, json.JSONDecodeError):
        return 0  # malformed hook input is not this gate's failure to report (LAW 38)
    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id") or "unknown"
    if not transcript_path:
        return 0
    try:
        verdict = grade(transcript_path)
    except (OSError, subprocess.SubprocessError) as exc:
        verdict = {"blind": f"grading failed: {exc}"}
    verdict["session_id"] = session_id
    try:
        record(session_id, verdict)
    except OSError:
        pass  # the ledger write is a nicety; it must never take a live session down with it
    return 0


def cmd_report(limit: int) -> int:
    if not LEDGER_DIR.is_dir():
        print("ok    reasoning-gateway no session has been graded on this machine yet")
        return 0
    files = sorted(
        LEDGER_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    for f in files[:limit]:
        v = json.loads(f.read_text())
        prm = v.get("prm", {}).get("exit", "?")
        budget = v.get("budget", {}).get("exit", "?")
        print(f"{f.stem}: prm_exit={prm} budget_exit={budget}")
    print(
        f"ok    reasoning-gateway {len(files)} session(s) graded, {min(limit, len(files))} shown"
    )
    return 0


def _self_test() -> int:
    import tempfile

    good = (
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"tool_use","name":"declare_plan","input":{"goal":"g","subgoals":'
        '[{"id":"sg1","text":"g"}]}}]}}\n'
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"tool_use","name":"complete_goal","input":{"goal_id":"sg1"}}]}}\n'
    )
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td) / "session.jsonl"
        tp.write_text(good)
        v = grade(str(tp))
        if (
            "blind" in v
            or v["prm"]["exit"] not in (0, 1)
            or v["budget"]["exit"] not in (0, 1)
        ):
            print(
                f"FAIL reasoning_gateway_hook --self-test: grading a real transcript failed: {v}"
            )
            return 1
        v2 = grade(str(Path(td) / "missing.jsonl"))
        if "blind" not in v2:
            print(
                f"FAIL reasoning_gateway_hook --self-test: a missing transcript was not BLIND: {v2}"
            )
            return 1
    print("ok    reasoning_gateway_hook --self-test: 2 case(s) passed")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--hook":
        return cmd_hook()
    if argv[0] == "--report":
        limit = int(argv[1]) if len(argv) > 1 else 10
        return cmd_report(limit)
    if argv[0] == "--self-test":
        return _self_test()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
