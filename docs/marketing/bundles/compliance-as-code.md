# Compliance-as-Code

> The bundle for any company that needs SBOM + license + placement +
> capacity evidence for SOC 2, ISO 27001, or vendor security review —
> the engineering layer, not the dashboard.

## The story the buyer tells their board

> "What runs, in whose pocket, with what licenses, with what CVEs, on a
> clock. The auditor got the receipt. The CFO got the dashboard. The
> engineering team got the gate."

That is Compliance-as-Code. Four products, one bundle, one story.

## What you get

The Compliance-as-Code bundle is the Platform + Compliance Pack +
Supply-chain audit + Trivy, configured as a single deployment. Every
component is a product on its own; together, they are the answer a
buyer's compliance team wants to hear when the auditor's email is in
the inbox.

| Component | What it does | Why it is in the bundle |
|---|---|---|
| **The Platform** | The IDP substrate: catalogue, identity, edge, secrets, scheduling, supply chain, policy | The audit log is the platform's, not the vendor's |
| **Compliance Pack** | SBOM + license + placement + capacity gates as a CI image | The engineering layer; the auditor gets the receipt |
| **Supply-chain audit** | SBOM + grype + license gate on every build | Every release is a receipt |
| **Trivy** | A VulnerabilityReport per scanned image, read by `bin/estate-security-scan` | A CVE is a row in the report, not a row in the news |

## What the buyer sees

- **One CI image.** `compliance-pack` runs in any GitHub Actions
  workflow. *Benefit: the integration is a row in the workflow.*

- **One SBOM per build.** SPDX + CycloneDX; signed; shipped with the
  artifact. *Benefit: the auditor gets the SBOM, not a Jira ticket.*

- **One license gate.** A Rego bundle that classifies every
  dependency's license against the sell-blocking list. *Benefit: a
  license that blocks a sale blocks a build.*

- **One placement gate.** A Rego bundle that says "this workload
  belongs on this node." *Benefit: a placement that drains a node
  drains a build.*

- **One capacity gate.** A Rego bundle that says "this container fits
  this floor." *Benefit: a capacity surprise is a build failure, not
  an outage.*

- **One CVE scan per build.** grype on the SBOM; the receipt is a row
  in the trace. *Benefit: a CVE is a row in the receipt, not a row in
  the news.*

- **One drill on a clock.** The drill proves the gates are the gates;
  a gate that could not run is a fail-closed FAIL, never a pass.
  *Benefit: the SLO is a number a buyer can read.*

## How it works

The bundle is the install wedge with the Compliance Pack, the
supply-chain audit, and Trivy enabled. The buyer adds one row to the
GitHub Actions workflow; the row runs `compliance-pack licenses &&
compliance-pack placement && compliance-pack capacity`. The receipts
land in the collector.

Trivy runs on every scanned image. The VulnerabilityReport is a row
in the buyer's trace. The buyer can ask "what CVEs are running
today" and get the answer.

The drill runs hourly. The drill proves the gates are the gates.

## Why us

- **The engineering layer, not the dashboard.** Styra DAS is the
  enterprise UI; the Compliance Pack is the CI image. They are
  complementary, not competitive. *Benefit: a buyer can run Styra and
  the Pack on the same Rego bundle.*

- **Drata and Vanta are GRC.** The bundle is engineering. The two
  together close the loop. *Benefit: a buyer does not have to pick;
  they can pair.*

- **The drill is the SLO.** A drill runs hourly that proves the gates
  are the gates. *Benefit: a gate that does not run is a gate that
  does not exist.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $300/month, up to 5 repos | One tenant, the Compliance Pack, the supply-chain audit, the CVE scan |
| Team | $3,000/month, up to 50 repos | Multi-tenant, the placement gate, the capacity gate, Slack alerts |
| Enterprise | Contact us | Unlimited repos, custom bundles, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the bundle
  with one sample repo in 30 minutes. The drill runs hourly.
- **Read the rules.** `policy/licences.rego`, `policy/placement.rego`,
  `policy/capacity.rego` are the Rego bundles.
- **See it in action.** The estate runs the bundle on every PR; the
  receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom bundle, or for a
  procurement-grade security one-pager.

Compliance-as-Code is the engineering layer. The auditor gets the
receipt.
