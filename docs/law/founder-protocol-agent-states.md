# The Founder Protocol - agent states and the Telegram founder door

**Status: standing law.** Issued by the founder over Telegram, 2026-11-09. Written once,
here, so no agent ever needs it repeated and no agent has to re-discover it. This is the
single canonical text; the machine enforcement is `catalog/agent_states.py`.

---

## 1. The three states - closed, enforced, no fourth

An agent given work has exactly three states:

| state | meaning |
|-------|---------|
| `in-progress` | the agent is working. **This is the default.** |
| `yielding` | the agent is still driving the work but has surfaced ONE bounded, structured decision to the founder (below). Yielding is live: the agent keeps working every other part of the task. The founder's tap is a capability, never a prerequisite. |
| `abandoned` | the work is released: claim lapsed or forfeited, session stalled, or superseded. Terminal for this owner - **auto-reassigned, never silently resumed.** Resuming requires a fresh claim. |

There is **no fourth state**. `running`, `blocked`, `narrating`, `pausing`, `done` are
**not** states an agent may report. A stalled session is auto-reassigned. Enforcement:
`catalog/agent_states.py` - `validate_state` and `validate_transition` raise on any value
outside the three, on an empty value, on a missing value, and on an illegal transition
(`abandoned -> in-progress` is refused). The falsifier `tests/test_agent_states.py`
proves this two ways. **No room for gossip, no room for error: a state that is not one
of the three cannot be expressed.**

## 2. Autonomy is the default - the founder is always there

Operate **as if the founder is always present**, so the estate runs **fully autonomous**.

- The founder is not at a screen reading a console. An agent does not default to
  talking *at* him like a chat surface.
- The Telegram door is **always listening**. That makes the founder's presence a
  **capability (one tap away)**, never a **prerequisite**. No agent waits for him to
  "be there".
- An agent given work runs to **done = operational = proven** without stopping, without
  narrating progress, without pausing to check in.

## 3. Telegram is the sole founder door

Every blocker, security request, temporary grant, and decision flows through
**Telegram** - not GitHub mobile, not a signed trailer the founder is expected to
produce, not a chat console.

- The founder **approves by tapping in Telegram**. Otto confirms; the machinery acts.
- One tap unblocks / decides, with full context. The founder feels the estate working
  for him - premium, luxury, never a raw log stream.

## 4. Contact is the rare, structured event - and only after exhaustion

The **only** reason an agent may contact the founder is: it is genuinely stuck **and**
can **prove** it exhausted every discovery mechanism and playbook. That proof is the
precondition, and it is a YES/NO machine check, not a feeling:

- `growmos query` / `context`, the capability registry (`bin/capability-index`), the
  intent registry (`estate_list` / `estate_show`), the memory door (`brief` / `recall`),
  `work-audit`, the runbooks (`docs/runbooks/`), the diagnoses (`docs/diagnoses/`), the
  decisions (`docs/decisions/`), and the estate's own gates and doors - **all** tried
  first, with the command and its output named.

Then, and only then, the agent surfaces **one** bounded decision with full context and a
one-tap answer - and keeps working everything else. Contacting the founder is not a
state; it is a question routed through the door while the work continues in `yielding`.

## 5. The only stop conditions

An agent stops only at:

1. **Done** - operational and proven (a real production log line, not a green gate), or
2. **Seriously blocked** - after trying to unblock, reported with evidence: the intent
   run (`estate-execute <intent>` / `estate_invoke`), its exit status, and the line it
   printed.

There is no third. "Still open", "remaining", "want me to...?", "shall I...?", "next steps
for you", "let me know if..." are all the disease this law extinguished. A turn never ends
in one of them.

## 6. Where this is enforced

- **The three states**: `catalog/agent_states.py` (single source of truth) +
  `tests/test_agent_states.py` (falsifier).
- **The Telegram door**: `bin/founder-decision` + `sovereign/otto/decision.py` +
  `platform/otto-golden/` (the luxury concierge surface).
- **The law**: this file, linked from AGENTS.md, so every agent and every harness loads
  it at session start.

The founder never wants to repeat this direction to any agent. This file, and its
enforcement, are why he will not have to.
