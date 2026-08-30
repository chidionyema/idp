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

Every vault entry an `ExternalSecret` reads, its birth path, and its verdict.
`bin/idp-root-trust` judges this table: a MEETS row must name a bootstrapper that exists on
disk; a MISS or PARTIAL row must name a crew ticket; an entry read by an ExternalSecret and
absent here is red. Audit of 2026-08-28 (crew#66, session a0d64ea4): re-graded by `bin/idp-root-trust` on every run; the count line is the audit.

| Vault entry | Consumer | Provider | Birth path | Verdict | Bootstrapper / ticket |
|---|---|---|---|---|---|
| `tailscale-operator` | platform/tailscale/external-secret.yaml, platform/hermes-agent/tailscale.yaml | Tailscale | driver over the Trust credentials page; no create-API (`oauth_keys` scope is GET/DELETE only, docs/reference/trust-credentials 2026-08-28) | MEETS | `bin/idp-bootstrap-tailscale` |
| `github-app` | platform/alerts-github/github-app.yaml, platform/image-automation/flux-writer.yaml | GitHub App | manifest flow, one Create tap; `convert` writes the vault in-process (or via CI when no session is live); `installation` and `refresh` run from oke-check | MEETS | `bin/idp-github-app` |
| `oke-autoscaler` | platform/oci/autoscaler/external-secret.yaml | OCI | `oci ce node-pool list` → vault in-process | MEETS | `bin/idp-autoscaler-seed` |
| `k8sgpt` | platform/healing/external-secret.yaml | estate router | `POST /key/generate` → vault in-process | MEETS | `bin/idp-router-key` |
| `litellm-sso-client-id`, `litellm-sso-client-secret`, `litellm-sso-admin-id` | platform/llm/external-secret.yaml | OCI Identity Domains | `oci_identity_domains_app.router_console` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `langfuse-sso-client-id`, `langfuse-sso-client-secret` | platform/observability/langfuse.yaml | OCI Identity Domains | `oci_identity_domains_app.langfuse` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `oauth2-proxy-client-id`, `oauth2-proxy-client-secret` | platform/identity/external-secret.yaml | OCI Identity Domains | `oci_identity_domains_app.front_door` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `langfuse-init-public-key`, `langfuse-init-secret-key`, `langfuse-init-user-password`, `langfuse-init-user-email`, `clickhouse-admin-password` | platform/observability/langfuse.yaml, platform/llm/external-secret.yaml | estate (Terraform random) | `random_password` + `oci_vault_secret` (platform/oci/langfuse.tf) | MEETS | `bin/idp-identity-apply` |
| `hermes-agent-a2a` | platform/hermes-agent/gateway.yaml | estate (in-cluster) | ESO `Password` generator | MEETS | ESO generator |
| `temporal-db` | platform/temporal/external-secret.yaml | estate Postgres | `openssl rand` in-process → vault, kept when well-formed | MEETS | `bin/idp-estate-seed` |
| `sunshine-auth` | platform/backstage/overlays/oke/sunshine-egress.yaml | estate (CI runner) | `/dev/urandom` in-process → vault, kept when complete; the Mac adopts it over the tailnet (`--adopt` via `mac-run`, crew#562 path 1) | MEETS | `bin/idp-bootstrap-sunshine` |
| `hermes-mac-run` | platform/hermes-agent/mac-run-key.yaml | estate (CI runner) | `ssh-keygen -t ed25519` in-process → vault, kept when complete; the Mac adopts the public half over the tailnet (`bin/idp-mac-adopt-otto`, crew#561) | MEETS | `bin/idp-bootstrap-macrun` |
| `guacamole` (`postgres-password`) | platform/guacamole/external-secret.yaml | estate Postgres | `openssl rand` in-process → vault; Guacamole itself holds no password (front door only, `guacadmin` deleted by the seed; the Mac login is typed by the founder at connect time and never stored, crew#562 path 2) | MEETS | `bin/idp-estate-seed` |
| `hindsight` (`postgres-password`) | platform/hindsight/external-secret.yaml | estate Postgres | `openssl rand` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `hindsight` (`HINDSIGHT_API_LLM_API_KEY`) | platform/hindsight/external-secret.yaml | estate router | `POST /key/generate` via `bin/idp-router-key --entry hindsight` | MEETS | `bin/idp-estate-seed` |
| `mcp-gateway` (`MCP_GATEWAY_KEY`) | platform/mcp/external-secret.yaml | estate | `openssl rand` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `mcp-gateway` (`GITHUB_MCP_TOKEN`) | platform/mcp/external-secret.yaml | GitHub | App installation token, lane application-engineer, re-minted hourly (platform/github-app/token-consumers.json) | MEETS | `bin/idp-github-app` |
| `oauth2-proxy-cookie-secret` | platform/identity/external-secret.yaml | estate | raw urlsafe secret in-process → vault | MEETS | `bin/idp-estate-seed` |
| `prospector-store-api-env` (`Jwt__SigningKeyPem`, `Store__*`) | platform/prospector/store-api-external-secret.yaml | estate | RSA PKCS#8 key pair + `openssl rand` in-process → vault (`--merge`) | MEETS | `bin/idp-estate-seed` |
| `flux-writer` | platform/image-automation/flux-writer.yaml | GitHub App | rendered from `github-app` (Flux `provider: github`); the deploy key is retired | MEETS | `bin/idp-github-app` |
| `litellm-upstream` (`LITELLM_MASTER_KEY`) | platform/llm/external-secret.yaml | estate router | `sk-` + `openssl rand` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `litellm-upstream` (vendor keys) | platform/llm/external-secret.yaml | Minimax, DeepSeek, OpenRouter, Google, Groq | one `SEED_<VENDOR>_API_KEY` repository secret per vendor, set once (R52), verified against the vendor API in the apply run, `--merge` → vault (platform/vendors/consoles.yaml) | MEETS | `bin/idp-bootstrap-vendors` |
| `prospector-engine-env` (vendor keys) | platform/prospector/engine-external-secret.yaml | Minimax, DeepSeek, Exa, OpenRouter, Anthropic | same registry, same secrets | MEETS | `bin/idp-bootstrap-vendors` |
| `prospector-engine-env` (`R2_*`) | platform/prospector/engine-external-secret.yaml | Cloudflare R2 | R2 token via `POST /user/tokens`, S3 credential derived in-process, bucket created if absent | MEETS | `bin/idp-bootstrap-cloudflare` |
| `prospector-engine-env` (`STORE_*`) | platform/prospector/engine-external-secret.yaml | estate | store URL is a constant of the cluster; `STORE_INTERNAL_API_KEY` copied from the store's own entry | MEETS | `bin/idp-estate-seed` |
| `cloudflare-api-token` | platform/prospector/cloudflare-external-secret.yaml, platform/dns/external-dns.yaml | Cloudflare | one root token minted by a driver over the dashboard, then DNS token via `POST /user/tokens`, root token deleted | MEETS | `bin/idp-bootstrap-cloudflare` |
| `hermes-agent-env` (vendor keys, Telegram) | platform/hermes-agent/gateway.yaml | Anthropic, OpenRouter, Exa, Telegram | same registry; the bot token is `SEED_TELEGRAM_HERMES_BOT_TOKEN`, made once with BotFather | MEETS | `bin/idp-bootstrap-vendors` |
| `hermes-agent-env` (`GITHUB_TOKEN`) | platform/hermes-agent/gateway.yaml | GitHub | App installation token, re-minted hourly (token-consumers.json) | MEETS | `bin/idp-github-app` |
| `hermes-agent-env` (`LITELLM_API_KEY`) | platform/hermes-agent/gateway.yaml | estate router | `POST /key/generate` via `bin/idp-router-key --entry hermes-agent-env` | MEETS | `bin/idp-estate-seed` |
| `flux-telegram` | platform/alerts-secret/flux-telegram.yaml, platform/robusta/external-secret.yaml | Telegram | `SEED_TELEGRAM_ALERTS_BOT_TOKEN`, made once with BotFather, verified with `getMe` | MEETS | `bin/idp-bootstrap-vendors` |
| `healthchecks-db-password`, `healthchecks-ping-key`, `healthchecks-secret-key`, `healthchecks-ro-key` | platform/healthchecks/external-secret.yaml | estate (Terraform random) | `random_password` + `oci_vault_secret` (platform/oci/healthchecks.tf), applied by oke-check | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `signoz-root-email`, `signoz-root-password` | platform/observability/signoz.yaml | estate (Terraform random) | `oci_vault_secret` (platform/oci/signoz.tf) | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `otlp-ingest-users` | platform/observability/httproute.yaml | estate (Terraform random) | `oci_vault_secret` (platform/oci/otlp-ingest.tf) | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `ghcr-pull` | platform/mcp/pull-secret.yaml, platform/temporal/pull-secret.yaml | GitHub | `bin/idp-flux-bootstrap:55` builds it from a `GITHUB_TOKEN` PAT read from the vault | MISS | crew#577 |
| `backstage-env` | platform/backstage/overlays/oke/backstage-external-secret.yaml | estate | `BACKEND_SECRET` + `POSTGRES_PASSWORD` in-process → vault | MEETS | `bin/idp-estate-seed` |
| `commerce-lago-credentials` | platform/commerce/data/external-secret.yaml | estate (Terraform random) | `random_password` + `oci_vault_secret` (platform/oci/commerce.tf); one password, used both as the database's own and inside the URL that dials it | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `commerce-lago-encryption` | platform/commerce/data/external-secret.yaml | estate (Terraform random) | `random_password` + `oci_vault_secret` (platform/oci/commerce.tf); the ledger's at-rest keys, generated once and never rotated in place | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `commerce-payment-provider` | platform/commerce/data/external-secret.yaml | payment provider | one root secret key from the provider's dashboard, then the webhook signing secret minted by code through the provider's API; no second console visit (R52) | MISS | crew#623 CP3 |
| root OCI credential (`estate-tofu` key pair) | every `bin/idp-cloud` call | OCI | one browser SSO, IAM and key pair via API, private half to the sops vault | MEETS | `bin/idp-oci-bootstrap` |

## Security policy

This page is the proof behind the security-policy row "Every credential is born by a
bootstrapper" (docs/reference/security-policy.md); the row's proof command is
`bin/idp-root-trust`, run by `ci.yml` and hourly by `bin/idp-verify-drill` (crew#580).
