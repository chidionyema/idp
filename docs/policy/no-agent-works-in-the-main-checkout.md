# No agent works in the primary checkout

Founder, 2026-09-07, in
`~/.claude/docs/founder/2026-09-07T1630Z-you-are-experiencing-multi-agent-state-collision-35fa6b38.md`:

> No agent is allowed to execute work in the primary main checkout directory. Every new
> task must be executed in a dedicated, isolated git worktree.

## What went wrong

Several sessions ran in the same directory. One left uncommitted edits; the next woke up
in that directory, found files it did not write, and asked the founder to choose between
stashing them, committing them, and leaving them. All three answers are wrong.

Stashing is the worst of them. `refs/stash` is a single list shared by every worktree and
every session on this machine, so stashing buries another session's work in a place that
session will never look. On the day this was written the list held fifteen entries and
nobody could say whose the oldest were.

Committing puts one session's edits into another session's branch. Leaving them carries
them onto the new branch, where they collide.

By the time that question is being asked, the mistake has already happened: two threads of
work were sharing one directory.

## The rule

A branch gets a directory. `git worktree add <dir> -b <branch> origin/main` creates one, the
primary checkout never moves, and the question above cannot arise -- there is nothing to
stash, because nothing is being switched.

The primary checkout holds `main` and stays clean. Work happens elsewhere.

## What enforces it

`rule-guard.py` refuses, at the moment the command is typed:

- `git stash push` and `git stash save`, pointing at the safe copy instead
  (`git stash create` writes a commit object and touches neither the working tree nor the
  shared list, so it stays allowed);
- switching branches in a checkout with uncommitted changes, naming how many files would
  ride along;
- committing in the shared checkout, which it already refused before this.

## Taking a safety copy without disturbing anyone

    snap=$(git stash create)
    git tag safety/<what-it-is> "$snap"
    git push origin safety/<what-it-is>

Nothing is popped, no working tree changes, and the work is on the server. This is how the
2026-09-07 rescue moved 138 local-only branch tips, 15 stash entries and a loose Backstage
plugin off the founder's laptop without touching a single file anyone was holding.
