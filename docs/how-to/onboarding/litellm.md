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
   either pick one from the **Existing Credentials** dropdown (see the next section) or
   reference a key the pod already holds: `os.environ/MINIMAX_API_KEY`,
   `os.environ/DEEPSEEK_API_KEY`, `os.environ/OPENROUTER_API_KEY`, `os.environ/GEMINI_API_KEY`.
4. Save. `store_model_in_db: true` in `general_settings` means the row is in `litellm-db` and
   survives a pod restart; `platform/llm/config.yaml` is never edited for this.

## Bringing a new provider's key (the console, nothing else)

This is the credential intake an enterprise operator gets, and so it is the one the founder
gets ([the founder is enterprise client zero](../../reference/policy/enterprise-client-zero.md),
across the board, not only here): no terminal, no repository secret, no fresh key when one
exists. Steps read from LiteLLM's own model-management page
(docs.litellm.ai/docs/proxy/model_management, read 2026-09-03):

1. In the console, open the **LLM Credentials** tab and click **Add Credential**. Pick the
   provider, paste the key, give the credential a name. The form's fields adapt to the
   provider picked.
2. Models → Add Model: pick the model, and choose that credential from the **Existing
   Credentials** dropdown instead of typing a key.
3. Done. The model row and the credential persist in `litellm-db` and survive pod restarts.
   Credentials are encrypted at rest; no `LITELLM_SALT_KEY` is set today, so LiteLLM
   encrypts with `LITELLM_MASTER_KEY`, which only the vault holds.

Two rules the console enforces that are easy to trip over:

- **A model name that `platform/llm/config.yaml` already defines is owned by git**, and the
  console refuses to edit it or attach a key to it ("defined in config"). If a lane should
  be console-owned, its git row is removed first — that is a platform change, not an
  operator step (the `kimi` lane moved to console-owned this way on 2026-09-03).

## Moving every git lane to the console (the founder, one run)

The founder's ruling of 2026-09-03 ("enable the thing", on the greyed-out Update API Key
button) makes every lane console-owned, not only Kimi. The move is one run of the
`vault-seed` workflow on the repository's Actions page: choose "Run workflow", pick the entry
`router-rows`, and run it. The run copies each lane of `platform/llm/config.yaml` into the
console with the vendor key the vault already holds, prints one line per lane (`ok`, `kept`
or `FAIL` naming the key it could not find) and never prints a value. A lane the console
already owns is kept, so the run can be repeated.

Until the git rows are removed (the follow-up platform change), the console lists each lane
twice, one row locked and one editable, and the router shares calls between the two; that
is its ordinary load balancing. Once the git rows are gone, the Update API Key form works on
every lane, and a key changed there is live within the router's next poll, no restart.

Why the rows move rather than a credential being attached to the git rows: at the version
the estate runs (v1.98.0) the router reads a named credential once, when the row is added,
and a credential edit only refreshes the list in memory. A git row pointing at a console
credential would keep its old key until the pod restarted, which is the greyed button with
extra steps.
- **A Kimi (Moonshot) key answers only at its home host** (see the section below). The
  console cannot probe the three hosts, so if the model's test call fails with an
  incorrect-key answer, set the row's API Base to the next host on the list and test again.

The automated alternative stays available: a `SEED_*` repository secret feeds the vault
entry `litellm-upstream` through the `oke-check` apply step (never from a laptop; one new
key, no re-seed), and git-rendered rows reference it as `os.environ/...`. That road suits
keys minted by code; the console road suits a key a person already holds.

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

## A Kimi key has one of three homes

Kimi (Moonshot) sells the same models from three hosts, and a key answers only at the host it was
made for: the open platform's global host, the Kimi Code membership host, and the open platform's
China host. The vendor's own FAQ says the key and the base URL must match. Nobody has to know or
say where a key was made: the apply step probes each host in turn with the one root
(`SEED_KIMI_API_KEY`), and the host that accepts the key is written to the vault beside it as
`MOONSHOT_API_BASE`. The router pod exports that file with the key, and LiteLLM's moonshot adapter
reads it, so the `kimi` lane calls the right host. A key refused at every host shows a line naming
each host's answer, never one word.

The list of hosts lives in `platform/vendors/consoles.yaml` under `kimi.bases`; the router row is
rendered from the same file.

## Checking it

- `curl -s -o /dev/null -w '%{http_code}\n' https://llm.<zone>/health/liveliness` → `200`
- `curl -s -o /dev/null -w '%{http_code}\n' https://llm.<zone>/ui/` → `200`
- `curl -sI https://llm.<zone>/sso/key/generate | grep -i '^location'` → the identity domain (`identity.oraclecloud.com`)
- `gh workflow run oke-check.yml -f mode=check` → the `model-routing` row

## The laptop stack is gone from the platform

`bin/litellm-up`, `llm/litellm.yml` and `llm/.env` are the developer's local mirror for tests
(`tests/test_llm_row.py` keeps the two `config.yaml` files in step). The estate's router is the
cluster one above; a laptop being off does not change whether a model call is routed (crew#313).
