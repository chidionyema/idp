# Onboarding: estate-next

`bin/estate-next` writes `docs/NEXT.md`, the page that answers "what is planned, what is blocking,
when" so that no session answers it from memory (crew#403 CP6, LAW 44).

## Inputs

| Input | Where | What it gives |
|---|---|---|
| open `- [ ] CP<n>` rows | every open issue of `chidionyema/crew` (`gh issue list`) | the planned checkpoints |
| newest handoff per lane, 🔴 and 🟡 lines | `~/.estate/feed.md` (`ESTATE_FEED`), last 3 hours | BLOCKING / ACTIVE |
| `Expect: <date>` indented under the checkpoint row | the issue body | when |

## Grades

- **BLOCKING**: a lane's 🔴 line names the issue (`crew#N` or `#N`).
- **ACTIVE**: a lane's 🟡 line names it.
- **PLANNED**: open and no lane named it in its newest handoff.
- **NO DATE** in the Expect column: no `Expect:` line under the row. Red on its own axis; a
  BLOCKING row is red on both.

## To change a row

Put `    Expect: 2026-09-01` (indented) directly under the checkpoint row on the issue. The next
hourly render picks it up. Do not edit `docs/NEXT.md`.

## Offline and tests

    bin/estate-next --issues issues.json --feed feed.md --out NEXT.md --taken T --now T

`sovereign/tests/bdd/test_gate_estate_next.py` binds `features/assurance/estate-next.feature`.
`--check` exits 1 when the page on disk differs from the inputs.
