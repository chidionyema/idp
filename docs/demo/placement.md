# Placement audit — what it looks like when it runs

Real output, captured 2026-08-24 on this machine. Nothing here is illustrative.

## Grading every loaded launchd job

```
$ bin/placement-audit
inventory  43 estate jobs, 34 monitored, 11 of those have never pinged -> reports/placement.json

WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.architect.gateway is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.consultd is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.deepseek-bridge is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.dep-alerts runs every 24h on a laptop. Measured 2026-08-24: 7 of 10 daily jobs here had never run. Confirm this one is meant to be a desk job.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.kimi-bridge is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.hermes.gateway is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.hermes.runaway-reaper is scheduled but not wrapped in hc-wrap.sh, so nothing notices when it stops. An instrument nobody reads is not an instrument.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.chidionyema.maestro is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.founder.boardserve is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.estate-inventory runs every 24h on a laptop. Measured 2026-08-24: 7 of 10 daily jobs here had never run. Confirm this one is meant to be a desk job.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.restore-drill runs every 24h on a laptop. Measured 2026-08-24: 7 of 10 daily jobs here had never run. Confirm this one is meant to be a desk job.
WARN - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.scheduler is a long-running service on a laptop. Anything depending on it is depending on the lid being open.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.dep-alerts (check 'dep-alerts') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.drills (check 'drills') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.drills is scheduled in the 4 o'clock hour and this machine is asleep then. It belongs on a host that stays awake.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.key-escrow (check 'key-escrow') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.key-escrow is scheduled in the 5 o'clock hour and this machine is asleep then. It belongs on a host that stays awake.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - ai.estate.key-escrow is survival work (backup, restore drill or key escrow) and it runs only here. If this laptop is what fails, it was never running.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.chidionyema.graphify-sweep (check 'graphify-sweep') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.chidionyema.guard-selftest (check 'guard-selftest') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.chidionyema.guard-selftest is scheduled in the 7 o'clock hour and this machine is asleep then. It belongs on a host that stays awake.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.estate.bundlepush (check 'estate-bundlepush') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.estate.restic-backup is scheduled in the 3 o'clock hour and this machine is asleep then. It belongs on a host that stays awake.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.estate.restic-backup is survival work (backup, restore drill or key escrow) and it runs only here. If this laptop is what fails, it was never running.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.founder.stuckdetector (check 'stuckdetector') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.backup (check 'prospector-backup') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.backup is scheduled in the 3 o'clock hour and this machine is asleep then. It belongs on a host that stays awake.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.backup is survival work (backup, restore drill or key escrow) and it runs only here. If this laptop is what fails, it was never running.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.offsite-backup (check 'offsite-backup') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.offsite-backup is scheduled in the 3 o'clock hour and this machine is asleep then. It belongs on a host that stays awake.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.offsite-backup is survival work (backup, restore drill or key escrow) and it runs only here. If this laptop is what fails, it was never running.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.process-audit (check 'process-audit') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.restore-drill (check 'restore-drill') has never pinged. It is not late -- it has never run.
FAIL - /Users/chidionyema/dev/code/idp/reports/placement.json - main - com.prospector.restore-drill is survival work (backup, restore drill or key escrow) and it runs only here. If this laptop is what fails, it was never running.

34 tests, 0 passed, 12 warnings, 22 failures, 0 exceptions

FAIL       jobs are placed on hardware that cannot honour their schedule -- see above
           docs/placement.md says where each class belongs and why
```

Twenty-two failures and twelve warnings across forty-three jobs. The three
deny rules each fire on a real job: a schedule inside the hours the laptop is
asleep, a monitored check that has never received a single ping, and survival
work whose only schedule is on the machine it is meant to protect. Several
jobs trip more than one, which is the point — `com.prospector.offsite-backup`
is booked for the 3 o'clock hour, has never pinged, and is the backup.

Warnings are the judgements: eight KeepAlive services that work while the lid
is open, three daily jobs that could legitimately be desk jobs, and one
scheduled job nobody is monitoring at all.

## Proving the rules allow correct work as well as refusing bad

```
$ bin/policy-test
FIXTURE              EXPECT   GOT      PROVES
-------------------- -------- -------- ------
clean.json           0        0        allows an ordinary permissive tree, including packages with no licence metadata
sell-blocking.json   1        1        refuses AGPL, SSPL, BUSL, Elastic, non-commercial CC and Commons Clause
broken-scan.json     1        1        refuses a full parts list with no terms in it, instead of calling it clean
placement-ok.json    0        0        allows short-interval desk jobs that are monitored and awake-hours only
placement-misplaced.json 1        1        refuses sleep-window schedules, never-pinged jobs and survival work on a laptop

PASS      every policy allows its good case and refuses its bad ones
```

The first two placement fixtures are the pair that matters. `placement-ok.json`
is five short-interval desk jobs, all monitored, none in the sleep window, and
it must exit 0 — a guard that refuses correct work is an outage, not a false
positive. `placement-misplaced.json` carries one job per deny rule, so a rule
that silently stops firing shows up here rather than in production.
