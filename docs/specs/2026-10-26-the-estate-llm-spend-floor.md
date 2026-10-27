# The estate's LLM spend floor

**Status:** accepted (founder, 2026-10-26 — "the decision record is solid") · the design is
accepted; the rungs in §5 are not yet implemented
**Receipt:** [idp#7248 — the founder's ruling](https://github.com/chidionyema/idp/issues/7248#issuecomment-6430382067)
**Issue:** #7248 (the claim of record)
**Diagnosis:** [`docs/diagnoses/2026-10-26-where-the-estates-llm-spend-actually-goes.yaml`](../../diagnoses/2026-10-26-where-the-estates-llm-spend-actually-goes.yaml) — H1 wins at posterior **0.996**
**Decision:** [`docs/decisions/2026-10-26-the-llm-spend-is-cut-at-the-router-on-the-cloud-route.md`](../../decisions/2026-10-26-the-llm-spend-is-cut-at-the-router-on-the-cloud-route.md)

---

## 1. The bill, measured

Every number in this document comes from one file — the estate gateway ledger
`~/.estate/efficiency-ledger.jsonl` — read over the 24 hours ending 2026-10-26T19:30Z. The
measurement is reproducible; the command is in §8.

### 1.1 Last 24 hours

| lane | calls | spend | share | billed input | uncached input | output | token cache hit | avg latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `minimax_m27` | 5,819 | **$21.06** | **71.7%** | 97.17M | 54.02M | 4.04M | 88.9% | 17.7 s |
| `deepseek-v4-flash` | 1,613 | $5.66 | 19.3% | 23.65M | 14.52M | 0.66M | 86.3% | 5.5 s |
| `zai/glm-5.3-flash` | 293 | $2.64 | 9.0% | 17.05M | 17.05M | 0.09M | 0.0% | 41.2 s |
| `voice` | 125 | $0.01 | 0.0% | 0.03M | 0.02M | 0.00M | 80.1% | 2.5 s |
| `groq` (free tier) | 156 | $0.00 | 0.0% | 0.07M | 0.07M | 0.16M | 3.4% | 28.0 s |
| **total** | **8,009** | **$29.36** | | **137.97M** | **85.68M** | **4.95M** | **85.9%** | |

Cost per call: **$0.00367**. Cost per 1M billed input tokens: **$0.213**.

### 1.2 Last 7 days

27,962 calls, **$77.68**. `minimax_m27` $48.12 (62.0%), `deepseek-v4-flash` $18.60 (23.9%),
`zai/glm-5.3-flash` $7.01 (9.0%), `groq` $2.45 (3.2% — this is the free tier's allowance running
out and metering), `minimax` $1.09, `cerebras` $0.18, `deepseek` $0.12, `voice` $0.08.
Everything else rounds to zero.

### 1.3 Where it concentrates

The bill is not one runaway agent. It is 8,009 calls spread over 169 conversations:

- top 10 conversations carry **$16.34 of $29.36 (55.7%)**;
- top 25 carry 78.7%; top 50 carry 95.6%;
- the top 1% of calls carry 13.5% of spend; the top 10% of calls carry 65.5%.

So the cost is in the *shape of the traffic* — long agent loops, each re-sending its context — and
not in a single bug.

### 1.4 Every billed call is an agent completion

All 8,009 billed calls in the window carry `call_type=acompletion`. There is no embedding, image,
batch or scheduled traffic in the bill at all. Two consequences, both load-bearing later:

- **There is no non-interactive workload to move off-peak.** Off-peak pricing has no traffic to
  price. The batch/off-peak rung of the funnel is real but empty today.
- **The lever is the model serving the agent loop, and the context it re-sends.** Nothing else
  moves 72% of the money.

### 1.5 The estate is over its own declared budget, and nothing enforces it

`AGENTS.md` declares `[budget.usd_per_day] litellm = 3.0`. The measured bill is **$29.36/day —
9.8× the declared budget**. It is not enforced because the route that spends cannot enforce it:
the running laptop router config (`~/.estate/router-state/config.runtime.yaml`) carries
`max_budget: 5.0` / `budget_duration: 1d` and **no `database_url`**. LiteLLM cannot enforce a
budget without a spend database, so the refusal that was configured never fired: the router
spent **$29.36 against a $5.00 ceiling** — nearly six times the budget the router was carrying.

---

## 2. The diagnosis: it is a routing decision, not a traffic accident

Three explanations competed for the bill, fixed before the numbers were read
([record](../../diagnoses/2026-10-26-where-the-estates-llm-spend-actually-goes.yaml)):

| | explanation | posterior |
|---|---|---:|
| **H1** | one pinned paid lane carries the bill; the largest saving is a routing change | **0.996** |
| H2 | the bill is repeated context; the largest saving is an answer cache | 0.003 |
| H3 | the bill is calls that never needed a frontier model; the largest saving is refusing them | 0.001 |

H1 wins by two orders of magnitude, and the mechanism is concrete:

- the client pins the lane. `settings.json` and `~/.pi/agent/settings.json` both carry
  `defaultModel: minimax_m27`;
- that lane is the **only** paid group in the router's fallbacks map with **no entry at all** —
  while its sibling group `minimax` already falls back to `minimax_m31f`, the *same family's
  half-price lane*, and `deepseek-v4-flash` already falls back through `minimax` to `groq`;
- `minimax_m31f` ($0.15/M in, $0.60/M out) is configured, priced and served **zero calls**.

One line of routing policy, already half-written by a previous change, would halve the biggest
line on the bill — **but not on the default route yet.** Measured 2026-10-26:

- the half-price lane lives only in the **laptop** router's own config
  (`~/.estate/litellm-local/config.yaml`: the lane at line 157, the chain `minimax:
  [minimax_m31f, gemini, groq]` at line 730). It is in **no file in this repository** —
  not `llm/config.yaml`, not `platform/llm/config.base.yaml`, not
  `platform/vendors/consoles.yaml` — so it does not exist on the cloud route, and a re-render
  drops it from the laptop;
- the cloud router's allowlist (`GET /v1/models` on `https://llm.${ESTATE_ZONE}`, measured:
  **29 model ids**) does **not** carry `minimax_m31f`; a request for it answers `403 key not
  allowed to access model`;
- the cloud route's own fallbacks map has the same hole as the laptop's: `minimax: [gemini,
  groq]`, and **no `minimax_m27` entry**.

So the saving has two preconditions before it can live on the route that will carry the
traffic: **version the lane** (one render fixes the laptop and the cluster together) and
**extend the cloud key's allowlist** to carry it.

---

## 3. The proposed funnel, mapped onto what the estate already owns

The funnel under review was: semantic cache → local distilled model → free-tier fleet →
batch/off-peak frontier → interactive frontier. Mapped onto the estate:

| funnel rung | what it means here | does it exist? | where | verdict |
|---|---|---|---|---|
| **semantic cache** | answer a repeated question without a call | **no** — the prefix cache is already 85.9% effective on tokens, but there is no *answer* cache anywhere | the cloud config has `cache: redis, ttl 300`; the laptop route that spends has **no cache block at all** | **build it once, on the cloud route, on the memory server's existing embeddings** |
| **local distilled model** | serve the cheap share from a model the estate owns | the machinery exists; the export does not | `forge` distillation; ladder rung 2 (`$69/mo`, grade `founder-supplied-unverified`) | **long rung** — pays only at ≥7.8% absorption (§4.3); not a 30-day lever |
| **free-tier fleet** | serve within a free allowance | **yes, mostly** | `groq` / `cerebras` / `sambanova` / `nvidia` / `openrouter` lanes (all `gpt-oss-120b` or nemotron); ladder rung 0 `local_free` on the OCI A1 pool (`platform/llm/ollama.yaml`) | **wire it into the fallback chains**; the OKE free floor is being revived under #7205 |
| **batch/off-peak frontier** | schedule non-interactive work into cheap windows | **no traffic** | §1.4: 100% `acompletion` | **not a lever today** — revisit when non-interactive traffic appears |
| **interactive frontier** | the model that answers the agent | **yes, and it is pinned** | `minimax_m27` (72%), `deepseek-v4-flash` (19%), `zai/glm-5.3-flash` (9%) | **the lever**: unpin, then fall back down the price ladder |

Three of the five rungs need no new layer. Two need one each: an answer cache (built on the
memory server that already stores embeddings) and the distillation export (already the forge's
job). Neither is a new product.

---

## 4. The floor: the physics of this traffic

### 4.1 What the same traffic costs at each lane's own list price

The measured traffic is 137.97M billed input tokens and 4.95M output tokens per 24 hours. Priced
at the router's own table (`llm/config.yaml`):

| lane | in $/M | out $/M | this traffic, per day | per month |
|---|---:|---:|---:|---:|
| `minimax_m27` (today's pin) | 0.30 | 1.20 | $47.33 | $1,420 |
| `minimax_m31f` | 0.15 | 0.60 | $23.67 | $710 |
| `deepseek` | 0.14 | 0.28 | $20.70 | $621 |
| a free lane (`groq`/`cerebras`/`sambanova`/`nvidia`) | 0 | 0 | **$0** inside the allowance | $0 |

Measured actual is **$29.36/day** — the prefix cache already pays **38% off** the `minimax_m27`
list-price equivalent. The floor for this traffic is therefore **$0/day (all free, inside the
allowance) to $20.70/day (cheapest paid lane at list)**.

### 4.2 The target

**$10.00/day or less, within 30 days, at unchanged traffic and unchanged quality.** That is a
66% cut, ≈ $580/month saved at the measured rate, and it is reachable without any new paid
infrastructure: half of it is one routing change (§5, R1).

### 4.3 Why the distilled local model is not the 30-day lever

Ladder rung 2 is `$69.00/month` (`platform/llm/cost-ladder.yaml`, grade
`founder-supplied-unverified`). At the measured $29.36/day = **$881/month** of metered spend, a
$69/month flat-rate box pays for itself if it absorbs **≥ 7.8%** of the traffic. That is a real
threshold, and it is cheap to clear — but only if the distillation export works, and today the
forge's export seam **refuses**, and the ladder's own grade for the rung is unverified. So the
honest position is: rung 2 is cheap and worth doing *after* the routing and cache rungs, not
before, and it must not be activated on the strength of a price that has never been checked
against the vendor's page.

---

## 5. The sequence

Each rung names the lever, who already owns it, the precondition, the expected saving (arithmetic
from the measured baseline, not a promise), the acceptance measure, and the risk. Rungs run in
order: **a saving nobody can measure is a saving nobody can keep.**

### R0 — Make the bill readable (before any saving is claimed)

- **Problem:** the spend door answers `401` (`$ESTATE_AGENT_KEY` is empty and the vault copy
  decrypts to a redacted placeholder); the route that spends has no spend database, so its
  `max_budget` is inert; the cluster ledger records nothing because its mounted key is a stub.
- **Lever:** the cloud route's own postgres (the cluster already composes `DATABASE_URL` in
  `platform/llm/litellm.yaml`), a working agent key by name, and the cluster action ledger.
- **Owns it:** #7081 (cluster router captures graph + signs the ledger), #7097 (lane inventory
  and Catalog Phase 0), the `cost-today` / `ledger-verify` intents, and `bin/idp-spend-floor` —
  the estate's existing per-key floor, which already reads the cluster's LiteLLM postgres and
  reports each key's window spend, its lifetime spend against `max_budget`, and the shape a
  total cannot see. R0 repairs what that tool reads; it does not write a second reporter.
- **Acceptance:** `estate-execute cost-today` answers 200 with a spend figure; the daily spend it
  reports equals the sum of per-call `cost_usd` in the ledger **within 5%**; a key with a
  `max_budget` of $5/day **refuses** traffic that exceeds it (a refusal that can be observed, not
  a number in a file); and `bin/idp-spend-floor` grades the cloud route's keys on that ledger
  without refusing to run for want of a password.
- **Saving:** $0 — this rung buys the ability to prove every later rung.

### R1 — Unpin the lane that carries 72% of the bill

- **Problem:** `minimax_m27` is pinned by the client and has no fallback entry, while
  `minimax_m31f` — the same family's half-price lane — sits configured, priced and unused.
- **Lever:** the client stops pinning a leaf lane (or the router gives `minimax_m27` the fallback
  chain its sibling already has: `minimax_m31f` → `gemini` → `groq`).
- **Owns it:** #6785 (add the `minimax_m31f` lane and fall back to it from `minimax`) — the lane
  exists; the missing piece is the pin and the fallback entry, which is this rung. That claim's
  heartbeat lapsed on 2026-10-21, so the files are free to re-claim.
- **Preconditions (measured 2026-10-26, both on the default route):** (a) **version the lane** —
  `minimax_m31f` is in no file in this repository, so it exists only in the laptop router's own
  config and a re-render drops it; one entry in the vendor registry
  (`platform/vendors/consoles.yaml`) gives both the laptop and the cluster the lane; (b)
  **extend the cloud key's model allowlist** — the allowlist is a key policy in the cluster's
  LiteLLM database (no file here holds it) and it does not carry `minimax_m31f` today.
- **Expected saving:** **≈ $10.50/day** (half of the pinned lane's measured $21.06) — **35.9% of
  the bill**, the single largest move available, **once the two preconditions hold**; on the
  laptop route alone the saving is available today, on the cloud route only after them.
- **Acceptance:** 7-day rolling spend on the pinned lane ≤ **$12** (today: $48.12) **while** the
  7-day call count moves by less than ±10% (so the traffic did not simply stop) **and** the
  quality probe below holds **and** `GET /v1/models` on the cloud route lists every lane the
  chain names — and the before/after pair (the pinned lane's 7-day spend and call count, then
  the same two numbers on the new lane) lands through `bin/idp-cost-proof`, which refuses a
  cost-touching change whose body carries no measurement command.
- **Quality gate (non-negotiable):** a fixed probe set (≥100 prompts spanning code edit, refactor,
  explanation, tool use) run through both the old and the new lane; agreement measured the way
  the forge measures agreement; **agreement must not fall below the current lane's baseline**, and
  any lane that fails goes to a fallback, not to the client.
- **Risk:** a quality regression on the agent loop is invisible in the bill and expensive in the
  work. Mitigation: the probe gate above, and the fallback chain means a bad lane is *out*, not
  *in*.

### R2 — Every paid group ends on a free lane

- **Problem:** the fallbacks map covers `deepseek`, `deepseek-v4-flash`, `minimax`, `gemini`,
  `default`, `fast`, `groq`, `voice`, `narrate`, `cerebras`, `sambanova` — but not `minimax_m27`,
  not `minimax_m31f`, not `zai/glm-5.3-flash`, not `voice-tts-minimax`. The lanes that can fail
  open into nothing are the ones the traffic lands on.
- **Lever:** complete the map so every paid group has a chain that ends on a free lane
  (`groq` → `cerebras` → `sambanova` → `nvidia` → `openrouter`), and put the OKE free floor
  (rung 0, `platform/llm/ollama.yaml`) at the bottom for code-shaped work.
- **Owns it:** `platform/llm/routing-matrix.yaml` + `route_table.py` (the estate's own routing
  contract); #7205 (revive the free floor on local-path); #6872 (a `claude-*` lane on the cluster
  so Claude Code survives failover — a subscription lane, measured at $0.00 over 7 days across
  2,080 calls).
- **Acceptance:** the routing matrix proves every paid group resolves to a free lane; a
  fault-injection test (kill the primary lane) shows the call served at $0.00 and the ledger
  recording the substituted lane; and `GET /v1/models` on the cloud route lists **every** lane
  the chains name — a chain that names a lane the key cannot call is a guaranteed refusal, which
  is the defect this rung exists to remove.
- **Expected saving:** the share of traffic that can be served free — target **≥ 1,600 calls/day
  at $0.00** (today 156), which is the `deepseek-v4-flash` share of the bill: **$5.66/day** if
  the allowance holds.
- **Risk:** free tiers meter past their allowance — measured: `groq` served 1,310 calls at **$0.00
  in 24 hours** and **$2.45 over 7 days**. The chain must therefore treat metered fallbacks as
  a last resort, and the acceptance measure is the *rate*, not the label.

### R3 — Answer cache on the route that spends

- **Problem:** 85.68M prompt tokens per day went **uncached** — 14% of the 608.56M the estate sent,
  but **62% of the 137.97M billed input tokens**, because a cache read is billed at a tenth of a
  fresh token. The route that spends carries **no cache block at all** — the cloud config has
  `cache: {type: redis, ttl: 300}` and the laptop route has none.
- **Lever:** (a) turn on the existing exact-match cache on whichever route is primary; (b) add the
  **semantic** tier on top, using the embeddings the memory server already computes for recall —
  one store, one writer, no new cache service.
- **Owns it:** `platform/llm/config.base.yaml` (cache block) and the unified memory server
  (`platform/llm/active_memory.py`, `platform/estate/memory`); the cloud route's redis.
- **Expected saving:** at a **15% call hit rate**, **≈ $4.40/day**.
- **Acceptance:** ≥15% of calls answered from cache, measured as ledger rows with
  `cache_source=answer`; the saved spend equals the hit count × the lane's measured cost per call.
- **Correctness (the reason this rung is scoped narrowly):** a cache that answers a *write* or a
  state-dependent question with a stale answer is worse than a bill. **Version 1 answers only
  read-only, tool-state-independent questions**; every answer carries the model, the prompt hash
  and the source commit it was derived from, so a stale hit is detectable. A write, a tool call
  and anything that reads mutable state are never cached.

### R4 — Stop calling for the repeatable work

- **Problem:** the estate's graded suites and graders call live models; `platform/llm/cassette.py`
  exists for exactly this and is **off by default** (`ESTATE_CASSETTE_MODE=off`). The ledger
  attributes calls to conversations but **not** to callers (`session` is `-` on every agent-loop
  row), so the size of this share cannot even be named today.
- **Lever:** (a) attribute callers in the ledger (session/agent id), (b) switch the repeatable
  suites to cassette replay, (c) route the repeatable share to the free fleet (R2).
- **Owns it:** `platform/llm/cassette.py`, `bin/prm_grader.py`, `bin/idp-prm`,
  `bin/redteam_promoter/promoter.py` — the estate's own list of live callers.
- **Acceptance:** the ledger names the top callers by spend (the measurement exists before the
  saving is claimed), and CI's graded suites make **zero live model calls** (cassette on, verified
  by the ledger showing no CI conversation ids).
- **Expected saving:** stated as a target after R0's attribution exists — deliberately not
  estimated here, because an unmeasured share cannot be promised.

### R5 — The distilled local floor (the long rung)

- **Problem:** the forge's distillation export seam refuses; ladder rung 2's price is
  founder-supplied-unverified.
- **Lever:** make the export work; serve the cheap share from a distilled local model on the
  OCI A1 pool (rung 0) or an Apple Silicon tier (rung 2).
- **Acceptance:** the export produces a loadable model **and** the ladder's own breakeven band
  is computed against the measured traffic — no activation before the price is verified against
  the vendor's page (the ladder's own ACCEPT line calls rung 2 a proposal, never an automatic
  activation).
- **Expected saving:** $0 today; the rung becomes worth activating once R1–R3 have lowered the
  metered spend enough for the $69/month to clear its threshold.

### Order and dependency

```
R0 (make it measurable)
  └─ R1 (unpin: -$10.50/day)  ─┐
  └─ R2 (free floor in the chain) ─┼─ these three are independent and can run in parallel
  └─ R3 (answer cache: -$4.40/day) ─┘
        └─ R4 (attribute, replay)
              └─ R5 (distilled local floor, once the export works)
```

R0 first, because every acceptance measure in R1–R4 is a number read off the ledger or the
spend door, and neither is trustworthy until the spend door answers.

---

## 6. What this design refuses

One of each layer, estate-wide:

- **No new cache service.** The semantic tier is built on the memory server's existing
  embeddings; the exact-match tier is the router's existing redis block. One store, one writer.
- **No new spend ledger.** The cluster's postgres is the ledger; the laptop route stays the
  fallback route, and the two are never double-counted (laptop calls bill vendors directly, cloud
  calls are metered through cloud keys).
- **No new spend reporter.** `bin/idp-spend-floor` already grades every key against its budget
  and reports the shape a total cannot see — the biggest single call and the input:output ratio —
  and it reads the cloud route's own postgres. R0 makes it answer; it does not replace it, and
  `platform/llm/spend-breaker-digest.yaml` stays the hourly totals breaker it already is.
- **No new cost-proof gate.** `bin/idp-cost-proof` already refuses a cost-touching change whose
  body carries no before/after pair and no command to re-take it. R1's evidence lands through
  that gate; this design adds no second one.
- **No new distillation framework.** The forge owns distillation; this design only asks it to
  export.
- **No new scheduler.** There is no non-interactive traffic to schedule; adding one would be a
  layer with no traffic.
- **No paid infrastructure.** Rungs 2 and 3 of the cost ladder need a verified price and a
  receipt before activation; this design activates neither.
- **No laptop-first architecture.** `https://llm.${ESTATE_ZONE}` stays the default route and the
  laptop stays the fallback (the law, landed in #7247). Every rung above is designed for the
  cloud route, because the cloud route is the one that owns postgres, redis and the cloud
  credentials — and, after the flip, the one that will carry the traffic.

---

## 7. Risks, and the ones this design cannot dodge

| risk | why it is real here | what the design does about it |
|---|---|---|
| **Quality regression** from moving the pinned lane | the bill measures tokens, not correctness | a probe set with an agreement floor (R1); a bad lane falls back, it is never pinned |
| **The half-price lane is not on the default route** | measured: `minimax_m31f` is in no file in this repository, and the cloud key's allowlist (29 ids) does not carry it — a chain that names it answers `403` | R1 versions the lane and extends the allowlist **before** the saving is claimed; the acceptance measure includes the allowlist listing |
| **Free-tier exhaustion** | measured: `groq` carried 1,310 calls for **$0.00 in 24 hours** and **$2.45 over 7 days** — a lane that is free only inside its allowance | free lanes are counted as free only *inside* the allowance; metered fallbacks are last; the metric is the rate, not the label |
| **The measurement moves with the traffic** | after the flip, the cloud route carries the calls; the laptop ledger stops | R0 makes the cloud route's own key/info and postgres the ledger of record before the flip |
| **A stale cache answers wrongly** | the 85.68M uncached prompt tokens a day are exactly what a cache would swallow | version 1 caches read-only, state-independent questions only; every answer carries its source |
| **Latency regression** | measured: `minimax_m27` 17.7 s, `deepseek-v4-flash` 5.5 s, `zai/glm-5.3-flash` 41.2 s, `groq` 28.0 s | the probe gate measures latency as well as agreement; the fallback chain prefers the lane that is actually faster, not the one that is nominally cheaper |
| **The bill is diffuse** | 169 conversations, top 10 = 55.7% | there is no single switch to flip; the saving is the sum of five measured moves, and each is measured independently |

---

## 8. The measurement contract

Every claim in this document, and every acceptance measure above, is read off one file:

```bash
python3 - <<'PY'
import json, os, time, collections
p = os.path.expanduser('~/.estate/efficiency-ledger.jsonl')
def ts(at):
    try: return time.mktime(time.strptime(at, '%Y-%m-%dT%H:%M:%SZ')) - time.timezone
    except Exception: return None
now = time.time(); agg = collections.defaultdict(lambda: dict(cost=0.0, calls=0, billed=0.0, prompt=0.0, cache=0.0, out=0))
with open(p, 'rb') as f:
    f.seek(0, 2); pos = f.tell(); data = b''
    while pos > 0:                                  # the ledger is large: read it backwards
        step = min(16 * 1024 * 1024, pos); pos -= step
        f.seek(pos); data = f.read(step) + data
        lines = data.split(b'\n'); data = lines[0]
        for ln in lines[1:]:
            if not ln.strip(): continue
            try: d = json.loads(ln)
            except Exception: continue
            if d.get('kind') != 'outcome': continue
            t = ts(d.get('at', ''))
            if t is None or t < now - 86400: continue
            a = agg[d.get('model') or '?']; u = d.get('usage') or {}
            a['cost'] += float(d.get('cost_usd') or 0); a['calls'] += 1
            a['billed'] += float(u.get('input_equiv_billed') or 0)
            a['prompt'] += float(u.get('prompt_tokens') or 0)
            a['cache'] += float(u.get('cache_read') or 0)
            a['out'] += int(u.get('output_tokens') or 0)
for m, a in sorted(agg.items(), key=lambda kv: -kv[1]['cost']):
    hit = a['cache'] / a['prompt'] * 100 if a['prompt'] else 0
    print(f"{m:22} calls={a['calls']:6d} cost=${a['cost']:7.2f} billed_in={a['billed']/1e6:7.2f}M out={a['out']/1e6:5.2f}M cache_hit={hit:5.1f}%")
PY
```

The spend door is the second instrument, and it must work for the cloud route:
`estate-execute cost-today` (and `ledger-verify`) against `https://llm.${ESTATE_ZONE}/key/info`.

**The rule:** a rung is done when its acceptance measure has been read off one of these two
instruments, in the same turn it was claimed. A saving that has only been argued is not a
saving.

---

## 9. What is already in flight (reuse, do not duplicate)

| issue | what it already covers | how this design uses it |
|---|---|---|
| #7247 | the routing law: cloud default, laptop fallback | the constraint every rung is designed inside |
| #7078 | the client flip to the cloud route | R0 must land before it; the measurement moves with the traffic |
| #7142 | a cloud refusal falls back to the laptop slot | the fallback chain of R2, on the new primary |
| #7081 | the cluster router captures the graph and signs the ledger | R0's ledger |
| #7097 | lane inventory converges; Catalog Phase 0 | R2's lane inventory |
| #7205 | the OKE free floor revived on local-path | R2's free bottom |
| #6785 | the `minimax_m31f` lane + fallback from `minimax` (its claim lapsed 2026-10-21) | R1 — the lane exists in the laptop's own config only; versioning it, and the pin and the fallback entry, are R1's work |
| #6872 | a `claude-*` lane on the cluster | R2's subscription lane ($0.00 over 7 days, 2,080 calls) |
| #7116 | the cluster's crash-loop rescue before the DB stand-in is Ready | R0's spend database |
| #7089 | one structured-format layer at three boundaries | R3's cached answers must be structured, not prose |
| #7104 | artifact tier routing | the context half of R3 (which artifacts are re-read) |
| #6607 | distill Claude's method into a playbook | a playbook, not a model: no overlap with the forge path |

---

## 10. Definition of done

1. `estate-execute cost-today` answers 200 for the cloud route, and its figure matches the
   ledger's per-call sum within 5%.
2. A key with a real `max_budget` refuses traffic that exceeds it, and the refusal is observed.
3. The pinned lane's 7-day spend is ≤ $12 with the 7-day call count within ±10% and the probe
   agreement not below baseline.
4. Every paid group in the fallbacks map resolves to a free lane, proven by fault injection.
5. ≥15% of calls are answered from cache, every cached answer carries its source, and no cached
   answer is a write or a state-dependent read.
6. The ledger names the top callers by spend; CI's graded suites make zero live model calls.
7. The rolling 24-hour spend is **≤ $10.00** — the floor in §4.2 — with the traffic and the
   quality unchanged.
8. Every lane the fallback chains name is **versioned in a file in this repository** (so a
   re-render keeps it), **carried by the cloud key's allowlist** (a chain that names an
   uncallable lane is a guaranteed refusal, and the routing matrix proves it cannot happen),
   and **observable in the spend ledger** (item 1), so no saving is claimed on a route the
   estate cannot read.

Until all eight hold, the bill is what it is, and the honest statement is "built", not
"operating".
