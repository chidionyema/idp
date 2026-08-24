"""The estate's one scheduler. Dagster, fed by scheduler/schedule.yml.

Each entry in schedule.yml becomes one Dagster job (one op that runs the
command) and one cron schedule. What the plists could not do lives here:

  max_load         the schedule skips, with a reason, while the 1-minute load
                   average is above it (2026-08-24: load 30 froze the Dock)
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
SCHEDULE_FILE = Path(os.environ.get("ESTATE_SCHEDULE", IDP / "scheduler" / "schedule.yml"))
FAILURE_LOG = IDP / "run" / "scheduler-failures.jsonl"
BREAKER_TRIP = 3


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


def make_op(label: str, spec: dict):
    @op(name=f"run_{_job_name(label)}")
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
        if proc.returncode != 0:
            raise Failure(f"{label}: exit {proc.returncode} after {took}s")
        context.log.info("%s: exit 0 after %ss", label, took)

    return _run


def make_job(label: str, spec: dict):
    the_op = make_op(label, spec)

    @job(name=_job_name(label), tags={"estate/label": label})
    def _job():
        the_op()

    return _job


def make_schedule(label: str, spec: dict, the_job):
    max_load = float(spec.get("max_load", 6.0))
    battery = bool(spec.get("skip_on_battery", False))

    @schedule(cron_schedule=spec["cron"], job=the_job, name=f"{_job_name(label)}_schedule")
    def _sched(context):
        current = load1()
        if current > max_load:
            return SkipReason(f"{label}: load {current:.1f} > max_load {max_load}")
        if battery and on_battery():
            return SkipReason(f"{label}: on battery")
        if circuit_open(context.instance, the_job.name):
            return SkipReason(f"{label}: circuit open after {BREAKER_TRIP} failures; run it by hand to reset")
        return RunRequest(run_key=None)

    return _sched


def make_dependency_sensor(label: str, spec: dict, the_job, upstream_job):
    @run_status_sensor(
        name=f"{_job_name(label)}_after_{upstream_job.name}",
        run_status=DagsterRunStatus.SUCCESS,
        monitored_jobs=[upstream_job],
        request_job=the_job,
    )
    def _after(context):
        if circuit_open(context.instance, the_job.name):
            return SkipReason(f"{label}: circuit open")
        return RunRequest(run_key=context.dagster_run.run_id)

    return _after


@run_failure_sensor(name="estate_failure_log")
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
