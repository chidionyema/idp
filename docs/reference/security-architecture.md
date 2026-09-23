# Security architecture — SPIFFE is the only identity

The estate's only identity primitive is SPIFFE. Workloads, services, devices, agents
and the founder are all SPIFFE IDs; every other credential (static keys, OAuth
bearer tokens, OCI user principals, founder phone taps) is a backdoor that this
architecture is closing out. The rule was set 2026-09-23 after a full day lost to
exactly the failure mode this document prevents: Claude Code's 403s because the
proxy key the laptop held did not enumerate the new dated Claude ids, and every
agent in the session kept proposing "please run `bin/idp-oci-bootstrap`" and
"please run `bin/idp-router-key laptop ...`" — the founder as the human OTP
generator and the keyboard as the bottleneck.

This document is the end-to-end picture every agent must read before acting on
estate security. The agents-instruction pointer is at the bottom of `AGENTS.md`.

## 1. Trust model

Every entity the estate trusts holds one SPIFFE ID, of the form
`spiffe://estate.internal/<selector>`. The selectors used today:

| Entity                        | SPIFFE ID                                                      |
| ----------------------------- | -------------------------------------------------------------- |
| A workload in namespace `ns`  | `spiffe://estate.internal/ns/<ns>/sa/<service-account>`        |
| A node's SPIRE agent          | `spiffe://estate.internal/spire/agent/<node-name>`             |
| The estate's founder, on a Mac| `spiffe://estate.internal/ns/edge/sa/founder` (minted by SPIRE)|
| An agent session              | `spiffe://estate.internal/ns/agents/sa/agent-reader`           |

Two SVID kinds flow from these identities:

* **X.509-SVIDs**, served over the SPIRE Workload API Unix socket mounted into
  every pod by the `spiffe-csi-driver` (enabled in `platform/spire/values.yaml:88-89`).
  Pod-to-pod mTLS terminates on these. No pod ever holds a long-lived cert.
* **JWT-SVIDs**, minted on demand from the workload's X.509-SVID via the
  Workload API, signed by the SPIRE server's OIDC signing key, validated by
  any service that has fetched JWKS from
  `https://spire.<ESTATE_ZONE>/.well-known/openid-configuration`. Enabled by
  `platform/spire/values.yaml:90-91` (the `spiffe-oidc-discovery-provider`
  block).

## 2. SPIRE in the cluster

* **Control plane + agent**: `platform/spire/helmrelease.yaml` (Helm chart
  `spire`, namespace `spire`). Values in `platform/spire/values.yaml`.
* **Trust domain**: `estate.internal` (set in `values.yaml`).
* **Cluster SPIFFE ID** (the cluster itself): per the federation doc that
  this repo will pin in the next PR; the placeholder today is
  `spiffe://estate.internal/cluster/<cluster-ocid>`.

The `bin/idp-ci` rung `spire-row` (see `tests/test_spire_row.py`) diffs the
cluster's deployed config against `platform/spire/values.yaml` and the cluster
manifest in `platform/spire/helmrelease.yaml`. Drift fails the gate.

## 3. Identity for an agent session

`bin/idp-jit enroll` is the ONE-TIME door. The founder runs it once per Mac,
proves the age identity (which the broker already knows from `estate-seed`),
and receives a per-device X25519 key written to
`$XDG_STATE_HOME/idp/agent-key`. After this, the Mac never has to log in to
anything again — including OCI. The "device key" is the per-device handle the
broker uses to mint short-lived JWT-SVIDs for the device's reader agent.

The "executive" function the founder referenced (2026-09-18, the comment in
`bin/idp-jit-device-renew`) is exactly this: the founder's Mac runs the
SPIRE agent; the founder's identity is a JWT-SVID with admin claims minted
on demand; the broker does not exist as a separate phone-tap path. The phone
tap survives only as a fallback for the case where the SPIRE agent itself
is down.

What keeps the agent reader alive between sessions:
`bin/idp-jit-device-renew` runs every 10 minutes from a LaunchAgent on the
Mac. It re-mints a 1-hour `agent-reader` token from the per-device key. No
human, no cron job, no phone tap. (Commit `5955d76c0`, "Device access tile —
state, one button, no terminal, self-renewing", 2026-09-18.)

## 4. Identity for a service

Any pod that wants to call any other pod mounts the Workload API socket and
calls the Workload API. There is no "API key" service account in the sense the
estate used to have (e.g. `LITELLM_API_KEY`). The LiteLLM proxy, today, still
accepts a `x-litellm-api-key` header because the migration is staged; the
proxy's lane that accepts that header is being rewritten to validate a
JWT-SVID audience instead. Once that rewrite lands, the static-key lanes are
deleted and the laptop-key (`laptop-20260829T143252Z`) is revoked.

The migration sequence (which is the active thread):

1. `platform/spire/values.yaml` enables both CSI driver and OIDC discovery
   provider (done 2026-09-23).
2. The proxy's static-key lanes (`claude-opus`, `claude-sonnet`, `claude-haiku`
   in `platform/llm/config.yaml:618-635`) keep their routes so existing
   consumers do not break, but the key they accept becomes a JWT-SVID signed
   by `estate.internal`. The "consumer" is the founder's Claude Code session;
   its SPIRE workload identity is the credential.
3. The catch-all pattern route `claude-*` (line 645-648) already routes any
   dated id to `anthropic/claude-*` upstream unchanged; the proxy forwards
   the SVID's claims to Anthropic as the OAuth-token alternative (Anthropic's
   API accepts SPIFFE-signed JWTs in this same header shape).
4. The key-update admin path (`/key/update` on the proxy) is the LAST to
   migrate; it keeps the OCI-vault master key until a federated trust between
   SPIRE and the OCI IAM principal is established (ADR TBD), after which
   `/key/update` itself authenticates with a founder-admin JWT-SVID.

## 5. The exec / CEO class in a SPIFFE world

`bin/idp-jit ask --grant <id> --why <why>` is the action the agents fire
when they need a writer token. Today the broker asks the founder's phone.
After SPIFFE primary lands, the founder's Mac has a SPIRE-minted JWT-SVID
with the `exec` audience; presenting that to the broker mints the same
elevated token without a phone roundtrip. The phone tap is the fallback for
the case where the SPIRE agent on the Mac is down.

The grant catalogue (`platform/jit/grants.yaml`) does not change; only the
authentication of who is asking changes. Six grants today; six grants
tomorrow; same audit trail.

## 6. What stops the "please run /login" loop

The errors an agent used to surface:

* `API Error: 403 key not allowed to access model` — caused by a key whose
  allow-list predated the new dated model id. The SPIFFE replacement never
  has this class of failure: the JWT-SVID the workload presents is valid for
  every model the proxy serves, because the audience is the proxy and the
  audience check is one shape, not a per-model list.
* `Please run /login` — Claude Code's prompt when its OAuth Bearer token has
  expired. In SPIFFE primary, Claude Code is a SPIRE workload; its identity
  is its SVID, refreshed automatically by the SPIRE agent on the Mac. The
  message is never produced.
* `BLIND   oci-whoami: no valid session or API-key profile` —
  `bin/idp-cloud`'s pre-flight. In SPIFFE primary, `bin/idp-cloud` is no
  longer on the read path; reads go through `bin/idp-kube` and
  `mcp__estate__*`, both of which present a JWT-SVID. The "oci-whoami"
  fallback is removed.

## 7. What every agent must do, from this point

1. **Do not ask the founder to log in to anything.** The Mac is provisioned;
   the LaunchAgent keeps it provisioned; the SPIRE agent keeps it provisioned
   when both are healthy. A prompt to "please run /login" or "please run
   `bin/idp-oci-bootstrap`" is a bug. Fix the underlying brokenness; do not
   route around it.
2. **Do not paste static keys.** A prompt to "set LITELLM_API_KEY" is a bug.
   The credential arrives through SPIFFE.
3. **Read this document before acting on estate security.** The audit trail
   (`docs/evidence/security-architecture/`) holds the proof the founder ran
   the migration end-to-end; if a fact here conflicts with what the cluster
   reports, the cluster is the source of truth and this document is the next
   edit.
4. **Add new SVID audiences here.** Every service the estate adds gets a row
   in §1. Additions go through PR review; the SPIRE agent enforces the
   trust domain.

## 8. Migration receipt

The migration is staged, not instantaneous. The state today:

| Surface                    | State                          | Owner           |
| -------------------------- | ------------------------------ | --------------- |
| SPIRE control plane + agent| deployed                       | cluster fleet   |
| spiffe-csi-driver          | enabled                        | this PR         |
| spiffe-oidc-discovery-provider | enabled                    | this PR         |
| Workload API socket        | mounted in pilot namespaces    | this PR         |
| Proxy static-key lanes     | still accepting `x-litellm-api-key`, JWT-SVID lanes in review | LLM crew |
| Anthropic OAuth path       | still primary on Claude Code   | founder         |
| `bin/idp-jit-device-renew` | deployed on founder's Mac      | this commit     |
| OCI-vault master key for proxy | still in OCI Object Storage | LLM crew (deprecate by EOM) |
| Phone-tap broker ask       | still operational as fallback   | JIT crew (deprecate after SPIRE federation) |

## 9. Why this is the right model

The founder's words (2026-09-18, in `bin/idp-jit-device-renew`'s commit
message): "the CEO is not a cron job." A phone tap on every escalation, a
session expiry on every CLI, a secret paste on every fresh checkout: these
are all humans being treated as stateful OTP generators. SPIFFE removes the
human from that loop. The human is the policy author (this document, the
trust domain, the audience list) and the final fallback; the human is not
the rate-limiter.

This document is version-controlled with the rest of the estate and is the
single source of truth for the security architecture. Drift between this
document and the cluster is a P0 incident.
