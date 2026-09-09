# Demo: estate-drift-reconciler

`bin/estate-drift-reconciler` is slot 4 of the estate's local ops tier
(crew#929). It reads the real branch/PR state of a repo and reports drift that
a human — or the ops tier — should reconcile: pull requests that are still a
draft, or that have sat open past a staleness threshold. Deterministic and
model-free: it reads `gh` and reports an action line per finding. It never
closes, deletes, or changes anything; it only reports.

Run it against the current repo state:

```
$ bin/estate-drift-reconciler
estate-drift-reconciler: 1 actionable item(s) on chidionyema/idp (2 open PRs read, stale threshold 14d)
  [draft] #2624 DRAFT: chore(inventory): estate sweep 9.1, orphaned fil
```

A draft or stale pull request is named so the work does not sit unmerged and
get lost — the "reconcile branches and tickets before they strand" scan that
recurs in every session. Use the report as a gate so the ops tier notices
drift automatically:

```
$ bin/estate-drift-reconciler --check ; echo "exit=$?"
exit=1    # drift present -> the tier flags it; 0 would mean clean
```

Point it at another repository or change how stale "stale" is:

```
$ bin/estate-drift-reconciler --repo chidionyema/crew --stale-days 7
```

The reconciler reads pull-request state only (number, title, created date,
draft flag) and never touches a secret or a branch head. Reporting drift is its
whole job; the separate cleaner slot is where a deletion would ever be proposed,
and even that only as a suggestion.
