"""The estate's one scheduler. Dagster, fed by scheduler/schedule.yml.

Each entry in schedule.yml becomes one Dagster job (one op that runs the
command) and one cron schedule. What the plists could not do lives here:

  load gate        the schedule skips, with a reason, while the 1-minute load
                   average is above max_load_per_core x cores (default 2.0;
                   2026-08-24: load 30 froze the Dock). Per core, because a bare
                   number describes one machine: a flat 6.0 on this 12-core Mac
                   skipped 3836 ticks in 24h and ran nothing for 16 hours
                   (crew#85, 2026-08-27). An explicit max_load still wins.
  skip_on_battery  the schedule skips while the Mac is discharging
  after            a run_status_sensor starts this job when the named job
                   succeeds; the cron on such a job is optional
  circuit breaker  three consecutive failures open the circuit and the schedule
                   skips until someone launches the job by hand and it passes
  concurrency      run/dagster.yaml queues runs, max 2 at once, so 30 jobs can
                   never fire in the same second again
  one log          every run's stdout/stderr is in the Dagster UI and
                   logs/scheduler-failures.jsonl records every failure

Nothing here names a machine: paths in schedule.yml use ~ and are expanded at
run time (LAW 46).
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import yaml

try:
    from .load_gate import CORES, load_ceiling, load_verdict
except ImportError:  # loaded as a bare file, not a package (dagster -f definitions.py)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from load_gate import CORES, load_ceiling, load_verdict  # type: ignore[no-redef]
from dagster import (
    DagsterRunStatus,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    Definitions,
    Failure,
    OpExecutionContext,
    RunFailureSensorContext,
    RunRequest,
    RunStatusSensorContext,
    ScheduleEvaluationContext,
    SkipReason,
    job,
    op,
    run_failure_sensor,
    run_status_sensor,
    schedule,
)

IDP = Path(__file__).resolve().parents[2]
# Dagster schedules run in UTC unless told otherwise (docs: guides/automate/schedules).
# The launchd crons these replaced were laptop-local, so every schedule is too.
TIMEZONE = os.environ.get("ESTATE_TZ", "Europe/London")
SCHEDULE_FILE = Path(os.environ.get("ESTATE_SCHEDULE", IDP / "scheduler" / "schedule.yml"))
FAILURE_LOG = IDP / "run" / "scheduler-failures.jsonl"
BREAKER_TRIP = 3


# $IDP is this checkout and $CODE is the directory that holds every checkout
# (LAW 46: schedule.yml never names where either lives). Override with the
# environment; the defaults come from where this file sits.
os.environ.setdefault("IDP", str(IDP))
os.environ.setdefault("CODE", os.environ.get("CODE_ROOT", str(IDP.parent)))


# workspace.yaml loads this file by path, so it is a top-level module and not a
# package member, and the working directory it resolves imports against is not
# ours to choose -- the running webserver resolved them against a directory
# that does not exist. Put this file's own directory on the path and the import
# works under any of them.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from .describe import describe as describe_job
except ImportError:  # loaded as a file, not as a package member
    from describe import describe as describe_job


def _expand(s: str) -> str:
    return os.path.expandvars(os.path.expanduser(s))


def load_spec() -> dict[str, dict]:
    with open(SCHEDULE_FILE) as f:
        data = yaml.safe_load(f) or {}
    return data.get("jobs") or {}


def _job_name(label: str) -> str:
    return label.replace(".", "_").replace("-", "_")


def load1() -> float:
    return os.getloadavg()[0]


def load_gate(label: str, spec: dict, current: float, cores: int = CORES) -> SkipReason | None:
    why = load_verdict(label, spec, current, cores)
    return SkipReason(why) if why else None


def on_battery() -> bool:
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001 - pmset missing means not a Mac on battery
        return False
    return "discharging" in out


SPEC_HASH_TAG = "estate/spec-hash"


def spec_hash(spec: dict) -> str:
    """Twelve hex chars over the row as schedule.yml states it, so a run carries which
    version of the row it executed."""
    import hashlib

    return hashlib.sha256(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _recent_statuses(instance, job_name: str, n: int, tags: dict | None = None) -> list[DagsterRunStatus]:
    from dagster import RunsFilter

    records = instance.get_run_records(RunsFilter(job_name=job_name, tags=tags or None), limit=n)
    return [r.dagster_run.status for r in records]


def circuit_open(instance, job_name: str, current_hash: str | None = None) -> bool:
    """Three consecutive failures of the row AS IT NOW STANDS open the breaker.

    crew#539 (2026-08-28, 09cd04a6 measured from run/dagster/schedules/schedules.db): 24 jobs
    sat circuit-open, some since 2026-08-25 02:30. com.estate.costsentinel tripped on exit 1
    before ok_exit [1] landed (crew#85); the fix landed, the breaker never re-closed, and the
    row stayed dark for 18 hours until a person launched it by hand. A run records the
    spec_hash of the row it executed; failures under an older hash belong to a row that no
    longer exists and do not count. Editing the row in schedule.yml is the reset.
    """
    tags = {SPEC_HASH_TAG: current_hash} if current_hash else None
    recent = _recent_statuses(instance, job_name, BREAKER_TRIP, tags)
    return len(recent) == BREAKER_TRIP and all(s == DagsterRunStatus.FAILURE for s in recent)


def exit_is_ok(spec: dict, returncode: int) -> bool:
    """0, or a code the job declares in ``ok_exit`` as "ran fine, found something".

    crew#85 (2026-08-27): com.estate.costsentinel exits 1 to say "spend warning" and
    ai.estate.sovereign-self-check exits 1 to say "enforced an action". Three of those in a
    row opened the circuit breaker, so each sentinel went silent exactly when it had
    something to say. Same split as hc-wrap.sh HC_FINDINGS_EXIT: a crash is any code not
    declared here and still trips the breaker.
    """
    return returncode == 0 or returncode in set(spec.get("ok_exit") or [])


def make_op(label: str, spec: dict):
    text, _ = describe_job(label, spec)

    @op(name=f"run_{_job_name(label)}", description=text)
    def _run(context) -> None:
        cmd = [_expand(a) for a in spec["command"]]
        cwd = _expand(spec["cwd"]) if spec.get("cwd") else None
        env = dict(os.environ)
        env.update({k: _expand(v) for k, v in (spec.get("env") or {}).items()})
        context.log.info("exec %s", shlex.join(cmd))
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=int(spec.get("timeout_s", 1800))
            )
        except subprocess.TimeoutExpired as e:
            raise Failure(f"{label}: timed out after {spec.get('timeout_s', 1800)}s") from e
        took = round(time.time() - t0, 1)
        if proc.stdout:
            context.log.info(proc.stdout[-20000:])
        if proc.stderr:
            context.log.warning(proc.stderr[-20000:])
        if not exit_is_ok(spec, proc.returncode):
            raise Failure(f"{label}: exit {proc.returncode} after {took}s")
        context.log.info("%s: exit %s after %ss", label, proc.returncode, took)

    return _run


def _job_metadata(label: str, spec: dict, source: str) -> dict:
    """The facts a person opening the Dagster UI needs before they touch a job.

    Everything here is read from schedule.yml, so it cannot drift from what
    actually runs the way a hand-written note would.
    """
    md = {
        "command": shlex.join([str(a) for a in spec["command"]]),
        "described by": source or "nothing -- see the description",
        "defined in": "scheduler/schedule.yml",
        "timeout": f"{int(spec.get('timeout_s', 1800))}s",
    }
    if spec.get("cron"):
        md["cron"] = f"{spec['cron']} ({TIMEZONE})"
    if spec.get("after"):
        md["runs after"] = spec["after"]
    if spec.get("cwd"):
        md["cwd"] = str(spec["cwd"])
    md["skipped when"] = _skip_note(spec)
    return md


def _skip_note(spec: dict) -> str:
    parts = [f"1-minute load average is above {load_ceiling(spec):.1f} ({CORES} cores)"]
    if spec.get("skip_on_battery"):
        parts.append("the laptop is on battery")
    parts.append(f"the breaker is open after {BREAKER_TRIP} consecutive failures")
    return "; ".join(parts)


def make_job(label: str, spec: dict):
    the_op = make_op(label, spec)
    text, source = describe_job(label, spec)

    # dagster/max_runtime: run monitoring cancels the run past timeout_s + 60s
    # (docs: deployment/execution/run-monitoring); dagster/priority orders the
    # queue (docs: deployment/execution/run-coordinators).
    @job(
        name=_job_name(label),
        description=text,
        metadata=_job_metadata(label, spec, source),
        tags={
            "estate/label": label,
            "estate/owner": label.split(".")[1] if label.count(".") >= 2 else label.split(".")[0],
            "dagster/max_runtime": str(int(spec.get("timeout_s", 1800)) + 60),
            "dagster/priority": str(int(spec.get("priority", 0))),
            SPEC_HASH_TAG: spec_hash(spec),
        },
    )
    def _job():
        the_op()

    return _job


def make_schedule(label: str, spec: dict, the_job):
    battery = bool(spec.get("skip_on_battery", False))

    text, _ = describe_job(label, spec)

    @schedule(
        cron_schedule=spec["cron"],
        job=the_job,
        name=f"{_job_name(label)}_schedule",
        description=(f"{spec['cron']} in {TIMEZONE}. {text} "
                     f"Skipped when {_skip_note(spec)}."),
        execution_timezone=TIMEZONE,
        default_status=DefaultScheduleStatus.RUNNING,
    )
    def _sched(context):
        skip = load_gate(label, spec, load1())
        if skip is not None:
            return skip
        if battery and on_battery():
            return SkipReason(f"{label}: on battery")
        if circuit_open(context.instance, the_job.name, spec_hash(spec)):
            return SkipReason(f"{label}: circuit open after {BREAKER_TRIP} failures of this row; edit the row or run it by hand to reset")
        return RunRequest(run_key=None)

    return _sched


def make_dependency_sensor(label: str, spec: dict, the_job, upstream_job):
    @run_status_sensor(
        name=f"{_job_name(label)}_after_{upstream_job.name}",
        run_status=DagsterRunStatus.SUCCESS,
        monitored_jobs=[upstream_job],
        request_job=the_job,
        default_status=DefaultSensorStatus.RUNNING,
    )
    def _after(context):
        if circuit_open(context.instance, the_job.name, spec_hash(spec)):
            return SkipReason(f"{label}: circuit open")
        return RunRequest(run_key=context.dagster_run.run_id)

    return _after


@run_failure_sensor(name="estate_failure_log", default_status=DefaultSensorStatus.RUNNING)
def estate_failure_log(context):
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "job": context.dagster_run.job_name,
        "run_id": context.dagster_run.run_id,
        "message": (context.failure_event.message or "")[:500],
    }
    with open(FAILURE_LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def build() -> Definitions:
    spec = load_spec()
    jobs, schedules, sensors = {}, [], [estate_failure_log]
    # A row graded `runs_on: retire` (crew#516) has left the Mac; it gets no job and no
    # schedule. crew#539: ai.idp.reconcile kept ticking retired and failing exit 2.
    spec = {label: s for label, s in spec.items() if s.get("runs_on") != "retire"}
    for label, s in spec.items():
        jobs[label] = make_job(label, s)
    for label, s in spec.items():
        if s.get("cron"):
            schedules.append(make_schedule(label, s, jobs[label]))
        if s.get("after"):
            up = s["after"]
            if up not in jobs:
                raise ValueError(f"{label}: after={up!r} is not a job in {SCHEDULE_FILE}")
            sensors.append(make_dependency_sensor(label, s, jobs[label], jobs[up]))
    return Definitions(jobs=list(jobs.values()), schedules=schedules, sensors=sensors)


defs = build()
