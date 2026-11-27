<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## 12. Machine-first: every action names its decider (T-7, ADR 0044)

Every action an agent takes is a decision somebody made. **Before you take one, say which
decider it has** — and the answer is one of three:

- **`machine`** — a deterministic program decides: a rule, a schema check, a hash, a gate. The
  same input gives the same answer every time, and the answer can be re-derived by anyone.
- **`model`** — a decision model decides: a typed value with a calibrated confidence (JEV and
  its floor), never a vibe. Below the floor it escalates; it does not guess.
- **`judgment`** — a person decides. **This is the residue, and it must say why**: one of
  `value-tradeoff` (two goods the estate cannot rank without a human), `irreversible` (it cannot
  be undone, or it reaches outside the estate), `novel` (no precedent and no rule), or
  `low-confidence-escalation` (a decision model came back under its floor).

The order is machine → model → judgment, and every step down costs an estate a turn, a
confidence band, or a person. **"I was not sure" is not an irreducibility.** If you cannot name
the kind, the honest mode is `machine` or `model` — go and build the check that decides it.

The one store is `policy/agent-decisions.json` (the decision register). The mode is **derived**
from a capability's own source wherever it can be (`bin/capability-index` reads the intent's
steps, and the scripts they call); the register holds only what cannot be derived — the
judgement residue and the estate-level decisions. `bin/registry-gate` invariant **I-6** refuses a
declaration that lies: a mode that does not exist, a judgement with no irreducibility, a
judgement whose reason is a shrug, a machine decider the estate does not have, a model the estate
does not run, a decider who is not a role, a duplicated id. A declaration that merely drifts from
its source is a **finding**, not a refusal — refusing correct work is an outage.

The question, the answer, the measure:

```bash
bin/capability-index decisions      # the register, the derived modes, who woke the work
```

Measured on the running estate (2026-10-26, executor ledger, 30 days): **1,619 runs machine-
triggered** (the greenlane's own `unconverged`/`unmerged` loops) against **1,831 runs with no
trigger named**; **189,738 model calls** over 22 models in the window — each one a decision turn
a rule or a calibrated decision model could have made; and **24.8% of all door calls were
`estate_show`**, the agent asking the door how to use the door. **BLIND is an honest answer, not
a pass**: on CI there is no `~/.estate`, so the live measures are BLIND and the gate says so.

**The greenlane is this tenet's machine trigger.** A PR lands, CI runs green, Flux converges —
those are decisions a machine made and they need no agent. The spine (EFDA: Flux events →
NATS JetStream → a Temporal signal → a workflow that verifies the outcome) turns the rest of
the estate's waking into the same kind of trigger: an event starts the work, and the agent is
called to decide only what the event cannot settle. An action the spine wakes is `machine`
until it needs a judgement.

**The estate's health is ONE number, and the founder's concerns are weighted into it.** The
critical-function registry (`catalog/critical-functions.json`) lists what the estate cannot work
without -- the founder's own surfaces first, because the registry's order is the priority order
the estate walks. The critical-function spine measures each one every 60 seconds and raises a
structured incident for the first failing entry: the head of that queue is where an idle agent
belongs (ADR 0049). The metric is `estate_health`, the weighted share of passing entries read
off the spine's own verdicts (founder-critical entries carry weight 2):

```bash
python3 platform/estate/libexec/critical-probe.py estate-health
```

The registry is judged, not wished for: `tests/test_critical_functions_registry.py` (a rung in
`bin/idp-ci`) refuses an entry the spine cannot measure, an entry with no structured remedy, a
founder-critical entry out of order or without its weight, and a registry that omits a function
the estate cannot work without. What these rules MEAN -- the founder's judgement, the incidents
it came from, the situations it applies to -- is written down once, for the fleet, in
[docs/training/2026-10-30-founder-judgement.md](docs/training/2026-10-30-founder-judgement.md).
Read it before you act on a judgement call.

## 13. The estate's state right now

The founder asked for the work to be visible in one place instead of re-derived by whoever picks
it up next. This block is that place. Every row was measured on the day it names; a row that
could not be measured says so, never PASS.

| what | state | measured by |
|---|---|---|
| the context broker | LANDED and proven | PR #7326, squash `0d9a8db4`, Greenlane-Head `09d8a476`; re-proved from the landed commit (verdict ALLOW, 8 excerpts, `/healthz` ok); issue #7262 closed with proof comment `6462965317` |
| the OCI block storage | RECLAIMED | 7 dead TERMINATED CSI volumes (350GB) deleted through the `oci-reclaim` door; the compartment holds 5 volumes / 250GB against a 200GB allowance |
| the estate memory door | DOWN | writes answer `written=false ... UNWITNESSED`, reads answer HTTP 500; the upstream (`unified-memory.estate.internal`) is in-cluster and the cluster is not up |
| the laptop volume | RECLAIMED, continuously | the resident guardian (`ai.estate.disk-watch`) takes one bounded incremental step per cycle and prints a RESULT line with free space before and after; the old watcher freed 0M |
| the critical-function spine | EXTENDED; the estate's metric is now ONE number | `catalog/critical-functions.json` (7 functions + 1 assumption, founder-critical first) + `platform/estate/libexec/critical-watch.py` + `platform/estate/libexec/critical-probe.py`: the metric is `estate_health` (ADR 0049), judged by `tests/test_critical_functions_registry.py`. Measured 2026-10-30: memory-plane DOWN (the door's TLS handshake fails), router-lanes DEGRADED (4 declared lanes not served), spend-bound ok, estate-substrate RED (the cluster-state receipt is 4160 min old) |

The live surfaces are the estate graph (`growmos context` — every row above is a node there),
`crew/STATE.md` (the generated snapshot; regenerate it, never trust it), and `/fleet` (the live
board). This block is dated **2026-10-28**: when it disagrees with those, they are right.

## P0 COMMAND CAP (2026-11-13)

No synchronous command may run longer than 20 seconds; executor commands may run up to 100 seconds. Longer work runs as a background job with an id. No sleep greater than 10. No nohup daemon outside launchd.
---

