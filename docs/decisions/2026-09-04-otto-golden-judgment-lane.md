# The next Otto was pointed at a model its router refuses

2026-09-04. Record for the change on `platform/otto-golden/deployment.yaml`.

## What was measured

`otto-golden` had `OTTO_ROUTER_LANE_JUDGMENT_MODEL` set to `kimi`. From inside the
`otto-golden` pod, using the key the pod already holds, against the estate model router at
`https://llm.mumchimp.com/v1`:

| Asked for | `/v1/models` lists it | `/v1/chat/completions` answers |
|---|---|---|
| `kimi` | yes | HTTP 400, `Invalid model name passed in model=kimi` |
| `minimax` | yes | HTTP 200 |
| `deepseek` | yes | HTTP 200 |

Being listed at `/v1/models` is not the same as being callable. The lane was configured
against the listing.

## What changed

The judgment lane is `minimax`, the measurement above recorded in a comment beside it so the
value is not silently reverted to the listed-but-dead one.

## Why it did not show up before

Nothing in this layer called a model at all — the boot lane answered every message with a
canned payload — so a dead lane cost nothing and stayed invisible. It becomes load-bearing the
moment the lane starts making real calls, which is the change in hermes-v2#71.
