# Supply chain — what is inside this, and what we may sell

## What it is for

Two questions a buyer asks on the first day, and neither has a good answer if it
has to be assembled by hand:

1. **What is this made of, and is any of it vulnerable?** A parts list of every
   dependency, and that list checked against known vulnerabilities.
2. **What are we allowed to sell?** LAW 40, test 3. A licence is discovered
   cheaply and swapped expensively, and the estate already has one worked
   example of why it matters: Humanitec ships **no licence file at all** on 12 of
   its 18 public repositories, which grants nothing and would have made anything
   built on it unsellable.

Doing this by hand works at our size and stops working the moment somebody asks
for the whole list at once.

## What it costs

**£0 / $0.** Three tools, all installed already, all permissively licensed:

| tool | job | licence | why this one |
|---|---|---|---|
| syft | writes the parts list | Apache-2.0 | 9,450 stars; the de-facto SBOM generator |
| grype | checks it for vulnerabilities | Apache-2.0 | 12,777 stars; same authors, reads syft output directly |
| conftest / OPA | enforces the licence rules | Apache-2.0 | **CNCF Graduated**, already enforcing the risk register |

Runtime cost is zero — nothing runs in the background. `bin/supply-chain` is
invoked, produces reports, and exits.

**An honest correction.** Syft and grype are **not** CNCF projects. They appear
in the CNCF landscape directory, which lists tools that exist in the ecosystem
and confers no governance status whatsoever. Trivy is the same. Calling them
"CNCF-backed" on a diligence page would be a false claim that takes one search
to disprove, so the phrase to use is "widely adopted". Only OPA in the table
above carries actual CNCF status, and it is the top tier.

## Why not the OSS Review Toolkit

ORT is the more serious licence tool: Linux Foundation governed, used by Bosch,
Volkswagen, Porsche and Deutsche Telekom, and it does far more than this —
curations, attribution documents, source scanning.

It also needs a JVM and a roughly 2 GB image on a laptop that is already running
Docker with seven Langfuse containers on it. Syft already extracts per-package
licence metadata, and OPA is already installed and already enforcing policy
elsewhere, so the licence question gets answered with two tools that are here
rather than one that is not.

ORT remains the upgrade path, and this is written down so the trade is inherited
rather than rediscovered. Take it when the answer needs to be richer than "which
licences are present" — specifically when an attribution document is required
for a release, or when a buyer wants declared licences checked against what the
source files actually say.

## Where it lives

```
bin/supply-chain            run everything, write reports/
policy/licences.rego        the licence rules
reports/                    generated, gitignored
  sbom.syft.json            native format, what grype reads
  sbom.spdx.json            SPDX — the format a buyer will ask for
  sbom.cyclonedx.json       CycloneDX — the other format a buyer will ask for
  vulns.json                grype findings
  licences.json             the SBOM reshaped for the policy
  licence-policy.txt        what conftest said
```

Reports are gitignored on purpose. They are generated output, and LAW 24
excludes generated output because a committed copy is a stale copy that reads as
a record.

## Reading the result

`bin/supply-chain` exits **0** when nothing sell-blocking is present, **1** when
the licence policy refuses, and **2** when a tool is missing.

The policy splits its findings deliberately, because a guard that refuses
correct work is an outage (LAW 38):

- **deny** — a licence is *declared* and it blocks a sale: AGPL, SSPL, BUSL,
  Elastic-2.0, non-commercial Creative Commons, Commons Clause. Unambiguous, and
  it fails the run.
- **warn** — copyleft that constrains distribution without blocking a sale
  (GPL, LGPL, MPL), and the count of packages declaring no licence at all. Both
  are worth knowing and neither fails a build. In an npm tree of a few thousand
  packages, missing licence metadata is common and usually a packaging gap.

## What goes wrong

**The parts list has no licences in it.** Scan the installed tree, not the
lockfile. Measured 2026-08-24: `backstage/yarn.lock` yields 2,802 packages and
**zero** licences, because a lockfile records versions and not terms. The
licence lives in each package's own `package.json`, which only exists in
`node_modules`. `bin/supply-chain` already targets the installed tree; if you
point it at a lockfile you get a parts list that cannot answer question 2.

**conftest reports every rule as failing, once per package.** The classic trap:
conftest splits a top-level JSON array into one document per element, so a bare
array makes whole-tree rules fire per row. `bin/supply-chain` wraps the array as
`{"packages": [...]}` for exactly this reason. Measured in the crew repo on
2026-08-24: eleven identical failures from a file that was fine.

**conftest itself fails an automated licence scan.** Its LICENSE text is plain
Apache-2.0, but a custom preamble defeats GitHub's detector, which reports
`NOASSERTION`. A buyer's scanner will flag it. The answer is written down here
rather than improvised in a meeting.

**grype reports nothing on the first run.** It downloads its vulnerability
database on first use. If the machine is offline it will say so and exit
non-zero; the run continues and the licence check still happens.

## How to turn it off

Nothing to turn off — it does not run in the background. To remove it entirely,
delete `bin/supply-chain` and `policy/licences.rego`.

## How to turn it back on

```
bin/supply-chain
```
