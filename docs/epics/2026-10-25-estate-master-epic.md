# The Estate Master Epic — a closed-loop, self-governing agentic workforce

- **Status:** proposed — founder go/no-go requested on §1, §2, §8 and §11 (second pass)
- **Date:** 2026-10-25 · **Author:** pi (chief-architecture review), commissioned by the founder
- **Scope:** every surface, the last seven days of work, and the target architecture
- **Evidence:** every number below was measured on 2026-10-25 with the instrument named (§10)

> **Intent, one sentence.** The estate becomes a **closed-loop, self-governing agentic
> workforce**: every failure becomes a ticket, every ticket is prioritised and dispatched to
> an agent that has the capacity to take it, every change is verified by a gate that can
> fail, and every result is written back to memory so the next decision is better than this
> one. The founder's remaining job is **go / no-go on high-level decisions**.

---

## 0. The 720-degree view — the data contract (R-27, R-36, R-39)

A consultant cannot have a 720-degree view from prose. It needs one structured record
answering eight questions, each from a named source, each re-derivable by a command. Prose
(including this document) is a **rendering** of that record, never the record.

| # | Field | Question it answers | Source of truth today | Freshness |
|---|-------|--------------------|-----------------------|-----------|
| 1 | **STATE** | What exists, where, in what condition? | `estate-360`, cluster twin (`clusters/oke`, `sovereign/`), `bin/idp-ci` | ≤ 15 min |
| 2 | **INTENT** | What does the founder want, in their words, with constraints? | §1 here + `~/.estate/intents/*.yaml` (340) | append-only |
| 3 | **HISTORY** | What have we tried; what happened; what did we learn? | git + PR ledger + `growmos` graph + facts store (rungs R1–R3) | append-only |
| 4 | **GAPS** | What is missing, ranked, with evidence? | this document §5 + `bin/estate-tickets` | daily |
| 5 | **METRICS** | Is it getting better? | eval harness, judge rounds, red-team runs, gate verdicts | per run |
| 6 | **DECISIONS** | Why is it like this? | `docs/decisions/` (ADR 0040–0043 this week) | append-only |
| 7 | **CONSTRAINTS** | What may not be done? | `AGENTS.md`, Active Focus claims, budget/capacity store | live |
| 8 | **CAPACITY** | Who can afford this work right now? | capacity contract §6.3 — **does not exist yet** | ≤ 60 s |

**720-1** An agent reads all eight fields before it decides, and cites the values it read. A
decision with no read is a guess.
**720-2** Every field is structured (JSON/YAML) and re-derivable; a field only a human can
produce is a gap, not a source.
**720-3** One store, many renderers — this document, the page, Otto, the CLI all render the
same records. A second copy of a field is stitching and gets deleted (AGENTS.md §6).

---

## 1. Requirements register — the founder's words, decoded

Verbatim anchors are quoted so a wrong decode is visibly wrong. **Founder action: mark any
row ✗ and the epic is re-cut; a silent row is taken as agreed.**

| ID | Founder's words | Operational meaning | Proven by | Owner |
|----|-----------------|---------------------|-----------|-------|
| R-01 | "review everything we have tried to do in last week or so" | weekly architectural review of merged work, not a changelog | §3–§4, re-generated weekly by a scheduled agent | review loop |
| R-02 | "current harness ways or works on all inflight stores" | every in-flight repo/branch/stash visible with owner + verdict | `bin/lane-where`, `work-audit` intent, greenlane status | execution |
| R-03 | "harmonise … a congruent architecture" | one of each layer; duplicates merged or deleted | §6.1 layer table + findings F-01…F-08 | architecture |
| R-04 | "workforce that can be adapted to any estate but using current estate as test bed" | the product is the pattern; this estate is the fixture | each layer ships a portable contract, no estate-specific hard-coding | all |
| R-05 | "voice first film/virtual world realtime" | Otto is spoken to, answers in real time, can render a scene | measured voice round-trip on the founder's surface | interaction |
| R-06 | "ephemeral user interfaces covering all activity" | any activity can summon a throwaway panel; no permanent app needed | panel generated from the same records as §0 | interaction |
| R-07 | "anti hallucination … structured formats … neuro symbolic, mathematically backed" | outputs cross a schema boundary; claims carry rungs; refusals are typed | rung 1f + schema conformance (#7100) + facts re-execution (`4/4 PASS`) | verification |
| R-08 | "skills, reasoning" | skills are a catalogue; reasoning is a routed capability | skill catalogue gate (#7125), reasoning gateway hook | capability |
| R-09 | "strong metrics, evals, red team, judges" | every agent and pipeline has a score it cannot fake | eval rounds, red-team fixtures, judge votes stored as data | verification |
| R-10 | "oncluster side we have shadows twin, we have intent" | cluster state simulated before applied; actions are intents | shadow runs (#7117, #7129) + intent executor | substrate |
| R-11 | "how to discover estate capabilities" | a machine-readable capability index with contracts and cost | index answers "what can do X, at what price" without reading the tree | capability |
| R-12 | "persistent agent identity" | an agent is an entity with history, claims, scores, capacity | identity record + claim ledger + eval history | identity |
| R-13 | "routing layer, efficiency layer, jev … otto" | one system with layers, not four products | single routing contract: capacity in, decision out | routing |
| R-14 | "an error results in a ticket being raised, prioritised, assigned and depending on capacity an agent is automatically launched" | **the core loop**: failure → ticket → priority → dispatch → fix → verify → learn | sealed-failure test closes itself; MTTR measured end-to-end | governance + routing |
| R-15 | "daily or weekly automated review / code reviews" | review agents open findings as tickets, not comments | review rounds produce owned tickets | review loop |
| R-16 | "research … create tickets and science lane that can run experiments automatically build prototypes that can turn into production" | research → ticket → experiment → prototype → production | chain traced from a research record to a merged PR | research loop |
| R-17 | "self improvement of our services ways of working" | the estate improves services and its own process | improvement tickets closed by agents; effect measured | governance |
| R-18 | "research what opensource tooling available" | continuous OSS harvest into the capability index | `bin/oss-harvest` on a schedule, feeding §0 field 1 | research loop |
| R-19 | "decode founder intent for the platform and autonomously try to solve it" | founder messages become intent records agents pursue | work item traces back to an intent id | intent |
| R-20 | "passive rather than event driven … work on schedule … otto, concierge, research, science" | every loop has a trigger: event or schedule, never a human kick | scheduler inventory shows zero loops needing a human | governance |
| R-21 | "founder wellbeing capability" | the estate protects founder attention, energy, time | founder-minutes metric, escalation policy, quiet hours | interaction |
| R-22 | "reflection and self-improvement tied with eval and judges as first class … for any agent" | each agent reflects, and the reflection is scored | reflection records + judge score per agent | verification |
| R-23 | "the platform is driving itself … founder does high-level go/no-go" | **definition of success** (§8) | autonomy ratio + founder-minutes per week | all |
| R-24 | "master epic … references all relevant capabilities surfaces recent work … all commits all tickets all proposals" | this document, with reproducible instruments | §3, §10 | architecture |
| R-25 | "undoubtedly certified bleeding edge" | certification is an artifact with evidence, not an adjective | §6.6 certificate, re-issued per release | verification |
| R-26 | "be sure you understand my requirements and concerns" | §1–§2 are the contract, confirmed or corrected | register versioned; founder marks rows | intent |
| R-27 | "consultant to have a 720 degree view of platform and founders wishes" | §0 data contract | all eight fields readable by one call | memory + intent |
| R-28 | "we have the quad layer … intelligent routing, epistemic firewall" | compose existing layers, never replace | layer map places each in exactly one row | architecture |
| R-29 | "ideas from zeroedge, agentic workforce and other harnesses … not properly analysed" | harvest external designs; adopt or refuse with a reason | harvest digest + one ADR per adopted idea | research loop |
| R-30 | "we have all the building blocks … unified memory, context, active focus active memory, realtime, fleet" | composition beats construction | each new capability names the blocks it composes | all |
| R-31 | "closed self improvement loop, potentially recursive" | improvement of the improver, bounded at each recursion | loop diagram with a bound per recursion | governance |
| R-32 | "slab of mess that could be truly best of breed" | refactor toward best, delete the rest | findings closed or accepted with a date | architecture |
| R-33 | "know usage limits left, credits left to estimate if enough capacity … not have request routed to them … know when they have capacity" | **capacity contract** (§6.3) | router refuses unaffordable work, re-admits on recovery | routing |
| R-34 | "closed loop is architectural guidance for this epic" | **Closed-Loop Law** (§6.2): no loop, no ship | each intent YAML declares its loop | all |
| R-35 | "self governing based on data" | thresholds are data, changed by evidence | policy store + measured effect per change | governance |
| R-36 | "data, metric collection discovery mechanisms … world class and structured format" | §0, with facts rungs applied to metrics | every metric has an instrument and a window | memory |
| R-37 | "invest in our mcp tooling" | the MCP surface is the product's API | contract + version + test per tool | capability |
| R-38 | "research and science … brought in otto … truly autonomous and ever present realtime, concierge also … real avatars and voice, plugged into the memory systems, part of the fleet" | Otto is the always-on surface; research, science, concierge are fleet agents with identity, voice, avatar, memory | each runs unattended 7 days and is visible in the fleet view | interaction + identity |
| R-39 | "critical we capture and understand founder intent" | intent is a versioned record with acceptance tests | every work item names the intent id it serves | intent |

---

## 2. Concerns register

| ID | Concern (anchor) | What it costs today | Answer in this epic |
|----|------------------|---------------------|--------------------|
| C-01 | "everything is disjointed … slapped on top of one another without architectural harmony" | every new capability adds a fourth way to do the same thing | §6.1 layer law, findings F-01…F-08, claim gate on a duplicate layer |
| C-02 | "the same problem we have tried to solve gazillion times, some naive, some more promising" | rework; the good idea is lost among the naive ones | HISTORY field in §0; a new attempt must cite the earlier ones |
| C-03 | "just run bliding, there is no closed loop" | the founder is the monitoring system | R-14 incident loop, Phase 1 |
| C-04 | "passive rather than event driven" | nothing starts without a human | R-20; every loop gets an event or schedule trigger |
| C-05 | "as founder I have done enough driving" | founder is scheduler, triager, reviewer | §8 involvement ceiling |
| C-06 | no memory of attempts (implied by C-02) | repeated dead ends | facts store + graph + ADR-per-fork |
| C-07 | "failures across the estate from ci to greenlane to services erroring in live to k8 errors" | silent red, no owner | incident loop spans CI, greenlane, live services, cluster |
| C-08 | "undeniably certified" | certification by assertion | §6.6 certificate with rungs, gate that can fail |
| C-09 | agents that cannot afford the work still receive it | burned budget, dropped work, no signal | §6.3 capacity contract |
| C-10 | founder intent lost between messages, docs and loops | agents solve the wrong problem well | §6.4 intent layer, R-39 |

---

## 3. What exists — measured 2026-10-25

| Measure | Value | Instrument |
|---|---|---|
| Repos on GitHub | 69 (58 public, 11 private, 11 archived); 16 pushed in 7 days; 186.4 MB | `~/.estate/bin/estate-360` |
| Working copies in `~/Documents/code` | 56 | `ls ~/Documents/code \| wc -l` |
| Executable intents | 340 YAML | `ls ~/.estate/intents/*.yaml \| wc -l` |
| Estate binaries | 34 | `ls ~/.estate/bin \| wc -l` |
| `idp/bin` tools | 440 | `gh api repos/chidionyema/idp/contents/bin` |
| `idp` commits since 2026-10-19 | 211 | `gh api .../commits?since=2026-10-19T00:00:00Z` (3 pages) |
| Facts store | `4/4 active facts re-executed … verdict: PASS` | `bin/idp-ci` facts rung, run 40169493942 |
| Live claims | #7003, #6921, #7116, #7113 | estate-memory Active Focus |
| Machine | load 33.81 / 156.20 / 227.71; disk 94% used, 5.8 GiB free | `uptime`, `df -h ~` |

**Last seven days by area** (subject histogram over 200 sampled subjects): platform 37, fix 15,
shadow 10, build 10, meridian 9, docs 8, research-engine 5, feat 5, router 4, memory 4,
face 4, estate 4, skills 3, otto 3.

**Proposals and decisions produced this week:**

| Artifact | Size | What it established |
|---|---|---|
| `docs/specs/2026-10-23-the-delegated-estate.md` | 207,938 B | delegation model and its verbs |
| `docs/specs/2026-10-23-estate-as-movie-director-engine.md` | 70,008 B | the film / virtual-world surface (R-05) |
| `docs/specs/2026-10-22-face-superpowers-audit.md` | 50,511 B | founder-surface audit |
| `docs/specs/2026-10-23-founder-agent-gate.md` | 16,882 B | eval + judge for the founder agent (R-09, R-22) |
| `docs/specs/2026-10-24-founder-surface-redesign.md` | 12,395 B | ephemeral founder surface (R-06) |
| `docs/specs/2026-10-24-skill-catalogue.md` | 10,747 B | skills as a catalogue (R-08) |
| `docs/specs/2026-10-25-one-schema-three-boundaries.md` | 10,055 B | structured formats at every boundary (R-07) |
| `docs/specs/2026-10-23-harness-inventory-and-how-a-harness-is-swapped.md` | 9,228 B | harness = substrate + runtime + door (R-02) |
| `docs/specs/2026-10-19-active-memory-and-focus-vs-muse.md` | 6,936 B | active focus vs muse |
| `docs/decisions/0040-the-director-runs-on-the-laptop-until-the-loop-is-proven.md` | — | prove the loop before scaling it |
| `docs/decisions/0041-the-artifact-on-screen-is-the-real-artifact.md` | — | the screen is the product |
| `docs/decisions/0042-one-schema-at-every-boundary.md` | — | one schema per boundary |
| `docs/decisions/0043-the-bound-lives-at-the-door.md` | 122 lines | one wall-clock bound, at the door |

**Blocks to compose, not repeat** (R-28, R-30): the door (`mcp/plugins/estate_executor.py`,
`CEILING_SEC = 100`), the intent executor (340 intents), facts with rungs
(`bin/estate-claim-check`), the graph (`growmos`), active memory/focus, the greenlane
(`bin/idp-greenlane`, `lane-submit`, `merge-when-green`), the shadow/twin cluster substrate,
the LiteLLM router (#7082, #7079), the epistemic firewall, the harness inventory
(`idp-harness-inventory`), the eval harness and the founder-agent gate (#6980), skills
(21 vendored packs, #7045), Otto (`hermes-agent`, #7054, #7058, #7066).

---

## 4. Congruency findings — the "slab of mess", named

Each finding is a place where the estate has two of something, or one of something that has
no consumer. Findings are the input to Phase 0, not opinions.

| ID | Finding | Evidence | Collapses into |
|----|---------|----------|----------------|
| F-01 | **Two doors.** `mcp/plugins/estate_executor.py` and `platform/estate/bin/estate-execute` both implement the governed execution door. #7123 had to fix the ceiling in both (+34/−3 and +109/−16 in one commit). | commit c8a6086c6 file list | one door module; one vendored launcher |
| F-02 | **Budget known in four places.** `bin/idp-budget`, `bin/budget_governor.py`, `~/.estate/efficiency-ledger.jsonl`, and now `bin/timeout-budget`. | `gh api contents/bin` filter `budget|cost`, five matches | one budget record, one reader |
| F-03 | **The claim ledger read is flaky and fails to `unknown`.** The focus query measured **5.16 s** against `FOCUS_TIMEOUT_S = 8.0`; when it loses that race the estate-memory brief prints "claim ledger unreadable" — observed twice in this very session. | `focus.py:54`, `gh issue list --search …` timed | cache-first read + stale-but-known fallback |
| F-04 | **Routing knows capability tier, not capacity.** #7053 routes delegated work by capability tier; nothing reads a usage limit or a credit balance before dispatch. Only `bin/idp-cost-proof` exists, and it proves cost after the fact. | commit 026d589cc; `bin` filter `quota|credit` empty | capacity contract §6.3 |
| F-05 | **Four ticket ledgers.** `bin/estate-tickets`, claim issues (#7003, #6921, #7116, #7113), `work-audit` findings, and greenlane lanes. A failure can legitimately appear in none of them. | live claims list vs lanes vs work-audit | one incident/ticket record type |
| F-06 | **Capability discovery is by name only.** 340 intents and 440 `bin` tools; discovery is `estate_list` / `estate_show`, which return YAML, not a contract with cost, latency and reliability. | `ls ~/.estate/intents/*.yaml \| wc -l`; MCP exposes 3 tools | capability index (§6.5) |
| F-07 | **The harness inventory is not wired.** `idp-harness-inventory` and the swap spec exist; the router does not consult them when choosing a runtime. | repo present; spec 2026-10-23 | routing reads the inventory |
| F-08 | **Emitters with no consumer.** Friction events (`estate.friction.v1`, #7050), the action ledger, hypotheses races — each records, none dispatches. Data is collected; no loop closes on it. | #7050, #7082, `hypotheses.race` | one event → decision → dispatch path |

---

## 5. Gap register

State is one of **present**, **partial**, **missing**. Phase refers to §7.

| Req | State | Evidence of state | Phase |
|-----|-------|-------------------|-------|
| R-01 weekly architecture review | partial | this document is the first one; no schedule | 2 |
| R-02 harness / in-flight review | partial | `lane-where`, `work-audit`, greenlane status exist; no weekly digest | 0 |
| R-03 congruency | partial | §4 findings open | 0 |
| R-04 portable workforce | partial | layers carry estate-specific paths (`docs/…`, `clusters/oke`) | 3 |
| R-05 voice-first realtime | partial | voice intents (`voice-query`, `voice-router`), Director Engine spec; no measured round-trip | 3 |
| R-06 ephemeral UI | partial | founder-surface redesign spec; panel generator absent | 3 |
| R-07 anti-hallucination | **present** | ADR 0042 + #7100 conformance gate + facts rungs + rung 1f on main | — |
| R-08 skills + reasoning | present | 21 vendored packs (#7045), catalogue gate (#7125), reasoning hook | — |
| R-09 metrics/evals/redteam/judges | partial | eval harness + founder-agent gate (#6980); no per-agent score served | 2 |
| R-10 twin + intent | present | shadow (#7117, #7129), intents (340) | — |
| R-11 capability discovery | **missing** | no index with contracts (§4 F-06) | 0 |
| R-12 agent identity | partial | claims + eval history; no identity record | 1 |
| R-13 routing/efficiency/jev/otto harmonised | partial | router (#7082), efficiency ledger, JEV; three readers | 1 |
| R-14 incident loop | **missing** | no path from a red CI job to an owned ticket to a dispatched agent (C-03) | 1 |
| R-15 scheduled review | missing | no review agent on a schedule | 2 |
| R-16 research → ticket → science → prototype | partial | `bin/arxiv-harvest`, `bin/oss-harvest`, `research-engine` repo; no ticket emission | 2 |
| R-17 self-improvement of services | missing | no improvement loop with measured effect | 2 |
| R-18 OSS harvesting | partial | `bin/oss-harvest` exists; not scheduled, not in an index | 2 |
| R-19 founder-intent decoding | **missing** | intent lives in chat; §1 of this doc is the first structured attempt | 0 |
| R-20 event-driven + scheduled workforce | partial | greenlane is event-driven; research, science, concierge are not | 1 |
| R-21 founder wellbeing | missing | no founder-minutes metric, no escalation policy | 3 |
| R-22 reflection + judge per agent | partial | founder-agent gate exists for one agent | 2 |
| R-23 platform drives itself | missing | §8 defines it; nothing measures it | 4 |
| R-24 master epic | **this document** | — | 0 |
| R-25 certification | partial | gates exist; no certificate artifact | 3 |
| R-26 register confirmation | **present** | §1–§2, awaiting go/no-go | 0 |
| R-27 720 view | partial | six of eight fields have sources; CAPACITY and INTENT are prose | 0 |
| R-28 quad layer / firewall | present | epistemic firewall, LiteLLM router, gateway | — |
| R-29 external harness harvest | missing | no ZeroEdge/agentic-workforce digest | 2 |
| R-30 composition | partial | true in places (#7123 composed the door), not enforced | 0 |
| R-31 recursive improvement | missing | no bound-on-the-improver design | 4 |
| R-32 best-of-breed refactor | partial | §4 findings are the work list | 0 |
| R-33 capacity-aware routing | **missing** | §4 F-04 | 1 |
| R-34 Closed-Loop Law | **missing** | no intent declares its loop; no gate enforces it | 0 |
| R-35 self-governance from data | missing | thresholds are hard-coded in scripts | 4 |
| R-36 world-class metrics | partial | facts rungs are the right pattern, applied to claims not metrics | 0 |
| R-37 MCP tooling investment | partial | 3 estate tools; no contracts/versions/tests | 1 |
| R-38 Otto as always-on fleet surface | partial | Otto exists (#7054, #7058, #7066); research/science/concierge not fleet agents | 3 |
| R-39 founder intent as data | missing | §1 is the first record | 0 |

---

## 6. Target architecture

### 6.1 Nine layers, one of each

One of each layer, no exceptions (AGENTS.md §6). The right column is what changes — usually a
merge or a deletion, not a build.

| # | Layer | Existing artifact today | Change |
|---|-------|------------------------|--------|
| 1 | **Substrate** | cluster + shadow/twin (`clusters/oke`, `sovereign/`, #7117, #7129) | declare the twin the only pre-flight authority |
| 2 | **Execution door** | `estate_executor.py` + vendored `estate-execute` (F-01) | one module; the launcher becomes a shim |
| 3 | **Intent** | 340 intent YAMLs | add the `loop:` block (§6.2), a `capacity:` estimate, and an `intent_id` reference |
| 4 | **Routing + capacity** | LiteLLM router (#7082), tier routing (#7053), efficiency ledger | add the capacity contract (§6.3) as a pre-dispatch read |
| 5 | **Identity** | claims + eval history | one identity record per agent (R-12) |
| 6 | **Memory** | facts store (rungs), graph, active memory/focus | fix the focus read (F-03); serve §0 fields 3, 5, 6 |
| 7 | **Verification** | `bin/idp-ci` (rungs 1a–1g), eval harness, judges, red team | every rung can fail and says so; eval score served as data (R-09) |
| 8 | **Governance** | budget governor, claim gate, certification | thresholds move to a policy store; the loop that acts on them (§6.2) |
| 9 | **Interaction** | Otto (voice, gateway), Director Engine spec, founder surface spec | Otto as the always-on surface for research/science/concierge (R-38) |

### 6.2 The Closed-Loop Law (R-34) — the architectural guidance

**A capability is shipped only when it declares five parts, and any part missing is a
refusal at the gate, not a review comment.**

```yaml
# every intent gains this block; bin/loop-gate refuses an intent without it
loop:
  sense:   {source: <event stream | schedule | query>, instrument: <command or endpoint>}
  decide:  {rule: <threshold or policy id>, owner: <layer>}
  act:     {verb: <intent name>, capacity: <estimate>, rollback: <what undoes it>}
  prove:   {gate: <bin/idp-ci rung | test | eval>, falsifier: <the case that must fail>}
  remember: {record: <facts | graph | adr>, consumer: <who reads it next>}
```

- **Sense** without a consumer is F-08 (an emitter with no loop).
- **Decide** without a threshold is an opinion; thresholds live in the policy store (R-35).
- **Act** without a capacity estimate is how C-09 happens.
- **Prove** without a falsifier is a gate that cannot fail — the defect #7123 fixed in miniature.
- **Remember** without a consumer is a write nobody reads; the graph already holds five to ten
  attempts at the same problem (C-02).

The same five parts, in order, are the shape of every loop in §7. One law, many instances.

### 6.3 The capacity contract (R-33) — structured, read before dispatch

```json
{"agent_id": "claude-code@laptop", "provider": "anthropic", "plan": "subscription",
 "windows": [{"kind": "5h", "limit": 100, "used": 62, "unit": "messages",
              "resets_at": "2026-10-25T14:00:00Z"}],
 "credits": {"remaining": 41.20, "currency": "USD", "unit": "tokens", "per_usd": 1},
 "burn": {"last_1h": 18.4, "last_24h": 61.0, "unit": "messages/h"},
 "verdict": "admit|throttle|refuse", "reason": "remaining 38% of 5h window; estimate 6%",
 "estimate_for": {"work_id": "EPIC-004", "cost": 6.0, "unit": "messages"},
 "observed_at": "2026-10-25T11:52:00Z", "source": "bin/capacity-probe --agent claude-code",
 "stale": false}
```

Rules, each one testable:

1. **Read before dispatch.** The router reads a capacity row per candidate agent; no row means
   `refuse`, not `admit` (today it would admit — C-09).
2. **Estimating is explicit.** The work carries a cost estimate in the unit the agent spends;
   `remaining < cost × safety_factor` (default 1.5) is a refusal.
3. **A refusal is a ticket,** raised in the same ledger as failures, with the estimate and the
   reason — never a silent drop.
4. **Near-exhaustion is flagged at a threshold** (default: 80% of the window consumed, or
   credits below one estimated work unit) and published as an event.
5. **Re-admission is automatic** when the data says capacity returned: window reset, credit
   top-up, or burn rate falling below the threshold for two consecutive reads.
6. **The machine has capacity too.** Today: load 33.81 / 156.20 / 227.71 and disk 94% used
   with 5.8 GiB free — dispatching compute into that is the same defect in a different unit.
7. **Never inferred from prose.** A model's claim that it has budget left is not a read.

### 6.4 The intent contract (R-19, R-39)

A founder message is not a task; it is an **intent record**:

```yaml
intent:
  id: INT-2026-10-25-01          # stable, cited by every work item derived from it
  quote: "<the founder's words, verbatim, never paraphrased>"
  decoded: [{requirement: R-33, meaning: "...", owner: routing}]
  constraints: ["closed loop is architectural guidance", "founder does go/no-go only"]
  acceptance: ["router refuses unaffordable work", "re-admission is automatic"]
  supersedes: [INT-2026-10-19-03]
  status: proposed | agreed | building | proven
```

The epic's §1 **is** such a record, at portfolio scale. The gap register (§5) is the
`status` field expanded. Once intent is data, R-19 ("autonomously try to solve it") becomes
mechanical: work items carry `intent_id`, and a weekly agent asks which intents are unserved.

### 6.5 The 720 view, implemented (R-27)

- **One record per field**, in the existing stores: facts (with rungs) for measurements,
  graph for relations, intents for intent, ADRs for decisions, claims for constraints.
- **One renderer entry point** — a single command returning the eight fields as JSON, which
  the document, the page, Otto and any consulting agent read. No second copy.
- **Capability index** (R-11) derived from the 340 intents + 440 bin tools + cluster objects:
  name, contract, cost class, latency class, last proven success, owning layer. This is the
  answer to "how do we discover estate capabilities" that is not `ls`.

### 6.6 What "undeniably certified" means (R-25, C-08)

A certificate is an artifact, re-issued per release, that a reader can check without trusting
the author:

1. **Every claim carries a rung** — R1 executed, R2 digested, R3 attributed
   (`bin/estate-claim-check`); today the facts store prints `4/4 … verdict: PASS`.
2. **Every gate can fail, and proves it** — each rung ships a falsifier case that must fail
   (the pattern `bin/catalog-refcheck` and the unbound BDD fixture already use).
3. **Every capability shows one production line** — a real log line, not a green check.
4. **Every loop declares its five parts** (§6.2).

"Bleeding edge" is then a measurement, not a mood: the certificate lists what was measured,
with the instrument and the window.

---

## 7. The epic — phases, workstreams, acceptance

Each phase is judged by an **acceptance test that can fail**, run by a gate, not by a review.
Tickets are named so they can be opened as they are read; none of them needs the founder to
start.

### Phase 0 — Truth and telemetry (week 1) · "we can see"

| Ticket | Work | Acceptance test (falsifiable) |
|--------|------|-------------------------------|
| EPIC-001 | Register §1–§2 as a versioned intent record with `intent_id` | `bin/intent-check` prints 39 requirements and 10 concerns with owners; exits 1 if any lacks an owner |
| EPIC-002 | 720 view: one command returning all eight fields | command returns valid JSON with 8 keys; CAPACITY and INTENT may be `unknown` for at most 7 days, then it fails |
| EPIC-003 | Fix the focus read (F-03): cache-first, stale-but-known fallback | a forced 10 s delay on the claim backend still yields a known owner set, not `unknown` |
| EPIC-004 | One ticket/incident record type; merge the four ledgers (F-05) | a seeded red CI job appears in one ledger with an owner within 60 s |
| EPIC-005 | Capability index v1 from intents + bin + cluster (F-06) | `bin/capability-index query "<verb>"` answers with contract, cost class, last success |
| EPIC-006 | `loop:` block added to intents + `bin/loop-gate` rung in `bin/idp-ci` | removing `prove:` from any intent makes the gate fail |
| EPIC-007 | One door (F-01): delete the duplicate implementation | grep for the second ceiling literal returns one hit; tests still green |
| EPIC-008 | One budget record, one reader (F-02) | two components cannot disagree: a single source is quoted by `idp-budget` and the governor |

### Phase 1 — The incident loop, end to end (weeks 2–3) · "it fixes itself"

This is R-14 and R-33 together: the loop that the founder named as the core concern (C-03).

| Ticket | Work | Acceptance test |
|--------|------|-----------------|
| EPIC-010 | Capacity probe + contract (§6.3) for every agent in the fleet | probe returns a row per agent with `observed_at` < 60 s; a stale row yields `refuse` |
| EPIC-011 | Router reads capacity before dispatch; refusal raises a ticket | an agent pinned to 100% usage receives zero work; a ticket exists naming the reason |
| EPIC-012 | Re-admission on recovery | after a simulated window reset, the same work is admitted without human action |
| EPIC-013 | Sense: CI, greenlane, live-service and k8s failures feed the incident ledger (C-07) | four forged failures (one per source) each become one ticket with a source tag |
| EPIC-014 | Decide: priority = f(severity, blast radius, age, capacity cost) | two forged incidents get deterministic, differing priorities from the policy file |
| EPIC-015 | Act: dispatch to the admitted agent, via the door, with a lane | a seeded failing test is fixed by a dispatched agent and merged by the greenlane |
| EPIC-016 | Prove + Remember: the fix's gate verdict and lesson are written to memory | MTTR recorded per incident; the incident's lesson is retrievable by `recall` |

**Phase 1 exit:** a failure injected on purpose (a red job, a 500 on a service, a crashloop)
closes itself — ticket, dispatch, fix, merge, verified, lesson stored — with the founder only
notified, and MTTR measured. That is C-03 answered with a number.

### Phase 2 — Review, research, science (weeks 4–6) · "it thinks while I sleep"

| Ticket | Work | Acceptance test |
|--------|------|-----------------|
| EPIC-020 | Scheduled architecture + code review agents (R-01, R-15) opening tickets | a week of merged commits yields ≥1 finding-as-ticket with an owner |
| EPIC-021 | External harness harvest: ZeroEdge, agentic-workforce, others (R-29) | digest lists each idea as adopted/refused with an ADR reference |
| EPIC-022 | Research → ticket → science lane → prototype (R-16) | one research record traverses to a merged prototype PR |
| EPIC-023 | OSS harvest on a schedule into the capability index (R-18) | index gains tools without a human running anything |
| EPIC-024 | Reflection + judge score per agent (R-09, R-22) | every agent in the fleet has a score series; a regression is an incident |
| EPIC-025 | Self-improvement of services + process (R-17) | an improvement ticket is closed by an agent, with before/after measurement |

### Phase 3 — Otto as the always-on surface (weeks 6–9) · "it is present"

| Ticket | Work | Acceptance test |
|--------|------|-----------------|
| EPIC-030 | Research, science and concierge as fleet agents with identity, memory, avatar, voice (R-38) | each runs 7 days unattended, visible in the fleet view, answering from memory |
| EPIC-031 | Voice-first realtime round trip (R-05) | measured p50/p95 latency on the founder's device, recorded as a metric |
| EPIC-032 | Ephemeral UI panels generated from §0 records (R-06) | a panel for any activity is produced on demand; no bespoke app |
| EPIC-033 | Founder wellbeing (R-21): founder-minutes metric, escalation policy, quiet hours | a week where the founder is interrupted ≤ N times, N agreed in EPIC-001 |
| EPIC-034 | Certification artifact v1 (R-25) | certificate lists each claim with instrument, window, and its falsifier |

### Phase 4 — Self-governance (weeks 9–12) · "it governs itself"

| Ticket | Work | Acceptance test |
|--------|------|-----------------|
| EPIC-040 | Thresholds move to a policy store, changed by evidence (R-35) | a policy change records the measurement that justified it and its measured effect |
| EPIC-041 | Bounded recursive improvement of the improver (R-31) | each recursion has a budget, an eval gate and a rollback; two levels proven |
| EPIC-042 | Autonomy ratio published weekly (R-23) | percentage of work dispatched, done and verified without a founder decision |
| EPIC-043 | Portable workforce: strip estate-specific paths behind a config contract (R-04) | the same loops run against a second, synthetic estate in CI |

---

## 8. Definition of success — the founder-involvement ceiling (R-23, C-05)

| Decision type | Who decides after Phase 4 | Evidence it happened |
|---------------|---------------------------|----------------------|
| Which failure to fix next | the loop (priority function) | incident ledger ordering |
| Which agent does it | the router (capacity-aware) | dispatch record |
| Whether a change is correct | the gate (rungs + evals) | verdict + falsifier |
| Whether a PR merges | the greenlane | merge commit |
| Whether a service deploys | Flux | production log line |
| What the estate should become | **the founder (go/no-go)** | intent record, agreed |
| Spend above a threshold | **the founder** | approval record |
| Anything irreversible or outward-facing | **the founder** | approval record |

Measured weekly, published as data: **autonomy ratio**, **MTTR** (failure → verified fix),
**founder-minutes** (a target agreed in EPIC-001), **capacity waste** (refused-and-idle vs
admitted-and-completed), **eval score** per agent, **red-team pass rate**, **certificate
currency** (age of the newest evidence per claim).

**The mark of success is not a document.** It is a week in which the estate found its own
failures, dispatched its own fixes, proved them on production lines, and told the founder
only the things that were genuinely his to decide.

---

## 9. Risks — what would make this fail

| Risk | Why it is real here | Mitigation |
|------|--------------------|------------|
| The epic itself becomes layer #2 | five to ten prior attempts at each loop (C-02) | every ticket names the existing block it composes; §4 findings are deletions first |
| Metrics theater | gates that report ok on stale data (a defect already seen this week) | each metric ships with a falsifier; stale data fails, never passes |
| Capacity data is unobservable (no API for a subscription window) | provider limits are partly opaque | probe + local ledger + conservative estimate; unknown = refuse, and unknown is a ticket |
| Machine contention | measured today: load 227 (15 min), disk 94% | capacity contract covers host load and disk; dispatch is refused when the host cannot carry it |
| Founder-intent drift | chat is the only record today | §6.4 intent records; a work item with no `intent_id` is refused |
| Recursion without a bound | R-31 invites it | EPIC-041: budget + eval gate + rollback at each level |

---

## 10. Evidence and references

**Instruments used for §3** (re-run any of them to reproduce a number):
`~/.estate/bin/estate-360`; `ls ~/Documents/code | wc -l`; `ls ~/.estate/intents/*.yaml | wc -l`;
`ls ~/.estate/bin | wc -l`; `gh api repos/chidionyema/idp/contents/bin`;
`gh api 'repos/chidionyema/idp/commits?since=2026-10-19T00:00:00Z&per_page=100'` (3 pages);
`uptime`; `df -h ~`; the `facts` rung of `bin/idp-ci` (run 40169493942).

**This week's load-bearing commits (idp `main`, newest first, abridged from 211):**
`5341f4205` claim-gate fail-closed (#7128) · `c8a6086c6` one wall-clock bound, the door's (#7123)
· `16a66e5e6` one schema, three boundaries (#7100) · the founder-agent gate spec (`docs/specs/2026-10-23-founder-agent-gate.md`)
· the LiteLLM router (#7082, #7079) · friction events (#7050) · skills vendored (#7045)
· shadow runs (#7117, #7129) · Otto surface (#7054, #7058, #7066) · catalog refcheck (#7091)
· estate claim check (#7094, #7095) · harness inventory (#7099). The full list is one call:
`gh api 'repos/chidionyema/idp/commits?since=2026-10-19T00:00:00Z&per_page=100'`.

**Open work at the time of writing:** claim issues #7003 (pi), #6921 (pi), #7116 (zcode-kimi),
#7113 (estate-agent); lanes merged this week: #7100, #7123.

**Decisions this epic relies on:** ADR 0040 (prove the loop before scaling it), 0041 (the
artifact on screen is the real artifact), 0042 (one schema at every boundary), 0043 (the bound
lives at the door).

**Adjacent documents that are implementation detail, not repetition:** the six specs listed in
§3, `AGENTS.md` (laws and ceilings), `docs/specs/2026-09-24-estate-agent-enforcement-platform.md`
(intent-only execution).

---

## 11. Second pass — the founder's additional wishes (2026-10-25, appended after §1–§10 landed)

§1–§10 landed on `main` as `7383bb20d` (#7131). This section is **append-only**: the founder's
words arrive after the register was agreed, and rewriting §1 would hide that. It is the same
register, extended — not a second document (720-3, and AGENTS.md §6).

### 11.1 Requirements, second pass

| ID | Founder's words | Operational meaning | How it is proven | Owner |
|----|-----------------|---------------------|------------------|-------|
| R-40 | "agents to act as partners on the estate autonomously brainstorming, researching, proposing, suggesting ways to improve the estate and platform" | agents generate *proposals*, not only execute tickets: each one carries evidence, a falsifier and a cost | a weekly partner round produces ≥3 evidence-backed proposals; a proposal without an instrument or a falsifier is refused by the gate | governance |
| R-41 | "awareness of calendar and time, book meetings with founder" | every loop reads one clock and one calendar record; a meeting is **proposed** and booked only on the founder's yes | a proposal generated at 03:00 is deferred to working hours, not dropped; a booking attempt without consent is refused and recorded | interaction |
| R-42 | "all centrally coordinated" | exactly one component creates work: the coordinator (priority + capacity + ledger) | a second creator of work items fails the gate; every work item names the coordinator decision that made it | governance |
| R-43 | "we have otto, we have face, we have fleet; fleet and face should act as mother ships — overview and total control of estate and platform" | Face and Fleet are the two HQ surfaces: whole-estate overview plus the authority to summon and assign | both render the same records (§0) and both summon through the same verb; neither holds a record of its own | interaction |
| R-44 | "headquarters where founder can summon any agent — concierge, ops, research, science, finance — assign work, get updates" | five verbs: **see, summon, assign, observe, schedule**; every named function is an addressable agent with identity | summoning each named function returns a subscribed work item and its live state; an unaddressable function is a named failure, not a silence | interaction + identity |
| R-45 | "architecturally things should be event and schedule driven for complete autonomy, and loop closing" | every loop has a trigger; nothing waits on a human to start it | an inventory of loops with trigger + budget + bound; a loop with no trigger fails the gate | governance |
| R-46 | "concierge, ops, research, science … finance" | the named functions are a roster, with finance holding budget and capacity authority | `bin/estate-roster` lists each function with its intents and its authority; a function with no intent coverage fails | identity + governance |
| R-47 | "just additional founder intents/wishes in case not captured" | the register is append-only and versioned; any founder message becomes a record, never a memory of a chat | every founder message that changes work has an intent id and a row here | intent |

**State of the second pass, measured 2026-10-25** (`ls ~/.estate/intents`, `ls bin`, `rg`):

| Req | State | Evidence | Phase |
|-----|-------|----------|-------|
| R-40 partners | **missing** | no proposal record type anywhere; agents execute intents only | 2 |
| R-41 calendar + time | **missing** | zero intents match `calendar|meet|agenda|book`; the four `calendar|meeting` hits in `bin`/`platform` are incidental words in unrelated tools | 3 |
| R-42 central coordination | **missing** | work is created by whoever is asked; no coordinator, no single creator | 1 |
| R-43 Face + Fleet as mother ships | partial | Face = `backstage/packages/app/src/modules/room` (ClaimsPanel, EfficiencyHud, HarvPanel, EstateNav); Fleet = `serve-fleetview` + `bin/fleet-regression`; no shared command contract (F-09) | 3 |
| R-44 summon / assign / observe | **missing** | `rg -l -i summon packages/app/src bin estate` returns nothing | 3 |
| R-45 event + schedule driven | partial | the bus exists (`bin/idp-agent-event-bus`, NATS `nats.event-bus.svc:4222`) and there is exactly one scheduler (`bin/idp-one-scheduler`, `scheduler-status`); no loop inventory, no trigger gate | 0 |
| R-46 roster (concierge, ops, research, science, finance) | **missing** | `~/.estate/agents` does not exist; functions are implied by intents, never addressable | 1 |
| R-47 append-only register | present | this section | — |

### 11.2 Concerns, second pass

| ID | Concern | What it costs | Answer |
|----|---------|---------------|--------|
| C-11 | partners become noise | a flood of proposals with no evidence, re-proposing what was refused last month | proposal record with instrument + falsifier + dedupe against HISTORY; a refusal is recorded with its reason so the next round does not re-propose it (C-02) |
| C-12 | calendar access is a trust boundary | an agent that can write the founder's real calendar can waste his week | consent perimeter: propose → yes → book; a per-week meeting budget; the token by name only from the vault (§4); revocation tested |
| C-13 | "total control" quietly becomes a second control plane | the HQ grows a button that bypasses the door and the estate forks again (F-01) | HQ-2/HQ-3 below: every verb is an existing intent, and the gate refuses a surface action with no intent behind it |
| C-14 | central coordination versus "all ways is a feature" (no single point of failure) | one coordinator becomes the outage | coordination is a **role**, not a machine: the ledger is the state, so if the coordinator dies the loops keep running and it catches up; a second coordinator is refused, a second ledger is impossible |

### 11.3 Finding F-09 — three surfaces, no shared command contract

Otto holds the founder's channel (the `otto-gateway` process, Telegram, NATS `nats.event-bus.svc:4222`),
Face is the backstage room surface (`backstage/packages/app/src/modules/room`: `ClaimsPanel`,
`EfficiencyHud`, `HarvPanel`, `EstateNav`), Fleet is `serve-fleetview` / `fleetview-launchd` with
`bin/fleet-regression`. Each renders a different slice; none can **summon an agent and assign
work**: `rg -l -i summon packages/app/src bin estate` returns nothing, and `~/.estate/agents` does
not exist as a roster. So R-43/R-44 are not a redesign — they are a **contract** the three
surfaces must share, plus a roster to address.

### 11.4 Headquarters — five verbs, composed from blocks that exist

The HQ is not a building and not a fourth application. It is one contract with five verbs, each
one an existing block, so nothing new is invented except the contract itself:

| Verb | What it does | Existing block it composes | New work |
|------|--------------|----------------------------|----------|
| **see** | the 720 view (§0) | facts store, greenlane status, cluster twin, live claims, `bin/estate-brief` | one JSON entry point |
| **summon** | address an agent by identity and hand it a task | intent executor (340 intents), session plane (`sb start` → Temporal), NATS bus, `otto-gateway` | `estate-roster` (R-46) |
| **assign** | turn a summon into a work item with an intent id and a cost estimate | capacity contract §6.3, tier router (#7053), door (`CEILING_SEC`) | the coordinator (R-42) |
| **observe** | live state of every work item, per agent | incident ledger (F-05 collapse), `bin/idp-greenlane status`, `bin/estate-brief` | one state record, three renderers |
| **schedule** | time and calendar awareness; propose and book a meeting | `bin/idp-one-scheduler`, `scheduler-status`, `scheduler-up` (one scheduler — never a second) | clock record, calendar record, `meeting-book` intent |

**HQ-1 One record, three renderers.** Face, Fleet and Otto render the same records. A surface
that keeps its own copy is stitching and is deleted (AGENTS.md §6).
**HQ-2 No verb without an intent.** Every HQ action resolves to a named intent; a button, voice
command or Telegram message that resolves to nothing is refused by the gate, not by a reviewer.
**HQ-3 The HQ never bypasses the door.** Authority is *which intent may run*, never *run this
instead* (F-01 is the precedent: two doors, one fix, twice the diff).
**HQ-4 The HQ is an interface, not a scheduler.** If Face, Fleet and Otto are all down, the loops
keep running and the surfaces catch up from the ledger. Availability of the HQ is never the
availability of the estate.

### 11.5 Time and calendar — the record, and the consent

```yaml
clock:    {now: <RFC3339>, tz: Europe/London, working_hours: [09:00, 18:00], quiet_hours: [21:00, 08:00]}
calendar: {source: <caldav|ics>, events: [...], observed_at: <RFC3339>, stale: <bool>}
booking:  {intent: meeting-book, state: proposed|agreed|booked|declined, agenda: <one line>,
           duration_min: 30, attendees: [founder], consent: <record id>, created_at: <RFC3339>}
```

1. **One clock.** Every loop reads the same record; an agent that reasons about a schedule it
did not read is guessing (720-1).
2. **Quiet hours are a bound on delivery, not on work.** A 03:00 finding is worked and *held*;
it is delivered at 09:00 unless severity crosses the policy threshold.
3. **A meeting is proposed first.** `meeting-book` moves `proposed → booked` only with a consent
record naming the founder's yes. A decline is recorded with its reason, so the proposing agent
learns rather than repeats (C-11).
4. **A per-week meeting budget** exists in the policy store; exceeding it needs an explicit
founder override — that is R-21 (wellbeing) expressed as a number.
5. **The calendar token is a name,** loaded from `estate-secrets`; never a value in a file or a
prompt (§4).
6. **Staleness is visible.** An unreadable calendar reads `stale: true` and the agent says so;
it does not silently assume an empty week.

### 11.6 Partners — the proposal record

```yaml
proposal:
  id: PROP-2026-11-02-04
  intent_id: INT-2026-10-25-01          # the founder wish it serves (R-47)
  claim: "greenlane latency p90 falls from X to Y"
  evidence: {instrument: <command>, measurement: <value>, window: <dates>}
  dedupe: [<graph node ids of prior attempts, or 'none found' with the query used>]
  cost: {estimate: <unit>, capacity_verdict: <admit|refuse>}
  falsifier: "<the measurement that would prove this wrong>"
  status: proposed | accepted | refused:<reason> | built | proven
```

Partners are agents with the **same** identity, memory and eval score as any worker (R-12, R-22).
A proposal is not a comment: it enters the coordinator's queue with a cost, is prioritised by the
same function as an incident (R-14), and its refusal is stored so the next round starts from it.
That refusal record is the loop closing — the difference between a partner and a chat participant.

### 11.7 Central coordination, without a single point of failure (R-42, C-14)

`PROPOSALS + INCIDENTS + SCHEDULE → coordinator (priority × capacity) → work items → door → gate → memory`

The coordinator is the **only** creator of work items. It is a role: the state it reads and writes
is the ledger, so it can be restarted, moved to another agent, or run twice in an election with no
work lost. A second *ledger* is impossible; a second *coordinator* is refused — which is how R-42
and the founder's "all ways is a feature" preference are both true.

### 11.8 Every loop, its trigger, its bound (R-45)

| Loop | Trigger | Bound | Closes with |
|------|---------|-------|-------------|
| incident | CI/greenlane/live/k8s event (NATS) | door ceiling per action; per-incident budget | fix merged + lesson in memory |
| partner proposal | weekly schedule + event (new failure signal) | proposals/week per agent; cost estimate | accepted → work item; refused → reason stored |
| review | weekly schedule | one review per repo per week | findings as tickets with owners |
| research → science | research record on the bus | experiment budget per run | prototype PR with evidence, or a recorded dead end |
| capacity | 60 s schedule + provider event | read-only | verdict per agent; refusal ticket when short |
| HQ delivery | quiet-hours boundary | meeting budget per week | founder sees it once, at the right time |

A loop with no trigger is not a loop; a loop with no bound is not governable; a loop with no
closing record is not closed (R-34).

### 11.9 Tickets for the second pass

| Ticket | Work | Acceptance test that can fail |
|--------|------|-------------------------------|
| EPIC-050 | `bin/estate-roster`: concierge, ops, research, science, finance — identity, intents, authority | a function with no covering intent makes the roster exit non-zero; summoning a listed function returns a work item id |
| EPIC-051 | HQ contract v1: see/summon/assign/observe/schedule as intents | each verb resolves to a named intent; a verb with no intent is refused (HQ-2) |
| EPIC-052 | One record, three renderers | a surface that renders a record absent from the §0 stores fails the gate; Face, Fleet and Otto show the same work-item state to within one poll |
| EPIC-053 | clock + calendar records; quiet-hours deferral | a finding produced in quiet hours is delivered at the boundary, not at 03:00; an unreadable calendar reads `stale: true` |
| EPIC-054 | `meeting-book` with consent | a booking without a consent record is refused and logged; the token is read by name only; revocation tested |
| EPIC-055 | partner proposal round | a proposal without `evidence` or `falsifier` is refused; ≥3 accepted-or-refused-with-reason per week; the refusal is retrievable next round |
| EPIC-056 | coordinator as sole work creator | two creators in one minute fails the gate; killing the coordinator mid-cycle loses no work item |
| EPIC-057 | loop inventory + trigger gate | a registered loop with no trigger or no bound fails the gate |
| EPIC-058 | finance function: owns capacity and spend | it refuses work above budget and the refusal appears as a ticket; spend above threshold reaches the founder before it is incurred |

### 11.10 What this adds to the definition of success (§8)

After Phase 4 the founder is **summoned**, not summoning: the estate proposes (R-40), books the
thirty minutes it needs (R-41), and brings evidence, a cost and a falsifier to that meeting. The
founder's job at the HQ is go/no-go — and the HQ's job is to make that the only thing he is asked
(R-23, R-44, C-05).

### 11.11 Risks added by this pass

| Risk | Why it is real | Mitigation |
|------|----------------|------------|
| proposal spam (C-11) | five partner agents × weekly rounds is a lot of text | evidence + falsifier + dedupe are required to *enter* the queue; the queue has a budget |
| calendar as the only new external trust | a write path to the founder's real week | propose-first, per-week budget, revocation test, token by name |
| HQ becomes the second control plane (C-13) | it is the natural place to put a shortcut | HQ-2/HQ-3 gates; F-01 precedent quoted in the law |
| time awareness without a trustworthy clock | drift, timezone, DST | one clock record with `observed_at`; an agent that cannot read it says so |


