# The scheduler survives a node, and the judge that said it already did

Date: 2026-09-02. Change: [pull request 1138](https://github.com/chidionyema/idp/pull/1138). Debt: [issue 1136](https://github.com/chidionyema/idp/issues/1136).

## What broke

The dagster HelmRelease upgrade stalled: the cluster's admission policy refused the
estate-scheduler Deployment. The dagster namespace is founder-facing, and the
availability standard (crew#555, crew#307) says a founder-facing Deployment runs two
replicas spread across nodes, so one node dying never takes the surface down. The
scheduler ran one replica with no spread, so admission said no, and the whole
upgrade — dagster, then notify and otto-staging behind it — wedged. The refusal is
recorded in [the cluster check run that caught it](https://github.com/chidionyema/idp/actions/runs/33618879684).

## Why the gate said it was fine

The offline judge that grades every pull request renders the chart and runs the same
policies — but it runs them without knowing any namespace labels. The availability
policy selects namespaces by label, so offline it silently skipped every rule and
printed a clean pass on the exact Deployment the live cluster refused. A green that
cannot fail is not a green. The judge fix (feeding the namespace labels to the
offline run) is proven locally and lands in a follow-up change, because it also
exposes nineteen platform directories with the same latent refusal, and unwedging
the cluster could not wait for that cleanup.

## What this change does

- The estate-scheduler runs two replicas, required to land on different nodes, with
  a rollout strategy that may take one replica down at a time — so an upgrade or a
  node drain always has somewhere to go (crew#307).
- The webserver runs two replicas with a spread rule added after rendering, because
  the chart offers no setting for it.
- The daemon stays a singleton on purpose: two daemons fire every schedule twice,
  and the upstream project ships no leader election. A scoped policy exception
  records that, and [issue 1136](https://github.com/chidionyema/idp/issues/1136)
  carries the debt until upstream offers a safe second replica.

## What it costs

Two extra pods: about 200m CPU and 1.25Gi memory of standing requests on the same
node pool. No new nodes.
