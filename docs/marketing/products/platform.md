# The Platform

> The mature IDP. Catalogue, identity, edge, secrets, model routing, traces,
> scheduling, supply chain, policy, and the agent interface — sold as one
> thing, because one is what it is.

## The problem

Every SaaS company past $20M ARR ends up needing the same five things: an
inventory of what is running, a portal where people find it, an identity
layer that holds them, a secret store that does not leak, and an audit log
that satisfies the auditor. Most companies past $50M ARR also need an LLM
gateway, a trace pipeline, a supply-chain audit, and a Zero-Trust boundary.

The default answer is to build them. The default answer is wrong. A
self-hosted Backstage hits the wall at 6–18 months (catalog drift, auth
integration, ticket backlog); a custom build never finishes; an "internal
platform team" becomes a full-time job for two engineers who would rather
build product.

The Platform is the mature answer. It is one thing, it has been running
in production since 2026-08-24, it is upgraded through Git, and the drill
runs hourly to prove the SLO is real.

## What you get

- **One inventory, two renderers.** A single YAML/JSON source is read by
  Backstage (the primary portal) and Datasette (the fallback). The two
  renderers share no runtime — if Backstage is broken, the buyer is on
  Datasette; if Datasette is broken, the buyer is on Backstage. *Benefit:
  one outage cannot take both renderers down.*

- **Identity, federated.** OIDC at the gateway (decision 0003); no password
  ever held for a person (decision 0007); SPIRE for workload identity;
  Tailscale for the tailnet. *Benefit: one identity layer, every surface.*

- **Edge, DNS, and certificates.** Traefik as the gateway, external-dns
  for the records, cert-manager for the renewal. One published URL on a
  tailnet. *Benefit: TLS, DNS, and routing are one operator's problem, not
  yours.*

- **Secrets, vault-backed.** External Secrets Operator reads from OCI
  Vault (or HashiCorp Vault, or AWS Secrets Manager). The Bitwarden bridge
  carries the human-side secrets the platform needs. *Benefit: no
  `Secret` literal in any manifest.*

- **Model routing, spend-bounded.** LiteLLM as the router, per-lane
  budgets, a spend breaker that tripped when a $0/minimax row bug drained
  $0.00 over 6 hours. *Benefit: a model bill is a model bill, not a
  surprise.*

- **Traces and audit.** Langfuse as the LLM trace, OTel as the fallback,
  SigNoz as the metrics + logs. The estate's collector is the receiving
  end. *Benefit: every model call, every prompt, every cost is a trace a
  buyer's engineer can open.*

- **Scheduling and supply chain.** Dagster as the scheduler (success-fail
  pings, freshness gates); GitHub Actions + Flux as the supply chain (SBOM,
  CVE scan, license gate). *Benefit: jobs run on a clock; releases run
  through a gate.*

- **Policy, enforced.** Kyverno at admission; Rego for the gates
  (license, placement, capacity). The `bin/idp-ci` chain refuses a
  namespace without a both-ways default-deny. *Benefit: a namespace that
  is not fenced is a namespace that does not exist.*

- **Agent interface, governed.** MCP + the Sovereign Bus. One door per
  agent, audited, identity-aware. *Benefit: an agent rollout is not a
  shadow-IT rollout.*

- **Drills, on a clock.** The drill is the SLO. Every drill is a workflow
  that proves a wall is a wall (zero-trust), that a probe is fresh
  (portal-freshness), that a door answers (door-probe). Hourly. *Benefit:
  the SLO is a number a buyer can read, not a slide a salesperson can
  read.*

## How it works

The platform runs on Kubernetes. It is delivered as Flux Kustomizations:
every capability is a row in `bin/idp-features plan`, every row has a
floor (CPU, memory, storage), and the plan says whether the combination
fits the node. The plan is computed, not hand-typed. A buyer with an
A1-4-16 node can run the lean tier; a buyer with an A1-6-24 node can run
the enterprise tier with traces, alerting, healing, and the full agent
stack.

The install wedge runs the whole thing on k3d in 30 minutes. The drill
runs hourly. The receipts land in the collector.

The catalogue is the asset; the portal is a renderer (the architecture
rule). If a renderer is wrong in a year, it is replaced and the platform
does not move.

## Why us

- **The catalogue is the asset, the portal is a renderer.** A buyer can
  replace the portal with another Backstage install, with a wiki, or
  with nothing — the inventory is what holds. *Benefit: lock-in is on the
  surface, not in the data.*
- **Two renderers, runtime-separated.** Backstage is node; Datasette is
  python. They run on different runtimes, on different ports, by design.
  *Benefit: a buyer is not stuck on a single point of failure.*
- **Drills are the SLO.** The platform does not say "99.9% uptime." The
  platform runs an hourly drill that proves a wall is a wall. *Benefit:
  the SLO is a number, not a slide.*
- **Decisions on the record.** 25 ADRs in `docs/decisions/`, each one a
  founder's ruling, dated, with the rejected road named. *Benefit: the
  buyer can read the architecture, not just the marketing.*

## Pricing

The Platform is sold as a managed deployment. Pricing is annual, tiered by
node size and feature tier.

| Tier | Price | What you get |
|---|---|---|
| Lean | $24,000/year | The lean tier from `features.yaml`: collector-only traces, Prometheus-only metrics, GitHub-issued alerts, no runbooks |
| Enterprise | $96,000/year | The enterprise tier: Langfuse + SigNoz, Robusta runbooks + k8sgpt, Temporal or Windmill, Hindsight memory |
| Platform | Contact us | The full estate: every feature on, every drill green, two-hats tenant split, the install wedge, dedicated support |

The Platform tier includes a SOC 2 conversation and a procurement-grade
security one-pager. We do not have SOC 2 Type II yet; the roadmap is on the
table.

## Get started

- **Run the install wedge.** `idp/quickstart` runs the whole Platform on
  k3d in 30 minutes. The drill runs hourly from the first minute. The
  screenshot is the case study.
- **Read the showcase.** `/showcase` renders the live estate bar (entities
  ELITE/GAP/BLIND), the per-system health donuts, the five Otto LIVE
  capabilities, and the buyer sandbox launch button. *Benefit: a buyer
  sees the platform do its job before they pay for it.*
- **Read the architecture.** `docs/explanation/architecture-overview.md`
  is the 60-second view; `docs/specs/backstage-as-a-product.md` is the
  product roadmap; `docs/decisions/` is the 25 ADRs. *Benefit: nothing
  is on a slide that is not on the record.*
- **Call us.** For the Platform tier, for a SOC 2 conversation, for a
  procurement-grade security one-pager, or for a custom deployment.

The Platform is the mature answer. Buy the platform; do not stitch one.
