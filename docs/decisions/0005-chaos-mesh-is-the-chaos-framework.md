# 0005. Chaos Mesh is the chaos-testing framework, delivered by Flux, gated by a steady-state probe

- Status: DECIDED 2026-08-25. Founder: "we need well designed chaos testing framework, research
  and see whats out there, open source". Manifests are in `platform/chaos/`; nothing runs until
  the OKE cluster from ADR 0004 exists.
- Date: 2026-08-25
- Deciders: founder (asked), session 1d (researched, recorded)
- Affects: `platform/chaos/`, `bin/idp-verify` (a future `chaos` row), the Backstage catalog

## The problem

Alerts here are reactive: a thing breaks, a person notices, a session fixes it (founder,
2026-08-25: "why are we always dealing with alerts"). Nothing on the estate fails on purpose,
so recovery paths are never exercised before they are needed. LAW 43 says buy the mature tool.

## Options considered

Compared on 2026-08-25 (GitHub API, CNCF project pages, image manifests on ghcr.io/quay.io):

| Tool | Licence / CNCF | Last release | arm64 images | Idle footprint | GitOps schedule | Steady-state probe |
|---|---|---|---|---|---|---|
| Chaos Mesh | Apache-2.0, Incubating | v2.8.4, 2026-08-18 | yes | ~360 Mi, no DB | `Schedule` CRD | `StatusCheck` CRD |
| LitmusChaos | Apache-2.0, Incubating | 3.31.0, 2026-07-15 | no (ChaosCenter needs MongoDB, no arm64 image) | >1.5 GB with 3 Mongo replicas | via ChaosCenter | probes, via ChaosCenter |
| Krkn | Apache-2.0, Sandbox | v5.2.7, 2026-08-18 | yes | none (CLI) | no reconciler | partial |
| Chaos Toolkit | Apache-2.0 | 1.20.0, 2026-08-08; 7 commits in 2026 | n/a (Python) | none | no in-cluster scheduler | yes |
| chaoskube / kube-monkey | MIT / Apache-2.0 | 2026-07 / 2026-08 | yes / unverified | tiny | Helm values only | none |
| PowerfulSeal | Apache-2.0 | 2021-09-17 | n/a | n/a | yaml | dead since 2023 |
| Steadybit, Gremlin | commercial | | | | | rejected: not self-hostable OSS |

## Decision

**Chaos Mesh v2.8.4**, installed by a Flux `HelmRelease` from `https://charts.chaos-mesh.org`
with `controllerManager.replicaCount=1`, `dashboard.create=false`,
`enableFilterNamespace=true`. The falsifiable reasons the others lose:

- Litmus needs a three-replica MongoDB with no arm64 image; the A1 worker is arm64 with 12 GB.
- Krkn and Chaos Toolkit have no in-cluster reconciler, so Flux cannot own the schedule.
- chaoskube and kube-monkey cannot express a steady-state probe, so a run has no verdict.

The first experiment is a `Workflow` that kills one Backstage pod while a `StatusCheck` polls
`/healthcheck` every 5 s with `abortWithStatusCheck: true`. The workflow's `Accomplished`
condition is the receipt. A `Schedule` runs it weekly with `concurrencyPolicy: Forbid`. Only
namespaces labelled `chaos-mesh.org/inject=enabled` can be targeted.

## Risk

`chaos-daemon` runs privileged as a DaemonSet. Mitigation: namespace filter on, dashboard off,
no network-chaos until a second experiment is written and reviewed.

## Done when

`kubectl -n chaos-mesh get pods` shows controller and daemon Running; `kubectl get workflow -n
backstage backstage-pod-kill -o jsonpath='{.status.conditions}'` shows `Accomplished=True`
after a scheduled run; that line lands in `crew/STATE.md`.
