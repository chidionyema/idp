# Spec — The Cryptographic CI Gateway and Zero-Trust Agent Enforcement

**Status:** IMPLEMENTING
**Date:** 2026-09-22
**Owners:** crew #180 (CP6)
**Related:** `sovereign/verifier.py`, `platform/executor/daemon.py`,
`bin/idp-ci-verify`, `bin/idp-prepush-verify`, `.github/workflows/verifier.yml`,
`.github/workflows/ci.yml`

## Context

An audit of `.github/workflows/verifier.yml` and `.github/workflows/ci.yml`
(2026-09-22) established four measured facts about the Deterministic Verifier as
it is wired into CI today:

1. **It is advisory.** `verifier.yml` runs the real three-stage gauntlet
   (`bin/idp-ci-verify` → `sovereign/verifier.py`, no daemon, no `estate.db`),
   but **no job depends on it**. Every downstream job in `ci.yml` gates on
   `fast-gate` (lines 56, 121, 128, 268, 299, 332, 471) or on `bdd-suites`
   (line 376). Nothing `needs: verifier`. The verifier reports and cannot block
   a merge.

2. **It fails open.** `verifier.yml:58-61` passes an empty diff with `exit 0`
   ("nothing to grade"). `verifier.yml:62-66` downgrades the tooling-unavailable
   exit code 2 to success so downstream jobs are not blocked. A gate that cannot
   fail is not a gate (estate law).

3. **It exempts agents.** `verifier.yml:26-35` skips the entire job when the
   author matches `*[bot]` or `estate-agent*`. The exact authors this architecture
   exists to constrain bypass the verifier in CI.

4. **It is three stages, not four.** The CI path runs structural / symbolic /
   execution (`bin/idp-ci-verify` header). `stage_sql` exists in
   `sovereign/verifier.py` but is **not** wired into the CI door. This spec does
   not add it; it is noted so the prose does not over-claim.

The pre-push hook already routes through the daemon
(`propose_patch → verify`) and is BLIND, not FAIL, when the daemon is down — so
CI is the backstop by construction (`verifier.yml:3-7`). This spec closes the gap
between "the verifier runs in CI" and "the verifier is the gate."

**Goal.** Convert CI from a heavy calculation engine into a millisecond
cryptographic gateway. An agent must **physically prove** its change with a
Sigstore attestation before code merges. The absence of a proof is a failure.

## 1. Remove the Agent Exemption (Zero-Trust Enforcement)

Agents are the primary threat model for stochastic breakage. They must not
bypass the verifier.

- **Target:** `.github/workflows/verifier.yml:26-35`.
- **Action:** Delete the author exemption (`if: github.actor != '*[bot]'` /
  `!startsWith(github.actor, 'estate-agent')`).
- **Rule:** Every automated author (`estate-agent*`, `*[bot]`, Dependabot) is
  strictly subjected to the verifier.

## 2. Enforce Fail-Closed (BLIND = FAIL)

A gate that fails open is a monitoring tool, not a gate.

- **Target:** `.github/workflows/verifier.yml:58-66`.
- **Action:** Remove BOTH the empty-diff `exit 0` (`:58-61`) and the exit-2
  downgrade (`:62-66`). If `bin/idp-ci-verify` cannot run, cannot parse the
  diff, or crashes, it MUST exit non-zero and fail the pipeline.
- **Rule:** The absence of a mathematical proof is a failure.

> Exception to carry forward: a genuinely docs-only PR still has a diff with
> file entries, so it flows through the structural stage rather than the
> empty-diff branch. No special-case is added for it.

## 3. Make the Verifier the Required Gateway

- **Target:** `.github/workflows/ci.yml` and GitHub Branch Protection.
- **Action:**
  1. Add `verifier` to the `needs:` array of every job that gates deployment or
     merge (the jobs now needing `fast-gate` / `bdd-suites`).
  2. Add a `.github/CODEOWNERS` requiring human approval for workflow changes
     (the Sensitive Write Boundary) — no agent-authored change to a workflow
     merges without a human `CODEOWNERS` approval.
  3. Enforce `verifier` as a **Required Status Check** on `main` in repository
     branch protection.
- **Rule:** `main` cannot move without a green `verifier` check.

## 4. Implement Cryptographic Fast-Path (Verify in Seconds)

> **DEFERRED — preconditions not met (2026-09-22).** The local daemon
> (`~/.estate/executor.sock`) is not listening; CI runners never have a daemon
> anyway. A self-contained fast-path needs two prerequisites that are not in
> the repo today:
>
> 1. A public key committed to the repository (the daemon's key is not).
> 2. `cosign` installed on the GitHub Actions runner (not currently added).
>
> Until both exist, every PR pays the three stages. The implementation below
> is the design; do **not** claim the fast-path is live.

CI should not re-run heavy tests if the local daemon already mathematically
proved the patch and signed it.

- **Target:** `.github/workflows/verifier.yml`.
- **Action:** Before the three-stage gauntlet, look for a valid
  `sigstore-bundle` on the commit. Verification reuses the existing
  fail-closed primitive `sovereign/verifier.py::_verify_sigstore_bundle`
  (missing `cosign` ⇒ `False`, never a pass). The subject used for
  `verify-blob` MUST be the PR's HEAD commit identity, so a bundle made over
  different content cannot pass. The signing key MUST be a public key
  committed to this repository (proposed path: `keys/ci-gateway.pub`); a
  bundle signed by a non-committed key fails closed.
- **Logic:**
  - Bundle present, signature matches the committed public key, and the
    signed subject matches the PR's HEAD → `exit 0` (bypass the heavy
    gauntlet). This is the "built-and-proven locally" path.
  - No bundle, **human** author → run the three-stage gauntlet in CI as a
    fallback.
  - No bundle, **agent** author → `exit 1` instantly. Agents are barred from
    the CI fallback; the fast-path has no agent fallback.
- **Rule:** For agents, a bundle is mandatory; for humans, the gauntlet is the
  fallback.

**Pre-PR checklist before opening this work:**
- [ ] Commit a cosign keypair (private key in password manager; public key at
      `keys/ci-gateway.pub`).
- [ ] Add `sigstore/cosign-installer` to `.github/workflows/verifier.yml`
      before the verifier step.
- [ ] Re-prove `_verify_sigstore_bundle` against the installed `cosign` with
      the committed key in a unit test (not just `main`).
- [ ] Update the comment in `.github/workflows/verifier.yml` to drop the
      "No fast-path yet" note.

## Non-goals

- Adding `stage_sql` to the CI door (fact 4). The CI gate stays three-stage.
- Replacing `fast-gate` / `bdd-suites` for human PRs. Those remain the human
  fallback; the fast-path only skips them when a valid bundle is proven.
- Building a second verifier. `sovereign/verifier.py` is the one engine; this
  spec only changes how CI calls it. A rule is a rung in `bin/idp-ci`, not a
  new service.

## Acceptance

The spec is met when:

1. An `estate-agent*` PR triggers `verifier` (no exemption).
2. A `bin/idp-ci-verify` exit 2 fails the pipeline.
3. `verifier` appears in the `needs:` of the merge-gating jobs and is a required
   status check on `main`.
4. §4 fast-path: deferred until preconditions met (see §4 header).

Proof of each is a production log line from a real run, not a green local test
(estate law: built and operating are different facts).
