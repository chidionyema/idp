# PR #8525 & Thin-Agent Execution Deficit — Remediation Packet

Generated: 2026-11-25T05:30Z (Class B Advisory — Zero Execution / Zero Repo Write Authority)

## 1. Live External Telemetry Retrieved (Gmail GitHub Notifications, UTC)

Branch: `founder/continuous-intelligence-switching`
PR Title: `Founder directive: continuous intelligence, discrete authority`
Latest SHA: `3eebde50ed934d4212d12c17587446c7116f283c` (prior SHA: `e88a66d`)

Observed failures on `3eebde5`:
1. `guarded-paths` FAILED at `2026-11-25T05:28:24Z` (run `45553775198`, 1 annotation; prior SHA `e88a66d` also failed at `05:27:27Z`, run `45553655818`).
2. `portal-app` (`gate / fast-gate`) FAILED at `2026-11-25T05:29:26Z` (run `45553775189`, 1 annotation; prior SHA `e88a66d` also failed at `05:27:56Z`, run `45553656414`).
3. `ci` FAILED at `2026-11-25T05:29:42Z` (run `45553775148`):
   - `claim-gate`: FAILED (1 annotation) — confirmed by `github-actions[bot]` LANE FEEDBACK comment at `2026-11-25T05:30:21Z`.
   - `fast-gate / fast-gate`: FAILED (1 annotation).
   - `ci-success`: FAILED (1 annotation).
   - Passing jobs in same run: `law-gate`, `executes-gate`, `production-readiness`, `feature-request-plan`, `dof-gate`, `verifier`, `bdd`.

Note on KARMA Epistemic Grounding: Exact failure log text inside runs `45553775148`, `45553775189`, and `45553775198` is NOT present in Gmail notifications (only job status and run URLs) and is reported as `UNKNOWN` until retrieved by an authenticated Zone B executor.

## 2. Root Cause Diagnosis: Why the Agent Stalled

The agent refused to push because its sandbox lacked both Ruff and an authenticated Git checkout. That is a structural routing defect across three seams:

1. **Bypassed the Cloud Admission Door (`submit/**`):**
   `chidionyema/idp` already has `.github/workflows/submit-gate.yml` (verified in Drive `test_submit_gate_door.py` for `idp#8304`, plus PR `#8515` Stage 2 submit-gate merged `2026-11-24T23:37:17Z`). Pushing to `submit/**` runs `./.github/workflows/fast-gate.yml` in Lane 3 and promotes only green commits to `lane/$name`. Pushing directly to `founder/continuous-intelligence-switching` bypassed that cloud door and exposed an unvalidated commit directly to PR gates.
2. **Missing Claim + Guarded-Path Contract:**
   `claim-gate` and `guarded-paths` failed independently of Ruff. Even if Ruff passes, `#8525` cannot go green until:
   - a claim issue carries a valid `CLAIM` + `SHIP-CONTRACT:` covering every touched path, and
   - guarded-path changes satisfy the repo's guarded-path authorisation rule.
3. **No Capability-Deficit Routing (`BLOCKED_CAPABILITY_ROUTING`):**
   A Class B / tool-less agent hit a surface capability ceiling and terminated with an open red PR instead of routing the mission ID to an authorised Zone B executor (Lane 1 Cloudflare Container, Lane 2 OCI ARM A1, or Lane 3 GitHub Actions workflow dispatch).

## 3. Zone B Architectural Fix (Strict `DARWIN_THIN_CLIENT` — Zero Zone A / Mac Daemons)

1. **Immediate #8525 Recovery (Route to Capable Zone B Executor):**
   - Dispatch `#8525` (`3eebde50ed934d4212d12c17587446c7116f283c`) to an authorised Zone B executor (Lane 2 OCI ARM A1 worker or Lane 3 GitHub Actions runner) with an isolated ephemeral `git worktree` and hermetic `./bin/estate-gate` + Ruff.
   - Read exact annotations from runs `45553775148` (`claim-gate` + `fast-gate`), `45553775189` (`portal-app / fast-gate`), and `45553775198` (`guarded-paths`).
   - Remediate all three failures in one atomic commit and route through `submit/**` -> `lane/**` -> Greenlane.
2. **Structural Fix for Tool-Less / Web Agents (Eliminate This Failure Class Permanently):**
   - **Enforce `submit/**` as the sole ingress for thin/web agents:** Any agent without local Ruff/Git must emit patches exclusively via the `submit/**` cloud door (`.github/workflows/submit-gate.yml`), which runs `fast-gate` + `ruff` + `claim-gate` in Lane 3 before touching any `lane/**` or PR.
   - **Add a Pre-Execution Capability Probe in `platform/brain-hub` / `platform/lifeboat`:** Before assigning a repo-mutation mission, check whether the target executor declares `ruff`, `git_auth`, and `estate_gate`. If absent, emit `BLOCKED_CAPABILITY_ROUTING` immediately and route to Lane 1 Container / Lane 2 OCI A1 / Lane 3 Actions—never assign code mutation to a naked sandbox.
   - **Register Violation Class:** Add `FC_UNVALIDATED_THIN_SURFACE_EXECUTION` to `catalog/issue-classes.json` and enforce in `bin/pre-push-wall.py` / `cage/i8096` / `platform/estate/governance/laws.yaml`.
