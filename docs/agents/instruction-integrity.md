<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## Instruction integrity — the model, in pure form (founder, 2026-11-14)

**Binding on every agent, every runtime, every surface, without exception.**

### Symbols

```
I   an instruction: (id, text, issuer, actor, accepted_at)
E   an effect: any change outside the actor's own context — commit, push, API write,
      message sent, file written outside the task sandbox, resource provisioned
T   an integration test: a command that exercises E on its real path
R   a receipt: (i, cmd, ran_at, exit, output_sha256, signer)
Y   yield: E is live, T passes, and a named beneficiary derives the benefit
```

### Axioms

```
A1  Every founder prompt is an I. Its text is stored verbatim; a summary is a different I.
A2  No E without a live I.     ∀E : ∃I  (actor(E) = actor(I)) ∧ live(I)
A3  No closure without Y.      close(I) ⇒ ∃T, R, Y  with T(R(i)) = pass ∧ benefit(Y) ≠ ∅
A4  No terminal by silence.    a turn ending is not a state; only Y, or an explicit refusal
                               carrying (cmd, exit, line)
A5  History is immutable.      records append-only; chain h = H(h_prev ‖ record);
                               tip anchored outside the actor's write scope
```

### State machine

```
received --plan--> planned --dispatch--> executing --T passes∧R signed--> verified
   |                  |                     |
   +------------------+---------------------+--> refused(reason, cmd, exit)   [not terminal]
                                                   |
                                                   +--> re-enter executing with a new attempt
verified is terminal. blocked/failed/abandoned are NOT states; they are attempts with evidence.
```

### Invariants and their falsifiers (all must exist as executable tests)

```
I1  an effect with no live I is refused ......... attempt an effect with no I -> expect refusal
I2  closure without T∧R∧Y is refused ............ close with empty probe -> expect refusal
I3  a no-op is not a terminal .................. end a turn with a question/summary -> expect refusal
I4  replay of a closed/expired I is refused .... reuse a verified I -> expect refusal
I5  a forged or edited record is refused ....... append/alter a record -> expect chain/signature fail
I6  delegation carries the parent I ............ child with no parent I -> expect refusal
```

### The generalisation

The model is not about commits. It applies to **any effect on any surface**: a Telegram message, an
API write, a deploy, a provisioned resource, a payment. Each surface binds as:

```
surface  ->  door  ->  gate(I live, R signed, Y present)  ->  effect  |  refusal(reason, cmd)
```

A surface that cannot name its door, its instruction check, and its falsifier is not integrated;
it is unguarded, and it is reported as unguarded rather than assumed safe.

### Compensation (required, not optional)

Every defect found under this model mandates, in the same change:
**(a)** the fix, **(b)** the falsifier that would have caught it, **(c)** the sweep of sibling
surfaces, and **(d)** a recorded recurrence check. A fix without (b)-(d) reopens the class.

### The correction chain — one pattern, five links, no exceptions (founder, 2026-11-14)

An error is corrected only when the whole chain completes **in the same change**:

```
CA1  instance      fix the thing that is actually wrong, now
CA2  proof         an integration test that fails before the fix and passes after; run it
CA3  class         a compensating action that plugs the GAP that allowed it -- not the symptom
CA4  broadcast     tell the other agents in the same turn: what broke, where, what to do instead
CA5  class ledger  register the class so a second occurrence is a governance failure
```

A fix without CA2 is a claim. Without CA3 it repairs one instance and leaves the class open.
Without CA4 the fleet repeats it within hours. Without CA5 nobody can prove the class is closed.

### The class ledger is the point

`catalog/issue-classes.json`, one record per class:

```
{class, first_seen, instances[], gap, compensating_action, falsifier, owner,
 surface(s), status: open|closed, recurrence_checks[]}
```

**A class may occur once.** A second instance of a registered open class is not an incident to
triage; it is a governance failure that names the agent who closed CA1–CA3 without CA4–CA5.

### Surfaces bound by this chain

Every surface that can produce an effect, including the ones with no hook: commits, lanes, the
Telegram spooler, MCP doors, cloud APIs, and **DSH web** — the session ingress where a founder
prompt first becomes an instruction. A surface is bound when it can name its door, its falsifier
and its class record; until then it is reported as UNBOUND, never assumed covered.

### Why this is self-reinforcing

CA3 changes the gate, CA5 makes the gate's silence visible, CA4 makes every agent carry the fix
without being told. The next agent does not need to know the history: the door refuses, the ledger
names the class, and the broadcast is already in the record it reads at session start.
