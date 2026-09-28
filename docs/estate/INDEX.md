# The Estate — one index

**Date.** 2026-09-20 · **Purpose.** There are fourteen documents in this estate that each claim, in
their own era and their own words, to describe "the estate." None of them knows the others exist.
A reader who opens them in the wrong order gets three different companies described in three
different tenses, and no way to tell which is current.

This file is the map. It says **which document to read**, **what it is good for**, **how stale it
is**, and **what is actually true today**. It does not replace them. It tells you which one to trust
for what.

---

## 1. Read in this order

| # | Question you are asking | Read this | Era | Trust |
|---|---|---|---|---|
| 1 | *What is the estate, in one sitting?* | **`idp/docs/estate/ESTATE-SNAPSHOT-FOR-CONSULTANT.md`** | 2026-09-20 | **Current** |
| 2 | *What is every platform layer?* | **`idp/docs/estate/PLATFORM-LAYERS-FULL-INVENTORY.md`** | 2026-09-20 | **Current** |
| 3 | *What is live right now?* | `crew/STATE.md` — a command-by-command snapshot | 2026-09-15 | Regenerate |
| 4 | *What is graded elite / gap / blind?* | `idp/docs/SHOWCASE.md` — 434 entities | 2026-09-17 | Regenerate |
| 5 | *What is planned, blocking, when?* | `idp/docs/NEXT.md` — 675 checkpoints | 2026-09-19 | Regenerate |
| 6 | *What did the founder get?* | `idp/docs/FOUNDER.md` — shipped / changed / stuck | 2026-09-19 | Current-ish |
| 7 | *What does every component run?* | `idp/docs/inventory.md` — 3,035 lines, graded vs git | 2026-09-15 | Regenerate |
| 8 | *What is the ethos, as machine rows?* | `idp/conscience/tenets.yaml` | live | **Live** |
| 9 | *Why does this estate repeat itself?* | `claude-estate/research/CONSULTANT-BRIEF.md` | 2026-08-21 | **Historical — still the sharpest diagnosis in the repo** |
| 10 | *How does the commercial engine hang together?* | `prospector/docs/ESTATE_MAP.md` | 2026-08-18 | **Historical — prospector-era** |
| 11 | *How does pricing work?* | `prospector/docs/CONSULTANT_BRIEF_PRICING_AND_CONTENT.md` | ~2026-08 | **Historical** |
| 12 | *What is the north star?* | `hermes-config/ESTATE_NORTH_STAR.md` | 2026-06-25 | **Historical — hermes era** |
| 13 | *What was the estate in June?* | `hermes-config/ESTATE_STATE.md` | 2026-06 | **Historical** |
| 14 | *How do we survive disaster?* | `prospector/docs/ESTATE_CONTINUITY_PLAN.md` | ~2026-08 | **Historical** |

**Generated files** carry "GENERATED … do not edit by hand" at the top. Treat any number in a
non-generated file older than a week as a lead, not a fact.

---

## 2. What is actually true today

Reconciled 2026-09-20 from the sources above. Where they disagree, the newer measurement wins and
the disagreement is named.

### 2.1 The estate is three estates in one repo

The fourteen documents are not fourteen drafts of one thing. They are **three eras stacked**, and
each era still has live code in it:

| Era | When | What it was | What survives |
|---|---|---|---|
| **Hermes era** | ~2026-06 | One agent, Telegram-first, North Star = total oversight from a phone | `hermes-v2`, `hermes-agent`, `hermes-config`, the North Star's three non-negotiables — **still the driving intent** |
| **Prospector era** | ~2026-08 | A commercial research engine + storefront, five agent sessions, no funds | `prospector`, `mumchimp-medusa`, the consultant brief's diagnosis of *why the founder repeats himself* — **never answered** |
| **Platform era (idp)** | 2026-09 → | One platform, 105 layers, 52 laws, evidence layer, agent crew | `idp`, `crew`, `claude-guards`, `sovereign`, `ironcage`, `survival-stack` — **where the real capability now sits** |

**The stacking is itself a finding.** The platform era was built *on top of* two earlier estates
without retiring them. That is why `crew/STATE.md` says "11 live repos"; why the founder's own
brief from 2026-08-21 complains he repeats himself; and why there are three front ends where the
standard says one.

### 2.2 What is measurably LIVE

| Thing | State | Where measured |
|---|---|---|
| OKE Kubernetes cluster | Running, **2 of 3 nodes Ready** | `kubectl get nodes` |
| Flux | **46 of 86 Kustomizations not ready** | `kubectl get kustomizations -A` |
| Estate MCP server | One server, ADR 0006 | `platform/mcp` |
| LiteLLM router | Route-per-model, severing budget breaker | `platform/llm` |
| Aevum evidence layer | Post-quantum receipts, standalone verifier | `platform/observability`, ADR 0028 |
| Ironcage research kernel | **Deployed to Oracle Free Tier, 2 OCPU, 0 GPU** | its own README + `platform/ironcage` |
| survival-stack lifeboat | Cloudflare Worker, Lighthouse page | `survival-stack`, `platform/lifeboat` |
| Dagster scheduler | 16 processes | `pgrep -f dagster` |
| Guards / hooks | **61,897 runs in 24h, 326 refused** | `hook-outcomes.jsonl` |
| Merged PRs, estate-wide, 7d | **964** | `gh search prs` |

### 2.3 What is measurably NOT working

| Thing | State | Where measured |
|---|---|---|
| Revenue | **never measured** — token unset | `crew/science/revenue.jsonl` |
| Forecast scoring | **15 predictions, 0 scored** | `crew/science/predictions.jsonl` |
| Warehouse | **0 dbt models**, rebuilt 523h ago | `crew/STATE.md` |
| MLflow (named by R34) | **ABSENT** | `command -v mlflow` |
| Drills | 12 entities GAP at **age 390.7h** | `idp/docs/SHOWCASE.md` |
| Guards observed | **16 BLIND — "last-status absent; never observed"** | `idp/docs/SHOWCASE.md` |
| SPIFFE identity | **1 proof pod, 0 catalog services, 0 mTLS calls** | `idp/docs/SHOWCASE.md` |
| `static-secret-gate` | **25** (bar is 0) | `idp/docs/SHOWCASE.md` |
| maestro | **RED — last cycle 3,351 min ago** | `crew/STATE.md` |
| CI runs measurement | **466h stale** (bar 30h) | `crew/STATE.md` |
| Stranded work | **1,201 commits on no remote**, 11 dirty files | `crew/STATE.md` |
| Founder-visibility P1 | **open** — "cannot open five of eight tools" | crew#718 |
| Open P1s | **30** | `crew/STATE.md` |
| Checkpoints | **675 planned, 670 with no date, 0 blocking, 0 active** | `idp/docs/NEXT.md` |

---

## 3. The disagreements between documents (named, not hidden)

Where the fourteen documents contradict each other. A consultant will hit these; better they hit
them here.

| # | Disagreement | Resolution |
|---|---|---|
| **D1** | `prospector/ESTATE_MAP.md` describes **four paths — Making, Selling, Operating, Building** — as the estate. `idp/README.md` describes **one platform, ~105 layers**. | Both are true of their era. The four paths are the *prospector business*; the platform is the *substrate it now runs on*. Neither document says so |
| **D2** | `crew/STATE.md` says **11 live repos**; `git` shows **49 repos with 25 committed in 7 days**. | STATE.md counts "live" = actively developed. The count is definitional, not factual |
| **D3** | `hermes-config/ESTATE_STATE.md` is titled **"the single source of truth"**; so is at least one other doc in each era | Three documents claim to be the single source of truth. **This index is the arbiter** |
| **D4** | `idp/docs/SHOWCASE.md` → **393 ELITE of 434**; `crew/STATE.md` → **386 ELITE of 422** | Different generation dates (09-17 vs 09-15) and different entity sets. Neither is wrong; **neither is current** |
| **D5** | The **one front end** standard vs **three unstandardised front ends** in `prospector`, `docs/storefront/look-engine`, `mumchimp-medusa` | Both in the same generated document. The standard is declared; adoption is not done |
| **D6** | Founder's brief says **no funds / $515 of $516.79 spent**; the platform has a **$150/month severing ceiling** | Different eras and different budgets. The severing breaker is the *platform-era* answer to the *hermes-era* complaint |
| **D7** | `prospector/ESTATE_MAP.md` says **"Live status is a command, not this file"** — the honest pattern. Most other estate docs assert status in prose | **The prospector doc is right.** Adopt its rule estate-wide |

---

## 4. The single honest paragraph

> One founder and an agent crew have built, in about three months on free-tier infrastructure, a
> self-hosting platform of **105 layers, 598 Kubernetes manifests, 354 executable acceptance specs,
> 48 ADRs, 52 laws and 163 guards**, where **agent authority is enforced by infrastructure rather
> than application code** (ADR 0023), every agent action can be **independently verified with
> post-quantum signatures by a third party** (ADR 0028/Aevum), and the governing rules are
> **machine-checked against their own must-fail fixtures**. It is genuinely further along than a
> one-person team should be able to get. It is also **three estates stacked without retiring the
> first two**, and its binding constraint is not capability but **closure**: 675 checkpoints with
> 670 undated and none active, 15 forecasts with none scored, revenue never once measured, 46 of 86
> Flux rows unhealthy, 16 guards that have never been observed running, and a founder who cannot
> open five of his own eight monitoring tools. **The estate's advantage is designed and proven. Its
> problem is that almost nothing it builds gets finished, graded, or shown to the person who asked
> for it.**

---

## 5. Fourteen documents, one rule

Every estate document in this repo makes claims. Exactly one of them states the rule that should
govern all of them — `prospector/docs/ESTATE_MAP.md`:

> **"Live status is a command, not this file."**

Adopt it. From now on, an estate document that asserts a status without naming the command that
produced it is stale by definition, and this index should say so.

---

## 6. Regenerating this index

```bash
# the fourteen
wc -l crew/STATE.md crew/ESTATE_STATE.md idp/docs/SHOWCASE.md idp/docs/NEXT.md \
      idp/docs/FOUNDER.md idp/docs/inventory.md idp/docs/CONSCIENCE.md \
      claude-estate/research/CONSULTANT-BRIEF.md prospector/docs/ESTATE_MAP.md \
      prospector/docs/CONSULTANT_BRIEF_PRICING_AND_CONTENT.md \
      prospector/docs/ESTATE_CONTINUITY_PLAN.md \
      hermes-config/ESTATE_STATE.md hermes-config/ESTATE_NORTH_STAR.md \
      idp/docs/estate/ESTATE-SNAPSHOT-FOR-CONSULTANT.md \
      idp/docs/estate/PLATFORM-LAYERS-FULL-INVENTORY.md

# which claim to be the single source of truth
grep -ril "single source of truth" --include="*.md" . | grep -v node_modules

# the live truth
cat crew/STATE.md
python3 crew/science/datamap.py --check
growmos --root ~/Documents/code/estate-graph context --brief
```

---

## 7. What should happen to these documents

| Action | Document | Why |
|---|---|---|
| **KEEP CURRENT** | `ESTATE-SNAPSHOT-FOR-CONSULTANT.md`, `PLATFORM-LAYERS-FULL-INVENTORY.md`, `conscience/tenets.yaml` | The platform-era truth |
| **REGENERATE, NEVER HAND-EDIT** | `SHOWCASE.md`, `NEXT.md`, `inventory.md`, `crew/STATE.md` | Generated; stale by design, refresh on read |
| **KEEP, MARK HISTORICAL** | `CONSULTANT-BRIEF.md` (08-21) | **The sharpest diagnosis in the estate.** Its seven clusters were never answered. Keep it visible |
| **KEEP, MARK HISTORICAL** | `ESTATE_NORTH_STAR.md` (06-25) | The three non-negotiables still govern everything. Keep the intent, drop the state |
| **ARCHIVE** | `hermes-config/ESTATE_STATE.md`, `hermes-config/reports/*`, `prospector/ESTATE_CONTINUITY_PLAN.md` | Superseded eras; keep for the record, stop feeding them |
| **MERGE INTO THIS INDEX** | the "single source of truth" claims in each era | Three documents cannot each be the source of truth |
| **ADOPT AS LAW** | `prospector/ESTATE_MAP.md`'s "live status is a command, not this file" | It is the only estate doc that protects itself from being stale |

---

*Prepared by the crew for the founder. Where this index disagrees with a source, the source's own
command is cited so a reader can re-run it and settle the question. That is the only mechanism that
ends the disagreement.*
