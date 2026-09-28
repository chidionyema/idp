# A three-dot diff reports divergence, not absence — and reads as a finding

**Status:** open
**Opened:** 2026-09-23
**Laws:** THE EMPIRICAL PROOF RULE (do not report a number you did not measure this turn);
the standing defect class measured all session: **a plausible wrong number is worse than no
number, because it is acted on**
**Source:** three wrong measurements made in one session, all corrected by the fourth
**Module:** `bin/`, `docs/`

---

## The fault

`git diff origin/main...branch` and `git diff origin/main..branch` differ by **one character**
and answer **different questions**. The three-dot form diffs against the **merge base**; the
two-dot form diffs the **current trees**.

Three-dot therefore reports **everything the branch changed since it forked** — including files
main has since added by another route. Read as "what main lacks", it is wrong, and it is wrong in
the direction that inflates.

## Three wrong numbers, measured this session

| reported | command | why it was wrong |
|---|---|---|
| **1,329** "unique changes across 348 branches" | `git log -p --all --not origin/main` + `patch-id` | counts by **ancestry**. A branch whose content landed through a squash still reports its commits as ahead: `consolidate/all-outstanding` showed 91 commits ahead while `bin/idp-affected-graph` — a file from it — was already in main. |
| **40** "files main lacks: Efficiency Gateway, control loops, dag-gen" | `git diff --diff-filter=A origin/main...<branch>` | **three-dot.** On the fork date those files did not exist, so the branch legitimately "added" them. **Main added the same files by another route.** Verified: `platform/efficiency/` is 9 files on main; the control-loop registry and `bin/estate-dag-gen` are on main. `feat/orbstack-event-driven-agents` — 77 commits, 109 files — netted **+12 lines, 0 new files**. |
| **106,576** "files main lacks" | summing `add=` per branch across 348 | **summed instead of unioned.** Dozens of unrelated branches report `add=613` — the *same* 613 files counted once per branch. |

**The correct number, computed four ways, is 1,877** — the union of files present on any branch
and absent from main, each counted once.

## Why this is a ticket and not a typo

Every one of the three wrong numbers was **specific, plausible, and actionable**. 1,329 and
106,576 do not read as bugs; they read as findings. Work was proposed off the first one.

The estate has a rule for this shape already — *"do not report a number you did not measure this
turn"* — and it did not catch these, because the numbers **were** measured. They were measured
against the wrong reference.

**A number whose reference is unstated cannot be checked.** That is the actual defect: not the
arithmetic, the frame.

## What to require

1. **State the reference with the number.** "1,877 files main lacks, two-dot, unioned across 348
   branches" is checkable. "106,576 files" is not.
2. **Two-dot for absence, three-dot for divergence.** They answer different questions and only
   one of them is "what does main lack".
3. **Union across branches, never sum.** A per-branch count is a count of *branch-files*, not of
   files.
4. **A claim about absence must name a file that is absent.** `feat/orbstack` was reported as
   carrying the Efficiency Gateway; `git cat-file -e origin/main:platform/efficiency/__init__.py`
   would have refuted it in one command, in a second, before any merge was attempted.

## Evidence

- `git cat-file -e origin/main:platform/efficiency/__init__.py` → present (and 8 siblings)
- `git cat-file -e origin/main:platform/config/control_loop_registry.py` → present
- `git cat-file -e origin/main:bin/estate-dag-gen` → present
- `git diff --diff-filter=A --name-only origin/main..land/orbstack` after the merge → **0 files**
- `git diff --stat origin/main..land/orbstack` → `AGENTS.md | 11 +++`, `mkdocs.yml | 2 +-`
- The union computation: `for b in <348 branches>; do git diff --diff-filter=A --name-only
  origin/main..origin/$b; done | sort -u | wc -l` → **1877**
- The per-branch floor: dozens of branches report `add=613`; a summed total of 106,576 against a
  unioned 1,877 is the double-counting, measured.
