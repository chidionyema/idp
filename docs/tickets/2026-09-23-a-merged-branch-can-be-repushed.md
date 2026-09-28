# A merged branch can be re-pushed, and nothing refuses it

**Status:** open
**Opened:** 2026-09-23
**Laws:** LAW 38 (a fence a correct machine cannot satisfy is an outage),
against the standing defect class measured all session: *the system permits a state it has
already ruled against*
**Source:** measured 2026-09-23 while cleaning up 348 stale branches
**Depends on:** `bin/idp-branch-archive`, the repo rulesets, `.githooks/`
**Module:** `.github/`, `bin/`

---

## The gap

The repository sets `delete_branch_on_merge: true`, so GitHub removes a branch when its PR
merges. **Nothing prevents that branch name from being pushed again.** A push recreates it, and
the recreation is indistinguishable from the original — same name, same commit, no record that
it was already merged and deleted.

Measured on this repo, 2026-09-23:

    $ gh api repos/chidionyema/idp --jq '{delete_branch_on_merge, allow_update_branch}'
    {"allow_update_branch": true, "delete_branch_on_merge": true}

    $ gh api repos/chidionyema/idp/rulesets --jq '.[] | "\(.id) \(.name)"'
    21333351 estate-default-branch-protection
    23893236 estate-idp-agent-trunk
    21866528 founder-only-releases
    23860624 require-pr-for-all-branches

`require-pr-for-all-branches` requires a PR for every branch, and `delete_branch_on_merge`
removes merged ones. Neither refuses a re-push of a name that was already merged. **The state
"this branch was merged and deleted" is not remembered anywhere a push can consult.**

## Why it matters here specifically

This session produced 348 branches and 2,392 commits not in main. The population is not one
mistake repeated; it is a name space with no lifetime. `agent-trunk` reached 84 commits ahead of
main as the one branch exempt from the PR rule, which is the same defect with a second door.

A branch that can be recreated after merge has no end. Every cleanup is therefore temporary --
which is the finding: the 348 will come back unless the recreation itself is refused.

## Two mechanisms, and they differ in what they refuse

**Option A -- refuse a push that adds nothing.**

A `receive` hook that refuses when every commit in the pushed ref is already reachable from
`main`:

    git merge-base --is-ancestor <pushed-commit> refs/heads/main  ->  refuse

Surgical. It refuses only pushes that cannot add information, so it cannot block real work. The
check is mechanical and needs no branch-name memory, which is what makes it correct: a branch
recreated at the same commit is refused because its commits are in main, not because its name
was seen before.

**Option B -- refuse branch creation entirely.**

A ruleset with `restrict creations` over `~ALL`, with a bypass for the founder. Stronger --
it makes the 348 unrepeatable -- and blunter: it blocks every legitimate new branch too, which
is an outage risk under LAW 38 if the bypass is misconfigured.

**This ticket proposes A first**, because it cannot block correct work, and B only if A proves
insufficient. A and B are not exclusive.

## What is already in place, and what is missing

| mechanism | effect | state |
|---|---|---|
| `delete_branch_on_merge` | removes the branch at merge | **on** |
| `require-pr-for-all-branches` | every branch needs a PR | **on** |
| `bin/idp-branch-archive` | exists | present |
| a re-push refusal | refuses a redundant push | **MISSING** |
| a reaper for branches fully in main | removes accumulated zombies | **not scheduled** |

## Verification this ticket must satisfy

Two fixtures, the estate's shape:

- **Negative** -- push a commit that is already reachable from `main` on a fresh branch name.
  The push is **refused**, and the refusal names the commit and the fact that main already has it.
- **Positive** -- push a commit that is NOT in `main`. The push **succeeds**. A refusal that
  cannot tell these apart is a fence correct work cannot pass, which LAW 38 forbids.

A test that only checks the refusal does not prove the mechanism; it proves the mechanism blocks.
Both directions are the requirement.

## Evidence

- `gh api repos/chidionyema/idp` -- `delete_branch_on_merge: true`, `allow_update_branch: true`
- `gh api repos/chidionyema/idp/rulesets` -- four rulesets, none restricting creation
- The session's branch census: 348 branches, 2,392 commits ahead of `main` by ancestry
- `feat/orbstack-event-driven-agents`: 77 commits, 109 files, **net +12 lines, 0 new files** when
  diffed against main with two dots -- the example that shows a large branch can carry almost
  nothing, and that "commits ahead" is the wrong measure
