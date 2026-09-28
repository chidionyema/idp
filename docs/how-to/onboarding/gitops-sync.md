# Onboarding the GitOps drift engine

The estate runs this itself. This page is what you read to understand it, change
it, or check it is alive.

Spec: `docs/specs/2026-09-13-gitops-sync-engine.md`.

## What it is for

On 2026-09-13 the estate had six Kustomizations that were not Ready and a
HelmRelease whose health check had been timing out for twenty minutes. Nothing
said so. Six is not a small number and twenty minutes is not a short time; the
only reason anyone knows either is that an agent ran `kubectl get kustomizations`
by hand and read it.

Flux had reported all of it the whole time. What Flux cannot do is name the pull
request:

```
health check failed after 20m0.036186674s: timeout waiting for: [HelmRelease/temporal]
```

That names the symptom and the object. It does not name the change. So the person
who caused it is the person not told, and the one person who could fix it in a
minute.

This engine reads the drift Flux already knows about, finds the file that owns
each drifting object, joins it to the commit and pull request that last touched
that file, and delivers one message per pull request through apprise.

## The three steps

**1. Read.** `kubectl get kustomizations,helmreleases -A -o json`, and the object's
own `Ready` condition decides:

- `Ready: True` — not a drift. A watcher that reports a healthy estate is a
  watcher nobody reads.
- `Ready: False` — a drift, and the `reason` reported is Flux's own message,
  never a paraphrase. A paraphrase is a claim about what Flux said.
- **no `Ready` condition at all — not a drift.** An object that was just applied
  has not reported yet. Reading that silence as breakage is how a watcher pages
  on every apply.

**2. Attribute.** The object's kind decides how the owning file is found: a
`HelmRelease` is a document under `platform/**/*.yaml` whose `name:` matches; a
`Kustomization` is a document under `clusters/**/*.yaml`. The file is then joined
to `git log origin/main`, and the pull request is read off the squash-merge
subject (`... (#3284)`).

An object whose file cannot be found is reported **as unattributed**, with the
sentence explaining it. It is never dropped and never guessed at.

**3. Deliver.** One message per pull request, through
`apprise.notify`, the same channel `holmes_watch` uses. A pull request that broke
three objects gets one message naming all three.

## Running it by hand

```bash
bin/idp-gitops-drift                 # every drift, with its pull request
bin/idp-gitops-drift --json | jq .summary
bin/idp-gitops-drift --notify        # deliver through apprise
```

Exit codes, and they are the contract:

| code | meaning |
|---|---|
| `0` | every drift is unattributed — nothing to act on, or the estate is clean |
| `1` | at least one drift names a pull request — a person can fix this |
| `2` | **BLIND** — kubectl is missing or a list could not be read |

`2` is separate from `0` on purpose. "Nothing is drifting" and "nothing could be
read" must never print the same thing. That is the defect `bin/idp-compile-helm`
was written to end, where eleven of thirty-three charts failed to render and the
first version exited 0.

## How it is scheduled

It is a Dagster sensor, not a timer:

- sensor `gitops_drift_sensor` — polls every `ESTATE_GITOPS_POLL_SECONDS` (300)
- job `gitops_drift_job` → op `report_gitops_drift`

Dagster is the estate's one scheduler (`bin/idp-one-scheduler`). A launchd timer
running a shell script would be a second scheduler and a second delivery path,
and a thing with no memory of what it had already said.

**The fingerprint is the memory.** The sensor's `run_key` is built from the set
of drifts, not from the time. The same set is the same situation and is reported
once, however long it burns. A new drift joining makes it a new one.

## What it deliberately does not do

**It does not repair.** Reverting a rollout is `execute_change` and its graders
(MUM-288, decision 0028), where a proposal is made, graded and expires. A watcher
with a revert button has no grader and no expiry.

**It does not keep its own store of drifts.** The run_key is the memory. A third
place holding "drifts we have seen" is the stitching THE HEADLINE names.

## Tests

```bash
python3 -m pytest sovereign/tests/bdd/test_gitops_sync.py -q
```

Fourteen scenarios, offline and deterministic, graded against recorded Flux
status rather than a cluster — because a test that needs the estate up is a test
that is skipped exactly when the estate is down. They cover: a ready object is
not a drift; each of the three readings above; the fingerprint ignoring time and
respecting a new reason; attribution filling in a pull request, refusing to
invent one from a bare commit, and reporting an unfindable file as unattributed
rather than dropping it; one comment per pull request; and a comment never
claiming a cause it cannot name.
