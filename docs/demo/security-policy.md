# Security policy — what it looks like when it runs

Real output, captured on main (`66b4e43`) on 2026-08-25. Nothing here is illustrative.

## The gate reads the policy page and checks every proof exists

```
$ bin/security-policy-gate
ok    security-policy 14 controls, every in-repo proof exists, 0 outside this repo not checkable here
```

Fourteen rows in `docs/reference/security-policy.md`, one per control, each with a
proof command. The gate parses the table and refuses the push when a proof names a
file that is not there. On the CI runner, proofs that live outside this repository
(the vault, restic, the laws file) report BLIND rather than a verdict, because a
check that cannot reach its evidence must not pretend it did.

## Every GitHub Action is pinned to a commit

```
$ bin/actions-pinned
ok    actions-pinned 12 of 12 pinned
```

## Images are scanned and signed on the way to the registry

From the main build that followed idp#44 (run 32794132246, job "merge"):

```
cosign verify ghcr.io/chidionyema/estate-mcp@sha256:c1c1fe5e8c72b61d120cf5d8e6b2610b644dde44df9e58d92069bc8efb04dd45 \
  --certificate-identity-regexp "^https://github.com/chidionyema/idp/" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Trivy ran in the build job on the exact tarball that was pushed; the sign step
verified its own signature before the job was allowed to pass.

## The same gate refusing a broken page

```
$ bin/security-policy-gate tests/fixtures/security-policy/bad.md; echo rc=$?
FAIL  security-policy tests/fixtures/security-policy/bad.md:20: proof command 'bin/does-not-exist' does not exist
rc=1
```

The good fixture exits 0 in the same CI run (`bin/idp-ci`, row `security-policy`).
