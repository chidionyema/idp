# Onboarding: dod-live-claim-gate

## What it is

`bin/dod-live-claim-gate` is the repository-CI check for DoD v3's fourth rule: "verified, not
asserted" (ADR 0029). It reads a doc's own `**Status:**` line — checked there and nowhere else,
so an unrelated sentence with the word "done" in it can never trip it. A line claiming built,
done, proven live, or doored, combined with the document naming a Kubernetes-shaped capability
(a `platform/<name>/` or `backstage/plugins/<name>/` path), must carry, somewhere in the
document, one of:

| What the doc shows | Result |
|---|---|
| a `Dockerfile` in the named path, plus a `kind: Deployment` manifest under `platform/` or `clusters/` naming the same capability | pass — the claim has a real manifest behind it |
| an explicit `**Not done:**` line | pass — the gap is named honestly instead of hidden |
| neither | fail |

A capability named only in prose (the words `Deployment`/`Service`/`on cluster`, no path) is not
graded — there is nothing to check a manifest against, and refusing on a word alone would be the
false-positive risk this gate must not create (R38: a check that blocks correct work is an
outage). Only a named path is checked.

## How it runs

Row `dod-v3-verified-not-asserted` in `rules.yaml`, planes `[ci, session]`. `bin/idp-ci` runs it
against `docs/tickets/*.md`, `docs/specs/*.md`, and `docs/audits/*.md` on every push
(`bin/idp-rules run`); a session hook grades the same files a Claude Code session touches
(`bin/idp-rules session`). Scope is a fixed, named list of docs, not a repo-wide sweep, with a
`live_gap_budget` tracking known gaps that are named but not yet fixed — the mutation-ledger
ticket sits in that budget today, named honestly rather than silently exempted.

## Try it by hand

```
python3 bin/dod-live-claim-gate --selftest                       # 3 fixtures: bad, good-not-done, good-deployed
python3 bin/dod-live-claim-gate docs/tickets/<name>.md            # grade one doc
python3 bin/dod-live-claim-gate                                   # grade every tickets/specs/audits doc
```

Fixtures live at `tests/fixtures/dod-live-claim/{bad,good,good-deployed}.md`. `--help` prints
this gate's own docstring and exits 0, same as every other script under `bin/` (the
`script-compiles` gate requires it).
