# Onboarding: estate-security-scan

## What it is

`--source DIR` scans another repository; the composite action
`.github/actions/security-scan` runs it that way from every active estate
repository. Checks adapt to what the repository tracks: pip-audit only where a
`requirements*.txt` exists, `npm audit --audit-level=high` only where a
`package-lock.json` exists, the policy gate only where `bin/security-policy-gate`
exists. Nothing to scan prints `ok ... none tracked`, never BLIND.

`bin/estate-security-scan [--quiet]` runs three checks and prints one receipt
with a timestamp and commit hash:

1. **Secrets in the codebase = 0.** `gitleaks detect` over the whole git
   history, so every tracked byte ever committed.
2. **Unaudited dependencies = 0.** `pip-audit` over every tracked
   `requirements*.txt`, in one resolver run.
3. **Policy contradiction = 0.** `bin/security-policy-gate`: every control row
   on the security policy page names a proof command that exists.

The last line is `SECURITY-SCAN PASS`, `FAIL` or `BLIND` (exit 0, 1, 3).

## Why it exists

The founder's Definition of Done v2.1 (2026-08-25) says a "Security passes"
claim needs `bin/estate-security-scan` output with a timestamp and commit
hash, and that any non-zero security metric blocks merge. Before this script
the three tools existed separately and nothing printed a receipt a buyer's
engineer could check against a commit.

## When it runs

- By hand, before claiming security passes: paste the output as the evidence.
- In CI, the `security-scan` job in `.github/workflows/ci.yml` runs it on
  every pull request and on pushes to `main`; a failure blocks merge.

## What you need on a laptop

```
brew install gitleaks          # 8.30.1 is what CI pins
pipx install pip-audit         # or have uv on PATH; uvx pip-audit is used then
```

Without one of them the check prints `BLIND` and exits 3 rather than guessing.

## Related files

```
bin/estate-security-scan                  the receipt
bin/security-policy-gate                  check 3
bin/supply-chain                          SBOM and licence policy (syft, grype, opa), the wider audit
docs/policy/definition-of-done.md         the policy that names this command
.github/workflows/ci.yml                  the security-scan job
```
