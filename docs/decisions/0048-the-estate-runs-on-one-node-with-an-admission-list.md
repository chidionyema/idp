# ADR 0048  --  The estate runs on one node, and everything it runs is on a list

- **Status:** accepted
- **Date:** 2026-10-30
- **Supersedes:** nothing. **Refines:** ADR 0034 (workloads are placed by the free tier, not by the cluster)
- **Claim:** estate-agent/idp#7520

## Context

The incident of 2026-10-29 took the cluster's control plane with it, and the OKE entitlement
with it (`cluster-count=0`). There is no cluster to run anything on. The replacement is one
Ampere A1 VM on OCI Always Free  --  4 OCPU, 24 GB of RAM, one 200 GB boot volume  --  with k3s
on it and `local-path` for persistent volumes.

That VM is the whole of the Always Free allowance. So the question is not "how do we deploy"
but "does the estate fit", and the answer has to be measured, not asserted.

The live plane is unreachable, so the measurement is made against **the declaration in git**:
the manifests Flux would apply. That is the platform's declaration of intended state, and it
is the only authoritative source that survives the loss of the control plane. The inventory
is explicit about this: the live plane is blind, and the tool says so rather than pretending
otherwise.

## The measurement

`bin/idp-infra-inventory` reads every Flux Kustomization that points at this repository
(a row whose `sourceRef` names another `GitRepository` is somebody else's declaration and is
not ours to grade), renders each applied path with `kustomize build`, and measures the pod
specs that come out. It writes `inventory.json` and `inventory.md`.

The baseline, before any change:

| Measure | Value |
|---|---|
| Applied workloads | 85 |
| Replica-weighted CPU demand | 3,975 m |
| Replica-weighted memory demand | 12,080 Mi |
| HelmReleases with no declared requests | 16 |
| PersistentVolumeClaims | 4 (13,312 Mi) |
| Declared-only platform directories | 54 |

Eleven of the applied workloads ran two replicas. On one A1 VM the second replica lands on
the same silicon: it bought no availability and cost 485 m of CPU and 2,096 Mi of memory. All
twelve are now one replica, and the `crew#539` two-node HA comments that sat next to four of
them were replaced with this rationale, because a stale rationale in a manifest is a lie.

After that cut, and after the deletions below, the declaration is:

| Class | CPU | Memory |
|---|---|---|
| Resident (Deployment, StatefulSet, DaemonSet) | 2,245 m | 6,560 Mi |
| Scheduled (CronJob) | 695 m | 2,112 Mi |
| One-shot (Job) | 550 m | 1,408 Mi |
| Chart reserves (16 HelmReleases) | 2,525 m | 10,304 Mi |

## The honest answer: as declared, the estate does not fit

Concurrent demand  --  resident plus scheduled plus chart reserves  --  is **5,465 m of CPU and
18,880 Mi of memory** against a node that can hold **3,600 m and 21,504 Mi**. The surface as
declared is **1,865 m over**.

The memory would have fitted. The CPU does not, and it does not fit by a rounding error: a
single always-on Prometheus stack (600 m) plus Kyverno (250 m) plus Hindsight (200 m) is
1,050 m of that gap, and none of those three is worth a free node's third of its CPU.

So the answer to "does the estate fit one free node" is: **not as it is declared today.** The
estate fits one free node **after the refusals below are carried out**, and not before.

## The decision

Every applied workload is now either **admitted** (with a justification and a ladder rung
from ADR 0034) or **refused** (with a reason and the place its capacity goes instead). Both
lists live in `platform/infra-budget.yaml`, which is checked by the inventory gate. A
workload that is in neither list fails the gate: new infrastructure needs a justification, or
a refusal with a destination.

**Refused, ranked by how much of the node they were eating:**

| Workload | CPU | Memory | Why it leaves | Where it goes |
|---|---|---|---|---|
| `monitoring/kube-prometheus-stack` | 600 m | 2,560 Mi | a dashboard the free telemetry tier holds for nothing | Grafana Cloud free (rung 3) |
| `monitoring/blackbox` | 100 m | 256 Mi | the same probes run from the free tier | Grafana Cloud free (rung 3) |
| `kyverno` | 250 m | 1,024 Mi | the estate already refuses bad changes deterministically at write, commit and push | the laptop admission gate and the git pre-push hook (rung 5) |
| `hindsight` | 200 m | 768 Mi | a second memory layer; one of each layer is the rule | cut, merged into the estate's one memory layer (rung 1) |
| `backstage/catalogue` | 275 m | 576 Mi | the developer portal is not the founder's surface; `/fleet` is | the laptop developer portal (rung 5) |
| `research-engine` (CronJob) | 200 m | 512 Mi | a batch that wakes on a schedule and holds nothing between runs | a GitHub Actions schedule (rung 2) |
| `agent-workforce` (CronJob) | 225 m | 768 Mi | the same, with a repository artefact as its output | a GitHub Actions schedule (rung 2) |
| `ollama` | 150 m | 768 Mi | a third copy of the floor the cloud router already holds | the cloud router's free ollama floor lane (rung 1) |
| `searxng` | 50 m | 192 Mi | the exa-backed lane in the router answers the same queries | cut (rung 1) |
| 10  x  `estate-db-copy-*` Jobs | 500 m | 1,280 Mi | a per-application database copy for a product that is not on this node | the product's own deployment path (rung 2) |

**Admitted and fitting:** 3,415 m of concurrent CPU and 11,456 Mi of memory against 3,600 m
and 21,504 Mi. That is 185 m of CPU headroom and 10 GB of memory headroom  --  thin, but honest,
and the gate fails the moment it stops being true.

One-shot Jobs are excluded from the concurrent budget and reported separately: a Job's
request is a burst, not a standing claim on the node. They total 550 m and 1,408 Mi of burst.

Persistent volume storage is 13,312 Mi against a 120 GB allowance: fine. The node's own disk
is 200 GB with the same 120 GB reserved for persistent volumes.

## What was cut, and what was kept but reserved

Five directories that no Flux row applies and no executable references were deleted, with
their unused admission waivers, because a waiver with no release behind it is an unwatched
door:

- `platform/oci/autoscaler` (with `platform/edge/autoscaler-exception.yaml`)
- `platform/weave-gitops`
- `platform/coroot` (with `platform/edge/coroot-exception.yaml`)
- `platform/robusta` (with `platform/edge/robusta-exception.yaml`)
- `platform/keda`

`platform/keda` was the KEDA scaler. Its removal is why `platform/scheduling/balloon.yaml`
now says that the remaining headroom is the whole headroom, and why `platform/otto-gateway`'s
secret no longer names a robusta layer.

**`platform/spire` was not deleted.** It is declared-only, but the estate's intents, the
`spire-proof-run` libexec, the macOS agent's Brewfile and launchd entries, the one-scheduler
policy, the namespace fences, the catalogue and `sovereign/trust/spiffe.py` all still name it.
Deleting the directory here would strand live trust machinery for no capacity gain, so it is
recorded as **reserved** with a follow-on cut: the cut removes the layer and its references
together, or not at all.

Every one of the 47 declared-only directories now carries a `cut` or `reserved` decision with
a reason in `platform/infra-budget.yaml`. The gate refuses any that does not.

## What is not in this change

- The `estate-db` copy Jobs live under `platform/estate-db/**`, which another agent holds a
  live claim on. They are refused here by decision, but their manifests are untouched. That
  residue is named rather than hidden.
- The refusal list is a decision, not a deployment. Until each refused workload actually
  leaves, the node is still 1,865 m over. The node build waits on that movement.
- The live cluster is gone, so nothing here is proven running. It is proven *declared*: the
  gate reads the same manifests Flux would apply.

## Falsifiers

The gate ships with its own falsifiers, in `tests/test_idp_infra_inventory.py`, each of which
runs the real tool against a synthetic repository and proves it refuses:

- an applied workload that is neither admitted nor refused  ->  exit 1
- an admission with no justification  ->  exit 1
- a declared-only directory with no decision  ->  exit 1
- an admitted set over the node budget  ->  exit 1
- a budget value that has drifted from the manifests  ->  exit 1
- a chart with no reserve  ->  exit 1
- a refusal with no destination  ->  exit 1
- an applied path that cannot be rendered  ->  exit 2, blind

The tool's exit codes are the contract: **0** the estate fits and everything is decided,
**1** a policy failure the estate can fix, **2** blind  --  something could not be read, so
nobody can say the estate fits.

## Consequences

- The estate's declared surface drops from 5,465 m to 3,415 m of concurrent CPU by decision,
  not by wishful thinking. The gate keeps it there.
- The node is a single point of failure. That is accepted: it is free, and the estate's
  restart path is the sovereign bus, not the node.
- Any new workload must be added to `platform/infra-budget.yaml` with a justification or a
  refusal, or the gate fails. New infrastructure is now expensive on purpose.
- The chart reserves are envelopes, not measurements. A HelmRelease declares no pod template
  in git, so each reserve states its basis and its uncertainty, and a missing reserve is a
  finding  --  unknown capacity is not zero capacity.
