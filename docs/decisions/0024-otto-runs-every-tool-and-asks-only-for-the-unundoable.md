# 0024 — Otto runs every tool, and asks only for what cannot be undone

- Status: DECIDED 2026-09-05 on the founder's instruction in session
- Deciders: founder
- Extends: 0021 (the founder wears two hats), 0022 (the founder override is voice-first), 0006
  (the platform answers for itself over one MCP)
- Governs: Otto's tool gateway (`otto/gateway/core.py`, `ToolGateway.call`, tiers T1/T2/T3) in
  `chidionyema/hermes-v2`, and the `[capabilities] destructive` list in `idp/AGENTS.md` that is
  the gateway's T3 floor.
- Founder record: this instruction was given verbatim in session 2026-09-05 while reviewing the
  Otto door-and-senses specification ("The word in the spec is about Otto, not you").

## The instruction

> Otto runs every tool without asking: git, terminal, research, estate queries, skills, voice,
> vision. The one exception is an action that cannot be undone. Before Otto runs one of these it
> replies "this needs your go-ahead" and waits for your next message:
> force push, delete files or directories recursively, delete a Kubernetes resource, drop a
> database or table, destroy infrastructure.
>
> That list is the destructive list already in the repository's rules, and the tool gateway's
> existing human gate enforces it. It stops a misheard voice note from deleting a deployment.

Recorded verbatim. One decision, and it is a ceiling on asking, not a new fence: a gateway that
interrupts the founder to check every tool call — even harmless ones a misheard word would not
endanger — is itself the failure the tool list exists to prevent.

## The decision

Otto asks before running exactly one class of tool call: one that cannot be undone. Every other
capability — git read and write short of force push, terminal work short of recursive deletion,
research, estate queries, skills, voice and vision — runs unattended, no consent round-trip.

The undoable class is closed and comes from the repository's own destructive list, already the
tool gateway's tier-floor rule:

- force push
- delete files or directories recursively
- delete a Kubernetes resource
- drop a database or table
- destroy infrastructure

This maps one-to-one onto the engine rules that exist today. `idp/AGENTS.md` `[capabilities]
destructive` is `["fs_delete", "git_push_force", "db_drop", "service_destroy", "rewind"]`, and
`sovereign/policy.py` already refuses those ops without quorum plus a hardware signature. The
Otto gateway's tier map is per-call: a `terminal` invocation whose command matches
`git push --force | rm -rf | kubectl delete | drop (table|database) | terraform destroy` is
denied at T2 and routed to the T3 human gate; harmless `terminal` calls are not. The voice note
that records "delete everything" therefore lands on the same door the text note does, reaches the
same irreversible route, and is stopped by the same gate.

### What the go-ahead looks like

When a route hits the undoable class, Otto does not pretend it ran and does not ask through a
side channel. It replies, in the thread the request came from: *this needs your go-ahead* — and
stops, holding the action until the next message from its human answers it. A misheard voice
note, an accidental mass-delete command, an over-broad `kubectl delete` — all stop at that one
plain sentence instead of at the cluster.

### What this explicitly is NOT

- Not a menu. There is no "should I also …" follow-up and no tier list offered back to the
  sender. The one sentence is the whole gate.
- Not per-capability permissioning. An "untrusted" sender never *sees* T3-capable tools exist
  (the gateway presents only tools at or below the envelope's effective tier), but that is a
  different, already-decided control — it is not the founder being asked before ordinary work.
- Not a ban on the undoable class. Otto *may* run a force push or a delete when the go-ahead is
  given. The gate is a pause for one human word, the guardrail the founder named — "auto-default
  up to a budget, refuse above it, ask only where proceeding either way would be unsafe or
  destroy something."

## Proof boundary

None of this is finished on a local run. The human gate is finished only when a *live* Otto
request that maps to the undoable class produces the exact sentence "this needs your go-ahead"
and holds the action — quoted from the forwarded cluster log — and a follow-up word from the
founder then lets the same request through. A unit test asserting the tier map is a probe, not
proof. Because the fork ([`chidionyema/hermes-agent`]) is gitignored and materialises only at
image build, the provable-green point is CI's build-agent-image run plus the hermes-v2 test
suite; the provable-true point is the live cluster, never a synthetic load.
