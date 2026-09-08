# Secrets Bridge

> A Bitwarden-to-Vault bridge for enterprises where operators hold
> shared credentials in a personal vault and workloads need them as
> Kubernetes secrets — the only "personal vault bridges to workload
> vault" pattern in market.

## The problem

Your operators hold shared credentials in Bitwarden. Your workloads
need them as Kubernetes secrets. The two stores do not talk to each
other. The bridge is whatever a person copy-pastes this morning, which
is a leak waiting to happen.

You could move everything to Vault. You could move everything to
Bitwarden. You could stand up a CI job that reads Bitwarden and writes
Kubernetes secrets, with the audit log being whatever the CI happened
to print. None of these is governance.

The Secrets Bridge is the pattern, packaged. A Bitwarden-side operator
that watches a project; an ESO bridge that reads the watcher and
writes a Kubernetes `Secret`; an audit log that lives in the
collector.

## What you get

- **One operator on each side.** Bitwarden side: an operator that
  reads the project and exposes the secrets. Kubernetes side: an ESO
  bridge that reads the watcher and writes a `Secret`. *Benefit: one
  pattern, two operators, no copy-paste.*

- **Per-namespace scoping.** The bridge carries a `BitwardenSecret` CRD
  with per-namespace scoping via machine accounts. *Benefit: a tenant's
  secrets are not a tenant's tenant's secrets.*

- **Audit log in the collector.** Every read and every write lands in
  the platform's collector. *Benefit: the auditor gets one log file,
  not nine.*

- **External Secrets Operator native.** The bridge is an ESO provider,
  not a second sync tool. *Benefit: the buyer's existing ESO stack is
  the integration point.*

- **A human-in-the-loop door.** The Bitwarden side is the human's door;
  the workload side is the workload's door. The two are connected by
  the bridge, not by trust. *Benefit: a person chooses what the workload
  sees.*

## How it works

The bridge is two operators:

1. **Bitwarden side.** An operator that watches a Bitwarden project and
   exposes the secrets through a service. The service is reached
   through the platform's identity plane.
2. **Kubernetes side.** An ESO provider that reads the Bitwarden
   service and writes a `Secret`. The provider is the workload's
   door.

The two operators communicate through the platform's identity plane.
Every read and every write lands in the collector. The audit log
carries the actor, the secret, the namespace, the verdict.

## Why us

- **The pattern is unique.** Bitwarden's own ESO provider is for
  Bitwarden Secrets Manager, not for Password Manager. Our bridge
  covers both. *Benefit: a buyer can keep their operators in the tool
  they already use.*

- **Per-namespace scoping.** A tenant's secrets are not a tenant's
  tenant's secrets. *Benefit: governance is the platform's default.*

- **Audit log in the collector.** Every read and every write is a
  receipt. *Benefit: the auditor gets one log file, not nine.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $30/seat/month, up to 5 namespaces | One tenant, the bridge, the audit log |
| Team | $300/month, up to 50 namespaces | Multi-tenant, the per-namespace scoping, Slack alerts |
| Enterprise | Contact us | Unlimited namespaces, SOC 2 conversation, dedicated support, on-prem |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Secrets
  Bridge with one sample tenant in 30 minutes. The drill runs hourly.
- **Read the design.** `docs/decisions/0017-bitwarden-is-the-human-door-for-secrets.md`
  is the canonical decision.
- **See it in action.** The estate's own operators bridge through
  Bitwarden to OCI Vault. The trace is in the collector.
- **Call us.** For the Enterprise tier, for a custom scoping, or for a
  procurement-grade security one-pager.

The bridge is the door between a person and a workload. The audit
log is the receipt.
