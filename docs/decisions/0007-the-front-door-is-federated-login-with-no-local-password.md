# 0007. The front door is federated login; the estate holds no password for a person

- Status: DECIDED 2026-08-26 on the founder's ruling. Supersedes the implementation half of ADR 0003
  (Authelia with a file user database). The standard half of ADR 0003 stands: identity is OIDC and
  the gateway enforces it.
- Date: 2026-08-26
- Deciders: founder
- Affects: every human-facing hostname on the estate zone, starting with `catalogue.<zone>`.

## The incident, 2026-08-26 01:00Z

The first front door went live with ADR 0003: Authelia, one user in a file, an argon2 hash in the
vault, the plaintext in the sops vault. To let the founder in, a session sent him the username and
the password over Telegram. His ruling, verbatim:

> "i was sent a user nane and passwordfor backstage, thats not in line with our security principles"
> "enterprise approach" / "not consistent with how we do things" / "seanless and secure"

Everything that followed (the message deleted, the hash rotated, the guard on the push script that
now refuses credential-shaped text, claude-guards#64) was the fire. This ADR is the class: **a
door with its own password has a password that has to travel**, and every route it can travel is
a place it leaks. The same design also had two stores that could disagree, and they did: the first
login was a 401 because the hash and the plaintext were made from different values (idp#144).

## The decision

**The estate never holds a password for a person. Login federates to an identity provider the
founder already uses, with MFA enforced there. The implementation is oauth2-proxy in front of the
gateway's ForwardAuth; the provider is the estate's own OCI identity domain (`platform/oci/identity`, since 2026-08-26, crew#269/#288). GitHub was the provider from 2026-08-25 to 2026-08-26; a Cloudflare Access broker (`platform/access`) was planned and deleted unapplied.**

- No user database, no hash, no plaintext, no reset flow, no sops file for a login.
- The only values the estate holds are the OIDC client id and client secret of one confidential
  application in the identity domain, and a random cookie secret. Terraform creates the application
  and writes both into the estate vault (`platform/oci/identity/main.tf`); ESO mounts them
  (`platform/identity/external-secret.yaml`) as a Kubernetes Secret. No person and no session sees
  them, and nothing carries them through chat, a log, or a push notification.
- Who may enter is the domain's grant table: `founder_emails` in `platform/oci/identity`, one
  `oci_identity_domains_grant` per address, reviewed in a pull request like any other change.
  `ESTATE_LOGIN_GITHUB_USER` is retired (crew#288 CP3).
- The gateway contract is unchanged from ADR 0003: an HTTPRoute outside `identity` carries a Traefik
  ForwardAuth Middleware, now `login-forward-auth`, address `oauth2-proxy.identity.svc/`. The
  application receives `X-Auth-Request-User` and `X-Auth-Request-Email`.

## Why not the alternatives

- **Keep Authelia, send the password another way.** The password still exists and still has to
  reach a person. The class survives the route.
- **Authelia as OIDC provider with GitHub upstream.** Authelia does not federate to an upstream
  identity provider; it is one. Two hops for the same result as one.
- **Keycloak / Dex in front of GitHub.** An OIDC broker earns its keep with several applications
  and several providers. There is one door and one person. Dex is the next step if a second
  application needs OIDC tokens rather than a ForwardAuth; nothing here blocks it, the ForwardAuth
  contract is the same.
- **Google or Microsoft as the provider.** The founder's GitHub account already authorises every
  push on the estate and has MFA. Adding a second identity to trust adds a second thing to secure.

## Consequences

- The chart is `oauth2-proxy` 10.7.0 from `https://oauth2-proxy.github.io/manifests` (app 7.15.3).
  Pattern: `--upstream=static://202`, ForwardAuth at `/`, `--reverse-proxy`, cookie for `.<zone>`,
  `/oauth2/` on each front-door hostname routed to oauth2-proxy through a ReferenceGrant, callback
  fixed at `https://auth.<zone>/oauth2/callback`.
- `bin/idp-verify` row `login` proves the door from outside with no credential: an unauthenticated
  request to the catalogue is a 302 to `/oauth2/start`, and that is a 302 to
  `github.com/login/oauth/authorize`. A 401, a 200 or a wrong Location is a FAIL.
- Residual: the probe cannot see whether the client id in the vault is the real one; only the
  founder's first sign-in proves that, and that sign-in is the `DONE:` receipt on crew#269.
- Residual: sessions are cookies, so they die with the pod restart (no Redis). Twelve-hour expiry;
  a restart means one more GitHub round-trip, no password.

## Sources

- oauth2-proxy docs, `docs/configuration/integrations/traefik.md` and `providers/github.md`, read
  2026-08-26 via the GitHub API.
- Chart index `https://oauth2-proxy.github.io/manifests/index.yaml`, read 2026-08-26.
- crew#269 incident comment 5418649684; claude-guards#64; idp#144.
