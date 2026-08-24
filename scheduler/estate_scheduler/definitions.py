"""The estate's one scheduler. Dagster, fed by scheduler/schedule.yml.

Each entry in schedule.yml becomes one Dagster job (one op that runs the
command) and one cron schedule. What the plists could not do lives here:

  load gate        the schedule skips while the 1-minute load average is above
                   max_load_per_core x cores (2026-08-24: load 30 froze the Dock).
                   Per core, because a bare number is a claim about one machine:
                   a flat 6.0 on this 12-core laptop skipped 541 of 615 ticks in
                   3h20m and starved every backup in the estate to zero runs.
  starvation       a skipped tick never retries -- a job on `27 0,2,...` that
                   skips waits two hours for a tick that skips too. So a job
                   that has not succeeded for starve_after_periods of its own
                   cron runs anyway, load or no load, and says so on the run.
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
import time
from pathlib import Path

import yaml
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

# The load gate is expressed per core, never as a bare number. os.getloadavg()
# counts runnable threads, so the same 9.8 is a busy 2-core box and a bored
# 12-core one; a constant compares the estate's laptop against nothing. The
# ceiling is max_load_per_core x cores, and 2.0 means "twice as many runnable
# threads as cores", which is loaded but still scheduling.
CORES = os.cpu_count() or 1
LOAD_PER_CORE = float(os.environ.get("ESTATE_MAX_LOAD_PER_CORE", "2.0"))

# How many of its own cron periods a job may go without a success before the
# load gate stops applying to it. 3 periods: a job that has missed three ticks
# in a row is not being deferred any more, it is being starved.
STARVE_PERIODS = float(os.environ.get("ESTATE_STARVE_PERIODS", "3"))


# $IDP is this checkout and $CODE is the directory that holds every checkout
# (LAW 46: schedule.yml never names where either lives). Override with the
# environment; the defaults come from where this file sits.
os.environ.setdefault("IDP", str(IDP))
os.environ.setdefault("CODE", os.environ.get("CODE_ROOT", str(IDP.parent)))


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


def on_battery() -> bool:
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001 - pmset missing means not a Mac on battery
        return False
    return "discharging" in out


def _recent_statuses(instance, job_name: str, n: int) -> list[DagsterRunStatus]:
    from dagster import RunsFilter

    records = instance.get_run_records(RunsFilter(job_name=job_name), limit=n)
    return [r.dagster_run.status for r in records]


def circuit_open(instance, job_name: str) -> bool:
    recent = _recent_statuses(instance, job_name, BREAKER_TRIP)
    return len(recent) == BREAKER_TRIP and all(s == DagsterRunStatus.FAILURE for s in recent)


def cron_period_s(cron: str, tz: str, now: float | None = None) -> float | None:
    """Seconds between two consecutive firings of `cron`. None if unreadable.

    The starvation escape needs to know what "overdue" means for this job, and
    only the cron knows: two hours late is nothing to a daily backup and four
    missed ticks to a */30 guard.
    """
    try:
        from dagster._utils.schedules import cron_string_iterator

        it = cron_string_iterator(now if now is not None else time.time(), cron, tz)
        first, second = next(it), next(it)
        return (second - first).total_seconds()
    except Exception:  # noqa: BLE001 - an unreadable cron disables the escape, never the gate
        return None


def last_success_ts(instance, job_name: str) -> float | None:
    """When this job last finished successfully, or None if it never has."""
    from dagster import RunsFilter

    records = instance.get_run_records(
        RunsFilter(job_name=job_name, statuses=[DagsterRunStatus.SUCCESS]), limit=1
    )
    if not records:
        return None
    r = records[0]
    return getattr(r, "end_time", None) or getattr(r, "start_time", None)


def gate(
    label: str,
    spec: dict,
    *,
    load: float,
    cores: int,
    last_ok: float | None,
    now: float,
    battery: bool,
    circuit: bool,
    period: float | None,
):
    """Decide one tick: RunRequest or SkipReason.

    Pure on purpose -- every input is an argument, so both directions can be
    proved by a test without a Dagster instance, a busy machine or a battery.
    A guard only ever seen refusing has never been shown to permit (LAW 38),
    and this one was seen refusing 541 times in 3h20m.

    Order matters. The circuit breaker and the battery are absolute: a starving
    job still does not run on a discharging laptop, and still does not run when
    its last three attempts failed. Only the load gate can be escaped.
    """
    if circuit:
        return SkipReason(f"{label}: circuit open after {BREAKER_TRIP} failures; run it by hand to reset")
    if battery:
        return SkipReason(f"{label}: on battery")

    if spec.get("max_load") is not None:
        # A job may still name a raw number, but it has to mean it: nothing
        # writes this key automatically any more (see import_launchd.py).
        ceiling = float(spec["max_load"])
    else:
        ceiling = float(spec.get("max_load_per_core", LOAD_PER_CORE)) * cores
    if load <= ceiling:
        return RunRequest(run_key=None)

    periods = float(spec.get("starve_after_periods", STARVE_PERIODS))
    if last_ok is None:
        why = f"{label}: ran despite load {load:.1f} > {ceiling:.1f} because it has no successful run on record"
    elif period and (now - last_ok) > periods * period:
        why = (
            f"{label}: ran despite load {load:.1f} > {ceiling:.1f} because it has gone "
            f"{(now - last_ok) / period:.1f} periods without success (limit {periods:g})"
        )
    else:
        return SkipReason(
            f"{label}: load {load:.1f} > {ceiling:.1f} "
            f"({load / cores:.2f} per core, ceiling {ceiling / cores:.2f})"
        )
    return RunRequest(run_key=None, tags={"estate/starvation_escape": why})


def make_op(label: str, spec: dict):
    @op(name=f"run_{_job_name(label)}")
    def _run(context) -> None:
        cmd = [_expand(a) for a in spec["command"]]
        cwd = _expand(spec["cwd"]) if spec.get("cwd") else None
        env = dict(os.environ)
        env.update({k: _expand(v) for k, v in (spec.get("env") or {}).items()})
        escape = (getattr(getattr(context, "run", None), "tags", None) or {}).get("estate/starvation_escape")
        if escape:
            # The receipt has to carry the reason, or a run that broke its own
            # load gate looks identical to one that never had to.
            context.log.warning("starvation escape: %s", escape)
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
        if proc.returncode != 0:
            raise Failure(f"{label}: exit {proc.returncode} after {took}s")
        context.log.info("%s: exit 0 after %ss", label, took)

    return _run


def make_job(label: str, spec: dict):
    the_op = make_op(label, spec)

    # dagster/max_runtime: run monitoring cancels the run past timeout_s + 60s
    # (docs: deployment/execution/run-monitoring); dagster/priority orders the
    # queue (docs: deployment/execution/run-coordinators).
    @job(
        name=_job_name(label),
        tags={
            "estate/label": label,
            "dagster/max_runtime": str(int(spec.get("timeout_s", 1800)) + 60),
            "dagster/priority": str(int(spec.get("priority", 0))),
        },
    )
    def _job():
        the_op()

    return _job


def make_schedule(label: str, spec: dict, the_job):
    battery = bool(spec.get("skip_on_battery", False))
    cron = spec["cron"]

    @schedule(
        cron_schedule=cron,
        job=the_job,
        name=f"{_job_name(label)}_schedule",
        execution_timezone=TIMEZONE,
        default_status=DefaultScheduleStatus.RUNNING,
    )
    def _sched(context):
        now = time.time()
        return gate(
            label,
            spec,
            load=load1(),
            cores=CORES,
            last_ok=last_success_ts(context.instance, the_job.name),
            now=now,
            battery=battery and on_battery(),
            circuit=circuit_open(context.instance, the_job.name),
            period=cron_period_s(cron, TIMEZONE, now),
        )

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
        if circuit_open(context.instance, the_job.name):
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
