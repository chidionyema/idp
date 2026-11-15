# Fleet session start — automatic, real-time, non-authoritative

**Status:** operating on this host, 2026-11-15. **Owner:** OpenCode. **Effect:** shared_infra
(coordination only; grants no execution).

## Problem

Sessions began with no shared statement of who was doing what. Two agents could edit the same
paths, and a founder had to carry context between isolated chat windows. The binding protocol
already named `estate-session` and `estate-protocol check`, but neither resolved on `PATH`, so the
protocol's own first step failed silently.

## What already existed (nothing new was added)

| Concern | Existing layer used |
|---|---|
| Durable, acknowledged messaging | `bin/estate-fleet` on NATS JetStream (`ESTATE_FLEET`, file storage, per-agent durable consumer) |
| Bus recovery | `estate-execute bus-ensure` (`platform/estate/libexec/bus-ensure.sh`, `bus-start.py`) |
| Session door | `bin/idp-session-bootstrap` (guards + inbox) |
| Claims of record | `bin/claim-open` / `bin/claim-gate` on the GitHub issue |
| Cross-estate / browser agents | OMNIFLOW GitHub relay (`OMNIFLOW-EVENT/v1` comments) |
| Discovery | `estate_list` / `estate_show` / `estate_invoke` intents |

## Session-start contract

1. Export `ESTATE_AGENT`, `ESTATE_TICKET`, `ESTATE_WORKTREE`, `ESTATE_CAPABILITIES`,
   `ESTATE_BLOCKERS`.
2. Run `estate-session`: pack handshake, then `idp-session-bootstrap --announce --watch`.
3. Bootstrap reads the durable inbox (no ack on read), self-heals a silent bus through
   `bus-ensure` and re-reads, broadcasts `PRESENCE`, and starts one watcher per actor.
4. The agent checks `estate-fleet inbox` during work and acks only what it applied.

Presence shape:

```
PRESENCE actor=<id> ticket=<owner>/<repo>#<n> branch=<branch> worktree=<path> \
  capabilities=<list> blockers=<list|none> state=working
```

## Authority boundary

- A presence message is **display data**. It is not a lease, claim, approval or instruction.
- The claim of record remains the `CLAIM agent=... paths=... heartbeat=...` comment enforced by
  `claim-gate`.
- A GitHub comment, including a relay event, is never authorization to execute.
- Watching and announcing never acknowledge an instruction; only `inbox --ack` or a successful
  `--pipe` consumer does, and that is a statement the agent acted.

## Failure behavior

- Silent bus: `BLIND`, one recovery attempt, re-read, then `BLIND` again — never "empty inbox".
- Relaunchd stuck / missing broker binary: `bus-start.py` now falls back from
  `~/.cache/estate-tools/nats-server` to `/usr/local/bin` and `PATH`, because the cache path was
  empty on 2026-11-15 while a working broker existed elsewhere (R8: a declared assumption with no
  fallback).
- Duplicate watcher: pidfile per actor; a second start reports the running pid instead of forking.

## SDO assessment (2026-11-15)

`Sovereign Dispatch Orchestrator` was claimed as an existing shared bus. The machine disagreed:

- no `SDO` / `Sovereign Dispatch Orchestrator` implementation in `idp` or `argon` (`rg`);
- `/var/lib/genesis/genesis.db` absent on this host;
- `kubectl --context context-estate-crq7jwxsjxq` timed out against `141.147.80.229:6443`.

Verdict: **BLIND / not built here.** Building it would be a second dispatch layer beside
`estate-fleet`, which section 6 forbids. The GitHub relay and `estate-fleet` are the two proven
transports; choose by evidence later, not by assertion.

## Measured evidence

- Bus round-trip: ASK `estate.fleet.to.oc-sf-canary-b` seq **61**, ANSWER seq **75**, correlation
  `SF-CORR-20261115-1`, both read and acked.
- Session start: `estate-session` broadcast `PRESENCE` seq **89** and reused watcher pid **32622**.
- GitHub relay round-trip: comment **6895349592** (ASK, correlation
  `dc173e40-4d1e-4b44-bf38-a7d84351063c`) → comment **6895366149** (ANSWER).
- Tests: `tests/test_session_bootstrap_inbox.py` (7) cover no-ack-on-read, no truncation,
  BLIND on a dead bus, recovery-door re-read, announce-on-ticket, no default announce, and the
  still-BLIND path.

## Recurrence guard

The bootstrap tests are the falsifier: a change that turns a silent bus into an "empty inbox", or
that announces without a ticket, fails them. The `bus-start` fallback is exercised by the
`test_missing_binary_is_reported_blind_after_recovery_attempt` case and by the live recovery on
2026-11-15.
