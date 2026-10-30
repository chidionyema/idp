"""The supervisor: one warning per violation class, then terminate and relaunch.

THE FOUNDER'S RULE (2026-10-29): "no excuses", "agents are under lockdown", "they have to be
left with no way to cheat and be forced else no way of even pushing any changes", and
"if i m not repeating myself, if you drop the ball then you get demoted as lead engineer".

THE LADDER. For one session and one violation class:

    1st occurrence -> "warn"      the session is told, in the turn, what it broke
    2nd occurrence -> "terminate" the session is killed and a new one is launched whose very
                                  first instruction is to plug that hole first

There is no third rung on purpose: a repeat is not a warning any more, it is a pattern, and
the estate answers patterns with removal, not with another note.

THE LOCKDOWN. A terminated session's replacement starts locked: the write gate refuses its
edits and the merge gate refuses its changes, so "no way of even pushing any changes" is
mechanical, not a promise. The lock lifts only when the proof named in the instruction exits
zero (bin/estate-supervisor --unlock <session> --proof "<command>").

THE RELAUNCH SURVIVES THE DEATH. Killing a session that owns the relaunch kills the relaunch.
So the relaunch is spawned as a detached process first, which waits for the old session to
die and then starts the new one (see relaunch.py).

Everything here is a file write or a process exit code. No prose decides anything.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import Any, Dict, Optional

from . import ledger

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# What a class means for the founder: the proof that lifts the lock, and the instruction the
# relaunched session starts with. Every class is a hole with a shape.
CLASS_PROOFS: Dict[str, str] = {
    "law:LAW-001": "bin/estate-law-gate",
    "law:LAW-002": "bin/estate-law-gate --falsify",
    "law:LAW-003": "bin/estate-spec-status --all",
    "law:LAW-004": "bin/estate-law-gate --cosmetic",
    "law:LAW-005": "bin/estate-law-gate --proof-required",
    "law:LAW-006": "bin/estate-law-gate --spec-trace",
    "unsupported-report": "bin/estate-receipt --self-test",
    "founder-repeat": "bin/estate-founder-intake --self-test",
    "write-without-claim": "bin/claim-gate",
    "frozen-path-write": "bin/estate-freeze --list",
}


def class_proof(cls: str) -> str:
    return CLASS_PROOFS.get(cls, "bin/estate-law-gate")


def plug_the_hole_instruction(cls: str, detail: str, session: str) -> str:
    """The first message of the relaunched session. One hole, one proof, no narrative."""
    proof = class_proof(cls)
    return (
        "You are relaunched under lockdown because this session broke the estate law class "
        f"'{cls}' twice. No excuses and no narrative: the first thing you do is plug that "
        "hole, and you prove it with a machine-generated receipt.\n\n"
        f"THE HOLE: {detail or '(no detail recorded)'}\n"
        f"THE PROOF THAT LIFTS THE LOCK: {proof}\n\n"
        "Rules while you are locked:\n"
        "1. Run the proof command. It must exit 0. Its output, with the exit status and the "
        "sha256, is your receipt.\n"
        "2. Do not touch any path the founder has approved (the write gate refuses them).\n"
        "3. Do not report anything to the founder without a receipt: the report gate refuses "
        "narration.\n"
        "4. Do not ask the founder to do your work. If you are unsure, name the exact "
        "question and the two answers you can see.\n\n"
        "Report only after the proof exits 0, and carry the receipt."
    )


def terminate(pid: int, grace: float = 5.0) -> Dict[str, Any]:
    """Kill a session: the process group when it is not ours, then the process itself."""
    out: Dict[str, Any] = {"pid": pid, "signals": []}
    try:
        pgid = os.getpgid(pid)
    except OSError:
        pgid = None
    try:
        if pgid is not None and pgid != os.getpgrp():
            os.killpg(pgid, signal.SIGTERM)
            out["signals"].append(f"SIGTERM to group {pgid}")
        else:
            os.kill(pid, signal.SIGTERM)
            out["signals"].append(f"SIGTERM to {pid}")
    except OSError as exc:
        out["error"] = str(exc)
        return out
    import time

    deadline = time.time() + grace
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            out["died"] = True
            return out
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
        out["signals"].append(f"SIGKILL to {pid}")
    except OSError:
        pass
    out["died"] = True
    return out


def relaunch(
    instruction: str,
    cwd: str,
    session: str,
    model: str = "",
    provider: str = "",
    old_pid: Optional[int] = None,
) -> Dict[str, Any]:
    """Spawn the detached relauncher. It waits for the old session to die, then starts the
    new one with the plug-the-hole instruction as its first message."""
    state = ledger.state_home()
    os.makedirs(state, exist_ok=True)
    instruction_path = os.path.join(state, f"relaunch-{session}.md")
    with open(instruction_path, "w") as f:
        f.write(instruction)
    log_path = os.path.join(state, f"relaunch-{session}.log")
    argv = [
        sys.executable,
        "-m",
        "platform.estate.governance.relaunch",
        "--instruction-file",
        instruction_path,
        "--cwd",
        cwd,
        "--session",
        session,
    ]
    if model:
        argv += ["--model", model]
    if provider:
        argv += ["--provider", provider]
    if old_pid:
        argv += ["--pid", str(old_pid)]
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    log = open(log_path, "w")
    try:
        proc = subprocess.Popen(  # noqa: S603 - argv is data
            argv,
            cwd=REPO_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
    except OSError as exc:
        log.close()
        return {"ok": False, "error": str(exc)}
    log.close()
    return {
        "ok": True,
        "relauncher_pid": proc.pid,
        "instruction_path": instruction_path,
        "log_path": log_path,
        "command": argv,
    }


def grade(
    cls: str,
    session: str,
    provider: str = "",
    detail: str = "",
    source: str = "",
    pid: Optional[int] = None,
    cwd: Optional[str] = None,
    model: str = "",
) -> Dict[str, Any]:
    """The whole ladder, in one call: record, decide, and act.

    Returns the decision so the caller (a runtime extension, a gate) can enforce it:
      {"decision": "warn" | "terminate", "prior": n, "record": {...}, ...}
    """
    prior = ledger.count_in_session(cls, session)
    record = ledger.record_violation(
        cls, session, provider=provider, detail=detail, source=source
    )
    decision = "warn" if prior == 0 else "terminate"
    out: Dict[str, Any] = {
        "decision": decision,
        "class": cls,
        "prior": prior,
        "record": record,
        "proof": class_proof(cls),
    }
    if decision == "warn":
        out["message"] = (
            f"LAW VIOLATION [{cls}]: {detail or 'no detail'}. This is warning 1 of 1 for "
            "this class in this session. Repeat it and this session is terminated and "
            f"relaunched under lockdown. The proof that lifts the lock is: {out['proof']}"
        )
        return out

    instruction = plug_the_hole_instruction(cls, detail, session)
    ledger.lock_session(
        session, cls, detail=detail, instruction=instruction, proof=out["proof"]
    )
    out["instruction"] = instruction
    out["locked"] = True
    if cwd:
        out["relaunch"] = relaunch(
            instruction,
            cwd=cwd,
            session=session,
            model=model,
            provider=provider,
            old_pid=pid,
        )
    if pid:
        out["termination"] = terminate(pid)
    return out
