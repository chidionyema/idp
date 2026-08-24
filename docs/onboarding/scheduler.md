# Onboarding: the estate scheduler (Dagster)

Standard: STANDARDS.md row 45 — Dagster used natively; launchd is the substrate's supervisor, not the estate's scheduler. crew#184.

## Add a job
1. Add an entry to `scheduler/schedule.yml` (cron, command, max_load, skip_on_battery, timeout_s, optional `after`). Paths use `~`, never a literal home directory.
2. `bin/scheduler-up` reloads nothing by itself: the daemon re-reads the code location on its next tick; to be sure, `bin/scheduler-down && bin/scheduler-up`.
3. New schedules start switched off. `cd scheduler && ../.venv/bin/dagster schedule start -w workspace.yaml <name>_schedule` (names: dots and dashes become underscores).

## Move a job off launchd
`bin/scheduler-import` prints every scheduled launchd job as YAML. Paste the entry, start its schedule, then `launchctl bootout gui/$(id -u)/<label>`. Keep the plist in claude-guards until the Dagster run has been green once.

## Where things are
- Policy: `scheduler/schedule.yml`
- Code: `scheduler/estate_scheduler/definitions.py`
- Instance: `run/dagster/` (sqlite; `run/dagster.yaml` copied from `scheduler/dagster.yaml`)
- Logs: `run/dagster-daemon.out`, `run/dagster-web.out`, failures in `run/scheduler-failures.jsonl`
- UI: http://127.0.0.1:3210

## Definition of done
`bin/scheduler-status` exits 0: every Dagster daemon healthy and at least one schedule tick in the last 10 minutes.
