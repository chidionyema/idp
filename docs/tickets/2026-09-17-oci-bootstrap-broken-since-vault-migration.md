# Bug: `bin/idp-oci-bootstrap` broken since OCI-Vault migration (2026-09-17)

## Symptom

On a fresh macbook (chidis-macbook-pro-2, 2026-09-17), running `bin/idp-oci-bootstrap` returns exit 100 with **no stdout, no stderr**. The exit-100 comes from `sops`; the silence comes from `set -euo pipefail` + `2>/dev/null` inside the `vget()` helper. No `BLIND` line, no `FAIL` line, no message pointing at the real cause.

The same silence blocks the composed bootstrap chain:

- `bin/idp-workstation-bootstrap` (2026-09-17)
- → `bin/idp-bootstrap-estate`
- → `bin/idp-oci-bootstrap` (exit 100, silent)

Every fresh workstation therefore hits an unreadable wall at Level 2.

## Root cause

Commit **`76ba8be chore(secrets): migrate all dev secrets to OCI Vault, delete from repo`** retired the sops-file-in-git pattern for dev secrets. `secrets/dev/` on `estate-secrets@main` now contains only `.gitkeep` and `LITELLM_LAPTOP_KEY.yaml`. Follow-up **`1c8ad50 chore(secrets): restore vault directory structure (now empty)`** kept the directory tree.

But `bin/idp-oci-bootstrap` was never updated. It still calls:

```bash
REGION="$(vget OCI_REGION)"
TENANCY="$(vget OCI_TENANCY_OCID)"
```

where `vget` runs `sops -d --extract "[...]" ".../$1.yaml" 2>/dev/null`. `sops` exits 100 on missing file. `set -euo pipefail` propagates 100 unconditionally; the `[ -n "$REGION" ] && [ -n "$TENANCY" ] || echo BLIND ...` guard on line 37 is never reached.

The estate graph already knows the current path: `bitwarden-machine OCI secret → enables access to → Bitwarden Secrets Manager` and `→ stored in → bin/idp-cloud` (ADR 0017).

## Fix (not "patch the legacy sops script")

1. **Confirm current entry point.** Read `bin/idp-cloud` — find where the Bitwarden machine token is consumed and how it exchanges to an OCI session. That is the new bootstrap boundary.
2. **Update `bin/idp-workstation-bootstrap`** to call that entry point directly instead of the legacy `bin/idp-oci-bootstrap`.
3. **Retire `bin/idp-oci-bootstrap`** — either delete or hard-fail-fast with an error naming ADR 0017 and the current entry point.
4. **Add a guard so a missing credential path fails loudly**, not with silent exit 100. Concretely, `vget` should distinguish "vault file missing" (a design change) from "sops decrypt failed" (a key problem) and print each explicitly. `set -e` should not swallow either.

## Blast radius

- Every fresh workstation since commit `76ba8be` (date: pre-2026-09-16 age re-bootstrap).
- Includes chidis-macbook-pro-2 (2026-09-17 replacement Mac) and any CI runner that assumed the sops-file vault.
- Existing workstations that already have `~/.oci/config` on disk from before the migration are unaffected because they never re-run bootstrap.

## Parked-lane linkage

- Lane N (bootstrap-in-any-env) is **blocked** on this fix. `bin/idp-workstation-bootstrap` was written 2026-09-17 in `feat/workstation-bootstrap`; it merges the mandate but cannot itself succeed on a fresh machine until this bug lands.
- Lane E (PR #3599 idp-agent operational) does **not** need this fix directly — cluster ops via GitHub Actions runners bypass the local bootstrap and have their own OIDC→OCI session exchange. Lane E's dispatch of `webhook-diagnose-v2.yml` can proceed independently.

## Owner + timeline

- Owner: unassigned; discipline call (founder 2026-09-17) was to file + park, not to timebox the fix mid-session with 5 lanes in flight.
- Priority: high — every new machine is currently un-bootstrappable via the documented chain — but not critical-path for PR #3599.
