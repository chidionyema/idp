# The anticipatory router — it already knows before the request arrives
**Status: APPROVED — 2026-10-01.** Founder: "the router should be preprobing super early and keep a
rolling registry, fallback is late … it should already know what to do before a request comes in."

The estate router (LiteLLM, `bin/litellm-local` on the laptop, `platform/llm/litellm.yaml` on the
cluster) works things out **on the request path, after the fact**. This spec moves every decision
off the request path. When a request lands, the router does a lookup; the thinking was done
earlier, continuously, against measurements it already holds.

---

## 1. What was measured on 2026-10-01 (the failures this replaces)

| Failure | Measured | Source |
|---|---|---|
| Late fallback | a lane must fail **3 real requests** before a 60 s cooldown (`allowed_fails: 3`, `cooldown_time: 60`) | `platform/llm/config.local.yaml` router_settings |
| Nothing probes ahead | `background_health_checks: false`; `bin/idp-router-lanes` probes, but only into a snapshot no routing decision reads | same; `bin/idp-router-lanes` |
| Compaction fold dead | **254 / 256** shadow folds failed: 123 × `402 Payment Required`, 110 × `429`, 21 × timeout, 2 ok | `~/.estate/efficiency-ledger.jsonl`, last 4,000 rows |
| Session never compacted | Claude Code session at 349,738 → 353,314 est. tokens, `m7=none`, `state_chars=0` | same ledger, 19:39–19:40Z |
| Ceiling interrupts work | 200k refusal returned as an assistant *message*, so Claude Code ended the turn instead of compacting | `platform/llm/request_ceiling.py:143` |
| Holdout has no safety | 1,143 / 1,881 calls in the 25 % `control` arm, which gets no compaction at all | ledger `arm` field; `ESTATE_HOLDOUT_PCT=25` |
| Dead vendor surfaced to the caller | pi → `moonshot/kimi-k3`: `429 … account suspended due to insufficient balance`, *"No fallback model group found"*, retried 2× then failed to the user | founder paste, 2026-10-01 |

The kimi case is the whole problem in one line: the account had been out of balance long before
that request, the router did not know, it spent two retries finding out, and it had nowhere to send
the work because a raw vendor model group has no fallback chain.

---

## 2. The shape

```
            continuously, off the request path                      on the request path
 ┌───────────────────────────────────────────────────────┐   ┌──────────────────────────────┐
 │ probes ─┐                                             │   │ request ─► classify (cached) │
 │ every   ├─► LANE REGISTRY ─► ROUTE TABLE (compiled) ──┼──►│        ─► table lookup       │
 │ real    │   state, quota,      class → ordered lanes  │   │        ─► compaction lookup  │
 │ call ───┘   forecast, caps     + compaction strategy  │   │        ─► send               │
 │ session trajectories ─► PRE-BUILT COMPACTION STATE ───┼──►│   (no network, no reasoning) │
 └───────────────────────────────────────────────────────┘   └──────────────────────────────┘
                       │  every transition streamed (JetStream) ─► /fleet, voice
```

Four parts, built in this order. Each is done only when /fleet shows it deciding on real traffic.

### 2.1 Lane registry — always warm

One record per **deployment** (not per alias), held in the router process and written atomically to
`~/.estate/router/lanes.json`, every transition appended to `~/.estate/router/lanes.jsonl`.

* **Passive measurement, free.** Every real call already is a probe. Success and failure callbacks
  record latency, status, error class and the vendor's own rate-limit headers
  (`x-ratelimit-remaining-{requests,tokens}`, `…-reset-*`, `retry-after`).
* **Active probes, only where passive data is stale.** One-token calls through the router's own
  deployment params, in parallel, cadence by state: a `ready` lane with fresh traffic is not probed;
  an idle one every 60 s; a `cooling` one at its reset time; a `dead` one every 10 min (it rejoins
  the moment credit returns — no person flips it back).
* **Error classes are facts, not counts.** `insufficient balance` / `402` / `suspended` → `dead`
  (credit) until a probe answers; `401/403` → `dead` (auth); `429` with a reset → `exhausted` until
  that reset; timeout → `degraded`. One observation is enough — the router never re-learns a fact by
  failing three more user requests.
* **Forecast.** Remaining quota ÷ recent consumption rate = time to exhaustion. A lane forecast to
  exhaust inside the probe interval is drained (`draining`) *before* it returns a 429.
* **Capabilities** per deployment: context window, tools, prompt caching, native compaction
  (Anthropic `compact_20260112` / context editing), cost per token, latency p50/p95.
* **Billing model** per deployment: `metered` or `subscription`. A subscription lane (the Kimi and
  GLM monthly plans) costs nothing per extra call until its plan window's limit, so the route table
  ranks it ahead of metered paid lanes and the forecast drains it before the limit. A
  pay-as-you-go account and a subscription for the same vendor are separate deployments; one being
  dead says nothing about the other.

### 2.2 Route table — compiled, not computed

Recompiled on every registry transition, never on a request. For each **request class** (2.3) an
ordered list of healthy deployments that hold that class's needs, ranked cost-first then latency,
plus that class's compaction strategy (2.4). On the request path two LiteLLM hooks read it from
memory:

* `async_filter_deployments` drops every deployment the registry holds not `ready`/`degraded` —
  the 3-strikes cooldown never has to fire.
* `async_pre_call_hook`: when a requested model group has **no** ready deployment (the kimi case),
  the request is served on the table's first lane for its class, and the response carries
  `x-estate-served-by` so the substitution is never silent. Aliases remain LiteLLM's; LAW 34 holds —
  no vendor name is written into code, the table is built from the live model list.

### 2.3 Pre-classification — decided on the first turns, then cached

Class per session, from what is already in the request: client (Claude Code / pi / opencode /
voice), key, session id, tool set, first-turn shape. Classes: `interactive-code`,
`voice-realtime` (latency-first), `bulk`, `background-fold`. Each request does a dict lookup.
Per session the router also keeps the **trajectory**: tokens per turn and growth rate, so it knows
*when* this session will reach the compaction setpoint.

### 2.4 Compaction prepared ahead — the ceiling never fires

Context size is a controlled variable with a setpoint (`ESTATE_EPOCH_TOKENS`). From the trajectory
the router schedules the fold **ahead of need**, on the lanes the registry shows have spare free
quota at that moment (a fold is a `background-fold` request routed by the same table — no model
named in the compactor). When the session crosses the setpoint the snap is a lookup.

Per-lane strategy is in the table, in this order, and the last always succeeds:

1. **native** — the vendor's own compaction where the lane has it (the sanctioned history edit on
   Anthropic lanes; preserved thinking stays valid);
2. **fold** — the shadow-state summary, checkpointed per chunk so partial progress counts;
3. **deterministic** — no model: superseded tool results cleared, old tool calls stubbed, last turns
   verbatim, under the existing hash lock so the prefix stays cache-stable.

The holdout arm withholds only the optimisations under trial; the regulator applies to every session.
`request_ceiling.py` stays as an interlock: it answers with the vendor-native
`prompt is too long` 400 (which Claude Code compacts on and continues), and every firing is an
incident on /fleet — it means 2.4 failed.

---

## 3. Seen and spoken

Registry, route table, per-session pressure and forecast, and every transition (`kimi → dead:credit`,
`groq-2 → draining, exhausts in 40 s`, `session 7f… folded ahead at 61k`) stream on the estate bus to
/fleet. Voice: "which lanes are down", "why was my request served by groq".

## 4. Done means

1. **Registry:** /fleet shows a lane go `dead` from a probe, with no user request having failed on it.
2. **Route table:** a request to a dead group is served elsewhere, `x-estate-served-by` set, ledger row.
3. **Classification:** every ledger `pre` row carries a class; voice sessions route latency-first.
4. **Compaction:** a real session passes the setpoint, compacts, and the ceiling's firing count stays 0.
