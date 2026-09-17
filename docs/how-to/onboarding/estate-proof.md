# Onboarding: estate-proof

## What it is

`bin/estate-proof` is the one deterministic join between git and the live cluster. Before it
existed, "what's been built in the last N days and is it actually live" was answered by an agent
reading `git log` and `bin/idp-kube` output live and narrating a join between them — a fresh,
non-reproducible judgment call every time, and the exact ad-hoc pattern the estate is trying to
stop repeating. This script computes that join in code; an agent reads its output, it does not
recompute the join by eye.

| Step | Mechanism |
|---|---|
| Which commits count as work | `git log --pretty=... origin/main`, filtered by commit **author**, not committer (a squash merge always shows committer `GitHub`; author is the real human/bot signal) |
| What is actually live | `bin/idp-kube get kustomizations -n flux-system -o json` — each `Kustomization`'s `spec.path` and live `status.lastAppliedRevision` SHA |
| The join | `git merge-base --is-ancestor <commit sha> <kustomization applied sha>` per commit, scoped to Kustomizations whose `spec.path` is a prefix of a path the commit touched |

No LLM call is in this path. The script either finds a mechanical ancestry relationship or it
doesn't; there is no "probably deployed."

## How it runs

Today: on demand, `bin/estate-proof [--days N]` (default 10). It is read-only — local `git`
plus `bin/idp-kube` reads, no cluster writes, no new schedule, no new store (extends nothing,
adds nothing per THE HEADLINE — it is a script, not a service).

## Try it by hand

```
bin/estate-proof                  # last 10 days, the founder's own "past 10 days" window
bin/estate-proof --days 30        # wider window
```

Output is one row per human commit in the window: `live @ <kustomization> (<sha>)`,
`not live yet (owner: <kustomization>)`, or a named reason nothing owns that path. The summary
line at the end gives the three counts: human commits, confirmed live, not live.
