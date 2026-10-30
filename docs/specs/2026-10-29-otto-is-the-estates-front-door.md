# Otto is the estate's front door

**Date:** 2026-10-29
**Status:** draft for founder ratification — companion decision `docs/decisions/0047-otto-is-the-estates-front-door-not-a-second-agent-platform.md`
**Issue:** chidionyema/idp#7408
**Author:** pi (claim on #7408)

---

## 0. The question, and the answer in one sentence

The founder's instruction (2026-10-29): reconstruct the vision for Otto from every ticket, spec
and decision; judge the architecture that resulted from it; and re-propose Otto so that the
concept and the architecture are unambiguous.

**The answer: Otto is the estate's front door.**

> Everything a human says to the estate, and everything the estate needs a human to say, crosses
> Otto. Below the seam, Otto owns nothing: it borrows the estate's one router, one memory, one
> executor, one verifier, one identity and one secret store. **The seam is where new surfaces
> come from; the layers below it never multiply.**

That sentence is unambiguous on purpose, and it is not new. It is the estate's own
`docs/specs/otto-answering-floor.md` ("Design rules that are not negotiable", lines 89–105)
read one layer down: that spec already forbids a second identity, a second answering path, a
second thread, a second collector — **inside** the surface. What it does not say, and what the
last three months proved, is that the same rule must hold **below** the surface. Today Otto
keeps the rules above the seam and breaks every one of them below it: its own router, its own
memory planes, its own tool registry, its own verification plane, its own lane literals.

This document is the wish-map, the judgement, the concept, and the waves.

---

## 1. The vision, reconstructed from the record

Every row below is a founder wish found in the estate's own files, in the founder's own words,
with the receipt it was recorded in. The status column is honest: it says whether the estate
satisfies the wish **today**, measured against the tree, not against the intention.

*On the record itself:* the founder's raw session notes (`~/.claude/docs/founder/`) hold no files
on this machine, so the wishes below are reconstructed from what survived in the estate — the
specs, the decisions, the manifests and the tickets that quote them. That is the record this
document now completes.

### A. Never silent

| # | The wish (founder's words) | Receipt | Where it lives today | Status |
|---|---|---|---|---|
| A1 | "otto must have 3 homes … has never been stable even once … we must have the alternative to litellm" | `platform/otto-gateway/three-homes.yaml:1-3` (founder order 2026-09-09) | three homes in one ConfigMap; a loopback litellm sidecar in Otto's pod (`deployment.yaml:398-405`) | **met**, with the cost in §3.3 |
| A2 | "it is not the estate router with a different address, it is not the estate router at all" | `three-homes.yaml:18-21` | home 2 — a direct vendor line with Otto's own key | **met** — this is the lifeboat, and it should stay |
| A3 | "theesare fr lands, can we use or ont" (2026-09-08) — free lanes must not queue behind a dying cluster | `three-homes.yaml:66-72` | the free direct lanes head every chain; the cluster router is "a rung in the middle" | **met** — and superseded by §3.6 (1) |
| A4 | "no i killed ollama because machine is slow", "lets think of another cloud home", "dont rely on macbook" (2026-09-10) | `three-homes.yaml:34-38` | home 3 = Groq through the Tailscale sidecar; the laptop is gone | **met** |
| A5 | "otto should never be out of options that the national/global is about" / "free with limits? what if limit is reached?" (2026-09-10) | `docs/explanation/otto-survival-matrix.md` (the founder's 2026-09-10 quote on the matrix of combinations; sixteen lanes and three homes) | the estate router already carries the vendor zoo (`platform/llm/config.yaml`: openrouter, deepseek, minimax, glm, gemini, groq, cerebras, nvidia, sambanova) | **met by the estate**, not by Otto |
| A6 | "ptto nust nnever go sdoen" — availability outranks accounting (2026-09-10) | `three-homes.yaml:80-82` | a Groq answer is **not** counted in the estate's LiteLLM spend table | **met**, and it is the crack the 2026-10-26 ruling opens (§3.3) |
| A7 | a third home must not be able to take the door down with it | chidionyema/idp#5894 (2026-10-12, open) — the token roll and tailnet node leak crash-looped `otto-gateway` | the third home's egress path sits in the door's own pod | **defect, open** — the lifeboat's egress has taken the door down once |

### B. Everywhere, any interface

| # | The wish | Receipt | Where it lives today | Status |
|---|---|---|---|---|
| B1 | "the showcase has to actually wow and impress … need to see, visualise and interact" (2026-09-05) | `otto-answering-floor.md:7-8` | portal `/ask`, SSE reply address, session registry in `otto_gateway` | **partly** — the seam exists; the page is the open part |
| B2 | "a new surface is one binding + one registry entry, no gateway rework" | `otto-answering-floor.md:23` (`hermes-v2/otto/ingress/plugins.py:237-242` -- the application code lives in the `hermes-v2` repository, not in this one) | the plugin enum + per-surface binding classes | **met** -- the best thing Otto built |
| B3 | a surface per channel: Telegram (live), HTTP, portal, Slack, email, voice, QR/camera | `otto-answering-floor.md:77-87` | Telegram + HTTP + (planned) portal/media/voice | **partly** |
| B4 | voice first, "voice ON by default", local STT, router as fallback | `docs/decisions/0022-the-founder-override-is-voice-first-and-nothing-is-deleted.md` | `voice-asr`/`voice-tts` lanes on the estate router; one voice owner | **met** (ADR 0039) |
| B5 | the edge voice loop (offline ASR/intent/TTS) is the *target*; today it is server-side and utterance-batched | `docs/decisions/0033-edge-compute-for-the-voice-loop-is-the-target-not-the-state.md` | not built | **open, correctly named** |
| B6 | approvals and applies must be reachable from a runner, a voice, or Telegram — no door assumes the founder is at a laptop | chidionyema/idp#7388 (2026-10-29) | not built | **open** — this is Wave 5 below |
| B7 | Otto answers on the API surface, and an accepted turn can no longer be dropped silently | chidionyema/idp#6986 (2026-10-23, open) | the seam has no API binding yet | **open** — and it is one more binding, not a new product |

### C. Superpowers — every iota, with hands

| # | The wish | Receipt | Where it lives today | Status |
|---|---|---|---|---|
| C1 | "we need to dig up every single iota of capability even potential not yet built", "no inch given", "every iota" (2026-09-05) | `docs/specs/otto-capability-inventory.md:3-4` | the 91 KB inventory: 20+ surfaces, 82 skills, sub-agents, browser, computer use, media gen, delegation | **met as a census**; not met as a runtime |
| C2 | "Otto runs every tool without asking. The one exception is an action that cannot be undone" (2026-09-05) | `docs/decisions/0024-otto-runs-every-tool-and-asks-only-for-the-unundoable.md` | `OTTO_TOOLSETS=terminal,web,search,skills,file,vision,tts,memory,todo,cronjob,code_execution` (`deployment.yaml:356`) | **met — and it is also the security hole in D3** |
| C3 | "The highest standard is that a model-driven shell never runs in the process that holds the bot token, the database password and the GitHub token" | `docs/specs/otto-door-hands-and-senses.md:200-203` | `terminal` and `code_execution` are in the toolset of the container that mounts those exact secrets | **not met** — the spec's own sandbox (a secretless `otto-sandbox` Job) was never built |
| C4 | one agent, one thread, one audit trail; continuity by principal across surfaces | `otto-answering-floor.md:89-105` | `otto/ingress/thread.py`, trust classes, the channel registry | **met** |
| C5 | one identity layer: OIDC at the gateway, never in an app; the channel-binding registry is the auth class | `otto-answering-floor.md:91-95`, `platform/otto-gateway/httproute.yaml:25` | oauth2-proxy + binding registry | **met** — keep exactly as is |

### D. Truth, proof, enterprise bar

| # | The wish | Receipt | Where it lives today | Status |
|---|---|---|---|---|
| D1 | "we need better testing for this as enterprise product" (2026-09-05) | `platform/otto-gateway/answer-probe.yaml`, `.github/workflows/otto-parity.yml` | a 15-minute answer probe, a scheduled parity tick, a registration reconciler | **partly** — and the tick measures nothing (idp#7354) |
| D2 | "the door stays probed"; a probe that grades a lane the door no longer uses is worse than no probe | `otto-answering-floor.md:104-105`, `platform/otto-gateway/router-lanes.yaml:1-30` | one `otto-router-lanes` ConfigMap consumed by door **and** probe | **met** — a model fix (lane drift happened twice before it) |
| D3 | "an instrument nobody can trust is not an instrument (LAW 28)" | `router-lanes.yaml:22-24` | the same | **met** |
| D4 | the founder must be able to *see* the work live, on the work surface | AGENTS.md §9 ("the Fleet page"), §3 ("done = operational") | `/fleet` shows claims and gates; Otto's own health is not on it | **partly** |
| D5 | a spec, a BDD and an eval harness that proves Otto beats a baseline ("beat Muse") | chidionyema/idp#6921 (2026-10-23, open) | not built | **open** — and it is a *measurement* wish, not a capability wish: the door's answers are graded against a baseline by the estate's harness, not by a private grader inside Otto |

### E. The estate's human-in-the-loop (new, and the biggest)

| # | The wish | Receipt | Where it lives today | Status |
|---|---|---|---|---|
| E1 | a stuck agent escalates to the founder on the `otto numum` Telegram channel with the blocker named | chidionyema/idp#7388 (2026-10-29) | not built | **open** |
| E2 | a structured decision: Otto asks, the founder answers with a comment, the build continues | chidionyema/idp#7340 (closed 2026-10-28, landed) -- PR #7384 -> `1cd65e8b1`: `sovereign/otto/decision.py`, `bin/founder-decision`, `platform/estate/intents/founder.decision.yaml` | **built** -- measured message id 2056, decision id `dec-306c912e`, expiry fail-closed, the webhook restored | **met** |
| E3 | approvals and applies reachable from anywhere the founder is | chidionyema/idp#7388 | not built | **open** |

### F. The estate's law (the constraints the wishes have to live inside)

| # | Law | Receipt | Status |
|---|---|---|---|
| F1 | one of each layer: routing, traces, identity, secrets, scheduling, catalog, execution boundary, evidence, verification, memory | AGENTS.md §6 | **broken in Otto's case** — see §3 |
| F2 | cloud router is the default; the laptop is the fallback; a capability that only works on the laptop is not done | AGENTS.md §7a (ruling 2026-10-26) | **contradicted by Otto's routing today** (§3.3) |
| F3 | the founder's own subscription lanes stay local; they are not a pattern to copy | AGENTS.md §7a | respected |
| F4 | never hand-apply; heal through Flux | AGENTS.md §2 | respected by Otto |

---

## 2. The architecture that answered the wishes

Each of Otto's components exists because it answered one wish above. This is the honest reading:
**almost nothing in Otto is gratuitous.**

| Component | File | The wish it answered | How it answered it | What it cost |
|---|---|---|---|---|
| Telegram door + bot | `platform/otto-gateway/` (`deployment.yaml`, `httproute.yaml`) | B1, B2, B3 | the founder's real surface, live | none — this is the product |
| The seam (bindings + registry) | `otto/ingress/plugins.py`, `otto/surface/bindings/*` | B2, B3 | a new surface = one file + one row | none — this is the asset |
| Thread + trust classes | `otto/ingress/thread.py`, `binding-seed.yaml` | C4, C5 | continuity by principal, strangers isolated | one table in `otto_gateway` — legitimate |
| Presence, media, reply delivery | `otto/boot/presence.py`, media normalisers | B1, B4 | the demo that "wows" | none |
| **Three homes + loopback litellm sidecar + 7 vendor keys** | `three-homes.yaml`, `three-homes-secrets.yaml`, `deployment.yaml:398-459` | A1–A6 | never be silent, without a human | **the estate router demoted to a rung; a turn usually escapes the estate's budget and ledger** (§3.3) |
| **Otto's own lane values** | `router-lanes.yaml` | A5, D2 | lane names, one ConfigMap | drift fixed once, and the fix is a model |
| **`OTTO_TOOLSETS` incl. `terminal`, `code_execution`** | `deployment.yaml:338-356` | C2 | hands, unattended | **the shell runs where the secrets are** (C3) |
| **Own memory: `otto_facts`, hindsight, `otto-memory-store` Job, own embeddings** | `deployment.yaml:269-311`, `platform/otto-gateway/memory-store-job.yaml`, `hermes-v2/otto/memory/` | C1, C4 | "every iota" of capability | **ADR 0036 already decided this is deleted — and it still runs** (§3.4) |
| Own verification plane: answer-probe, registration reconciler, parity tick | `answer-probe.yaml`, `registration-reconciler.yaml`, `.github/workflows/otto-parity.yml` | D1, D2 | the enterprise bar | **a second verification layer; the tick measures nothing today** |

---

## 3. The judgement: why the architecture took this shape

### 3.1 The mechanism: every wish was answered locally

Each of the ten components above is a *local* answer to a *global* wish. The person who held
"never be silent" built a router; the person who held "every iota" built a memory and a tool
registry; the person who held "enterprise bar" built a probe. Each answer was correct on its
own terms, and each was made inside Otto because Otto was the thing in front of the founder.

**Nothing reconciled them.** The estate's law of one-of-each-layer is a *global* constraint, and
it was never applied to Otto's parts as a set. Three months is roughly the time it takes for
locally-correct answers to accumulate into an architecture nobody chose.

### 3.2 What was right and must not be lost

Otto's own answering-floor spec got this exactly right, and its six rules are the seed of this
proposal: one identity layer, one answering path, one thread per principal, one collector,
structured denials, a probed door. The seam ("a new surface is one binding + one registry
entry") is the answer to the founder's "future-proof for any interface". It is genuinely good
work, it is the part that took the three months, and it survives this proposal unchanged.

**The seam is where the estate's laws stop.** Above the seam, one of each. Below it, one of
each *again*.

### 3.3 The inversion: the estate's one router was demoted to a rung

`three-homes.yaml` opens with the founder's order of 2026-09-09 and states the design in one
line (lines 41–47):

> "This is not a second platform router. The estate keeps one router and home 1 is it: every
> happy-path turn still walks litellm.llm.svc, still spends against the estate's budgets and
> still lands in Langfuse."

Eighty lines later, the same file records what actually shipped (lines 66–82): the free
direct lanes head every chain, the cluster router is "a rung in the middle", and

> "The price, stated plainly: a turn Groq answers is not counted in the estate's LiteLLM spend
> table, because it never touches it."

The manifest agrees: `LITELLM_BASE_URL=http://127.0.0.1:4010/v1` (`deployment.yaml:327`) —
the door talks to the **pod-local lifeboat**, not to the estate router. Measured consequence:
Otto's happy path is the one path the estate's virtual keys, daily budget, and Langfuse cost
table cannot see.

That is not a bug in Otto; it is the correct execution of wishes A3 and A6 ("do not queue
behind a dying cluster", "availability outranks accounting") — the two wishes that a later
founder ruling overturned. The 2026-10-26 ruling (AGENTS.md §7a) now says the **cloud** router
(`https://llm.${ESTATE_ZONE}`) is the default route, and the laptop is the fallback. The
estate's own agent SDK already points there (`packages/aei/src/aei/estate.py:36`:
`ROUTER_URL = ... "https://llm.mumchimp.com"`). So the current state is the worst of both:
Otto's default route is a pod-local sidecar, which is neither the estate's default route nor
the cloud router.

Even the *concept* and the *implementation* of the homes disagree, which is the lane drift one
layer up: the survival matrix makes home 2 a **Cloudflare edge Worker**
(`docs/explanation/otto-survival-matrix.md`), while the deployed ConfigMap's home 2 is a
**direct vendor line** out of the Tailscale sidecar (`three-homes.yaml:17-21`). One file per
reader fixed this for the lanes; the homes need the same treatment.

**The reconciliation is small and it preserves every availability wish:** point Otto at the
estate's one router — the cloud one, which is outside the cluster failure domain — and keep the
lifeboat exactly where the founder put it: **last**, with no policy and no ledger, for the case
where the router itself is unreachable. Two *transports* is the price of "never be silent" (A2
asked for precisely that). Two *routers* is not, and is not what the founder asked for.

### 3.4 The decision that was written and never executed

`docs/decisions/0036-one-memory-plane-and-it-is-cortex.md` (2026-10-02, founder-accepted)
already ruled:

> "`otto/memory/fast_recall.py` and `otto_facts` — **deleted**; its writes move to `remember`.
> The `otto-memory-store` Job — **deleted**. Hindsight — **retired**."

Measured on the tree today:

- `platform/otto-gateway/memory-store-job.yaml` — **still there**;
- `deployment.yaml:269` — `OTTO_MEMORY_HINDSIGHT_URL=http://hindsight-api.hindsight.svc:8888` — **still pointed at the retired service**;
- `hermes-v2/otto/memory/` — `fast_recall.py`, `hindsight.py`, `embeddings_litellm.py`, `backfill.py`, `store.py`, `migrations/` — **all still there**;
- `deployment.yaml:291` — Otto's embedding path calls the **cluster** router, so it dies with the cluster.

Twenty-seven days after the decision, the manifests did not move. That is the whole lesson of
this section: **a decision that is only a document does not move a manifest.** ADR 0036 is
correct and needs enforcement, not restatement (§8).

### 3.5 The contradiction with the founder's own security standard

`otto-door-hands-and-senses.md:200-203` sets the bar: a model-driven shell must never run in the
process that holds the bot token, the database password and the GitHub token; `terminal` was to
execute as a secretless Kubernetes Job in an `otto-sandbox` namespace. Today `terminal` and
`code_execution` are in `OTTO_TOOLSETS` (`deployment.yaml:356`) **in the container that mounts
exactly those secrets** (`deployment.yaml:269-356`: the channels secret, `hermes-agent-env` with
`GITHUB_TOKEN` and `ESTATE_MCP_KEY`, the DB password, the router key).

This is not a design disagreement; it is the founder's standard, unmet, by the founder's own
hands.

### 3.6 The five contradictions, in one table

| # | The architecture today | The founder's later ruling | Where |
|---|---|---|---|
| 1 | Otto's default route is a pod-local lifeboat; the estate router is a rung and usually not used | cloud router is the default; laptop is the fallback (2026-10-26) | `deployment.yaml:327`, `three-homes.yaml:66-82` vs AGENTS.md §7a |
| 2 | Otto keeps its own memory planes | one memory plane; `otto_facts`/hindsight/store-Job deleted (2026-10-02) | `deployment.yaml:269,291`, `memory-store-job.yaml` vs ADR 0036 |
| 3 | `terminal` runs beside the bot token, DB password and GitHub token | a model-driven shell never runs in that process | `deployment.yaml:356` vs `otto-door-hands-and-senses.md:200-203` |
| 4 | a private verification plane (probe, reconciler, parity tick) | one verification layer; the estate has a doctor family | `answer-probe.yaml`, `otto-parity.yml` |
| 5 | the answer path assumes the cluster's router and cluster services | no door assumes a laptop, and the cloud is the default route | `deployment.yaml:291`, ADR 0033's honesty rule; and the estate's own Otto SLA proves the founder's **laptop** and **hindsight** (`docs/explanation/otto-on-the-mac.md`: the playbook is `gateway-ready`, `no-restart-loop`, `key-usable`, `key-direct`, `tailnet-up`, `mac-run-hostname`, `hindsight-answers`, `cron-lanes-installed`) |

### 3.7 The honest verdict

**Otto is worth investing in** — and the reason is now precise rather than sentimental. The
seam, the thread, the trust classes, the media pipeline, the presence and the reply delivery
are real, measured, and reusable. What is missing is not capability; it is that **the layers
under the seam were built inside Otto instead of borrowed from the estate**, and that three
global constraints (one of each layer, cloud-default routing, the secretless shell) were never
applied to Otto as a set.

The three months were not wasted: they are the measurement that produced this verdict. What
they produced is a **front door with a second platform attached underneath it**. The front door
is the asset. The second platform is the cost.

### 3.8 The three loud demands, tested

The founder's demands were not vague adjectives; each was a real, expensive wish. Three of them
are worth testing on their own terms, because each contains one achievable thing and one thing
that cannot be had.

**"Available everywhere, all the time."**
The achievable half: *reachable from anywhere, through one door*. The door is a stateless ingress
in three failure domains, and with the cloud route it no longer waits on the cluster — the
founder's "do not queue behind a dying cluster" is answered by the route, not by the ladder.
The unachievable half: *always answering, with nothing else failing*. Measured, it never held:
Otto's answer path reached into the cluster twice — the embedding URL at
`deployment.yaml:291` and the hindsight URL at `deployment.yaml:269` — so a cluster outage took
Otto's memory with it, and the estate's own Otto SLA has measured nothing for two days
(idp#7354). The honest form of the wish is: **the door is always reachable; what it can answer
degrades with the estate, and says so.** That is what `BLIND` means in the doctor.
The price of the literal version is what Otto paid: a private ladder, seven vendor keys, and an
estate router demoted to a rung.

**"Future-proof for any interface."**
The seam is the mechanism, and it works: a new surface is one binding and one registry row, and
the gateway does not change (`otto-answering-floor.md:23`). What did not work was trying to
future-proof the *layers under the seam* — each layer got its own copy "so it could be made
future-proof later", and a copy is not a hedge, it is a migration waiting to happen. Measured:
ADR 0036 (2026-10-02) decided Otto's memory planes were deleted; twenty-seven days later the
manifests still point at hindsight. A surface costs one file. A layer costs a migration, and the
migration is what did not happen.
So the wish survives, with one amendment: **future-proofing belongs at the seam and nowhere
else.**

**"Superpowers — every iota."**
The census is real and worth keeping (`otto-capability-inventory.md`, 91 KB): it is the estate's
map of what a personal agent could do, and it is why the estate has skills, media pipelines and
voice. But capability was never the bottleneck — the estate already owns execution, memory,
identity, secrets, evidence and verification, and a second copy of each adds no iota. Two
"superpowers" are genuinely missing, and neither is a new tool: **reaching a human when an
agent is stuck** (D7, #7388) and **proving what happened** (the doctor family). The rest of the
iota is the estate's, reached through doors.
And the superpowers have a cost the founder set himself: hands that act unattended (ADR 0024) are
safe only because the boundary is real — the claim gate, the executor, the sandbox. A superpower
without a boundary is a liability with a nice name.

---

## 4. The concept

### 4.1 The sentence

> **Otto is the estate's front door. Everything a human says to the estate, and everything the
> estate needs a human to say, crosses Otto. Below the seam, Otto owns nothing.**

### 4.2 What that forbids, in five lines

1. No second router, no second memory store, no second execution boundary, no second
   verification plane, no second identity, no second secret store — **anywhere under the seam**.
2. No Otto-side copy of an estate value that can drift (the lane literals drifted twice; the
   lane ConfigMap fixed it — apply the same treatment to every shared value).
3. No behaviour that only works on the founder's laptop, in his browser, or on a machine he is
   sitting at.
4. No capability claim without a proof that runs on the founder's real path.
5. No new surface that needs the gateway to change — a surface is one binding and one registry
   row, or it is not a surface.

### 4.3 The ownership table — one line per layer

| Layer | Owner | The door Otto uses | Otto's obligation |
|---|---|---|---|
| Surface ingress (Telegram, portal, Slack, email, voice, QR) | **Otto** | — | the seam; one binding + one registry row per surface |
| Thread, presence, trust classes, reply delivery, media normalisation | **Otto** | — | continuity by principal; structured denials |
| Human-in-the-loop (escalation, approval, structured decisions) | **Otto** (the estate's front door for a human) | the claim/approval records the estate already keeps | a blocked agent reaches a human by voice or Telegram, with the blocker named (#7388, #7384) |
| Identity | **the estate** | OIDC at the edge, channel-binding registry as the auth class | trust the gateway's header and nothing else |
| Model routing | **the estate** | the cloud router (`https://llm.${ESTATE_ZONE}`), with Otto's lifeboat as the last rung | name lanes, never vendors; never bypass the ledger on the default path |
| Memory | **the estate** | `remember`/`recall` on the one MCP door (ADR 0036) | keep the thread; do not keep a second fact store |
| Execution boundary | **the estate** | intents + `estate-execute` + the claim gate | estate-affecting actions go through the door; the founder's approval is the gate |
| Verification | **the estate** | the doctor family (`telegram-agent.doctor` and its siblings) | be probed by it, not by a private plane |
| Secrets | **the estate** | the vault; workload identity | never hold a vendor key the estate already holds |
| Evidence / traces | **the estate** | the one collector, one bus | emit to it (already done) |

**The test, in one line:** if Otto owns a layer the estate owns, that is a second platform; if
the estate owns it and Otto calls it through its door, that is borrowing. Borrowing is the
whole point of a front door.

### 4.4 The shape

```
        human (voice, Telegram, portal, anything)
                        |
        +---------------+----------------+
        |        OTTO — the seam        |   ingress · thread · trust · presence
        |   (and the estate's          |   delivery · escalation · approval
        |    human-in-the-loop plane)   |
        +---------------+----------------+
                        |  every call crosses a door
   +---------+---------+--+--------+---------+----------+
   |         |         |     |        |         |          |
 identity  routing  memory  exec   verify   secrets   evidence
 (estate) (estate) (estate)(estate)(estate) (estate)  (estate)
                        |
                   +----+----+
                   |  lifeboat |  ← last rung only: no policy, no ledger,
                   |  (Otto)   |    for the case where the router is gone
                   +----------+
```

---

## 5. The target architecture, layer by layer

**Routing.** One router: the estate's, on the cloud, which is outside the cluster's failure
domain. Otto names lanes (`router-lanes.yaml` already does this correctly — "the values are lane
names on the estate router, never vendor model identifiers"). The lifeboat stays in Otto's pod,
still a loopback litellm, still last, still with no policy and no ledger — but it is no longer
the default, and a turn it answers is accounted to the estate's ledger by the `router.outcome`
event Otto already emits. The founder loses nothing: A1–A4 are still met, because the cloud
router plus the lifeboat is still two failure domains plus a floor.
The laptop keeps one honest role, the one idp#5708 already describes: a **bounded command door**
that Otto may reach over the tailnet — never a home, never a dependency, never a path the
founder must be sitting at.

**Memory.** `remember`/`recall` on the one MCP door; `otto_facts`, `hindsight`, the
`otto-memory-store` Job and Otto's own embedding path are deleted (ADR 0036 — decided, not
executed). The thread stays in Otto: a thread is a *surface* concept, a fact is not.

**Execution.** Two kinds of action, two doors, and no third:
- *Estate-affecting* (git, PRs, CI, cluster, claims, deploys) → the estate's intents, through
  `estate-execute`, with the claim gate and the audit trail. Otto's pod already holds
  `ESTATE_MCP_KEY` and reaches the estate MCP, so this is a configuration change, not a rewrite.
- *Personal work the estate's intents do not cover* (arbitrary shell, research, media) → Otto's
  own tools, but `terminal`/`code_execution` move to the secretless `otto-sandbox` Job that
  `otto-door-hands-and-senses.md:200-203` already specified. ADR 0024 is honoured: Otto still
  runs every tool unattended and asks only for the unundoable.

**Verification.** The answer probe, the registration reconciler and the parity tick stop being a
second verification layer and become *inputs* to the estate's one: the doctor's registry already
names `otto-gateway`, `otto-golden` and `jit-broker`, and the doctor already reads the scheduled
plane as context (`telegram-agent.doctor`, landed in #7361/#7380/#7386). The probe keeps asking
the real lane — that is its job — but it stops being the thing that decides whether Otto is
healthy. #7354 owns the tick's timeout.
The estate already states the principle this follows: a work item cannot be called done without
a fresh verdict "produced by a process the agent cannot run" —
`docs/explanation/verification-plane.md` (crew#631), which removes self-certification. Otto's own
probe cannot certify Otto; that is the definition of self-certification. (Two different planes,
not to be confused: the verification plane grades *artifacts* with signed verdicts, the doctor
grades *health* with a named first broken link.)

**Identity, secrets, evidence.** Unchanged. They are already the estate's, and they are right.

**The human-in-the-loop plane.** This is the new work and it is the reason Otto's role grows
rather than shrinks: when an agent is blocked, it escalates to a human *through Otto*, by voice
or Telegram, with the blocker, the claim, and the approval path named (#7388). When the founder
answers a structured decision, the answer is a record, not a message that evaporates (#7384).

---

## 6. Keep, move, delete — with receipts

| Component | Verdict | Receipt / reason |
|---|---|---|
| The seam (bindings + registry) | **KEEP** | `otto-answering-floor.md:23`; it is the future-proofing mechanism |
| Thread, trust classes, presence, media, reply delivery | **KEEP** | `otto-answering-floor.md:89-105` |
| Identity (OIDC + binding registry) | **KEEP** | already the estate's |
| Traces to the one collector | **KEEP** | already the estate's |
| `otto-router-lanes` ConfigMap | **KEEP, extend** | the model for every shared value (lanes, toolsets, memory URLs) |
| Lifeboat sidecar | **KEEP as last rung** | A2 asked for it; it is the availability floor |
| `LITELLM_BASE_URL=127.0.0.1:4010` as the *default* | **MOVE** | → the cloud router as default, lifeboat last (§5 Routing) |
| `otto_facts`, `otto/memory/fast_recall.py`, hindsight URL, `otto-memory-store` Job, Otto's embedding path | **DELETE** | ADR 0036 (decided 2026-10-02, never executed) |
| `terminal`/`code_execution` in the secret-holding container | **MOVE** | → the secretless `otto-sandbox` Job (`otto-door-hands-and-senses.md:200-203`) |
| Estate-affecting tools inside Otto | **MOVE** | → the estate's intents (the pod already holds `ESTATE_MCP_KEY`) |
| The answer probe, reconciler, parity tick as a *verdict* | **MOVE** | → the doctor family owns the verdict; the probe is an input |
| Otto's private vendor keys (`three-homes-secrets.yaml`) | **MOVE** | → the estate's vault; a vendor key the estate holds must not be held twice |
| The laptop as a home | **GONE already** | A4; and no door may assume it (F2) |

---

## 7. The waves, and the proof each one owes

Each wave is small enough to land in one lane and each carries a proof that can fail. A wave is
done when its receipt exists.

**Wave 1 — Route through the estate, keep the lifeboat.** Otto's door points at the estate's
cloud router; the lifeboat becomes the last rung; `router.outcome` accounting covers the
lifeboat; the estate's `router-doctor` sees Otto's traffic.
*Proof:* a turn answered by the default path appears in the estate's cost table; a turn answered
by the lifeboat appears as an accounted event; the lanes Otto names are the lanes the estate
router serves. *Falsifier:* if the cloud router's outage took Otto silent, the lifeboat must be
re-promoted — and that is measured, not argued.

**Wave 2 — Execute ADR 0036.** Delete the memory planes; write through `remember`.
This wave is not new work: the estate already ordered it in idp#6162 ("import Hindsight, then
retire it"), idp#6163 ("delete the duplicate memory layers"), idp#6229 ("wire unified estate
memory into Otto numun, fleetview voice and agent-workforce") and idp#6165 (the epic) — all
still open, while ADR 0036 has sat unimplemented since 2026-10-02. Wave 2 is those tickets,
finished.
*Proof:* `rg hindsight|otto_facts|otto-memory-store` finds nothing in the manifests; a fact
written by Otto is recalled by the estate's `recall`; `bin/memory-gate --check` is green.
*Falsifier:* if recall latency through the one door breaks the founder's tolerance, the door
needs a read-through cache — not a second store.

**Wave 3 — The secretless shell.** `terminal` and `code_execution` move to the `otto-sandbox`
Job; estate-affecting actions move to the estate's intents.
*Proof:* the toolset in the secret-holding container no longer contains a shell; a terminal tool
call runs with no secret mounted; an estate-affecting action produces an intent receipt and a
claim.

**Wave 4 — One verification plane.** The probe, the reconciler and the tick become inputs to
the doctor; the doctor owns the verdict; `/fleet` shows it.
*Proof:* `telegram-agent.doctor` names the first broken link for every Otto agent; the scheduled
tick's rows come from the doctor; the tick no longer self-cancels (#7354).

**Wave 5 — The human-in-the-loop plane.** A blocked agent escalates to the founder through Otto
by voice or Telegram, with the blocker and the approval path; a structured decision is answered
as a record.
*Proof:* a real blocked agent reaches Telegram with the blocker named; the founder's answer
becomes a record attached to the claim; no approval path requires the founder to be at a laptop
(#7388).

**Wave 6 — More surfaces.** Each new surface is one binding and one registry row.
*Proof:* the seam test — the gateway is untouched (asserted by diff scope) — and a question asked
on the new surface is answered by the same agent, in the same thread.

**Sequencing:** 1 → 2 → 3 are independent and can land in any order; 4 depends on 1–3 being
settled enough for the doctor to have a stable chain to read; 5 depends on 1 and 3 (an escalation
that cannot act is a notification); 6 depends on nothing but is worthless until 4 proves the
door.

---

## 8. Enforcement — so the decision stops being a document

ADR 0036 is correct and twenty-seven days stale. The reason is structural: **a document cannot
move a manifest.** Five gates, all in the estate's existing shape:

1. **Manifest conformance (new).** A gate that reads `platform/otto-gateway/*.yaml` and fails
   when a manifest names a layer the estate owns: a hindsight/otto_facts URL, a loopback
   `LITELLM_BASE_URL` that is not the last rung, `terminal`/`code_execution` in a container that
   mounts secrets, a vendor key duplicated from the vault. The rule is a table, so it is
   checkable.
2. **One shared value, one place (the `router-lanes.yaml` model).** Every value both the door
   and a probe read comes from one ConfigMap. The lane drift happened twice before that file
   existed; the fix is a pattern, not a one-off.
3. **`bin/memory-gate`** (exists, ADR 0036) — fails when the memory plane is unreachable, when
   a written probe fact is not recalled, or when an empty store reports healthy.
4. **`telegram-agent.doctor`** (exists) — the estate's one verdict for every Telegram agent.
5. **The claim gate** — a change that adds a private layer to Otto must claim those paths
   visibly; the claim is the record of who decided to duplicate.

---

## 9. What would prove this concept wrong

- If the estate's cloud router cannot serve Otto's latency, and the lifeboat must be the default
  to meet the founder's patience, then "one router" is the wrong shape and the honest answer is
  two routers with an honest ledger — not a quiet demotion.
- If the estate's intents cannot carry Otto's estate-affecting work with the latency a Telegram
  user accepts, Otto needs its own execution boundary, and the concept is wrong about the
  execution layer.
- If moving Otto's memory to `remember` costs answer latency the founder will not tolerate, the
  door needs a read-through cache — and the cache is a door, not a store.
- If the seam cannot absorb a new surface without a gateway change, the seam is not a seam and
  "future-proof for any interface" is a wish, not a mechanism.

Each of these is a measurement to take, not an argument to have.

---

## 10. What this spec does not do

- It does not remove a surface, a binding, a thread, a probe, or the lifeboat.
- It does not add a service, a store, a router, or a gate that cannot fail.
- It does not claim any of it is operating. Every wave above carries its own proof; none of them
  is done.
- It does not touch `AGENTS.md`, the lane values, the founder's vault, or the cluster by hand.

---

## Appendix — receipts index

| Claim | Where |
|---|---|
| Three homes; the founder's order of 2026-09-09; "it is not the estate router at all"; the laptop killed | `platform/otto-gateway/three-homes.yaml:1-47` |
| The inversion: free lanes head the chains; the estate router is a rung; the price is uncounted spend | `three-homes.yaml:66-82` |
| The door talks to the loopback lifeboat | `platform/otto-gateway/deployment.yaml:327` |
| Hindsight, `otto-memory-store`, Otto's own embeddings | `deployment.yaml:269,291`; `platform/otto-gateway/memory-store-job.yaml`; `hermes-v2/otto/memory/` |
| The toolsets, including `terminal` and `code_execution` | `deployment.yaml:338-356` |
| The lifeboat sidecar image and its no-database shape | `deployment.yaml:398-459` |
| The estate's one router is the cloud router | AGENTS.md §7a; `packages/aei/src/aei/estate.py:36` |
| One memory plane; `otto_facts`/hindsight/store-Job deleted | `docs/decisions/0036-one-memory-plane-and-it-is-cortex.md` |
| The secretless shell standard | `docs/specs/otto-door-hands-and-senses.md:200-203` |
| Hands without asking | `docs/decisions/0024-otto-runs-every-tool-and-asks-only-for-the-unundoable.md` |
| Voice first; one mouth; edge voice as the target | `docs/decisions/0022-*.md`, `0033-*.md`, `0039-*.md` |
| The seam; the six non-negotiable rules; the ground truth | `docs/specs/otto-answering-floor.md:23,89-105` |
| The capability census and its words | `docs/specs/otto-capability-inventory.md:3-4` |
| Lane drift, twice, and the ConfigMap that fixed it | `platform/otto-gateway/router-lanes.yaml:1-30` |
| The doctor's registry and the scheduled plane | `platform/estate/intents/telegram-agent.doctor.yaml` (#7361, #7380, #7386) |
| Escalation and structured decisions from anywhere | chidionyema/idp#7388, #7384, #7340 |
| The parity tick measuring nothing | chidionyema/idp#7354; `docs/epics/2026-10-28-otto-minimum-viable-programme.md` (RC3) |
| The tickets: memory already ordered (#6162, #6163, #6165, #6229), the API surface (#6986), the eval harness (#6921), the laptop's bounded door (#5708), the tailnet crash-loop (#5894), escalation and decisions (#7388, #7384, #7340) | chidionyema/idp, all open unless stated |
| The homes as a concept, and the founder's 2026-09-10 quote on the matrix of combinations | `docs/explanation/otto-survival-matrix.md` |
| The laptop's honest role: a bounded command door the pod reaches over the tailnet; and the parity playbook that proves `mac-run-hostname` and `hindsight-answers` | `docs/explanation/otto-on-the-mac.md` (crew#561) |
| Verification removes self-certification: a verdict "produced by a process the agent cannot run" | `docs/explanation/verification-plane.md` (crew#631) |
