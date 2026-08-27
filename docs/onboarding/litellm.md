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
2. Sign in with the router console login. It lives in the estate vault as `litellm-ui`
   (`UI_USERNAME`, `UI_PASSWORD`); it reached the founder's Telegram once, from the session that
   seeded it. Nobody types it into a file.
3. Models → Add Model. Pick the provider, type the public model name, and for the credential
   reference the key the pod already holds: `os.environ/MINIMAX_API_KEY`,
   `os.environ/DEEPSEEK_API_KEY`, `os.environ/OPENROUTER_API_KEY`, `os.environ/GEMINI_API_KEY`.
   A provider the vault does not hold a key for needs the key added to the vault entry
   `litellm-upstream` first (`bin/idp-vault-put`, run by the `oke-check` apply step from
   `SEED_*` repository secrets, never from a laptop).
4. Save. `store_model_in_db: true` in `general_settings` means the row is in `litellm-db` and
   survives a pod restart; `platform/llm/config.yaml` is never edited for this.

Keys, Teams and Spend are the other tabs of the same console: a product gets its own virtual key
with a daily budget there (the kernel's is alias `sovereign-kernel`, $5/day).

## Rotating the console login

`gh secret set SEED_LITELLM_UI_USERNAME`, `gh secret set SEED_LITELLM_UI_PASSWORD`, then
`gh workflow run vault-seed.yml -f entry=litellm-ui`. The ExternalSecret refreshes within an hour;
`kubectl -n llm rollout restart deploy/litellm` (or the next Flux reconcile of a changed
Deployment) makes the pod read it. Any session can do this; it is a row in the capabilities
register, not a founder action.

## Checking it

- `curl -s -o /dev/null -w '%{http_code}\n' https://llm.<zone>/health/liveliness` → `200`
- `curl -s -o /dev/null -w '%{http_code}\n' https://llm.<zone>/ui/` → `200`
- `gh workflow run oke-check.yml -f mode=check` → the `model-routing` row

## The laptop stack is gone from the platform

`bin/litellm-up`, `llm/litellm.yml` and `llm/.env` are the developer's local mirror for tests
(`tests/test_llm_row.py` keeps the two `config.yaml` files in step). The estate's router is the
cluster one above; a laptop being off does not change whether a model call is routed (crew#313).
