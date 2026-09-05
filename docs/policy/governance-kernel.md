# Governance kernel

Founder, 2026-08-26, crew#307, verbatim on the three defects that let the catalogue serve him an
error while every gate was green: "silent 500s masked by 302 proxy redirects, orphaned OCI
buckets causing Tofu state drifts, and critical drills being skipped because a previous step
failed ... it must act as a strict Governance Kernel." This page is that kernel: three rules,
each with the file that enforces it and the command that proves it. A rule with no file is a wish.

## 1. Drills are adversaries, never downstream steps

A drill runs on its own clock whether the pipeline is green, red or absent. It has no `needs:`.
It never reads `skipped`; a skipped drill is a broken drill and blocks the next merge.

- Enforced by: `.github/workflows/login-drill.yml` (every 5 minutes, dispatch, push to main;
  `concurrency` keeps one at a time), `chaos-drill` in `oke-check.yml` with no `needs:`.
- Loud: a failed run opens or comments `P0: login drill failed` on this repository with the FAIL
  line and the run URL, and the FAIL line is on the run summary.
- Proof: `gh run list -R chidionyema/idp --workflow login-drill.yml --limit 20 --json conclusion`
  contains no `skipped`.

## 2. Assertions are deep: the whole stack, and application state

A 302 from the proxy proves the proxy. A probe that cannot sign in, read a structured answer
through the signed-in session and see a rendered page without errors classifies the service as
degraded. Rows that curl for a status code are topology rows; they stand in for nothing.

- Enforced by: `bin/idp-login-drill`, stages `redirect`, `credentials`, `session`, `catalogue`,
  `identity`, `entities`, `shell`; each FAIL line names its layer.
- Spec: `features/drills/front-door-login-drill.feature`.
- Proof: the `ok      login-drill` line names the identity, the entity count and `0 js errors`.

## 3. State is absolute: reality is adopted declaratively or reported as drift, never hand-fixed

If a resource exists in the cloud and not in state, it is adopted with an `import` block in the
same file as the resource, in a pull request, and the block is removed after one clean apply. No
session runs `tofu import` or touches the console by hand.

- Enforced by: `platform/oci/receipts.tf` import block (crew#301); `bin/idp-oke-rebuild --check`
  fails on any plan diff (`OKE_CHECK_EXPECT_CHANGES=0` outside pull requests).
- Reaper: report mode first. A destroy loop that cannot tell the state bucket from an orphan is
  a LAW 11 decision, not a cron job; the first reaper prints untracked buckets as a FAIL row and
  destroys nothing. Fix mode follows once the report has run clean for a week.
- Console write access: revoked for people once every platform layer is in this repository
  (crew#227 CP3 tracks the 28 remaining static credentials).

## What a session may not do

- Add `needs:` to any job whose name ends in `-drill`.
- Add a health row that asserts only a status code and call it a drill.
- Run `tofu import`, `oci ... delete`, or a console change by hand for anything this repository declares.
