# ironcage: where it is, and what finishes it

Written 2026-09-19 because the machine needs a reboot and a reboot ends the session. Everything
below is committed and pushed, so a new session can pick this up from the repo alone.

## The goal

ironcage is deployed on the OKE cluster but has **never run**. Its pods report
`ImageInspectError` and have done for three and a half days.

    ironcage-api-6c456b946d-pgv5z    0/1   ImageInspectError   3d6h
    ironcage-kernel-59597d7f57-wqg8h 0/1   ImageInspectError   3d6h

## Everything diagnosed, and what was fixed

FIVE causes, found one at a time. Four are fixed and pushed; the fifth needs a credential.

### 1. The repository could not write packages — FIXED

The repo's default workflow permission was `read`, so the `packages: write` declared in the
workflow was not honoured. Every push died with:

    denied: permission_denied: write_package

Fixed via the API (`gh api -X PUT repos/chidionyema/ironcage/actions/permissions/workflow -f
default_workflow_permissions=write`). Now `write`.

### 2. The job-level `permissions:` block dropped `contents: read` — FIXED

A job-level `permissions:` block **replaces** the workflow-level one; it does not merge with it.
The `publish` job declared only `packages: write`, silently removing `contents: read` — and a token
minted without contents read cannot create a package.

Commit `3a3aa4a`.

### 3. The workflow only published `:<sha>`, and the manifests asked for `:latest` — FIXED

Two halves of one mismatch:

* the workflow pushed `ghcr.io/chidionyema/ironcage-kernel:${{ github.sha }}` and nothing else;
* `k8s/deployment.yaml` asked for `:latest`.

Even with a working push, the cluster would have pulled a tag nothing produces. Now the workflow
publishes **two tags** (the sha as the immutable record, `main` as the moving tag a cluster can
track) and the manifests ask for `:main`.

Commits `c01b98a` and `0673faa`.

### 4. A dispatch could not publish — FIXED

The push step was gated on `event_name == 'push'`, so a manually started run built the images and
threw them away — the one route available to somebody recovering a broken publish was the one route
that could not publish. The gate is now `ref == refs/heads/main`, and `workflow_dispatch` is
declared.

Commit `c01b98a`.

### 5. THE IMAGES DO NOT EXIST, AND GHCR WILL NOT LET THIS ACCOUNT CREATE THEM — BLOCKED

    chidionyema/lago-front        tags -> 200   (exists; idp pushes to it fine)
    chidionyema/ironcage-kernel   no token      (ABSENT)

`idp`'s `build-multiarch` pushes to GHCR successfully with the same `GITHUB_TOKEN`, so GHCR is not
broken — the package simply does not exist, and GHCR refuses to *create* a new package for a token
that does not already own one.

The Mac's `gh` token cannot do it either:

    x-oauth-scopes: gist, read:org, repo      <- no write:packages

Verified directly: a push-capable bearer for an existing package returns
`permission_denied: The token provided does not match expected`.

## What finishes it

**One of these:**

1. `gh auth refresh -h github.com -s write:packages` — then push both images from the Mac directly.
   This was attempted; GitHub's device flow asked to confirm with **GitHub Mobile**, and the person
   was not able to complete it.
2. Create the two packages once in the GitHub web UI (`ghcr.io/chidionyema/ironcage-kernel`,
   `ironcage-api`). Once they exist, the workflow's `packages: write` is honoured and CI publishes.
3. Add a PAT with `write:packages` as a repo secret and use it in place of `GITHUB_TOKEN` in the
   login step.

Then:

    # verify both tags exist
    for P in ironcage-kernel ironcage-api; do
      T=$(curl -s "https://ghcr.io/token?scope=repository:chidionyema/$P:pull&service=ghcr.io" \
          | python3 -c 'import json,sys;print(json.load(sys.stdin).get("token",""))')
      curl -s -o /dev/null -w "$P %{http_code}\n" \
        "https://ghcr.io/v2/chidionyema/$P/tags/list" -H "Authorization: Bearer $T"
    done

## Still to do once the images exist

**ironcage is not managed by Flux.** Its deployments were created by `kubectl-client-side-apply`,
which is why nothing in git describes them and why a broken image sat unnoticed for days. That
violates the estate's own rule (AGENTS.md 2: "Git is the only writer of this cluster").

The full spec **is** recoverable — it lives in the `last-applied-configuration` annotation on the
live objects, and a partial recovery is already committed at `platform/ironcage/recovered.yaml`.
The complete set is 8 resources:

    Namespace                ironcage
    PersistentVolumeClaim    models-pvc
    PersistentVolumeClaim    ledger-pvc
    Deployment               ironcage-kernel   (ghcr.io/chidionyema/ironcage-kernel:main, port 3000)
    Service                  ironcage-kernel
    Deployment               ironcage-api      (ghcr.io/chidionyema/ironcage-api:main, port 3001)
    Service                  ironcage-api
    RuntimeClass             gvisor

The source of truth for the manifests is the ironcage repo itself: `k8s/deployment.yaml`, already
fixed and pushed there. The right shape is probably for `idp` to reference it rather than copy it,
so the two cannot drift.

## Two things to know before touching this

**The sandbox internet-egress allowance.** `platform/ns-fences/allowances.yaml` gained
`demo-sandbox: egress_internet: [443]` for the ARM voice benchmark. The generated fence in
`platform/ns-fences/network/demo-sandbox.yaml` is regenerated from it by `bin/idp-ns-fence-gen`.
Never hand-edit the generated file.

**Never `gh pr merge` with a dirty tree.** It checks out `main` in the working directory. This
laptop's `main` and the working branch have **no common ancestor** (roots `e726816e` vs `9c380d8b`),
so switching between them makes files such as `bin/idp-oci-session` appear to vanish.

## Outstanding, unrelated to ironcage

* `arm-voice-bench` Job: **fixed, not yet re-run** (PR #3795 — the `$HOME`/read-only-root fault).
  It reached the ARM nodes and printed `aarch64 / 6 cores / asimd / 23.2 GB` before dying, so the
  hardware is confirmed; the int8-vs-fp32 NEON numbers are still unmeasured.
* `epistemic-ingest-github` and `-slack`: missing vault key `epistemic-fabric-github`. Not a code
  fault.
* `expert-vibethinker`: Pending on node memory.
* The OTEL injector fix (`c9493eae`) is on the working branch and **not yet merged to main**, so the
  live litellm is still receiving corrupted env vars.
