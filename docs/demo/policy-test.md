# Demo: policy-test

`bin/policy-test` runs `conftest` over six fixtures and checks each one's exit
code against what it should be — three that must pass, three that must fail.
It exists because LAW 38 (a guard that refuses correct work is an outage)
means a policy is only proved once it is shown to say yes to good work and no
to bad work, not just no.

```
$ bin/policy-test
FIXTURE               EXPECT   GOT      PROVES
--------------------- -------- -------- ------
clean.json             0        0        allows an ordinary permissive tree, including packages with no licence metadata
sell-blocking.json     1        1        refuses AGPL, SSPL, BUSL, Elastic, non-commercial CC and Commons Clause
broken-scan.json       1        1        refuses a full parts list with no terms in it, instead of calling it clean
placement-ok.json      0        0        allows short-interval desk jobs that are monitored and awake-hours only
placement-misplaced.json 1      1        refuses sleep-window schedules, never-pinged jobs and survival work on a laptop
placement-blind.json   1        1        refuses a monitored job whose check could not be read, so a monitoring outage cannot read as a pass

PASS      every policy allows its good case and refuses its bad ones
```

A row whose GOT does not match EXPECT prints `<-- WRONG` beside it, followed
by `conftest`'s own output for that fixture, and the run exits 1. There is no
bespoke test harness here: `conftest` is what runs the policy in production,
so it is what proves the policy here as well — a hand-rolled evaluator would
be testing a copy of the real rule engine, not the rule engine itself.
