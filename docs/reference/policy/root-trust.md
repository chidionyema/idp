# Root trust

**Ruling:** founder, 2026-08-28, crew#66 ([5453747447](https://github.com/chidionyema/crew/issues/66#issuecomment-5453747447)),
verbatim: "The founder will never copy-paste a secret or click through web UI settings" /
"thats the standard i expect, founndr is also ceo / ceo does not need frction" / "but this
standard has to be platforn wide / not just tailscale" / "case closed". Standing ruling
R45-root-trust in claude-guards `rulings.json`.

**The standard.** Every credential the estate holds is born through a bootstrapper,
`bin/idp-bootstrap-<provider>` (or the provider's existing door: `bin/idp-github-app`,
`bin/idp-oci-bootstrap`, `bin/idp-router-key`, `bin/idp-autoscaler-seed`, a Terraform
`oci_vault_secret`, or an ESO generator in-cluster). A bootstrapper:

1. takes at most one human act, an SSO consent in a browser the bootstrapper opened;
2. mints every derived credential through the provider's API;
3. writes the vault in the same process (`bin/idp-vault-put`, values never on argv, never
   printed, never in a repository secret);
4. proves the credential works before storing it (a token exchange, a read with it);
5. exits. Re-running is safe; `--rotate` mints anew.

**R52 (founder 2026-08-29): one root per provider, set once, then code.** A provider has
exactly one root credential. The founder makes it once on his own machine and sets it as a named
repository secret (`gh secret set SEED_<PROVIDER>_...`); that is his whole part, ever. The
bootstrapper reads that secret in the apply run, mints every second credential through the
provider's API where one exists, proves it, writes the vault and rotates. Asking him for a console
click, a form field, a copied value, or a second credential on a provider that has its root is
the incident. Driving a web console with a browser (Playwright over the founder's session) is a
wrong root too: it needs his login every time the session lapses, and it is deleted wherever it is
found (crew#66 comment 5461144560). Pasting a value into a prompt stays a **MISS**; the no-toil
gate (`policy/no-manual-steps.rego`) refuses the sentence.

**The provider floor.** A provider with no create-key API (every vendor in
`platform/vendors/consoles.yaml`) has the key itself as its root: made once, set once, proved and
vaulted by `bin/idp-bootstrap-vendors`, kept while it verifies. A provider with a key API
(Tailscale, Cloudflare) has a root that only mints: `bin/idp-bootstrap-tailscale`,
`bin/idp-bootstrap-cloudflare`.

## Register

Every vault entry an `ExternalSecret` reads, **who is asked for it**, its birth path, and its
verdict.

**The Owner column** answers a different question from the verdict, and the estate needed both
before it could say whether onboarding was finished (founder 2026-09-05: "need to understand what
is customer and what is estate/founder credentials also", "founder as discussed is customer 0").
The verdict says whether code can mint the value. The owner says whose account it comes out of,
and there are exactly three answers:

- **Supplier** — ours, needed to build and ship the platform itself. A customer never sees one;
  a missing supplier credential is our outage, never their setup step.
- **Operator** — the installation's: cloud, network, identity, databases, internal keys. Paid for
  once by a single sign-on consent at install, after which every one of them is minted, proved and
  rotated by code.
- **Customer** — their own account with their own vendor, born in a browser they are already
  signed in to. No engineering removes the human from these; the only question is how much work we
  make them do once the value is in their clipboard.

One person can wear two of these hats — the founder is customer zero and is also part of the
estate's own security — so the register records the hat, not the person. **The count of Customer
rows that are not yet MEETS is the onboarding number**, printed by `bin/idp-root-trust` on every
run, and it is the one that decides whether a business user can finish setup without a terminal.
`bin/idp-root-trust` judges this table: a MEETS row must name a bootstrapper that exists on
disk; a MISS or PARTIAL row must name a crew ticket; an entry read by an ExternalSecret and
absent here is red. Audit of 2026-08-28 (crew#66, session a0d64ea4): re-graded by `bin/idp-root-trust` on every run; the count line is the audit.

| Vault entry | Consumer | Provider | Owner | Birth path | Verdict | Bootstrapper / ticket |
|---|---|---|---|---|---|---|
| `tailscale-operator` | platform/tailscale/external-secret.yaml, platform/hermes-agent/tailscale.yaml | Tailscale | Operator | driver over the Trust credentials page; no create-API (`oauth_keys` scope is GET/DELETE only, docs/reference/trust-credentials 2026-08-28) | MEETS | `bin/idp-bootstrap-tailscale` |
| `github-app` | platform/alerts-github/github-app.yaml, platform/image-automation/flux-writer.yaml | GitHub App | Operator | manifest flow, one Create tap; `convert` writes the vault in-process (or via CI when no session is live); `installation` and `refresh` run from oke-check | MEETS | `bin/idp-github-app` |
| `oke-autoscaler` | platform/oci/autoscaler/external-secret.yaml | OCI | Operator | `oci ce node-pool list` → vault in-process | MEETS | `bin/idp-autoscaler-seed` |
| `k8sgpt` | platform/healing/external-secret.yaml | estate router | Operator | `POST /key/generate` → vault in-process | MEETS | `bin/idp-router-key` |
| `science` | platform/research-engine/secrets.yaml | estate router | Operator | `POST /key/generate` scoped to the neutral lanes → vault in-process, scoped to the lanes named on the mint (run 33867639366) | MEETS | `bin/idp-router-key` |
| `estate-db` (`superuser-password`, `dagster-password`, `langfuse-password`, `research-password`) | platform/estate-db/cluster/secrets.yaml | estate Postgres (CloudNativePG) | Operator | `openssl rand` in-process → vault, one field per role; the other seven roles read the consumer's own entry and mint nothing | MEETS | `bin/idp-estate-seed` |
| `flux-webhook-token` | platform/flux-webhook/externalsecret.yaml | GitHub → Flux notification-controller | Operator | Terraform `random_password` → OCI Vault (platform/oci/flux-webhook.tf); GitHub verifies the same value as an HMAC signature, and nobody types or reads it | MEETS | Terraform |
| `signoz-prover` | .github/workflows/verdict-signoz.yml (bin/idp-prove signoz, [step nine of the verification plane](https://github.com/chidionyema/crew/issues/631)) | SigNoz | Operator | root login from the vault → `POST /api/v1/service_accounts/{id}/keys` over a port-forward → vault in-process | MEETS | `bin/idp-signoz-key` (bin/idp-estate-seed step 4) |
| `litellm-sso-client-id`, `litellm-sso-client-secret`, `litellm-sso-admin-id` | platform/llm/external-secret.yaml | OCI Identity Domains | Operator | `oci_identity_domains_app.router_console` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `langfuse-sso-client-id`, `langfuse-sso-client-secret` | platform/observability/langfuse.yaml | OCI Identity Domains | Operator | `oci_identity_domains_app.langfuse` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `oauth2-proxy-client-id`, `oauth2-proxy-client-secret` | platform/identity/external-secret.yaml | OCI Identity Domains | Operator | `oci_identity_domains_app.front_door` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `langfuse-init-public-key`, `langfuse-init-secret-key`, `langfuse-init-user-password`, `langfuse-init-user-email`, `clickhouse-admin-password` | platform/observability/langfuse.yaml, platform/llm/external-secret.yaml | estate (Terraform random) | Operator | `random_password` + `oci_vault_secret` (platform/oci/langfuse.tf) | MEETS | `bin/idp-identity-apply` |
| `hermes-agent-a2a` | platform/hermes-agent/gateway.yaml | estate (in-cluster) | Operator | ESO `Password` generator | MEETS | ESO generator |
| `temporal-db` | platform/temporal/external-secret.yaml | estate Postgres | Operator | `openssl rand` in-process → vault, kept when well-formed | MEETS | `bin/idp-estate-seed` |
| `otto-gateway-db` (`password`) | platform/otto-gateway/external-secret.yaml | estate Postgres | Operator | `openssl rand` in-process → vault, kept when well-formed | MEETS | `bin/idp-estate-seed` |
| `sunshine-auth` | platform/backstage/overlays/oke/sunshine-egress.yaml | estate (CI runner) | Operator | `/dev/urandom` in-process → vault, kept when complete; the Mac adopts it over the tailnet (`--adopt` via `mac-run`, crew#562 path 1) | MEETS | `bin/idp-bootstrap-sunshine` |
| `hermes-mac-run` | platform/hermes-agent/mac-run-key.yaml | estate (CI runner) | Operator | `ssh-keygen -t ed25519` in-process → vault, kept when complete; the Mac adopts the public half over the tailnet (`bin/idp-mac-adopt-otto`, crew#561) | MEETS | `bin/idp-bootstrap-macrun` |
| `guacamole` (`postgres-password`) | platform/guacamole/external-secret.yaml | estate Postgres | Operator | `openssl rand` in-process → vault; Guacamole itself holds no password (front door only, `guacadmin` deleted by the seed; the Mac login is typed by the founder at connect time and never stored, crew#562 path 2) | MEETS | `bin/idp-estate-seed` |
| `hindsight` (`postgres-password`) | platform/hindsight/external-secret.yaml | estate Postgres | Operator | `openssl rand` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `hindsight` (`HINDSIGHT_API_LLM_API_KEY`) | platform/hindsight/external-secret.yaml | estate router | Operator | `POST /key/generate` via `bin/idp-router-key --entry hindsight` | MEETS | `bin/idp-estate-seed` |
| `mcp-gateway` (`MCP_GATEWAY_KEY`) | platform/mcp/external-secret.yaml | estate | Operator | `openssl rand` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `mcp-gateway` (`GITHUB_MCP_TOKEN`) | platform/mcp/external-secret.yaml | GitHub | Operator | App installation token, lane application-engineer, minted in-cluster every 45m (GithubAccessToken generator, platform/mcp/external-secret.yaml) | MEETS | `bin/idp-github-app` |
| `oauth2-proxy-cookie-secret` | platform/identity/external-secret.yaml | estate | Operator | raw urlsafe secret in-process → vault | MEETS | `bin/idp-estate-seed` |
| `prospector-store-api-env` (`Jwt__SigningKeyPem`, `Store__*`) | platform/prospector/store-api-external-secret.yaml | estate | Operator | RSA PKCS#8 key pair + `openssl rand` in-process → vault (`--merge`) | MEETS | `bin/idp-estate-seed` |
| `flux-writer` | platform/image-automation/flux-writer.yaml | GitHub App | Operator | rendered from `github-app` (Flux `provider: github`); the deploy key is retired | MEETS | `bin/idp-github-app` |
| `litellm-upstream` (`LITELLM_MASTER_KEY`) | platform/llm/external-secret.yaml | estate router | Operator | `sk-` + `openssl rand` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `litellm-upstream` (vendor keys) | platform/llm/external-secret.yaml | Minimax, DeepSeek, OpenRouter, Google, Groq | Customer | one `SEED_<VENDOR>_API_KEY` repository secret per vendor, set once (R52), verified against the vendor API in the apply run, `--merge` → vault (platform/vendors/consoles.yaml) | MEETS | `bin/idp-bootstrap-vendors` |
| `notify-apprise-founder-telegram` | platform/notify/external-secret.yaml | Telegram (founder's bot) | Customer | a pair of repository secrets set once (`SEED_TELEGRAM_ALERTS_BOT_TOKEN` + `SEED_TELEGRAM_ALERTS_CHAT_ID`, the bot made once at BotFather under the one-root-credential rule), graded together by `getChat`, `--merge` → vault in the apply run; the vault-fed secret composes the `tgram://` URL | MEETS | `bin/idp-bootstrap-vendors` |
| `prospector-engine-env` (vendor keys) | platform/prospector/engine-external-secret.yaml | Minimax, DeepSeek, Exa, OpenRouter, Anthropic | Customer | same registry, same secrets | MEETS | `bin/idp-bootstrap-vendors` |
| `prospector-engine-env` (`R2_*`) | platform/prospector/engine-external-secret.yaml | Cloudflare R2 | Operator | R2 token via `POST /user/tokens`, S3 credential derived in-process, bucket created if absent | MEETS | `bin/idp-bootstrap-cloudflare` |
| `prospector-engine-env` (`STORE_*`) | platform/prospector/engine-external-secret.yaml | estate | Operator | store URL is a constant of the cluster; `STORE_INTERNAL_API_KEY` copied from the store's own entry | MEETS | `bin/idp-estate-seed` |
| `cloudflare-api-token` | platform/dns/cloudflare-external-secret.yaml, platform/dns/external-dns.yaml | Cloudflare | Operator | one root token minted by a driver over the dashboard, then DNS token via `POST /user/tokens`, root token deleted | MEETS | `bin/idp-bootstrap-cloudflare` |
| `hermes-agent-env` (vendor keys, Telegram) | platform/hermes-agent/gateway.yaml | Anthropic, OpenRouter, Exa, Cursor, Telegram | Customer | same registry; the bot token is `SEED_TELEGRAM_HERMES_BOT_TOKEN`, made once with BotFather; Cursor is `SEED_CURSOR_API_KEY` | MEETS | `bin/idp-bootstrap-vendors` |
| `hermes-agent-env` (`GITHUB_TOKEN`) | platform/hermes-agent/gateway.yaml | GitHub | Operator | App installation token, minted in-cluster every 45m (GithubAccessToken generator in the row) | MEETS | `bin/idp-github-app` |
| `hermes-agent-env` (`LITELLM_API_KEY`) | platform/hermes-agent/gateway.yaml | estate router | Operator | `POST /key/generate` via `bin/idp-router-key --entry hermes-agent-env` | MEETS | `bin/idp-estate-seed` |
| `otto-golden` (`LITELLM_API_KEY`) | platform/otto-golden/router-key.yaml | estate router | Operator | `POST /key/generate` via `bin/idp-router-key --entry otto-golden` | MEETS | `bin/idp-estate-seed` |
| `agent-workforce` (`LITELLM_API_KEY`) | platform/agent-workforce/external-secret.yaml | estate router | Operator | `POST /key/generate` via `bin/idp-router-key --entry agent-workforce`, scoped to the kimi, minimax and deepseek lanes with its own daily budget; until 2026-09-04 the crew read the router's MASTER key instead (idp#1491) | MEETS | `bin/idp-estate-seed` |
| `flux-telegram` | platform/alerts-secret/flux-telegram.yaml, platform/robusta/external-secret.yaml | Telegram | Customer | `SEED_TELEGRAM_ALERTS_BOT_TOKEN`, made once with BotFather, verified with `getMe` | MEETS | `bin/idp-bootstrap-vendors` |
| `healthchecks-db-password`, `healthchecks-ping-key`, `healthchecks-secret-key`, `healthchecks-ro-key` | platform/healthchecks/external-secret.yaml | estate (Terraform random) | Operator | `random_password` + `oci_vault_secret` (platform/oci/healthchecks.tf), applied by oke-check | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `superset-db-password` | platform/observability/superset-external-secret.yaml | estate (Terraform random) | Operator | `random_password` + `oci_vault_secret` (platform/oci/superset.tf), applied by oke-check | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `superset-secret-key` | platform/observability/superset-external-secret.yaml | estate (Terraform random) | Operator | `random_password` + `oci_vault_secret` (platform/oci/superset.tf), applied by oke-check | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `signoz-root-email`, `signoz-root-password` | platform/observability/signoz.yaml | estate (Terraform random) | Operator | `oci_vault_secret` (platform/oci/signoz.tf) | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `otlp-ingest-users` | platform/observability/httproute.yaml | estate (Terraform random) | Operator | `oci_vault_secret` (platform/oci/otlp-ingest.tf) | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `ghcr-pull` | platform/mcp/pull-secret.yaml, platform/temporal/pull-secret.yaml | GitHub | Supplier | `bin/idp-flux-bootstrap:55` builds it from a `GITHUB_TOKEN` PAT read from the vault | MISS | crew#577 |
| `backstage-env` | platform/backstage/overlays/oke/backstage-external-secret.yaml | estate | Operator | `BACKEND_SECRET` + `POSTGRES_PASSWORD` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `verdict-hmac-key` | platform/verification/verdict-key-wall.yaml (the wall probe: reads as a pod and must be REFUSED, crew#631 CP2; the prover reads it in CI as `estate-provers`, never through an ExternalSecret) | OCI | Operator | `random_password` → vault by Terraform, `platform/oci/identity/main.tf` | MEETS | `bin/idp-oci-bootstrap` (apply) |
| `commerce-lago-credentials` | platform/commerce/data/external-secret.yaml | estate (Terraform random) | Operator | `random_password` + `oci_vault_secret` (platform/oci/commerce.tf); one password, used both as the database's own and inside the URL that dials it | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `commerce-lago-encryption` | platform/commerce/data/external-secret.yaml | estate (Terraform random) | Operator | `random_password` + `oci_vault_secret` (platform/oci/commerce.tf); the ledger's at-rest keys, generated once and never rotated in place | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `commerce-payment-provider` | platform/commerce/data/external-secret.yaml | payment provider | Customer | one root secret key from the provider's dashboard, then the webhook signing secret minted by code through the provider's API; no second console visit (R52) | MISS | crew#623 CP3 |
| `bitwarden-machine` | platform/human-vault/access-token.yaml | Bitwarden (machine account) | Operator | the access token is born once in the operator's browser (Bitwarden web vault, decision 0017); the vault write is code — `bin/idp-cloud secret put bitwarden-machine` reading a file only the operator's user can read, deleted in the same run, never a console form (2026-09-02: the console's twin-vault dropdown sent a paste to a vault scheduled for deletion); the runbook is docs/how-to/bitwarden-human-vault.md | MISS | [the bridge ticket](https://github.com/chidionyema/crew/issues/809) |
| `rotation-canary` | platform/state/rotation-canary.yaml | vault (drill fixture) | Operator | a fresh random value minted by code on every drill run: `bin/idp-vault-put rotation-canary` in the oke-check rotation-drill job; never touched by hand (crew#722) | MEETS | `bin/idp-vault-put` |
| `otto-staging-telegram` | platform/otto-golden/telegram-secret.yaml, platform/otto-golden-secret/webhook-substitution.yaml | Telegram (BotFather) | Customer | This row claimed the human road and the estate does not run it that way. The manifest's own header records the reversal on 2026-09-02, and the live cluster agrees: the ExternalSecret names `estate-vault`, and on 2026-09-05 there were 89 ExternalSecrets on `estate-vault`, 6 on `ghcr-pull` and ZERO on `human-vault`. `token` is born on the founder's phone in BotFather and reaches the vault through `bin/idp-vault-put --merge otto-staging-telegram token=...`, a terminal command reading an env file — which is what LAW 54 refuses for a founder-facing step. `webhook_secret` is minted in-process and never printed. | MISS | `bin/idp-vault-put`. Ticketed as [the API key lifecycle ticket](https://github.com/chidionyema/crew/issues/832): the fix is not a bootstrapper for this one entry, it is the one-shot ingest road. |
| root OCI credential (`estate-tofu` key pair) | every `bin/idp-cloud` call | OCI | Operator | one browser SSO, IAM and key pair via API, private half to the sops vault | MEETS | `bin/idp-oci-bootstrap` |
| `bridge-instance-ocid` | platform/rbac-identity/external-secret.yaml | OCI | Operator | not a credential: the OCID of the break-glass bridge instance, which terraform is the only thing that knows and every rebuild changes. `platform/oci/bridge.tf` writes it into the vault at apply time, so no identifier is ever hand-carried from an apply into a manifest (crew#841). | MEETS | Terraform (`platform/oci/bridge.tf`) |
| `cyrus-linear` | platform/cyrus/external-secret.yaml | Linear | Customer | The earlier claim on this row was wrong: Linear does publish a create-API for the webhook half (`webhookCreate`), so only ONE of the two is human-born. The personal API key is, and can be born nowhere else — Settings, Account, Security & access, New API key, scoped rather than full access. It rides the human road: born in the founder's browser, saved into Bitwarden, pulled by the cluster through the `human-vault` store, never typed into a terminal or an estate env file. `webhook_secret` is then minted by code through `webhookCreate` using that key and written to the machine vault, so there is no second console visit (R52). MISS until the key is in Bitwarden; the manifest is already pointing at it. | MISS | [the Cyrus board ticket](https://github.com/chidionyema/crew/issues/834) |
| `cyrus-linear-api-token` | platform/cyrus/external-secret.yaml | Linear | Customer | the personal API key, born in a browser at Linear Settings, Account, Security & access, New API key: Linear publishes no create-API for this half, so a human holds it and always will. It rides the human road (`human-vault`) and is the estate's first entry to do so. What is missing is not the key but the door: today the only way to hand it over is to type the exact secret name into Bitwarden's own web interface and pick the right project, which failed twice on 2026-09-05 (external-secrets 19:53:40Z, `no secret found for project id 18e57b2f... and name cyrus-linear-api-token`). Decision 0020 road one, one-shot ingest through the portal, is the fix. | MISS | [the API key lifecycle ticket](https://github.com/chidionyema/crew/issues/832) |
| `holmes` | platform/robusta/external-secret.yaml | estate router | Operator | a LiteLLM virtual key, never a vendor key: `bin/idp-router-key holmes minimax` mints it and writes the vault in-process, driven by `.github/workflows/vault-seed.yml -f entry=holmes`. | MEETS | `bin/idp-router-key` |

## Security policy

This page is the proof behind the security-policy row "Every credential is born by a
bootstrapper" (docs/reference/security-policy.md); the row's proof command is
`bin/idp-root-trust`, run by `ci.yml` and hourly by `bin/idp-verify-drill` (crew#580).
