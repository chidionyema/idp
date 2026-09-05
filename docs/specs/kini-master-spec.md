# KINI.AI master spec — the synthesized sovereign control plane, v1.0

**Author: the founder. Received 2026-08-25, pasted into a Claude Code session.**

Saved here because it had nowhere to live. He wrote it, then asked "id want to
save this doc but dont know how to", and that question is the first finding this
spec makes about the estate: there is no intake path for a document. It is
tracked as friction, not as a footnote — see "What saving this cost" at the end.

**Nothing in the body below is mine.** The markdown structure was destroyed in
transit — code fences arrived as the bare words `Table`, `plain`, `JSON` and
`gherkin`, and the pipe tables arrived as loose lines. Fences and table pipes are
restored; not one word, number, threshold or hash is changed, added or removed.
Diff it against the session transcript if you want that proved.

---

## 1. The unified doctrine

You do not build a better chatbot. You do not build a better runtime. You build a
neural operating system where the Founder is the root certificate, the estate is
content-addressed, and the interface is a presence model rather than a messaging
app.

The synthesis:

- **Gemini's Synaptic Fabric** provides the execution layer: checkpoint
  immortality, temporal branching, auto-distillation, and the shadow-founder.
- **Your Governance Kernel** provides the trust boundary: hardware-rooted
  sovereignty, Merkle DAG state, cross-model consensus, finite budgets, and
  capability-based A2A.
- **The Presence Model** provides the UX layer: four distinct presence states
  (Ghost, Haptic, Spatial, Converse) that govern when and how the system demands
  your attention.

Google AX is a runtime. The Synaptic Fabric is an execution mesh. The Governance
Kernel is a trust boundary. The Presence Model is the interface. All four layers
are mandatory. Remove any one and the system collapses into either a chatty bot,
an unsecured script, or an unusable fortress.

## 2. The presence model: UX as system architecture

The core insight: **Attention is the scarce resource, not compute.** The UI must
operate on O(1) attention. Chat is O(n) — you read every message. The Presence
Model is O(1) — you feel the estate, glance at topology, and only speak when you
choose to.

### 2.1 The four presence states

| State | Signal | Founder action | System behavior |
|---|---|---|---|
| **Ghost** (default) | None | None required | Estate runs silently. No screen pixels change. No haptics fire. Menu bar dot is grey. The only evidence of governance is that nothing has burned down. |
| **Haptic** (ambient) | Felt, not read | None required | Non-interruptive physical feedback: single tap = state commit OK; double tap = budget threshold approaching; sustained buzz = halt required, glance at Mac. |
| **Spatial** (review) | Visual graph | Founder clicks menu bar | Force-directed estate topology: nodes = sessions (color = health, size = burn rate), edges = capability invocations (thickness = data flow). Hover = Merkle root, budget, heartbeat. Drag to merge branches. Right-click to halt. |
| **Converse** (interactive) | Natural language | Founder initiates | High-bandwidth 1-on-1 strategy, debugging, venting, brainstorming. Unfiltered natural language with your lead copilot. Fires ONLY when you initiate. |

**State transition rules (hardcoded):**

- Ghost is the default. The system may only leave Ghost if a boundary condition
  is met.
- Haptic may fire without leaving Ghost. It is a sub-threshold signal.
- Spatial may only be entered by explicit founder action (clicking the menu bar
  app) or by a catastrophic alert (lockdown, integrity failure).
- Converse may only be entered by explicit founder action (sending a message) or
  by a dead man's switch recovery prompt.
- **The system may NEVER push a notification that causes a state transition from
  Ghost to Converse.** That is the old Hermes-v2 failure mode.

### 2.2 The zero-noise receipt protocol

In Command Mode (Ghost/Haptic/Spatial), agents do not generate natural language.
They emit terminal-style receipts — dense, structured, cryptographically
verifiable.

Receipt format:

```
[✓] DOC_COMMIT | file:docs/article_2026_08_25.md | hash:8f2a1b3c | tags:#ml,#governance | budget:-1.2k | state:a3d9e2
```

Rules:

- One line. No prose. No "I have successfully..."
- Every receipt includes a Merkle hash of the resulting state.
- Every receipt includes the token budget delta.
- Receipts are editable in-place (Telegram `editMessageText`) until the next
  state commit, then frozen.
- If the founder replies to a receipt with `undo`, the kernel reverts to the hash
  in that receipt.

### 2.3 The vision-to-repo pipeline (Converse → Command handoff)

This is the canonical example of how Converse and Command modes bridge.

**Step 1 — Ingestion (Converse mode).** Founder snaps a photo and types: "this
article is brilliant, pull out the core arguments and save it to the knowledge
base"

**Step 2 — Extraction (silent).** Hermes-v2 intercepts `message.photo`, routes to
Vision model via LiteLLM. Strict system prompt:

- Extract all text cleanly.
- Format as semantic Markdown.
- Generate 3-word slug for filename.
- Extract 3 keyword tags.
- Do not reply with extracted text. Return structured JSON only.

**Step 3 — Execution (Command mode).** Governance Kernel checks budget,
classifies op as `fs_commit` (non-destructive, no quorum needed), executes write.

**Step 4 — Receipt (Ghost mode).** A single line appears in the Converse thread
(because that is where the request originated), then the system returns to Ghost:

```
[✓] DOC_COMMIT | file:docs/article_2026_08_25.md | hash:8f2a1b3c | tags:#ml,#governance | budget:-1.2k
```

**Step 5 — Actionability.** If the founder replies `undo` to the receipt, the
kernel reverts the exact commit via Merkle hash. No guessing. No "which file?"

### 2.4 Predictive pre-authorization (the shadow-founder UX)

The Shadow-Founder is not just a local model trained on your past interventions.
It is a **predictive authorization layer** that changes the UX from reactive to
proactive.

- Current broken UX: "Budget exhausted. Approve?" (interrupts you at failure)
- Synthesized UX: "Agent `deploy-v2` exhausts budget in 4 steps. Pre-authorize
  50k refill? [Touch ID]" (interrupts you at prediction)

Mechanism:

- Before every state transition, the kernel runs a shadow planning loop: it
  simulates the next N steps, counts predicted tokens, and identifies if a
  boundary will be hit.
- If a boundary is predicted within the next 3 steps, the system surfaces ONE
  card in Spatial mode (or one haptic double-tap if you are away from the
  screen).
- One biometric gesture (Touch ID) pre-authorizes the entire **predicted
  trajectory**, not a single step.
- If you do not respond within T minutes, the agent hard-halts at the boundary
  (default-deny).

Result: **You approve futures, not events.** One gesture = multiple steps
covered.

### 2.5 Chat as emergency broadcast only

Telegram/WeChat carries exactly three things:

1. Founder-initiated conversation (Converse mode, unbounded)
2. Catastrophic alerts (integrity failure, lockdown, dead man's switch
   activation)
3. One daily digest at 09:00 local time, max 6 lines, signed by the kernel

Everything else — state diffs, budget alerts, branch completions, distillation
events — routes to Spatial HUD or Haptic channel. **The chat app is the fire
alarm, not the control room.**

### 2.6 Voice-as-root-certificate

Siri Shortcuts bound to the local kernel API:

- "Hey Siri, estate status" → auditory summary ("Three agents active. One budget
  threshold approaching.")
- "Authorize branch alpha" → Apple's built-in voice auth for low-stakes ops
- High-stakes (destructive ops, budget >10k refill) still require Secure Enclave
  touch.

No typing. No buttons for routine status checks.

## 3. The execution fabric (synaptic + governance)

### 3.1 Content-addressed checkpoint immortality

Every agent action writes a checkpoint. But unlike Gemini's original JSON dump,
checkpoints are **Merkle DAG nodes**.

Estate topology:

```
~/.estate/
├── dag/                    # Content-addressed Merkle DAG
│   └── <hash>.json         # Immutable state nodes (diffs, not full snapshots)
├── heads/                  # Branch pointers (like Git refs)
│   ├── main                # -> hash of latest main commit
│   └── experiment-1        # -> hash of latest experiment commit
├── interventions/          # Signed, append-only transparency log
│   └── <counter>_<hash>.json
└── distillation/           # Frontier traces queued for Ollama tuning
    └── <hash>_distill.json
```

Checkpoint structure:

```json
{
  "parent": "a1b2c3...",
  "timestamp": 1692931200,
  "diff": { "added_tokens": 200, "action": "tool_result", "tool": "git_status" },
  "context_hash": "d4e5f6...",
  "budget_remaining": 95000,
  "signature": "..."
}
```

**Key property:** Only the diff is stored. Full state is reconstructed by walking
the DAG from genesis. This makes branching computationally free — both branches
share immutable history.

### 3.2 Temporal branching

When an agent faces a high-entropy decision, the kernel does not guess. It forks.

Mechanism:

1. Agent reaches decision point (e.g., "which refactoring strategy?").
2. Kernel spins up 3 concurrent micro-sessions from the current DAG node.
3. Each branch explores one strategy silently (Ghost mode).
4. After N steps or budget-per-branch exhaustion, the kernel evaluates each
   branch against `AGENTS.md` success criteria.
5. The winning branch is fast-forward merged to main. Losing branches are
   archived (not deleted — Merkle DAG preserves them for audit).
6. Founder is notified via ONE receipt:
   `[✓] BRANCH_MERGE | main←experiment-3 | hash:9c8b7a | savings:+12k tokens`

**Edge case — founder override during branch:** If the founder halts while
branches are running, all branches freeze. The intervention receipt includes the
parent hash. On resume, founder may choose which branch to promote.

### 3.3 Auto-distillation pipeline

LiteLLM is not just a passive router. It is an **active learning gateway**.

Mechanism:

1. For complex ops, frontier model (Claude) executes first.
2. On success, the kernel captures:
   `(prompt, context, successful_completion, tool_calls)`.
3. The distillation queue feeds this trace to a local fine-tuning job (Ollama +
   llama.cpp LoRA).
4. Once the local model achieves >90% accuracy on the distilled task class,
   future instances of that task class are routed to local first.
5. The kernel logs the model switch with hash evidence:
   `[✓] DISTILL | task:git_rebase | local_accuracy:0.91 | routing:ollama`

**Cost impact:** Over 90 days, 60-80% of routine ops migrate to local inference.
API spend drops exponentially, not linearly.

### 3.4 The shadow-founder (predictive authorization)

A lightweight local model (fine-tuned on your intervention history) predicts your
likely response to boundary conditions.

- **Training data:** Every 🛑 tap, every budget refill, every branch merge
  decision, every undo.
- **Inference:** When a boundary is predicted, the Shadow-Founder generates a
  probability distribution over your likely actions.
- **UX:** If confidence > 0.95 and the op is within policy, the system
  auto-authorizes and logs:
  `[✓] SHADOW_AUTH | boundary:budget_refill | confidence:0.97 | founder_notified:false`.
  If confidence < 0.95, it surfaces for explicit authorization.
- **Safety invariant:** Shadow-Founder may NEVER auto-authorize destructive ops.
  Those always require hardware signature.

## 4. The trust boundary

### 4.1 Hardware-rooted cryptographic sovereignty

The mechanism:

- Overrides are signed by the Mac Secure Enclave (Touch ID / Face ID).
- The kernel verifies the signature against the enrolled public key before
  acting.
- Receipts are Merkleized into an append-only transparency log, not JSON files.
- A hardware monotonic counter prevents replay attacks.

**Fallback:** If Secure Enclave is unavailable, degrade to 2-of-3 multi-sig
(founder + 2 hardware tokens). Log the fallback with full attestation chain.

### 4.2 Cross-model consensus with policy invariant

For destructive ops:

1. Kernel routes prompt to 3 models via LiteLLM.
2. Requires 2/3 identical tool proposals.
3. AND the command must be within the `AGENTS.md` allowlist.
4. If 2/3 agree but the command is outside policy → **blocked**. Policy is a hard
   safety invariant above consensus.

For non-destructive ops: single model (cheapest available via LiteLLM fallback
chain).

**Stale vote rejection:** If model C responds after 30s timeout, its vote is
rejected. For destructive ops, partial quorum = hard fail, never proceed.

### 4.3 Finite state machine + budget enforcer

FSM states: `init → planning → tool_use → synthesis → terminal`

Rules:

- Every transition consumes tokens from the pre-allocated budget.
- Budget is enforced with optimistic locking (prevents race conditions).
- At zero, hard halt. No "ask for more." State is Merkleized. Session awaits
  signed refill.
- **Cycle detection:** `planning→tool_use→synthesis→planning` repeated 5 times =
  suspicious. Pause before 6th cycle.

### 4.4 Capability-based A2A (SPIFFE/SPIRE)

- Agents declare capabilities in `AGENTS.md`.
- SPIFFE IDs authenticate every A2A message.
- mTLS binds identity to communication.
- Revoked SVID = instant isolation from the synaptic bus.
- **Ghost agent detection:** 3 missed heartbeats = SVID expiry.

## 5. Observability and auto-termination

Self-terminating conditions:

- Confidence < 0.4 for 3 consecutive reasoning steps → soft halt.
- Latency > 30s (2s baseline) → retry once via fallback, then halt.
- Langfuse unreachable > 5 min → halt non-critical agents (blind execution is
  unacceptable).
- Alert volume > 50/hour → compress into signed digest, escalate to higher
  severity channel.

**Trace integrity:** Every Langfuse entry is signed against the session Merkle
root. Fake entries fail verification.

## 6. Implementation payload (crew handoff)

- **File 1: `synaptic_bus.py` — the kernel engine.** Merkle DAG operations,
  checkpoint/branch/merge, budget locking, interrupt polling, distillation queue.
- **File 2: `governance_executor.py` — the trust boundary.** Secure Enclave
  signature verification, cross-model consensus routing, FSM enforcement,
  `AGENTS.md` compilation, policy invariant checks.
- **File 3: `presence_bridge.py` — the UX layer.** State-to-UI translation,
  Ghost/Haptic/Spatial/Converse mode management, receipt formatting, predictive
  pre-auth surfacing, Siri shortcut binding.
- **File 4: `hermes_v2_patch.js` — Telegram adapter.** Photo ingestion → vision
  handoff, inline button → signed receipt, Converse mode gating, alert routing to
  correct channel.
- **File 5: `AGENTS.md` — living policy.** Capability declarations, FSM
  transition rules, budget defaults, model routing preferences, branch merge
  criteria.

## 7. Acceptance criteria (BDD)

```gherkin
Feature: Presence Model State Transitions
  Scenario: System remains in Ghost during routine execution
    Given 3 agents are active within budget
    When all agents commit states successfully
    Then the UI remains in Ghost mode
    And no Telegram messages are sent
    And menu bar dot remains grey

  Scenario: Haptic signals budget threshold without leaving Ghost
    Given agent deploy-v2 has 5k tokens remaining
    And its predicted next 3 steps require 8k tokens
    When the shadow-founder predicts a boundary
    Then the system fires a double-tap haptic
    And the menu bar dot pulses amber
    And no state transition to Converse occurs

  Scenario: Catastrophic alert forces Spatial mode
    Given the kernel detects a Merkle hash mismatch
    When integrity verification fails
    Then the system transitions to Spatial mode
    And the menu bar dot turns red
    And a single emergency message is sent to Telegram
    And the message contains the exact hash and remediation action

Feature: Vision-to-Repo Pipeline
  Scenario: Photo ingestion produces zero-noise receipt
    Given the founder sends a photo with caption "save this article"
    When the vision model extracts text and commits to docs/
    Then the system returns to Ghost mode
    And the receipt is exactly one line
    And the receipt contains a Merkle hash
    And no natural language summary is emitted

Feature: Predictive Pre-Authorization
  Scenario: Shadow-founder auto-authorizes low-risk boundary
    Given the shadow-founder confidence is 0.97
    And the boundary is a 10k token refill
    And the op is classified as non-destructive
    When the agent predicts budget exhaustion in 3 steps
    Then the kernel auto-authorizes the refill
    And logs a shadow_auth receipt
    And the founder is not interrupted

  Scenario: High-risk boundary requires hardware signature
    Given the boundary is a destructive op (git push --force)
    When the shadow-founder predicts the boundary
    Then the system surfaces a Spatial card
    And requires Touch ID signature
    And never auto-authorizes

Feature: Temporal Branching
  Scenario: High-entropy decision spawns silent branches
    Given the agent faces a refactoring decision with 3 strategies
    When the kernel forks 3 micro-sessions
    Then all branches run in Ghost mode
    And the founder receives zero messages during execution
    And after evaluation, one receipt is emitted with merge result

Feature: Auto-Distillation
  Scenario: Successful frontier execution queues local training
    Given Claude successfully resolves a complex git merge
    When the kernel captures the trace
    Then the distillation queue receives the prompt/response pair
    And a local LoRA job is scheduled
    And future git_merge tasks are routed to local model once accuracy > 0.9
```

## 8. The cost and velocity contract

**Direct costs:** $0 to -$150/mo (Ollama handles 2/3 quorum load, LiteLLM routes
cheap models for simple ops, self-hosted Langfuse on Oracle Free tier).

**Hidden costs managed:**

- **Velocity tax:** Branch-based policy (dev = permissive, main = strict). 60% of
  engineering time on traction, 40% on fortress.
- **False positive tax:** Shadow-founder learns your patterns. Predictive auth
  reduces daily interruptions from ~15 min to ~2 min.
- **Cognitive load:** High upfront (1-2 weeks learning spatial UI). Daily
  overhead near-zero after adaptation.
- **M&A burden:** Every crypto component maps to EU AI Act / SOC 2 clause. No
  resume-driven complexity.

**The deal:** You trade chat noise for spatial design. You trade reactive
interrupts for predictive pre-auth. You trade API dollars for local compute. The
system drives its own API costs to zero over time by teaching its local models
how the frontier models think.

---

## What saving this cost — the friction this document is evidence of

**The founder wrote a 3,000-word architecture spec and had no way to keep it.**
His words on handing it over: "id want to save this doc but dont know how to",
then "frictiona", then "governance annd seanlessness absent".

That is not a complaint about this file. It is §2.3 of this very spec failing on
its own author. The vision-to-repo pipeline exists as prose in section 2.3 and as
nothing else; the estate has no `fs_commit` op, no receipt, no `undo`. Saving
this required an agent, a worktree, a hand-written commit and a pull request —
seven minutes of a Claude session to do what §2.3 specifies as one photo and one
line of feedback.

Two things are absent, and this document names them:

- **Seamlessness.** There is no intake path for a document. Not from the phone,
  not from chat, not from the laptop. Every artefact the founder produces reaches
  the estate only by an agent typing it in.
- **Governance.** Nothing here was budgeted, quorum-checked, hash-committed or
  reversible. The commit that lands this file is trusted because a human read the
  diff, which is exactly the property §4 exists to replace.

**Related work already in flight.** `docs/specs/phone-idea-flow.md` (crew#182)
covers the phone → idea → board half of §2.3 and carries the founder's hard rule
for it: "I need it to confirm to me if I want it on the board. That's a simple
solve." This spec is the wider architecture that flow is one path through. The
MCP surface both need is crew#180 CP5, still open.
