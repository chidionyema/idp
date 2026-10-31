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

> **Amended 2026-10-29.** The verdict stands; the noun was wrong. *Dispatcher* implies Otto
> routes work to capabilities it owns — it owns none of them. The accurate concept, ratified in
> `docs/decisions/0047-otto-is-the-estates-front-door-not-a-second-agent-platform.md`, is that
> **Otto is the estate's front door**: the surface layer plus the estate's human-in-the-loop
> plane, standing on the estate's own layers. See the amendment at the end of this document.

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
Telegram agent's chain; the doctor script exits 0 healthy / 1 broken / 3 blind and the intent
that fronts it exits 0 whenever it answered — the verdict is the last line, and `json=true`
keeps stdout a pure JSON document; `--heal` repairs through `flux-reconcile` and re-reads the
link; the contract is pinned by `tests/test_telegram_agent_doctor.py`.

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
- **A doctor that exits on its verdict gets refused by the estate's own policy.** Measured
  2026-10-28, with the estate already dark from this laptop: `would refuse
  telegram-agent.doctor -- 5/5 runs not ok in 30d, p_fail=0.86`. The policy reads an intent's
  30-day not-ok rate, and a doctor's non-zero exit means *the estate is broken*, not that the
  verb is broken — so the intent exits 0 whenever it answered and prints the verdict, while the
  general fix (the executor's per-intent `exit_is_finding` flag,
  `docs/specs/2026-09-29-machine-learning-dept.md` §6a) is what every diagnostic verb in the
  estate needs, `voice-doctor` and `router-doctor` included.
- **Waves 3 and 4 are product work**, and the product is the cheap part. If the estate spends
  its remaining effort on the portal page, the door work goes unfinished and Otto stays
  unprovable. The order above is not a preference; it is the dependency.

---

## Amendment — 2026-10-29: Otto is the estate's front door

**Spec:** `docs/specs/2026-10-29-otto-is-the-estates-front-door.md`
**Decision:** `docs/decisions/0047-otto-is-the-estates-front-door-not-a-second-agent-platform.md`
**Issue:** chidionyema/idp#7408

The founder's instruction of 2026-10-29: reconstruct the vision for Otto from every ticket,
spec and decision; judge the architecture that resulted; re-propose so the concept and the
architecture are unambiguous. This amendment records what that changed in this epic. It changes
no finding above.

### 1. The verdict's noun was wrong

This epic called Otto "a dispatcher over the estate's governed plane". A dispatcher routes work
to capabilities it owns; Otto owns none of them, and that is the finding, not a detail. The
concept is now named once:

> **Otto is the estate's front door.** Everything a human says to the estate, and everything the
> estate needs a human to say, crosses Otto. Below the seam, Otto owns nothing: it borrows the
> estate's one router, one memory, one executor, one verifier, one identity and one secret store.

Otto keeps the seam, the thread, the trust classes, the presence, the media pipeline and the
reply delivery — and it takes on the estate's human-in-the-loop plane (escalation, approval,
structured decisions), which is new work and the strongest claim Otto has to centrality.

### 2. The root causes gain one, and two decisions gain a gate

RC1 said Otto was asked to be an agent and told to dispatch. The deeper cause is in the spec's
§3.1: **every founder wish was answered locally, inside Otto, and no global constraint was
applied to the parts as a set.** Two decisions were written and never executed:

- **ADR 0050** (2026-10-02) — `otto_facts`, hindsight and the `otto-memory-store` Job are
  deleted, writes move to `remember`. Measured 2026-10-29: the Job is still in the tree, the
  deployment still points at hindsight, and `hermes-v2/otto/memory/` still ships `fast_recall.py`.
- **`docs/specs/otto-door-hands-and-senses.md:200-203`** — a model-driven shell never runs in
  the process that holds the bot token, the DB password and the GitHub token. Measured
  2026-10-29: `terminal` and `code_execution` are in `OTTO_TOOLSETS` of exactly that container.

A decision that is only a document does not move a manifest. The amendment therefore adds a
gate, not another paragraph: a **manifest-conformance gate** that fails when Otto's manifests
name a layer the estate owns.

### 3. The programme gains the waves under the seam

| Track | Wave | DoD in one line | State |
|---|---|---|---|
| Door (this epic) | 0 — the one doctor door | the doctor names the first broken link of every Telegram agent's chain | **landed** (#7361, #7380, #7386) |
| Door | 1 — the scheduled plane asks the doctor | the tick's rows come from the doctor; the tick stops self-cancelling (#7354) | open |
| Door | 2 — the answer floor becomes a gate | a delivery claim is refused when the answer link is FAIL | open |
| Seam (the spec) | 1 — route through the estate, keep the lifeboat | the default route is the estate's cloud router; the lifeboat is last and accounted | open |
| Seam | 2 — execute ADR 0050 | `remember` is Otto's only memory; the manifests name no other one | open |
| Seam | 3 — the secretless shell | no shell in the secret-holding container; estate actions go through intents | open |
| Seam | 4 — one verification plane | the doctor owns the verdict; the probe and the tick are inputs | open |
| Seam | 5 — the human-in-the-loop plane | a blocked agent reaches the founder by voice or Telegram with the blocker named (#7388) | open |
| Seam | 6 — more surfaces | one binding and one registry row per surface; the gateway untouched | open |

**Order.** The seam waves 1–3 are independent of the door track and may land first — they are
what make the door honest. The door's wave 1 depends on the seam's wave 4 (one verdict, one
plane). The seam's wave 5 depends on the seam's waves 1 and 3: an escalation that cannot act
is a notification. The seam's wave 6 depends on the door's wave 0, which has landed.

**What the amendment does not do.** It reopens no finding above; it claims no wave done except
wave 0, which has its own receipt; it touches no `AGENTS.md`, no lane value, no vault, and no
cluster by hand.

---

## Addendum -- 2026-10-30: the substrate moved under the programme

**Issue:** chidionyema/idp#7387 (recovery), #7393 (replacement)
**Measured:** 2026-10-30T03:20Z, from the laptop, against OCI, GitHub and the edge itself.

This addendum records a fact that changed the estate's ground while this programme was in
flight, states what it does to the waves, and restates the verdict. **It re-opens no finding
above and claims no wave done.** Its only new claim is that the receipt surface of this
programme has moved: what was provable on 2026-10-28 is not provable today, and the honest
answer for anything that needs the cluster is `BLIND`.

### 1. What was measured

| command | result |
|---|---|
| `oci ce cluster list --compartment-id ocid1.compartment.oc1..aaaaaaaaynd3mq5nhnccywzbmwfdevpkmvyzwcsxm7kyevei5s72ikyge5oq --all` | one cluster, `estate`, `lifecycle-state: DELETED` |
| `oci ce cluster get --cluster-id ocid1.cluster.oc1.uk-london-1.aaaaaaaak3vxjechxim2cnrxowiec4jjvagtcbpenob2oj5ftcrq7jwqsjxq` | `NotAuthorizedOrNotFound` -- "Authorization failed or requested resource not found" (the cluster is gone from the tenancy's API) |
| `oci lb load-balancer list --compartment-id ... --all` | one load balancer, `ACTIVE`, public IP `193.123.184.22` -- the edge exists and has nothing behind it |
| `curl -sS https://mcp.mumchimp.com/` | `curl: (35) TLS connect error: error:0A000126:SSL routines::unexpected eof while reading` |
| `curl -sS https://llm.mumchimp.com/` | the same TLS EOF |
| `curl -o /dev/null -w '%{http_code}' https://api.github.com/` | `200` -- the control: the laptop's internet is fine, so this is the estate and not the network |
| `kubectl` against `141.147.80.229:6443` | no answer (the control plane went with the cluster) |

The tenancy has no live cluster to create a replacement in (`oci ce cluster list` returns the
deleted one and nothing else), and the OKE entitlement is gone -- #7393's body records it: "tenancy
container-engine limits are 0 (cluster, enhanced, node). OKE cannot be recreated", with the plan
of one A1 VM carrying k3s. #7387 carries the recovery, and its comment of 2026-10-30T02:17Z
records the measured capacity refusal: four governed applies asked AD-1 for a
`VM.Standard.A1.Flex` host and OCI refused every one with `Error: 500-InternalError, Out of
host capacity.` (`LaunchInstance`) while AD-1's own quota reported standard-a1-core-count
available=2 -- quota headroom is not capacity. The router and tunnel are therefore moving to the
one Always Free host OCI can create (AD-2 `VM.Standard.E2.1.Micro`), and the three CSI volumes
stay exactly where they are: detached and untouched in AD-1.

**The honest limit on this addendum:** the estate's own memory (`brief`/`recall`) and every
in-cluster truth are unreachable while the substrate is gone, so every receipt above is from
OCI, GitHub and `curl` on the laptop. Nothing here was read out of the estate's own store.

### 2. What it changes

**RC4 gets sharper, not softer.** RC4 said Otto's control plane was blind. Today the cluster
itself is `DELETED` and the edge load balancer has no serving backend, so RC4 is not a
condition -- it is the estate's state. This is not Otto's failure; it is the substrate's, and it
is tracked in #7387 and #7393 with its own recovery receipts. It matters here for one reason:
**every in-cluster receipt in this programme is now BLIND by construction.** Waves 1 and 2 and
seam wave 4 all end in a measurement that needs the cluster. A programme whose DoD cannot be
measured is a programme that reports nothing, which is exactly the failure RC3 describes about
the tick.

**The doctor's contract earns its keep.** The doctor exits `3` (blind) when it cannot read a
link, and the intent in front of it exits `0` whenever it answered. On 2026-10-28 that looked
like a nuance; on 2026-10-30 it is the design: the estate is dark, and the door still says
which link it cannot read, in a machine-readable line, instead of dying or claiming health.
Wave 0 is the only wave that is fully provable while the substrate is gone, and it is provable
because it was pinned by tests that need no cluster, no network and no executor.

**The tick's missing bound was never about the cluster.** The reason the SLA measured nothing
for two days was the job's own `timeout-minutes: 15` cancelling the run before the playbook
concluded -- a guessed bound, in the estate's own words (decision 0043). The cluster being dark
made the playbook slow; the *bound* is what turned a slow playbook into silence. That fix is
substrate-independent: it lives in the workflow and in the playbook's own budget, and it
converts "cancelled" (silence the SLA reads as a run) into "BLIND, unmeasured" (a red tick with
a reason). On a dark estate that distinction is the whole product.

### 3. The waves, restated for the estate as it is on 2026-10-30

| wave | needs the cluster? | provable on 2026-10-30? | state |
|---|---|---|---|
| Door 0 -- the one doctor door | no (tests drive it with a fake probe) | **yes** | landed (#7361, #7380, #7386) |
| Door 1 -- the scheduled plane asks the doctor | no for the bound, the budget and the BLIND grade; yes for the doctor's live rows | **partly** | the tick's bound lands on `lane/otto-parity-tick-recovery`; the doctor's rows still wait on the doctor's verdict being readable |
| Door 2 -- the answer floor becomes a gate | no (it grades a claim) | **yes** | open |
| Seam 1 -- route through the estate, keep the lifeboat | no (manifests and the router config) | **yes** | open |
| Seam 2 -- execute ADR 0050 | partly (the manifests are in the tree; the Job's runtime is in the cluster) | **partly** | open |
| Seam 3 -- the secretless shell | no (the conformance gate reads the manifests) | **yes** | open |
| Seam 4 -- one verification plane | yes (the doctor walks live links) | **no** | open |
| Seam 5 -- the human-in-the-loop plane | partly (the door is in the runtime; the escalation reaches Telegram) | **partly** | open (#7388) |
| Seam 6 -- more surfaces | no (a binding and a registry row) | **yes** | open |

The waves keep their numbers and their order from the table above; only their provability
changes. Nothing in the ordering rule is revised: the seam waves 1-3 are still independent of
the door and still land first, the door's wave 1 still depends on the seam's wave 4, and the
seam's wave 6 still waits on the door's wave 0.

### 4. The verdict, restated

**Otto is still worth investing in -- as the estate's front door -- and the condition on that
investment has changed shape.**

Before: *invest conditionally on the health floor*. Now: **the first cash and the first
attention go to the substrate (#7387, #7393), not to Otto features.** A door with nothing
behind it cannot be proved, and Otto's failure mode for three months was precisely that it
could not be proved. Building surfaces while the substrate is dark would repeat the mistake
this programme exists to end: work that no receipt can confirm.

The order therefore holds, and one rule is added to it: **every wave lands with a receipt that
does not need the cluster, until the cluster is back.** That is a discipline, not a delay -- it
is what keeps the programme from re-entering the state RC3 and RC4 describe, where the estate
was working and could not see itself.

### 5. What this addendum is not

- It is not a diagnosis of the deletion. That is the estate's incident, owned by #7387 and
  #7393, with its own receipts and its own recovery path.
- It does not re-open any finding above, and it does not soften RC1, RC2, RC3 or RC5.
- It claims no wave done except wave 0, which has its own receipt (#7361, #7380, #7386).
- It changes no manifest, no cluster and no vault by hand.
