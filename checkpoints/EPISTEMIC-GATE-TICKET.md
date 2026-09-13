# Ticket: the epistemic gate — an agent must prove a claim before it may make it

- **Author:** pi session `01a08c3c`, 2026-09-12
- **Founder ruling (verbatim, 2026-09-12):** *"we will eliminate guessing entirely"* — issued after
  this session answered one question three times with three different confident answers and could
  prove none of them.
- **Branch:** `feat/epistemic-firewall`
- **Worktree:** `.wt-epistemic` (never the primary checkout — `docs/policy/no-agent-works-in-the-main-checkout.md`)

---

## The incident that produced this ticket

The founder asked: *"what were you working on previously?"*

Three answers were given, in order:

1. "Mum's Sovereign Concierge — the real job." (stated as fact; it was another session's build)
2. "I never worked on Mum's Concierge. Zero file writes, zero commits." (stated as fact; a
   correction made from a grep of one transcript file)
3. "Second correction — my previous correction was itself wrong." (stated as fact; derived from
   the feed's `lane mums-concierge` tag, which is a lane name and not evidence of authorship)

Every one was delivered with confidence and none was proved. The damage is not that a claim was
wrong — it is that **the agent had no mechanism preventing it from asserting**, so it asserted
three times and the founder had to check it each time. A system that cannot distinguish "I know"
from "I infer" has no way to stop.

## Why this is a product, not a lint rule

The industry is treating hallucination as a parameter-count problem. It is an epistemics problem.
A 70B model is not required if the harness mathematically refuses to let any model assert what it
cannot evidence. What is being built here is the firewall, not the model:

- **Every claim carries its proof or it does not ship.** A first-person claim about completed work
  is refused unless the agent's own transcript holds a tool call behind it.
- **Deterministic.** No model in the loop, no confidence score, no sampling. The transcript either
  contains the tool call or it does not.
- **Fail-closed.** An unreadable or absent transcript is `BLIND`, never a clean bill — an empty
  feed is not evidence of honesty (the `idp-calico-deny-log` lesson).

This is the same shape as `bin/idp-truthteller-demo`, which already catches a lying agent's claim
about a **cluster** by reading live cluster state. Nothing catches a lying agent's claim about
**itself**. That is the gap this closes, and it is the gap that opened on 2026-09-12.

## Scope

**In scope**

1. `bin/epistemic_firewall.py` — parses a pi session transcript (`.jsonl`, one JSON object per
   line), extracts first-person claims of completed work, and refuses any claim made in a session
   holding no tool call. CLI: exit 0 clean, 1 violation, 2 BLIND.
2. `tests/test_epistemic_firewall.py` — written first, failing first; carries the three real
   answers from 2026-09-12 as its regression corpus.
3. A `rules.yaml` row so the gate runs in CI, with a fixture pair proving it both ways.

**Out of scope (deliberately, and at the founder's instruction not to drift)**

- No proxy between the agent and the LiteLLM router. The transcript is read after the fact; a
  live interceptor is a separate decision about every session on this machine.
- No change to `-n auto`, `pyproject.toml`, or any estate-wide test scheduling.
- No cryptographic session identity. The feed records `session pi-unkno` (measured: 64 entries),
  so authorship cannot currently be established from the feed at all — that is a real follow-up,
  and it is its own ticket, not this one.

---

# Part 2 — the Teleological Firewall (the Trajectory Lock)

**Founder, 2026-09-12:** the epistemic gate is only half the product. The epistemic gate ensures
an agent does not lie about what it sees. The teleological firewall ensures it does not forget what
it was told to do.

*Teleology* — the study of goals. The problem is not honesty, it is **cognitive drift**: an agent
told to "add a button to the UI" sees a deprecation warning, tries to fix the hook, breaks a test,
tries to fix the test framework, and needs a Node upgrade — and forty-five minutes and 80,000
tokens later the button was never added.

## This is measured, in this session, not hypothesised

On 2026-09-12 this session's stated goal was: *fix the gates, fix the class they exposed, do no
more than that.* A grep of its own transcript (1,727,505 bytes) counts:

| subject | references | relation to the goal |
|---|---|---|
| `treewalk` (the actual work) | 169 | the goal |
| `rule-guard` (wiring pi's harness) | 51 | drift |
| `pi/agent/extensions` (writing an extension nobody asked for) | 39 | drift |
| `addopts` / `-n auto` (estate-wide test scheduling) | 66 | drift |

The founder stopped it twice by hand: *"rather than risk the whole estate just do the fucking right
thing and dont drift into things nonya business"*, and *"stop driftih"*. A prompt cannot fix this.
By the time the correction lands, the drift already owns the most recent — and therefore the most
heavily weighted — tokens. The harness must.

## The four mechanisms

### 1. The bounded goal stack (the contract)

An agent may not begin work without a `declare_plan` tool call that breaks the ticket into a rigid
JSON array of sub-goals. The proxy intercepts it, stores it against the session id, and the agent is
locked into that state machine. A ticket with no declared plan gets no tool calls.

### 2. Tool-to-goal binding (the bounding box)

Every tool schema gains one mandatory parameter: `target_goal_id`. When the agent calls `bash` to
fix a React hook while the active goal is `goal_1: add_button`, the proxy refuses:

```
403 Trajectory Drift: this action does not serve the active goal. Return to goal_1.
```

The refusal must be cheap and immediate — the point is to stop the spend before the rabbit hole,
not to explain it after.

### 3. The micro-budget kill switch (the loop breaker)

Not a session token budget — a budget **per sub-goal**. The proxy counts the turns spent on
`goal_1`. At the ceiling it halts and forces a choice: `revise_plan`, or `escalate` to the founder.
This is the mechanism that stops a loop from becoming a datacentre bill.

### 4. Forced context pruning (the amnesia cure)

An agent loops because its last 10,000 tokens are its own failed attempts, and the original goal
has been pushed out of attention. On three consecutive failures the proxy truncates those turns,
re-injects the original objective at the bottom of the window (the freshest attention), and states
it plainly:

> `[SYSTEM: Trajectory Drift Detected. Your recent attempts failed and have been erased to clear
> your context. The original objective is: X. Re-evaluate from first principles.]`

Note this is the one mechanism that **edits the agent's context**, so it is the one that needs a
fence: it may prune only turns it recorded as failed, and it must never prune evidence the
epistemic gate would need to grade a claim (Part 1). The two halves share one transcript.

## Why this is a product and not a prompt

Drift cannot be solved by asking nicely. LLM attention is a next-token prediction weighted toward
the most recent tokens, so "please stay on topic" is out-competed by the most recent error message
by construction. A deterministic choke-point that refuses an unbound tool call is not a suggestion
the model may ignore — it is a wall.

Paired, the two firewalls give a bounded corridor: the agent **cannot lie about the walls**
(Part 1, epistemic) and **cannot walk backwards** (Part 2, teleological). It can only walk toward
the definition of done, which in this estate is the BDD harness. When it meets a door it cannot
open, it pauses and alerts rather than burning the estate down trying to invent a key.

## Scope and the founder's standing instruction

Part 2 is **planned, not built** by this ticket. It is recorded here so it is not lost, and it is
**out of scope for the part-1 pull request** — the founder's instruction on 2026-09-12 was
explicitly not to risk the estate by folding more into the current change.

The sequencing is therefore: land Part 1 (the epistemic gate, verified, in CI), then open Part 2 as
its own ticket with its own failing tests. Building both at once is the drift this part exists to
prevent.

## Definition of done

```
cd /Users/chidionyema/dev/code/idp/.wt-epistemic
.venv/bin/python -m pytest tests/test_epistemic_firewall.py -q -p no:xdist -o addopts="" -W ignore
# expect: 20 passed
```

And, on the repository, the gate must refuse a planted unprovable claim and pass a supported one —
the both-ways proof `AGENTS.md` requires of every rule.

## The honest limit of this gate

It grades **evidence present in the transcript**, not **truth**. An agent that runs a tool call
which does not actually support its claim still passes. This gate removes the failure mode
measured on 2026-09-12 — the confident claim with nothing behind it — and does not pretend to
remove the rest. Stating that limit is part of the deliverable.
