# The estate's live state is one object, three readers, and BLIND is a value

Status: proposed, 2026-11-28. Owner: the claim on this lane. Replaces nothing until the proof section passes.

## Why this exists

The founder hops between OpenCode, Claude Code, GitHub and terminals because each console sees
only its own slice. The founder's order of 2026-11-28 asks for one real-time state object read by
the laptop, Telegram and the web, with a missing signal shown as BLIND and never as 0 or green.
The founder's standing instruction the same day: do not engage the founder for what a default can
settle, and leave nothing open.

## What the order named, and what origin/main holds (measured 2026-11-28 at 77ecbd870)

| Named in the order | On origin/main | Command that shows it |
|---|---|---|
| `bin/estate-watch` | absent. `estate-watch` is `.github/workflows/estate-watch.yml`, a 15-minute GitHub Actions drill that files issues for downed homes | `git ls-tree -r --name-only origin/main \| rg 'estate-watch'` |
| `EstateLiveStateDO` | absent. Two Durable Objects exist: `platform/router-edge/src/ledger-do.ts`, `platform/router-edge/src/routing-do.ts` | `git ls-tree -r --name-only origin/main \| rg 'router-edge/src'` |
| `meridianTelemetry.ts`, `genesis-founder-surface` | absent | `git ls-tree -r --name-only origin/main \| rg -i 'meridianTelemetry\|genesis-founder'` |
| FleetView Fleet page | present: `backstage/plugins/fleetview-backend` (sessions, claims, approvals, evals, delivery) | `git ls-tree -r --name-only origin/main \| rg fleetview-backend` |
| Telegram live board | one open issue: #8134 (canonical Telegram pin); outbox lane #8619 is RED and owned by another agent | `gh issue view 8134`, `gh issue view 8619` |
| Optimus metrics | `catalog/optimus-metrics.json` holds a list of 39 | `git show origin/main:catalog/optimus-metrics.json \| python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'` |

Consequence: the "laptop terminal feed" and "web PWA" consumers are new work, and the spine is
a third Durable Object beside the two that exist. Nothing in this spec deletes FleetView. The
bar from AGENTS.md section 6 is met only if the spine adds what FleetView cannot.

## What FleetView cannot do (the bar this raises)

1. It is a Backstage backend, so it answers only where Backstage runs. The estate is retiring
   OKE; a surface that needs the cluster is a fallback, not a home (AGENTS.md section 7a).
2. It has no cross-surface contract: nothing proves the laptop, Telegram and the web print the
   same numbers. Issue #8070 (REQ-025) asks for exactly that parity.
3. It has no BLIND value in its data model, so a missing signal can render as zero.

## Design

One Durable Object, `EstateLiveStateDO`, in its own worker `platform/estate-live-state` (decided
2026-11-28, replacing the earlier plan to put it in `platform/router-edge`). The model router serves
every agent's calls, so a fault or a deploy of the live-state endpoint must not be able to take it
down. The worker is registered in `platform/deploy/targets.json`, but that file is a registry
only (measured 2026-11-28: it is read by `bin/estate-gate`, `bin/estate-topology`,
`bin/estate-debug-pack` and a test, and deploys nothing). Each existing worker has its own release
workflow (`router-edge-release.yml`, `otto-lifeboat.yml`). This worker has none yet, and a
workflow under `.github/workflows/` is a guarded path that needs a founder-signed seal
(chidionyema/idp#8705, #8032), so until that lands the worker is built, not operating.

- Input: append-only events `{seq, ts, source, kind, subject, value | BLIND, evidence}`. A
  producer that cannot measure sends `BLIND` with a reason; the object never defaults a missing
  field.
- Output: one snapshot `estate-live-state.v1`, a pure fold over the log, plus a WebSocket
  (Hibernation API) that pushes each event.
- Readers, all thin, none with a store of its own: the terminal board, the Telegram editor, the
  web page. Each prints `seq` and the snapshot hash, so parity is checkable by comparing two
  strings.
- Producers: the Greenlane verdicts, the existing estate-watch workflow results, session
  heartbeats, and one scheduled sweep that runs every metric in `catalog/optimus-metrics.json`.

## Falsifiers (each must fail on a known-bad input before the gate is believed)

1. A snapshot with a missing producer field renders `BLIND`, never `0`. Known-bad: drop a field
   and assert the reader output contains `BLIND`.
2. Two readers fed the same log print the same `seq` and hash. Known-bad: corrupt one reader's
   fold and assert the parity check exits non-zero.
3. A producer silent for longer than its declared interval shows `BLIND` with the age. Known-bad:
   stop a producer and assert the state flips within one interval.

## Order of work

1. Object, event schema and falsifiers, with the sweep as the first producer.
2. Terminal reader, replacing nothing, proving parity against the snapshot.
3. Telegram reader on top of #8134's canonical pin and #8619's outbox once that lane is green.
4. Web reader. FleetView pages that duplicate a panel are deleted in the change that ships the
   panel, per section 6.

## Out of scope here

The founder seal and guarded-path rules (claimed by another agent on #8541). This spec touches
no guarded path.

## Proof of done

Each item is `operating`, not `built`: a timed read of the snapshot endpoint from the laptop, the
Telegram board and the web page, showing the same `seq` and hash within five seconds of one
event, with the laptop lid closed. Until then this document is a proposal.
