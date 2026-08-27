# Demo: KINI (crew#284), what runs today and what does not yet

KINI is the founder's phone talking to the estate: a Telegram command becomes a
kernel receipt, and every model call the kernel makes goes through the one
router at `https://llm.mumchimp.com`. This page shows real output, captured
2026-08-26, and says plainly which rows are not live. Checkpoint state is the
box list on [crew#284](https://github.com/chidionyema/crew/issues/284).

## What you can do now: the router answers from the internet

DNS, certificate and health, from a laptop with no cluster access:

```
$ dig +short llm.mumchimp.com
193.123.184.22
$ curl -s https://llm.mumchimp.com/health/readiness
{"status":"healthy","db":"Not connected", ...}
```

The model list, with the master key from the vault entry `litellm-upstream`
(read in-process, never printed):

```
$ curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" https://llm.mumchimp.com/v1/models
['deepseek', 'gemini', 'minimax', 'minimax_m27', 'openrouter', 'vision']
```

One routed call per consensus alias (`sovereign/config.py` `model.consensus`),
same day, before idp#257:

```
minimax    429  No deployments available (cooldown after upstream failure)
deepseek   429  DeepseekException: Insufficient Balance
gemini     429  GeminiException: prepayment credits are depleted
openrouter 200  'OK'
```

The platform routed every call and Langfuse traced every failure. The three
direct vendor accounts were empty. idp#257 puts an OpenRouter-backed
deployment of the same three models first in each fallback chain, so one
empty account no longer takes consensus down. After it reconciles the same
three lines read `200`.

## What you cannot do yet

| Row | State on 2026-08-27 | Owner |
|---|---|---|
| CP1 Telegram to kernel receipt, `undo`, photo intake | not confirmed from the phone; `hermes-v2/plugins/sovereign` registers 7 commands (`bin/verify` PASS); the founder's `/sb-list` on 2026-08-27 00:08Z hit a gateway process older than the plugin code and was answered as chat; gateway restarted 00:23Z, resend requested | session d5ae1960 |
| CP2 router | live with a database (idp#262, #263, #270, #274); a kernel key is minted from outside and stored in `estate-secrets` dev; `sovereign/tests/bdd/test_cp2_litellm_real.py` 3 passed against the live router on 2026-08-27 | crew#284 comment 5432705704 |
| CP7 identity | crew#227, linked only | crew#227 |

The phone demo (send `status` in Telegram, get a one-line receipt with hash
and budget delta) is the demo this page will carry once CP1 posts its receipt
id. Until then the router demo above is the whole of what is demonstrable.
