# Every strong model on the estate router is unfunded, so every answer comes from MiniMax

2026-09-04. Record for the change on `platform/otto-golden/deployment.yaml`, and for the
question behind it: why does every reply come back from the weakest model?

## The measurement

Every chat lane the running proxy serves was called once, from inside the `litellm` pod with
the proxy's own key, each request carrying a unique nonce so no cache could answer it, and
with fallbacks switched off so each lane had to answer for itself.

| Lane asked for | What happened |
|---|---|
| `claude` (`claude-sonnet-5`) | HTTP 400 — "Your credit balance is too low to access the Anthropic API" |
| `claude-fast` (`claude-haiku-4-5`) | HTTP 400 — same, same account |
| `deepseek` (direct) | HTTP 401 — "Authentication Fails, Your api key: ****af0f is invalid" |
| `gemini` (`gemini-2.5-flash`) | HTTP 429 — "Your prepayment credits are depleted" |
| `gemini-or` (Gemini through OpenRouter) | HTTP 402 — "This request requires more credits" |
| `groq`, `groq-fast` | not served by the running proxy at all, though both are in `platform/llm/config.yaml` |
| `kimi` | HTTP 400, "Invalid model name" — there is no `kimi` row in the config; it has never existed |
| `minimax` (direct, `MiniMax-M2`) | HTTP 200, answered in 2.2s |
| `minimax-or`, `deepseek-or`, `openrouter` | HTTP 200 through OpenRouter |

Account balances, read from the vendors with the estate's own keys:

* MiniMax — key valid, account funded. The one account with money in it.
* OpenRouter — `total_credits` 10, `total_usage` 10.18. Overdrawn.
* Anthropic — key valid, balance too low to serve a request.
* Google — prepayment credits depleted.
* DeepSeek direct — key invalid.

## Why every answer came from MiniMax anyway

`router_settings.fallbacks` in `platform/llm/config.yaml` ends every chain in `minimax`:
`claude: [minimax, deepseek]`, `gemini: [minimax, deepseek]`, `deepseek: [minimax]`. So a
caller that asks for Claude, Gemini or DeepSeek gets HTTP 200 and a MiniMax answer, and
nothing in the reply says so. Measured: asking the proxy for `claude` returned
`"model": "MiniMax-M2"` with a normal 200.

The fallback is doing its job — a dry account must not take the estate offline. What is
missing is that it is silent. A chain that quietly downgrades every request looks identical,
from the outside, to a platform that only ever had one model.

## What changed here

`OTTO_ROUTER_LANE_JUDGMENT_MODEL` moves from `kimi` to `minimax`. `kimi` was never a row in
the router config, so the lane named a model that does not exist and was answered with HTTP
400 on every call. `minimax` is the only directly funded lane, so it is the honest name for
what this layer actually gets today.

## What this costs, and the one thing that changes it

The estate is running on one vendor account. The strongest lane on the router,
`claude-sonnet-5`, is one billing top-up away — its key is valid and authenticates; only the
balance refuses. Funding the Anthropic account switches `claude` and `claude-fast` on with no
code change, because both rows are already in the config and already in the fallback chains.
