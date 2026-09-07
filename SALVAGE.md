# What was rescued on 2026-09-07, and where it is

Work was scattered across one laptop: branches the server had never seen, a shared stash
nobody owned, and source files that were in no branch at all. None of it is deleted and
none of it had to be judged in a hurry. Every piece was copied to the server first.

## Where each thing went

| what was stranded | how many | where it is now |
|---|---|---|
| local branch tips no remote ref contained | 138 | tags `safety/20260907T1628Z/branch/<branch>` |
| entries on the shared stash | 15 | tags `safety/20260907T1626Z-stash-NN` |
| uncommitted edits in live checkouts | 2 worktrees | tags `safety/20260907T1625Z-<worktree>` |
| untracked source in no branch at all | 8 files | tag `safety/20260907T1626Z-untracked-source`, and restored onto this branch |
| the four commits blocking session start | 4 | `chidionyema/claude-guards` pull request #250 |

List them with:

    git ls-remote --tags origin 'refs/tags/safety/*'

Recover one with:

    git switch -c <a-name> <tag>

## The loose source on this branch

`backstage/plugins/custom-entity-extensions/` and `backstage/packages/app/src/modules/home/`
were untracked in the primary checkout -- real code with real tests, in no branch, on one
laptop. They are restored here so they are findable. They are **not** reviewed and **not**
proposed for `main` by this branch; whoever wrote them lands them properly.

## Nothing was popped

The stash still holds all fifteen entries. Tagging reads a commit that already exists; it
does not consume it. `git stash list` is unchanged.

## What stops the next one

`docs/policy/no-agent-works-in-the-main-checkout.md`, and the `rule-guard.py` refusals it
names.
