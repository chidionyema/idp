# The GitOps synchronization engine: a drift that cannot name its cause is not found

Status: **built** (sensor, contract, tests). Written 2026-09-13.

## The failure this exists to end

On 2026-09-13 the estate had six Kustomizations that were not Ready, and
`HelmRelease/temporal` had been failing its health check for twenty minutes. Nothing
said so. The number was found by hand, once, in a shell command, by an agent that
happened to look. A drift that is found by looking is found once.

Worse is the shape of what it reports. Flux says:

```
health check failed after 20m0.036186674s: timeout waiting for: [HelmRelease/temporal]
```

That names the symptom and the object. It cannot name the pull request. So the
person who caused it -- who merged a values change an hour earlier and has since
moved on -- is the one person who is not told, and the one person who could fix it
in a minute.

This is the same class as the langfuse 1000m defect that stayed in the estate for
five days: **the estate knows the current state and does not know how it got
here.** The compiled-infrastructure gate closes that gap before a merge, by
refusing a pull request whose compiled output disagrees with what it claims. This
closes it after a merge, by carrying the drift back to the pull request that
caused it.

## What it does

Three steps, in order, each one able to refuse:

1. **Read the drifts.** Flux's own `Kustomization` and `HelmRelease` status, read
   from the cluster API. A Kustomization whose `Ready` condition is not `True`, and
   a HelmRelease that is not `Ready`, are both drifts. Not a second source of
   truth, not a scrape of the same data into a store: the objects Flux already
   writes.

2. **Isolate the cause.** For each drifting object, find the commit on `main` that
   last changed the file that owns it, and the pull request that commit came from.
   Attribution before repair: the estate may only say "this pull request caused
   this" when it can point at the file and the commit.

3. **Comment back on the merged pull request.** One comment per pull request,
   carrying every drift currently attributed to it, updated in place so a pull
   request that is re-broken does not collect a thread.

## Why it is a sensor and not a script (LAW 1, LAW 43)

`holmes_watch.py` already does this shape and is the proof it works: a Dagster
sensor polls a live source (Alertmanager), fingerprints the situation so one
outage is one investigation, isolates a cause with a model, and delivers through
`apprise.notify`. This is that same shape pointed at Flux instead of Alertmanager,
and it adds no component: Dagster already schedules it, GitHub already receives
the comment, Flux already knows the drift.

A shell script that ran `kubectl get kustomizations | grep -v True` and posted to
Slack on a launchd timer is the stitched solution: it would be a second scheduler
(LAW 43, `bin/idp-one-scheduler` names exactly this), a second delivery path, and
it would have no memory of what it had already said.

## The contract

`drift_fingerprint(drift)` is one id for one drift, built from the object's
identity and its failure reason, **never from when it was seen**. The same
Kustomization failing for the same reason is the same drift however long it has
been broken; a different reason is a new one worth saying out loud. This is
`alert_fingerprint`'s rule and it is what stops a broken object paging the founder
every five minutes for a day.

`attribute(drift, commits)` takes the drifts and a mapping of file path to the
commit that last touched it, and returns each drift with `commit`, `pull_request`
and `file` filled in, or explicitly `None` with a `reason`. An object whose owning
file cannot be determined is reported as unattributed **and said to be
unattributed** -- never silently dropped, and never guessed at.

`comment_body(pull_request, drifts)` is the text posted. It names the object, the
reason Flux gave, the file, and what to do. It never claims a cause the evidence
does not carry.

## What was deliberately not built

- **A second drift store.** The existing evidence layer (Aevum) and the existing
  memory bank (Hindsight, `MUM-285`) both hold things. A third place that holds
  "drifts we have seen" is the stitching THE HEADLINE names. The sensor's run_key
  is the memory.
- **A new scheduler.** Dagster is the estate's one scheduler; this is a sensor in
  the scheduler that exists.
- **Automatic repair.** The estate may revert a rollout it can prove is bad, and
  that decision belongs to `execute_change` and its graders (`MUM-288`), not to a
  watcher. This reports; it does not act.

## Done command

```
python3 -m pytest sovereign/tests/bdd/test_gitops_sync.py -q
bin/idp-gitops-drift --json | jq '.summary'
```

The first proves the contract both ways offline. The second reads the live estate
and prints how many drifts, how many attributed, how many unattributed -- and
exits non-zero when a drift is attributed, because a drift with a named cause is
something to act on.
