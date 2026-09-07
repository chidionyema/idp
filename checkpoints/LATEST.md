## RESUME HERE

**2026-09-07 ~15:20 GMT+1 — SigNoz asks for a second login; building the one-login shim.**

Founder: "why is https://signoz.mumchimp.com/login askingfor login info". The estate's OIDC front
door works (302 to Oracle IDCS with an `_oauth2_proxy_csrf` cookie); what he met underneath is
SigNoz's own email/password form. That is two identity layers, against the one-identity policy.

Proven this session, empirically:
- SigNoz keeps its session in **localStorage** (`AUTH_TOKEN`, `REFRESH_AUTH_TOKEN`, `IS_LOGGED_IN`),
  not cookies, so no proxy header can establish it. Bundle `assets/index-CqkWcg8Z.js`, helpers
  `P_`/`N_`/`Cv` over `localStorage`, key prefix `M_()` is a no-op because `<base href="/" />`.
- Unauthenticated routes redirect **client-side** (`<Redirect to={F.LOGIN}>`), so intercepting the
  `/login` path at the edge does not catch a visit that starts at `/`.
- The mint works: `GET /api/v2/sessions/context?email=&ref=` -> `data.orgs[0].id`, then
  `POST /api/v2/sessions/email_password {email,password,orgId}` -> accessToken/refreshToken,
  `expiresIn 1799`. Root credential is the existing Secret `signoz-root` in `observability`.
- SigNoz free has no SSO (enterprise feature); Langfuse solved the same hop natively (crew#503).

Decision: a small hardened front in `observability` — nginx that proxies the browser route to
`signoz:8080` and `sub_filter`s one inline script into index.html, plus a loopback-only minter
that calls the two APIs with the root credential. The script writes the three localStorage keys
before the deferred module bundle runs, so the form never renders on any path.

Work is in worktree `.../scratchpad/wt-sso` on branch `fix/signoz-one-login`. Next: write
`platform/observability/signoz-sso.yaml`, add it to the kustomization, point the browser rule of
the signoz HTTPRoute at `signoz-sso:8080`, record the decision, open the PR.

Do NOT switch branches in the main checkout: it sits on `fix/cyrus-webhook-routes` and another
session holds uncommitted work in `platform/cyrus/`.

# checkpoint 2026-09-07T13:25:12Z


Founder, 2026-09-07: "you made the ui worse with this everyday tools shit, previous home
page was clean and polished". PR #2235 (merged 11:04) put an Everyday band on the front
page. Reverting the band only; the `estate/tier: daily` annotations stay so the estate Mac
still sits first on the Tools page.

Open after this: PR #2284 (another session's home redesign) sits on top of the band and
needs rebasing. "pair my phone, estate mac not working" is unread.

Merged today: 2268 fence, 2271 vault seed, 2275 helm retry, 2276 catalogue fold, 2280 runbook.
