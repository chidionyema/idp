# Work orders: how the cloud executor scales at no extra spend

Date: 2026-10-31. Status: tool built and tested (7 tests); not wired, not run in the cloud, not operating.
Founder, 2026-10-31: no extra spend; the executor should need to do the minimum: discovery and thinking are
finished beforehand, it runs a protocol and is done. Extends `agent-sandbox.yml` and the Greenlane; adds no
second lander. Companion: `docs/specs/2026-10-31-always-on-chief-executor.md`.

## The idea

Split a task into the part that needs intelligence and the part that does not.
- Thinking (discovery, design, the diff) is done once, by whoever is best placed, and frozen as a **work order**:
  `order.json` (claim, agent, base commit, allowed paths, patch digest, checks, lane) plus `change.patch`.
- Doing is a deterministic runner, `bin/work-order run`: verify, apply, check, commit through the repo hooks,
  push `lane/<id>`. No model, no tokens, no discovery. Cost is runner minutes on the free tier.
- A model is called only when an order fails (patch no longer applies, a check fails), on a free lane, with the
  failure as its whole task, and its output is a new order. A failed order never mutates the checkout.

This is the protocolkit `execution` protocol made concrete: declared scope (E1), dry-run of the same plan by
digest (E2), commit carries that digest (E3), per-step approval for irreversible steps (E4: none are allowed here).

## What the runner refuses (exit 2), proven by tests

Digest mismatch; a path outside the order's declared paths; any path under `.github/` or `.githooks/`;
a check that is not an allowed argv (no shell strings, first element `python3`, `pytest` or a `bin/` script);
a patch that does not apply to this checkout. A failing check rolls the checkout back (exit 3).

## Scaling

Orders are files, so the queue is a directory of orders: N orders run as N independent free-tier jobs, each
with its own lane and claim. The scarce resource becomes the thinking, which can be done by the strongest lane
once and amortised, instead of every executor re-deriving it. Orders for the same paths conflict by claim
(AGENTS.md section 5), which the claim gate already refuses.

## Trust boundary

Checks execute code, so an order is trusted only if it comes from a reviewed source: committed on a lane and
landed, or carrying the author's claim. The runner treats an unlanded order as untrusted: dry-run only.
Not built: that trust rule, the scheduled workflow that scans for orders, and the failure-repair loop.

## Next, in order

1. A workflow job (needs a credential and yamllint, which this session lacks) that runs `work-order run --apply
   --push` over orders found on main, one per tick, as the estate App.
2. One real order: this branch's work, packaged with `work-order make` and run by that job.
3. Proof: the Greenlane's verdict on the pushed lane's head.
