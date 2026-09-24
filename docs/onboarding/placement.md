# What runs on the laptop, what runs on a server, and why the schedules keep missing

## The short answer

The schedules are not missing because the jobs are broken. They are missing
because a MacBook sleeps and roughly half the estate's scheduled work is booked
for hours when the lid is shut.

Measured 2026-08-24 against the live Healthchecks instance at
`http://127.0.0.1:8000`, 35 checks:

| | total | never pinged once |
|---|---|---|
| daily jobs (period ≥ 12h) | 10 | **7** |
| sub-daily jobs (period < 12h) | 25 | 4 |

Same wrapper, same machine, same scripts. The only thing that differs between
the two rows is whether the schedule lands inside the hours somebody has the
laptop open. Seven daily jobs have never run at all — they are not late, and
repairing any one of them individually fixes nothing, which is why this keeps
coming back.

The second angle agrees. `pmset -g log` shows this Mac entering Maintenance
Sleep repeatedly through the night and staying there; on 2026-08-22 it slept
through 08:57, 09:58, 10:33, 10:59 and 12:00, waking for six to thirteen seconds
at a time. The night jobs are booked at 03:30, 03:40, 03:50, 04:30, 05:10 and
07:15.

## The second thing being called a missed schedule, which is not one

Ten checks currently read **down** having pinged within the last hour. Those did
not miss anything. `hc-wrap.sh` reports the wrapped job's exit code, so a
non-zero exit is recorded as a failure ping and the check goes red. That is a
job that ran and failed, and it needs a different repair entirely.

Cross-checked against `launchctl list`, which reports last exit status
independently: `com.founder.board`, `com.estate.costsentinel`,
`com.prospector.estate-inventory`, `com.prospector.launchd-held`,
`com.prospector.log-rotation` and `com.founder.sciencecollect` all show status
`1` there and `down` in Healthchecks. Two instruments, same answer.

Conflating "never ran" with "ran and failed" under one phrase is most of why
this has stayed open. They are counted separately from here on.

## Host classes

Three, and a job belongs to exactly one.

### Desk — this MacBook

**What it is honest for.** Work whose subject is the laptop itself, or the
session running on it. If the machine is asleep, there is nothing to measure and
nothing is lost by not measuring it.

Friction relay, tracked-guard, downshift, reflect, the IDP refresh, stuck
detector, law writer, cost sentinel. All short-interval, all monitored, all
pointless on a machine nobody is sitting at.

**What it is not honest for.** Anything with a fixed clock time, anything daily,
and anything whose whole purpose is to survive this laptop being lost.

### Always-on — a host that does not sleep

**What belongs here.** Everything with a calendar schedule, everything daily,
and all survival work without exception:

- `com.estate.restic-backup` (03:30)
- `com.prospector.backup` (03:40)
- `com.prospector.offsite-backup` (03:50)
- `ai.estate.drills` (04:30)
- `ai.estate.key-escrow` (05:10)
- `com.chidionyema.guard-selftest` (07:15 and 19:15)
- `ai.estate.dep-alerts` (08:10)
- `com.prospector.restore-drill` (daily)
- `com.prospector.process-audit`
- `com.estate.bundlepush`

A backup that runs only on the machine it is backing up protects nothing at the
moment that machine is the thing that failed. That is not a scheduling
preference, it is the definition of the job.

**Where.** Not decided here. Picking the host is a spending and architecture
decision and it is the founder's (LAW 11). What this document fixes is which
jobs need one, so the decision is about hosting rather than about triage.

### Long-running services — currently on the desk, and shouldn't be

Eight KeepAlive processes serve something other sessions or the founder read:
`ai.architect.gateway`, `ai.hermes.gateway`, `com.chidionyema.maestro`,
`com.founder.boardserve`, `ai.estate.consultd`, `ai.estate.deepseek-bridge`,
`ai.estate.kimi-bridge`, `com.prospector.scheduler`.

Each is fine as a development convenience and wrong as a dependency. Anything
that expects one of them to answer is expecting the lid to be open. They are
reported as warnings rather than failures because whether a given one is a dev
tool or a dependency is a judgement, not a measurement.

## How this is enforced rather than remembered

A document nobody re-reads is not a control. The rules above are written as
policy and run as a command:

```
bin/placement-audit
```

It reads every loaded launchd job, works out when each wants to run, joins it to
its Healthchecks record, and grades the result against `policy/placement.rego`.
Refusals are hard failures; judgements are warnings. As of 2026-08-24 it reports
**22 failures and 12 warnings across 43 jobs**.

It reads and changes nothing. Moving a job has a blast radius and is not a
script's decision to make.

The policy has paired controls, because a gate that has only been tested on the
bad case is a gate nobody has proved is safe to install (LAW 38):

```
bin/policy-test
```

`policy/fixtures/placement-ok.json` is correct placement and must pass.
`policy/fixtures/placement-misplaced.json` carries one job per deny rule and
must fail.

## What it costs

**£0 / $0 on this machine.** `bin/placement-audit` is a shell script over
`plutil`, `curl` and conftest, all already here, and it runs when invoked rather
than on a schedule. It reads two things that already exist: the launchd plists
and the Healthchecks API.

The cost this document argues for is the always-on host, and that number is not
guessed here. It is the founder's decision and it needs a quote against the ten
jobs listed above, not a placeholder.

## Where it lives

```
bin/placement-audit               read every job, grade it, write the report
policy/placement.rego             the rules
policy/fixtures/placement-*.json  the paired controls
reports/placement.json            the inventory (generated, gitignored)
reports/placement-policy.txt      what conftest said
docs/onboarding/placement.md      this file
```

## How to turn it off

Nothing to turn off — it runs only when invoked, holds no daemon and changes
nothing. To remove it, delete `bin/placement-audit` and `policy/placement.rego`.

## How to turn it back on

```
bin/placement-audit
```

## What goes wrong

**Every job reports "not wrapped in hc-wrap.sh".** The join between launchd and
Healthchecks is the second argument to `hc-wrap.sh`. A job invoked any other way
has no discoverable check, so it is reported as unmonitored even when a check
exists under a name nobody can derive.

**The Healthchecks section is empty.** `bin/placement-audit` degrades to an
inventory with no ping history when `~/.estate/healthchecks/api_key` is missing
or the container at `127.0.0.1:8000` is down. It still grades schedules; it just
cannot tell you what has never run. That case is silent by design — the audit is
not the right place to raise a Healthchecks outage.

**A job is flagged that is meant to be a desk job.** That is the guard refusing
correct work, which is an outage and not a false positive (LAW 38). Fix the
rule, add the case to `policy/fixtures/placement-ok.json`, and re-run
`bin/policy-test`.

## What this does not fix

Moving a job to an always-on host removes the sleep problem and introduces a new
one: the host becomes something that can be lost. Whatever is chosen needs the
same treatment as everything else here — an exit that has been drilled, not
assumed (LAW 19).

And the ten red checks that ran and failed are untouched by any of this. They
are a separate list and they need reading one at a time.
