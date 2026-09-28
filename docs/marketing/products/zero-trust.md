# Zero-Trust Boundary

> Calico policy-only mode, audit-first enforcement — the smallest change
> that turns 154 dormant NetworkPolicy objects into walls.

## The problem

You have a Kubernetes cluster. You wrote 154 NetworkPolicy objects.
They look right; they read right; they pass the gate (`bin/idp-ci`
refuses a namespace without both-ways default-deny). They enforce
nothing. The cluster runs flannel, which does not implement
NetworkPolicy. The fences are a decoration.

You could migrate to Cilium. You could rewrite the 154 objects. You
could add Calico as a CNI and rewrite every workload's network. None of
these is small; each is an outage waiting to happen.

The Zero-Trust Boundary is Calico policy-only mode beside flannel — the
combination that has shipped as Canal for a decade. It turns all 154
existing policies on at once and rewrites none of them. It is not a CNI
migration; the pod network keeps working through flannel; it is the
smallest change that closes the defect.

The audit step is the differentiator. A flag-day cutover is an
estate-wide outage with 154 causes. The Zero-Trust Boundary is
log-only posture for one full day, then enforce.

## What you get

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

- **Drills on a clock.** The drill is the SLO. A drill runs hourly that
  proves a wall is a wall (a probe that could not run is a fail-closed
  FAIL, never a pass). *Benefit: the SLO is a number a buyer can read.*

- **The two-hats pattern.** The control plane and the tenant plane
  each carry their own policies; a tenant's policies cannot widen the
  operator's road. *Benefit: governance is the platform's default.*

## How it works

Calico policy-only is installed beside flannel. The flannel data plane
stays; Calico is the policy plane. Every existing NetworkPolicy object
is enforced without rewrite.

The first 24 hours are log-only. The Calico logs capture every packet
the policies would deny. The audit step turns the logs into allow rules
for traffic a workload actually needs. The rules land in git before
enforcement flips.

The drill runs hourly. The drill is a workflow that opens TCP to a
destination the fences deny, and fails unless it is refused. A probe
that could not run is a fail-closed FAIL, never a pass.

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
| Solo | $200/month, up to 50 policies | One cluster, the sidecar, the audit, the drill |
| Team | $2,000/month, up to 500 policies | Multi-cluster, the allow-rule generator, the Slack alert on cutover |
| Enterprise | Contact us | Unlimited policies, custom audit windows, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any cluster with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Zero-Trust
  Boundary on k3d in 30 minutes. The drill runs hourly.
- **Read the spec.** `docs/specs/zero-trust-boundary.md` is the canonical
  design. Step 1 is the measured defect; Step 2 is the remedy.
- **See it in action.** The estate's own cluster is in the install. The
  drill receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom audit window, or
  for a procurement-grade security one-pager.

The fences are not a decoration. The drill is the proof.
