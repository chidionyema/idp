# The identity and secrets architecture, reviewed against a buyer's diligence

Measured 2026-09-04, 14:22Z, before building anything on top of it. The founder asked for the
review because the next build — one-shot secret ingestion for an enterprise customer — sits
directly on this layer, and a design is only as sound as the floor it stands on.

Everything below is either a file in this repository or a command whose output is printed. No
claim here rests on a description.

## What actually runs

Three human-facing surfaces, probed at 14:22Z from outside the estate:

```
catalogue  302 https://idcs-e664824341af437895312af8a61882b1.identity.oraclecloud.com/oauth2/v1/authorize?...
auth       302 https://idcs-e664824341af437895312af8a61882b1.identity.oraclecloud.com/oauth2/v1/authorize?...
hc         302 https://idcs-e664824341af437895312af8a61882b1.identity.oraclecloud.com/oauth2/v1/authorize?...
llm        200
```

The three doors a person opens all hand an anonymous request to the same identity domain. The
fourth, `llm`, answers 200 with no redirect because it is a machine door: its callers are
programs presenting a bearer token, and there is no browser to send anywhere.

The chain behind those redirects, in order:

1. **Traefik**, expressed in Gateway API (ADR 0001). Every hostname is an `HTTPRoute`; no service
   is given a port of its own.
2. **A ForwardAuth middleware** on the route (`platform/backstage/overlays/oke/httproute.yaml`,
   `platform/observability/httproute.yaml`, `platform/healthchecks/httproute.yaml`,
   `platform/guacamole/httproute.yaml`, `platform/weave-gitops/httproute.yaml`). The gateway
   subrequests every request to oauth2-proxy before the application sees it.
3. **oauth2-proxy** (`platform/identity/oauth2-proxy.yaml`, chart 10.7.0, two replicas, a pod
   disruption budget and a topology spread across nodes) answers that subrequest: 202 with the
   identity headers, or a redirect to the identity domain.
4. **Oracle Cloud Identity Domains** is the identity provider. The confidential application
   `front_door` is created by Terraform in `platform/oci/identity/main.tf`, and its client id and
   secret are written straight into the estate vault by that same apply — no person ever sees
   either value.

Secrets reach workloads by provenance, which is decision 0017:

- `ClusterSecretStore/estate-vault` — the OCI vault, for everything a machine minted.
- `ClusterSecretStore/human-vault` — Bitwarden Secrets Manager, for the few values only a person
  can produce. The bridge is External Secrets Operator's own Bitwarden provider; the estate
  writes no sync script.

Machine-to-machine access to the model router is already federated rather than shared: three
consumers hold a lane-scoped LiteLLM virtual key minted by `bin/idp-estate-seed`
(`hindsight`, `hermes-agent-env`, `otto-golden`), each with its own budget, and rotation is
`ROUTER_ROTATE=1` on the seed rather than a console visit.

## Where this is already the pattern an enterprise buyer expects

**The identity-aware proxy is the whole of it.** No application in the estate carries a login
page, a user table or a password reset. Authentication is a property of the network path, not of
each service — the shape Google's BeyondCorp made standard and every serious platform has copied
since. It is why adding a surface costs one `HTTPRoute` and a middleware reference and never a
sign-in flow.

**Header trust is closed correctly, which is where this pattern is usually broken.** An
identity-aware proxy hands the application a header saying who the caller is; if the application
trusts that header and anything can reach it directly, the header is a forgery kit. Here the
middleware lists `X-Auth-Request-User`, `X-Auth-Request-Email` and
`X-Auth-Request-Preferred-Username` under `authResponseHeaders`, which makes Traefik *overwrite*
whatever the client sent with oauth2-proxy's verdict, and every namespace carries a both-ways
default-deny `NetworkPolicy` so nothing reaches the pod except through the gateway. Two
independent controls, either of which alone would close it.

**No human holds a credential for the front door.** The OIDC client id and secret are Terraform
output written to the vault; the cookie secret is machine-generated. The pod reads all three from
a mounted file, never an environment variable, because the cluster policy
`secrets-not-from-env-vars` refuses the chart's default wiring outright.

**Transport manners are set once, at the edge, for every door.**
`platform/identity/edge-manners.yaml` sets HSTS with a two-year max-age, subdomains and preload,
`nosniff`, same-origin framing and a referrer policy, and strips the `Server` and `X-Powered-By`
banners so no door tells a stranger what is behind it.

**An expired session cannot break a running page.** The 2026-09-03 incident — a background API
call following a login redirect cross-origin and invalidating the sign-in the founder was typing
— was fixed by giving API routes their own middleware pointed at `/oauth2/auth`, which answers
202 or 401 and never a redirect. An API call is not a browser navigation, and the routes now say
so.

## The four gaps, in the order a buyer's engineer would find them

### 1. Authentication is strong; authorisation is flat

`platform/identity/external-secret.yaml` renders `email_domains = [ "*" ]`. No route asks for a
group, no `authResponseHeaders` list carries one, and `platform/observability/superset.yaml` sets
`AUTH_USER_REGISTRATION = True` with `AUTH_USER_REGISTRATION_ROLE = "Admin"`.

So the estate makes exactly one authorisation decision — *did the identity domain admit you* —
and the answer grants everything, everywhere, as an administrator. For one founder that is not
merely acceptable, it is the correct simplification, and the comment in `superset.yaml` says as
much: whoever the front door admits is the operator. For an enterprise customer it is the first
thing diligence asks about and the answer cannot be "there are no roles".

The fix needs no new component. The identity domain already holds groups; oauth2-proxy carries
them with `--set-xauthrequest` plus an `X-Auth-Request-Groups` response header, and enforces them
per route with `allowed_groups`. Each application then maps a group to its own role instead of
registering every arrival as an administrator.

### 2. One workload holds the router's root credential

`platform/infra-crew/external-secret.yaml` reads `LITELLM_API_KEY` from
`{ key: litellm-upstream, property: LITELLM_MASTER_KEY }`. That is not a per-consumer key; it is
the router's master key, which can mint keys, read every consumer's spend and change the model
list. Its own comment says so and parks the fix.

This is a gap of one line, not a design flaw: the pattern is built, proven and in use by three
other consumers. `bin/idp-estate-seed` mints a lane-scoped virtual key per entry, and adding a row
to its `ROUTER_PLAN` extends it. Fixed in the change that carries this document.

### 3. SPIRE runs and nothing reads it

`clusters/oke/platform.yaml` delivers `platform/spire` as a live Flux row with a HelmRelease
health check, so workload identity is installed and issuing SVIDs. The only files in the estate
that mention SPIFFE are SPIRE's own proof job and the policy that keeps it portable — no workload
authenticates with an SVID, and no service accepts one.

That is LAW 28 exactly: an instrument nobody reads is not an instrument. It is also the answer to
gap 2 in its mature form, because LiteLLM accepts JWT authentication and an SVID is a JWT with a
verifiable workload identity in it. Either the router starts taking SVIDs and the virtual keys
become a fallback, or the row is suspended until it does. Running and unread is the one state
with all of the cost and none of the benefit.

### 4. There is no customer identity, so a customer-facing admin surface has nothing to stand on

ADR 0013 chose Keycloak for customer sign-in, with one realm per product reconciled from git.
`platform/features/features.yaml` carries it as `status: planned` and `default: "off"`, and
`platform/customer-identity/` holds a realm directory and nothing else.

The estate can therefore sign in the founder, and cannot sign in a customer at all. This is the
finding that matters most for the work queued behind this review: the six-point secret-ingestion
design opens with an enterprise Admin UI where a customer pastes a key once and clicks Activate.
The only login the estate has admits its holder to everything as an administrator, so that UI has
no identity layer to sit behind, and building it first would mean either shipping it unprotected
or inventing a second sign-in — the stitching this platform exists to avoid.

## What follows for the secret-ingestion build

Read against the six points the founder set out, the floor holds for four of them and gives way on
two.

Proving a key before storing it, storing exactly one real root in the vault, and distributing it by
ExternalSecret on a refresh interval — points 2, 3 and 4 — are built and running today, in
`platform/vendors/consoles.yaml` (a `verify:` call and a `targets:` list per vendor),
`bin/idp-bootstrap-vendors` and the two secret stores. Automated rotation, point 6, exists for
router keys and needs extending to vendor keys, not inventing.

Proactive monitoring, point 5, is the piece with no floor problem and no component yet: nothing in
the estate watches whether a stored vendor key is still valid, which is why the DeepSeek lane was
dead for an unknown period and was found by a person rather than by an alert.

The customer-facing Admin UI, point 1, is blocked behind gap 4 and should not be started before
it. Its bleeding-edge alternative — a customer's own Bitwarden delivering the value with nobody
pasting anything — is already built, live and validated, and has never had one secret put through
it. That is the shortest road to the outcome he wants, and it needs no identity layer that does
not exist.

The honest summary is that this estate has an unusually strong perimeter for its age, one
authorisation decision where it needs several, and two capabilities installed and unused. None of
the four gaps requires a new platform layer; three of them are configuration on components that
are already running.
