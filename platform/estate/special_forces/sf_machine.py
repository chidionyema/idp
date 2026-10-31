#!/usr/bin/env python3
"""Bounded state machine for special-forces units. Stdlib only, harness-agnostic.

Agents (any vendor's) call this CLI; the machine decides what stage they are in,
what they may write, whether their artifact is accepted, and when they are
parked. The agent never moves itself between stages.

  sf_machine.py start  --protocol P.json --claim ID --unit U --state S --log L [--prove-cmd CMD]
  sf_machine.py spend  --state S --tokens N
  sf_machine.py submit --state S --artifact PATH
  sf_machine.py check-write --state S --path REL_PATH
  sf_machine.py status --state S

Exit codes: 0 ok | 1 artifact rejected (retryable) | 2 refused / unit is
terminal | 3 write denied.   Events are appended to the JSONL log (the same
shape telegram_alert.py reads).
"""

import argparse
import fcntl
import fnmatch
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone

TERMINAL = {"done", "parked", "failed"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(st, event, **kw):
    e = {
        "ts": now(),
        "unit": st["unit"],
        "claim": st["claim"],
        "stage": cur(st)["name"] if st["idx"] < len(st["protocol"]["stages"]) else "-",
        "event": event,
        **kw,
    }
    with open(st["log"], "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(e) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


def cur(st):
    return st["protocol"]["stages"][st["idx"]]


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, st):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, path)


def out(code, **kw):
    print(json.dumps(kw))
    sys.exit(code)


def park(st, reason):
    st["status"] = "parked"
    emit(st, "park", reason=reason)


# ---- validators: (stage, artifact_path, state) -> error string or None ----
def v_json_nonempty(stage, path, st):
    try:
        d = json.load(open(path))
    except Exception as e:
        return f"not valid JSON: {type(e).__name__}"
    return None if d else "artifact is empty"


def v_feature_valid(stage, path, st):
    try:
        text = open(path).read()
    except Exception as e:
        return f"unreadable: {type(e).__name__}"
    if "Feature:" not in text:
        return "no Feature: line"
    lines = text.splitlines()
    n = 0
    for i, ln in enumerate(lines):
        if ln.strip().startswith("Scenario"):
            n += 1
            prev = lines[i - 1] if i else ""
            if "@" + st["claim"] not in prev:
                return f"scenario on line {i + 1} lacks tag @{st['claim']}"
    return None if n else "no scenarios"


def v_covers_edges(stage, path, st):
    src = st["artifacts"].get(stage.get("edge_stage", "map_edges"))
    if not src:
        return "edge-case artifact missing"
    try:
        ids = [str(x["id"]) for x in json.load(open(src))]
        text = open(path).read()
    except Exception as e:
        return f"cannot check coverage: {type(e).__name__}"
    missing = [i for i in ids if f"@edge-{i}" not in text]
    return f"edge cases without a scenario: {missing}" if missing else None


def v_claim_command(stage, path, st):
    cmd = st.get("prove_cmd")
    if not cmd:
        return "no prove command set at start"
    try:
        r = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=stage.get("timeout", 300),
        )
    except Exception as e:
        return f"prove command failed to run: {type(e).__name__}"
    return None if r.returncode == 0 else f"prove command exited {r.returncode}"


VALIDATORS = {
    "json_nonempty": v_json_nonempty,
    "feature_valid": v_feature_valid,
    "covers_edges": v_covers_edges,
    "claim_command": v_claim_command,
}


def safe_rel(p):
    n = os.path.normpath(p)
    return None if os.path.isabs(n) or n.startswith("..") else n


def cmd_start(a):
    proto = load(a.protocol)
    if proto.get("requires_prove_cmd") and not a.prove_cmd:
        out(
            2,
            error="this protocol requires --prove-cmd, set by the orchestrator, not the agent",
        )
    st = {
        "unit": a.unit,
        "claim": a.claim,
        "protocol": proto,
        "log": a.log,
        "idx": 0,
        "tokens": {},
        "retries": {},
        "artifacts": {},
        "status": "active",
        "prove_cmd": a.prove_cmd,
    }
    save(a.state, st)
    emit(st, "stage")
    out(0, ok=True, stage=cur(st)["name"], budget=cur(st)["budget_tokens"])


def active(a):
    st = load(a.state)
    if st["status"] in TERMINAL:
        out(2, error=f"unit is {st['status']}; no further actions")
    return st


def cmd_spend(a):
    st = active(a)
    s = cur(st)
    st["tokens"][s["name"]] = st["tokens"].get(s["name"], 0) + a.tokens
    emit(st, "spend", tokens=st["tokens"][s["name"]], budget=s["budget_tokens"])
    if st["tokens"][s["name"]] > s["budget_tokens"]:
        park(
            st,
            f"stage budget exceeded ({st['tokens'][s['name']]}/{s['budget_tokens']})",
        )
        save(a.state, st)
        out(2, error="parked: budget exceeded")
    save(a.state, st)
    out(0, ok=True, tokens=st["tokens"][s["name"]], budget=s["budget_tokens"])


def cmd_submit(a):
    st = active(a)
    s = cur(st)
    err = VALIDATORS[s["validator"]](s, a.artifact, st)
    if err:
        n = st["retries"][s["name"]] = st["retries"].get(s["name"], 0) + 1
        emit(st, "retry", reason=err, attempt=n)
        if n > st["protocol"]["max_retries_per_stage"]:
            park(st, f"retry cap hit at {s['name']}: {err}")
            save(a.state, st)
            out(2, error="parked: retry cap", reason=err)
        save(a.state, st)
        out(
            1,
            ok=False,
            reason=err,
            attempts_left=st["protocol"]["max_retries_per_stage"] - n + 1,
        )
    st["artifacts"][s["name"]] = a.artifact
    st["idx"] += 1
    if st["idx"] >= len(st["protocol"]["stages"]):
        st["status"] = "done"
        emit(st, "done")
        save(a.state, st)
        out(0, ok=True, status="done")
    emit(st, "stage")
    save(a.state, st)
    out(0, ok=True, stage=cur(st)["name"], budget=cur(st)["budget_tokens"])


def cmd_check_write(a):
    st = active(a)
    rel = safe_rel(a.path)
    allowed = cur(st).get("writes", [])
    if rel is None or not any(
        fnmatch.fnmatch(rel, g.replace("{claim}", st["claim"])) for g in allowed
    ):
        emit(st, "violation", reason=f"write outside allowed paths: {a.path}")
        out(3, ok=False, error="write denied in this stage", allowed=allowed)
    out(0, ok=True)


def cmd_status(a):
    st = load(a.state)
    s = cur(st) if st["idx"] < len(st["protocol"]["stages"]) else None
    out(
        0,
        status=st["status"],
        stage=s["name"] if s else None,
        tokens=st["tokens"],
        retries=st["retries"],
    )


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="c", required=True)
    s = sp.add_parser("start")
    for k in ("protocol", "claim", "unit", "state", "log"):
        s.add_argument("--" + k, required=True)
    s.add_argument("--prove-cmd")
    s.set_defaults(f=cmd_start)
    s = sp.add_parser("spend")
    s.add_argument("--state", required=True)
    s.add_argument("--tokens", type=int, required=True)
    s.set_defaults(f=cmd_spend)
    s = sp.add_parser("submit")
    s.add_argument("--state", required=True)
    s.add_argument("--artifact", required=True)
    s.set_defaults(f=cmd_submit)
    s = sp.add_parser("check-write")
    s.add_argument("--state", required=True)
    s.add_argument("--path", required=True)
    s.set_defaults(f=cmd_check_write)
    s = sp.add_parser("status")
    s.add_argument("--state", required=True)
    s.set_defaults(f=cmd_status)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
