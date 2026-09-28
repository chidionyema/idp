# Compliance Pack

> SBOM + license + placement + capacity gates as a CI image — a buyer
> runs one command in GitHub Actions and gets the receipts the auditor
> wants.

## The problem

You ship software. The auditor wants SBOM. The auditor wants license.
The auditor wants to know what ran, where, with what CPU, with what
memory. You can give them a one-off PDF. You can give them a Jira
ticket that says "we'll fix it." You can stand up Styra, or Drata, or
Vanta, and pay per-employee per-year for the dashboard.

None of these is the engineering layer. None of these is "what did
this PR ship, and is it allowed?"

The Compliance Pack is the engineering layer. It is a CI image that
runs the Rego rules + conftest + license/placement/capacity gates, and
emits a receipt for every PR. The receipt is JSON, signed, ready to
hand to an auditor or a vendor security review.

## What you get

- **One CI image.** `ghcr.io/<vendor>/compliance-pack:latest` runs in
  any GitHub Actions workflow. *Benefit: the integration is a row in
  the workflow.*

- **License gates.** A Rego bundle that classifies every dependency's
  license against the sell-blocking list. A red build for a copyleft
  the buyer does not allow. *Benefit: a license that blocks a sale
  blocks a build.*

- **Placement gates.** A Rego bundle that says "this workload belongs
  on this node, with this affinity." A red build for a placement the
  buyer does not allow. *Benefit: a placement that drains a node drains
  a build.*

- **Capacity gates.** A Rego bundle that says "this container fits
  this floor." A red build for a request that exceeds the floor.
  *Benefit: a capacity surprise is a build failure, not an outage.*

- **SBOM on every build.** syft emits SPDX + CycloneDX; the receipt
  is signed and shipped with the artifact. *Benefit: the auditor gets
  the SBOM, not a Jira ticket.*

- **grype on every build.** The CVE scan runs on the SBOM; the receipt
  is a row in the trace. *Benefit: a CVE is a row in the receipt, not
  a row in the news.*

- **A drill on a clock.** The drill proves the gates are the gates;
  a gate that could not run is a fail-closed FAIL, never a pass.
  *Benefit: the SLO is a number a buyer can read.*

## How it works

The Compliance Pack is a CI image with three binaries:

1. **`compliance-pack licenses`** — runs the Rego license bundle
   against the SBOM.
2. **`compliance-pack placement`** — runs the Rego placement bundle
   against the manifest.
3. **`compliance-pack capacity`** — runs the Rego capacity bundle
   against the manifest and the node floor.

The image runs in the buyer's GitHub Actions workflow. The receipt is
JSON, signed with the platform's key, ready to hand to an auditor or a
vendor security review.

The drill runs hourly. The drill is a fixture set: a manifest that
should fail the gate, a manifest that should pass. The drill fails when
the gates stop being the gates.

## Why us

- **The engineering layer, not the dashboard.** Styra DAS is the
  enterprise UI; the Compliance Pack is the CI image. They are
  complementary, not competitive. *Benefit: a buyer can run Styra and
  the Pack on the same Rego bundle.*

- **Drata and Vanta are GRC.** The Compliance Pack is engineering.
  The two together close the loop. *Benefit: a buyer does not have to
  pick; they can pair.*

- **The drill is the SLO.** A drill runs hourly that proves the gates
  are the gates. *Benefit: a gate that does not run is a gate that
  does not exist.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $100/month, up to 5 repos | One tenant, the license gate, the placement gate, the SBOM |
| Team | $1,000/month, up to 50 repos | Multi-tenant, the capacity gate, the CVE scan, the drill |
| Enterprise | Contact us | Unlimited repos, custom bundles, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Compliance
  Pack with one sample repo in 30 minutes. The drill runs hourly.
- **Read the rules.** `policy/licences.rego`, `policy/placement.rego`,
  `policy/capacity.rego` are the Rego bundles.
- **See it in action.** The estate's own CI runs the gates on every PR.
  The receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom bundle, or for a
  procurement-grade security one-pager.

The Compliance Pack is the engineering layer. The auditor gets the
receipt.
