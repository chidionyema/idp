# Onboarding: the estate scheduler (Dagster)

Standard: STANDARDS.md row 45 — Dagster 1.13 OSS used natively; launchd supervises two Dagster
processes and nothing else. crew#184. Docs: https://docs.dagster.io/ (each feature below cites its page).

## Layout (production, not `dagster dev`)
`dagster dev` is documented as local-development only. The estate runs the two supervised processes
the docs prescribe, both under one `DAGSTER_HOME` (`$IDP/run/dagster`):

| Process | Started by | Log |
|---|---|---|
| `dagster-daemon run` — schedules, sensors, run queue, run monitoring | `bin/scheduler-up` via launchd `ai.estate.scheduler` (every 10 min, idempotent) | `run/dagster-daemon.out` |
| `dagster-webserver -h 127.0.0.1 -p 3210` — the dashboard | same | `run/dagster-web.out` |

Instance config: `scheduler/dagster.yaml` (copied into `DAGSTER_HOME` by `scheduler-up`). Storage is the
SQLite default under `DAGSTER_HOME`; the documented escalation if lock contention appears is
`dagster-postgres` (docs: deployment/oss/dagster-yaml).

## Features in use and where each is set
| Feature | Where | Doc |
|---|---|---|
| Cron schedule per job, laptop-local time (`execution_timezone`, env `ESTATE_TZ`) | `definitions.py make_schedule` | guides/automate/schedules |
| Schedules and sensors ON by default (`default_status=RUNNING`) | `definitions.py` | guides/automate/schedules |
| Skip with a reason: `max_load_per_core` x cores, or an explicit `max_load` (1-min load), `skip_on_battery` | `schedule.yml` per job; `SkipReason` | guides/automate/schedules |
| Circuit breaker: 3 consecutive failures → tick skipped until run by hand | `definitions.py circuit_open` | — (estate rule) |
| Dependencies: `after: <job>` runs on upstream SUCCESS | `run_status_sensor` | guides/automate/sensors |
| Failure log `run/scheduler-failures.jsonl` | `run_failure_sensor estate_failure_log` | guides/automate/sensors |
| Run queue: 2 concurrent runs, `dagster/priority` tag from `priority:` | `dagster.yaml run_coordinator`; job tags | deployment/execution/run-coordinators |
| Runtime cap: `timeout_s` → subprocess timeout and `dagster/max_runtime` tag | `make_op`, `make_job` | deployment/execution/run-monitoring |
| One automatic retry, then the breaker | `dagster.yaml run_retries` | deployment/execution/run-retries |
| Tick retention 30/7 days | `dagster.yaml retention` | deployment/oss/dagster-yaml |
| Telemetry off | `dagster.yaml telemetry` | about/telemetry |
| Description on every job, op and schedule, derived from the target script's docstring | `estate_scheduler/describe.py`; `make_job`, `make_op`, `make_schedule` | concepts/ops-jobs-graphs |
| Metadata on every job: command, cron, timeout, cwd, what it skips on, which file described it | `_job_metadata` | concepts/metadata-tags |
| Owner tag `estate/owner` from the label's second segment, so the UI filters by owner | `make_job` | concepts/metadata-tags |

Not used, and why: Declarative Automation and asset freshness policies are for data assets, not
shell jobs; Alerts and Insights are Dagster+ only — the failure sensor is the OSS path.

## Dashboard — http://127.0.0.1:3210
- **Overview → Timeline**: every run of every job on one time axis; the load storm would show as 39 bars starting together.
- **Overview → Schedules / Sensors**: on/off toggles, next tick, tick history with each `SkipReason` (load, battery, circuit open).
- **Runs**: filter by job or status; a run opens to its stdout/stderr and the Gantt of the step.
- **Deployment → Daemons**: heartbeat of each daemon; this is what `bin/scheduler-status` reads.
- **Deployment → Code locations**: press Reload after editing `schedule.yml` or `definitions.py`; no restart needed.

## Add a job
1. Add an entry to `scheduler/schedule.yml`: `cron`, `command` (list), `max_load`, `skip_on_battery`,
   `timeout_s`, optional `after`, `priority`, `cwd`, `env`. Paths use `$IDP`, `$CODE` or `~`; never a
   literal home or checkout directory (LAW 46, enforced by `bin/idp-ci`).
2. Give the script a module docstring whose first paragraph says what the job does. That paragraph is
   the description the dashboard shows, so there is nothing to write here and nothing to keep in step;
   whoever changes the behaviour edits the sentence. A job whose script has no docstring is refused by
   `bin/idp-verify`, and the dashboard names the file to fix. A command that is not a script we own
   (`/bin/echo`, a vendor binary) may carry `description:` in `schedule.yml` instead.
3. Reload the code location in the dashboard (or `bin/scheduler-down && bin/scheduler-up`).
4. It is on. Nothing else to start.

Check what the dashboard will show before you reload:

    cd scheduler && python3 -m estate_scheduler.describe

## Move a job off launchd
`bin/scheduler-import` prints every scheduled launchd job as YAML. Paste the entry, reload, then
`launchctl bootout gui/$(id -u)/<label>`. Keep the plist in claude-guards until the Dagster run has been green once.

## Known limits (from the docs)
- Non-partitioned schedules do not catch up ticks missed while the laptop slept; the next cron tick runs.
- `DefaultRunLauncher` cannot detect a crashed run worker; the runtime cap is the protection.
- SQLite is single-writer; watch `run/dagster-daemon.out` for lock timeouts.

## Definition of done
`bin/scheduler-status` exits 0: every Dagster daemon healthy and at least one tick in the last 10 minutes.

## Code locations from other repos (crew#140)

`scheduler/workspace.yaml` is the list. Every entry is a path relative to that directory, so
`..` is this checkout and `../..` is the directory that holds every checkout; no entry names
a machine or a home (LAW 46).

| location | file | what it declares |
|---|---|---|
| `estate-scheduler` | `scheduler/estate_scheduler/definitions.py` | one job and one cron per row of `schedule.yml` |
| `estate-facts` | `../../crew/science/scheduler/estate_dagster/facts.py` | one asset per source in `crew/science/sources.json`, each with the freshness window that file declares; observed every 15 minutes |

`bin/scheduler-up` imports both before it starts anything and refuses, with the location named,
if either does not load; on a running webserver it reloads the workspace and
`scheduler/reload_check.py` refuses a location that came back as a `PythonError`. To add a
third location: one entry here, one load line in `bin/scheduler-up`, and the package's
dependencies must install on this venv's interpreter (`dagster-dbt` does not on Python 3.14,
which is why the crew dbt model is not registered).
