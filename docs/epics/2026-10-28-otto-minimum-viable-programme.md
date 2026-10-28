# Epic — Otto's minimum viable programme

**Date:** 2026-10-28 · **Claim:** idp#7347 · agent `pi`
**Decision:** `docs/decisions/2026-10-28-one-doctor-door-for-every-telegram-agent.md`
**Spec:** `docs/specs/2026-10-28-the-telegram-agent-doctor.md`

## What the founder asked for

> An evidence-based audit of Otto's three months with the estate — conversations plus codebase —
> that maps the root causes of its failure to deliver code, lands a written verdict on whether
> Otto is worth investing in, and the concrete plan to fully onboard it. (2026-10-28)

This document is that audit and that plan. It is written from what is in the tree, and every
claim below names its receipt.

## What Otto has produced in three months

| artefact | size | what it is |
|---|---|---|
| `docs/specs/otto-capability-inventory.md` | 91,496 bytes | the capability census |
| `docs/specs/otto-door-hands-and-senses.md` | 21,393 bytes | the door's design |
| `docs/specs/otto-five-capabilities-finished.md` | 8,383 bytes | the five capabilities |
| `docs/specs/otto-answering-floor.md` | 10,037 bytes | the bar: every surface for real, portal first |

Four documents, one of them 91 KB, and a set of surfaces. Read together with the platform
(`platform/otto-gateway/`, `platform/otto-golden/`, `platform/jit/`), the estate has a **real
Telegram door**: one bot owner, one webhook writer, one mirror, one staging bot, an answer
probe and a registration reconciler (`platform/otto-gateway/OWNER.yaml`).

What it does **not** have is code that an agent would call to get work done. Otto was given a
product to build — surfaces, seams, a portal page — and the seams are where the three months
went.

## The root causes, and the receipt for each

**RC1 — Otto was asked to be an agent, and told to dispatch.**
The floor spec's own landings are "Floor 1 — ask Otto on the portal" and "Floor 2 — the push
channel": a page, a stream registry, a binding. Each floor is a new surface. An agent that
dispatches to capabilities that already exist would have shipped a dispatch in week one. The
estate's law (AGENTS.md, one of each layer) already says a second platform is a stitch: the
estate owns routing, memory, identity, secrets, execution, evidence and verification. Otto
built a surface layer; it did not need to.

**RC2 — the estate proved surfaces, not outcomes.**
The probes were about the surface: the edge answers (a 200), the webhook is registered, the
deployment is ready. Two recorded failures are the same mistake: an edge 200 while the webhook
pointed at nobody; a 200 on the answer path while the door said nothing. `otto-answer-probe`
(the 15-minute probe that asks the real lanes and records a real completion) is the estate's
answer to this, and it is the right answer — it arrived late.

**RC3 — there was no single door, so every incident started from zero.**
Today the intent set has 103 entries, each narrow: `voice-doctor` for voice, `router-doctor`
for the laptop router, `k8s-diag` for the cluster, `silence-audit` for alert coverage, plus
the founder-surfaces probe and Otto's two CronJobs. Nothing joined them for a Telegram agent, so
an agent told "Otto is not answering" had to re-derive which of four links broke, using
whichever door it happened to guess. The cost is not one bad incident; it is that the estate
could not *see* Otto at all. Measured 2026-10-28: the estate does run a scheduled verdict for
Otto — `.github/workflows/otto-parity.yml`, every fifteen minutes, alerting the founder on
Telegram — but that tick answers the **founder**, on a schedule, about both Ottos and the layers
under them. It is not a door an agent can ask, it does not name the first broken link, and it
cannot repair anything. The estate could watch Otto; it could not *ask*.

**Measured 2026-10-28, and it is worse than "the tick is narrow":** the last six scheduled
ticks of `otto-parity.yml` were **cancelled**, and the two before them were red. The job
started at 15:26:04Z and was cancelled at 15:41:25Z — its own `timeout-minutes: 15` — with
every step before the playbook green (checkout, python, oci cli, kubectl, the OIDC token
exchange, the kubeconfig mint) and the playbook step itself `cancelled`. So the estate's Otto
SLA has **measured nothing for two days**: the first broken link is
`bin/idp-oke-break-glass otto-parity`, whose steps run `kubectl exec` without a bound, so a
cluster that does not answer turns the whole tick into a timeout instead of a row. That is
the same defect class as decision 0043 — a guessed bound, or no bound at all, in someone
else's place — and it is why the doctor names a link at a time instead of running one long
grader.

**RC4 — Otto's own control plane was blind, so Otto could not read its own state.**
Measured 2026-10-28, from this laptop: the cluster did not answer (`kubectl` reached the
100 s door ceiling), the memory door refused the connection (`URLError: EOF occurred in
violation of protocol`), and the executor refused every job with `the volume has 594 MB free,
under this door's 1500 MB floor`. An agent that cannot read its own state cannot prove what it
did. Every "Otto did not deliver" report in three months is downstream of this.

**RC5 — the ask had no DoD, so nothing could be called finished.**
"Full bleeding edge" (2026-09-06) is a direction, not a finish line. The floor spec is
excellent at naming the experience and silent on what proves it landed. Without a DoD, "done"
is a judgement, and a judgement is not a thing a lane can gate on.

## The verdict

**Otto is worth investing in — as a dispatcher over the estate's governed plane, and not as a
second agent platform.**

The reasoning, in the estate's own terms:

- The capability is not the bottleneck. The estate has already built execution, memory,
  identity, secrets, evidence and verification. What Otto would add on top is the founder's
  always-on Telegram presence with a real job: take a request, dispatch it to a governed
  intent, answer with the receipt.
- The three months failed because it was pointed at building surfaces (RC1) and at proving
  surfaces (RC2) — not because Telegram is the wrong interface.
- The missing piece was never a capability; it was a **door that proves the door works**, and
  an agent that can read its own state (RC3, RC4).

So the investment is justified **conditional on the health floor**. An Otto that cannot say
which link is broken is an Otto the founder debugs by hand; that is the thing three months of
work produced. The first thing this programme therefore builds is not a capability — it is the
door.

## The programme, wave by wave

Each wave has one measurable DoD. A wave is done when its receipt exists, not when it is
described.

### Wave 0 — the one doctor door (this PR)

**DoD:** `estate-invoke telegram-agent.doctor` exists; it names the first broken link of every
Telegram agent's chain; it exits 0 healthy / 1 broken / 3 blind; `--heal` repairs through
`flux-reconcile` and re-reads the link; the contract is pinned by
`tests/test_telegram_agent_doctor.py`.

### Wave 1 — the scheduled plane and the callable door become one

The estate already runs `otto-parity.yml` every fifteen minutes and alerts the founder on
Telegram. Wave 1 makes that tick **ask this doctor** for the Telegram rows instead of keeping
its own, writes the doctor's verdict into the capability registry's health store, and puts it
on `/fleet`.

**DoD:** the parity tick's Telegram rows come from the doctor (one set of rows, not two), the
doctor's verdict appears on `/fleet` with the link named, and an agent can call the same door
and get the same answer the founder sees.

The tick itself has to stop timing out first: measured 2026-10-28, its playbook step hangs
and its own 15-minute timeout cancels the run, so there is currently no verdict to join to
anything. The fix is a bound on every playbook step — the same lesson as decision 0043 — and
it belongs to the workflow's owner, not to this door.

### Wave 2 — the answer floor becomes a gate

No Telegram capability may be claimed as delivered unless its doctor links are `ok`. A claim
whose `answer` link is `FAIL` is refused by the gate, not argued about.

**DoD:** the gate refuses a delivery claim with a `FAIL` on the agent's chain, and says which
link.

### Wave 3 — Otto dispatches

Every request Otto accepts becomes a dispatch to a governed intent, and Otto's answer carries
the receipt. No side path, no bespoke call, no second surface.

**DoD:** a real Telegram question, answered by a real intent receipt, visible live on `/fleet`.

### Wave 4 — the portal surface (only after 0–3)

`/ask` on the portal, as `docs/specs/otto-answering-floor.md` describes it — last, because a
page in front of a door that cannot be proved is a showcase, not a surface.

**DoD:** a question typed in the portal is answered by the same agent, in the same thread, that
answers on Telegram.

## What "fully onboarded" means

Otto is fully onboarded when all five are true, and each is checkable:

1. **Its state is readable** — one call says every Telegram agent's health, and says which
   link broke (Wave 0), next to the verdict the scheduled tick already reaches the founder
   with (Wave 1).
2. **Its health is watched** — a scheduled verdict, an alert that names the link, and a receipt
   (Wave 1).
3. **Its delivery is gated** — nothing claims Otto is done unless the gate agrees (Wave 2).
4. **Its work is dispatched and receipted** — the request, the intent, the ticket, the answer
   (Wave 3).
5. **Its surface is the same agent** — portal and Telegram are one thread, not two products
   (Wave 4).

## The risks, stated plainly

- **The estate's control plane is currently dark** (RC4). Waves 1 and 2 need a machine that can
  reach the cluster and a data volume with room; until then the doctor reports `BLIND`, which is
  the honest answer and not a small one.
- **A doctor is a new thing that can be wrong.** It is pinned by tests that drive the walk with
  a fake probe — no cluster, no network, no executor — so the contract is falsifiable even
  while the estate is down.
- **Waves 3 and 4 are product work**, and the product is the cheap part. If the estate spends
  its remaining effort on the portal page, the door work goes unfinished and Otto stays
  unprovable. The order above is not a preference; it is the dependency.
