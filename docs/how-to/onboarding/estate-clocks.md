# Onboarding: estate-clocks

`bin/estate-clocks` writes `docs/scheduling/CLOCKS.md`, the one page that answers "what runs on a
clock, where, and when" — so nobody reads twenty source files to find out.

## Inputs

| Input | Where | What it gives |
|---|---|---|
| the schedule file | `scheduler/schedule.yml` | every Dagster job: its cron, where it runs, its command |
| every timed cluster job | `platform/**/*.yaml` (`kind: CronJob`) | its schedule and its first comment line, which must say what it does in plain words |
| every timed workflow | `.github/workflows/*.yml` with `on.schedule` | the jobs GitHub runs on a clock |

## To add a clock

1. Define the job in one of the three sources above, with a plain-words description.
2. Run `bin/estate-clocks`.
3. Commit the regenerated page together with your change — the test refuses a page that no longer matches its sources.

## Tests

    python3 -m pytest -q tests/test_clocks_table_matches_sources.py

The suite renders the table from the sources and fails when the file on disk differs, so the page
cannot be hand-edited or left stale.
