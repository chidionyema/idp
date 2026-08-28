# Security policy — what it is, what it costs, how to stop it

## What it is for

A buyer's engineer asks "show me your security policy" on day one. The answer is one
page, `docs/reference/security-policy.md`: fourteen controls, each mapped to an
ISO 27001 clause, each with the command that proves it and the state it was in on
the day it was measured. The gate makes sure the page cannot drift from the repo:
a proof that names a missing file fails the build.

## What it costs

Nothing recurring. `bin/security-policy-gate` and `bin/actions-pinned` are Python
and bash, run in under a second, and only run inside `bin/idp-ci` on a pull
request. The image scan (Trivy) and signing (cosign, keyless via GitHub OIDC) add
about a minute to each image build on `main` and need no key to store or rotate.

## What it watches or changes

It reads the policy page, the workflow files and the container image. It changes
nothing on the laptop. On `main` it refuses to tag an image that carries a
CRITICAL, fixable CVE, and it signs the manifest list by digest.

## Where it lives

```
docs/reference/security-policy.md     the page
bin/security-policy-gate              the proof-exists check
bin/actions-pinned                    every uses: is a 40-hex SHA
.github/workflows/build-multiarch.yml Trivy scan and cosign sign/verify
.github/dependabot.yml                weekly PR that moves the pinned SHAs
tests/fixtures/security-policy/       good and bad pages the gate is proved on
```

## How to turn it off

Remove the two rows from `bin/idp-ci`:

```
sed -i '' '/security-policy-gate\|actions-pinned/d' bin/idp-ci
```

The scan and signing stop when the `scan` and `sign` steps are deleted from
`build-multiarch.yml`. Nothing else depends on them.

## How to turn it back on

`git checkout main -- bin/idp-ci .github/workflows/build-multiarch.yml`.

## What goes wrong

A proof that lives outside this repository reports BLIND on the CI runner and ok
on the laptop. That is by design: CI cannot see the vault. If every row reads
BLIND, the runner has lost the checkout, not the policy. Dependabot's weekly PR
changes only trailing version comments and SHAs; if it stops arriving, the repo
went private (this account bills private CI as a failure).
