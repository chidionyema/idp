# The Once-Only Contract

**Status:** binding. Every mandatory door, loop and agent on the estate.
**Founder, 2026-11-08:** *"the amount of times issues was noted and logged is damning, it should
have only needed to occur once."* and *"map all root causes once and address all once must be part
of the contract."*

---

## 1. What was measured, before anything was written

This contract is not a wish. It is the response to five measurements taken from the live estate on
2026-11-08.

### 1.1 The incident funnel

`~/.estate/state/incidents.db`, 60 rows, read-only:

```
sensed        60  100.0%
ticketed      55   91.7%   (dropped 5)
dispatched    52   86.7%   (dropped 3)
verified      10   16.7%   (dropped 42)   <-- the cliff
closed        10   16.7%

dispatched -> verified : 10/52 = 19.2%
open and stuck         : 50/60 = 83.3%   (all 50 open > 7 days, median 9.6)
```

The loop is excellent at **recording** and fails at **resolving**. Every stage up to `dispatch` is
instrumentation; `verified` is the only stage that requires the fix to work, and that is where
80.8% of dispatched incidents die.

### 1.2 Recurrence

Same ledger, fingerprints over normalised titles:

```
60 incidents  ->  32 distinct fault fingerprints   (47% of the ledger is recurrence)
```

### 1.3 Root-cause collapse

The 50 open incidents, grouped by `(workflow, ref)`:

```
50 open incidents  ->  22 distinct root causes

  portal-app  on mutation/ldg-b8a43261685f   12x   #7616,7618,7620-7623,7625,7629-7631,7637,7640
  Generate Estate Topology DAG  (no ref)      9x   #7641,7643-7648,7651,7652
  ci          on mutation/ldg-b8a43261685f    7x   #7615,7619,7627,7628,7632,7635,7638
  context-index on main                       2x   #7602,7609
  otto-parity   on main                       2x   #7597,7598
  build-multiarch on main                     2x   #7614,7617
  16 further faults, one ticket each
```

**28 of 50 open tickets are duplicates of 3 faults. One ref (`ldg-b8a43261685f`) holds 19 tickets.**
And #7581 reads *"Incident loop saturated: P0 blockers"* -- the loop sensing its own saturation and
filing a ticket about it instead of converging.

### 1.4 Silent failure is a class, not an instance

A scan for `except: -> return "" | None | [] | 0 | False | pass` across
`platform/estate/memory`, `mcp/plugins`, `platform/estate/libexec`:

```
119 silent neutrals
```

`platform/estate/memory/door.py:36` is one of them: the vault loader fails, returns `""`, and
`remember` prints an error and moves on. The neutral value is the poison -- downstream code cannot
distinguish "the door said nothing" from "the door said nothing went wrong".

### 1.5 A mandatory door can be down and say nothing

`https://mcp.mumchimp.com/estate/mcp` resolves to `193.123.184.22` (Oracle). TCP connects in
0.039 s, then the peer **drops the TLS handshake**:

```
curl: (35) LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to mcp.mumchimp.com:443
http=000 tls=1
```

`llm.mumchimp.com` on the same zone answers 200 behind Cloudflare. The memory door has been
unreachable while every agent's `remember` failed silently.

---

## 2. The contract

Six clauses. Each is falsifiable, and each has a gate that fails while it is violated.

### C1 -- Once only, per fault identity

A fault is identified by `(workflow, ref)` -- not by prose, not by time. The **first** occurrence
opens an incident. Every later occurrence of the same identity **increments that incident**
(`recurrence`, `last_seen`) and never opens a second one.

> *A ledger that holds 60 rows for 32 faults is lying about the size of the estate's problems.*

### C2 -- Recurrence escalates, it does not accumulate quietly

`score = base x (1 + log2(recurrence))`. The 12th occurrence of `portal-app` scores strictly higher
than the 1st. A fault that recurs is louder than a fault that appeared once, so dedup can never make
the worst faults the quietest.

### C3 -- A fault is closed only by verification

`state -> closed` requires `verified_at`, which requires the fingerprint to stop reproducing on the
ref. A ticket closed by hand, a claim released, or a dispatch returning 0 does **not** close an
incident. This is the clause the 19.2% conversion violates today.

### C4 -- No silent neutral on a mandatory door

A mandatory call returns a **typed outcome**, not a bare value:

| outcome | meaning | what must happen |
|---|---|---|
| `answered` | the door replied | proceed |
| `degraded` | the door is unreachable, caller chose a documented fallback | the fallback is written at the call site |
| `unreachable` | the door is down | **spool durably, report, escalate -- never return neutral** |

`return ""` / `None` / `[]` / `False` on a mandatory call is a defect. Where degraded behaviour is
correct (an optional cache), it is declared with `# door:optional` -- a written decision, not an
accident.

### C5 -- A failure survives the failure

When a door is down, the payload is written to a durable local outbox **before** the call fails, and
replayed on recovery. A lesson learned during an outage must not be lost by that outage. If the
outbox itself cannot be written, that is a hard raise -- silence at that point loses the record
with no trace.

### C6 -- Every fault gets an owner before it gets a ticket

An incident with no `dispatch_leg` and no `dispatch_ref` is `UNOWNED` and is escalated on its own
schedule. It never sits as a record waiting for a human to notice. Full autonomy means the loop
either dispatches an agent, or states precisely what capability is missing that prevents it.

---

## 3. Migration -- the 28 duplicates already filed

The contract is retroactive, not aspirational:

1. **Map**: every open incident is given its `(workflow, ref)` fingerprint.
2. **Pick a survivor** per fingerprint -- the lowest ticket number.
3. **Collapse**: the duplicates are closed with a comment naming the survivor, so no ticket
   disappears without a pointer.
4. **Address once**: the survivor is the unit of work. Fixing it closes every duplicate by
   construction, because they were always the same fault.

Measured result to be proven: `50 open -> 22 open`, `0 tickets orphaned`, and
`dispatched -> verified` conversion rising as the duplicates stop re-entering the funnel.

---

## 4. Falsifiers (a gate that cannot fail is not a gate)

| id | must FAIL when | must PASS when |
|---|---|---|
| F1 once-only | a second incident is opened for an open fingerprint | recurrence increments the existing row |
| F2 escalation | the 12th occurrence scores `<=` the 1st | score rises monotonically with recurrence |
| F3 verification | an incident closes without `verified_at` | it closes only after the fingerprint stops reproducing |
| F4 silence | a mandatory door returns a neutral on failure | it returns `unreachable` + spool + escalation |
| F5 survival | a payload written during an outage is lost | it is replayed and lands once |
| F6 ownership | an incident sits `UNOWNED` past its schedule | it is escalated with the missing capability named |

---

## 5. Why this is the contract and not a patch

The estate had every part of the loop already, separately: sensors, a ledger, a scorer, a dispatcher,
a Greenlane, a claim gate. `incident-loop.py`'s own docstring says so -- *"what did not exist was the
join"*. Fifty incidents later the join still is not the problem: the **identity** is. Without fault
identity there is no "once", so recurrence is indistinguishable from novelty, and the estate pays
full price for the same fault on every occasion.

Give the estate fault identity and three things follow at once: duplicates collapse, recurrence
becomes a signal that escalates, and closure means something because only verification can produce
it. That is the difference between a log and a loop.
