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

import json
import os
import re
import sys
import threading
import time
from typing import Optional
from dataclasses import dataclass, field

try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - datasette-less CI venv

    def hookimpl(fn):
        return fn


# THE CEILING. Founder, 2026-10-19: "100s as default instead of 60" — the standing value.
# Supersedes the 2026-09-13 "60 secsos is the max" ruling, which held the door at 60 for five
# weeks and was itself a reaction to runaway jobs. Not expressible in a unit that hides it, and
# still enforced by the EXECUTOR, on the far side of the message, so a caller that forgets it
# does not remove it. Per-job ceilings clamp to this (min(requested, CEILING_SEC)); nothing a
# caller sends can exceed the door.
CEILING_SEC = 100

# The free-space floor below which this door refuses to start work. 1500 MB is ~1.3% of the 113 GB
# volume: below it macOS cannot grow a swapfile, the compile/bundler caches of a single job are enough
# to fill it, and every other agent's job slows down. Env-overridable for a test and for a machine
# with a different volume.
MIN_FREE_MB = int(os.environ.get("ESTATE_MIN_FREE_MB", "1500"))


def _free_mb(path: str = "/") -> Optional[int]:
    """Free space on the volume that holds `path`, in MB, or None if it cannot be read.

    None is not zero: a door that cannot measure must not invent a floor breach and refuse a job
    that would have run (the estate's rule that an unmeasurable grader is UNKNOWN, never a pass or
    a fail). The measured case above is a real number, and it is only ever used as a real number.
    """
    try:
        import shutil

        return int(shutil.disk_usage(path).free / (1024 * 1024))
    except Exception:
        return None


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

# STEERING, NOT A BLUNT NO. Measured 2026-10-23 over 24h of live transcripts (bin/process-census,
# job exec-1792784032-4447): 1,277 tool calls were agents asking "has my branch landed yet?" in
# 418 different commands, 108 of them hand-written `for i in ...; do sleep; done` loops -- and the
# door that answers it (`bin/lane-where`) did not exist, while `bin/idp-greenlane status` (lane-wide)
# did and was used 16 times against 1,277 polls. So a plain refusal is not the fix: it would be a
# guard that rejects correct intent (R38) and leaves the agent to guess again. Each pattern here
# names the door, and the refusal returns it in `detail` so the caller's next call is the right one
# rather than a variation of the wrong one. The `_NEVER` patterns below stay blunt because there is
# no door to name: a command with no return path has no replacement, only a different shape.
_STEER = (
    (
        re.compile(r"gh\s+api\s+[^;|&]*/commits/[^;|&]*/status"),
        "bin/lane-where <branch> -- one observation, exit 0 landed / 3 pending / 4 red / 2 blind; "
        "do not poll the status API, the lane converges on its own (AGENTS.md section 2)",
    ),
    (
        re.compile(r"gh\s+api\s+[^;|&]*/check-runs"),
        "estate_invoke ci.status sha=<sha> (all check runs, failures with URLs), or bin/lane-where <branch> "
        "for the head verdict",
    ),
    (
        re.compile(r"\bgh\s+run\s+(view|list)\b"),
        "estate_invoke ci.status sha=<sha> -- it returns the failures with their URLs; `gh run view` "
        "costs a call per run and is what the census measured 261 times in 24h",
    ),
    (
        re.compile(r"\bgh\s+pr\s+checks\b"),
        "bin/lane-where <branch>",
    ),
    (
        # A shell loop that waits. The first version of this pattern was `\b(?:for|while)\b[^;|&]*\bsleep\b`,
        # which failed on the real shape that motivated it (observed live 2026-10-23):
        #   for i in $(seq 1 40); do if git log -1 --format=%s | grep -q x; then break; fi; sleep 2; done
        # `[^;|&]*` cannot cross the `;` before `do`, so the loop that was the whole point went
        # through while the cheaper `gh api` polls were caught. `.*` crosses anything but a newline.
        re.compile(r"\b(?:for|while)\b.*\bsleep\b"),
        "remove the loop: ask once (`bin/lane-where <branch>`, estate_invoke lane) and act on the verdict. "
        "A polling loop is the fourth rung no agent is allowed to invent -- measured 145 calls / 108 forms in 24h",
    ),
    (
        re.compile(r"api\.github\.com/[^\s;|&]*(?:/status|/check-runs)"),
        "bin/lane-where <branch> (or estate_invoke ci.status sha=<sha>) -- one observation, the lane "
        "converges on its own; do not poll the GitHub API",
    ),
)


def _steer_for(command: str) -> Optional[dict]:
    """The door that answers this command, when the command is a shape a door already owns.

    Returns the refusal body with the replacement in `detail`, or None. Deliberately placed BEFORE
    the ceiling and `_NEVER` checks: an agent that composed a poll loop should be told which door
    answers the question, not merely that its command was too long.
    """
    for pattern, replacement in _STEER:
        if pattern.search(command):
            return _refusal(
                "this shape already has a door: do not compose it, run the door",
                detail=replacement,
            )
    return None


def explicit_ceiling_sec(command: str) -> Optional[int]:
    """The ceiling a command sets on itself, in seconds, or None when it sets none.

    Every spelling is read. The earlier form of this check caught `timeout 150` and missed
    `timeout 2m` and `gtimeout -k 5 150` -- it parsed the `5` from `-k 5` and passed the real
    number. A rule that catches one spelling is a rule the agent steps around without meaning to.
    """
    ceiling: Optional[int] = None
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
    cwd: Optional[str] = None
    accepted_at: float = field(default_factory=time.time)
    state: str = "accepted"
    exit_code: Optional[int] = None
    log: Optional[str] = None


def _daemon_socket_path() -> str:
    """Where the executor daemon listens. Read from the environment, never a literal (LAW 46).

    The same variable the daemon itself defaults to, so the door and the thing behind it cannot
    drift to two different sockets -- a door pointing at the wrong socket answers `accepted` to
    every caller and runs nothing, which is the defect this function exists to end.
    """
    return os.environ.get(
        "IDP_EXECUTOR_SOCKET", os.path.expanduser("~/.estate/executor.sock")
    )


def _ask_daemon(request: dict, *, timeout: float = 10.0) -> dict:
    """One request, one reply over the executor's UNIX socket.

    THE DAEMON IS THE ONLY THING THAT SPAWNS. Before this function existed, `Executor.submit()`
    minted a job id, stored it in a dict, and returned -- so `execute_command` answered
    `accepted: True` and started no process at all, while the daemon's own socket path executed
    commands correctly. The sanctioned door ran nothing and reported success: a silent no-op with
    a receipt, which AGENTS.md section 8 calls a lie.

    A dead daemon is NOT a lost job and NOT a success. It raises, and the caller turns that into a
    refusal naming the fix -- because a caller that cannot tell "running" from "nobody is home"
    is the defect, not the outage.
    """
    import socket as _socket

    path = _daemon_socket_path()
    if not path or not os.path.exists(path):
        raise ConnectionRefusedError(
            f"no executor daemon at {path}; start it with bin/exec-daemon "
            f"(bin/idp-executor-status reports the socket)"
        )
    sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect(path)
        sock.sendall(json.dumps(request).encode("utf-8") + b"\n")
        raw = b""
        while b"\n" not in raw and len(raw) < 4_000_000:
            chunk = sock.recv(65536)
            if not chunk:
                break
            raw += chunk
    finally:
        sock.close()
    if not raw:
        raise ConnectionRefusedError(
            f"the executor daemon at {path} closed the connection with no reply; "
            f"check bin/idp-executor-status"
        )
    try:
        return json.loads(raw.decode("utf-8").strip())
    except (ValueError, UnicodeDecodeError) as exc:
        raise ConnectionRefusedError(
            f"the executor daemon at {path} sent an unreadable reply: {exc}"
        ) from exc


class Executor:
    """The injected runner. One method: start a command detached and return its id.

    In production this reaches the executor daemon over its UNIX socket, which is the half that
    actually spawns: the daemon applies the ceiling and starts `platform/executor/run.py`
    detached, and the job's log/exit land in `<ESTATE_RUNS>/<job_id>.{log,pid,exit}`. This class
    HOLDS NO JOB STATE of its own for exactly that reason -- a second registry in this process
    would report a job id the daemon has never heard of.

    In tests it is a stub, so every edge case is graded with no subprocess and no shell. A stub
    that overrides `submit` keeps working unchanged; only the real one talks to the socket.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._seq = 0
        # `daemon.py` serves each connection on its own thread (ThreadingUnixStreamServer,
        # daemon_threads=True), and this registry is one shared instance across all of them.
        # Measured 2026-09-14: `self._seq += 1` is LOAD/ADD/STORE, not one bytecode, so two
        # threads can read the same value before either writes it back. 3,200 concurrent
        # `execute_command` calls against the unlocked version produced 2,779 unique job ids --
        # 421 jobs silently overwrote a sibling job in `self._jobs` and vanished. A lock around
        # the id mint plus the dict write is the whole fix; no new store, no new id scheme.
        self._lock = threading.Lock()

    def submit(
        self, command: str, cwd: Optional[str] = None, ceiling_sec: int = CEILING_SEC
    ) -> Job:
        """Start the work on the daemon, and return a Job describing what was started.

        Callers that already ARE the daemon use `LocalExecutor` below, not this method, or the
        daemon opens a connection to the socket it is serving and recurses until it dies.
        """
        request: dict = {"verb": "execute", "command": command}
        if cwd:
            request["cwd"] = cwd
        if ceiling_sec:
            request["ceiling_sec"] = ceiling_sec
        try:
            reply = _ask_daemon(request)
        except ConnectionRefusedError:
            raise
        if not reply.get("ok"):
            raise RuntimeError(
                f"the executor daemon refused the command: {reply.get('error')}"
            )
        job_id = reply.get("job_id")
        if not job_id:
            raise RuntimeError(
                "the executor daemon accepted the command but returned no job id; "
                "nothing can be tracked, so nothing is reported as started"
            )
        with self._lock:
            job = Job(
                job_id=job_id,
                command=command,
                ceiling_sec=reply.get("ceiling_sec", ceiling_sec),
                cwd=cwd,
            )
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def finish(self, job_id: str, exit_code: int, log: str = "") -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.state = "finished"
            job.exit_code = exit_code
            job.log = log
        return job


_REGISTRY = Executor()


class LocalExecutor(Executor):
    """An Executor that mints jobs in THIS process instead of asking the daemon.

    FOR THE DAEMON'S OWN USE ONLY. The daemon's request handler is already the far side; if it
    used the socket-backed `submit()`, each request would open a second connection to the socket
    it is serving, and the two would wait on each other until the caller's timeout expired --
    measured 2026-09-20, the caller saw `TimeoutError` and the daemon logged the same traceback
    over and over while still reporting itself healthy.

    It is a SUBCLASS so `isinstance(x, Executor)` stays true and no type annotation changes, and
    it overrides only `submit`. Injected test stubs are unaffected: they subclass `Executor` too
    and keep their own `submit`.
    """

    def submit(
        self, command: str, cwd: Optional[str] = None, ceiling_sec: int = CEILING_SEC
    ) -> Job:
        with self._lock:
            self._seq += 1
            job = Job(
                job_id=f"exec-{int(time.time())}-{self._seq}",
                command=command,
                ceiling_sec=ceiling_sec,
                cwd=cwd,
            )
            self._jobs[job.job_id] = job
        return job


def _refusal(reason: str, *, detail: str = "", **extra) -> dict:
    out = {"accepted": False, "error": reason}
    if detail:
        out["detail"] = detail
    out.update(extra)
    return out


# ---------------------------------------------------------------------------------------------
# THE FRICTION LEDGER
#
# Why this exists: the 24h census (docs/diagnoses/2026-10-23-agent-process-friction.yaml) measured
# 1,277 polls of an answer a door already had, and separately measured that the estate's own guards
# can be unsatisfiable through this door (three commits SIGTERMed at the ceiling; a gate budgeting
# 115s inside a 100s cap, idp#7013). Both classes were found by reading transcripts afterwards.
# A number reconstructed after the fact is an audit; a number written as it happens is a metric.
#
# This ledger is the second kind: one JSON line per refusal and per ceiling kill, at the instant it
# happens, in a shape that can be counted without judgement. It is the same idea as the census
# classifier -- the shape is derived deterministically (tool name plus the first tokens of the
# first argument, with paths, SHAs and numbers placeholdered), never from a model's opinion -- so
# two identical repetitions collapse to one key and a repetition is a number rather than a memory.
#
# It is the raw material a goal/reward signal needs, and it is deliberately not a score: nothing
# here decides whether work was good, only what the door did and why. Reward logic reads this; it
# never writes it.
FRICTION_ENV = "ESTATE_FRICTION"  # a test points this at a temporary file

_SHAPE_RULES = (
    (re.compile(r"/Users/[^\s'\"]+"), "<path>"),
    (re.compile(r"(?<![\w/])/(?:[A-Za-z0-9._-]+/){2,}[A-Za-z0-9._-]*"), "<path>"),
    (re.compile(r"\b[0-9a-f]{7,40}\b"), "<sha>"),
    (re.compile(r"\b\d+\b"), "<n>"),
)


def friction_path():
    """Where the ledger lives -- read from the environment, never a literal (LAW 46)."""
    from pathlib import Path as _Path

    override = os.environ.get(FRICTION_ENV)
    if override:
        return _Path(override)
    return _Path.home() / ".estate" / "friction" / "events.jsonl"


def command_shape(command: str, tokens: int = 3, _depth: int = 0) -> str:
    """The countable identity of a command: its first `tokens` words, placeholdered.

    Deliberately blunt. `gh api repos/x/y/commits/<sha>/status` and the same call for another sha
    are one shape, because the agent's repetition is the shape and the sha is the incident.

    A LOOP IS THE WORST CASE AND GETS HANDLED EXPLICITLY. "for i in" is true of every loop and is
    therefore useless as a key: the 145 calls of `for i in ...; do sleep` in the 24h census were all
    polling the *same* question with different loop counters. So a loop's shape is the loop keyword
    plus the shape of what it repeats -- still derived from the text alone, by splitting on `do`.
    """
    words = (command or "").strip().split()
    if not words:
        return ""
    if _depth < 2 and words[0] in {"for", "while"} and " do " in f" {' '.join(words)} ":
        inner = f" {' '.join(words)} ".split(" do ", 1)[1].strip()
        return f"{words[0]} <loop> do {command_shape(inner, tokens, _depth + 1)}"[:120]
    head = " ".join(words[:tokens])
    for pattern, replacement in _SHAPE_RULES:
        head = pattern.sub(replacement, head)
    return head[:120]


def record_friction(kind: str, command: str = "", detail: str = "", **extra) -> None:
    """Append one line to the friction ledger. Best-effort by construction.

    A ledger that can refuse a command is worse than no ledger: it would put a second, uninspected
    guard in front of the door it is supposed to observe. Every failure here -- no permission, no
    disk, a serialisation error -- is swallowed, and the door's answer is unchanged either way.
    """
    try:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "kind": kind,
            "shape": command_shape(command),
        }
        if detail:
            record["detail"] = detail[:300]
        for key, value in extra.items():
            if value is not None:
                record[key] = value
        path = friction_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception:  # noqa: S110, BLE001 - observe the door, never stand in front of it
        pass


def execute_command(
    command: str,
    *,
    cwd: Optional[str] = None,
    ceiling_sec: int = CEILING_SEC,
    executor: Optional[Executor] = None,
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

    # 0b. A MACHINE WITH NO FREE SPACE CANNOT RUN A JOB, SO THE DOOR REFUSES INSTEAD OF ADDING TO IT.
    #
    #     Measured 2026-10-23 on this laptop: 197 MB free of 113 GB, 8 GB of swap exhausted, load
    #     average 476 -- and 17 pi sessions plus the executor kept accepting work, each one writing
    #     logs and state into a volume with no room, so every job was slower than the one before it.
    #     Nothing in the estate refused for lack of space. The reaper (bin/idp-disk-guard, 10 GB
    #     floor) only ever advised; scheduler/schedule.yml's ai.estate.disk-cleanup was not installed
    #     on this machine at all, so the advice was never acted on.
    #
    #     The refusal is stated in the units the caller can act on (MB free, the floor, and the one
    #     command that frees space), and the cleanup itself is let through, or the door would refuse
    #     the only call that fixes the condition it is complaining about (R38).
    free_mb = _free_mb()
    if free_mb is not None and free_mb < MIN_FREE_MB and "disk-cleanup" not in command:
        record_friction(
            "refuse-disk", command, detail=f"{free_mb} MB free, floor {MIN_FREE_MB} MB"
        )
        return _refusal(
            f"the volume has {free_mb} MB free, under this door's {MIN_FREE_MB} MB floor; a job "
            "started now makes the machine slower for every other agent running on it. Free space "
            "first -- the estate's own cleaner is the door that does it",
            detail="run: estate-execute disk-cleanup apply=true only_below_mb=10240 worktrees=true",
            free_mb=free_mb,
            floor_mb=MIN_FREE_MB,
        )

    # 1. A command whose question a door already answers is steered to that door, not merely
    # refused: the door is what makes the answer one call instead of a loop.
    steer = _steer_for(command)
    if steer:
        record_friction(
            "steer",
            command,
            detail=steer.get("detail", ""),
            reason=steer.get("reason"),
        )
        return steer

    # 2. A command with no return path is refused at the door, whatever ceiling is on it.
    for pattern in _NEVER:
        if pattern.search(command):
            record_friction("refuse-wait", command, detail=f"matched {pattern.pattern}")
            return _refusal(
                "this command waits on something outside the process; the executor runs work, it "
                "does not park an agent",
                detail=f"matched {pattern.pattern}",
            )

    # 2. The caller's own ceiling may never exceed the estate ceiling, in any spelling.
    written = explicit_ceiling_sec(command)
    if written is not None and written > CEILING_SEC:
        record_friction("refuse-ceiling", command, detail=f"written {written}s")
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

    try:
        job = executor.submit(command, cwd=resolved_cwd, ceiling_sec=effective)
    except ConnectionRefusedError as exc:
        # A DEAD DAEMON IS NOT A LOST JOB. Reporting `accepted` here would put a running node on
        # the board for work that never started, and the caller would wait on it forever. The
        # refusal names the fix, because an outage a caller cannot act on is an outage it retries
        # blindly.
        return {
            "accepted": False,
            "error": (
                f"the executor daemon is not reachable, so nothing was started: {exc}"
            ),
            "refused": True,
            "fatal": True,
            "reason": "no_daemon",
        }
    except RuntimeError as exc:
        return _refusal(str(exc))
    return {
        "accepted": True,
        "job_id": job.job_id,
        "ceiling_sec": effective,
        "note": "the turn ends here; read the outcome with read_job or the jobs page",
    }


def _runs_root():
    """Where the detached runner writes `<job_id>.log/.pid/.exit` -- read from the environment,
    never a literal (LAW 46). The same variable `platform/executor/run.py` itself reads
    (`ESTATE_RUNS`), so this reads the one file format that module already owns, rather than a
    second one invented for the MCP surface (LAW 43)."""
    from pathlib import Path as _Path

    return _Path(os.environ.get("ESTATE_RUNS") or (_Path.home() / ".estate" / "runs"))


def _sync_from_disk(job: Job, executor: Executor) -> None:
    """Bridge the detached runner's real exit file into this in-memory Job.

    Measured 2026-09-14: `Job.finish()` had no caller anywhere in this file, so `read_job`
    reported every job as `state: "accepted"` forever, with an empty log and a null exit code,
    no matter how long the real detached process the daemon started had already finished --
    the exact symptom `exec-*` job ids showed against a plain `echo`. This does not re-implement
    completion detection: it reads the SAME `<job_id>.exit` / `<job_id>.log` files
    `platform/executor/run.py`'s own `status()` already reads.
    """
    exit_path = _runs_root() / f"{job.job_id}.exit"
    if not exit_path.exists():
        return
    try:
        code = int(exit_path.read_text().strip() or 0)
    except (OSError, ValueError):
        return
    log_path = _runs_root() / f"{job.job_id}.log"
    log_text = log_path.read_text(errors="replace") if log_path.exists() else ""
    executor.finish(job.job_id, code, log_text)
    _report_failure(job.job_id, job.command, job.cwd, code, log_text)


def _report_failure(
    job_id: str, command: str, cwd: Optional[str], exit_code: int, log_text: str
) -> None:
    """Feed a failed job to the via-negativa RCA worker (Primitive D, bin/rca_worker/worker.py).

    This is the producer half of the pipeline that worker's `run_forever()` consumes: without
    it nothing ever lands on `via_negativa:failures` and the RCA worker has nothing to read,
    which was the gap measured 2026-09-15 -- the schema/guard logic worked, the ledger schema
    existed, but no caller anywhere ever XADDed a failure.

    Fire-and-forget by design, matching the proxy's own fail-open rule: a Redis outage must
    never slow down or break `read_job` on the executor's own timing budget, so this uses a
    short connect/read timeout and swallows every error rather than raising or retrying.
    Called once per job, from the one place `Executor.finish()` itself is called, so a job
    cannot be reported twice (`_sync_from_disk` only runs while `job.state == "accepted"`).
    """
    if exit_code == 0:
        return  # Primitive D learns from failures; a clean exit is not a signature to extract
    # 124 is the code this estate's supervisor records when IT killed the job at the ceiling
    # (platform/executor/run.py). That is a guard-versus-guard failure, not the command's fault, and
    # it is exactly the class that cost three commits on 2026-10-23 -- so it is counted as friction
    # at the moment it happens rather than rediscovered by reading transcripts a day later.
    if exit_code == 124:
        tail = (log_text or "").strip().splitlines()
        record_friction(
            "ceiling-kill",
            command,
            detail=(tail[-1][:200] if tail else ""),
            ceiling_sec=CEILING_SEC,
        )
    try:
        import redis  # lazy: read_job must keep working with no redis installed or reachable

        url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379")
        stream = os.environ.get("VN_FAILURE_STREAM", "via_negativa:failures")
        client = redis.from_url(url, socket_connect_timeout=0.3, socket_timeout=0.3)
        payload = {
            "command": command,
            "exit_code": exit_code,
            "stderr": log_text[-4000:],  # tail only: keep the stream entry small
            "cwd": cwd or "",
        }
        client.xadd(stream, {"payload": json.dumps(payload)})
    except Exception:  # noqa: S110, BLE001 - fail-open: running commands outranks shipping telemetry
        pass


def read_job(job_id: str, *, executor: Optional[Executor] = None) -> dict:
    """Read one job's outcome. Never waits -- a door that waits is the thing this replaces.

    TWO STORES, ONE ANSWER. When a caller injects a stub, the stub owns the outcome (every test
    in this repository). When it does not, the DAEMON owns it, because the daemon started the
    work -- a local dict would answer "no job with that id" about a job that exists, which is how
    a caller learns to distrust the door and reach for a shell instead.
    """
    if executor is None:
        # Ask the daemon first. It holds the id it minted and the process it started.
        try:
            reply = _ask_daemon({"verb": "read", "job_id": job_id}, timeout=5.0)
        except ConnectionRefusedError:
            reply = None
        if reply and reply.get("ok"):
            result = reply.get("result") or {}
            if result.get("found"):
                return result
        # The daemon did not know it either. Fall through to the local registry for the jobs a
        # caller submitted with an injected stub, so the stub surface and the real one agree.
        executor = _REGISTRY
    job = executor.get(job_id)
    if job is None:
        return {"found": False, "error": "no job with that id"}
    if job.state == "accepted":
        _sync_from_disk(job, executor)
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
    datasette, mcp
) -> None:  # pragma: no cover - exercised by the estate MCP server
    """Register the pair on the estate MCP server (ADR 0006: one interface, never a second).

    `execute_command` is the state-changing verb, so the simulate gate (`bin/idp-simulate-gate`)
    requires a propose twin under this same module. `simulate_command` is that twin: it answers
    what the executor would do with the payload -- accept or refuse, at which ceiling, from which
    directory -- without running anything.
    """

    # datasette-mcp's MCPServer.tool() (mcp==2.2.0) takes no `parameters=` kwarg: the JSON
    # schema is derived from the registered callable's own type hints (func_metadata.py), the
    # way FastMCP does it. `execute_command` and `read_job` take an injected `executor=` for
    # testability (tests/test_executor_mcp.py passes a fake); that parameter's type (`Executor`)
    # has no JSON schema, so registering those two directly makes schema generation raise at
    # import time -- the same class of crash this function is being fixed for, one call deeper.
    # These thin wrappers expose only the public, JSON-safe surface; the real functions (with
    # `executor=`) stay the ones under test.
    def execute_command_tool(
        command: str,
        cwd: Optional[str] = None,
        ceiling_sec: int = CEILING_SEC,
        mutates_live_worktree: bool = False,
    ) -> dict:
        """Run a command through the estate executor. Returns a job id in milliseconds; the turn
        ends. Every command is bounded to the estate ceiling by the executor, on the far side of
        this call. Read the outcome later with read_job. A payload that declares it mutates the
        live worktree is refused, fatally.

        Measured 2026-09-14: this used to call `execute_command()` in this process -- the MCP
        server's own interpreter, a different process than `platform/executor/daemon.py`'s, each
        with its own `_REGISTRY` in its own memory. The call minted a job id and stopped: nothing
        told the daemon to run anything, so `~/.pi/agent/bin/run`/`run.py` never started and no
        `<job_id>.exit` was ever going to appear, however long `read_job` waited. Every job the
        MCP surface accepted was structurally unable to finish. Routed onto the same socket
        `bin/idp-exec` and the verifier tools already use (`_verifier_call`, generic despite its
        name -- one request, one reply, to any verb `Handler.handle` answers) so the MCP surface
        and the command line cannot disagree about where the door is (LAW 43).
        """
        result = _verifier_call(
            {
                "verb": "execute",
                "command": command,
                "cwd": cwd,
                "ceiling_sec": ceiling_sec,
                "mutates_live_worktree": mutates_live_worktree,
            }
        )
        if result.get("unread"):
            return {
                "accepted": False,
                "error": result.get("error", "executor unreachable"),
            }
        if not result.get("ok", True) and "accepted" not in result:
            return {"accepted": False, "error": result.get("error", "refused")}
        return result

    def read_job_tool(job_id: str) -> dict:
        """Read one job's state, exit code and log. Never waits.

        Reads through the daemon socket (same fix as execute_command_tool): the job this process
        would look up locally was minted in a different process's registry and would never be
        found here.
        """
        result = _verifier_call({"verb": "read", "job_id": job_id})
        if result.get("unread"):
            return {
                "found": False,
                "error": result.get("error", "executor unreachable"),
            }
        return result.get("result", result)

    mcp.tool(name="execute_command")(execute_command_tool)
    mcp.tool(
        name="simulate_command",
        description="Answer what execute_command would do with this payload, without running it.",
    )(simulate_command)
    mcp.tool(name="read_job")(read_job_tool)

    mcp.tool(
        name="propose_patch",
        description=(
            "Propose a unified diff to an ephemeral ledger instead of writing it into the tree. "
            "Answers the ledger id; the agent is suspended pending deterministic verification. "
            "Then call verify with that ledger id."
        ),
    )(propose_patch)

    mcp.tool(
        name="simulate_patch",
        description=(
            "Answer what propose_patch would do with this payload -- whether the diff parses, to "
            "how many files, under which ledger root -- without opening a ledger."
        ),
    )(simulate_patch)

    mcp.tool(
        name="verify",
        description=(
            "Run the three-stage gauntlet over a proposed ledger: structural (the bytes compile), "
            "symbolic (Z3 over the patch's own guard) and execution (the supplied tests in a "
            "throwaway tree). The verdict is a function of the bytes. claim_verdict is VERIFIED "
            "or FAILED; the ledger is destroyed either way."
        ),
    )(verify_patch)

    mcp.tool(
        name="seal",
        description=(
            "Mint a Sigstore attestation over the exact bytes of a payload. The subject is the "
            "SHA-256 of the artifact, never of a description of it."
        ),
    )(seal_payload)

    mcp.tool(
        name="admit",
        description=(
            "Admit a sealed payload into the estate. A payload carrying no attestation from the "
            "Deterministic Verifier is intercepted with violation_code UNATTESTED and is not "
            "admitted; nothing enters without the seal."
        ),
    )(admit_payload)

    mcp.tool(
        name="propose_mutation",
        description=(
            "Propose code+manifest+SQL as one ledger spanning all three domains, instead of "
            "three unrelated calls with three unrelated verdicts. Answers a ledger id; call "
            "verify_mutation with it next. Pass `envelope` with an `inverse_spec` (ADR 0024) -- "
            "verify_mutation refuses a proposal without one."
        ),
    )(propose_mutation)

    mcp.tool(
        name="verify_mutation",
        description=(
            "Run the gauntlet (structural, SQL, symbolic, execution) over every domain in the "
            "ledger. All-or-nothing: if any domain fails, the whole mutation is unverified, and "
            "per_domain names exactly which domain failed with its own real stage message. "
            "Refuses a proposal whose envelope carries no verifiable inverse (ADR 0024), with "
            "violation_code NO_INVERSE."
        ),
    )(verify_mutation)

    mcp.tool(
        name="seal_mutation",
        description=(
            "Mint a Sigstore attestation over the whole bundle's digest. Refuses unless "
            "verify_mutation already returned admissible for this ledger id."
        ),
    )(seal_mutation)

    mcp.tool(
        name="admit_mutation",
        description=(
            "Admit an attested bundle onto a new Git branch (never main, never live), then push "
            "it and open its PR so the Greenlane can land it. Returns pr_required True always -- "
            "this verb never merges; the founder (or the Greenlane row) merges. Delivery is "
            "fail-soft: the admission stands even when the push or PR fails, and "
            "delivery_error says why."
        ),
    )(admit_mutation)

    mcp.tool(
        name="verify_inverse",
        description=(
            "Run a mutation's declared verification probe against the real machine and return "
            "its exit code -- this is what makes `verification_probe` operational rather than a "
            "string in an envelope nobody reads. Pass `probe` directly, or a `ledger_id` whose "
            "admitted envelope carries one. `executed: False` is BLIND (the probe could not "
            "run), never a pass."
        ),
    )(verify_inverse)


def simulate_command(
    command: str,
    *,
    cwd: Optional[str] = None,
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
    cwd: Optional[str],
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
    steer = _steer_for(command)
    if steer:
        reasons.append(steer)
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


def admit_payload(payload_path: str, attestation: Optional[dict] = None) -> dict:
    """Admit a sealed payload. A payload without the seal is intercepted, never admitted."""
    return _verifier_call(
        {"verb": "admit", "payload_path": payload_path, "attestation": attestation}
    )


def propose_mutation(
    code_patch: str = "",
    manifest_patch: str = "",
    sql_migration: str = "",
    tests: str = "",
    claim: str = "",
    envelope: Optional[dict] = None,
) -> dict:
    """Propose code+manifest+SQL as one ledger, never three unrelated calls.

    Spec: `docs/specs/2026-09-15-typed-multidomain-mutation-ledger-door.md`. At least one of
    the three payload fields must be non-empty; the daemon refuses an all-empty call before a
    ledger is opened. Non-blocking, same as propose_patch -- read the verdict later with
    verify_mutation, never a wait_for_verdict verb (this ticket's own "remove the verb" rule).

    `envelope` is the reversibility envelope (ADR 0024): the `inverse_spec` this mutation will
    be undone by. It may be supplied here or left None and supplied before verification, but
    `verify_mutation` refuses a proposal that has none -- see `bin/idp-reversibility-gate`.
    """
    return _verifier_call(
        {
            "verb": "propose_mutation",
            "code_patch": code_patch,
            "manifest_patch": manifest_patch,
            "sql_migration": sql_migration,
            "tests": tests,
            "claim": claim,
            "envelope": envelope,
        }
    )


def verify_mutation(ledger_id: str) -> dict:
    """Run the gauntlet over every domain in the ledger; all-or-nothing across the bundle.

    If any domain fails, ok is False for the whole mutation -- there is no reply shape where
    one domain passed and the caller can admit it alone.
    """
    return _verifier_call({"verb": "verify_mutation", "ledger_id": ledger_id})


def seal_mutation(ledger_id: str, tests: str = "", claim: str = "") -> dict:
    """Mint a Sigstore attestation over the bundle digest verify_mutation returned."""
    return _verifier_call(
        {
            "verb": "seal_mutation",
            "ledger_id": ledger_id,
            "tests": tests,
            "claim": claim,
        }
    )


def admit_mutation(ledger_id: str, attestation: Optional[dict] = None) -> dict:
    """Admit an attested bundle, push its branch, and open its PR. Never writes live, never merges.

    ADR 0025: the agent never touches git -- the gateway (this door) builds the commit, pushes
    the branch and opens the pull request, then Greenlane Row 3 proves it again before anything
    lands. pr_required is always True: this verb never merges. Delivery is fail-soft; a failure
    is reported in `delivery_error` and the admission still stands.
    """
    return _verifier_call(
        {"verb": "admit_mutation", "ledger_id": ledger_id, "attestation": attestation}
    )


def verify_inverse(
    probe: str = "",
    ledger_id: str = "",
    cwd: str = "",
) -> dict:
    """Run the declared inverse's verification probe against the real machine.

    This is what makes `verification_probe` operational: the daemon executes the command for
    real and returns its exit code, rather than the envelope being a test nobody takes. Supply
    the probe directly (finishing a rollback you just performed) or a `ledger_id` whose admitted
    envelope carries it. `executed: False` is BLIND -- the probe could not run -- and is never a
    pass (LAW 38).
    """
    payload: dict = {"verb": "verify_inverse"}
    if probe:
        payload["probe"] = probe
    if ledger_id:
        payload["ledger_id"] = ledger_id
    if cwd:
        payload["cwd"] = cwd
    return _verifier_call(payload)


if __name__ == "__main__":  # pragma: no cover - a human reading the door
    # A tiny self-check a person can run: `python3 mcp/plugins/estate_executor.py`.
    import sys

    sample = sys.argv[1] if len(sys.argv) > 1 else "git status --short"
    print(json.dumps(simulate_command(sample), indent=2))
