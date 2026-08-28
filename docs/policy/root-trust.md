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

A person typing a value into a `SEED_*` repository secret, pasting into a prompt, or
creating a key in a web console is a **MISS**, and a MISS is ticketed, never documented as
a procedure. The no-toil gate (`policy/no-manual-steps.rego`) refuses the sentence; this page
refuses the path.

**The provider floor.** Some providers cannot mint their own root (measured per row below).
Their floor is one console session, and the bootstrapper drives that session itself through
the estate's browser profile (`~/.estate/tailscale-browser`, Playwright): the founder signs
in if the session lapsed and does nothing else; the driver creates the credential, reads it
from the page, verifies it against the API and writes the vault. That is
`bin/idp-bootstrap-tailscale`; crew#579 applies the same driver to every vendor console key.

## Register

Every vault entry an `ExternalSecret` reads, its birth path, and its verdict.
`bin/idp-root-trust` judges this table: a MEETS row must name a bootstrapper that exists on
disk; a MISS or PARTIAL row must name a crew ticket; an entry read by an ExternalSecret and
absent here is red. Audit of 2026-08-28 (crew#66, session a0d64ea4): re-graded by `bin/idp-root-trust` on every run; the count line is the audit.

| Vault entry | Consumer | Provider | Birth path | Verdict | Bootstrapper / ticket |
|---|---|---|---|---|---|
| `tailscale-operator` | platform/tailscale/external-secret.yaml, platform/hermes-agent/tailscale.yaml | Tailscale | driver over the Trust credentials page; no create-API (`oauth_keys` scope is GET/DELETE only, docs/reference/trust-credentials 2026-08-28) | MEETS | `bin/idp-bootstrap-tailscale` |
| `github-app` | platform/alerts-github/github-app.yaml | GitHub App | manifest flow, one Create tap; vault written by a second CI job via `SEED_GITHUB_APP_*` | PARTIAL | `bin/idp-github-app` · crew#577 |
| `oke-autoscaler` | platform/oci/autoscaler/external-secret.yaml | OCI | `oci ce node-pool list` → vault in-process | MEETS | `bin/idp-autoscaler-seed` |
| `k8sgpt` | platform/healing/external-secret.yaml | estate router | `POST /key/generate` → vault in-process | MEETS | `bin/idp-router-key` |
| `litellm-sso-client-id`, `litellm-sso-client-secret`, `litellm-sso-admin-id` | platform/llm/external-secret.yaml | OCI Identity Domains | `oci_identity_domains_app.router_console` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `oauth2-proxy-client-id`, `oauth2-proxy-client-secret` | platform/identity/external-secret.yaml | OCI Identity Domains | `oci_identity_domains_app.front_door` + `oci_vault_secret` (platform/oci/identity/main.tf) | MEETS | `bin/idp-identity-apply` |
| `langfuse-init-public-key`, `langfuse-init-secret-key`, `langfuse-init-user-password`, `langfuse-init-user-email`, `clickhouse-admin-password` | platform/observability/langfuse.yaml, platform/llm/external-secret.yaml | estate (Terraform random) | `random_password` + `oci_vault_secret` (platform/oci/langfuse.tf) | MEETS | `bin/idp-identity-apply` |
| `hermes-agent-a2a` | platform/hermes-agent/gateway.yaml | estate (in-cluster) | ESO `Password` generator | MEETS | ESO generator |
| `temporal-db` | platform/temporal/external-secret.yaml | estate Postgres | `SEED_TEMPORAL_DB_PASSWORD` by hand → vault-seed.yml | MISS | crew#575 |
| `hindsight` (`postgres-password`) | platform/hindsight/external-secret.yaml | estate Postgres | `SEED_HINDSIGHT_DB_PASSWORD` by hand | MISS | crew#575 |
| `hindsight` (`HINDSIGHT_API_LLM_API_KEY`) | platform/hindsight/external-secret.yaml | estate router | `SEED_HINDSIGHT_LLM_API_KEY` by hand | MISS | crew#576 |
| `mcp-gateway` (`MCP_GATEWAY_KEY`) | platform/mcp/external-secret.yaml | estate | `SEED_MCP_GATEWAY_KEY` by hand | MISS | crew#575 |
| `mcp-gateway` (`GITHUB_MCP_TOKEN`) | platform/mcp/external-secret.yaml | GitHub | `SEED_GITHUB_MCP_TOKEN` PAT by hand | MISS | crew#577 |
| `oauth2-proxy-cookie-secret` | platform/identity/external-secret.yaml | estate | no CI call site | MISS | crew#575 |
| `prospector-store-api-env` | platform/prospector/store-api-external-secret.yaml | estate | no writer found | MISS | crew#575 |
| `flux-writer` | platform/image-automation/flux-writer.yaml | GitHub deploy key | ssh-keygen + `gh api` by hand → `SEED_FLUX_WRITER_*` | MISS | crew#575 |
| `litellm-upstream` (`LITELLM_MASTER_KEY`) | platform/llm/external-secret.yaml | estate router | `SEED_LITELLM_MASTER_KEY` by hand | MISS | crew#575 |
| `litellm-upstream` (vendor keys) | platform/llm/external-secret.yaml | Minimax, DeepSeek, OpenRouter, Google, Groq | `SEED_*_API_KEY` by hand → oke-check.yml | MISS | crew#579 |
| `prospector-engine-env` (vendor keys) | platform/prospector/engine-external-secret.yaml | Minimax, DeepSeek, Exa, OpenRouter, Anthropic | `SEED_*_API_KEY` by hand → vault-seed.yml | MISS | crew#579 |
| `prospector-engine-env` (`R2_*`, `STORE_*`) | platform/prospector/engine-external-secret.yaml | Cloudflare R2, estate | `SEED_R2_*`, `SEED_STORE_*` by hand | MISS | crew#578 (R2) · crew#575 (store) |
| `cloudflare-api-token` | platform/prospector/cloudflare-external-secret.yaml, platform/dns/external-dns.yaml | Cloudflare | no writer found; dashboard token pasted | MISS | crew#578 |
| `hermes-agent-env` (vendor keys, Telegram) | platform/hermes-agent/gateway.yaml | Anthropic, OpenRouter, Exa, Telegram | `SEED_HERMES_*` by hand → oke-check.yml | MISS | crew#579 |
| `hermes-agent-env` (`GITHUB_TOKEN`) | platform/hermes-agent/gateway.yaml | GitHub | `SEED_HERMES_GITHUB_TOKEN` PAT by hand | MISS | crew#577 |
| `hermes-agent-env` (`LITELLM_API_KEY`) | platform/hermes-agent/gateway.yaml | estate router | `SEED_HERMES_LITELLM_API_KEY` by hand | MISS | crew#576 |
| `flux-telegram` | platform/alerts-secret/flux-telegram.yaml, platform/robusta/external-secret.yaml | Telegram | no CI call site; BotFather token pasted | MISS | crew#579 |
| `healthchecks-db-password`, `healthchecks-ping-key`, `healthchecks-secret-key` | platform/healthchecks/external-secret.yaml | estate (Terraform random) | `random_password` + `oci_vault_secret` (platform/oci/healthchecks.tf), applied by oke-check | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `signoz-root-email`, `signoz-root-password` | platform/observability/signoz.yaml | estate (Terraform random) | `oci_vault_secret` (platform/oci/signoz.tf) | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `otlp-ingest-users` | platform/observability/httproute.yaml | estate (Terraform random) | `oci_vault_secret` (platform/oci/otlp-ingest.tf) | MEETS | Terraform · `bin/idp-oke-rebuild` |
| `ghcr-pull` | platform/mcp/pull-secret.yaml, platform/temporal/pull-secret.yaml | GitHub | `bin/idp-flux-bootstrap:55` builds it from a `GITHUB_TOKEN` PAT read from the vault | MISS | crew#577 |
| `backstage-env` | platform/backstage/overlays/oke/backstage-external-secret.yaml | estate | no writer found in bin/, workflows or Terraform | MISS | crew#575 |
| root OCI credential (`estate-tofu` key pair) | every `bin/idp-cloud` call | OCI | one browser SSO, IAM and key pair via API, private half to the sops vault | MEETS | `bin/idp-oci-bootstrap` |

## Security policy

This page is the proof behind the security-policy row "Every credential is born by a
bootstrapper" (docs/reference/security-policy.md); the row's proof command is
`bin/idp-root-trust`, run by `ci.yml` and hourly by `bin/idp-verify-drill` (crew#580).
