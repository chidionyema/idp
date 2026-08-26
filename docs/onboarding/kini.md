# Onboarding: KINI (crew#284)

## What it is for

KINI is the founder-facing surface of the estate: one Telegram chat, a
presence dot, a daily digest, and a kernel that signs a receipt for every
action it takes. The founder never opens a terminal (LAW 31). Every model call
behind it goes through the one router, so spend, routing and traces have one
place each (LAW 34, the headline: one platform).

## Where it lives

```
platform/llm/                       the router on the cluster (Flux row `llm`)
platform/llm/config.yaml            aliases: minimax, deepseek, gemini, vision, openrouter, *-or
llm/config.yaml                     the laptop copy; tests/test_llm_row.py keeps the two in step
sovereign/config.py                 model.consensus = minimax, deepseek, gemini; litellm.base_url from the secret store
hermes-v2/plugins/sovereign/        the Telegram side (CP1), lives with the product, not the platform
features/sovereign-bus/             the executable spec per checkpoint
docs/demo/kini.md                   what is live, with captured output
```

## How a call flows

1. Telegram message reaches hermes-v2; the `sovereign` plugin calls the kernel.
2. The kernel reads `LITELLM_BASE_URL` and a virtual key from the estate
   secret store and calls `https://llm.mumchimp.com/v1/chat/completions`
   with an alias, never a vendor name.
3. The router picks the deployment. If the direct vendor account fails, the
   `*-or` deployment of the same model through OpenRouter answers (idp#257).
4. Langfuse gets the trace; the kernel signs the receipt; Telegram shows one
   line with hash and budget delta.

## Checking it

From anywhere:

```
curl -s https://llm.mumchimp.com/health/readiness
```

With the master key from vault entry `litellm-upstream` (read into a variable,
never echoed):

```
curl -s -H "Authorization: Bearer $KEY" https://llm.mumchimp.com/v1/models
```

From the phone, when CP1 is live: send `status`, expect one receipt line.

## Money

Vendor accounts run dry. The router reports it as `429` with the vendor's
own words (`Insufficient Balance`, `credits are depleted`). Topping up a
vendor account is a billing decision and stays with the founder; the
fallback chain is what keeps consensus answering meanwhile.

## Related

```
docs/onboarding/litellm.md          the router itself
docs/onboarding/langfuse.md         where the traces land
https://github.com/chidionyema/crew/issues/284   checkpoint boxes and receipts
```
