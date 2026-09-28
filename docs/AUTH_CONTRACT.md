# Authorization Contract (zero-trust)

**Founder ruling 2026-09-17.** The estate is zero-trust. Every policy exists so junk cannot
enter the cluster. Any lever an agent can reach to bypass a policy is a security breach. This
contract closes the reachable levers with cryptographic guarantees; nothing here is memory or
convention.

## Guarantees

A commit merged to `main` satisfies **all three** of the following, verified server-side by the
required `guarded-paths` CI check:

1. **Signed by the hooks.** The commit carries an `X-Idp-Signed:` trailer that is an HMAC of the
   commit body, keyed by `.git/idp-hook-secret` (per-checkout, provisioned by
   `bin/idp-install-hooks`, never on the tree). `git commit --no-verify` produces no stamp, so
   the required check refuses the PR.

2. **Founder-authorized when touching a guarded path.** Any commit that changes a file listed by
   `bin/idp-guarded-paths` must carry an `X-Idp-Auth:` trailer that is an Ed25519 signature over
   the tuple `(timestamp, parent-sha, reason, paths)`, verified against the founder public key at
   `docs/keys/founder.pub`. Only the private key at `~/.idp/founder.key` (mode 600) can produce a
   valid signature. No agent holds this key.

3. **No blind-accept merges.** A commit whose message contains `X-Idp-Merge-Strategy: theirs` or
   `X-Idp-Merge-Strategy: ours` is refused. Legitimate merges declare no such trailer.

## Guarded paths (`bin/idp-guarded-paths`)

- `platform/edge/otel-endpoint-exception.yaml` — the OTel exception queue; every entry requires
  a ticketed reason recorded in the file plus a founder signature on the commit that adds it.
- `platform/edge/inject-otel-endpoint.yaml` — the Kyverno mutation that injects the endpoint.
- `platform/edge/require-otel-endpoint.yaml` — the Kyverno validation that refuses workloads
  without an endpoint.
- `platform/policies/kyverno/` — every other Kyverno policy in the tree.
- `.githooks/` — the hook infrastructure itself; a change to a hook cannot go in without
  founder authorization.
- `bin/idp-auth` — the signing tool.
- `bin/idp-guarded-paths` — this list itself.
- `bin/idp-ci-guarded-paths` — the enforcer.

## Founder ceremony

To change a guarded file the founder runs, from the working tree:

```sh
bin/idp-auth "<one-line reason>" <guarded-path> [<guarded-path>...] \
  | git interpret-trailers --in-place --if-exists=addIfDifferent HEAD
```

The four trailers appended to HEAD are: `X-Idp-Auth`, `X-Idp-Auth-Reason`,
`X-Idp-Auth-Timestamp`, `X-Idp-Auth-Paths`. `bin/idp-auth-verify HEAD` proves the signature
against `docs/keys/founder.pub` before pushing.

## Bypass levers that are structurally closed

Every one of the following was reachable to an agent before this contract. Each is now refused
mathematically:

| Lever | Refusal path |
|---|---|
| `git push --no-verify` | HEAD lacks `X-Idp-Signed` → `guarded-paths` refuses |
| `git commit --no-verify` | Same |
| `PRE_COMMIT_SKIP=1 git commit` | Env-var check removed from `.githooks/pre-commit`; hook runs unconditionally |
| `IDP_MAIN_GREEN_GATE=0` | Env-var check removed from `.githooks/pre-push`; founder override requires a signed token file |
| `IDP_WIP_GATE=0` | Same |
| `git merge -X theirs` / `-X ours` | Merge stamped with `X-Idp-Merge-Strategy` → refused |
| Direct edit `otel-endpoint-exception.yaml` | Guarded path → `X-Idp-Auth` required |
| Direct edit `inject-otel-endpoint.yaml` | Same |
| Direct edit `require-otel-endpoint.yaml` | Same |
| Flip Kyverno `failureAction: Enforce` → `Audit` | Guarded path → signature required |

## Key rotation

The founder key is a 32-byte Ed25519 private key. Public key at `docs/keys/founder.pub` is what
`bin/idp-auth-verify` reads. Rotating the key is a single, founder-signed PR that replaces the
public key file; that PR is itself gated by the current key (bootstrap: the initial key is
committed by the same founder push that ships this contract, with the `X-Idp-Signed` HMAC alone
covering the bootstrap commit).

## What this does not close

- A founder whose private key leaks. This is a key-hygiene problem, not a lever problem.
- A required-check ruleset that is later disabled at the repo settings level. That surface is
  itself GitHub-admin-only; add an audit workflow to alert on ruleset changes as a follow-up.
