# Runbook: the host wall clock lies

## What happened

On 2026-10-29, between 22:16:41 and 22:36:00 UTC, this host's wall clock read
**2024-01-01**. It was not an application bug: the kernel was serving that time, and every
process that asked the kernel for the time got it. Six Pi agent sessions created in that window
stamped themselves 2024-01-01, the Codex desktop app wrote its Chromium profile under the same
date, and the estate's own incident loop filed a real NATS outage as
`estate-bus-20240101T000541Z.json`. The clock was corrected forward by the time service about
nineteen minutes later, and the estate's own incident ledger shows the same thing: row 20 was
stamped `2024-01-01T00:05:41Z` between rows 19 and 21, which were both sane.

Nothing detected it. The timestamps were well-formed, so no gate, no sensor and no human read
them as wrong. That is the whole failure: a clock that lies quietly corrupts every age, every
ordering and every SLA computed from it, in the same second, with no alarm.

The mechanism is measured as far as the evidence goes. The clock was set to exactly
`2024-01-01T00:00:00Z` at power-on, 24 seconds before the kernel booted, and the kernel's own
boot record carried that 2024 stamp. The leading explanation is an invalid RTC at power-on,
with the platform falling back to a fixed date; the exact firmware constant is unverified and
is deliberately not named. No `date -s`, `settimeofday` or equivalent was found in the estate
repo, the agent tooling, the shell history, the rc files, the launchd jobs or the running
processes, and there is no passwordless sudo on this machine to inspect the privileged time
configuration directly. A wake-related assertion for the Wi-Fi interface
(`0x100=MAGICWAKE`, created under the bad clock) is evidence that a wake event happened, not
proof of what set the clock. The attribution stays at the macOS/kernel layer, and the guard
below is deliberately built so that it does not depend on the attribution.

The full record, with the measurements, is
[docs/incidents/2026-10-29-the-host-clock-fell-back-to-2024.md](../incidents/2026-10-29-the-host-clock-fell-back-to-2024.md).

## The measurement that changed the design

The first version of this guard treated the kernel as its strongest witness, on the belief that
the kernel's boot record does not follow a later change of the wall clock. **That belief was
wrong, and the arithmetic is the proof.**

The time service corrected the clock forward by `89,245,001.563908` seconds:

```
2026-10-29 22:36:00.293794+0000  dasd: Time change: Clock shifted by 89245001.563908 secs
```

The kernel's boot record on this host, read after the correction:

```
kern.boottime raw: { sec = 1793312225, usec = 563910 } Thu Oct 29 22:17:05 2026
```

Subtract the step from the boot record and the kernel's own boot stamp comes back exactly:

```
1793312225.563910 - 89245001.563908 = 1704067224.000002
```

and `1704067224` is `2024-01-01T00:00:24Z`, which is the stamp in the kernel's own boot record
in the unified log:

```
2024-01-01 00:00:24.000000+0000  Timesync  === system boot
```

The difference is two microseconds, which is the rounding of the two records. So on macOS the
boot record moved by the wall-clock step, exactly: `kern.boottime` follows the wall clock
through a step, and `kern.boottime + CLOCK_MONOTONIC` is the wall clock. Measured live on this
host after the correction, the deviation is one microsecond.

The consequence for the guard is the whole point of this revision: a witness that follows the
clock cannot witness the clock. The kernel is now the **last** witness asked, and it can never
overrule the anchor or the ledger.

## What the guard does

`platform/estate/libexec/clock-guard.py` never trusts the wall clock on its own. It asks three
witnesses, in this order, and takes the first one that can decide.

### A. The anchor (what the clock said before, strongest)

One state file, `~/.estate/state/clock-skew.json`, holds the last trusted reading of both
clocks: `{"wall": ..., "monotonic": ...}`. It is the only witness that knows what the clock
said before, so it decides first.

* Inside one boot, the comparison is relative: the wall delta against the monotonic delta. A
  clock that went backwards, or jumped forward faster than real time, is named.
* Across a reboot, the comparison is absolute. The monotonic clock restarting is the signal
  that the host rebooted, and a power-off can move the wall clock forward by any amount, so a
  forward jump after a reboot is **not** a fault. A wall clock that is *behind* the anchor
  after a reboot is the signature of a host that came up on a stale clock, which is exactly the
  2026-10-29 failure, and it is named `backward`.
* An **anchored** entry (see below) mixes two timelines: its wall is a projection and its
  monotonic is the reading at the moment of the fault. It is compared absolutely and is
  excluded from the wall-versus-monotonic skew test.

### B. The ledger (what the estate itself recorded, independent)

`SELECT MAX(last_seen) FROM incidents` over the estate incident ledger
(`~/.estate/state/incidents.db`, read only) is the latest timestamp the estate itself wrote
while its clock was sane. A wall clock behind that by more than the tolerance is a backward
jump. It is one second coarse, and it is independent of the anchor: it catches a clock that was
already wrong when the anchor was taken, which is the case where the anchor was written during
the bad window.

### C. The kernel (a consistency check, last)

```
kern.boottime  +  CLOCK_MONOTONIC
```

On this host that sum tracks the wall clock to the microsecond, so it cannot see a step. It is
still worth asking, for two reasons: on a host whose boot record does *not* follow the wall
clock, a gross disagreement is real evidence and the guard should use it; and on every host it
records whether the wall clock and the kernel's own clock are telling the same story. It is
asked only when the anchor and the ledger are silent, it never overrules either of them, and
it never supplies the projection while either of them can.

The kernel's deviation is recorded in the verdict whenever the kernel can be reached, even when
another witness decided, because a witness that was not asked still has something to say about
the diagnosis.

### Precedence

1. The anchor decides when it can: relative inside a boot, absolute across a reboot.
2. The ledger decides when the anchor is silent and the wall clock is behind it.
3. The kernel decides when both are silent and it disagrees grossly with the wall clock.
4. Otherwise the verdict is `ok` (the anchor or the ledger vouched), or `unknown` (nothing to
   go on), and the current reading becomes the new baseline.

### The verdicts

| verdict | meaning | trusted stamp |
|---|---|---|
| `ok` | a witness agrees that the wall clock has not moved | the wall clock |
| `backward` | the wall clock went backwards | the projection: the anchor advanced by real time, or the ledger's last sane stamp |
| `forward` | the wall clock jumped forwards faster than real time | the projection |
| `unknown` | no witness could decide (first run, no anchor, no ledger) | the wall clock |
| `blind` | no verdict was possible at all | the wall clock, and the door exits 2 |

The tolerance is `max(2.0 s, 5% of the monotonic elapsed time)`, so a long gap between samples
allows more drift than a short one. The kernel's tolerance is separate and tighter:
`max(2.0 s, 10 ppm of uptime)`, because the boot record is parsed to the microsecond.

`time.monotonic()` is deliberately not used: on this macOS/Python pair it returned a near-zero
value, and a monotonic reading that restarts is not a monotonic reading. `clock_gettime` is the
authoritative call.

### The anchor: a bad window must not destroy the baseline

The first version of this guard detected the fault and then overwrote its own baseline with the
regressed reading. The next stamp compared the poisoned sample with the wall clock, found them
equal, and stamped the naive wall clock -- the guard had called the clock a liar and then
trusted it, in the same pass.

So when the verdict is untrusted, `commit()` writes the **anchor**:

```json
{"wall": <the projection>, "monotonic": <the current monotonic reading>, "anchored": true}
```

The trusted wall anchor is preserved and only the monotonic reference advances. A regressed
reading is never written back as the baseline. On a healthy verdict the sample is written
normally, which is also how the estate re-baselines after a recovery.

The projection is the anchor advanced by the real time that has passed since it was taken:
inside a boot, the monotonic delta; across a reboot, the uptime of the current boot, which is
a lower bound because the power-off time is not knowable from here.

### Corrupt state

An unreadable or corrupt state file costs the estate the anchor, and only the anchor. The
ledger and the kernel are read independently of that file, so the guard still asks them: if the
ledger or the kernel can decide, the verdict is decided and the state file is re-baselined, with
the corruption recorded in the verdict's `reason`. Only when no witness can be reached at all
is the verdict `blind` (exit 2): with no way to check anything, the guard fails closed.

### The hot-path cache

Stamping a ledger row asks for the verdict once per row. The verdict is cached by state path for
at most 0.5 s, so one pass over many rows does not call `sysctl` once per row. 0.5 s is far
below the clock-jump tolerance, so detection is not delayed in any way that matters.

## The door

```bash
bin/estate-incident-loop clock          # 0 the clock is trustworthy, 1 it is not, 2 no verdict
bin/estate-incident-loop clock --json   # the same verdict as JSON
```

The same code is reachable as the governed intent `incident-loop` with `action=clock`, so an
agent never has to shell out to reach it.

## The writers that refuse a regressed clock

- `platform/estate/libexec/incident-loop.py` stamps the incident ledger, the sensor windows and
  the MTTR from the trusted clock. A backward jump is sensed as an incident like any other
  error, with the skew in the detail. The clock incident's fingerprint is
  `fingerprint("clock", repo, f"clock-{state}")`, so a repeated jump in the same state does not
  open a second ticket.
- `platform/estate/libexec/critical-watch.py` stamps the incident ids and the `detected_at`
  fields from the trusted clock, and ages heartbeats against it. Incident ids keep their
  `YYYYMMDDTHHMMSSZ` shape, so a projected id is still sortable and still unique.

Both writers load the same `clock-guard.py` by sibling path, so there is one implementation and
one verdict, not two.

## What to do when the door says `backward`

1. Read the verdict: `bin/estate-incident-loop clock --json`. `wall_delta_s` is how far the
   clock moved, `monotonic_delta_s` is how much real time passed, `reboot` says whether the host
   rebooted, `witness` says which witness decided and `projected_epoch` is the time the estate
   is using instead.
2. Do not trust any file written during the window. Session transcripts, incident files and
   tickets stamped inside the window carry the regressed time.
3. Fix the host clock (`sudo systemsetup -setusingnetworktime on`, then `sudo systemsetup
   -setnetworktimeserver time.apple.com`), and check the time service:

   ```bash
   systemsetup -getusingnetworktime
   systemsetup -getnetworktimeserver
   scutil --get TimeZone
   ```

4. Confirm the estate agrees again: `bin/estate-incident-loop clock` must print `ok`. It
   re-baselines by itself: the next healthy pass writes the current reading over the anchor.
   Until then the anchor keeps the trusted projection, so the estate keeps stamping a sane time.
5. Only if the anchor itself has to be reset by hand (a corrupt state file that the ledger and
   the kernel cannot repair):
   `rm ~/.estate/state/clock-skew.json` (the next sample starts a fresh baseline).

## Proof

- `tests/test_clock_guard.py` -- the measured kernel arithmetic, the five falsifiers (the
  2026-10-29 power-on fallback caught by the anchor across a reboot, the kernel unable to mask
  the anchor, the ledger unable to be masked either, a long power-off with a forward wall not
  called a fault, and a healthy host still `ok`), the anchor and the anchored entry, the
  corrupt-state behaviour, the door's three exit codes, and the two writers (incident ledger,
  critical-watch incident ids) refusing to record a regressed clock.
- The kernel demotion is not decoration: putting the kernel back in front of the anchor kills
  `test_the_kernel_witness_cannot_mask_the_anchor` and
  `test_the_ledger_cannot_be_masked_by_the_kernel_either`.
- The anchor is not decoration: restoring the pre-2026-10-30 behaviour (write the current
  sample even when the verdict is untrusted) kills
  `test_the_baseline_survives_a_bad_window` and
  `test_a_tick_that_detects_a_bad_clock_does_not_then_trust_it`.
- The reboot handling is not decoration: treating a monotonic reset as `blind` instead of a
  reboot kills `test_a_power_on_fallback_is_caught_by_the_trusted_anchor_across_a_reboot`.
- The measurement itself, re-runnable: `/tmp/boottime_proof.py` prints the live deviation
  between the kernel's own estimate and the wall clock, and the recorded arithmetic of the
  2026-10-29 step, and exits nonzero if any of it stops holding.
