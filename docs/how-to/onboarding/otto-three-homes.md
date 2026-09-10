# Onboarding: Otto's three homes

**Door (from the UI):** Backstage → **Create** → *Which home is Otto on?*. One button, no
parameters, and its verdict is a token Otto actually generated rather than a health check. You
never need a terminal to know which brain answered the founder. The button dispatches
`.github/workflows/otto-homes.yml`, which runs the `otto-homes` playbook of
`bin/idp-oke-break-glass`; the Backstage template is generated from that workflow's header by
`bin/idp-portal-buttons`, so the button and the check can never drift apart.

## Why this exists

Founder, 2026-09-09: *"otto must have 3 homes. Otto is founders personal assistant, has never
been stable even once. affirmative action, end of get it done"* and *"we must have the
alternative to litellm"*.

Record: `~/.claude/docs/founder/2026-09-09T2250Z-you-built-a-distributed-multi-agent-workforce-but-e6a3b096.md`,
`~/.claude/docs/founder/2026-09-09T2246Z-tells-litellm-if-anthropic-is-down-route-to-d96ca971.md`.

## The shape

```
Telegram ──> otto-gateway pod
               ├── gateway    (Otto himself; LITELLM_BASE_URL = http://127.0.0.1:4010/v1)
               ├── otto-brain (litellm, non-database image, loopback only)   <- the switch
               └── tailscale  (userspace; HTTP proxy on 127.0.0.1:1055)      <- the tailnet

  otto-brain's upstreams, in order. The first two are the homes; the three under them
  are the floor, and every one of the floor lanes is free:
    home 1   http://litellm.llm.svc.cluster.local:4000/v1        the estate router
    home 2   https://api.minimax.io/v1                            direct, no cluster, no router
    floor 1  https://api.groq.com/openai/v1                       openai/gpt-oss-120b
    floor 2  https://generativelanguage.googleapis.com/v1beta/... gemini-2.5-flash-lite
    floor 3  https://openrouter.ai/api/v1                         a free slug, and last for a reason
```

## Home 3 used to be the founder's Mac. It is not any more.

Founder, 2026-09-10: *"no i killed ollama because machine is slow"*, *"lets think of another
cloud home"*, *"dont rely on macbook"*. The measurements taken that morning agree with him: the
laptop is an Intel i7-8850H, Ollama reports `inference compute id=cpu library=cpu` with 4.7 GiB
free and no GPU at all; `qwen2.5-coder:7b` held resident answered 16 output tokens in 24-46s,
returned `unexpected EOF` on a realistic 1.4k-token prompt, and `llama3.2:3b` returned nothing
in 240 seconds. A home that cannot answer a real prompt inside Otto's own client timeout is not
a lifeboat, and one that depends on a laptop being open is not one either.

## Why the floor is three vendors and not one

Founder, the same day: *"free with limits? what if limit is reached? need otto to live
forever"*, and *"this has to be sophisticated"*. He is right that a free tier ends. Groq's own
headers, read from inside the pod:

```
x-ratelimit-limit-requests   1000     per day
x-ratelimit-limit-tokens     8000     per minute
```

Generous, and still finite. So under Groq sit two more free lanes at two more vendors, and the
estate already holds a live key for each. Exhausting one is a hop, not an outage.

The router parks a spent lane rather than re-asking it: `allowed_fails: 1` and
`cooldown_time: 300` in `three-homes.yaml`. Without that the chain still works but works
stupidly — the day Groq's thousandth request is spent, every turn would pay a round trip to
Groq to be told 429 again before reaching Gemini. This is litellm's own cooldown machinery,
which is the whole reason the switch is litellm and not a hand-written script.

What was measured, from inside the pod, on the estate's own keys:

| lane | result |
|---|---|
| groq `openai/gpt-oss-120b` | 200 in 0.48s, tool calls work |
| `gemini-2.5-flash-lite` | 200 in 0.82s, tool calls work |
| `gemini-2.5-flash` | 200 in 0.78s, but returned **no** tool call when one was demanded |
| openrouter `nvidia/nemotron-3.5-lightning:free` | 200 in 8.68s, no tool call |
| openrouter, three other free models | a 45s timeout, a 403, and a 429 |

That last row is why OpenRouter is last and never counted on. Model slugs churn there: three
`:free` models every list still names now answer `404 "This model is unavailable for free."`
Groq's do too — `llama-3.3-70b-versatile` is named everywhere and 404s.

## Where each thing lives

| thing | file |
|---|---|
| the three homes and their order | `platform/otto-gateway/three-homes.yaml` |
| home 2's key, and the pod's tailnet key | `platform/otto-gateway/three-homes-secrets.yaml` |
| the three floor keys, and the door they come through | `platform/vendors/consoles.yaml`, `platform/human-vault-bridge/` |
| the two sidecars, and Otto's one changed line | `platform/otto-gateway/deployment.yaml` |
| how long Otto waits before giving up | `platform/otto-gateway/deployment.yaml`, `OTTO_ROUTER_TIMEOUT_SECONDS` |
| the lane names Otto asks for | `platform/otto-gateway/router-lanes.yaml` |

## Changing the order

Edit the `fallbacks:` block of `platform/otto-gateway/three-homes.yaml` and open a pull
request. Reloader rolls the door on the change. Do not add a home whose lane cannot answer:
this estate has written the same sentence into `platform/llm/config.yaml` twice — *"a hop that
always refuses is latency, not redundancy"* — and a dead home costs a timeout on the one turn
that mattered.

## Adding a fourth home

Add a `model_list` row with its own `api_base`, and name it at the tail of each chain. Keep the
free lanes last, for the reason `llm/config.yaml:166` already records — a hop that costs
nothing is the right floor, not the right first try.

Then check the arithmetic, because this is the step that has actually bitten. Every lane's
`timeout:` is paid in series when the ones above it are silent, and the total must stay under
`OTTO_ROUTER_TIMEOUT_SECONDS` in `deployment.yaml`. Today: 20 + 60 + 20 + 20 + 25 = 145s of
lanes against a 170s ceiling. Get this wrong and the failover works perfectly while the founder
still gets nothing — Otto hangs up moments before the last home answers. It was wrong exactly
once, on 2026-09-10, when the ceiling was the unset default of 120s.

## What this is not

It is not a second estate router. The estate keeps one router and home 1 is it: every
happy-path turn still walks `litellm.llm.svc`, still spends against the estate's budgets and
still lands in Langfuse. Home 2 and the floor carry no policy and no ledger and are reached only
when home 1 could not answer. A lifeboat, not a fleet — and no other workload gets one, because no
other workload is the founder's assistant.

## If Otto goes quiet anyway

1. Which home answered last: the Backstage card above.
2. Is the switch itself up: the `otto-brain` container's own probe is
   `/health/liveliness` on `127.0.0.1:4010`, and it needs no upstream, so a red probe there is
   the sidecar and never a vendor.
3. Did the door hand the switch a key the switch can read: the `ottodoorkey` row on
   `otto-gateway`'s CI checks. The sidecar is the no-database image, so it can only compare a
   *master* key in process; hand it the estate router's *virtual* key and it refuses every turn
   with `400 "No connected db."` before any home is tried, in about 0.2s, while every probe
   that goes around it stays green. That is precisely what happened on 2026-09-10 and the rule
   exists so it cannot happen twice.
4. Is a floor lane simply spent: a 429 is not a fault. `allowed_fails: 1` parks that lane for
   five minutes and the turn goes to the next vendor. Otto should be answering from a
   different home, not falling silent.
5. Do the free keys still resolve: the four `human-*` ExternalSecrets in the `otto-gateway`
   namespace must all read Ready. They are `optional:` in the pod on purpose, so a key that
   goes missing costs Otto one lane rather than holding the whole door shut — which also means
   a missing key is quiet, and this is where you look for it.
