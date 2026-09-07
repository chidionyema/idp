# Zero-Trust Estate

> The bundle for any enterprise running Kubernetes that wants Zero
> Trust without a CNI migration — Calico policy-only, audit-first
> enforcement, two-hats tenant split, drills on a clock.

## The story the buyer tells their board

> "Every pod's traffic is enforced by the network. Every tenant is in
> its own lane. Every drill proves the SLO is real. The CNI did not
> change. The audit ran for a day before the cutover."

That is the Zero-Trust Estate. Five products, one bundle, one story.

## What you get

The Zero-Trust Estate is the Platform + Zero-Trust Boundary + Two-hats
tenant split + Drills + the install wedge's audit-first posture.
Every component is a product on its own; together, they are the
answer a buyer's security team wants to hear when Zero Trust is on
the agenda.

| Component | What it does | Why it is in the bundle |
|---|---|---|
| **The Platform** | The IDP substrate: catalogue, identity, edge, secrets, scheduling, supply chain, policy | The audit log is the platform's, not the vendor's |
| **Zero-Trust Boundary** | Calico policy-only beside flannel, audit-first enforcement | The smallest change that turns 154 dormant NetworkPolicy objects into walls |
| **Two-hats tenant split** | The control-plane vs. tenant-plane boundary, end-to-end | A tenant's road does not widen the operator's road |
| **Drills** | Hourly drills that prove the walls are the walls | The SLO is a number a buyer can read |

## What the buyer sees

- **One CNI sidecar.** Calico policy-only beside flannel; the pod
  network keeps working through flannel. *Benefit: a CNI migration is
  not required.*

- **154 policies on at once.** The existing NetworkPolicy objects
  become walls. *Benefit: the gate a buyer already passed is the gate
  the cluster enforces.*

- **Log-only posture for one day.** The first day of install runs in
  log-only mode; would-be-denied flows are captured. *Benefit: a
  flag-day cutover is not an outage.*

- **Allow rules merged before enforcement.** The audit captures the
  flows a policy does not allow; the allow rules land before the
  cutover. *Benefit: a real-traffic outage is not a cutover surprise.*

- **Two-hats boundary.** The control plane and the tenant plane each
  carry their own policies; a tenant's policies cannot widen the
  operator's road. *Benefit: governance is the platform's default.*

- **Drills on a clock.** Every drill is a workflow that proves a wall
  is a wall. *Benefit: the SLO is a number a buyer can read.*

## How it works

The bundle is the install wedge with Calico policy-only installed.
The first 24 hours are log-only. The Calico logs capture every packet
the policies would deny. The audit step turns the logs into allow
rules for traffic a workload actually needs. The rules land in git
before enforcement flips.

The two-hats pattern (decision 0021) is the platform's default: a
tenant's MCP namespace is reachable no other way. The drills run
hourly; the receipts land in the collector.

## Why us

- **The smallest change that closes the defect.** A CNI migration is
  months; Calico policy-only is hours. *Benefit: the audit is the
  work, not the install.*

- **The audit step is the differentiator.** Most "zero trust in a day"
  pitches skip the audit and risk an estate-wide outage. We do not.
  *Benefit: the buyer is not paying for a cutover surprise.*

- **Drills are the SLO.** A drill runs hourly that proves a wall is a
  wall. *Benefit: the SLO is a number, not a slide.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $500/month, up to 1 cluster | The install wedge, the sidecar, the audit, the drills |
| Team | $5,000/month, up to 5 clusters | Multi-cluster, the allow-rule generator, Slack alerts on cutover |
| Enterprise | Contact us | Unlimited clusters, custom audit windows, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the bundle on
  k3d in 30 minutes. The drill runs hourly.
- **Read the spec.** `docs/specs/zero-trust-boundary.md` is the
  canonical design. `docs/specs/two-hats-tenant-split.md` is the
  multi-tenant boundary.
- **See it in action.** The estate's own cluster is in the install;
  the drill receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom audit window, or
  for a procurement-grade security one-pager.

The fences are not a decoration. The drill is the proof.
