# Demo — the lane that runs on a GPU nobody bills for

Every other lane Otto can think on is somebody's free tier: Groq's 1,000 requests a day,
Gemini's 1,500, Cloudflare's neuron allowance, OpenRouter's 50. A free tier can be withdrawn,
re-priced, or have its model slug quietly retired, and the day all of them do it at once the
estate has nothing to think with. This lane is the answer to that day. Kaggle gives 30 GPU-hours
a week on a T4 or a P100 at no cost, and a model **we** chose, running on a GPU **we** launched,
answers regardless of what any vendor decides.

It is also a fourth failure domain, which is the part that matters more than the price. Kaggle
shares no node, no network, no DNS and no control plane with the OKE cluster, and none with
Cloudflare either. Home 1 and home 2 can both be gone and this still answers.

## See it without launching anything

```
bin/idp-kaggle-lane --preflight
```

It reports what is present and writes nothing. Today, from a laptop with no Kaggle credential
in the vault, it prints three BLIND lines naming exactly what is missing and the door that
supplies each one — the Kaggle API token (one console step, once, by the founder), and the
Cloudflare tunnel token and shared bearer, both minted from the standing Cloudflare root that
the estate already holds (R52, one root per provider).

## Launch it

```
bin/idp-kaggle-lane --model qwen2.5-coder:7b --gpu nvidiaT4
bin/idp-kaggle-lane --status
```

The first pushes a four-cell notebook to Kaggle and starts it on a GPU: install Ollama, pull
the model, dial out through a **named** Cloudflare tunnel so the address is the same hostname
every session, then hold the session open. Nothing dials in and no inbound port is opened on
Kaggle's side. The second asks Kaggle how that push is doing.

## What you should expect to see

`ok kaggle pushed <user>/otto-gpu-lane on nvidiaT4`, and then, once the tunnel is up, the
lifeboat reaching it at `KAGGLE_LANE_URL`. The Worker skips the lane entirely when either the
key or the URL is unset, so nothing breaks before the notebook exists — that is why the lane
could ship before this launcher had ever been run.

## The part that is intermittent on purpose

Kaggle caps a session at 12 hours and that is not negotiable, so the launcher holds 11 and
stops itself rather than being killed mid-answer. When no notebook is running the hostname does
not answer, the fetch throws, and `think()` counts the lane as tried and moves on to the next
one — which is exactly what a lifeboat is supposed to do with a lane that is not there.
Re-launching on a cadence is the scheduler's job, not a loop inside this file: the estate has
one scheduler and it is Dagster.
