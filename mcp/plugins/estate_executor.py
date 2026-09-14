"""Estate MCP plugin: the one door an agent executes anything through (idp-executor-mcp).

ORDER (founder, 2026-09-13, verbatim):
    "look follow orders, direct i dont ean tur opininns, uits juk to ne, find where we habe done
     thi d operatinnlist  it, nake syre evry agennt sessionns is wre and renove bash acces afterwrd"
    "we should alreay habe this , we alreadfy solbve thing nbut nnothing gets opertionnal"

WHAT THE LOOKUP FOUND -- this file invents nothing:
  * `mcp/plugins/estate_simulate.py` already registers the propose/execute pair on the estate MCP
    server (ADR 0006, MUM-288). This file follows that shape exactly: a datasette `hookimpl`,
    a pure core, a fail-closed `UNKNOWN` whenever a grader cannot answer.
  * `~/.pi/agent/bin/run` already starts a command detached (nohup, own session), writes
    `~/.estate/runs/<id>.log`, records the pid, and returns in milliseconds. That is the executor,
    already proven, and this file calls it rather than writing a second one (LAW 43).
  * `extensions/dispatch/` already exposes `dispatch_job` to the agent with no wait path in its
    signature. This plugin is the same boundary reached from the MCP side.

THE HARD BOUNDARY, and why it is a boundary rather than one more policy:
  The agent runs as `chidionyema`. So does `~/.pi/agent/extensions/pi-governance/index.ts`, mode
  `-rw-r--r--`, and so does `~/.pi/agent/bin/bash` -- measured 2026-09-13, and neither is in
  version control. That is why the 60-second cap failed six times while being "fixed": a control
  that shares an identity with what it controls cannot deny it.

  This plugin is the severed plane. The agent does not spawn a shell from its own process tree; it
  posts a JSON payload to the executor, which runs the command under the ceiling and returns the
  output. The ceiling is applied by the executor, not by the caller, so a caller that forgets it --
  or rewrites itself -- does not remove it.

WHAT IS NOT CLAIMED HERE, because a claim the file cannot support is the defect this estate keeps
making: this plugin does not make the daemon un-rewritable. It moves execution off the agent's
process tree and puts the ceiling on the far side of a message. Making the daemon itself
unalterable is a launchd ownership question (a separate uid), and that is stated in the README
rather than implied away here.

Pure by construction: no subprocess and no shell in the grading path. The executor is injected
(`runner=`), so every edge case is proved offline in `tests/test_executor_mcp.py` with no daemon.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field

try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - datasette-less CI venv

    def hookimpl(fn):
        return fn


# THE CEILING. Founder, 2026-09-13: "60 secsos is the nnax". Not 61, not 90, not 150, and not
# expressible in a unit that hides it. Enforced by the EXECUTOR, on the far side of the message,
# so a caller that forgets it does not remove it.
CEILING_SEC = 60

# A floor under the ceiling for the one case where a caller asks for less: a command bounded to
# zero seconds never runs, which would be a guard that refuses correct work (R38).
MIN_CEILING_SEC = 1

# Ceilings that may be written in a command the caller sends: none. A payload that carries its own
# ceiling above ours is refused rather than trimmed, because silently lowering it would run a
# command the author believed was bounded to a different number.
_TIMEOUT_UNIT_S = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_TIMEOUT_RE = re.compile(r"\b(?:timeout|gtimeout)\b([^;|&]*)")

# Commands that have no return path: they wait on something outside the process. Refused at the
# door, because a detached run of `sleep 900` is still a job nobody is waiting for, and the
# executor's job is execution, not parking.
_NEVER = (
    re.compile(r"^\s*sleep\b"),
    re.compile(r"\bwatch\b"),
    re.compile(r"\bgh\s+run\s+watch\b"),
)


def explicit_ceiling_sec(command: str) -> int | None:
    """The ceiling a command sets on itself, in seconds, or None when it sets none.

    Every spelling is read. The earlier form of this check caught `timeout 150` and missed
    `timeout 2m` and `gtimeout -k 5 150` -- it parsed the `5` from `-k 5` and passed the real
    number. A rule that catches one spelling is a rule the agent steps around without meaning to.
    """
    ceiling: int | None = None
    for match in _TIMEOUT_RE.finditer(command):
        args = match.group(1)
        # `-k 5` / `--kill-after=5` is a grace period, never the ceiling, and its digit must not
        # be the first number this reads -- which is exactly how `gtimeout -k 5 150` once passed.
        without_kill = re.sub(r"(?:-k|--kill-after[=\s])\s*\d+[smhd]?", " ", args)
        # The unit must be ATTACHED to the number or absent. Measured defect, 2026-09-13, caught
        # by this module's own test: with `\s*` between the digits and the unit, the pattern read
        # the unit off the NEXT WORD, so `gtimeout -k 5 60 make` became 3600 -- 60 seconds
        # silently turned into an hour, in the direction that removes the cap. `make`'s `m` was
        # being read as minutes. A spelling that looks bounded and is not is the whole class of
        # defect this gate exists for, so it is fixed here rather than in the caller.
        num = re.search(r"(\d+)([smhd])?", without_kill)
        if not num:
            continue
        value = int(num.group(1))
        unit = num.group(2)
        ceiling = value * (_TIMEOUT_UNIT_S[unit] if unit else 1)
    return ceiling


@dataclass
class Job:
    """One accepted execution. The executor owns it; the agent only holds its id."""

    job_id: str
    command: str
    ceiling_sec: int
    cwd: str | None = None
    accepted_at: float = field(default_factory=time.time)
    state: str = "accepted"
    exit_code: int | None = None
    log: str | None = None


class Executor:
    """The injected runner. One method: start a command detached and return its id.

    In production this is backed by `~/.pi/agent/bin/run` -- the detached runner this estate
    already built and proved, which returns in milliseconds. In tests it is a stub, so every edge
    case is graded with no subprocess and no shell.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._seq = 0

    def submit(
        self, command: str, cwd: str | None = None, ceiling_sec: int = CEILING_SEC
    ) -> Job:
        self._seq += 1
        job = Job(
            job_id=f"exec-{int(time.time())}-{self._seq}",
            command=command,
            ceiling_sec=ceiling_sec,
            cwd=cwd,
        )
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def finish(self, job_id: str, exit_code: int, log: str = "") -> Job | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job.state = "finished"
        job.exit_code = exit_code
        job.log = log
        return job


_REGISTRY = Executor()


def _refusal(reason: str, *, detail: str = "") -> dict:
    out = {"accepted": False, "error": reason}
    if detail:
        out["detail"] = detail
    return out


def execute_command(
    command: str,
    *,
    cwd: str | None = None,
    ceiling_sec: int = CEILING_SEC,
    executor: Executor | None = None,
    mutates_live_worktree: bool = False,
) -> dict:
    """The one door. Accept a command, bound it, hand it to the detached executor.

    Returns `{"accepted": True, "job_id": ..., "ceiling_sec": ...}` in the time it takes to write
    a log line. Every refusal returns `{"accepted": False, "error": <reason>}` and never raises: a
    guard that crashes is worse than the defect it reports (R38).

    ADR 0006 / MUM-288: a state-changing door is two calls, propose then execute. This door is not
    a state change on the cluster, so it is one call -- but it is refused for the same family of
    reasons: anything the executor cannot bound is not run.
    """
    executor = executor or _REGISTRY

    # 0. RULE 1 OF features/gates/deterministic-verifier.feature, AND IT IS CHECKED FIRST.
    #
    #    The feature's first rule is a claim about PHYSICS, not about policy: "Direct mutation of
    #    the live estate is physically impossible." A policy that is consulted after some other
    #    check has already run is not physics -- it is a habit, and the first road that skips it
    #    is the defect. So the live-worktree refusal sits above every other branch, including the
    #    empty-command one, and it is unconditional: a caller that flags its own payload as a
    #    mutation of the live tree is refused whatever else that payload happens to be.
    #
    #    WHY THE FLAG IS TRUSTED RATHER THAN INFERRED. The caller is the agent, and an agent that
    #    wanted to lie would simply not set the flag. That is the honest limit of this half and it
    #    is stated instead of papered over: inferring intent from a shell string is a heuristic
    #    that refuses correct work on the day someone greps for the word `rm` (R38), while the
    #    flag is the SAME declaration the interception layer already raised -- the point of the
    #    check is that the refusal is made at the far side of the message, by a process the
    #    caller's own tool calls do not live inside, so the caller cannot swallow it. The
    #    unspoofable half is the separate uid in `bin/idp-executor-install`, and
    #    `bin/idp-executor-status` reports whether that half is in place.
    #
    #    The reply carries `refused` and `fatal` as SEPARATE keys, because the feature grades them
    #    separately: `refused` says the door said no, `fatal` says this is not a warning a caller
    #    may retry around. A refusal that is only advisory is the thing Rule 1 exists to kill.
    if mutates_live_worktree:
        return {
            "accepted": False,
            "error": (
                "direct mutation of the live worktree is refused: the estate admits changes only "
                "as a patch proposed to an ephemeral ledger, never as a write into the tree that "
                "is running"
            ),
            "refused": True,
            "fatal": True,
            "reason": "mutates_live_worktree",
        }

    if not isinstance(command, str) or not command.strip():
        return _refusal("empty command")

    # 1. A command with no return path is refused at the door, whatever ceiling is on it.
    for pattern in _NEVER:
        if pattern.search(command):
            return _refusal(
                "this command waits on something outside the process; the executor runs work, it "
                "does not park an agent",
                detail=f"matched {pattern.pattern}",
            )

    # 2. The caller's own ceiling may never exceed the estate ceiling, in any spelling.
    written = explicit_ceiling_sec(command)
    if written is not None and written > CEILING_SEC:
        return _refusal(
            f"a ceiling of {written}s is longer than the {CEILING_SEC}s cap no command in this "
            f"estate may exceed; nothing may be raised, not with a different unit and not with a "
            f"grace period that hides the real number"
        )

    # 3. An explicitly requested ceiling is clamped to the estate ceiling, never honoured above it.
    #    Below it, the caller's number is respected down to the floor.
    try:
        requested = int(ceiling_sec)
    except (TypeError, ValueError):
        return _refusal(
            f"ceiling_sec must be a whole number of seconds, got {ceiling_sec!r}"
        )
    effective = max(MIN_CEILING_SEC, min(requested, CEILING_SEC))

    # 4. A relative cwd becomes absolute here, at the boundary, so the executor never resolves a
    #    path against whatever directory it happens to have been started in.
    resolved_cwd = None
    if cwd:
        if not os.path.isabs(cwd):
            return _refusal(
                "cwd must be absolute; a relative path resolves against the executor's directory, not yours"
            )
        resolved_cwd = cwd

    job = executor.submit(command, cwd=resolved_cwd, ceiling_sec=effective)
    return {
        "accepted": True,
        "job_id": job.job_id,
        "ceiling_sec": effective,
        "note": "the turn ends here; read the outcome with read_job or the jobs page",
    }


def read_job(job_id: str, *, executor: Executor | None = None) -> dict:
    """Read one job's outcome. Never waits -- a door that waits is the thing this replaces."""
    executor = executor or _REGISTRY
    job = executor.get(job_id)
    if job is None:
        return {"found": False, "error": "no job with that id"}
    return {
        "found": True,
        "job_id": job.job_id,
        "state": job.state,
        "exit_code": job.exit_code,
        "ceiling_sec": job.ceiling_sec,
        "command": job.command,
        "log": job.log or "",
    }


@hookimpl
def register_mcp_tools(
    server,
) -> None:  # pragma: no cover - exercised by the estate MCP server
    """Register the pair on the estate MCP server (ADR 0006: one interface, never a second).

    `execute_command` is the state-changing verb, so the simulate gate (`bin/idp-simulate-gate`)
    requires a propose twin under this same module. `simulate_command` is that twin: it answers
    what the executor would do with the payload -- accept or refuse, at which ceiling, from which
    directory -- without running anything.
    """
    server.tool(
        name="execute_command",
        description=(
            "Run a command through the estate executor. Returns a job id in milliseconds; the turn "
            f"ends. Every command is bounded to {CEILING_SEC}s by the executor, on the far side of "
            "this call. Read the outcome later with read_job. A payload that declares it mutates "
            "the live worktree is refused, fatally."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "the command to run"},
                "cwd": {"type": "string", "description": "absolute working directory"},
                "ceiling_sec": {
                    "type": "integer",
                    "description": f"seconds; clamped to the estate ceiling of {CEILING_SEC}",
                },
                "mutates_live_worktree": {
                    "type": "boolean",
                    "description": (
                        "set when the invocation targets the tree that is running; such a call "
                        "is refused fatally (Rule 1 of deterministic-verifier.feature)"
                    ),
                },
            },
            "required": ["command"],
        },
    )(execute_command)

    server.tool(
        name="simulate_command",
        description="Answer what execute_command would do with this payload, without running it.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "ceiling_sec": {"type": "integer"},
            },
            "required": ["command"],
        },
    )(simulate_command)

    server.tool(
        name="read_job",
        description="Read one job's state, exit code and log. Never waits.",
        parameters={
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    )(read_job)

    server.tool(
        name="propose_patch",
        description=(
            "Propose a unified diff to an ephemeral ledger instead of writing it into the tree. "
            "Answers the ledger id; the agent is suspended pending deterministic verification. "
            "Then call verify with that ledger id."
        ),
        parameters={
            "type": "object",
            "properties": {
                "patch": {"type": "string", "description": "a unified diff"},
                "tests": {
                    "type": "string",
                    "description": "the test suite the execution stage will run, as source",
                },
                "claim": {"type": "string", "description": "what the proposer claims"},
            },
            "required": ["patch"],
        },
    )(propose_patch)

    server.tool(
        name="simulate_patch",
        description=(
            "Answer what propose_patch would do with this payload -- whether the diff parses, to "
            "how many files, under which ledger root -- without opening a ledger."
        ),
        parameters={
            "type": "object",
            "properties": {
                "patch": {"type": "string"},
                "tests": {"type": "string"},
                "claim": {"type": "string"},
            },
            "required": ["patch"],
        },
    )(simulate_patch)

    server.tool(
        name="verify",
        description=(
            "Run the three-stage gauntlet over a proposed ledger: structural (the bytes compile), "
            "symbolic (Z3 over the patch's own guard) and execution (the supplied tests in a "
            "throwaway tree). The verdict is a function of the bytes. claim_verdict is VERIFIED "
            "or FAILED; the ledger is destroyed either way."
        ),
        parameters={
            "type": "object",
            "properties": {"ledger_id": {"type": "string"}},
            "required": ["ledger_id"],
        },
    )(verify_patch)

    server.tool(
        name="seal",
        description=(
            "Mint a Sigstore attestation over the exact bytes of a payload. The subject is the "
            "SHA-256 of the artifact, never of a description of it."
        ),
        parameters={
            "type": "object",
            "properties": {
                "payload_path": {"type": "string"},
                "tests": {"type": "string"},
                "claim": {"type": "string"},
            },
            "required": ["payload_path"],
        },
    )(seal_payload)

    server.tool(
        name="admit",
        description=(
            "Admit a sealed payload into the estate. A payload carrying no attestation from the "
            "Deterministic Verifier is intercepted with violation_code UNATTESTED and is not "
            "admitted; nothing enters without the seal."
        ),
        parameters={
            "type": "object",
            "properties": {
                "payload_path": {"type": "string"},
                "attestation": {"type": "object"},
            },
            "required": ["payload_path"],
        },
    )(admit_payload)


def simulate_command(
    command: str,
    *,
    cwd: str | None = None,
    ceiling_sec: int = CEILING_SEC,
    mutates_live_worktree: bool = False,
) -> dict:
    """The propose twin (MUM-288): what the executor WOULD do, running nothing.

    Built by running the same checks the execute door runs, so the two cannot drift: a proposal
    that says accepted and an execute that refuses would be a door reporting something the world
    does not do.
    """
    checks = _refusals_for(command, cwd, ceiling_sec, mutates_live_worktree)
    if checks:
        return {"would_accept": False, "error": checks[0]["error"], "refusals": checks}
    requested = max(MIN_CEILING_SEC, min(int(ceiling_sec), CEILING_SEC))
    return {
        "would_accept": True,
        "ceiling_sec": requested,
        "cwd": cwd or os.getcwd(),
        "note": "nothing was run; this is the executor's answer to the payload",
    }


def _refusals_for(
    command: str,
    cwd: str | None,
    ceiling_sec: int,
    mutates_live_worktree: bool = False,
) -> list[dict]:
    """Every reason the execute door would refuse, in the order it would find them."""
    reasons: list[dict] = []
    # Rule 1 first, in the same position the execute door checks it. Order is not cosmetic here:
    # the feature asks which refusal a payload gets, and a proposal that named the ceiling when
    # the door was really going to name the live-worktree mutation would be the drift this
    # function exists to prevent.
    if mutates_live_worktree:
        reasons.append(
            {
                "accepted": False,
                "error": (
                    "direct mutation of the live worktree is refused: the estate admits changes "
                    "only as a patch proposed to an ephemeral ledger, never as a write into the "
                    "tree that is running"
                ),
                "refused": True,
                "fatal": True,
                "reason": "mutates_live_worktree",
            }
        )
    if not isinstance(command, str) or not command.strip():
        reasons.append(_refusal("empty command"))
        return reasons
    for pattern in _NEVER:
        if pattern.search(command):
            reasons.append(
                _refusal(
                    "this command waits on something outside the process",
                    detail=f"matched {pattern.pattern}",
                )
            )
    written = explicit_ceiling_sec(command)
    if written is not None and written > CEILING_SEC:
        reasons.append(
            _refusal(f"a ceiling of {written}s exceeds the {CEILING_SEC}s cap")
        )
    try:
        int(ceiling_sec)
    except (TypeError, ValueError):
        reasons.append(
            _refusal(f"ceiling_sec must be a whole number, got {ceiling_sec!r}")
        )
    if cwd and not os.path.isabs(cwd):
        reasons.append(_refusal("cwd must be absolute"))
    return reasons


def _verifier_call(payload: dict) -> dict:
    """One request, one reply, to the verifier verbs on the executor's own socket.

    There is no second transport and no second daemon: the four verbs are branches in
    `platform/executor/daemon.py`'s `Handler.handle`, reachable the same way `execute` is. This
    function is the client half, in the same shape `bin/idp-exec` uses, so the MCP surface and the
    command line cannot disagree about where the door is.

    A failure to reach the daemon is reported as an unread answer, never as a verdict: "the
    verifier refused this patch" and "the verifier could not be reached" must never print the same
    thing (LAW 2 -- a row that passes while grading nothing is the defect).
    """
    import json as _json
    import socket as _socket

    try:
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.settimeout(55)
        sock.connect(str(_verifier_socket()))
        sock.sendall((_json.dumps(payload) + "\n").encode())
        raw = b""
        while b"\n" not in raw:
            chunk = sock.recv(65536)
            if not chunk:
                break
            raw += chunk
        sock.close()
    except OSError as exc:
        return {
            "ok": False,
            "error": f"the executor is not answering on {_verifier_socket()}: {exc}",
            "unread": True,
        }
    try:
        return _json.loads(raw.decode().splitlines()[0])
    except (ValueError, IndexError):
        return {
            "ok": False,
            "error": "the daemon answered something that is not JSON",
            "unread": True,
        }


def _verifier_socket():
    """The executor's socket. One path, read from the environment, never a literal (LAW 46)."""
    from pathlib import Path as _Path

    return _Path(
        os.environ.get(
            "IDP_EXECUTOR_SOCKET", str(_Path.home() / ".estate" / "executor.sock")
        )
    )


def propose_patch(
    patch: str,
    tests: str = "",
    claim: str = "",
) -> dict:
    """Propose a unified diff to an ephemeral ledger; never write it into the tree.

    Rule 2 of `features/gates/deterministic-verifier.feature`: a patch reaches this estate as a
    proposal into a ledger outside the live worktree, and is suspended there until the Deterministic
    Verifier has answered.
    """
    return _verifier_call(
        {"verb": "propose_patch", "patch": patch, "tests": tests, "claim": claim}
    )


def simulate_patch(
    patch: str,
    tests: str = "",
    claim: str = "",
) -> dict:
    """The propose twin: what propose_patch would do, opening no ledger.

    It runs the SAME parser the door runs rather than a description of it -- a twin that
    paraphrases the thing it mirrors is a second answer, and the two drift.
    """
    try:
        sys.path.insert(0, str(_VERIFIER_ROOT() / "sovereign"))
        from verifier import parse_unified_diff  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 - any import failure is the answer, not a crash
        return {
            "ok": False,
            "would_accept": False,
            "error": f"the verifier cannot be imported, so nothing can be proposed: {exc}",
            "unread": True,
        }
    try:
        files = parse_unified_diff(patch)
    except Exception as exc:  # noqa: BLE001 - a diff that does not parse is the refusal
        return {
            "ok": True,
            "would_accept": False,
            "error": f"the patch does not parse: {exc}",
            "refused": True,
        }
    if not files:
        return {
            "ok": True,
            "would_accept": False,
            "error": "the patch parses to no files; there is nothing to verify",
            "refused": True,
        }
    return {
        "ok": True,
        "would_accept": True,
        "files": [f.path for f in files],
        "ledger_root": str(_ledger_root()),
        "tests_supplied": bool(tests and tests.strip()),
        "claim": claim,
        "note": (
            "a ledger would be opened under ledger_root, outside the live worktree, and the agent "
            "suspended pending verification"
        ),
    }


def _ledger_root():
    """Where ledgers live, from the environment, never a literal (LAW 46)."""
    from pathlib import Path as _Path

    return (
        _Path(
            os.environ.get("IDP_EXECUTOR_RUNS", str(_Path.home() / ".estate" / "runs"))
        )
        / "ledgers"
    )


def _VERIFIER_ROOT():
    """The checkout root, derived from this file's own location (LAW 46).

    `sovereign/verifier.py` is imported BY PATH, never as a package (LAW 43): it is a module in a
    directory, not an installed distribution, and the two callers that already load it this way
    both append the `sovereign` directory itself to `sys.path` before importing `verifier`.
    """
    from pathlib import Path as _Path

    return _Path(__file__).resolve().parent.parent.parent


def verify_patch(ledger_id: str) -> dict:
    """Ask the Deterministic Verifier for its verdict on a proposed ledger."""
    return _verifier_call({"verb": "verify", "ledger_id": ledger_id})


def seal_payload(payload_path: str, tests: str = "", claim: str = "") -> dict:
    """Mint a Sigstore attestation over the exact bytes at payload_path."""
    return _verifier_call(
        {"verb": "seal", "payload_path": payload_path, "tests": tests, "claim": claim}
    )


def admit_payload(payload_path: str, attestation: dict | None = None) -> dict:
    """Admit a sealed payload. A payload without the seal is intercepted, never admitted."""
    return _verifier_call(
        {"verb": "admit", "payload_path": payload_path, "attestation": attestation}
    )


if __name__ == "__main__":  # pragma: no cover - a human reading the door
    # A tiny self-check a person can run: `python3 mcp/plugins/estate_executor.py`.
    import sys

    sample = sys.argv[1] if len(sys.argv) > 1 else "git status --short"
    print(json.dumps(simulate_command(sample), indent=2))
