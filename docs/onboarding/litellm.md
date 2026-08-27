# Founder tutorial: picking and adding models (the router, llm.<zone>)

Executable spec: `features/gates/model-routing.feature`, graded by `tests/test_llm_row.py`.
Tracked on crew#400. `<zone>` is `estate.zone` in `clusters/<cluster>/estate-config.yaml`
(today `mumchimp.com`); the founder-surface card "Model router (llm)" in the catalogue at
`https://catalogue.<zone>` carries the resolved links.

## What it is

LiteLLM is the estate's one model router. Every model call from every product goes to
`https://llm.<zone>/v1` with a virtual key. It runs on the cluster as the Flux Kustomization
`llm` (`platform/llm/`), with its own Postgres (`litellm-db`), so which models exist, who may
call them and what they cost is one place, and that place is a web console, not a YAML file.

## Picking a model (as a caller)

`model` in the request is a row in the console's Models tab. The floor is `platform/llm/config.yaml`
`model_list`: `minimax`, `minimax_m27`, `deepseek`, `openrouter`, `minimax-or`, `deepseek-or`,
`gemini-or`, `gemini`, `vision`. `GET https://llm.<zone>/v1/models` with a key lists what the
router serves right now, including anything added in the console.

## Adding or changing a model (the founder, no PR)

1. Open `https://llm.<zone>/ui` (the "Admin console" link on the router's catalogue card).
2. Sign in with your estate login: the console sends you to the identity domain, the same
   sign-in as the catalogue. There is no console password (ADR 0007, crew#408). Who may sign in is
   `founder_emails` in `platform/oci/identity` (app `estate-router-console`), applied by
   `bin/idp-identity-apply`.
3. Models → Add Model. Pick the provider, type the public model name, and for the credential
   reference the key the pod already holds: `os.environ/MINIMAX_API_KEY`,
   `os.environ/DEEPSEEK_API_KEY`, `os.environ/OPENROUTER_API_KEY`, `os.environ/GEMINI_API_KEY`, `os.environ/GROQ_API_KEY`.
   A provider the vault does not hold a key for needs the key added to the vault entry
   `litellm-upstream` first (`bin/idp-vault-put --merge`, run by the `oke-check` apply step from
   whichever `SEED_*` repository secrets are set, never from a laptop; one new key, no re-seed).
4. Save. `store_model_in_db: true` in `general_settings` means the row is in `litellm-db` and
   survives a pod restart; `platform/llm/config.yaml` is never edited for this.

Keys, Teams and Spend are the other tabs of the same console: a product gets its own virtual key
with a daily budget there (the kernel's is alias `sovereign-kernel`, $5/day).

## Who can sign in, and how it is wired

`platform/oci/identity/main.tf` creates the confidential OIDC client `estate-router-console`
(redirect `https://llm.<zone>/sso/callback`), grants it to every address in `founder_emails`, and
writes the client id, secret and admin id to the vault as `litellm-sso-client-id`,
`litellm-sso-client-secret` and `litellm-sso-admin-id`. `platform/llm/external-secret.yaml`
(`litellm-sso`) mounts them; the pod exports them as `GENERIC_CLIENT_ID`, `GENERIC_CLIENT_SECRET`
and `PROXY_ADMIN_ID`, and the endpoints come from `estate-config` (`ESTATE_OIDC_DOMAIN_URL`).
Nothing is seeded by hand and no value is ever sent to a person (crew#407). Break-glass: the
form at `/ui/login` accepts the master key, which only the vault holds (`litellm-upstream`); it
is read by a pod, never by a chat.

## Checking it

- `curl -s -o /dev/null -w '%{http_code}\n' https://llm.<zone>/health/liveliness` → `200`
- `curl -s -o /dev/null -w '%{http_code}\n' https://llm.<zone>/ui/` → `200`
- `curl -sI https://llm.<zone>/sso/key/generate | grep -i '^location'` → the identity domain (`identity.oraclecloud.com`)
- `gh workflow run oke-check.yml -f mode=check` → the `model-routing` row

## The laptop stack is gone from the platform

`bin/litellm-up`, `llm/litellm.yml` and `llm/.env` are the developer's local mirror for tests
(`tests/test_llm_row.py` keeps the two `config.yaml` files in step). The estate's router is the
cluster one above; a laptop being off does not change whether a model call is routed (crew#313).
