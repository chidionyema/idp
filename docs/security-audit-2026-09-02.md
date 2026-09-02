# Deep security audit — 2026-09-02

Ordered by the founder ("deeep audit all", 2026-09-02). Four read-only lanes swept the
estate — identity and sign-in, secrets, network and admission fences, supply chain — over
`idp`, the prospector edge, and `hermes-v2`, plus live probes of the public perimeter.
Nothing was changed by the audit itself except this record and one correction to
`docs/security-end-to-end.md`, whose fence claim the audit proved false.

**Verdict in one line: the perimeter and the secrets discipline are genuinely strong; the
inside of the cluster has no walls, and three doors behind the front gate are unlocked.**

## What is proven good

- **The perimeter is one door.** One public address (193.123.184.22); only ports 80 and
  443 answer; 80 is a redirect. Every admin hostname (langfuse, signoz, auth, metabase)
  sends an anonymous visitor to Oracle sign-in. Probed live, not read from config.
- **Zero live credentials in any repo.** No committed Secret objects, no weak passwords,
  no cloud keys. Root-trust check: 42 of 44 secrets correctly machine-minted.
- **Pods are hardened.** 46 of 46 declared workloads run non-root with seccomp; no
  hostPath, no hostNetwork, no privileged anywhere; RBAC has no cluster-admin and no
  wildcards outside vendored Flux; exactly one internet-facing load balancer (R20 holds).
- **The gateway pattern is real where it is applied.** Healthchecks, Guacamole and the
  Otto webhook are textbook: gateway sign-in, identity by stamped header, no app
  password, machine paths scoped and negatively probed. oauth2-proxy has zero skip rules.

## P0 — fix before anything else

**P0-1. SigNoz stores the founder's password and ships its own login.**
`platform/oci/signoz.tf:24-25` mints `signoz-root-email` = the founder's address and a
root password into the vault; `platform/observability/signoz.yaml:37-45` feeds both to
SigNoz's own sign-in page, which still renders behind the gateway. This breaks the two
oldest identity laws at once (no app login — decision 0003; no stored human password —
decision 0007). Langfuse got the SSO treatment; SigNoz never did — there is no
`estate-signoz` app in `platform/oci/identity/main.tf`. Remedy: give SigNoz the same
gateway-header/OIDC door Langfuse got, then delete both vault entries.

**P0-2. The LLM router's admin console is on the internet with no gateway sign-in.**
`llm.<zone>` deliberately skips the gateway gate because "the callers are programs"
(`platform/llm/httproute.yaml:1`) — but the same hostname serves `/ui`, a human admin
console whose only lock is sign-in code inside the app
(`platform/oci/identity/main.tf:186-188`). The front-door test waves the route through on
its machine-key annotation alone and never checks which paths it exposes
(`tests/test_front_door_every_route_is_behind_the_one_login.py:159-167`). Remedy: split
the route — machine paths keep the key annotation, `/ui` gets ForwardAuth — and make the
test require path scoping on every machine-annotated route.

**P0-3. The portal runs with sign-in disabled and the guard that licensed it is blind.**
`backstage/app-config.container.yaml:41` sets guest access
(`dangerouslyAllowOutsideDevelopment: true`), justified by a comment claiming no route
publishes the portal. That claim is false: `platform/backstage/overlays/oke/httproute.yaml:23`
publishes `catalogue.<zone>`. The test meant to catch this looks only in `platform/edge`
(`tests/test_incident_backstage_image_critical_cve.py:65`), so it is green because it
cannot see the file. Today the gateway's ForwardAuth is the only lock — and P0-4 below
means any pod in the cluster can walk past it to the portal's port directly. Remedy: turn
the flag off and give Backstage a real sign-in from the gateway header; fix the test to
glob every route in `platform/`.

**P0-4. The cluster has no interior walls, and the debt grows behind a green check.**
Not one NetworkPolicy or LimitRange exists in `platform/` — 0 of 33 namespaces are
fenced. The estate's own gate (`bin/ns-fence-gate`) reports **127 defects across 32
namespaces**, but the CI row can only warn (`bin/idp-ci:537-539`); the tracking comment
recorded the debt as 76 on 2026-08-27 and no run since could report that it grew 67%.
Any compromised pod can reach every service, every database and every other namespace.
Remedy: land the fences namespace by namespace, and make the CI row a ratchet — the
count may fall, never rise. (The end-to-end doc claimed this fence existed; corrected in
this commit.)

## P1 — real weaknesses, ranked next

**Identity and routing**
1. **`metabase.<zone>` is a listener with no route.** DNS is minted from routes only, so
   the name never resolves and — worse — the certificate order covering **all 13
   hostnames** cannot complete its challenge for that name. This is the exact mechanism
   of the 2026-08-31 Otto certificate outage, re-armed (`edge.yaml:197`,
   `platform/dns/external-dns.yaml:75-76`). Decision 0016's build must add the route.
2. **A password for the founder sits in the vault for Langfuse too**
   (`platform/oci/langfuse.tf:20-21`). Password sign-in is disabled in the app, which is
   the mitigation — but the credential exists, and decision 0007 forbids it outright.
   Delete it once the machine-seed path is confirmed.
3. **Langfuse's interactive sign-in machinery (`/api/auth/*`) is reachable with no
   gateway gate** (`platform/observability/httproute.yaml:97`) — a sanctioned widening,
   but a browser-reachable auth surface outside the gateway.
4. **The MCP route is a catch-all**: no path match at all, so anything agentgateway
   serves beyond its two key-locked paths is exposed bare
   (`platform/mcp/httproute.yaml:17-18` vs `platform/mcp/agentgateway.yaml:17,39`).
5. **The remote-desktop relay accepts unauthenticated callers inside the cluster**:
   `credentials: dangerously-allow-unauthenticated` on the `/sunshine` proxy that injects
   a privileged token toward the founder's Mac (`backstage/app-config.container.yaml:77-80`).
6. **Any labelled namespace can claim any hostname.** Listener attachment is by namespace
   label, not hostname ownership (`edge.yaml:138-143`) — the unauthenticated `llm` and
   `mcp` namespaces could shadow `catalogue.<zone>` paths.
7. **One TLS private key covers all 13 hostnames and lives in the storefront's
   namespace** (`edge.yaml:71`): any prospector workload with secret-read holds the key
   for every estate admin surface.
8. **The front door trusts any identity the domain mints, unverified**:
   `email_domains = ["*"]` plus `insecure-oidc-allow-unverified-email: true`
   (`platform/identity/external-secret.yaml:27`, `oauth2-proxy.yaml:117`); the real
   allow-list is the IDCS grant table, which no test asserts.
9. **`api.mumchimp.com` is never graded by the front-door law** — the test globs
   `platform/` only, so prospector routes are structurally out of scope.

**Fences and admission**
10. **The fence gate cannot tell a real fence from a fake one**: Flux's `allow-egress`
    (destination: everywhere, every port) passes both checks — fix `denies_everything()`
    before the 32 fences land, or they can all be nominal.
11. **The pod-hardening policy bundle (no `:latest`, probes, PSS) lives in the private
    prospector repo**; `platform/edge/` carries 12 exception files waiving policies this
    repo cannot even see.
12. **The env-var-secret policy reports instead of refusing** (Audit mode,
    `platform/edge/kyverno-secrets-policy.yaml:30`) and its flip condition (zero
    violations) is unreachable while the Dagster exception is permanent.
13. **One service account can read every secret in the cluster**: `cluster-state-reader`
    holds `list` on Secrets cluster-wide; the metadata-only restraint lives in the
    client, not the grant (`platform/state/cluster-state.yaml:31-33`). Needs a ruling:
    drop the check or accept and document the capability.
14. **Quota with no LimitRange in `staging` and `flux-system`** — the documented
    admission-refusal outage mode, live in the namespace most likely to get ad-hoc pods.

**Supply chain**
15. **Every idp PR executes an unpinned script from another repo's default branch with
    the workflow's full token** (`.github/workflows/fast-gate.yml:18-27`, no
    `permissions:` block). Pin to a commit hash and add `permissions: contents: read`.
16. **The infra-crew agent runs a floating `:main` image while holding a GitHub token
    that writes to crew and idp** (`platform/infra-crew/cronjob.yaml:130`); the
    `:latest`-only regex (`policy/conscience.rego:33`) does not catch it.
17. **`curl | sh` installs in CI** (`ci.yml:59,200` temporal; `portability-drill.yml:121`
    k3s) and hermes-v2 actions pinned `@main` with no permissions block.

**Secrets**
18. **The payment-provider vault entry can never sync** (ExternalSecret orphan,
    root-trust MISS — already ticketed, crew#623 CP3) and **the registry pull secret is a
    hand-minted personal token** outside the vault path (`bin/idp-flux-bootstrap:55`).

## P2 — logged, justified or dark

Unsalted SHA-256 key hashes with no per-route revocation (`agentgateway.yaml:21`);
Traefik `allowCrossNamespace: true`; the drill user's stored password (deliberate — the
drill walks the human flow); Keycloak buyer realm with open registration (dark, no route,
graded when its route PR comes); the OTLP basic-auth edge credential (machine, scoped,
negatively probed — fine); `require-registry-host` in Audit with no flip deadline; 10
namespaces missing a pod-security enforce label, including `edge` and `staging`; 6
workloads mounting an API token they never use; 3 missing read-only root filesystems;
`docs/policy/auth-is-infrastructure.md` is cited by the estate rules but exists nowhere —
a dangling citation to write or retarget; Telegram has two bot roots (HERMES + ALERTS) —
one-root rule needs a decision.

## What this audit did not cover

- **Git history.** No sweep for secrets in past commits; `gitleaks` over full history is
  the named follow-up lane.
- **Chart-rendered pods.** Helm-templated workloads are invisible to a manifest scan.
- **The prospector policy bundle and IDCS grant table** — both live outside these repos;
  their contents are asserted, not verified, here.

## The order of work

1. P0-4 fence ratchet + first fenced namespaces (biggest blast-radius cut).
2. P0-1 SigNoz SSO, P0-3 Backstage sign-in + blind-test fix, P0-2 LLM route split — the
   three unlocked doors behind the gate.
3. P1 items 15–16 (supply chain: pin the scripts, pin the image) — cheap, high leverage.
4. The rest of P1 in numbered order; P2 as touched.
