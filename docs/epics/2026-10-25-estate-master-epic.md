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

---

# Part IV — the programme

*Appended 2026-10-25. §12–§21 turn §1–§11 from requirements into a programme: one record format for
every interaction and action, a coverage register tracing every wish the founder has spoken to a row and
a ticket, the substrate that makes the stack coherent, and a delivery plan whose every item must be
**operating and earning its keep** (§20, R-62) rather than specified.*

## 12. One record for every interaction and every action (the structured-format law)

**R-48 — every founder interaction is one record.** Anything the founder says or is shown — a Telegram
line, a voice turn, a Face tap, a Fleet click, a meeting, a silence that mattered — is written as an
`interaction` **before** any agent acts on it:

```yaml
interaction:
  id:          i-<ulid>
  at:          <rfc3339>          # from the clock record, never from a model
  channel:     telegram | voice | face | fleet | calendar | email | cli
  principal:   founder
  kind:        directive | question | report | approval | refusal | preference | mood | smalltalk
  about:       [<work-item id>, <agent id>, <capability id>]
  text:        <verbatim; never summarised in place>
  intent:      <intent id it became, or null>
  outcome:     <ticket / PR / job id it produced, or null>
  sensitivity: normal | personal | health | finance
  derived:     {focus: [...], memory: [...]}   # what Active Focus/Memory contributed
```

**R-49 — every agent action is one record.** The action record is the only thing a surface may render
and the only thing a review may grade. It half-exists today as the door's job log, the claim and the
gate result; the law is that the three are **one joinable record**:

```yaml
work_item:
  id:        w-<ulid>
  origin:    {interaction: i-… | schedule: s-… | event: e-… | proposal: p-…}
  goal:      <the sentence that defines done>
  owner:     <agent id>          # exactly one; the roster is R-46
  authority: <intent id>         # what it may run — never "whatever it likes"
  state:     proposed|queued|running|blocked|gate|landed|failed|refused
  bound:     {budget_s: <int>, deadline: <rfc3339>|null}
  evidence:  [<job id>, <gate id>, <sha>, <url>]
  closed_by: <the measurement that proves it, or null>
```

**R-50 — one Brain, many screens.** The founder's "mega oracle brain attached to Face and Fleet": one
query surface — the **Brain API** — over unified memory, the active-focus claim registry, the knowledge
graph, the interaction/action records, the capability catalog and the estate's state. Face and Fleet are
**renderers of Brain**; neither keeps a private store (HQ-1 restated for knowledge). A surface that
answers a founder question from its own cache is the F-09 defect returning. Otto and every other agent
read the same Brain — that is what "attached to any agent" means.

| HQ-5 | The Brain is a query surface, not a second database. It reads memory + graph + records + catalog at request time and names the store each answer came from. |
|---|---|

| id | concern | bound |
|---|---|---|
| C-15 | a second format appears (a dashboard's own JSON, an agent's own log line) | the schema is versioned in one file; a producer that cannot fill it writes `state: unknown` and fails the gate rather than being silently accepted |
| C-16 | the Brain becomes the slow path (every founder turn queries six stores) | a p95 budget per surface, cached folds where measured, and `stale: true` rather than a silent answer |

**Tickets.** EPIC-059 the interaction record and a writer in every channel · EPIC-060 the `work_item`
record joining door job, claim and gate · EPIC-061 Brain API v0 with per-store provenance · EPIC-062 the
format gate (a producer that invents a format fails).

## 13. Coverage register — every wish the founder has spoken, traced

*This is the answer to "I hope you are not missing anything". A wish is not covered because a paragraph
mentions it; it is covered when it has a row here, a ticket, and a wave. Status vocabulary:* **PROVEN**
(measured operating this pass) · **PARTIAL** (a block exists, the capability does not) · **ABSENT**
(measured missing) · **DESIGNED** (row + acceptance test, no build).

| id | the founder's words | status | the measurement behind it | row / ticket | wave |
|---|---|---|---|---|---|
| W-01 | agents as autonomous partners that propose and brainstorm | ABSENT | no `propose`/`proposal` intent in `~/.estate/intents`; no proposal record | R-40 · EPIC-055 | W3 |
| W-02 | calendar and time awareness | ABSENT | zero intents match `calendar\|meet\|agenda\|book\|time` except `scheduler-venv`; no calendar in `bin platform packages/app/src` | R-41 · EPIC-053 | W4 |
| W-03 | book meetings with the founder | ABSENT | same probe; nothing in the estate can write a calendar | R-41 · EPIC-054 | W4 |
| W-04 | central coordination of all agents | PARTIAL | one scheduler (`bin/idp-one-scheduler`), session plane (`bin/sb` → Temporal), no coordinator record | R-42 · EPIC-056 | W2 |
| W-05 | Face + Fleet as the mother-ship HQ | PARTIAL | `backstage` 1/1, `hermes-agent` 1/1; no shared command contract (F-09) | R-43 · EPIC-051/052 | W4 |
| W-06 | summon any agent | ABSENT | `rg -l -i summon packages/app/src bin estate` → nothing | R-44 · EPIC-051 | W4 |
| W-07 | assign work to an agent | PARTIAL | the session plane accepts a task; no assignment record, no capacity check | R-44 · EPIC-051/056 | W4 |
| W-08 | get updates from agents | PARTIAL | fleetview renders; there is no `work_item` record to render | R-44 · EPIC-060 | W2 |
| W-09 | concierge | PARTIAL | `concierge` declared, **0/0 running**; `concierge-task` intent exists | R-46 · EPIC-050 | W1 |
| W-10 | research scientist as a role | PARTIAL | `research-engine` declared **0/0**; `searxng` 1/1; `harv` (crates) works | R-46 · EPIC-050/071 | W3 |
| W-11 | finance as a role | PARTIAL | `cost-today` intent; no spend authority, no budget record | R-46 · EPIC-058 | W3 |
| W-12 | event-driven autonomy | PARTIAL | `event-bus` 1/1 with JetStream + PVC, `router-events` 2/2; no per-loop trigger inventory | R-45 · EPIC-057 | W2 |
| W-13 | schedule-driven autonomy | PARTIAL | `scheduler/schedule.yml` exists; no loop declares its trigger and bound | R-45 · EPIC-057 | W2 |
| W-14 | loop closing, feedback loop closing | ABSENT | `work-audit` finds LOST work; nothing writes a *closing* record | R-45 · EPIC-070 | W2 |
| W-15 | truly autonomous across all spheres (Otto, research, science, finance) | ABSENT | four roles sit at 0/0 or absent (W-09…W-11) | R-42/R-46 · EPIC-050/056 | W1–W3 |
| W-16 | founder wellbeing taken ultra seriously (goals, mood, habits, stress, priorities, health, finance, recreation) | ABSENT | no wellbeing intent, no signal store; memory + focus exist and are wired | R-53 · EPIC-064 | W1 |
| W-17 | every founder interaction classified | ABSENT | no classifier; the `interaction` record does not exist yet | R-48 · EPIC-059 | W1 |
| W-18 | unified memory + active focus involved | PROVEN | this agent's own context carries Active Memory and Active Focus; `unified-memory` 1/1 | — · EPIC-061 | — |
| W-19 | mood/habits/goals change over time, so memory and focus adapt | ABSENT | no profile, no versioning, no decay rule | R-54 · EPIC-065 | W1 |
| W-20 | Otto/Face/concierge proactively guarantee wellbeing | ABSENT | Otto gateway **degraded** (`ready=Unknown`); concierge 0/0 | R-55 · EPIC-066 | W1 |
| W-21 | expectations zealously met without the founder repeating themselves | ABSENT | no expectations ledger; this wish was spoken four times in one session — that is the measurement | R-54 · EPIC-067 | W1 |
| W-22 | estate-wide realtime broadcast, every agent gets every message, group comms | PARTIAL | the bus is proven; the only contract is `estate.news.story.json`; no broadcast channel, no fanout record | R-56 · EPIC-068 | W2 |
| W-23 | all agents and bots (Otto, JEV, k8 agents) in sync across goals, state, events, history, capabilities | ABSENT | no published agent state; Active Focus is per-agent, not shared | R-57 · EPIC-069 | W2 |
| W-24 | harmonised shared realtime knowledge and collaboration | ABSENT | no shared knowledge feed; `hindsight` **degraded** (`ready=False`) | R-57 · EPIC-069 | W2 |
| W-25 | architectural coherence and congruence as a headline; where Temporal sits beside NATS/JetStream | DESIGNED | `temporal` 6/6 pods, `temporalio/server` + `postgres12_pgx`, 512 shards; JetStream + PVC; §14 assigns one job per plane | R-51/R-52 · EPIC-073 | W0 |
| W-26 | capacity accounts — what is needed from the founder | — | a founder answer, not a build: §21 | R-58 · §21 | now |
| W-27 | film integration in Fleet and Face | DESIGNED | `docs/specs/2026-10-23-estate-as-movie-director-engine.md` S0–S4; no build | R-59 · EPIC-077 | W5 |
| W-28 | virtual world vs realtime film; avatars; the founder opens the real URL | DESIGNED | `docs/research/2026-10-25-virtual-world-vs-realtime-film.md`: film first, world as a renderer, the URL is the evidence | R-59 · EPIC-078 | W6 |
| W-29 | discovery | PARTIAL | `harv` harvests crates with signed evidence; `search-text`; `searxng` 1/1; no discovery loop over the estate's own gaps | R-60 · EPIC-074 | W3 |
| W-30 | metrics | PARTIAL | `monitoring` 5/5, `metrics-server` 1/1; `coroot` frozen, **3/6 not ready** | R-62 · EPIC-075 | W0 |
| W-31 | identity | PARTIAL | `identity` 2/2 operating; **`spire` frozen** — 6/6 running yet undeclared (F-10) | R-52 · EPIC-073 | W0 |
| W-32 | intelligent routing, with capacity planning inside routing | PARTIAL | `llm` namespace **degraded** (`ready=False`, 5/5); `router-events` 2/2; routing takes no capacity input | R-61 · EPIC-076 | W3 |
| W-33 | harnesses | PARTIAL | the estate's own harness (`~/.estate/harness/cc`); `agent-workforce` declared **0/0 running** | R-60 · EPIC-074 | W3 |
| W-34 | evals, judges, evaluation of judges (JEV) | PARTIAL | `platform/eval/pareval_layer.py`; `jev.decide`/`jev-setup` intents exist; no judge-of-judges record | R-63 · EPIC-074 | W3 |
| W-35 | red team | ABSENT | no red-team intent; `trivy` frozen (supply-chain scan only) | R-63 · EPIC-074 | W3 |
| W-36 | recursive self-improvement | ABSENT | no self-modification path — the door refuses it by design; needs a bounded row, not a loophole | R-64 · EPIC-074 | W6 |
| W-37 | surfacing errors across the stack | PARTIAL | five **degraded** layers simultaneously (`estate-db`, `hindsight`, `llm`, `otto-gateway`, `otto-golden-secret`), `coroot` 3/6, three role-planes with 0 pods — and the founder was not told (F-11) | R-62 · EPIC-075 | W0 |
| W-38 | CI/CD and raising tickets autonomously | PARTIAL | `bin/idp-ci`, `claim-gate`, `feature-request-plan` run; nothing files a ticket from a failure without a human | R-65 · EPIC-075 | W0 |
| W-39 | date/time awareness (asked twice) | ABSENT | no clock record; the founder asked twice because nothing could tell them the date | R-41 · EPIC-053 | W4 |
| W-40 | context awareness | PARTIAL | Active Memory/Focus per agent; no context packet per work item | R-48 · EPIC-061 | W1 |
| W-41 | research → planner → executor pipeline | PARTIAL | `research-engine` 0/0, planner absent, executor proven (the door) | R-60 · EPIC-071 | W3 |
| W-42 | structured formats for every interaction and agent action | DESIGNED | §12 schema; no writer, no gate yet | R-48/R-49 · EPIC-059/060 | W1 |
| W-43 | proper programme/delivery management, strategy, to be the leading agentic platform | DESIGNED | §20 waves + exit criteria; §21 the founder's inputs | R-66 · §20 | now |
| W-44 | review other harnesses ("zero edge", Agent Workforce) and pick the best bits | PARTIAL | `zeroedge` **is the estate's own** gateway (incubating, off without `ZEROEDGE_URL`), `agent-workforce` declared 0/0, isolation ladder reports `temp_tree`; §18 names the mechanism each contributes (F-13) | R-60 · EPIC-074/076 | W3 |
| W-45 | everything must be working and earning its keep | DESIGNED | R-62: no ticket closes on a document; every wave exits on an operating state plus a number | R-62 · §20 | every wave |
| W-46 | one mega oracle brain attached to Face, Fleet, Otto and any agent | DESIGNED | §12 R-50/HQ-5: one Brain API, many screens, six stores of record | R-50 · EPIC-061 | W1 |

**The traceability rule.** A founder wish that is not in this table is not in the programme. A row
without a ticket is a note; a ticket without a wave is a wish. When a new wish arrives, §13 grows by a
row first, then the ticket, then the wave — never the other way round. A row whose status is PROVEN
carries the measurement that proved it; a row with no measurement is ABSENT by definition.

## 14. The substrate — where each technology sits, and where it may not

The founder's question — *where does Temporal come in, alongside NATS/JetStream?* — has one answer in
one table. Every state below is measured this pass (`estate-inventory`, 2026-10-25); a technology with
no job in the table has no job in the estate.

| Plane | The one technology | What it does | What it must never do | State (measured) |
|---|---|---|---|---|
| **Time / durable orchestration** | **Temporal** (`platform/temporal/temporal.yaml`) | long-lived, resumable, budgeted, approval-gated **sessions**: work that survives a laptop closing, retries a step, holds a timer for days. `bin/sb` is the client; `sovereign/engine/workflow.py` holds `SessionWorkflow` | schedule ordinary work (that is the scheduler), carry founder-facing events (that is the bus), or become the state of record (that is Postgres) | `temporal` **6/6 pods**, `temporalio/server`, persistence `postgres12_pgx`, `numHistoryShards: 512` |
| **Events / replay** | **NATS JetStream** (`platform/event-bus/nats.yaml`) | the spine: every fact that happened, replayable, at-least-once, file-store PVC; consumers fan out to Otto, Face, Fleet, the Brain and any agent | be the source of truth (a stream is a log, not a table), or hold a founder decision unrecorded | `event-bus` **1/1**, `jetstream:` configured with a PVC, `platform/messaging/dlq` for poison messages |
| **State of record** | **Postgres** (`platform/estate-db`, `platform/temporal/postgres.yaml`, `platform/unified-memory-server`) | rows that are queried and joined: work items, interactions, approvals, memory, claims, calendar | carry high-frequency event traffic (JetStream), or become a second copy of another store | `estate-db` **degraded** (`estate-db-migrate ready=Unknown`); `unified-memory` 1/1 |
| **Execution** | **the door** (`mcp/plugins/estate_executor.py`, `~/.estate/intents/*.yaml`) | every action, named, budgeted (100s ceiling), logged, refused when unclaimed | be bypassed by a renderer, a workflow, or an agent with a shell | 340 intents; the door **refused this very session** at a 1.5 GB disk floor — the door working |
| **Clock** | **the clock record** (new, R-41) | `now`, `tz`, `observed_at`, `drift`, `stale` — the only place time comes from | be read from a model's guess or a container's unset `TZ` | ABSENT |
| **Knowledge** | **the Brain** (R-50) | one query surface with provenance per answer | keep a private copy per surface | memory 1/1, graph via `growmos`, records ABSENT |

**R-51 — Temporal carries sessions; it never owns schedules.** A session is work that must survive time
(hours to days, a budget, an approval, a laptop that closes). A schedule is a cron expression that starts
a session or an intent. A schedule hidden inside Temporal cannot be found by the estate's one scheduler;
a resumable session put in cron is lost on reboot. The two are complements with a hard boundary:
**cron decides *when*, Temporal carries *through*, JetStream records *that*, Postgres remembers *what*,
the door does *it*.**

**R-52 — one writer per plane.** Each plane has exactly one writer role. An agent writes to Postgres only
through the intent that owns that table, publishes to JetStream only through the bus client, starts work
only through the door, and reads time only from the clock. Two writers on one plane is the duplicate
layer of AGENTS.md §6, one level down.

| id | finding | evidence |
|---|---|---|
| **F-10** | **identity runs twice**: `spire` is 6/6 running yet `frozen`/orphan-owner, while `identity` is declared and operating — two identity planes, one unmanaged | `estate-inventory`, 2026-10-25 |
| **F-11** | **the estate did not tell the founder that five layers were degraded** — `estate-db`, `hindsight` (`ready=False`), `llm` (`ready=False`, 5/5), `otto-gateway` (`ready=Unknown`), `otto-golden-secret`; `coroot` frozen at 3/6 not-ready; `agent-workforce`, `concierge`, `research-engine` declared with **zero pods** | `estate-inventory`, 2026-10-25 |

**F-11 is the sharpest fact in this document.** The founder has been asking for error surfacing across
the stack (W-37) while three role-planes stood empty and the founder's own gateway was degraded.
Surfacing is not a dashboard; it is a **push** that reaches the founder without being asked (EPIC-075).

| id | concern | bound |
|---|---|---|
| C-17 | Temporal and the scheduler both hold timers, so a job can run twice | one owner per timer, an idempotency key on every workflow start, and a duplicate-run metric |
| C-20 | the Brain and Postgres disagree about the same fact | the plane that owns the fact is named in the schema; the other plane reads through it, never beside it |

**Tickets.** EPIC-073 substrate proof: a written plane-ownership table enforced by a gate that fails when
a new writer targets a plane it does not own; F-10 and F-11 closed by measurement, not by a note.

## 15. Founder wellbeing as a scored capability

The instruction was not "add a wellbeing page". It was: take wellbeing, goals, moods, preferences,
habits, stress, priorities, concerns, recreation, health and finance **as seriously as everything else**,
classify **every** interaction, involve unified memory and active focus, adapt as the founder changes,
and have Otto, Face and the concierge *guarantee* expectations are met without the founder repeating
themselves. Four rows carry it.

**R-53 — wellbeing is a scored capability, not a sentiment.** Six signals, each with a writer and a
number, in one `founder_state` record (Postgres) with `observed_at` on every field:

| signal | written by | measured as | never |
|---|---|---|---|
| mood / stress | Otto (voice, Telegram), Face (check-in), concierge | a 1–5 self-report plus **behavioural proxies** (late-night turns, repeated asks, escalation rate, refusal rate) kept as evidence | inferred as a medical judgement, or echoed back as a label the founder did not choose |
| goals / priorities | founder statements, weekly review | an ordered list with a horizon and the work items serving each | silently reordered by an agent without a record |
| preferences | interaction records | typed preferences with provenance and a decay date | overwritten by a later inference without a diff |
| habits / rhythms | interaction timestamps only | quiet hours, working windows, meeting tolerance per week | used to predict health |
| concerns / open loops | the expectations ledger (R-54) | each with an owner agent and a promised date | dropped without a closing record |
| finance / capacity | the finance role (R-46), `cost-today` | spend and runway against the work queue | exposed to a surface without a sensitivity tag |

**R-54 — the expectations ledger, and the repeated-wish alarm.** Every promise made to the founder —
"I will re-run that", "the release lands today", "I will check in Thursday" — is a row: `promise`,
`owner`, `due`, `evidence`, `state`, `closed_by`. The founder repeating a wish is the ledger's failure
metric: **a repeated wish files a bug against the agent that dropped it.** W-21 exists because this
programme was asked for four times in one session; that repetition is the measurement, not a
coincidence.

**R-55 — proactive duty, with a rate limit.** Otto, Face and the concierge each own a duty cycle: read
`founder_state`, read the ledger, read the estate's degraded layers (F-11), then act — one nudge, one
resolved promise, one surfaced failure. Proactivity is bounded: quiet hours are respected (R-41), a
nudge with no new information is refused, and every proactive message cites the record that caused it.
"Guaranteed" means *closed by evidence*, never *feels attentive*.

| id | concern | bound |
|---|---|---|
| C-18 | wellbeing data is the most sensitive store in the estate | keys by name only from the vault, field-level sensitivity tags, a consent record per field class, and a deletion path that provably deletes |
| C-21 | the estate starts optimising the founder instead of serving them (nudging toward what is measurable) | every inferred preference needs consent to be inferred; the founder can freeze a field and the estate must still work |

**Tickets.** EPIC-063 the wellbeing store's consent record, sensitivity tags and deletion path ·
EPIC-064 `founder_state` and its writers · EPIC-065 adaptation (preference decay, goal-drift
detection, a diff every time the estate changes its mind about the founder) · EPIC-066 duty cycles for
Otto/Face/concierge · EPIC-067 the expectations ledger and the repeated-wish alarm.

## 16. Broadcast and shared realtime knowledge

**R-56 — one bus, one broadcast, every agent a subscriber.** The estate already has the bus (measured:
`event-bus` 1/1 with JetStream). What it does not have is a **broadcast** — a subject every agent
subscribes to, carrying founder directives, estate-state changes, incidents, queue changes and
capability changes, each with an id and a cursor so an agent can prove what it has seen.

```
broadcast  (JetStream, one subject per class, retained)
  ├─ founder.directive     the founder said something; every agent must know it happened
  ├─ estate.state          a layer changed state (operating/degraded/frozen) — F-11 made live
  ├─ estate.incident       something is broken: layer, symptom, owner
  ├─ work.queue            work items opened, assigned, closed (R-49)
  ├─ capability.changed    the intent catalog changed; agents re-read their authority
  └─ knowledge.digest      the shared fold: goals, priorities, open loops, history (R-57)
```

Each agent keeps `last_seen_cursor` per subject. The **staleness metric** — `now − last_seen_cursor`
per agent per subject, published to monitoring — is what makes "in sync" measurable: an agent acting on
knowledge older than its bound is *stale*, and a stale agent's work is suspect by definition. This is
also the missing piece behind the face app's false "12 agents running" incident: a counter with no
cursor and no reconciliation is a number that can only drift.

**R-57 — shared knowledge is a fold, not a copy.** Every agent reads the same fold — goals, priorities,
open loops, current events, history, capabilities — computed by the Brain (R-50) from memory + graph +
records + catalog. No agent keeps a private version of the estate's purpose; a private copy is the
synchronisation bug, pre-installed. Collaboration then means one thing: two agents act on work items
that name each other, with the fold as the shared referent.

| id | concern | bound |
|---|---|---|
| C-19 | broadcast becomes noise — every agent acts on every message | each subject has an **addressed** class (must act) and an **observed** class (must know); only addressed messages may wake an agent |
| C-22 | the fold becomes a stale oracle nobody trusts | the fold carries `computed_at` and per-source `as_of`; a consumer that needs fresher reads the source, and the Brain says which |

**Tickets.** EPIC-068 broadcast channels and per-agent cursors · EPIC-069 the knowledge fold, the
staleness metric and one agent-state publisher · EPIC-070 loop closing: every trigger writes its closing
record, and `bin/work-audit` gains a `CLOSED` verdict beside LOST/PARTIAL/REMOVED/LANDED.

## 17. Research → planner → executor, with evals, judges and red team in one pipeline

The founder's pipeline, with one home per stage — this is the structure that stops the estate building
a fourth research loop:

```
discovery ──► research ──► planner ──► proposal (R-40) ──► door (execution) ──► gate ──► closing record
   │             │            │                               │                    │
   └── harv ─────┘            └── capacity (R-61)            └── job log          └── eval + judge + red team
```

| stage | exists today (measured) | ticket |
|---|---|---|
| discovery | `harv` (crates, signed evidence), `search-text`, `searxng` 1/1 | EPIC-072: a discovery loop that targets §13's ABSENT rows, not a fresh crawl of the internet |
| research | `research-engine` **0/0**; the arXiv/GitHub probe pattern used for this pass | EPIC-071: a research role that must cite a **probe** (a command and its output), never a memory |
| planner | absent | EPIC-060: plans are work items with bounds, produced from the fold (R-57) |
| proposal | absent (R-40) | EPIC-055 |
| execution | **proven** — the door | — |
| gate | proven (`bin/idp-ci`, claim-gate, fast-gate) | — |
| eval | `platform/eval/pareval_layer.py` | EPIC-074: evals as **gate steps**, with a baseline and a score, not a notebook |
| judges | `jev.decide`, `jev-setup` intents | **R-63** below |
| red team | ABSENT (only `trivy`, which is frozen) | EPIC-074 |

**R-60 — a claim without a probe is a memory, and memory is not evidence.** The research role's output is
a digest with the command that produced each fact (the pattern of
`docs/research/2026-10-25-virtual-world-vs-realtime-film.md`, Appendix A). A digest with no probe column
is refused by the research gate.

**R-61 — capacity is an input to routing, not a post-mortem.** Every route decision (which model, which
agent, which machine) carries: tokens/spend remaining, the queue depth, the p95 of the last N runs, and
the founder's declared priority order (§21). A router that cannot see capacity is choosing by vibes, and
`llm` sitting **degraded (ready=False, 5/5)** is what its absence looks like.

**R-63 — the judge is judged.** JEV scores a decision; something must score JEV. Every judge has a
held-out set, an agreement rate against human verdicts, and a **known-failure list**. A judge that has
never disagreed with itself is not calibrated. Red team's job is to attack the *judges first* — a
compromised judge silently blesses everything downstream.

**R-64 — recursive self-improvement is a bounded loop, never an open one.** The estate may propose
changes to its own prompts, orderings and heuristics; it may not change its own authority (the door, the
gates, the registers) without a founder approval recorded as an interaction. The bound is what makes
self-improvement safe to run continuously: it improves **within** the constraint, and the constraint only
moves with a human signature.

| C-23 | evals and judges become a second gate nobody reads | eval results attach to the work item's `evidence` and a failing eval blocks like any other gate |
|---|---|---|

## 18. Other harnesses — a measured review, not an opinion

The founder asked for a review of other harnesses ("zero edge", Agent Workforce, and the like) and for
picking the best bits. The state of that research is the table below: every cell is a probe run this
pass, and where a name turned out to be **the estate's own component**, that is said rather than
searched for on the internet (R-60 — a probe beats a recollection).

| candidate | what the probe found | verdict |
|---|---|---|
| **"Zero Edge" = `zeroedge`** | it is **the estate's own**: `~/Documents/code/zeroedge-repo` (27 Python files), "a provider-agnostic, drop-in LLM cost-optimization gateway — canonicalise, compress, cache, budget, route"; deployed as `platform/llm/zeroedge.yaml` + `zeroedge_gateway.py`, image pinned by `platform/image-automation/zeroedge.yaml`; classified `incubating` in `docs/synthesis/factory-inventory.md` and "off unless `ZEROEDGE_URL` is set"; catalogued in `docs/specs/2026-10-23-harness-inventory-and-how-a-harness-is-swapped.md` §4 | **adopt the mechanisms, delete the second layer.** Cache, compression, per-key budget and route-scoring fold into the one router (R-61); two routing/cost layers beside each other is AGENTS.md §6's duplicate layer. Ticket: EPIC-076 carries the four mechanisms explicitly |
| **Agent Workforce** | `agent-workforce` is the estate's own crewAI crew on a `*/15` CronJob; measured declared **0/0 running** and, in the 2026-10-23 inventory, `Running 0/1` after 21 minutes | take: a workforce plane is worth having — the estate declared one and never staffed it. **Staff the plane or delete the declaration** (EPIC-050/EPIC-074), and do not buy a crew to run beside an empty one |
| **the estate's own harness stack** | `~/.estate/harness/cc` drives jobs; `bin/idp-ci` is the gate; `hypotheses.race`, `code-review`, `work-audit` are intents; `platform/executor/sandbox.py` reports `ISOLATION_KIND=temp_tree` on this laptop, i.e. the weakest rung | keep as the base — it already holds the door, the claims and the gates — and fix its substrate honestly: the isolation ladder's top rungs are unreachable on macOS, so the estate must *say* `temp_tree` rather than imply a sandbox |
| **external harnesses (firecracker / gVisor / vcluster / kronos)** | `firecracker` unreachable (no `/dev/kvm`); gVisor namespace declared and **used by nothing** (91 files mention it); vcluster used for shadow clusters (79 files); `kronos` is a Rust spec with ring0 named `firecracker-run` as a placeholder | adopt **mechanisms**, not products: the ring ladder (`kronos`) as the *documented* isolation ladder, vcluster for cluster-side isolation, and an explicit refusal (`UNKNOWN_SANDBOX_<name>`) instead of a silent default — which the estate already has in `factory/sandbox.py` |

| id | finding |
|---|---|
| **F-13** | the estate runs **two routing/cost layers** — the platform's router and `zeroedge` (incubating, off without `ZEROEDGE_URL`) — while the `llm` namespace that hosts both is **degraded** (`ready=False`, 5/5). The routing plane is the one the founder asked to make intelligent (W-32), and it is currently broken *and* duplicated |

**The rule the review establishes:** a harness is adopted for a *named mechanism* it does better (a
cache, a budget, a ring ladder, a crew shape), with the mechanism written into a row that names where it
lands. "Best bits" is never a vibe; it is a list of mechanisms with the ticket that adopts each one —
and when the "other" harness turns out to be the estate's own, the honest move is to finish or delete
it, not to cite it as external.

## 19. Film, realtime visuals, and the virtual world — decided on evidence

Two founder wishes meet here and must not be conflated: **film integration in Fleet and Face** (W-27,
cinematic rendering of what the estate is doing) and **a realtime virtual world** where avatars mirror
estate work, the founder watches an agent write code and ship, and can open the real browser URL (W-28).

**R-59 — film first, world as a renderer, the URL as the proof.** The full reasoning, the tooling sweep
and the kill criteria are in `docs/research/2026-10-25-virtual-world-vs-realtime-film.md` (this pass,
with its probe appendix, §Appendix A). The decision it supports, stated here so the programme carries it:

1. **The film is the interface of record** — the estate already has the spec
   (`docs/specs/2026-10-23-estate-as-movie-director-engine.md`, S0–S4) and a proven render pipeline
   (`bin/estate-render-pages`: self-contained HTML, data inlined, no server). Ship that first; it needs no
   new runtime and no founder-supplied asset budget.
2. **The world is a renderer over the same records**, not a second estate. Its scenes read `work_item`
   (R-49) and the fold (R-57); if it invents its own state it is the duplicate layer of AGENTS.md §6.
3. **The founder's acceptance test is a URL**, and specifically: a real deployment URL opened in the real
   browser, reached from inside the world, at the moment the estate shipped it. A world that cannot
   open the real URL is a screensaver.

| id | finding |
|---|---|
| **F-12** | the estate's cinematic ambition has been specified twice (movie spec 2026-10-23, this pass) and built zero times; meanwhile the *rendering* primitive that would carry it (`bin/estate-render-pages`) exists and works. The gap is sequencing, not capability |

**Tickets.** EPIC-077 film surface in Fleet/Face over `work_item` + fold · EPIC-078 world renderer spike
with the URL acceptance test · EPIC-079 avatars as a projection of the roster (R-46) with no second
identity · EPIC-080 the kill criteria: if the world cannot show a *real* job landing inside its own wave,
it is demoted to a renderer target and the film keeps the surface.

## 20. Delivery plan — waves, exit criteria, and the rule that makes "done" mean operating

**R-62 — a capability is shipped only when it is operating and earning its keep.** Four conditions, all
four required, checked in the wave's own exit test:

1. **operating** — it appears in `estate-inventory` in a non-frozen, non-degraded state, with pods/units running;
2. **a number** — it writes at least one metric or record that can be read (`observed_at`, a count, a p95);
3. **a consumer** — something else in the estate reads it (a surface, an agent, a gate). An unconsumed record is a log;
4. **a cost line** — what it spends (tokens, CPU, founder attention) is known and bounded.

A ticket that closes on a document, a spec or a green gate alone is **not** closed under this rule. That
is the difference between *built* and *operating* that AGENTS.md §3 already demands, and it is why every
row in §13 carries a status rather than a date.

| wave | theme | tickets | exit criteria (all measured, not asserted) |
|---|---|---|---|
| **W0** — *the estate tells the truth* | honesty before ambition | EPIC-073 (plane ownership), EPIC-075 (surfacing + failure→ticket), F-10, F-11 | (a) `estate-inventory` shows **zero** layers in `degraded` with `ready` unknown/False, or each is declared frozen **with a written reason**; (b) `spire` and `identity` have one owner; (c) three empty role-planes (`concierge`, `research-engine`, `agent-workforce`) are either staffed or removed; (d) a deliberately broken probe reaches the founder as a **push** within one minute and files a ticket carrying the evidence |
| **W1** — *one record, and the founder known* | §12 + §15 | EPIC-059, 060, 061, 062, 063, 064, 066, 067, 050 | (a) 100% of founder-directed interactions in the window exist as `interaction` records with `outcome`; (b) every job the door ran in the window joins to a `work_item`; (c) Brain answers a founder question naming its store; (d) `founder_state` has all six signals with `observed_at` and a consent record; (e) the ledger closes ≥90% of promises by `due`, and a repeated wish files a bug automatically; (f) the concierge answers one real founder turn end to end |
| **W2** — *the estate in sync* | §16 + coordination | EPIC-068, 069, 070, 056, 057 | (a) every registered agent publishes `last_seen_cursor` and a digest is stamped ≤ its bound; (b) a founder directive broadcast reaches every agent (proven by cursor advance) within seconds; (c) the loop inventory lists every autonomous loop with trigger + bound, and `bin/work-audit` reports `CLOSED` for a loop that ran; (d) the coordinator record exists and one real assignment moves a work item through `queued → running → gate → landed` |
| **W3** — *autonomy that earns its keep* | §17 | EPIC-071, 072, 074, 076, 058, R-61, R-63, R-64 | (a) the research role produces a digest whose every fact carries a probe, and the gate refuses one that does not; (b) finance reports spend/runway against the queue and one routing decision is visibly changed by capacity input; (c) evals run as gate steps with a baseline score; (d) JEV's agreement rate is measured on a held-out set and a deliberately wrong judge is caught; (e) red team finds at least one real defect and it is fixed and re-tested; (f) the harness review adopts ≥1 named mechanism per adopted candidate |
| **W4** — *the HQ the founder can command* | §9 HQ + clock | EPIC-053, 054, 051, 050, 056 | (a) a clock record answers *what is the date, what is the time, what is my next meeting* with `observed_at`, and DST/zone changes are handled in a test; (b) the founder books a real meeting through an intent, propose-first, and can revoke it; (c) one command contract serves Face and Fleet with no divergence (the same JSON, asserted in a test); (d) the founder summons an agent and sees it appear, addressed, in the roster; (e) an assignment lands as a `work_item` with an owner and a bound |
| **W5** — *the film* | §19 (1) | EPIC-077 | (a) Fleet and Face render live `work_item` data through the existing render-pages pipeline; (b) a real job landing in production is visible as a scene within the same session, with the real PR sha and a real log line; (c) the film costs no new runtime and no founder-supplied assets |
| **W6** — *the world, on trial* | §19 (2)(3) + R-64 | EPIC-078, 079, 080 | (a) a world renderer reads the fold and `work_item`, holding no state of its own (proven by killing the world and losing nothing); (b) **the URL test**: from inside the world the founder opens the real deployment URL of a real ship, in a real browser, and it serves; (c) avatars are a projection of the roster with no second identity; (d) self-improvement runs one loop inside its bound and its proposed change is approved or refused as an interaction record. **Kill criterion:** if the URL test fails twice, the world is demoted to a renderer target per EPIC-080 and the film keeps the surface |
| **W7** — *continuously* | steady state | §13 upkeep, R-62 | the register is re-read every week against `work-audit`; every row is PROVEN or DESIGNED with a ticket; zero rows silently ABSENT without a ticket; the estate's own dashboard shows the four R-62 conditions per shipped capability |

**Sequencing is not negotiable in one direction:** a later wave may be *designed* early, but nothing in W2+
may claim "operating" while W0's exit criteria are false. The estate has been here before — three
role-planes declared empty while the founder asked for autonomy — and the cure is order, not effort.

**R-65 — a failure files its own ticket.** A gate failure, a degraded layer, a stale agent or a refused
action opens a ticket automatically, owned by the agent that sees it, carrying the evidence (job id, gate
id, log line) and linking the `work_item` it broke. The founder never files a bug about the estate; that
is what W-38 and F-11 mean together.

**R-66 — programme discipline: one register, one record, one gate.** One coverage register (§13), one
record format (§12), one verification gate (`bin/idp-ci`), one weekly audit (`work-audit` + §13 statuses).
A wave cannot open until the previous wave's exit criteria are true **or** a written waiver exists as an
interaction record signed by the founder. Waivers are visible in §13; silent slippage is not a status.

| risk | why it is real here | mitigation |
|---|---|---|
| **breadth** — eleven planes and forty-six wishes at once | the estate's own history: five to ten copies of the same capability | the register *is* the dedupe; one ticket per row; a new row requires a refused-or-adopted decision against §13 |
| **role-planes stay empty** (W-09…W-11 at 0/0) | three planes already sit declared and unstaffed | W0 closes them by staffing or deleting; an unstaffed declared plane is a planned failure |
| **wellbeing becomes surveillance** | the most sensitive store, written by agents | C-18/C-21: consent per field class, freeze, deletion path, no inference without consent |
| **the record format becomes a religion** (schemas over shipping) | the founder's complaint about structure is about *coherence*, not ceremony | the format is one file, versioned, and the format gate is a single CI step; producers fill it or say `unknown` |
| **the world eats the programme** | cinematic surfaces are the most attractive build and the least load-bearing | R-59 sequencing + EPIC-080 kill criterion + W5 ships before W6 starts |
| **local network/disk fragility** (door refusals this pass) | the door refused work at a 1.5 GB disk floor during this very session | disk-free intent already exists; W0 adds the founder-visible push when a door refusal happens |

## 21. What only the founder can supply (capacity accounts, R-58)

Everything above is buildable by agents inside existing authority. These eight items are **not** — they
need a founder decision, and each one unblocks a named row. They are asked once, in one place, so the
founder never has to repeat themselves (R-54).

**R-58 — capacity is asked for once, as an account.** A request for founder input is a row in this table
with four fields: *what* is needed, *why only the founder* can give it, the *format* it must arrive in,
and *which row it unblocks*. An agent that asks the founder for anything outside this table is creating
work, not requesting capacity — and the ask is refused by review. This is the accounting side of R-33
(the capacity contract): the estate's own capacity includes the founder's attention, and it is spent
deliberately or not at all.

| # | the supply | why only the founder | format | unblocks |
|---|---|---|---|---|
| 1 | **calendar truth**: the real calendars, and the booking policy (who may propose, what may auto-book, quiet hours) | it is the founder's actual week, not a data source | a list of calendar ids by name (vault) + a one-line policy | W-02, W-03, EPIC-051/052 |
| 2 | **wellbeing thresholds and consent**: which fields may be inferred vs must be asked, what is never stored | consent cannot be delegated to an agent | a per-field `ask / infer / never` table | W-16, W-19, C-18/C-21 |
| 3 | **quiet hours and channels**: when not to be interrupted, and on which channel a push may arrive | it is the founder's attention | a window per day + channel order | R-55, W-20, EPIC-075 |
| 4 | **which URLs count as "the real app"** for the world's URL test — production only, or staging too | it is the founder's own definition of "shipping" | a list of allowed hosts | W-28, EPIC-078 |
| 5 | **model/spend budget**: the monthly ceiling and any provider preferences | it is money, and routing needs the number (R-61) | a ceiling + a preference order | W-32, EPIC-076 |
| 6 | **the acceptance surface**: film first, or is the world the acceptance test from day one | the founder's own test of "I want to *see* it" | one sentence | W-27, W-28, EPIC-077/078 |
| 7 | **what may be automated without asking**: the list of actions the estate may take unattended (e.g. restart a degraded pod, open a PR, book a 30-minute slot) | authority is the founder's to grant (R-64) | an allow-list of intents | R-64, W-15 |
| 8 | **priority order of the spheres**: Otto, research, science, finance — what matters most when they compete for capacity | only the founder ranks their own goals | an ordered list | W-15, R-61, EPIC-053 |

**The answer to "is anything missing?"** — §13 is the register: forty-six spoken wishes, each with a
status measured this pass, a row, a ticket and a wave. Eight of them need the founder (§21). The other
thirty-eight are unblocked and ordered. **Nothing in the founder's words is untraced**, and every trace
ends in a measurement rather than a paragraph.

## 22. Ticket index — every row above, as work with a failing test

EPIC-050…058 are defined in §11.9. These are the part-IV tickets, each with the acceptance test that
**can fail**. A ticket with no failing test in its description is not ready to start.

| Ticket | Work | Acceptance test that can fail | Wave |
|---|---|---|---|
| EPIC-059 | `interaction` record + a writer in every channel (telegram, voice, face, fleet, calendar, email, cli) | a founder turn on any channel with no `interaction` row fails the gate; `at` is rejected when it does not match the clock record | W1 |
| EPIC-060 | `work_item` record joining door job + claim + gate result | a door job in the window with no joinable `work_item` fails; `closed_by` empty on a `landed` item fails | W1 |
| EPIC-061 | Brain API v0: one query over memory + graph + records + catalog, provenance per answer | an answer with no `store` provenance is refused; a surface holding a private cache fails review | W1 |
| EPIC-062 | the format gate | a producer emitting an unversioned shape fails `bin/idp-ci`; `state: unknown` is accepted only with a reason field | W1 |
| EPIC-063 | wellbeing store: consent per field class, sensitivity tags, deletion path | a write without consent is refused; a deletion request removes every copy and the test proves it by query | W1 |
| EPIC-064 | `founder_state` with six signals and `observed_at` | a signal with no writer or no `observed_at` fails the schema check; a stale signal reports `stale`, not a guess | W1 |
| EPIC-065 | adaptation: preference decay, goal-drift detection, a diff per change | an inferred change without a diff is refused; a preference past its decay date stops being applied | W1 |
| EPIC-066 | duty cycles for Otto, Face, concierge | a proactive message that cites no record is suppressed in test; a nudge inside quiet hours is deferred to the boundary | W1 |
| EPIC-067 | expectations ledger + repeated-wish alarm | a promise past `due` with no `closed_by` opens a bug against its owner; the same wish twice files exactly one bug | W1 |
| EPIC-068 | broadcast channels + per-agent cursors | an agent whose cursor is older than its bound is reported stale; a directive broadcast unread by any agent shows up as a named gap | W2 |
| EPIC-069 | the shared knowledge fold + one agent-state publisher | a consumer reading a fold older than its bound is refused; killing an agent's cache changes no decision | W2 |
| EPIC-070 | loop closing: every trigger writes its closing record; `work-audit` gains `CLOSED` | a loop that ran with no closing record is reported; `CLOSED` is asserted only with an evidence id | W2 |
| EPIC-071 | research role that must cite a probe | a digest with a fact lacking (command, output) is refused by the research gate | W3 |
| EPIC-072 | discovery loop targeting §13's ABSENT rows | a discovery round that reports no new source for an ABSENT row is reported as a finding, not silence | W3 |
| EPIC-073 | substrate plane-ownership table, enforced | a new writer targeting a plane it does not own fails the gate; `spire`/`identity` resolve to one owner | W0 |
| EPIC-074 | evals as gate steps; judge-of-judges; red team; harness mechanism adoption | a failing eval blocks a merge; a deliberately wrong judge is caught by JEV's own score; a red-team finding is re-tested | W3 |
| EPIC-075 | surfacing: push on degraded/stale/refused, and failure files its own ticket | a deliberately broken probe reaches the founder within one minute with the log line; a gate failure opens a ticket with evidence and an owner | W0 |
| EPIC-076 | routing with capacity input — adopting `zeroedge`'s four mechanisms (cache, compression, per-key budget, route scoring) into the one router | a routing decision made without capacity data is refused in test; a capacity change visibly changes the route; a second routing layer beside the first fails the one-of-each gate | W3 |
| EPIC-077 | film surface in Fleet and Face over `work_item` + fold, through `bin/estate-render-pages` | a scene showing a job not in the records fails; a landed job renders with its real sha and log line | W5 |
| EPIC-078 | world renderer spike reading the fold and `work_item`, holding no state | killing the world loses no state; **the URL test** opens a real deployment URL in a real browser from inside the world | W6 |
| EPIC-079 | avatars as a projection of the roster (R-46) | an avatar with no roster entry is refused; changing a roster entry changes the avatar with no second edit | W6 |
| EPIC-080 | world kill criteria | two failed URL tests demote the world to a renderer target, recorded as an interaction — and the film keeps the surface | W6 |

**Register map.** §13 rows → tickets: W-01→055 · W-02/W-03→053/054 · W-04→056 · W-05→051/052 ·
W-06/W-07/W-08→051/056/060 · W-09/W-10/W-11→050/071/058 · W-12/W-13/W-14→057/070 ·
W-15→050/056 · W-16…W-21→063…067 · W-22/W-23/W-24→068/069 · W-25/W-31→073 · W-27/W-28→077/078 ·
W-29/W-33/W-34/W-35/W-36/W-44→072/074 · W-30/W-37/W-38→075 · W-32→076 · W-39/W-40/W-42/W-46→053/059/060/061 ·
W-41→071 · W-43/W-45→§20 · W-26→§21.

Every row of §13 therefore terminates in a ticket, every ticket in a wave, every wave in an exit test, and
every exit test in a measurement. That chain — wish → row → ticket → wave → operating state → number — is
the programme of record.





---

# Part V — programme v2: headlines, tenets, and the revised spine

*Appended 2026-10-25 by kimi (chief-architecture pass), commissioned by the founder after review of
§1–§22, the founder-prompt corpus (160 pi sessions, 4,823 messages), both ticket boards and the live
branch state. This part supersedes the §7 phase ordering with the founder's own sequence and adds the
tenets every surface, agent and gate must hold. §1–§22 remain the evidence base.*

## 23. The headlines — what the programme is for

Six headlines, in the founder's order. Each has a measure; a headline without a measure is a slogan.

| # | Headline | The measure that proves it |
|---|----------|---------------------------|
| H-1 | **Autonomy and closed feedback loops** across estate and platform: every loop runs sense → decide → act → prove → remember with no human kick | autonomy ratio ≥ 80%; self-healed MTTR < 1h for known classes; 100% of registered loops declare trigger + bound |
| H-2 | **Coherence and congruence**: one of each layer, one record per fact, one writer per plane | the registry proves one-of-each; a second writer to any plane fails the gate (R-52) |
| H-3 | **Proactive**: the estate surfaces, proposes and acts before being asked — within consent and quiet hours | pushes arrive with evidence and citation; a nudge with no new information is suppressed in test |
| H-4 | **Event and schedule driven**: nothing waits on a human to start it | the loop inventory shows zero loops requiring a human trigger (R-45) |
| H-5 | **Metric- and data-driven closed-loop self-improvement**: thresholds are data, changed by evidence, and the improver is itself improved inside a bound | every policy change records the measurement that justified it and its measured effect (R-35, R-64) |
| H-6 | **Future-proof, better than anything out there**: the bar is the best external practice, measured — not the estate's own history | §26 bar-raiser annex re-run quarterly; every adopted mechanism names the external benchmark it beats |

## 24. The tenets — binding on every build

These are architectural law. AGENTS.md references this section; a build that violates a tenet fails review.

- **T-1 Structured and schema-driven at every boundary** (ADR 0042 extended): every interaction, agent
  action, work item, capability and claim is a versioned schema record. Where a model produces the
  record, constrained decoding enforces it at generation time — XGrammar-class engines make schema
  conformance effectively free (<40µs/token, JSONSchemaBench) — so "the model drifted off-schema" is
  a gate failure, never a runtime event.
- **T-2 Unified memory, active memory and active focus are first-class.** One memory plane: Cortex and
  the unified-memory server consolidate into a single store with temporal validity windows (the
  Graphiti pattern: facts carry `valid_from`/`valid_to`, never silent overwrite). An agent that cannot
  read the fold does not act. Memory writes carry provenance and decay dates.
- **T-3 Best-of-breed selection, by evidence.** Capabilities are chosen from the registry's own data
  with the founder; anything that does not meet the highest bar, does not solve a key issue, or is not
  bar-raising is merged or deleted with an ADR. Adoption is of named mechanisms, never of products.
- **T-4 Bleeding-edge asymmetric engineering.** The estate's advantage is composition speed and proof
  discipline, not headcount: small surface, maximum leverage, free-tier placement (ADR 0034), and
  adoption of mechanisms at the research frontier before they commoditise (§26).
- **T-5 Evals and judges as first-class principles.** Every agent, pipeline and judge has a score it
  cannot fake, stored as data; judges are themselves judged (R-63); a failing eval blocks like any
  other gate. No score, no ship.
- **T-6 Proof, not assertion** (AGENTS.md §3 restated as a tenet): every claim carries an instrument
  and a window; built and operating are different facts.

## 25. The revised spine — the founder's sequence

§7's phases are re-cut. The founder's order is the law of this programme:

**Phase A — DISCOVERY: the Estate Capability Registry.** One realtime registry as the single source of
truth about the estate — every capability with contract, owner, cost class, health and a last-proof
receipt — queryable by the founder and every agent. This is the mega-oracle's spine (R-50/W-46) and the
founder's most-repeated unmet wish (~225 corpus mentions). All existing maps (growmos graph,
estate-360, estate-inventory, backstage catalog, harness inventory, intents) become writers, never
parallel maps. The founder-prompt corpus seeds the intent register (R-19/R-39/R-47). Carries EPIC-005,
EPIC-059–062, and the four rows the first pass missed: Face-as-CTO trust repair, the bash-vs-executor
ADR, the inner-timeout purge, and the registry-status question itself.

**Phase B — CONSOLIDATION & CONGRUENCE, with the founder.** Domain-by-domain best-of-breed from the
registry's data: two doors, four budget readers, four ticket ledgers, five run stores, two routing
layers, two identity planes, three surfaces with no shared contract (F-09), three empty role-planes.
Keep / merge / delete, one ADR per decision. Closes F-01…F-13.

**Phase C — VISION LOCK, with the founder.** The eight founder-only inputs of §21 answered once; the
target architecture confirmed or corrected; final specs and the full delivery plan produced here.

**Phase D — AUTONOMY WAVES** (§7's waves re-cut): D0 truth (incl. Face staleness repair — a false
count is a truth violation), D1 records, D2 sync, D3 earning autonomy (research→planner→executor,
evals-as-gates, judge-of-judges, capacity-aware routing incl. closing the CLI spend blind spot),
D4 the HQ (Face-as-CTO: see/summon/assign/observe/schedule), D5 film, D6 the world on trial,
D7 continuous. Sequencing law unchanged: nothing in D2+ claims "operating" while D0 exit criteria
are false.

## 26. Bar-raiser annex — bleeding-edge research, 2026-10-25

Adopt mechanisms, not products. Each row names the mechanism, the evidence, and where it lands.

| Area | Bar-raiser mechanism | Evidence (2025–26) | Verdict / lands |
|------|---------------------|--------------------|-----------------|
| Agent observability | OTel `gen_ai.*` conventions as the estate's agent span shape: `invoke_agent` / `execute_tool` spans, `gen_ai.usage.*` metrics. Conventions still "Development" status but the wire format has won — every vendor maps to it | dash0.com knowledge base (2026-09); reactify-solutions agent-eval-observability-2026; klu.ai glossary | **Adopt** as the run-record attribute standard · Phase A, D1 |
| Delivery metrics | DORA 2025: AI raises throughput AND instability — "faster but more fragile"; platform quality + user focus are the multipliers. The estate's fragility is the textbook case; the registry + gates are the cure | Splunk DORA 2025 review; platformengineering.com (2025-09) | **Cite** as the programme's external benchmark · H-5/H-6 |
| Agent identity | No ratified standard exists (Oct 2026). Direction: SPIFFE-style trust domains + WIMSE (IETF, in progress), NIST AI Agent Standards Initiative (Feb 2026), A2A v1.0.1 agent cards (May 2026), MCP donated to LF AAIF (Dec 2025). The estate's SPIRE + claims + HMAC receipts already point this way | CSA labs research note (2026-09); nhigovernance.com (2026-10) | **Adopt** A2A agent-card shape for the roster (R-46); keep SPIRE as the workload-identity plane (resolve F-10) · Phase B, D2 |
| Memory | Temporal knowledge-graph memory with validity windows (Graphiti/Zep pattern). Benchmark honesty: vendors disagree wildly on LoCoMo/LongMemEval; one public eval beat every memory product with BM25 — so the estate scores its own memory on its own gold set | ajayk.sh agent-memory-2026 (2026-10); narrativegoldmine agent-memory (2026-10); arXiv 2603.17244 | **Adapt**: consolidate Cortex + unified-memory into one temporal store (T-2); eval against estate gold sets, never vendor numbers · Phase B |
| Voice | Production voice agent frameworks have converged: LiveKit Agents 1.0 and Pipecat, with 450–600 ms turn-taking budgets as the production bar; speech-to-speech APIs (OpenAI Realtime GA, Gemini Live, Claude voice preview) as the low-latency lanes | reactify-solutions voice-2026 (2026-06); livekit.com blog (2026-09); aiengineeringfromscratch L22 | **Adopt** the 450–600 ms budget as the voice proof metric (R-05); Pipecat-style pipeline composition for the estate voice engine · D4 |
| Structured formats | Constrained decoding is now effectively free: XGrammar-2 (May 2026) — default in vLLM/SGLang/TensorRT-LLM — <40µs/token, ~100% schema conformance on JSONSchemaBench (~10k real schemas). The quality-trade-off concern is settled at agentic boundaries | zylos.ai structured-output-2026; llms.blog grammar-constrained-2026; JSONSchemaBench arXiv 2501.10868 | **Adopt** as T-1's enforcement mechanism at every agent boundary · Phase A |
| Closed loops / AI SRE | AI-SRE agents claim 38–90% MTTR reduction (vendor numbers — treat as ceiling, not plan); the proven production patterns are automated triage/routing (60–80% fewer pages) and bounded auto-remediation with rollback. The estate's incident loop (R-14) matches the pure-play architecture | corelayer.com AI-SRE-2026; squareops.com (2026-05); resolve.ai | **Adapt**: the estate's own loop, bounded by the door and budgets — external tools would be a duplicate layer · D0/D3 |
| Routing + capacity | Learned routing (RouteLLM-class) reports 85% cost cuts at 95% quality on MT-Bench; learned adds 15–25% over static rules. The estate's tier router + zeroedge mechanisms (cache, compress, per-key budget, route-score) fold into ONE capacity-aware router | klymentiev.com llm-router-2026; nx1.io ai-query-routing-2026; arXiv RouteLLM | **Adopt** the four zeroedge mechanisms into the one router (EPIC-076); learned routing only after the registry supplies training data · D3 |
| World / film | WebGPU is production-ready in Three.js (r171+): ~4× particle throughput, Gaussian splatting and ray-traced reflections in-browser. The world is engineering-feasible; the film-first sequence stays — the URL test remains the kill criterion | multiwaresolutions 3d-web-2026; digiformation webgl-webgpu-2026 | **Keep** R-59 sequencing; WebGPU renderer when the world ships · D5/D6 |
| Registry / discovery | IDPs are converging on "agent control plane": catalogs exposed via MCP so agents query and act (Backstage MCP actions registry; CNCF 2026: 73% of platform teams run AI assistants in workflows). The estate's registry must be agent-readable first, human-rendered second | retran.me (2026-05); blog.saaro.net backstage-2026 | **Adopt**: registry ships an MCP surface from day one · Phase A |
| Durable execution | Temporal's bet is validated externally (Series D $300M / $5B, Feb 2026; OpenAI Agents SDK + Temporal patterns). R-51's plane split (cron when / Temporal through / JetStream that / Postgres what) matches the 2026 consensus | reactify-solutions durable-ai-agents-2026; kanopylabs comparison 2026 | **Keep** Temporal; no second orchestrator · D2 |

| Evals, judges, red team | Trajectory-level evals (whole-run grading, not single answers) are the 2026 standard; adversarial CI suites: promptfoo (acquired by OpenAI, Mar 2026), garak, PyRIT; agent-attack benchmarks: AgentDojo (ETH Zürich). Judge calibration is a research field of its own (R-63's judge-of-judges is the right instinct) | langfuse.com agent-evaluation guide (2026-08); confident-ai.com eval guide (2026-10); beyondscale.tech agent-security-2026; zone.ci red-team tooling review (2026-09) | **Adopt** trajectory evals + AgentDojo-class adversarial fixtures as gate steps; judges carry held-out agreement rates · D3 |
| Ephemeral / generative UI | AG-UI (CopilotKit, launched May 2025) is the open event protocol connecting agents to frontends — 17 event types, SDKs in Python/TS; generative UI went mainstream in 2026 (v0, Vercel AI SDK, assistant-ui). Ephemeral panels (R-06) = registry record + AG-UI events + the design-kit tokens, never a bespoke app | reactify-solutions ag-ui-protocol-2026; brainy.ink generative-ui-handbook (2026-05); github.com/narrowin/awesome-generative-ui | **Adopt** AG-UI event model for agent→surface streaming; panels render §12 records only · D4 |
| Self-improving agents | The field's own consensus matches R-64: unbounded self-modification is research-only (Darwin-Gödel Machine, Sakana — ICLR 2026; Gödel Agent); production practice is bounded improvement of prompts/skills/heuristics behind eval gates, with an evolving archive of variants | sakana.ai/dgm; arXiv 2505.22954; o-mega.ai self-improving-guide-2026 | **Adapt**: bounded self-improvement over the estate's skills/prompts/orderings with eval gate + rollback; authority never self-modifies (R-64) · D3/D7 |
| Sandboxing / isolation | Production convergence on a two-layer pattern: microVM for the agent's execution (Firecracker: E2B ~125 ms, Daytona ~90 ms) + an ephemeral environment per PR for the result; Cloudflare Sandbox SDK (V8 isolates) fits the free-tier ladder. macOS has no /dev/kvm — the estate's honest `temp_tree` declaration stands until the cluster carries the upper rungs | narrativegoldmine agent-execution-sandboxes (2026-10); qovery.com sandboxing-at-scale (2026-09); devencelab sandbox reference architecture | **Adopt** the two-layer pattern; kronos ring ladder documents the rungs; Cloudflare Sandbox as the free-tier rung · Phase B, D0 |
| Broadcast / fleet sync | Per-consumer cursors on retained streams (the §16 design) match JetStream/Kafka best practice; the bar-raiser is the staleness SLO published per agent — few fleets measure sync at all | §16 (estate's own); NATS JetStream docs | **Keep** §16 design; the staleness metric is the differentiator · D2 |

**Annex rule (H-6):** this annex is re-run quarterly by the research role (EPIC-071/072); every row
names the external benchmark the estate must beat, and the registry measures whether it does.

## 27. AGENTS.md reference

`idp/AGENTS.md` carries a pointer to this document and to §23–§24 (headlines and tenets) as binding
law, so every agent — whatever runtime — reads the programme at session start.
