# Onboarding: estate-drift-reconciler

## What it is

`bin/estate-drift-reconciler` reads a repository's open pull requests and
reports the ones that have drifted and need reconciliation — drafts that were
never finished, and open PRs that have sat stale past a threshold. It is slot 4
of the seven-agent local ops tier (crew#929, roster in
`docs/ops/local-ops-tier-roster.md`).

## Why it exists

Every session a human reconciles "what is still open, what is draft, what has
been sitting unmerged" so finished work is not stranded. A reporter that reads
that state deterministically takes the scan away and, run as a gate, is what
notices drift before a branch is forgotten.

## What it reads

It calls `gh pr list` for open pull requests and reads each one's number, title,
created date, and draft flag. It makes no write calls and reads no secrets.

## Usage

- `bin/estate-drift-reconciler` — report drift on `chidionyema/idp`.
- `bin/estate-drift-reconciler --repo owner/name` — another repository.
- `bin/estate-drift-reconciler --check` — exit 1 when drift is present (a
  gate the ops tier can use), 0 when clean.
- Thresholds: `--stale-days N` or `ESTATE_DRIFT_STALE_DAYS` (default 14).

## The contract

- A draft pull request and an open PR past the staleness threshold are each an
  actionable finding with an action line.
- The reconciler reports only — it never closes, merges, or deletes. Deleting a
  branch belongs to a suggest-only cleaner slot, never to this one.
- State is read live each run; nothing is cached or guessed, so the report is
  always about the repo as it is now.
