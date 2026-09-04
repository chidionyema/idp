# The router was two generations behind, and one of its lanes did not exist

2026-09-04. Record for the change to `llm/config.yaml` and `platform/llm/config.yaml`.

## What was measured

Every model the vendors actually serve was read from the vendors themselves, with the estate's
own keys, from inside the `litellm` pod.

**MiniMax.** `api.minimax.io/v1/models` returned eight models: MiniMax-M3, M2.7,
M2.7-highspeed, M2.5, M2.5-highspeed, M2.1, M2.1-highspeed, M2. The estate was pinned to
`MiniMax-M2`, the oldest of the eight, on a funded account entitled to all of them. A live
completion on M3 answered in 1.8 seconds against M2's 4.3.

**Kimi.** There was no `kimi` row in either config file. The estate nevertheless had a layer
configured to ask for `kimi` — `otto-golden` — and every one of those calls came back
`Invalid model name passed in model=kimi`, then fell through the chain to MiniMax. A lane that
was named everywhere and declared nowhere.

**DeepSeek.** The direct lane answers HTTP 401: `Authentication Fails, Your api key: ****af0f
is invalid`. The credential is present in the estate's secret store (35 bytes, the right shape
for a DeepSeek key) — it is present and rejected, not missing. The OpenRouter catalogue carries
`deepseek/deepseek-v4-pro` at 1,048,576 context, four generations past the `deepseek-chat` the
`deepseek-or` lane was buying.

## What changed

| Lane | Was | Is |
|---|---|---|
| `minimax` | `openai/MiniMax-M2`, 204,800 context | `openai/MiniMax-M3`, 1,000,000 context |
| `minimax-or` | `openrouter/minimax/minimax-m2` | `openrouter/minimax/minimax-m3` |
| `deepseek-or` | `openrouter/deepseek/deepseek-chat` | `openrouter/deepseek/deepseek-v4-pro` |
| `kimi` | did not exist | `openrouter/moonshotai/kimi-k3`, falls to `minimax` |
| `claude-or` | did not exist | `openrouter/anthropic/claude-sonnet-5`, first hop of the `claude` chain |

Kimi is bought through OpenRouter rather than from Moonshot directly because the estate holds
no Moonshot credential, and a row wired to a key that does not exist is the same phantom lane
in a new costume. `moonshotai/kimi-k3` is the newest Kimi in the OpenRouter catalogue.

One account now covers everything the estate is short of. OpenRouter's catalogue, read the
same day, sells `anthropic/claude-sonnet-5` at 1,000,000 context alongside Kimi K3 and DeepSeek
v4 Pro. So a single top-up on the OpenRouter account turns on Claude, Kimi, DeepSeek and Gemini
together, with no key to mint at four vendor consoles and no new credential anywhere in the
estate.

## What still does not answer, and why

Two of these lanes are declared and correct and will still refuse, for one reason: the account
behind them has no money.

* **Kimi** — measured 2026-09-04, OpenRouter is at `total_credits` 10 against `total_usage`
  10.18. A 2,000-token Kimi turn returned HTTP 402, "can only afford 294". Funding that
  account is the whole of switching Kimi on: no deploy, no code change.
* **DeepSeek direct** — the key in the store is rejected by the vendor and has to be minted
  again at the DeepSeek console and seeded through `vault-seed.yml`. Until then the
  `deepseek` lane falls to MiniMax on every call.

## The class of mistake

Nothing failed loudly for either of these. A lane pinned to a two-year-old model returns HTTP
200. A lane that does not exist returns HTTP 200 from the fallback. An expired vendor key
returns HTTP 200 from the fallback. The estate looked like it was running four vendors while
it was running one, because the only signal that says otherwise is the `model` field in the
response body and nothing was reading it.

The durable fix is not in this change: the router should say, in the reply, which model
actually answered, so a silent downgrade is visible at the point it happens rather than in a
probe run weeks later.
