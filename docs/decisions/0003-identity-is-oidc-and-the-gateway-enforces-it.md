# 0003. Identity is OIDC, the gateway enforces it, and Authelia implements both

- Status: DECIDED 2026-08-24 on the founder's instruction ("final decision"). Only the founder
  moves a thing to live (ruling R16), so this records the choice; it does not claim it runs.
- Date: 2026-08-24
- Deciders: founder
- Closes: the one question ADR 0001 left open — "The identity proxy is not chosen."
- Affects: every human-facing surface in the estate, starting with the board on :3300

## The problem, measured on 2026-08-24

The founder, for the second time: *"still getyting xhttp://localhost:3300/login, i thoght we
sprted out seanless secutort, any ticket for that"*.

There was no ticket. `crew` issues #133, #119, #114, #102, #101, #95, #85 and #34 are about the
board as a concept; none is about its authentication. ADR 0001 named this blocker and pointed at
`idp/board/MIGRATION.md`, and that file did not exist. So the blocker was recorded in a citation
to nothing, which is why it stayed open and why he had to ask twice.

`crew/docs/STANDARDS.md` has 16 layer rows and **no identity row**. Nothing was agreed. That is
the honest answer to "what was agreed".

Measured state of the doors, this machine, this date:

```
world-reachable listening binds: 7      localhost-only binds: 18
  *:7107        node            Backstage backend      <-- ours, and wrong
  *:53145       ssh -> k3d      k3s API server :6443   <-- ours, and wrong
  0.0.0.0:8080  prospector-edge Caddy, the drill edge  <-- intended
  0.0.0.0:8443  prospector-edge Caddy, the drill edge  <-- intended
  *:5000 *:7000 ControlCe       Apple AirPlay receiver, not ours
  *:49248       rapportd        Apple Continuity, not ours
  *:53          limactl         colima DNS
```

The claim that agents are scattering `0.0.0.0` bindings is **mostly false and specifically true**:
18 of 25 binds are loopback, every Docker publication except the edge is `127.0.0.1`, and the two
that are wrong are the developer portal and the Kubernetes API server. Those two are the finding.

## The decision

**Identity is OIDC. Authorisation is enforced at the gateway, not in each application. The
implementation is Authelia, and it is replaceable because the contract is a standard.**

Three parts, kept separate for the same reason ADR 0001 split standard from implementation.

**1. The contract is OIDC for login and Envoy `ext_authz` for enforcement.** Gateway API is
standardising exactly this as GEP-1494 `HTTPExtAuthFilter`, which speaks the Envoy ext_authz
protobuf over gRPC or plain HTTP where a 200 means allow. GEP-1494 is **Experimental** today, so
we write the same contract in Traefik's ForwardAuth now and move to the filter when it lands. The
HTTP form is byte-identical in both: a subrequest, a 200, and identity in response headers.

**2. The implementation is Authelia.** Apache-2.0, created 2016-12, 28,681 stars, **118 open
issues**, v4.39.20 released 2026-05-26. One Go binary. It is both halves at once: an OpenID
Connect Provider, and a forward-auth endpoint the gateway subrequests. It sets `Remote-User`,
`Remote-Groups`, `Remote-Name` and `Remote-Email` on the allowed response.

**3. No application keeps its own login.** An app that can consume a trusted header does. An app
that cannot becomes an OIDC client. Nothing gets a second password.

## Why not the alternatives

Figures read from the GitHub API on 2026-08-24.

- **Keycloak** (36,383 stars, Apache-2.0, 26.7.2 on 2026-08-19, CNCF) is the answer a buyer's
  engineer expects, and it is the one I would pick on a cluster with users. It is rejected *here*
  for a falsifiable reason, not a preference: Keycloak is an IdP and **not** a proxy, so it cannot
  enforce anything at the gateway on its own — it needs oauth2-proxy in front of it. That is two
  containers plus a Postgres and a JVM, for one user, on a laptop whose owner has said three times
  today that it is too slow. Authelia is one container and does both jobs.
  **The swap is cheap and that is the point of part 1**: because the contract is OIDC, moving to
  Keycloak changes an issuer URL and a client secret. It does not touch one route.
- **Zitadel** (14,844 stars, v4.17.1 on 2026-08-14) is **AGPL-3.0**. We are selling this platform.
  An AGPL component in a *platform layer* the buyer inherits is a question their lawyer asks and we
  cannot answer cheaply. Kanboard is AGPL and that is accepted, because a product a buyer may
  replace is not the same risk as a layer everything runs on.
- **oauth2-proxy** (14,870 stars, MIT) is only the enforcement half. Choosing it still leaves the
  IdP unchosen, which is the question this ADR exists to close.
- **Ory Hydra** (17,495 stars) is a bare OAuth2 server with no user management by design; Kratos is
  a second component. Two moving parts where Authelia is one.
- **Pomerium** was checked and is **not** on the Gateway API conformance list.
- **A per-application login.** This is the status quo and it is what produced the question.

## What this immediately fixes, using both products as documented

Kanboard's own `config.default.php`, read on 2026-08-24, carries the seam already:

```php
define('REVERSE_PROXY_AUTH', false);              // -> true
define('REVERSE_PROXY_USER_HEADER', 'REMOTE_USER'); // -> the header Authelia sets
define('REVERSE_PROXY_DEFAULT_ADMIN', '');        // -> the founder's username
define('HIDE_LOGIN_FORM', false);                 // -> true, no form to meet
define('SESSION_DURATION', 0);                    // 0 = until the browser closes
define('REMEMBER_ME_AUTH', true);
```

No plugin, no patch, no script. The login page disappears because Kanboard is being used the way
its maintainers documented, behind a proxy that has already established who you are.

## Consequences, and the one that is a real risk

- One process holds every door. If Authelia is down, nothing behind the gateway is reachable.
  That is the price of removing per-app logins and it is accepted, bounded two ways: loopback
  bindings stay in place through the migration, and the swap to Keycloak is an issuer URL.
- `REVERSE_PROXY_AUTH` trusts a header. A header is only trustworthy if the application cannot be
  reached except through the proxy. **This is why the bind policy below is part of this ADR and
  not a separate cleanup** — turning on header auth while the port is still open is strictly worse
  than a login form.
- **Bind policy, binding:** the gateway is the only process that binds a non-loopback address.
  Everything else binds `127.0.0.1` or nothing. The two current violations are Backstage's backend
  on `*:7107` and the k3d API forward on `*:53145`.

## Sources

- Kanboard defaults: https://github.com/kanboard/kanboard/blob/main/config.default.php
- GEP-1494, HTTP Auth in Gateway API: https://gateway-api.sigs.k8s.io/geps/gep-1494/
- Gateway API conformant implementations: https://gateway-api.sigs.k8s.io/implementations/
- Repository figures read from the GitHub API on 2026-08-24.
- Bind measurement: `lsof -nP -iTCP -sTCP:LISTEN`, output quoted above.
