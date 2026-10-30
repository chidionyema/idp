# Runbook: the host wall clock lies

## What happened

On 2026-10-30, between roughly 06:00 and 06:16 UTC, this host's wall clock read
**2024-01-01**. It was not an application bug: the kernel was serving that time, and every
process that asked the kernel for the time got it. Six Pi agent sessions created in that window
stamped themselves 2024-01-01, the Codex desktop app wrote its Chromium profile under the same
date, and the estate's own incident loop filed a real NATS outage as
`estate-bus-20240101T000541Z.json`. The clock then returned to 2026-10-30 on its own.

Nothing detected it. The timestamps were well-formed, so no gate, no sensor and no human read
them as wrong. That is the whole failure: a clock that lies quietly corrupts every age, every
ordering and every SLA computed from it, in the same second, with no alarm.

What is still unknown: who or what set the clock. No `date -s`, `settimeofday` or equivalent was
found in the estate repo, the agent tooling, the shell history, the rc files, the launchd jobs or
the running processes, and there is no passwordless sudo on this machine to inspect the
privileged time configuration directly. A wake-related assertion for the Wi-Fi interface
(`0x100=MAGICWAKE`, created under the bad clock) is evidence that a wake event happened, not
proof of what set the clock. The attribution stays at the macOS/kernel layer, and the guard
below is deliberately built so that it does not depend on the attribution.

## What the guard does

`platform/estate/libexec/clock-guard.py` never trusts the wall clock on its own. It asks three
independent witnesses and takes the strongest one that can decide.

### A. The kernel witness (absolute, strongest)

```
kern.boottime  +  CLOCK_MONOTONIC
```

`kern.boottime` is the moment the kernel booted, read from the kernel itself.
`CLOCK_MONOTONIC` is the time since that boot, which nothing can set without a reboot. Their
sum is an absolute estimate of true wall time that does not depend on the wall clock at all, and
it is available on the first run, with no state file.

Measured on this host, 2026-10-30, while the wall clock was healthy:

```
kern.boottime raw: { sec = 1793312225, usec = 563910 } Thu Oct 29 22:17:05 2026
boot epoch:        1793312225 2026-10-29T22:17:05Z
mono:              32892.915166
wall:              1793345118.4790778
boot + mono:       1793345117.915166
wall - (boot+mono): 0.5639119148254395
```

The residual is exactly the boot record's `563910` microseconds, so the implementation parses
the microseconds and adds them to the boot epoch. With them, the kernel witness and the wall
clock agree to about 0.05 s on the healthy host.

During the 2024 window the boot record still read `Thu Oct 29 22:17:05 2026`, so the kernel
witness was pointing at the true time while the wall clock said 2024. That is what makes it a
witness and not a copy of the same mistake.

### B. The sample witness (relative, fallback)

One state file, `~/.estate/state/clock-skew.json`, holds the previous reading of both clocks:
`{"wall": ..., "monotonic": ...}`. Comparing the previous sample with the current one, using
the monotonic delta as the real elapsed time, catches a jump that happened between two samples.
It needs a prior sample, so it cannot decide on the first run.

### C. The ledger witness (coarse, last resort)

`SELECT MAX(last_seen) FROM incidents` over the estate incident ledger
(`~/.estate/state/incidents.db`, read only) is the latest timestamp the estate itself wrote.
A wall clock behind that by more than the tolerance is a backward jump. It is one second
coarse and it only knows about incidents the estate recorded, so it is consulted only when the
kernel witness cannot decide.

### Precedence

1. The kernel witness decides. If it disagrees with the wall clock by more than the tolerance,
   the verdict is `backward` or `forward` and the projection is the kernel estimate.
2. If the kernel witness agrees, the verdict is `ok`, even if the persisted sample is stale. A
   sample poisoned by an older guard version must not keep the estate untrusted forever after
   the clock has recovered; the kernel outranks it and the sample is re-baselined.
3. Only when there is no kernel witness does the sample witness decide.
4. Only when there is no kernel witness and no usable sample does the ledger witness decide.

### The verdicts

| verdict | meaning | trusted stamp |
|---|---|---|
| `ok` | a witness agrees with the wall clock within tolerance | the wall clock |
| `backward` | the wall clock went backwards | the projection: the witness's estimate |
| `forward` | the wall clock jumped forwards faster than real time | the projection |
| `unknown` | no witness could decide (first run, no kernel, no sample) | the wall clock |
| `blind` | no verdict was possible at all | the wall clock, and the door exits 2 |

The tolerance is `max(2.0 s, 5% of the monotonic elapsed time)`, so a long gap between samples
allows more drift than a short one.

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

### Corrupt state

An unreadable or corrupt state file is `blind` (exit 2) **only** when there is no kernel
witness: with no way to check anything, the guard fails closed. With a readable kernel witness
the estate can still decide, so the state is re-baselined and the corruption is recorded in the
verdict's `reason` instead of blocking the estate.

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

## The writers that now refuse a regressed clock

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
   clock moved, `monotonic_delta_s` is how much real time passed, `witness` says which witness
   decided and `projected_epoch` is the time the estate is using instead.
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
   re-baselines by itself: the healthy kernel witness outranks a stale sample, so the poisoned
   baseline is replaced on the next pass.
5. Only if the kernel witness itself is unavailable (a non-Darwin host, or `kern.boottime` not
   readable) and the sample must be reset by hand:
   `rm ~/.estate/state/clock-skew.json` (the next sample starts a fresh baseline).

## Proof

- `tests/test_clock_guard.py` -- 25 tests: the five verdicts, the three witnesses and their
  precedence, the kernel and ledger parsing, the anchor, the corrupt-state behaviour, the door's
  three exit codes, and the two writers (incident ledger, critical-watch incident ids) refusing
  to record a regressed clock.
- The kernel witness is not decoration: removing it (`return None`) kills five of the tests,
  including the real-host kernel agreement and both refusal directions of the fake-`sysctl`
  end-to-end tests.
- The anchor is not decoration: restoring the pre-2026-10-30 behaviour (write the current
  sample even when the verdict is untrusted) kills
  `test_the_baseline_survives_a_bad_window` and
  `test_a_tick_that_detects_a_bad_clock_does_not_then_trust_it`.
- Real path on this host, 2026-10-30, healthy:

  ```
  $ bin/estate-incident-loop clock
  ok       the wall clock agrees with the kernel's own clock within 2.0s
  wall 1793345933  trusted True
  $ bin/estate-incident-loop clock --json
  { "state": "ok", "trusted": true, "witness": "kernel", "kernel_deviation_s": -0.046, ... }
  ```
- Real path with a poisoned clock (a fake `sysctl` on `PATH` reports a boot record two years
  ahead, so the wall clock is behind the kernel witness), the incident loop's own tick:

  ```
  incident 61fac628af16783b source=clock
  first_seen 2028-10-29T07:39:39Z      <- the kernel projection, not the naive wall clock
  naive wall 2026-10-30T07:39:41Z
  state file: {"wall": 1856417977.896542, "monotonic": 33752.877223, "anchored": true}
  ```
- Real path with the same poisoned clock, the critical watcher: the incident file is named
  `clock-drill-20281029T074418Z.json` and its `detected_at` is `2028-10-29T07:44:18Z`, the
  projection, while the naive wall clock read `2026-10-30T07:44:19Z`.
