# Incident report: the policy webhook refused every new pod for 43 hours, and nobody saw the root

Date: 2026-08-30. Author session: 41fd24d8. Founder words that opened this report, 08:0xZ:
"why was it down and why did it take us 2 days to figure out it was down", "can we write up
incident report also". Every receipt below names the run or ticket it was read from.

## What the founder saw

The Estate Mac tab in Backstage (`/screen/`, the remote-hands door to his own Mac) did not work
from 2026-08-28 midday to 2026-08-30. He turned Screen Sharing on, was told "ready" once
(wrongly), and was still looking at a dead tab two days later. Behind the same fault: the private
network operator (Tailscale) never upgraded, the alerting pods (alertmanager, prometheus) had no
endpoints, and 41 Flux objects sat not-Ready, so fixes merged by other lanes never rolled.

## Timeline (UTC)

| When | What | Receipt |
|---|---|---|
| 08-28 12:43:47 | HelmRelease tailscale/tailscale-operator turns UpgradeFailed. Its ReplicaSet operator-56cf79864d reads `Error creating: admission webhook "validate.kyverno.svc-fail" denied the request:` — an EMPTY reason — and repeats it every ~16 min from here. Same for healing/estate. | diagnose run 33297528033 |
| 08-28 (same window) | The CNI is swapped from Cilium to flannel; the kyverno admission pod keeps its old sandbox. `kustomization/edge` reads `failed calling webhook "mutate-policy.kyverno.svc": Post "https://kyverno-svc.kyverno.svc:443/policymutate?timeout=10s": EOF`. kyverno-admission-controller reports 1/1 Available the whole time. | diagnose run 33297528033; `kube-flannel-ds` present, no cilium pods |
| 08-28 → 08-30 | monitoring alertmanager and prometheus Services have no endpoints (their pods cannot be created either). No alert fires. | diagnose run 33297528033, `--- endpoints` |
| 08-29 20:35 | A peer session diagnoses "kyverno webhook denies the operator pod with an empty reason + vault entry tailscale-operator missing" on crew#633. No owner is named; nobody claims it. | crew#633 |
| 08-30 05:5x | Founder: "also estate mac tab not not working". | friction relay, crew feed |
| 08-30 06:2x | This session tells the founder the tab is "ready" from a port-5900 probe and a 302. Founder: "are u sure", "it was on when i looked". Retracted on crew#562. | crew#562 comment 5467142516 |
| 08-30 06:4x | apply run 33296889510 proves the vault entry `tailscale-operator` exists and exchanges; the credential lead is closed. The webhook is the one fault. | run 33296889510 |
| 08-30 06:5x | diagnose 33297528033 read in full: empty-reason denials + EOF to the webhook = the class of run 33133317589 (webhook pods in a dead sandbox after a CNI change), which cilium-unchain fixed with two `rollout restart` steps. | run 33297528033, bin/idp-oke-break-glass pb_cilium_unchain |
| 08-30 07:2x | Fix built: playbook `webhooks-restart` (attribute from events, restart the two webhook deployments, reconcile edge/secret-store/tailscale/guacamole, breaker 2 per 6 h). | this branch |

## Why it broke

kyverno's admission webhooks are registered with `failurePolicy: Fail`. When the CNI changed, the
admission pod's network sandbox died but the pod stayed Running and Ready (its probes are
answered from inside the pod, not across the cluster network). The API server could not reach it,
so every mutating or validating call ended in `EOF`, and every pod create in a namespace the
policies match was refused with an empty message. The refusal *looks* like a policy decision; it
is a transport failure wearing a policy's name.

## Why it took 43 hours

1. **The failure lied about itself.** An empty denial reason reads as "a policy said no"; a 1/1
   Available deployment reads as "kyverno is fine". Two sessions chased a credential (real, but
   secondary) and a policy diff. The fact that names the class — an empty reason means the
   webhook was unreachable — was in nobody's head and no test.
2. **The alarms were victims of the same fault.** The alerting pods could not be created
   either, so silence looked like health. (Silent green, the estate's third-largest class.)
3. **The state view has no ranking.** cluster-state prints 41 not-Ready rows with the root
   (a webhook nobody can reach) indistinguishable from the 40 symptoms beneath it.
4. **Nobody owned it.** The correct diagnosis sat on crew#633 for 11 hours with no owner.
5. **The only fix was welded to a bigger hammer.** The two restart lines lived inside
   cilium-unchain, which also rewrites CNI files on every node; with flannel live nobody ran it.
6. **A wrong "ready" cost the founder a round trip.** A port being open is not the door working.
   Infra claims come from the surface itself (memory: infra-claims-are-certain-or-unsaid).

## What changes so this is once

- `webhooks-restart` playbook: one button in the oke-check tile; refuses to act unless the
  cluster's events show the fault; breaker-limited. Test:
  `tests/test_incident_crew633_webhooks_restart_attributes_then_heals_with_a_breaker.py`.
- Owed next (crew#633 CP2): an `admission-refusals` row in the cluster-state drill that goes RED,
  above every symptom row, when any `FailedCreate` event carries an empty admission reason or a
  `failed calling webhook` message — the check that would have found this in the first 16 minutes.
- Owed (crew#633 CP3): kyverno admission controller at 2 replicas with a PodDisruptionBudget,
  so one dead sandbox is not a cluster-wide refusal; or `failurePolicy: Ignore` on the mutate
  webhook with the validate webhook kept strict — the smaller road, decided with a measurement.

## Founder-facing summary

The cluster's policy checker went unreachable after a network-layer change and, by design, refused
every new pod rather than let one through unchecked. The refusal message was blank and the checker
reported itself healthy, the alarms were among the pods it refused, and the one diagnosis that was
right had no owner. Repair is now one button; the detector that ranks this above its symptoms is
the next checkpoint.
