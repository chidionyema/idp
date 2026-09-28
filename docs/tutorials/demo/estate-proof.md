# estate-proof — the git+cluster join, seen running

This is what the join does when you run it, with the real output.

## What it is

Every prior answer to "what's been built and is it live" was an agent reading git, reading the
cluster, and narrating a join between the two by eye — a fresh, LLM-computed judgment call every
single time it was asked, and never the same answer twice run to run.

`bin/estate-proof` is that join done once, in code, deterministically:

- **Source A — git**: every commit on `origin/main` in the lookback window, filtered by commit
  **author** (not committer — every squash merge shows committer `GitHub` for everyone, so
  committer carries no bot signal at all).
- **Source B — cluster**: every live Flux `Kustomization`, its `spec.path` (which part of the
  repo it applies) and its live `status.lastAppliedRevision` SHA, read straight off the object.
- **Join key**: `git merge-base --is-ancestor <commit> <kustomization's applied SHA>` — a
  mechanical ancestry check. No model judges whether something "seems deployed."

## See it

```console
$ bin/estate-proof --days 10
SHA       DATE        AUTHOR            STATUS                                  SUBJECT
b401c30b  2026-09-15  Chidi Onyema      live @ backstage (089527f1)             fix(backstage): fleetview-backend liveness/readiness probes
f51dde1c  2026-09-15  Chidi Onyema      live @ backstage (089527f1)             FleetView backend: real sidecar deployment in the catalogue
0bf0ec68  2026-09-15  Chidi Onyema      owning Kustomization never reconciled (owner: via-negativa)  fix(via-negativa): stop duplicating the $imagepolicy marker
1d7d6d5c  2026-09-15  Chidi Onyema      no Kustomization owns a path this commit touched  feat(fleetview): triage panel and merged focus timeline on /
...
473 human commits in 10d, 214 confirmed live by Flux-applied-SHA ancestry, 259 not.
```

Three outcomes per commit, all mechanical:

1. `live @ <kustomization> (<sha>)` — the commit is an ancestor of what Flux actually applied.
2. `not live yet (owner: <kustomization>)` — the owning Kustomization exists and has reconciled
   something, just not yet past this commit.
3. `owning Kustomization never reconciled` / `no Kustomization owns a path this commit touched`
   — either the owning Kustomization has no applied SHA yet, or the commit only touched paths
   (docs, specs, runbooks) that no Kustomization deploys at all — which is correct, not a gap.

`live` does not mean the resulting pod is healthy — it means Flux applied that manifest change.
Pod/workload health is a separate check (`bin/idp-kube get pods ...`); this tool answers one
question only: is this commit's change the one currently applied in the cluster.

## Try it by hand

```
bin/estate-proof                 # last 10 days
bin/estate-proof --days 30        # wider window
```

Read-only: two `bin/idp-kube` calls and local `git log`/`git merge-base`, no cluster writes.
