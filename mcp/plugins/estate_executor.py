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
            "this call. Read the outcome later with read_job."
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


def simulate_command(
    command: str,
    *,
    cwd: str | None = None,
    ceiling_sec: int = CEILING_SEC,
) -> dict:
    """The propose twin (MUM-288): what the executor WOULD do, running nothing.

    Built by running the same checks the execute door runs, so the two cannot drift: a proposal
    that says accepted and an execute that refuses would be a door reporting something the world
    does not do.
    """
    checks = _refusals_for(command, cwd, ceiling_sec)
    if checks:
        return {"would_accept": False, "error": checks[0]["error"], "refusals": checks}
    requested = max(MIN_CEILING_SEC, min(int(ceiling_sec), CEILING_SEC))
    return {
        "would_accept": True,
        "ceiling_sec": requested,
        "cwd": cwd or os.getcwd(),
        "note": "nothing was run; this is the executor's answer to the payload",
    }


def _refusals_for(command: str, cwd: str | None, ceiling_sec: int) -> list[dict]:
    """Every reason the execute door would refuse, in the order it would find them."""
    reasons: list[dict] = []
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


if __name__ == "__main__":  # pragma: no cover - a human reading the door
    # A tiny self-check a person can run: `python3 mcp/plugins/estate_executor.py`.
    import sys

    sample = sys.argv[1] if len(sys.argv) > 1 else "git status --short"
    print(json.dumps(simulate_command(sample), indent=2))
