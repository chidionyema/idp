"""The supervisor: a measured correction window before termination and relaunch.

THE FOUNDER'S RULE (2026-10-29): "no excuses", "agents are under lockdown", "they have to be
left with no way to cheat and be forced else no way of even pushing any changes", and
"if i m not repeating myself, if you drop the ball then you get demoted as lead engineer".

THE LADDER. For one session and one violation class, inside a bounded grace window:

    reporting classes (unsupported-report, founder-repeat)
      1st occurrence -> warn       the exact proof and receipt command
      2nd occurrence -> final warn the remaining countdown and one last correction path
      3rd occurrence -> terminate  lock and relaunch only after both warnings are ignored

    mutation and security classes
      1st occurrence -> warn       the exact proof and the grace deadline
      2nd occurrence -> terminate  a second dangerous act inside the window remains fail-closed

The grace window resets after a clean, receipt-backed report. A warning is not a hidden stop:
every warning carries the countdown, the failing class, and the exact command that clears it.

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
import time
from typing import Any, Dict, Optional

from . import ledger

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SOFT_CLASSES = {"unsupported-report", "founder-repeat"}
SOFT_STRIKE_LIMIT = 3
HARD_STRIKE_LIMIT = 2
DEFAULT_GRACE_SECONDS = int(os.environ.get("ESTATE_GOVERNANCE_GRACE_SECONDS", "180"))

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


def strike_limit(cls: str) -> int:
    return SOFT_STRIKE_LIMIT if cls in SOFT_CLASSES else HARD_STRIKE_LIMIT


def grace_seconds(cls: str) -> int:
    return DEFAULT_GRACE_SECONDS


def _epoch(timestamp: str) -> float:
    try:
        return time.mktime(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ"))
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _recent_violations(
    cls: str, session: str, now_epoch: float
) -> list[Dict[str, Any]]:
    cutoff = now_epoch - grace_seconds(cls)
    cleared_at = _epoch(
        str(ledger.get_session_state(session).get("warning_cleared_at", ""))
    )
    cutoff = max(cutoff, cleared_at)
    return [
        row
        for row in ledger.violations(session=session, cls=cls)
        if _epoch(str(row.get("ts", ""))) >= cutoff
    ]


def _remediation(cls: str) -> str:
    if cls == "unsupported-report":
        return (
            "1) Run `bin/estate-receipt --self-test`; "
            "2) produce the evidence with `bin/estate-receipt -- <command>`; "
            "3) include the receipt line and sha256 in the next report."
        )
    if cls == "founder-repeat":
        return (
            "Read the prior instruction, repeat back the unmet requirement, and address it "
            "before asking the founder to repeat anything."
        )
    return f"Run the proof command `{class_proof(cls)}`; it must exit 0 with a receipt."


def plug_the_hole_instruction(cls: str, detail: str, session: str) -> str:
    """The first message of the relaunched session. One hole, one proof, no narrative."""
    proof = class_proof(cls)
    return (
        "You are relaunched under lockdown because this session broke the estate law class "
        f"'{cls}' past its correction limit. No excuses and no narrative: the first thing "
        "you do is plug that hole, and you prove it with a machine-generated receipt.\n\n"
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
    """The whole correction ladder, in one call: record, decide, and act.

    Returns the decision so the caller (a runtime extension, a gate) can enforce it:
      {"decision": "warn" | "terminate", "prior": n, "record": {...}, ...}
    """
    now_epoch = time.time()
    recent = _recent_violations(cls, session, now_epoch)
    prior = len(recent)
    record = ledger.record_violation(
        cls, session, provider=provider, detail=detail, source=source
    )
    strike = prior + 1
    limit = strike_limit(cls)
    decision = "warn" if strike < limit else "terminate"
    first_recent = _epoch(str(recent[0].get("ts", ""))) if recent else now_epoch
    grace_remaining_s = max(0, int(first_recent + grace_seconds(cls) - now_epoch))
    out: Dict[str, Any] = {
        "decision": decision,
        "class": cls,
        "prior": prior,
        "strike": strike,
        "strikeLimit": limit,
        "attemptsRemaining": max(0, limit - strike),
        "graceSeconds": grace_seconds(cls),
        "graceRemainingSeconds": grace_remaining_s,
        "softClass": cls in SOFT_CLASSES,
        "record": record,
        "proof": class_proof(cls),
    }
    if decision == "warn":
        final = strike == limit - 1
        label = "FINAL WARNING" if final else "WARNING"
        out["message"] = (
            f"{label}: law violation [{cls}] ({strike} of {limit}): {detail or 'no detail'}. "
            f"You have {grace_remaining_s}s to correct course before this window closes. "
            f"Required correction: {_remediation(cls)} "
            + (
                "A clean, receipt-backed report clears this warning window."
                if final
                else f"{limit - strike} attempt(s) remain before the session is locked."
            )
        )
        ledger.set_session_state(
            session,
            status="grace",
            locked=False,
            violation_class=cls,
            strikes=strike,
            strike_limit=limit,
            grace_seconds=grace_seconds(cls),
            grace_remaining_seconds=grace_remaining_s,
            grace_ends_at=time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(now_epoch + grace_remaining_s),
            ),
            proof=out["proof"],
        )
        return out

    instruction = plug_the_hole_instruction(cls, detail, session)
    ledger.lock_session(
        session,
        cls,
        detail=detail,
        instruction=instruction,
        proof=out["proof"],
    )
    ledger.set_session_state(session, strikes=strike, strike_limit=limit)
    out["message"] = (
        f"Law violation [{cls}] reached {strike} of {limit} inside the correction window. "
        f"The session is locked. Unlock only after `{out['proof']}` exits 0; then run "
        f"`bin/estate-supervisor --unlock {session} --proof '{out['proof']}'`. "
        f"Required correction: {_remediation(cls)}"
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
