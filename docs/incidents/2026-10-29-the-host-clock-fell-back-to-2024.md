# Incident: the host wall clock fell back to 2024-01-01 (2026-10-29 22:16 to 22:36 UTC)

Status: the clock was corrected forward by the time service after about nineteen minutes. No
estate process set it: no `date -s`, `settimeofday` or equivalent was found in the estate repo,
the agent tooling, the shell history, the rc files, the launchd jobs or the running processes.
The leading explanation is an invalid RTC at power-on with the platform falling back to a fixed
date; the exact firmware constant is unverified and is deliberately not named. The estate is
now guarded (see "The fix"), and the guard was itself wrong once: the first version trusted the
kernel as an absolute witness and could not have seen this failure. That second failure is the
one this incident is really about.

## What happened

- Real time `2026-10-29T22:16:41.563910Z`: the host came up and the wall clock was set to
  exactly `2024-01-01T00:00:00Z`.
- Real time `2026-10-29T22:17:05.563910Z`: the kernel booted, 24 s later, with its boot record
  carrying the 2024 stamp.
- Real time `2026-10-29T22:36:00.293794Z`: the time service adjusted the wall clock forward by
  `89,245,001.563908` seconds. The estate's clock was correct again.

Everything the estate wrote between those two instants was stamped 2024-01-01, and nothing
detected it: the timestamps were well-formed, so no gate, no sensor and no human read them as
wrong.

## The measurements

### The wall clock moved, and the kernel moved with it

The kernel's boot record, read on 2026-10-30:

```
kern.boottime raw: { sec = 1793312225, usec = 563910 } Thu Oct 29 22:17:05 2026
```

The unified log, bounded window around the correction (`/tmp/bootall.log`, 11,584 lines):

```
2026-10-29 22:36:00.293794+0000  Timesync  === system wallclock time adjusted
2026-10-29 22:36:00.294551+0000  dasd: Time change: Clock shifted by 89245001.563908 secs
```

The kernel's own boot stamp, in the 2024 log store (`/tmp/log2024.log`):

```
2024-01-01 00:00:24.000000+0000  Timesync  === system boot
```

The arithmetic that settles the mechanism:

```
1793312225.563910 - 89245001.563908 = 1704067224.000002
1704067224 = 2024-01-01T00:00:24Z
```

The difference between the computed value and the kernel's own boot stamp is two microseconds,
which is the rounding of the two records. **The boot record moved by exactly the wall-clock
step.** So on macOS `kern.boottime` follows the wall clock through a step, and
`kern.boottime + CLOCK_MONOTONIC` is the wall clock. Measured live afterwards, the deviation is
one microsecond.

This is the load-bearing measurement of the whole incident, and it is the one that broke the
first version of the guard.

### The estate's own ledger shows the window

`~/.estate/incidents/ledger.jsonl`, three consecutive rows:

```
19: 2026-10-29T20:21:23Z     (sane, before the fault)
20: 2024-01-01T00:05:41Z     (the fault: 5m41s after the clock was set back)
21: 2026-10-30T00:32:26Z     (sane, after the correction)
```

Row 20 is a real NATS outage, filed under a date two years in the past, as
`~/.estate/incidents/estate-bus-20240101T000541Z.json`. The real instant of row 20 is
`2026-10-29T22:22:22Z` (bogus time plus the 22:16:41.56 offset), which is inside the window.

### The kernel's process start times show the same window

Six Pi agent processes and one `/usr/bin/caffeinate -s -i` carry kernel-derived start times
inside the fault window. The APFS birth times of 3,637 files agree. Those two are the strongest
system-wide witnesses, because neither is derived from `Date.now()`.

`ps etime` was checked as a third witness and is **not** monotonic on macOS: it is computed from
the stored wall-clock process start time, so it agrees with the bad clock rather than
contradicting it.

### Power state, and one inconsistency that is still open

`pmset -g log` (20,293 lines, `/tmp/pmset.log`):

```
2026-10-29 20:03:02 +0000 DarkWake DarkWake from AutoPowerOff [CDN] : due to /HibernateError Using BATT (Charge:0%) 1 secs
2026-10-29 20:23:23 +0000 Sleep  Entering Sleep state due to 'Low Power Sleep':TCPKeepAlive=inactive
2026-10-26 16:50:17 +0000 ShutdownCause SMC shutdown cause: 5: Software initiated shutdown
```

The `dasd` RTC history contains the interval `Mon Jan 1 12:08:45 2024 - Tue Jan 2 12:08:45
2024`. That is stored history, not proof of a live 2024 reading, and it is recorded here as
such.

Open, and not to be resolved by guessing: `PowerUIAgent` reported `battery level=92,
externalConnected=1` at real `2026-10-30 00:00:51`, which does not fit a simple
drained-battery-only explanation for the dark wake. `systemsetup`, `/var/db/timed` and the
privileged time configuration are not inspectable on this machine without administrator
access, so the exact firmware or kernel constant behind the `2024-01-01T00:00:00` fallback
cannot be named from here.

## What was ruled out

- A user-space or privileged user process: no setter was found in the shell history, the rc
  files, the Pi transcripts, the session files, the repo, `~/.estate/bin`, `~/.estate/libexec`
  or any worktree.
- A second clock adjustment after the correction: not ruled out. Scans of 12 and 24 hours and a
  store-wide `system boot` scan all timed out (`rc=142`), so absence of evidence is not evidence
  of absence here.
- Recurrence: not established. A raw count of files with 2024 APFS birth times is a count, not
  a recurrence rate.

## The impact

- Six Pi agent sessions and the Codex desktop profile were created under 2024-01-01. The
  sessions are transcripts of real work; their timestamps are wrong.
- One real estate incident was filed under 2024-01-01.
- The Codex desktop app reported `This conversation is unavailable. Its cached transcript and
  draft remain here; input is paused.` The cause is not established: a bad clock and a
  remote-thread absence are different failures and the evidence does not yet separate them.

## Root cause, and the law it broke

**Law 9 R1, "gates fail open", and law 3, "proof, not assertion".** The estate had no guard on
the wall clock at all: every timestamp the estate writes came from a clock it never questioned.
That is the origin of the incident.

**The same law, a second time.** The first clock guard (PR #7538, landed as `752301bb3`) made
the kernel boot record its strongest witness, on the belief that the boot record does not follow
a later change of the wall clock. The measurement above proves the belief false. A gate that
cannot fail is not a gate, and that gate could not have failed on this failure: on this host it
would have agreed with the regressed clock and called it `ok`. The missing law, now written
into the code: **a witness that follows the clock under test cannot witness that clock**, and a
witness that has been measured to follow it must be demoted to a consistency check and must
never be allowed to overrule a witness that has not.

## The fix

- `platform/estate/libexec/clock-guard.py` now decides in the order **anchor -> ledger ->
  kernel**: the last trusted reading first, the estate's own incident ledger second and
  independently, and the kernel's boot record last, as a consistency check that can neither
  veto nor supply a projection while the other two can.
- A monotonic reset is a reboot, not a fault: the wall clock is then compared with the anchor
  absolutely. A wall clock *behind* the anchor after a reboot is the signature of a host that
  came up on a stale clock, and it is named `backward`. A wall clock *ahead* of it after a long
  power-off is legitimate and is not alarmed.
- An untrusted verdict writes an anchored projection (`"anchored": true`) instead of the
  regressed reading, so the baseline survives the bad window.
- `tests/test_clock_guard.py` carries the falsifiers: the 2026-10-29 power-on fallback caught
  by the anchor across a reboot, the kernel unable to mask the anchor, the ledger unable to be
  masked, a long power-off with a forward wall not called a fault, a healthy host still `ok`,
  and both writers (incident ledger, critical-watch incident ids) refusing to record a
  regressed clock.
- The runbook `docs/runbooks/clock-skew.md` carries the measurement, the precedence and the
  recovery steps.

## Open follow-ups

- The Codex `This conversation is unavailable` condition is not yet explained; reproduce it and
  keep the request, the response and the logs.
- The exact firmware or kernel constant behind the `2024-01-01T00:00:00` fallback is not
  verified; it needs administrator access or board-level evidence.
- Whether a second clock adjustment occurred after the correction is not established; the wide
  log scans need a bounded, indexed approach.
- Recurrence is not established; the estate needs a standing record of clock verdicts, which the
  incident loop now provides.
