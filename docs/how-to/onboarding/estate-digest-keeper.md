# Onboarding: estate-digest-keeper

## What it is

`bin/estate-digest-keeper` keeps the estate's free local model resident and
proves the tier is alive. It is slot 7 in the seven-agent local ops tier
(crew#929, roster in `docs/ops/local-ops-tier-roster.md`), and every other
worker depends on it to start warm.

## Why it exists

A local 7B that has sat idle for five minutes is unloaded by Ollama, and the
next worker pays a cold reload before doing anything. That reload measured
30.8 s cold versus 16.9 s warm on the reference hardware, and during the
consensus-vote work it cost a voting deadline. The keeper removes that tax:
it is the always-on heartbeat that makes an "always-warm free tier" a true
claim rather than a hopeful one.

## What it needs

A host with Ollama serving `qwen2.5-coder:7b`. Override the model and endpoint
with `ESTATE_DIGEST_MODEL` and `ESTATE_OLLAMA`.

## The commands

- No argument (default): a one-shot liveness check that prints `ALIVE:<epoch>`
  only when the model answered a real minimal generation, else FAIL and a
  non-zero exit.
- `--load`: issue one small generation to load the weights and keep them warm.
- `--loop N`: repeat the liveness check every N seconds (default 300) until
  stopped, for a cron/background heartbeat.

## The contract

Liveness is measured, never assumed. A FAIL on an unreachable or cold model is
an honest failure state, and the worker never fabricates a green value in
place of an answer. Run it as a scheduled heartbeat so the rest of the ops
tier wakes into a warm model instead of a cold-start bet.
