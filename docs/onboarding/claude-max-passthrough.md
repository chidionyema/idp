# Claude Code through the estate router (Max subscription passthrough)

How Claude Code reaches the estate's LiteLLM router while staying on the founder's
Claude Max subscription, and why this does not reverse the 2026-09-04 ruling.

Status: **built, not yet operating.** The router config is written; the client env and the
live verification below have not been run against the cluster. The empirical proof rule
binds this page: until `claude /status` on the laptop reads the claude.ai subscription and a
real turn completes through `llm.mumchimp.com`, this is "built", not "operating".

## The problem this solves

Pointing Claude Code at the router used to turn it into whatever non-Anthropic lane the model
name resolved to, because LiteLLM's normal job is **credential substitution**: it replaces the
client's credential with an estate-owned one. The `claude` and `claude-fast` lanes were
deleted on 2026-09-04 and no Anthropic API key exists in the estate, so there was nothing for
a substituted credential to authenticate against.

## The mechanism

Passthrough **inverts** substitution. The router relays the client's own OAuth token to
`api.anthropic.com` unchanged. Each client authenticates as itself against its own Max
subscription, so the model is genuinely Claude and the estate holds no Anthropic credential.

Two config facts make it work, both in `platform/llm/config.base.yaml` (and mirrored in
`llm/config.base.yaml`, since this repo has two routers):

1. **A lane with no `api_key`.** `claude-opus` carries `model: anthropic/claude-opus-4-5` and
   nothing else. The missing `api_key` is the mechanism, not an omission — it is what tells
   LiteLLM to use the forwarded client credential.
2. **`general_settings.forward_client_headers_to_llm_api: true`.** This forwards `x-*` and
   `anthropic-beta` headers, which is what keeps `ENABLE_TOOL_SEARCH` and beta features
   working through the router.

   Note precisely what this flag does and does not do, because it is easy to overstate
   (this page did, and the measurement corrected it): it is **not** what carries the
   subscription token. The OAuth `Authorization` header is forwarded by LiteLLM's
   `clean_headers` path regardless of this setting, as the upstream docs also say.

`forward_llm_provider_auth_headers` is deliberately **not** set. That is the `x-api-key` BYOK
path, and an Anthropic `x-api-key` is exactly the API key the ruling forbids.

### The discriminator is the token prefix, not a config flag

This was verified by running LiteLLM 1.98.0's own `clean_headers` and
`is_anthropic_oauth_key` (see "Proof" below). LiteLLM forwards the `Authorization` header
**only when it carries an OAuth token** — the `sk-ant-oat` prefix:

| Credential | Forwarded to Anthropic? |
|---|---|
| `sk-ant-oat01-…` (Max subscription OAuth token from `claude /login`) | **yes** |
| `sk-ant-api03-…` (Anthropic API key) | **no** |

And the header is forwarded only when it was **not** the header used to authenticate with the
router. That is why the client must send `x-litellm-api-key`: if the client authenticates with
`Authorization`, the subscription token is consumed for gateway auth and dropped. Both cases
were measured.

Source: <https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription> and
<https://docs.litellm.ai/docs/proxy/forward_client_headers>, both read 2026-09-21.

## Proof

Run against the real LiteLLM 1.98.0 code on 2026-09-21 (`clean_headers` and
`is_anthropic_oauth_key` imported from the published package), not a re-implementation:

```
is_anthropic_oauth_key("Bearer sk-ant-oat01-abc123")  -> True
is_anthropic_oauth_key("Bearer sk-ant-api03-KEY")     -> False

clean_headers({x-litellm-api-key, Authorization: Bearer sk-ant-oat01-…},
              authenticated_with_header="x-litellm-api-key")
  -> {'Authorization': 'Bearer sk-ant-oat01-…'}   # subscription forwarded

clean_headers({x-litellm-api-key, Authorization: Bearer sk-ant-api03-…},
              authenticated_with_header="x-litellm-api-key")
  -> {}                                            # API key dropped

clean_headers({Authorization: Bearer sk-ant-oat01-…},
              authenticated_with_header="authorization")
  -> {}                                            # OAuth dropped: wrong client config
```

This proves the **mechanism**. It does not yet prove the **estate deployment**: the cluster's
`/anthrompic` path, virtual-key auth, and a live Claude Code turn are steps 1–5 below and are
still unrun.

## Why this does not reverse the ruling

Founder, 2026-09-04 (`platform/llm/external-secret.yaml`): *"estate will never use antropic
api keys ... final and end of."*

That ruling bans **API keys**. An OAuth token minted by `claude /login` against a Max
subscription is a different credential on a different billing path. Nothing in this change
creates, stores, or transmits an Anthropic API key: not in the vault, not in
`external-secret.yaml`, not on the lane.

## Client setup (the Mac)

Set these. **Do not set `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`** — setting either
replaces the subscription with an API-key credential and defeats the whole arrangement.

```bash
export ANTHROPIC_BASE_URL="https://llm.mumchimp.com"
export ANTHROPIC_MODEL="claude-opus"
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer <router-virtual-key>"
```

The two credentials coexist without collision: `x-litellm-api-key` authenticates the client
to the estate router (budgets, rate limits, tracking), while the OAuth `Authorization` header
is forwarded upstream to Anthropic.

`ENABLE_TOOL_SEARCH=true` is worth setting in the same `env` block. Claude Code disables tool
search whenever `ANTHROPIC_BASE_URL` is not a first-party Anthropic host, which inlines every
MCP tool schema into the context window. That is precisely the traffic the router's
`efficiency_gateway.py` MCPAdapter mechanism truncates, so leaving it off both bloats the
window and under-uses the efficiency layer.

## Verification (do not skip; this is the "operating" proof)

1. `claude /status` — the login method must read the **claude.ai subscription**, not an API
   key. If it shows an API key, `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` is set somewhere
   and the passthrough is not in effect.
2. Run a real turn in Claude Code and confirm it completes.
3. Confirm the request appears in the router's logs at `llm.mumchimp.com/ui`, attributed to
   the `claude-opus` lane.
4. Confirm the model is genuinely Claude (an `anthropic/claude-opus-4-5` response), not a
   fallback lane.
5. Confirm no Anthropic API key was created: the lane has no `api_key`, and
   `external-secret.yaml` still carries none.

Until steps 1–4 have been observed on the laptop, this page describes something built, not
something operating.
