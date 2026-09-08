# Vendor Key Activation

> A vendor pastes one key at one console; the platform does the rest —
> no copy-paste into YAML, no second sync, no audit gap.

## The problem

You are a vendor. You want to sell into our catalogue. You have a key.
We have a vault. The path from your key to our catalogue is whatever
the integrator happened to type that morning.

You want one URL. You want to paste one key. You want the platform to
mint the rest: the ExternalSecret, the policy bundle, the audit log,
the spend breaker, the gate.

The Vendor Key Activation is that path, packaged. A vendor pastes
one key at one console. The platform mints the rest. The gate refuses
everything that is not the gate.

## What you get

- **One console step.** The vendor pastes one key at one console. The
  console is the LiteLLM UI (or the platform's equivalent), and it
  attaches the key to a vendor-named alias. *Benefit: the vendor does
  not edit a config file.*

- **The platform mints the rest.** The ExternalSecret, the policy
  bundle, the audit log, the spend breaker — the platform mints
  every artifact from the alias. *Benefit: the vendor pastes once; the
  platform does the rest.*

- **A gate that refuses the wrong path.** A `bin/idp-vendor-key` gate
  reads the seed, grades the artifact, and refuses an off-road path.
  *Benefit: a vendor that pastes a key into YAML is a vendor the
  platform refuses.*

- **An audit log on the record.** Every activation lands in the
  collector with the vendor, the key, the alias, the verdict.
  *Benefit: the auditor gets one log file, not nine.*

- **A per-vendor spend breaker.** The breaker reads the spend log per
  vendor; a vendor that drains the budget trips the breaker.
  *Benefit: a vendor surprise is a dashboard, not an invoice.*

- **A revocation path.** The vendor revokes the key at the console; the
  platform propagates the revocation to every artifact. *Benefit: a
  vendor leaves; the platform cleans up.*

## How it works

The vendor goes to the LiteLLM console (or the platform's equivalent).
The vendor pastes a key. The console attaches the key to a vendor-named
alias. The platform's seed-vault-road reads the alias, mints the
ExternalSecret, writes the policy bundle, and stamps the audit log.

The gate is `bin/idp-vendor-key`, in the shape of `bin/idp-root-trust`:
it reads the seed SQL, it grades the artifact, it gets a row in
`AGENTS.md` with two fixtures.

The drill runs hourly. The drill proves the gate is the gate; a gate
that could not run is a fail-closed FAIL, never a pass.

## Why us

- **One console step.** The vendor pastes once. The platform mints the
  rest. *Benefit: a vendor onboarding is 30 seconds, not 30 minutes.*

- **The gate is the product.** The `bin/idp-vendor-key` gate refuses
  the off-road path. *Benefit: a vendor that pastes a key into YAML is
  a vendor the platform refuses.*

- **The audit log is the receipt.** Every activation lands in the
  collector. *Benefit: the auditor gets one log file, not nine.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $50/month, up to 3 vendors | The console, the gate, the audit log, the spend breaker |
| Team | $500/month, up to 25 vendors | Multi-tenant, the revocation path, Slack alerts |
| Enterprise | Contact us | Unlimited vendors, custom gates, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Vendor Key
  Activation with one sample vendor in 30 minutes. The drill runs
  hourly.
- **Read the spec.** `docs/specs/vendor-key-activation.md` is the
  canonical design. `docs/specs/key-ingest-door.md` is the human-side
  door.
- **See it in action.** The estate's own vendors onboarded through
  this path. The receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom gate, or for a
  procurement-grade security one-pager.

A vendor pastes one key. The platform does the rest.
