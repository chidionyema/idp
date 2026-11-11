# Diagnosis - the nine token-reduction patterns, graded against the estate

**Date:** 2026-11-11
**Scope:** agent <-> runtime control flow, tool exposure, and context growth
**Method:** read the repo and ran the estate's own instruments. **Every number below was measured
this turn, with its command shown.** A thing I could not measure says **BLIND**, never zero.

---

## 0. The one finding

The estate is **not missing these layers**. It has built most of them. The recurring failure is
different and more expensive:

> **We build the mechanism, and then nothing calls it.**

Three of the nine patterns are in exactly that state: built, correct, and **not operating**
(AGENTS.md section 3 - "built" and "operating" are different facts):

| mechanism | state | measured proof |
|---|---|---|
| `bin/estate-fleet inbox` (durable JetStream per-agent inbox) | **BUILT, 0 callers** | `rg -ln "estate-fleet (inbox\|recv\|listen)" bin platform docs .github` -> 1 file, the producer |
| `platform/efficiency/token_killer.py` (output compression) | **BUILT, dependency absent** | `command -v rtk` -> ABSENT, so it rewrites to a binary that does not exist |
| `bin/estate-supervisor` (relaunch a session) | **wired to violations only** | `bin/estate-supervisor:11-14,18` - never fired on a *work* event |

That is the same defect as a gate that cannot fail (section 9 R2), one layer over: an instrument nobody
calls is not an instrument.

---

## 1. Reactive wakeup - **GAP (the join is missing)**

The law is already written. `docs/decisions/0044-machine-first-agent-action.md:105-106`:

> "the event that starts the work is a fact, not a poll. ... the anti-pattern to refuse is the poll"

### What we have

**A durable bus with a durable inbox nobody calls** - `bin/estate-fleet` stores messages in NATS
JetStream, stream `ESTATE_FLEET`, per-agent subjects, acks, replay:

```
bin/estate-fleet:54   await js.add_stream(name=STREAM, subjects=["estate.fleet.>"], ...)
bin/estate-fleet:122  sub = await js.pull_subscribe(subj, durable=f"{agent}-{kind}", ...)
```

**A relaunch primitive** - `bin/estate-supervisor:18`: *"it kills a pid and relaunches `pi --print`"*,
with `platform/estate/governance/supervisor.py:179 def resume_if_proved(...)`.

Both are correct. They are never joined: `inbox` has no caller (section 0), and `supervisor` fires on a
**violation**, never on **"your lane landed"**.

### Poll elimination is DONE - and it is not the same thing

`bin/lane-where` removed 1,277 polls (`docs/diagnoses/2026-10-23-agent-process-friction.yaml:91`),
and the executor refuses a park outright. Verified this turn:

```
$ sleep 300
FAILED  this command waits on something outside the process; the executor runs work, it does not park
        an agent (sleep 300 is a park, not a pace)

$ for i in 1 2 3 4 5; do bin/lane-where main --json; sleep 2; done
FAILED  this shape already has a door: do not compose it, run the door
```

**The distinction the estate is currently short of:**

- `lane-where` = **poll elimination**. One question, answered once, cheaply. The agent must still
  *decide* to ask, so the agent's turn is still the loop.
- **reactive wakeup** = the agent **ends its turn** and the runtime **re-invokes** it.

We solved the first and called it finished. The second was never built.

### Measured: the polls that remain (24 h, this turn)

```
$ python3 bin/process-census
  calls variants  class / tool
     60       54  ci-poll-loop / estate_execute     <- for/while + gh
     40       33  ci-poll-gh-run / estate_execute
     33       23  ci-poll-gh-api / estate_execute
      0        0  bare-wait                         <- ZERO: the park refusal works
```

**133 polling calls, and `bare-wait` at 0.** The refusal is doing its job, so what remains is not
laziness - it is **an agent with no non-polling option**: an agent waiting for a lane outcome it
cannot subscribe to.

### Measured: the laptop plane polls on a timer

```
$ ls ~/Library/LaunchAgents | wc -l                                                   98
$ rg -l "StartInterval|StartCalendarInterval" ~/Library/LaunchAgents | wc -l           60
$ rg -l "WatchPaths|QueueDirectories|KeepAlive" ~/Library/LaunchAgents | wc -l         36
```

| agent | interval | what it wants to react to |
|---|---|---|
| `ai.estate.incident-watch.plist:24` | 300 | a red CI run / new incident |
| `ai.estate.critical-watch.plist:25` | 60 | a critical function going down |
| `ai.estate.continuity-watchdog.plist:15` | 300 | a continuity break |
| `ai.estate.disk-watch.plist:15` | 60 | *(legitimate - disk fill has no event source)* |

`platform/estate/libexec/incident-loop.py` states its own ceiling: *"`tick` is what the laptop
watcher runs every five minutes."* Flux already **pushes** (`.github/workflows/flux-events.yml:22`,
`repository_dispatch`); the incident loop **asks GitHub again every 300 s** instead of subscribing.

**Do not convert all 60.** Disk, backup and drill timers are correct. Only the three work-event
agents above are polls for something that already emits an event.

---

## 2. SOPR / tool schema bloat - **GAP, measured at ~1,710 tokens per call**

```
$ python3 -c "..."   # measured over the live intent set
intents: 381
chars: 6840  ~tokens: 1710
```

`estate_list` returns **381 intent names ~ 6,840 chars ~ 1,710 tokens**, on every discovery call,
and the response in this very session was ~300 lines. `~/.estate/intents` holds 399 files.

SOPR's claim - 1,200 -> 420 tokens for tool discovery - is a 65% cut. The estate's number is
**1,710 tokens for zero task information**: it says what exists, not what is relevant.

**The change (one layer, additive):** a routed view. The door returns the 5-8 intents the task's
class needs, with the full catalogue still reachable via an explicit `--all`. Falsifier: a session
doing a greenlane handover discovers `lane-where`/`lane-submit` without ever seeing 381 names, and
the full list remains callable so a missing route is never mistaken for a missing capability.

---

## 3. Layered routing & caching - **PARTLY (half-built, and one half is a deliberate refusal)**

**Built:** pennyd is the one router with a free floor; `platform/llm/pennyd/providers/ollama.toml:16`
declares `aliases = ["triage"]  # cheap classification / does-this-need-a-model calls`.

**Not built:** the door does not escalate by difficulty. `rg -ln "difficulty|complexity|task_class|escalat"`
over the executor and libexec returns triage-verdict/delegate-build/etc., but the **executor door
itself has no cost tier** - it has no model choice at all.

**The semantic cache is deliberately refused, and correctly.** `platform/llm/pennyd/crates/penny-core/src/cache.rs:9-10`:

> "NO semantic cache on agent traffic (cross-serves tool payloads between callers), NO cross-key
> sharing (exact match only)."

This is a **safety decision with a reason** - a semantic cache would serve one agent's tool payload
to another agent whose "similar" request had a different answer. The estate runs an **exact-match
cache with adaptive TTL** instead (EWMAx3, `cache.rs:3-5`).

**So the honest grade:** layered routing = PARTLY; semantic cache = **deliberately refused, and the
refusal is right.** Recommending it here would be recommending against the estate's own measured
safety choice. The real gap is the other half of Uber's pattern - the **planner/executor split**:
`triage` exists but only `triage-verdict.py` calls it. Falsifier: a classification call routes to
`triage` and the router record shows the cheap lane, not a frontier lane.

---

## 4. Runtime-level task spawning - **PARTLY**

The session plane exists (`estate_session_start` -> `sb start` -> Temporal `SessionWorkflow`), and
`bin/estate-supervisor` can spawn. What is missing is the **event feed** into it - the same join as
section 1. `platform/estate/libexec/incident-loop.py` already dispatches to the bus *or* the task queue, so
this is a wiring task, not a build.

---

## 5. Context window accumulation (the append-only trap) - **PARTLY, unmeasured**

`bin/idp-context-pruner` exists and is real: *"Reads a JSONL transcript, applies the 3-Fail Rule to
prune consecutive failures, preserves successful evidence, and reinjects the goal."*

**BLIND on the benefit.** I found no measurement of what it saves, and no proof any live session
runs it. Per section 9 R6, a recovery path that depends on what it recovers is fragile - and here the
pruner's saving is **unmeasured**, which by section 3a means it cannot be called operational.

**The change:** emit an Optimus `optimus.metric.v1` per pruned session (tokens in, tokens out,
turns saved). Falsifier: a stale/missing metric blocks the claim from being called operational.

---

## 6. Static tool schema bloat - same row as section 2, measured at 1,710 tokens

Not a separate sink from SOPR; it is the same defect counted once. **Do not fix it twice** (section 6).

---

## 7. Uncompressed tool results - **GAP, with a built-but-dead compressor**

The door **does** truncate: `mcp/plugins/estate_executor.py:1162` -> `log_text[-4000:]`, so one log
tail is capped at 4,000 chars (~1,000 tokens) - that is a real mitigation.

But the general compressor is dead:

```
$ command -v rtk
rtk ABSENT -> token_killer compresses nothing
```

`platform/efficiency/token_killer.py:11-20` rewrites `cat|head|tail|grep|rg|find|ls|git log` to
`rtk ...`, and **`rtk` is not on PATH**. Every mapping is a no-op on the real path. Its only
referents are a feature file, two test files and two synthesis docs - **no production caller**.

This is the cleanest instance of the section 0 pattern: a correct design, shipped, wired to nothing.

**The change:** either vendor `rtk` into the toolchain (`bin/idp-install-deps` already pins
binaries - the same fix as the nats-server step in memory) or delete the module. **Do not leave it
looking alive.** Falsifier: `command -v rtk` resolves AND the efficiency gateway records compression
on a real call; or the file is gone.

Census evidence that results are still verbose: `json-shape` **310 calls**, `inspect-fs` **159
calls** in 24 h.

---

## 8. Model overkill - **PARTLY, and unmeasurable at the door**

The free floor is real (`ollama`, `triage`), and section 7a forbids a request executing as a model the
operator did not declare. What is missing is a **cheap-first decision at the door** (section 3).

**BLIND** on the utilisation: I can see the lanes, but not the per-call model split from the door,
because the door records no model. **The change:** the door records the resolved lane per job, so
"how many calls used a frontier lane for a trivial task" becomes a query. Until then, any claim
about overkill here is a guess and is not reported.

---

## 9. Retrieval thrash - **GAP, and the estate already has the count**

`inspect-fs` **159 calls** and `json-shape` **310 calls** in 24 h (`process-census`, above). Both are
"fetch a whole file / dump a whole JSON to find one field". The estate already has the targeted
tools and does not push them: `bin/symbol_slicer`-class slicing (`platform/estate/libexec/symbol_slicer.py`)
and `rg -l` (mandated by AGENTS.md section 8, which exists precisely because `grep -r` timed out).

**The change:** the executor's *refusal* text (which already teaches - section 1's park steer) names the
targeted form for a whole-file dump, exactly as it does for a poll. Falsifier: a `cat` of a file
over a threshold returns the sliced alternative and the following call uses it.

---

## 10. Retry storms - **GAP: there is a ceiling, not a breaker**

`CEILING_SEC = 100` (`mcp/plugins/estate_executor.py:62`) bounds **one job**, not a **sequence**. A
loop of bounded retries is legal today and burns the day's budget in minutes (section 9 R5 says every loop
needs a budget *and* a breaker; `bin/idp-circuit-breaker` exists).

**The change:** a per-(agent, command-fingerprint) attempt budget in the door, refusing the *n*th
identical failing command **with the steer** rather than SIGTERMing it. Falsifier: a repeated
identical failing command is refused at a declared count, and the refusal appears in the friction
ledger - the same instrument that already records `refuse-wait`.

Note the good news in the measurement: `bare-wait` at **0** proves the estate **can** make a
refusal stick fleet-wide when the refusal teaches. That is the mechanism to reuse.

---

## 11. Scoreboard

| # | pattern | grade | measured evidence | owner (one layer) |
|---|---|---|---|---|
| 1 | Reactive wakeup | **GAP** | 133 polls/24 h; `inbox` 0 callers; 60/98 timed agents | `bin/estate-fleet` + greenlane producers |
| 2 | SOPR / schema bloat | **GAP** | 381 intents, ~1,710 tokens/call | `estate_list` (routed view) |
| 3 | Layered routing | **PARTLY** | `triage` alias exists, 1 caller; door has no cost tier | pennyd + executor door |
| 3b | Semantic cache | **REFUSED (correct)** | `cache.rs:9-10` - cross-serves tool payloads | pennyd (keep) |
| 4 | Runtime task spawning | **PARTLY** | session plane exists, no event feed | `sb start` + bus |
| 5 | Context accumulation | **PARTLY / BLIND** | pruner exists, saving unmeasured | `bin/idp-context-pruner` |
| 6 | Tool schema bloat | **GAP** | same as #2 (counted once) | - |
| 7 | Uncompressed results | **GAP (built, dead)** | `rtk` ABSENT; door truncates 4,000 chars | `token_killer` + `idp-install-deps` |
| 8 | Model overkill | **BLIND** | door records no model | executor door |
| 9 | Retrieval thrash | **GAP** | `json-shape` 310, `inspect-fs` 159 / 24 h | executor steer |
| 10 | Retry storms | **GAP** | 100 s per job, no per-sequence budget | executor door + `idp-circuit-breaker` |

**3 gaps in the "built but uncalled" class (#1 inbox, #7 rtk, #1 supervisor).** That is the highest
leverage in this document: it is finishing, not building.

---

## 12. What to do, in order (one claim each)

1. **Finish the wake join.** `bin/estate-wait` + an `estate_wait` capability: a blocking durable
   subscribe on `estate.fleet.to.<agent>` (make `inbox` stop being a 1 s `fetch`), returning the
   payload, and the runtime re-invokes the agent. Falsifier: a session waiting on a lane event
   makes **1** door call, 0 polls, and wakes within 5 s.
2. **Producers, on change only.** `greenlane/engine.py` publishes
   `estate.lane.<branch>.{landed,red}`; `critical-watch.py` publishes
   `estate.critical.<id>.{down,up}`. A producer that publishes every tick **is** the poller.
3. **Routed `estate_list`.** 1,710 tokens -> the task's 5-8 intents. Additive; full list stays
   reachable.
4. **Kill or fix `token_killer`.** `rtk` absent = dead code that looks alive.
5. **Attempt budget in the door**, teaching on refusal, mirroring the `refuse-wait` pattern that
   already drove `bare-wait` to zero.

**Budgets and breakers (section 9 R5):** every wait needs a maximum, a declared fallback, and a
**never-silent** timeout - a wait that expires must return `PENDING`/`BLIND`, because a silently
expired wait reads as a healthy idle agent and would hide an outage behind good-looking dormancy.

**The class falsifier:** re-run `python3 bin/process-census` after 7 days. `ci-poll-loop` must fall
from 60 toward the floor set by real events, and `estate_list`'s payload must fall below 500 tokens.
If neither moves, we built a second unused `inbox` - and that is the thing to find out next week,
not to assume.

---

## 13. Re-runnable

```
python3 bin/process-census                                            # poll counts (60/40/33/0)
ls ~/Library/LaunchAgents | wc -l                                     # 98
rg -l "StartInterval|StartCalendarInterval" ~/Library/LaunchAgents | wc -l   # 60
rg -ln "estate-fleet (inbox|recv|listen)" bin platform docs .github   # 1 (the producer)
command -v rtk                                                        # ABSENT
ls ~/.estate/intents | wc -l                                          # 399 files / 381 intents / ~1,710 tokens
```

Every count is this turn's. Re-run them; if they disagree with this prose, the commands are right
and the document is stale.
