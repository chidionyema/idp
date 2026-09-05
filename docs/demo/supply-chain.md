# Supply chain — what it looks like when it runs

Real output, captured 2026-08-24 against `backstage/node_modules`. Nothing
here is illustrative.

## The full run

```
$ bin/supply-chain
01:49:37Z  sbom      scanning /Users/chidionyema/dev/code/idp/backstage/node_modules
01:51:28Z  sbom      4996 packages, 3081 with a declared licence -> reports/sbom.{syft,spdx,cyclonedx}.json
01:51:28Z  vulns     scanning the SBOM
01:54:27Z  vulns     447 findings: 49 critical, 203 high -> reports/vulns.json
01:54:27Z  licence   reshaping the SBOM for the policy
01:54:28Z  licence   conftest against policy/licences.rego
WARN - /Users/chidionyema/dev/code/idp/reports/licences.json - main - 1915 of 4996 packages declare no licence. Usually a metadata gap, but no licence grants nothing -- check any that ship in the product itself.
WARN - /Users/chidionyema/dev/code/idp/reports/licences.json - main - axe-core@4.13.0 is MPL-2.0 -- copyleft, fine to use, constrains distribution
WARN - /Users/chidionyema/dev/code/idp/reports/licences.json - main - rollup-plugin-dts@6.5.1 is LGPL-3.0-only -- copyleft, fine to use, constrains distribution

5 tests, 2 passed, 3 warnings, 0 failures, 0 exceptions

PASS      4996 packages (3081 licensed), 447 vulnerabilities (49 critical), nothing sell-blocking
```

Two minutes to catalogue 4,996 packages into three SBOM formats, three
minutes for grype to read that SBOM back and find 447 vulnerabilities, and a
second for the licence policy. The headline for LAW 40 test 3 is the last
line: nothing in the tree is AGPL, SSPL, BUSL, Elastic, non-commercial
Creative Commons or Commons Clause, so nothing here blocks a sale.

Two copyleft packages are named rather than hidden — `axe-core@4.13.0` under
MPL-2.0 and `rollup-plugin-dts@6.5.1` under LGPL-3.0-only. Both are fine to
use and both constrain how a binary is distributed, which is worth knowing
before a buyer finds it rather than after.

## The bug this run exists because of

The first version of this reported 1,821 packages and **2** licences, and the
policy passed it and printed "licences clean". It had checked nothing.

`syft cataloger list` shows why, on two lines:

```
│ javascript-lock-cataloger              │ declared, deno, directory, javascript, language, node, npm, package                   │
│ javascript-package-cataloger           │ image, installed, javascript, language, node, package                                 │
```

A `dir:` scan selects catalogers tagged `directory` and `declared`, so syft
ran the lockfile reader — which records versions and not terms — and never
ran the `package.json` reader, which is tagged for image scans and is the
only place an npm licence actually lives. Forcing it with
`--select-catalogers "+javascript-package-cataloger"` takes the same tree from
2 licences to 3,081.

A guard that passes because it was fed nothing is worse than no guard, so the
policy now refuses that shape outright:

```
$ conftest test --parser json -p policy policy/fixtures/broken-scan.json
WARN - policy/fixtures/broken-scan.json - main - 19 of 20 packages declare no licence. Usually a metadata gap, but no licence grants nothing -- check any that ship in the product itself.
FAIL - policy/fixtures/broken-scan.json - main - only 1 of 20 packages carry a licence. That is a broken scan, not a clean tree -- check syft ran javascript-package-cataloger. Passing this would report 'licences clean' having checked nothing.

11 tests, 9 passed, 1 warning, 1 failure, 0 exceptions
```
