# Job-bound capability authority — revocable access and independent proof

**Canonical owner:** IDP #7787 (action-door enforcement), IDP #7771 (FLOW), #7800 (trusted-base recovery), existing QUAD identity, executor, Greenlane, KARMA. **Adoption:** staged canary only. This document is a standard, not proof of deployed enforcement.

## Security invariant

Every privileged external effect is separately authorised for an exact actor, immutable workload, instruction, action, resource, payload digest and bounded time interval. A completed effect does not settle the job until the independent verifier confirms both its externally observed result and the termination of residual authority.

No agent may create, approve, sign, extend, refresh, revive or grade its own privileged grant. Do not create another broker, scheduler, credential database, issue tracker or policy hierarchy; use the existing executor action door and custody planes.

## Threat and trust assumptions

- An attacker may control prompts, agent tool arguments, repository text, an issue, an unprivileged worker or a queued branch.
- Model-visible data may try to instruct the agent to elevate itself, change repositories or issue numbers, repeat calls, re-use expired credentials or forge the founder's consent.
- A trusted authority and the provider's signing/minting keys are isolated from agents; the broker enforces permit validation before the effect; protected policy revision and monotonic clock are independently controlled.
- A stolen secret held outside the broker, an already accepted remote mutation, or a compromised host privileged to alter the broker exceeds this boundary. Report such paths as **UNMEDIATED**, never as guaranteed safe.
- Refusal to provide any lease must preserve read-only diagnostics and authorised separately scoped recovery. A policy that blocks its own recovery is an incident, not a security success.

## Lease and action contract

An accepted FLOW instruction is a request for execution, *not* a privilege grant. Existing QUAD identity and independent authorisation create permits with these fields:

`lease_id, instruction_id, issuer, agent_urn, workload_identity, policy_sha256, repository_id, environment, action_verb, target_resource_id, payload_sha256, issued_at, expires_at, max_effects, atomic_nonce, idempotency_key, independent_verifier, revocation_mode`.

On every effect the trusted broker must atomically consume a one-use nonce and check the actor, workload identity, action verb, canonical target, exact payload, current policy, dependencies and deadline. At most one effect is allowed for a one-action permit. A commit trailer, ChatGPT answer, issue comment, fabricated proof or agent-controlled environment variable never changes authorisation.

On unavailable authority, expired lease, replay, unknown dependency, stale incident record or malformed permit, privileged operations are refused while unaffected safe operations continue. No self-certified bypass, synthetic incident, or trusted-policy mutation by an untrusted agent.

## Existing GitHub implementation — deliberately bounded

- Source: `bin/idp-github-app` and `platform/github-app/lanes.json`.
- Initial repository-scoping canary: `platform/github-app/job_token_request.py` plus `job-token-scopes.json` instruct the existing issuer to request a `ticket-verifier` token limited to **two immutable GitHub repository IDs**: `1342523800` (`chidionyema/crew`, actual ticket updates and status comment #102) and `1344360654` (`chidionyema/idp`, verdict GitHub Actions reads). Source authority: `.github/workflows/ticket-verification.yml` and `bin/idp-ticket-verify` (default `--repo owner/crew`, `--idp owner/idp`). A narrower IDP-only issuance would break the real workflow; no other installation repositories are authorized by this canary. Existing permission envelope is unchanged (issues:write, actions:read, metadata:read).
- Unenrolled lanes retain their old provider request pending authenticated consumer census. The canary may not be promoted estate-wide without evidence that legitimate workflows remain operational.
- The GitHub installation token is still a one-hour bearer credential, **not** a five-minute job-bound capability. A later broker lease can expire earlier but must enforce that deadline independently.
- Action-level authorisation, atomic nonce consumption, broker-only token custody and automatic revoke are NOT implemented by the repository-scope patch. Do not count it as full containment.
- GitHub provider revocation: `DELETE /installation/token` using the credential itself. Only an independent denial probe confirms its effect. Never put raw credentials in model prompts, agent transcripts or long-lived logs.

## Required operational state machine

`ACCEPTED → IDENTITY_VERIFIED → PERMITTED → LEASE_ACTIVE → EFFECT_CHECKED → EFFECT_READBACK → QUIESCING → REVOKE_REQUESTED → REVOKE_VERIFIED → SETTLED`.

If provider revocation or denial probe fails after a verified effect, return `EFFECT_VERIFIED / AUTHORITY_UNVERIFIED`. If an operation was already accepted remotely, revocation does not roll it back; separately reconcile and contain it. A crash without completion event must not outlive the broker lease deadline.

## Negative and positive tests

| Failure injection | Must happen |
|---|---|
| Wrong repository, issue, method, body digest, workload, actor | DENY |
| Forged issuer / founder signature or model-claimed approval | DENY |
| Duplicate dispatch, replay, race between two workers | One atomic use maximum |
| Expired token, 300-second broker deadline, crash, timeout, cancel | New effects DENY independently of agent heartbeat |
| Privileged bypass directly using raw bearer | Token inaccessible to agent; deny via provider restriction |
| Missing revocation receipt, provider outage or UNKNOWN health | No verified settlement; safe diagnostics remain |
| Safe nondependent work during incident | Continues; no blanket freeze |
| Exact approved action | Provider effect accepted once, independently observed |
| Provider revoke then re-use old bearer | Provider denies; receipt independently stored |

Run negatives against a real isolated GitHub installation and test repository in addition to hermetic tests. No protected-branch changes, signing, source approvals or business data may be forged. Measure independent original effect receipt, provider revocation and negative replay; then read the exact state from Genesis and KARMA.

## Promotion and honesty

`SOURCE_CANDIDATE → TESTED → CI_VERIFIED → REVIEWED → MAIN_MERGED → PROVIDER_SCOPE_CANARY → BROKER_CANARY → REVOKE_VERIFIED → GENESIS_READBACK → OPERATING`.

Each transition requires exact SHA, CI run, actor, policy revision, verifier, timestamp, exception class, and provider readback. A PR, ZIP, passing tests, successful workflow or HTTP response by itself is not verified production yield.

**Research references:** [GitHub App token creation](https://docs.github.com/en/rest/apps/apps#create-an-installation-access-token-for-an-app), [GitHub token revocation](https://docs.github.com/en/rest/apps/installations#revoke-an-installation-access-token), [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693) token exchange, [RFC 9396](https://www.rfc-editor.org/rfc/rfc9396) rich authorisation, [RFC 9449](https://www.rfc-editor.org/rfc/rfc9449) DPoP, [SPIFFE](https://spiffe.io/docs/latest/spiffe-about/overview/), [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final).
