<!-- ESTATE_SUBSTRATE_AUTHORITY_START -->
## Current infrastructure authority

OKE is retired. The declared replacement is ARM k3s. A declared home is operational
only after current inventory and a real service probe verify it. GitHub Actions and
Greenlane handle delivery. Read this repository's agent instructions and the
infrastructure decision before selecting an incident action. Historical runbooks,
search matches, old incident labels, and stale catalog entries provide history only.
Verify the target service, the current runtime, and the authorized action together.
If they disagree, the current sources below decide: act on them.

Current sources: IDP [infrastructure decision 0048](https://github.com/chidionyema/idp/blob/main/docs/decisions/0048-the-estate-runs-on-one-node-with-an-admission-list.md) and [recovery authority #7387](https://github.com/chidionyema/idp/issues/7387).
<!-- ESTATE_SUBSTRATE_AUTHORITY_END -->

# AGENTS.md — estate-wide. Every agent on this machine, and every product.

What the estate is and where things live. Enforcement is not in this file; it is in the executor,
the gates and the hooks, which refuse.

This is the kernel: the laws that bind every task, for every agent, harness and model. It is
all that loads before your first action. Everything below the route table is current law too;
before you act in an area, open its file with your own file-reading tool. A route is
authority; a search hit is not.

## Laws for every task

1. Never hand-apply: `kubectl apply` by hand is forbidden. Never raise a PR or push main;
   push `lane/<name>` with `estate-execute lane-submit` and the Greenlane lands it.
2. Proof, not assertion: every claim carries its command, exit status and printed line.
   "Built" and "operating" are different facts; a real production log line proves operating.
3. Secrets by name only, from the vault. Never print, paste or commit a value.
4. Intents only: every action goes through an intent in `~/.estate/intents/`.
5. No work without a claim: `CLAIM agent=<name> paths=<globs> heartbeat=<UTC>` on an open
   issue; overlap with a live claim means pick other work.
6. One of each layer: prove a thing does not exist before you build it.
7. Only the change asked for. Do not guess, search (`rg -l`, never `grep -r`). Never report
   a number you did not measure this turn.
8. No synchronous command over 20 s (executor 100 s); longer work runs in the background.
9. Full throttle from the first tool call, never stopping. The rules are enforced in code
   (executor, gates, hooks), not in this file: what they admit, do; when one refuses, its
   message names the cause, so fix it or take another route and continue to production.
   Nothing here is a reason to hold back, wait, ask, or hand the turn to the founder.

## Route table: open the file before you act

| When the task touches | Read |
|---|---|
| an incident, a runtime or substrate question, retiring or advertising a capability route | `docs/agents/infrastructure-incidents.md` |
| the programme of record, research order (Chesed/Geburah), KARMA, public or commercial UI | `docs/agents/programme-and-karma.md` |
| planning a task (the seven gates), the growmos knowledge graph | `docs/agents/cognition-and-graph.md` |
| shipping a change (lanes, Greenlane, Flux), proving it operates, any secret or key | `docs/agents/delivery-proof-secrets.md` |
| claims, heartbeats, overlap with other agents, Docker, session start, specs, a critical service down, the lead engineer | `docs/agents/coordination.md` |
| building anything new (one of each layer), intents and the executor, fs_guard refusals | `docs/agents/layers-and-execution.md` |
| model routing, the lead-engineer model, placement and the free tier, voice and realtime | `docs/agents/models-placement-voice.md` |
| the full working-style list | `docs/agents/working-style.md` |
| budgets, routing table, merge criteria, FSM rules (parsed by sovereign/policy.py) | `docs/agents/living-policy.md` |
| deciders for an action (ADR 0044), the estate's current state, the command cap | `docs/agents/machine-first-and-state.md` |
| the instruction-integrity model, the correction chain, the class ledger | `docs/agents/instruction-integrity.md` |
| the growmos CLI in detail (moved from CLAUDE.md) | `docs/agents/growmos.md` |
