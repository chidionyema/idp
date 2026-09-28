# Migration runbook: launchd jobs -> Dagster estate scheduler

Written after the fact (R19 step 5 says the runbook comes first; this one was done by hand on
2026-08-24 and is recorded here so it is never done by hand again). crew#184, crew#186 CP1.

## What it changes
| Item | Before | After |
|---|---|---|
| Scheduler | 39 launchd StartInterval/StartCalendarInterval jobs, all firing at load time | one `dagster-daemon` reading `scheduler/schedule.yml` |
| UI | none | `dagster-webserver` on `127.0.0.1:$SCHEDULER_PORT` (3210, declared in `catalog/ports.yaml`) |
| State dir | none | `$DAGSTER_HOME` (`run/dagster`): `dagster.yaml`, sqlite storage, `daemon.out`, `web.out` |
| launchd | 39 jobs loaded | those 39 booted out; their plists stay in `~/Library/LaunchAgents` for rollback; `ai.estate.scheduler` supervises the daemon |
| Ledger | — | `run/migrations.jsonl`: who, when, git sha, previous-state hash, verification hash |

Env vars: `DAGSTER_HOME`, `SCHEDULER_PORT`, `MIGRATE_LAUNCHD` (0 on CI/Linux), `MIGRATE_LEDGER`, `ESTATE_TZ`.
Volumes: none. Global config touched: none. Secrets: none.

## The four verbs (`bin/scheduler-migrate`)
- `can_apply` — dagster in `.venv`, `schedule.yml` loads, `$DAGSTER_HOME` writable, port free or already ours.
- `apply` — idempotent: copies `dagster.yaml` only if changed, starts daemon/webserver only if absent, boots out only jobs still loaded. Run it twice: second run prints "already" three times and changes nothing.
- `healthcheck` — every Dagster daemon heartbeat healthy and the webserver answering, within 90 s.
- `rollback` — stops both processes and bootstraps the 39 plists back. Has been run: `bin/migration-gate bin/scheduler-migrate` runs it on every CI run, and it ran on this machine on 2026-08-24 (ledger row `verb: rollback`).

## Proof
`bin/migration-gate bin/scheduler-migrate` — pristine temp `DAGSTER_HOME`, port 3299, launchd off:
apply → healthcheck green → apply again → state identical → rollback → state equals pre-state.
It is a row of `bin/idp-ci`, so a change that breaks idempotence or rollback fails the PR.

## Manual first-time setup that remains
None on this machine. On a fresh machine: `python3 -m venv .venv && .venv/bin/pip install dagster dagster-webserver pyyaml`, then `bin/idp-install-launchd` for `ai.estate.scheduler`.
