# Credential life cycle

Founder, 2026-08-29 (crew#618): "all this needs to be documented; no PR covering critical infra
like this can have setup going to void: reusable? expiration? we need policy."

This page is the policy. It is written in plain English and it is graded by
`tests/test_incident_crew618_every_root_has_a_life_cycle.py`: every `SEED_*` repository secret a
workflow reads must have a row below, and every row must fill expiry, rotation and revocation. A
pull request that adds a root without a row is red. A pull request that touches a bootstrapper,
the vendor registry or a `SEED_*` line carries a `Lifecycle:` line naming its row
(`policy/operating_model.rego`, rule `lifecycle_row`).

## The rule in five lines

1. **One root per provider** (R52). The founder makes it once, with the least power that still
   lets code mint the rest, and sets it with `gh secret set <NAME> -R chidionyema/idp`.
2. **Reusable, never single-use.** A root is used by every apply run. It is never regenerated
   for a run, never copied to a second place, never shared between providers.
3. **Expiry is stated, not assumed.** Where the provider lets a root expire, the row says how
   long. Where it cannot, the row says "none" and rotation is the control.
4. **Rotation is one action.** Make a new root, set the same secret name, run apply. The old one
   is revoked after the run proves the new one. Children are re-minted by the pipeline.
5. **Revocation is one click at the provider** and kills every child. The row names the click.

Configuration values that ride a `SEED_*` name but are not credentials (a chat id, a user id
list, a slug) are listed at the end so the gate knows them; they have no life cycle.

## Roots

| Secret | Provider | Made where, once | Power | Expiry | Rotation | Revocation | Audit |
|---|---|---|---|---|---|---|---|
| `SEED_TAILSCALE_CLIENT_ID`, `SEED_TAILSCALE_CLIENT_SECRET` | Tailscale | admin console, Trust credentials page, Credential, OAuth; scope OAuth keys write only | mints OAuth clients tagged `tag:k8s`; cannot join the tailnet | none (kb/1215); OAuth clients do not expire | new client, same two secret names, `oke-check` apply; children re-minted by `bin/idp-bootstrap-tailscale`; then delete the old client | delete the client in the console; every child dies with it | Tailscale audit log (client creations); apply log names keys, never values |
| `SEED_CLOUDFLARE_ROOT_TOKEN` | Cloudflare | dash, My Profile, API Tokens; permission User API Tokens: Edit only | mints the DNS token and the R2 credential; cannot edit DNS itself | set a TTL at creation; the row's floor is 1 year | new token, same name, apply; `bin/idp-bootstrap-cloudflare` re-mints the children; roll the old token | roll or delete the token in the dash; children keep working until re-minted, so re-mint at once | Cloudflare audit log; apply log |
| `SEED_ANTHROPIC_API_KEY` | Anthropic | console, API keys | model calls on the estate account | none | new key, same name, apply (`bin/idp-bootstrap-vendors` proves and vaults it); delete the old key | delete the key in the console | Anthropic usage page per key |
| `SEED_OPENROUTER_API_KEY` | OpenRouter | settings, keys; set a credit limit | model calls | none | as Anthropic | delete the key | OpenRouter activity per key |
| `SEED_DEEPSEEK_API_KEY` | DeepSeek | platform, API keys | model calls | none | as Anthropic | delete the key | DeepSeek usage |
| `SEED_MINIMAX_API_KEY` | Minimax | platform, interface key | model calls | none | as Anthropic | delete the key | Minimax usage |
| `LITELLM_LAPTOP_KEY` (the Mac reads it as `LITELLM_API_KEY`) | the estate router (LiteLLM, `platform/llm`) | `vault-seed.yml` entry `laptop`: `bin/idp-router-key laptop <lanes>` mints it from the router's master key, `estate-secrets/scripts/secret-add` vaults it; no console | model calls on the listed lanes only, `max_budget` per day (`bin/idp-router-key`); no vendor key, no admin | none; the daily budget is the ceiling | re-run `vault-seed.yml` entry `laptop`: a new virtual key, same secret name; the Mac picks it up through `scripts/secret-load` | delete the key in the router console (`/ui`, Virtual Keys) or set its budget to 0; the Mac has nothing else | router spend ledger (`oke-check.yml -f mode=break-glass -f playbook=router-spend`) per key alias `laptop` |
| `SEED_GROQ_API_KEY` | Groq | console, keys | model calls | none | as Anthropic | delete the key | Groq usage |
| `SEED_GEMINI_API_KEY` | Google | AI Studio, API key; restrict to Generative Language API | model calls | none | as Anthropic | delete the key | Google Cloud API key usage |
| `SEED_EXA_API_KEY` | Exa | dashboard, API keys | search calls | none | as Anthropic | delete the key | Exa usage |
| `SEED_STRIPE_SECRET_KEY` | Stripe | dashboard, API keys; restricted key with the store's needs only | payments on the store account | none | new restricted key, same name, apply; roll the old key | roll the key in the dashboard | Stripe request log |
| `SEED_TELEGRAM_HERMES_BOT_TOKEN` | Telegram | BotFather, `/newbot` or `/token` | the Hermes bot | none | `/revoke` in BotFather gives a new token; set the same name; apply | `/revoke` | none at Telegram; the gateway logs every update |
| `SEED_TELEGRAM_ALERTS_BOT_TOKEN` | Telegram | BotFather | the alerts bot | none | as above | `/revoke` | as above |
| `SEED_HERMES_TELEGRAM_BOT_TOKEN` | Telegram | superseded by `SEED_TELEGRAM_HERMES_BOT_TOKEN`; deleted after the vendors step is green once (crew#618) | the Hermes bot | none | n/a, being removed | `/revoke` | as above |
| `SEED_HERMES_LITELLM_API_KEY` | estate router | superseded by `bin/idp-estate-seed` (`bin/idp-router-key`); deleted after the seed is green once (crew#618) | model calls through the router | none | n/a, being removed | delete the key in the router | router spend log |
| `SEED_HERMES_AUTH_JSON` | Hermes | the gateway's own auth store, exported once | the gateway's stored logins | none | re-export, same name, apply | delete the entry in the vault and re-run | gateway log |
| `SEED_GITHUB_APP_ID`, `SEED_GITHUB_APP_CLIENT_ID`, `SEED_GITHUB_APP_SLUG` | GitHub | created by the App manifest flow (`bin/idp-github-app`) | identifiers, not secrets | none | change with the App | delete the App | GitHub App settings |
| `SEED_GITHUB_APP_PEM_B64` | GitHub | the App's private key, made by the manifest flow | mints installation tokens (1 hour each, re-minted hourly by `bin/idp-github-app refresh`) | none; children expire in 1 hour | generate a new private key on the App, set the same name, delete the old key | delete the key on the App; every token dies within the hour | GitHub App audit log |
| `SEED_FLUX_WRITER_IDENTITY_B64` | GitHub | deploy key for Flux image automation, made by `bin/idp-estate-seed` | push to `flux/image-updates` | none | new key pair, same name, apply; remove the old deploy key | remove the deploy key on the repository | repository deploy keys page |
| `SEED_R2_ACCOUNT_ID`, `SEED_R2_ACCESS_KEY_ID`, `SEED_R2_SECRET_ACCESS_KEY` | Cloudflare | superseded by the R2 credential `bin/idp-bootstrap-cloudflare` mints from the root; deleted after #746 is green once (crew#618) | R2 bucket read and write | none | n/a, being removed | delete the R2 token in the dash | Cloudflare audit log |

## What the founder puts in, per provider (once)

Each block is the whole of his part for that provider. He does not read this page to do it:
`bin/idp-set-root <provider>` opens the page, says the same steps in the terminal, takes each
value with hidden input, sets the secret and dispatches the apply run (R53: instructions and
action in one place, zero friction). After the secret is set, say "set" in
Telegram; the next `oke-check` apply run does the rest.

**Tailscale.** Admin console, Trust credentials page (kb/1215), Credential, OAuth, Generate credential. Description:
`estateseed`. Scopes: tick only "OAuth keys", choose Write. Tags, if asked: `tag:k8s`. Generate.
Then, on the laptop, paste each value when asked:
`gh secret set SEED_TAILSCALE_CLIENT_ID -R chidionyema/idp` and
`gh secret set SEED_TAILSCALE_CLIENT_SECRET -R chidionyema/idp`.

**Cloudflare.** Dash, My Profile, API Tokens, Create Token, Custom token. Name: `estate-root`.
Permissions: one row, "User", "User API Tokens", "Edit". TTL: one year. Create. Then
`gh secret set SEED_CLOUDFLARE_ROOT_TOKEN -R chidionyema/idp`.

**AI and search vendors.** Make one key on the vendor's key page (the `page` field in
`platform/vendors/consoles.yaml`), name it `estate`, then set it under the name in the table
above, for example `gh secret set SEED_ANTHROPIC_API_KEY -R chidionyema/idp`. One command per
vendor: Anthropic, OpenRouter, DeepSeek, Minimax, Groq, Gemini, Exa, Stripe.

**Telegram.** In BotFather, `/token`, pick the bot, copy the token. Hermes bot:
`gh secret set SEED_TELEGRAM_HERMES_BOT_TOKEN -R chidionyema/idp`. Alerts bot:
`gh secret set SEED_TELEGRAM_ALERTS_BOT_TOKEN -R chidionyema/idp`.

**GitHub, OCI, Sunshine.** Nothing. They already run on machine identity.

## Configuration that is not a credential

`SEED_HERMES_TELEGRAM_ALLOWED_USER_IDS`, `SEED_HERMES_TELEGRAM_HOME_CHANNEL`, `SEED_R2_BUCKET`. A chat id, a user
id list and a bucket name. They ride the hermes-agent-env step as configuration and have no life cycle.
