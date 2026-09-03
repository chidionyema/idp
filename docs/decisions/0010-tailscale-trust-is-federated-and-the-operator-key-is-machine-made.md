# 0010. Tailscale trust is federated from GitHub; the operator's key is machine-made; the no-secret road is parked at £58 a month

- Status: ACCEPTED 2026-08-29 (founder: "ok that's fine, we need to document all this ... every single thing we do is hard won knowledge").
- Date: 2026-08-29
- Deciders: founder (the money and the one-way step), session 2d8b3bd0 (the research)
- Affects: how the cluster joins the tailnet; `bin/idp-bootstrap-tailscale`; `platform/tailscale`; `clusters/oke/estate-config.yaml`; crew#66, crew#618, crew#620.

## The day, in plain words

The cluster needs Tailscale's permission to join the private network. Permission is either a
password somebody holds, or trust that the joining party proves each time. Three roads were on
the table by the end of 2026-08-29; one was built twice, one is chosen, one is parked.

### Road 1, deleted: a person makes a password in the console

`idp-set-root tailscale` sent the founder to the Tailscale console to create an OAuth client and
paste two values into repository secrets (`SEED_TAILSCALE_CLIENT_ID/_SECRET`, idp#742). He was
marched there three times, once to a page that does not exist. He refused, correctly: the
federated road below already existed on main (idp#722) and the summaries every session was
reading said otherwise. Ruling: never propose a console-secret road when a no-secret road exists.
Memory `summary-over-source-is-the-mistake-class`; the removal is tracked on crew#66.

### Road 2, chosen: GitHub proves itself, then a machine makes the key. Cost £0

1. The founder registered one federated identity in Tailscale (Trust credentials, OIDC):
   description `estate`, issuer GitHub Actions, subject `repo:chidionyema@377396/idp@1344360654:*` (GitHub immutable subject: idp was created 2026-08-24, after the 2026-07-15 cutoff; the classic `repo:chidionyema/idp:...` form was refused, run 33248046751; source: GitHub OIDC reference, "Immutable subject claims", https://docs.github.com/en/actions/reference/security/oidc; the id comes from `gh api repos/chidionyema/idp/actions/oidc/customization/sub` -> `sub_claim_prefix`; Tailscale's matching rules, https://tailscale.com/kb/1581/workload-identity-federation),
   scope `oauth_keys` write, client id `T8XvMsM4vA11CNTRL-kmgFbQMnqn11CNTRL` (a public id, not a
   secret; `clusters/oke/estate-config.yaml`, idp#754). This is the one human step, done once.
   Scope rule learned on 2026-08-29 (run 33264994104, `actor cannot set scopes`): a Tailscale
   identity can only grant scopes it itself holds, so the identity carries every scope the
   operator client will get: auth_keys write and devices:core write (both bound to `tag:k8s`),
   policy_file write, users read, oauth_keys write. A write scope bound to a tag is refused
   until the tailnet policy defines that tag in `tagOwners`, so `tag:k8s` (and `tag:founder-mac`)
   were put into the tailnet policy first (source: tailscale.com/kb/1581, "scopes and tags").
   Both were set in the console by the agent session, not the founder, and the identity page
   shows `auth_keys +6`, tag `tag:k8s`.
2. On `oke-check apply` the runner asks GitHub for an OIDC token with audience
   `api.tailscale.com/<client id>` and posts it to `POST /api/v2/oauth/token-exchange` with
   `client_id` and `jwt` (the exact request on tailscale.com/kb/1581). Tailscale answers a
   short-lived token. No secret exists on the runner.
3. With that token the runner creates the operator's OAuth client through the API
   (`POST /api/v2/tailnet/-/keys`, `keyType: client`, scopes auth_keys, devices:core, policy_file,
   users:read, tag `tag:k8s`), writes it to vault entry `tailscale-operator`, and the ExternalSecret
   `tailscale/tailscale-operator-secret` hands it to the operator. The daily run rotates it and
   deletes the old one.

From the founder's side: nothing to type, ever. The one difference from road 3 is that a
machine-made password exists in the vault. That was the founder's question and answer, verbatim:
"so what option gets us seamlessness without the extra increase in price" -> this one.

What broke on the first run (oke-check 33244862380): Tailscale refused the exchange and the
script printed `ok federated` before reading the answer, then failed on the seed line. Silent
green. Fixed in the PR that carries this record: HTTP status checked, the full refusal printed,
non-zero exit, no fall-through to any secret road, mock tests for 200, 403 and an empty 200.

### Road 3, parked: the operator itself is trusted, no key exists anywhere. Cost £58 a month

Found late, by reading the operator's own Helm chart instead of writing a script
(tailscale/tailscale cmd/k8s-operator/deploy/chart: values.yaml lines 32-42, templates/deployment.yaml
lines 44-52): the chart takes `oauth.clientId` + `oauth.audience` and mounts a projected service-account
token; the operator exchanges that token with Tailscale itself. No vault entry, no rotation, no
`bin/idp-bootstrap-tailscale` at all. It needs:

- the cluster to publish an OIDC discovery endpoint. OKE does (`is_open_id_connect_discovery_enabled`,
  updatable in place, provider doc `containerengine_cluster` line 166) but only on an **enhanced**
  cluster. Ours is `cluster_type = "basic"` (`platform/oci/main.tf:13`). Basic to enhanced is an
  in-place upgrade and cannot be undone (docs.oracle.com contengcomparingenhancedwithbasicclusters).
- price, from Oracle's public price-list API on 2026-08-29: `OCI Kubernetes Engine - Enhanced
  Cluster` GBP 0.07987 per cluster-hour = £57.51 a month. Basic is free.
- one Tailscale federated identity for the operator: issuer = the OKE discovery URL, subject
  `system:serviceaccount:tailscale:operator`, scopes auth_keys + devices:core, tag `tag:k8s`. The
  API creates it (`keyType: federated`, Go client `CreateFederatedIdentityRequest`), and the road-2
  identity has the `oauth_keys` scope to make that call from CI. No console.

Founder's decision: not now. Reopen when the enhanced tier is wanted for another reason (node
cycling, SLA, workload identity for OCI itself); then this is one Terraform bool, one API call
and a Helm values change, and road 2 and its script are deleted.

## The lesson, so it is not paid for twice

Read the vendor's chart, values and API before the first line of a script (LAW 43). The
no-secret mode had been in the operator chart the whole time; every design of the day started
from "how do we hand the operator a secret" instead of "does the platform already do this".
The estate-wide fence for the shell-script class is crew#620.

## Sources read raw on 2026-08-29 (never from memory)

- tailscale.com/kb/1581 workload identity federation: the token-exchange request shape
- tailscale.com/kb/1215 trust credentials: the console page and the two credential kinds
- github.com/tailscale/tailscale `cmd/k8s-operator/deploy/chart` values.yaml, deployment.yaml
- github.com/tailscale/tailscale-client-go-v2 keys.go: `CreateFederatedIdentityRequest`
- github.com/tailscale/github-action README: federation section (`audience`, `id-token: write`)
- oracle terraform-provider-oci `containerengine_cluster` doc; docs.oracle.com OIDC discovery and
  enhanced-vs-basic pages; apexapps.oracle.com cetools price-list API

## Amendment 2026-09-03: the identity carries the tags it mints

The apply run of 2026-09-03 12:42Z (run 33756246171) exchanged the federated identity's token,
held every scope, and then the operator mint answered `requested tags [tag:k8s tag:k8s-operator]
are invalid or not permitted`. Tailscale lets an actor mint only the tags its own tags own
(kb/1215); the identity had been registered from code with scopes and no tags, and `tagOwners`
in the policy cannot change that.

Decision: the registration body carries `tags: [tag:k8s, tag:k8s-operator]`, and road a reads
the identity's own key record (`GET /api/v2/tailnet/-/keys/<id>`) before trusting it; an
identity that exchanges but carries no tag is re-registered by road b on the next apply, with no
console step. Guard: `tests/test_incident_crew66_seed_registers_the_federated_identity_from_code.py`
(the drift test `..._carries_no_tags_is_re_registered_with_them`). The tests also blank the
runner's `ACTIONS_ID_TOKEN_REQUEST_*` variables themselves: the verify-claims job runs them with
those set, and road b was being entered from a test that meant to stay off the runner.
