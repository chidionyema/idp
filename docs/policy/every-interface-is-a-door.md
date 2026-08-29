# Every interface is a door

Founder ruling, 2026-08-29 (crew#307): "how was even a surface allowed into the estate without
being on Backstage", "is that not our inventory", "if a surface is not registered in the
inventory, the cluster must refuse to boot it". This page is the policy; the enforcement is the
cluster, not a person and not a script.

## The rule

1. **Anything that serves a port names its catalogue entity.** Every `Service` and every
   `HTTPRoute` outside the system namespaces carries Backstage's own link label,
   `backstage.io/kubernetes-id: <entity>`, where `<entity>` is the founder surface (the door a
   person opens) it belongs to, from `backstage/founder/catalog-info.yaml`.
2. **The control plane refuses the rest.** `platform/edge/require-catalogue-entity.yaml` is a
   Kyverno `ClusterPolicy` in `Enforce`: an object without the label is rejected at admission,
   whoever sends it (Flux, a workflow, a hand). Nothing can run outside the inventory.
3. **The live cluster is re-read every 15 minutes.** `platform/state/cluster-state.yaml` lists
   every live Service without the label (`services_unlisted`); `bin/idp-catalogue-drift` is
   `FAIL` on one and `BLIND` when the list is missing, never a clean row by omission.
4. **Every door is on the home page, in its group, on one screen.** `estate/group` on each
   surface is `Watch`, `Run`, `Build` or `Companies`; the home page renders one line per door
   under those headings, in that order. A surface without a group lands in `Other`, last, and
   `tests/test_incident_crew401_every_founder_surface_is_in_the_catalogue.py` refuses it.

## How each kind of interface gets its label

| Interface | Where the label is set |
|---|---|
| A manifest in git (`platform/**`) | `metadata.labels` on the Service / HTTPRoute |
| A Helm chart (`HelmRelease`) | a Flux `postRenderers` kustomize patch on the release, targeting `kind: Service` and `kind: HTTPRoute` |
| A Service an operator creates for itself (`prometheus-operated`, `alertmanager-operated`, tailscale `ts-*`, `k8sgpt-*`) | `platform/edge/catalogue-entity-exception.yaml`, by name; the operator's own Deployment is labelled through its release |
| A product repo deployed by Flux (`prospector` `deploy/k8s`) | labels in that repo, `company-<product>` as the entity |
| Something on the estate Mac (Dagster, Ollama, `catalog/ports.yaml`) | a founder surface whose links say where it is and how to reach it (`founder-dagster`, `founder-models-mac`); the Mac is not admission-controlled, the door is the inventory |

## What this replaced, and why

Until 2026-08-29 the only inventory check counted public hostnames
(`tests/test_incident_crew401_*`, `bin/idp-catalogue-drift`). Every UI without a public address
(Temporal, Alertmanager, Hindsight, Chaos Mesh, the status page) and everything on the Mac
(Dagster, Ollama) passed it in silence. A hand-typed list of interfaces was tried and rejected the
same day ("guard is novice", "you cannot be trusted to write your own guards"): a list only
catches what its author remembered. The label is the inventory; the API server is the guard.

## Proof

- Offline: `bin/idp-kyverno-render <platform dir>` applies every ClusterPolicy in git to every
  rendered object, Helm charts included; a missing label fails the offline gate on the PR.
- Live: the `catalogue-drift` row of the next `oke-check` run, and `services_unlisted` in the
  cluster-state receipt.
- Home page: `backstage/packages/app/src/modules/home/EstateHome.test.tsx` (`crew307`).
