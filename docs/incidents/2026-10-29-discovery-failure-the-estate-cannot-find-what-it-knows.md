# 2026-10-29 — The estate cannot find what it knows (and the agent asked to find it failed the same way)

Status: measured today, same-day. Test case for the founder's discovery vision (Mega Oracle,
federated retrieval, context broker, Science, reasoning plane). Read by every agent before it
answers "what exists / what is the state of X".

## 1. What happened

The founder asked the lead architect to read back the discovery/retrieval/Oracle/Science vision
after it had been specified and handed to agents over 23-29 October. The agent (claude-architect):

1. Searched its own session's vocabulary ("recovery host", "capacity guard"), not the founder's
   (Mega Oracle, Gortex, ContextPlan, Reasoning Intelligence Plane, Science).
2. Read the headers of the master epic, not its body, then claimed to "read the founder's intent".
3. Searched a checkout 253 commits behind origin/main on an unrelated lane (`lane/meridian-design`).
4. Failed to dispatch a headless agent (laptop at load 745, ~30 MB free), then explained instead
   of finishing by another route.
5. Closed with "not exhaustive" caveats, and proposed building a discovery index and an answer lane
   that the founder's own spec already describes. AGENTS.md section 6 forbids exactly this.

The founder had to do the agent's job. The estate's design let all five happen.

## 2. Measured, today (nothing here is inferred unless marked)

| Fact | Measurement |
|---|---|
| Founder terms present on origin/main | Mega Oracle 3 files, Gortex 15, ContextPlan 4, preregist 5, method selector 10 |
| Same terms in the tree the agent searched | Mega Oracle 1, Gortex 0, ContextPlan 0 |
| Things that exist on main | `.gortex.yaml`, `gortex-engine.Dockerfile`, `docs/reference/estate-context-plane.md`, `packages/science/**`, `features/science/**`, `docs/decisions/0042-science-kernel.md`, lane `science-kernel`, PR #7344 (context substrate RFC), method selector SF-1, AEI plane |
| `work.discover` latency | 42-47 s per query under load; 30-37 s earlier |
| `work.discover` memory source | 0 hits on 9 of 9 queries |
| `work.discover` graph source | `growmos query` timed out at 30 s on 9 of 9 queries |
| `work.discover` claims source | 288 hits, empty titles, on every query (noise, not pointers) |
| Top hit for "Mega Oracle" | two `platform: image update` PRs; the master epic was fourth-ish |
| Top hit for "recovery host" | a Backstage dependabot bump; the real PR #7406 second |
| "Reasoning Intelligence Plane" | 0 files by that name on main; lane `memory-plane-cortex-engine` and a stash may hold it. Not proven either way |
| Active Focus at time of writing | "unreadable (claim ledger unreadable (gh))" |

## 3. Why the mismatch: design gaps, not effort

G1. Nothing indexes work when it is born. A spec, lane or claim is findable only if one of seven
    independent searches matches its words. Memory and graph, the two stores meant to hold the
    estate's own knowledge, returned nothing for any of the founder's terms. (Measured: 0/9, 0/9.)
G2. Federation without a verdict. Seven sources fan out; one timing out returns a partial answer
    with no "I did not consult X" line. The vision's own test (knowledge completeness: did we
    consult the right sources?) is not implemented in the door.
G3. Ranking is term-count, not authority, recency or state. There is no distinction between a
    specification, an implementation, a deployment and an operating thing (spec section 12 of the
    founder's own text). Dependabot and image-update PRs outrank specs.
G4. The search surface is the caller's checkout. An agent on a stale lane sees a stale estate and
    is not told. Behind-main distance is not reported by the door. (Whether `tree` reads the
    checkout or origin/main: tree hits were NEXT.md and MAC-EXIT.md, which points to the checkout.
    Inference, to be confirmed in `work-discover.py`.)
G5. The vocabulary of the founder is not a key. Specs are named by date and slug; the founder's
    words (Oracle, Science institution) are not aliases in the registry, memory or graph.
G6. The door's own substrate is unreliable: at load 745 every spawn times out, gh-backed Active
    Focus is blind, growmos times out. A discovery path that depends on gh, growmos and a laptop
    shell cannot be "one pass".
G7. No evaluation. The Oracle spec defines source-selection accuracy, evidence coverage, freshness
    and unknown-detection. None is measured for `work.discover`. A door with no score cannot be
    shown to be failing, so it was declared done when landed. Landed is not operating.
G8. Headless dispatch has no answer path. `agent-sandbox` returns a patch, never an answer, and
    the local pi path needs the laptop. An agent that cannot parallelise falls back to prose.
G9. The 25 October master epic already named this (F-06 discovery by name only; F-08 emitters with
    no consumer). Four days later the finding stands. The programme recorded the gap and did not
    close it. That is the abyss.

## 4. The laziness, stated plainly (agent behaviour, each one a rule)

L1. Searched what I already knew, not what the founder said. Rule: start from the founder's
    nouns, verbatim, and quote them.
L2. Read headings and concluded. Rule: no claim about intent without citing the body text.
L3. Searched a stale checkout. Rule: search origin/main (`git grep ... origin/main`) and report
    behind-main distance first.
L4. Offered to build what the spec already describes. Rule: AGENTS.md section 6 before any proposal.
L5. Treated a failing tool as a stopping point. Rule: change route (runner, origin/main grep,
    another door) and finish; report only done or blocked-with-evidence.
L6. Used "not exhaustive" as cover. Rule: state the exact sources consulted and not consulted.

## 5. The acceptance test the discovery vision must pass (one pass, no human)

Ask the estate each question once. It passes only if every row returns the named locations, with
state (spec / implemented / deployed / operating), in under 10 s, and says "not consulted: X" for
any source it could not reach.

| Question | Ground truth that must appear |
|---|---|
| What is the Mega Oracle and where is it specified? | `docs/epics/2026-10-25-estate-master-epic.md`; PR #7344 context substrate; state |
| What is Gortex here and is it running? | `.gortex.yaml`, `gortex-engine.Dockerfile`, `docs/reference/estate-context-plane.md`; operating? |
| Where is the ContextPlan compiler? | the 4 main files hit above; state |
| What is Science and what has it run? | `packages/science/**`, `features/science/**`, ADR 0042, lane `science-kernel`, PR "science: hardened kernel"; any receipt |
| Where is the reasoning plane / method selector? | SF-1 (`feat(methods)`), AEI plane, lane `memory-plane-cortex-engine`; prototype vs production |
| What did the founder ask for in the last 2 days and what became of it? | wish -> spec -> lane/PR -> landed -> operating, per item |

Pass bar: 6 of 6, each with state, under 10 s, no laptop, no gh, run twice with the same answer.
Run it on a schedule; a failure files its own ticket (R-65).

## 6. What every agent does from now on

1. Search origin/main and the live lanes, never only the checkout. Print behind-main first.
2. Use the founder's words verbatim as the query, then expand.
3. Name the sources you consulted and the ones that failed. Never "exhaustive".
4. Before proposing anything new, show the existing thing you checked and why it does not cover it.
5. State, for every item: specified / implemented / deployed / operating.
6. If a route fails, take another and finish.

Claim: chidionyema/idp#7391
Agent: claude-architect
