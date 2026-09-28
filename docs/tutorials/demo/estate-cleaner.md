# Demo: estate-cleaner

`bin/estate-cleaner` is slot 6 of the estate's local ops tier (crew#929). It
proposes cleanup — specifically, remote topic branches that have no open pull
request and are likely dead ends a human may want to archive. It is strictly
suggest-only: it returns candidates and who must confirm, and it never deletes
a branch or force-pushes. The intentional archive namespace (`backup/`,
`archive/`) is excluded, because that is the recycle bin, not drift to re-propose.

```
$ bin/estate-cleaner
estate-cleaner: 205 topic branch(es) with no open PR = archive candidates (--dry-run; never deletes)
  SUGGEST archive branch 'adr-0003-findings' (no open PR); owner to confirm before any delete.
  SUGGEST archive branch 'deepseek-build-lane' (no open PR); owner to confirm before any delete.
```

A real branch with no live PR is surfaced as an archive candidate; `backup/`
branches are not re-proposed. The cleaner's whole output is a proposal list with
an owner-confirm line on every row. A suggestion with no review line is a
refusal, not a pass — the no-op contract.

The cleaner never runs a destructive command. Look at the proposal, decide, and
only a human (or an explicitly authorized driver) archives a branch:
```
$ git push origin --delete some-branch-that-you-confirmed
```
The cleaner only ever printed the suggestion; it did not and cannot do that.
