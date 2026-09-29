# Authorization Contract (zero-trust)

**Founder ruling 2026-09-17.** The estate is zero-trust. Every policy exists so junk cannot
enter the cluster, and any lever an agent can reach to bypass a policy is a security breach.
**Founder, 2026-09-29:** "founders work surface broken is a security breach", "needs firewalled
from agent carelessness", "need clearance to work on it". The founder's work surface is guarded
by the same contract.

## The founder key: what it is and what it is not

The founder key is a personal Ed25519 key pair that proves **the founder approved a change to a
guarded file**.

| | Founder key | SPIRE / SPIFFE (`platform/spire`) |
|---|---|---|
| Identifies | the founder, a person | a workload in the cluster (e.g. `spiffe://estate.internal/ns/llm/sa/idp-router`) |
| Used for | signing git commits that touch guarded paths | pods proving who they are, e.g. to the key broker before it serves a secret |
| Lifetime | long-lived, rotated by hand | short-lived SVIDs, issued and rotated automatically by the SPIRE server |
| Lives | private half: `~/.idp/founder.key`; public half: `docs/keys/founder.pub` | issued in the cluster, never in git |

**They are unrelated.** Losing, rotating or leaking one has no effect on the other.

## Guarantees

A commit merged to `main` satisfies all three of the following, verified by the required
`guarded-paths` check (`bin/idp-ci-guarded-paths`):

1. **Signed by the hooks.** The commit carries an `X-Idp-Signed:` trailer, an HMAC of the commit
   body keyed by `.git/idp-hook-secret` (per checkout, provisioned by `bin/idp-install-hooks`).
   `git commit --no-verify` produces no stamp.
2. **Founder-authorized when it touches a guarded path.** The PR's head commit carries an
   `X-Idp-Auth:` Ed25519 signature over `(timestamp, parent sha, reason, paths)`. The signature
   is verified against **`docs/keys/founder.pub` as it is on the base branch (main)**, never
   against the PR's own copy.
3. **No blind-accept merges.** `X-Idp-Merge-Strategy: theirs` or `ours` is refused.

The check fails closed. If it cannot resolve the base, or cannot compute what the PR changed, it
refuses the PR.

### What was not true before 2026-09-29

This document described these guarantees from 2026-09-17, but two defects meant they did not hold:

- **The guard never fired.** It computed the changed files with `"$BASE"...HEAD_REV`, which is
  the literal word, not the variable. git refused it, `|| true` hid the refusal, and the changed
  list was always empty. An unsigned edit to `bin/idp-guarded-paths` got "ok".
- **Any PR could approve itself.** The signature was checked against `docs/keys/founder.pub` in
  the PR's own tree, and `docs/keys/` was not guarded. A PR could swap in its own public key and
  sign with its own private key, and the old guard answered "founder signature valid".

`tests/test_guarded_paths_fires.py` reproduces both. Every case fails on the old guard and
passes on the fixed one, and a control case proves that a real founder signature still passes.

## Guarded paths (`bin/idp-guarded-paths`)

**Policy and cluster admission**
- `platform/edge/otel-endpoint-exception.yaml`, `inject-otel-endpoint.yaml` and
  `require-otel-endpoint.yaml`
- `platform/policies/kyverno/`

**The contract itself**
- `.githooks/`
- `bin/idp-auth`, `bin/idp-auth-verify`, `bin/idp-guarded-paths` and `bin/idp-ci-guarded-paths`
- `docs/keys/`: the trusted public key

**The founder's work surface**
- `backstage/packages/app/src/modules/room/` and `backstage/packages/app/src/modules/home/`: the
  /fleet Reactor and home
- `backstage/packages/app/e2e-tests/fleet`: the /fleet end-to-end tests
- `backstage/plugins/fleetview-backend/` and `fleetview-backend.Dockerfile`: the sidecar that
  serves /fleet's data and voice
- `platform/backstage/`: the catalogue's deploy manifests
- `tests/test_fleetview_image_imports.py` and `tests/test_guarded_paths_fires.py`: the regression
  gates. A gate cannot be weakened in the same unsigned PR that breaks what it guards.

## Signing a change (founder only)

The signature covers the commit the founder signed. That commit becomes the **parent** of the
commit carrying the trailers, so the signature goes on one new, empty commit at the branch tip:

```sh
git pull --ff-only                       # be at the tip you are approving
git commit --allow-empty -m "auth: <what you approve>" \
  -m "$(bin/idp-auth '<one-line reason>' <guarded-path> [<guarded-path>...])"
bin/idp-auth-verify HEAD                 # must print: ok idp-auth: valid founder signature
git push
```

`<guarded-path>` lists the guarded paths the branch touches. The check's failure message names
them. A new commit after signing invalidates the signature, so sign last.

## Keeping the key safe

Today the private key is a single file, `~/.idp/founder.key` (mode 600), on the founder's laptop.
That creates two risks:

1. **Agents can read it.** Agent sessions run on the same laptop with shell access, and file
   permissions do not stop a process running as the founder's user. Signing proves founder
   intent only as long as no agent touches the file.
2. **There is no copy.** If the laptop dies, the key dies with it.

### Do now: take the key off the disk, keep it in the password manager

The steps assume 1Password and its `op` CLI; any password manager with a CLI works the same way.

```sh
op document create ~/.idp/founder.key --title "idp founder signing key" --vault Private
op document get "idp founder signing key" --vault Private | shasum -a 256
shasum -a 256 ~/.idp/founder.key        # the two hashes must match before the next line
rm -P ~/.idp/founder.key
```

To sign, fetch the key into a temporary file only for the signature:

```sh
k=$(mktemp) && chmod 600 "$k" && op document get "idp founder signing key" --vault Private > "$k" \
  && git commit --allow-empty -m "auth: ..." -m "$(IDP_FOUNDER_KEY=$k bin/idp-auth '<reason>' <paths>)"; rm -P "$k"
```

The password manager is then the backup, and it is protected by the founder's master password and
second factor. An offline second copy (an encrypted USB drive in a drawer) covers losing the
password manager account too.

### Next: a hardware key

The strongest form is a key that never exists as a file: a FIDO2 security key (a YubiKey) holding
an `ed25519-sk` key, which signs only when touched. That needs `bin/idp-auth` and
`bin/idp-auth-verify` to sign and verify with `ssh-keygen -Y sign` / `-Y verify` instead of
`openssl pkeyutl`. That change is not made yet. It is itself a guarded change, and the founder
signs it with the current key before rotating.

## If the key is lost

Nothing is locked out permanently, because the GitHub account is the root of trust, not the file.

1. Make a new pair: `openssl genpkey -algorithm Ed25519 -out ~/.idp/founder.key && chmod 600
   ~/.idp/founder.key && openssl pkey -in ~/.idp/founder.key -pubout -out docs/keys/founder.pub`.
2. A PR changing `docs/keys/founder.pub` needs a signature from the **old** key, which no longer
   exists. As repository owner, in GitHub settings, temporarily remove `guarded-paths` from the
   required checks of the `required-checks-main` ruleset.
3. Land the new public key, then restore `guarded-paths` to the ruleset at once.
4. Record the rotation in `docs/decisions/` with the date and the reason.

Protect the GitHub account (hardware second factor, recovery codes offline) as carefully as the
key: whoever controls it can do step 2.

## If the key leaks

Treat it as compromised immediately: rotate with the steps above (the old key still works, so a
normal signed PR replacing `docs/keys/founder.pub` suffices). Then review every commit carrying
`X-Idp-Auth` since the suspected leak: `git log --grep '^X-Idp-Auth:' --since <date> main`.

## Bypass levers that are structurally closed

| Lever | Refusal path |
|---|---|
| `git commit --no-verify` / `git push --no-verify` | HEAD lacks `X-Idp-Signed`, so `guarded-paths` refuses |
| `PRE_COMMIT_SKIP=1`, `IDP_MAIN_GREEN_GATE=0`, `IDP_WIP_GATE=0` | Env-var checks removed from the hooks |
| `git merge -X theirs` / `-X ours` | `X-Idp-Merge-Strategy` trailer refused |
| Edit a guarded file unsigned | `X-Idp-Auth` required |
| Replace `docs/keys/founder.pub` and self-sign | Verified against main's key; `docs/keys/` is guarded |
| Point the check at a missing base | Refused; the base must resolve |

## What this does not close

- **Author-based exemption.** Commits authored as the founder's email skip the `X-Idp-Signed`
  requirement, and agents commit under that identity. Guarded paths still need `X-Idp-Auth`.
- **Repository settings.** A ruleset disabled in GitHub settings is outside git. Only a
  GitHub admin can do that; alerting on ruleset changes is a follow-up.
