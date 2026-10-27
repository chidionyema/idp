# The estate's LLM spend is cut at the router, on the cloud route, and every saving is measured

**Date:** 2026-10-26
**Status:** accepted (founder, 2026-10-26 — "the decision record is solid")
**Receipt:** [idp#7248 — the founder's ruling](https://github.com/chidionyema/idp/issues/7248#issuecomment-6430382067)
**Issue:** #7248
**Spec:** [`docs/specs/2026-10-26-the-estate-llm-spend-floor.md`](../specs/2026-10-26-the-estate-llm-spend-floor.md)
**Diagnosis:** [`docs/diagnoses/2026-10-26-where-the-estates-llm-spend-actually-goes.yaml`](../diagnoses/2026-10-26-where-the-estates-llm-spend-actually-goes.yaml) — H1 at posterior **0.996**

## The problem

The estate's LLM bill was measured on 2026-10-26 from the estate gateway ledger
(`~/.estate/efficiency-ledger.jsonl`, the 24 hours ending 19:30Z): **8,009 calls, $29.36,
137.97M billed input tokens, 4.95M output tokens.** Over 7 days: 27,962 calls, $77.68.
**Scope, measured 2026-10-27:** that ledger records the **laptop route's** calls — the client's
`estate` provider points at `http://127.0.0.1:4000/v1` and the laptop router is the process
that writes the file — while the cloud route meters through the cluster's cloud keys and is
invisible to it. The two are never added together. It is the estate's whole model bill today
only because the client still runs through the laptop; after the flip the same traffic is metered
on the cloud route, where the ledger of record is the cloud's own postgres.
`AGENTS.md` declares a daily litellm budget of **$3.00**. The estate spent **9.8×** that, and
nothing stopped it: the running laptop router carries `max_budget: 5.0` and **no
`database_url`**, so LiteLLM cannot enforce a budget and the refusal that was configured never
fired.

Three explanations competed for the bill — one pinned paid lane, repeated context, and calls
that never needed a frontier model — and the Bayesian record puts the first at **0.996**. The
mechanism is not subtle:

- the client pins the lane (`settings.json` and `~/.pi/agent/settings.json` both carry
  `defaultModel: minimax_m27`), and that lane carries **71.7%** of the money;
- `minimax_m27` is the **only** paid group in the router's fallbacks map with **no entry at
  all**, while its sibling `minimax` already falls back to `minimax_m31f` — the same family's
  **half-price** lane — which is configured, priced and served **zero calls**;
- every one of the 8,009 billed calls is an `acompletion`. There is no batch, embedding or
  scheduled traffic in the bill, so the off-peak rung of the funnel has nothing to price.

## The decision

**The bill is cut at the router, on the cloud route, in a fixed order, and every move is
measured before it is claimed.**

1. **Measure first.** `estate-execute cost-today` must answer 200 against the cloud route, its
   figure must match the ledger's per-call sum within 5%, and a key with a real `max_budget`
   must be observed refusing traffic that exceeds it. A saving nobody can read is not a saving.
2. **Unpin the lane that carries 72% of the bill.** The client stops pinning a leaf lane, or
   `minimax_m27` gets the fallback chain its sibling already has. Expected **≈ $10.50/day**
   (35.9% of the bill), against a quality gate — a fixed probe set, agreement measured the way
   the forge measures agreement, no lane allowed below the current baseline. Two preconditions,
   both measured: the half-price lane `minimax_m31f` is in **no file in this repository** (it
   exists only in the laptop router's own config, so a re-render drops it), and the cloud key's
   allowlist — 29 ids, read from `GET /v1/models` — does **not** carry it, so the default route
   answers `403` for it. The saving lands on the route that will carry the traffic only once
   the lane is versioned and the allowlist extended.
3. **Every paid group ends on a free lane.** The fallbacks map gains the entries it is missing
   and terminates in `groq` → `cerebras` → `sambanova` → `nvidia` → `openrouter`, with the OKE
   free floor (`platform/llm/ollama.yaml`, ladder rung 0) at the bottom for code-shaped work.
   Target **≥ 1,600 calls/day at $0.00** (today 156), worth ≈ $5.66/day inside the allowance.
4. **Answer cache on the route that spends.** 85.68M prompt tokens a day went uncached — 14% of
   the 608.56M the estate sent, but 62% of the 137.97M billed input tokens, because a cache read
   is billed at a tenth of a fresh token. The route that spends carries no cache block at all
   while the cloud config already has `cache: redis, ttl 300`. The semantic tier is built on the
   **memory server's existing embeddings** — one store, one writer, no new cache service. Version 1
   answers only read-only, state-independent questions, and every answer carries its source.
   Target ≥15% of calls, ≈ $4.40/day.
5. **Stop calling for the repeatable work.** The ledger must name the top callers by spend
   (today `session` is `-` on every agent-loop row — re-measured 2026-10-27: one distinct session
   value across 5,518 calls — so this share cannot even be named), and
   CI's graded suites must make zero live model calls through the cassette that already exists.
6. **The distilled local floor is the long rung, not the first.** Ladder rung 2 is $69/month
   against a measured $881/month of metered spend, so it pays at **≥ 7.8% absorption** — but the
   forge's export seam refuses and the rung's price is founder-supplied-unverified. It activates
   after the routing and cache rungs, and never on an unchecked price.

**The floor this aims at: $10.00/day, within 30 days, at unchanged traffic and unchanged
quality** — a 66% cut, ≈ $580/month, with no new paid infrastructure.

## What this rules out

- **A parallel spend ledger.** The cloud route's postgres is the ledger of record; the laptop
  route stays the fallback, and laptop calls (which bill vendors directly) and cloud calls
  (metered through cloud keys) are never added together.
- **A parallel cache.** The router's redis plus the memory server's embeddings, or nothing.
- **A parallel distillation framework.** The forge owns distillation; this asks it to export.
- **A new scheduler.** There is no non-interactive traffic to schedule. Adding one would be a
  layer with no traffic — the same defect the diagnosis just found.
- **A laptop-first architecture.** `https://llm.${ESTATE_ZONE}` stays the default and the
  laptop the fallback (the law, #7247). Every rung is designed for the cloud route, because the
  cloud route owns postgres, redis and the cloud credentials — and, after the flip, the traffic.
- **Free tiers as free.** Measured: `groq` carried 1,310 calls at **$0.00 in 24 hours** and
  **$2.45 over 7 days** — a lane that is free only inside its allowance. A free lane is free only
  inside its allowance, so the metric is the rate, never the label.

## Consequences

- The estate's daily LLM spend becomes a number with a floor and a ratchet instead of a
  surprise, and it lands under the declared budget instead of at 9.8× it.
- A probe set and an agreement floor become part of the estate's model-change contract: the
  price of a lane is no longer a line in a YAML file, it is a measured exchange rate against
  quality.
- The cache becomes a correctness surface, so it is scoped to read-only questions and carries
  its source. A cache that answers a write with a stale answer is worse than a bill.
- The measurement moves with the traffic: after the flip to the cloud route (#7078), the cloud's
  own key/info and postgres are the ledger, and the laptop ledger goes quiet. Rung 1 therefore
  lands before the flip, not after it.

## What would falsify this

- If the probe agreement of `minimax_m31f` (or any replacement lane) falls below the current
  lane's baseline, rung 2's saving is not available and the floor must be re-derived.
- If the half-price lane cannot be versioned and allowlisted on the cloud route, rung 2's saving
  does not exist on the default route at all, and the floor must be re-derived from the
  allowlisted lanes alone.
- If the free-tier allowance cannot carry the repeatable share, rung 3's saving collapses to
  the metered rate and the floor moves up.
- If, after the flip, the cloud route's per-call `cost_usd` cannot be read back from the
  ledger, the measurement contract is broken and no rung can be claimed as done.

---

*Measured 2026-10-26. Reproduce with the command in the spec's §8.*
