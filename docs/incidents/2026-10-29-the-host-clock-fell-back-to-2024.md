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

### The Codex conversations became unavailable, and why

The message the founder saw, `This conversation is unavailable. Its cached transcript and draft
remain here; input is paused.`, is emitted by the native Codex CLI, not by the ChatGPT desktop
renderer: the string is present in the native `codex` binary and absent from `app.asar`. The
native symbols place it in the transport reconnect path
(`codex_tui::app::reconnect::App::thread_unavailable`,
`codex_tui::chatwidget::reconnect::ChatWidget::pause_unavailable_thread`), so it is the state a
conversation is put into when the app-server connection for the selected thread is lost.

The connection was lost because of the clock. The desktop log written during the fault window
(`~/Library/Logs/com.openai.codex/2024/01/01/codex-desktop-...-408-t0-i1-000414-0.log`, 1,143
lines) records the TLS handshake to the remote host failing with a certificate that was not yet
valid:

```
2024-01-01T00:06:08.518Z error [AppServerConnection] app_server_connection.websocket_error connectionId=2 errorCode=CERT_NOT_YET_VALID hostKind=durable message="certificate is not yet valid" transport=websocket
```

That is line 83 of that log and the first of 534 lines that carry the failure (777 occurrences
of the phrase; 43 of them name the error code). The last is the last line of the file, at bogus
`2024-01-01T00:19:13.116Z`. Mapped through the offset measured above, the failure runs from
real `2026-10-29T22:22:50.081910Z` to real `2026-10-29T22:35:54.679910Z`: the fault window and
nothing outside it. A clock behind a certificate's `notBefore` makes every TLS client on the
host reject the certificate, so this was not a Codex defect. It was the wall clock the estate
never questioned.

The same window explains the failed founder turn in the affected conversation
(`01a18830-a71e-7653-b7df-7b705e722c23`): the app-server answered with
`{"code":-32603,"message":"workspace routing discovery failed"}` and the turn ended at real
`2026-10-29T22:35:15.607910Z` with `task_complete` carrying that message and no agent message.
The fault window holds four `workspace routing discovery failed` records and 114
`Workspace routing is unavailable` records; the post-correction log holds none of either.

The conversation's own rollout file carries the transition, and it is the founder-side record that
the open follow-up below used to be missing. The file
`~/.codex/sessions/2026/10/29/rollout-2026-10-29T15-04-16-01a18830-a71e-7653-b7df-7b705e722c23.jsonl`
(1,734 lines) records a sane turn ending at `2026-10-29T16:55:32.209Z`, then the first record
written under the regressed clock at `2024-01-01T00:18:15.815Z`, then the founder's message at
`2024-01-01T00:18:16.832Z` (real `2026-10-29T22:34:58.395910Z`): "i asshged work to previos
sessons, any updtes". The turn then failed with `task_complete` at `2024-01-01T00:18:34.044Z`
(real `2026-10-29T22:35:15.607910Z`), carrying `error.message` "workspace routing discovery
failed", `last_agent_message` null and `duration_ms` 18131. The next record in the same file is
`2026-10-29T22:49:26.182Z`: the same conversation worked normally once the clock was right.

The regressed clock also reached the model. The environment context and the world state that
the runtime injected for that turn both carry the regressed date, `current_date` `2024-01-01`,
so the agent was told the current date was two years in the past, in the same turn that failed.

Two candidate causes are ruled out. The remote thread was not absent: `thread/resume` for that
conversation returned `errorCode=null` inside the fault window and was followed by
`maybe_resume_success`. The expired rendezvous token was not the trigger: the
`rejectionReason=expired`, `httpStatus=401` events belong to the Local Work executor's Noise
rendezvous, they post-date the correction, and they are a different path from the TUI's
app-server transport.

Recovery followed the correction, and the boundary is measured. The already-running desktop
process kept its broken state for about twenty seconds: the post-correction log still carries
the certificate failure at `2026-10-29T22:36:14.690Z`, and by `2026-10-29T22:36:17.045Z` the
transport had advanced past TLS to `Unexpected server response: 503`. The last line that still
carries the certificate text is at `2026-10-29T22:36:20.133Z`, propagating the earlier error
into the renderer rather than failing a new handshake. The founder worked around the paused
conversation by starting two new ones, at real `2026-10-29T22:36:23Z` and `22:36:49Z`.

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
- The regressed clock reached the model context as the current date for one founder turn in the
  Codex conversation above.
- One real estate incident was filed under 2024-01-01.
- The Codex desktop app reported `This conversation is unavailable. Its cached transcript and
  draft remain here; input is paused.` The cause is now established and measured: the regressed
  clock put the host behind the TLS certificate's `notBefore`, the app-server connection could
  not be established, and the TUI put the conversation into its unavailable state.

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

- The Codex `This conversation is unavailable` condition is explained and measured above: it
  was the regressed clock failing TLS certificate validation. One detail stays open for the
  next recurrence: the remote host whose certificate was rejected is not named in the log
  (`hostKind=durable` only). The founder-side request that surfaced the message has now been
  recovered from the conversation's own rollout file and is quoted above.
- The exact firmware or kernel constant behind the `2024-01-01T00:00:00` fallback is not
  verified; it needs administrator access or board-level evidence.
- Whether a second clock adjustment occurred after the correction is not established; the wide
  log scans need a bounded, indexed approach.
- Recurrence is not established; the estate needs a standing record of clock verdicts, which the
  incident loop now provides.
