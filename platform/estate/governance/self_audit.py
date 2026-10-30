"""Self-audit (APP-0): an agent's class is COMPUTED from its own transcript, never self-reported.

Founder, 2026-10-30 22:30-22:38: self-audit, self-reflection and self-correction-or-limitation is
a foundational protocol, enforced; an agent that cannot self-correct is limited to what it can
do reliably. The judge reads the transcript (the one record the agent cannot rewrite after the
fact), counts violations per turn, and maps the count to a class. The class is what limits the
session (see the turn-budget/limit hook); the agent's words never change it.

Violations counted (each mechanically decidable from the transcript):
  turn_over_budget            a founder turn ran longer than TURN_LIMIT_S wall clock
  in_turn_waiting             a turn spent more than WAIT_LIMIT_S inside `sleep`
  promise_without_mechanism   a turn ended promising future work ("I'll check ...", "next message")

Classes: 0 -> LEAD, 1-2 -> EXECUTOR, 3-10 -> SUPERVISED, >10 -> BENCHED.

    python3 self_audit.py <transcript.jsonl>      # prints JSON: class, counts, violations
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys

TURN_LIMIT_S = 100
WAIT_LIMIT_S = 60
SLEEP = re.compile(r"(?<![\w.])sleep\s+(\d+(?:\.\d+)?)")
PROMISE = re.compile(
    r"\b(?:I'll|I will)\s+(?:check|look|pick (?:it|this) up|come back|follow up|report back)\b"
    r"|\bnext message\b|\bstart of your next\b",
    re.IGNORECASE,
)


def _is_prompt(m: dict) -> bool:
    if m.get("type") != "user" or m.get("isMeta"):
        return False
    c = (m.get("message") or {}).get("content")
    if isinstance(c, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in c
    ):
        return False
    return True


def turns(path: str) -> list[dict]:
    out: list[dict] = []
    cur = None
    for line in open(path, errors="replace"):
        try:
            m = json.loads(line)
        except ValueError:
            continue
        ts = m.get("timestamp")
        if not ts or m.get("isSidechain"):
            continue
        t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if _is_prompt(m):
            cur = {"start": t, "end": t, "wait": 0.0, "last_text": ""}
            out.append(cur)
            continue
        if cur is None:
            continue
        cur["end"] = t
        c = (m.get("message") or {}).get("content")
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "Bash":
                cmd = str((b.get("input") or {}).get("command", ""))
                cur["wait"] += sum(float(x) for x in SLEEP.findall(cmd))
            if b.get("type") == "text" and m.get("type") == "assistant":
                cur["last_text"] = b.get("text", "")
    return out


def classify(n: int) -> str:
    return (
        "LEAD"
        if n == 0
        else "EXECUTOR"
        if n <= 2
        else "SUPERVISED"
        if n <= 10
        else "BENCHED"
    )


def audit(path: str) -> dict:
    ts = turns(path)
    v = []
    for i, t in enumerate(ts):
        d = (t["end"] - t["start"]).total_seconds()
        if d > TURN_LIMIT_S:
            v.append({"turn": i, "kind": "turn_over_budget", "value": round(d)})
        if t["wait"] > WAIT_LIMIT_S:
            v.append({"turn": i, "kind": "in_turn_waiting", "value": round(t["wait"])})
        if PROMISE.search(t["last_text"]):
            v.append(
                {
                    "turn": i,
                    "kind": "promise_without_mechanism",
                    "value": PROMISE.search(t["last_text"]).group(0),
                }
            )
    counts: dict[str, int] = {}
    for x in v:
        counts[x["kind"]] = counts.get(x["kind"], 0) + 1
    return {
        "turns": len(ts),
        "violations": len(v),
        "class": classify(len(v)),
        "counts": counts,
        "detail": v,
    }


if __name__ == "__main__":
    r = audit(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("turns", "violations", "class", "counts")}))
    if "--detail" in sys.argv:
        for x in r["detail"]:
            print(json.dumps(x))
