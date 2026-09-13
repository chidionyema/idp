# clean-tree: onboarding

## What it is for

Every gate in this estate answers a question about a tree. `bin/idp-clean-tree` answers whether
that tree is one the answer is true for.

It exists because of a measured failure. On 2026-09-12 an agent session ran
`bin/idp-rules run --plane ci` four times from the shared primary checkout and reported three
defects to the founder. All three were another session's work in progress:

- `defs-load-by-path` reported BLIND — the checkout had no `.venv`
- `sleep-ban` reported 14 LAW 14 violations — that rule does not exist on main
- `rule-coverage` reported a stale ledger — the ledger on main is accurate

A clean worktree off `origin/main` reports exit 0, 74 rules ok, no FAIL, no BLIND.

## What it costs

Nothing. It reads `git status --porcelain` and exits. No network, no cluster, no daemon.

## Where it lives

    bin/idp-clean-tree            the gate
    rules.yaml                    row `clean-tree`, planes ci and session
    tests/fixtures/clean-tree/    bad.json, good.json, midmerge.json

## How to run it

    bin/idp-clean-tree                 # the checkout this runs in
    bin/idp-clean-tree --path DIR      # another
    bin/idp-clean-tree --explain       # what it checks, and why

Exit 0 clean, 1 refused, 2 BLIND (not a git checkout, so nothing could be judged).

## What it refuses, and what it must never refuse

**Refused:** the shared primary checkout carrying uncommitted work; any checkout mid-merge
(`UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD`).

**Never refused (R38 — a guard that refuses correct work is an outage):** an ordinary dirty
worktree, any feature branch, and machine-specific noise (`.venv/`, `.agent/`, `.DS_Store`,
`__pycache__/`, `.pytest_cache/`, `node_modules/`).

## How to stop it

Remove the `clean-tree` row from `rules.yaml`. The gate is one row and one script; nothing else
depends on it.

## The habit it enforces

`docs/policy/no-agent-works-in-the-main-checkout.md` has been policy since 2026-09-07. This is
its enforcement: work wherever you like, but **grade in a worktree cut from `origin/main`.**

    git worktree add /tmp/wt-verify origin/main
