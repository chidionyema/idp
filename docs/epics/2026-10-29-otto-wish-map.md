# Otto's wish map -- every founder wish, and what satisfies it

The spec [`2026-10-29-otto-is-the-estates-front-door.md`](../specs/2026-10-29-otto-is-the-estates-front-door.md)
reconstructs **31 founder wishes** from the estate's own record, in six families (A never
silent, B everywhere, C superpowers, D truth, E the human-in-the-loop plane, F the estate's
law), plus **5 contradictions** between the architecture and the founder's later rulings.

A wish list is not a programme. This file is the tracking instrument: **one row per wish**, each
with the thing that satisfies it and **the falsifier that would prove the row is not really
satisfied**. A wish with no gate, no ticket and no receipt is visibly `NOT-YET`.

Every path and ticket number in the *where* column was checked against `origin/main` or against
the GitHub API on **2026-10-29**; the date each was read is stated where it matters.

## The four statuses

| status | meaning | what closes it |
|---|---|---|
| **ENFORCED** | a gate refuses the failure | the gate fails when the wish is broken |
| **OWNED** | an open ticket is working on it | the ticket lands, with its receipt |
| **RECEIPTED** | a dated measurement proves it | the measurement is re-run and still holds |
| **NOT-YET** | nothing owns it | someone claims it, or the founder decides not to |

A row may carry two statuses and one ticket -- `ENFORCED (baseline)` means the gate holds today's
violation as debt and refuses any **new** one.

---

## A. Never silent

| # | wish | status | where | falsifier |
|---|---|---|---|---|
| A1 | three homes, so the door is never out of options | RECEIPTED | `platform/otto-gateway/three-homes.yaml:1-47` -- three failure domains in one ConfigMap; the sixteen-lane matrix in `docs/explanation/otto-survival-matrix.md` | a home removed without a decision, or the door silent when one home fails (that is A7) |
| A2 | the lifeboat "is not the estate router with a different address, it is not the estate router at all" | OWNED | #7445 -- the lifeboat becomes the **last** rung, not the default | the door's default route is still the pod-local sidecar (that is F2) |
| A3 | free lanes must not queue behind a dying cluster ("theesare fr lands, can we use or ont", 2026-09-08) | OWNED | #7445; the chain order in `three-homes.yaml:66-82` | the estate router is still demoted to a rung while the free lanes are not first |
| A4 | no dependence on the laptop ("no i killed ollama because machine is slow... dont rely on macbook", 2026-09-10) | RECEIPTED | `three-homes.yaml:34-38` -- home 3 is Groq (free tier, no card); the laptop is gone | a lane in the chain that resolves to `127.0.0.1` or to the laptop's hostname |
| A5 | "never out of options that the national/global is about" | RECEIPTED | the estate's router carries the vendor zoo (`platform/llm/config.yaml`: openrouter, deepseek, minimax, glm, gemini, groq, cerebras, nvidia, sambanova) | the estate router loses a vendor lane and Otto has no other |
| A6 | availability outranks accounting ("otto must never go down", 2026-09-10) | OWNED | #7445 -- `router.outcome` must account for the lifeboat's turns; today `three-homes.yaml:80-82` counts only the estate's spend | a lifeboat turn appears in no spend table and no outcome stream |
| A7 | a third home must not be able to take the door down with it | OWNED | #5894 -- the token roll and tailnet node leak crash-looped `otto-gateway`; the lifeboat's egress sits in the door's own pod | the lifeboat's egress is still in the door's pod |

## B. Everywhere, any interface

| # | wish | status | where | falsifier |
|---|---|---|---|---|
| B1 | "the showcase has to actually wow and impress... need to see, visualise and interact" (2026-09-05) | **NOT-YET** | nothing owns it: the seam exists, the page does not | a portal page lands without a review against the bar |
| B2 | a new surface is one binding + one registry entry, no gateway rework | RECEIPTED | `docs/specs/otto-answering-floor.md:23`; the registry is `hermes-v2/otto/ingress/plugins.py:237-242` -- "Adding Slack is one entry here and one class above; nothing outside this module changes" | a new surface that needs a change outside the ingress module |
| B3 | a surface per channel: Telegram, HTTP, portal, Slack, email, voice, QR/camera | **NOT-YET** | Telegram and HTTP are live (`platform/otto-gateway/binding-seed.yaml`); nothing owns the rest | -- |
| B4 | voice first, voice ON by default, local STT, router as fallback | RECEIPTED | ADR 0039 (`docs/decisions/0039-one-mouth-the-router-owns-the-estates-voice.md`) -- one voice owner; `voice-asr`/`voice-tts` lanes on the estate router | a second voice owner appears |
| B5 | the edge voice loop (offline ASR/intent/TTS) is the target, not the state | **NOT-YET** | ADR 0033 names it as the target; nothing is building it | -- |
| B6 | approvals and applies reachable from a runner, a voice or Telegram -- no door assumes the founder is at a laptop | OWNED | #7388 | -- |
| B7 | Otto answers on the API surface, and an accepted turn can no longer be dropped silently | OWNED | #6986 | -- |

## C. Superpowers -- every iota, with hands

| # | wish | status | where | falsifier |
|---|---|---|---|---|
| C1 | "dig up every single iota of capability even potential not yet built" (2026-09-05) | RECEIPTED (as a census) | `docs/specs/otto-capability-inventory.md` -- the 91 KB inventory: 20+ surfaces, 82 skills, sub-agents, browser, computer use, media gen, delegation | the inventory stops being regenerated -- the wish is a census, not a runtime |
| C2 | "Otto runs every tool without asking. The one exception is an action that cannot be undone" (2026-09-05) | RECEIPTED | ADR 0024 (`docs/decisions/0024-otto-runs-every-tool-and-asks-only-for-the-unundoable.md`); `platform/otto-gateway/deployment.yaml:356` (`OTTO_TOOLSETS`) | the toolset shrinks without a decision, or a reversible action starts asking |
| C3 | "a model-driven shell never runs in the process that holds the bot token, the database password and the GitHub token" | OWNED | #7446 (the secretless sandbox); the standard is `docs/specs/otto-door-hands-and-senses.md:200-203`; the violation is `deployment.yaml:338-356` | the secret-holding container still lists `terminal` or `code_execution` -- this is the conformance gate's R3, and it fails on any new one |
| C4 | one agent, one thread, one audit trail; continuity by principal across surfaces | RECEIPTED | `hermes-v2/otto/ingress/thread.py`, the trust classes, the channel registry | two threads for one principal |
| C5 | one identity layer: OIDC at the gateway, never in an app | RECEIPTED | `platform/otto-gateway/httproute.yaml:25` (oauth2-proxy) + the binding registry | an app takes its own identity |

## D. Truth, proof, enterprise bar

| # | wish | status | where | falsifier |
|---|---|---|---|---|
| D1 | "we need better testing for this as enterprise product" (2026-09-05) | OWNED | #7354 -- the parity tick that measured nothing (every run from `#40715893797` to `#40792186310` concluded `cancelled`) | a tick concludes `cancelled` again |
| D2 | the door stays probed; a probe that grades a lane the door no longer uses is worse than no probe | RECEIPTED | `platform/otto-gateway/router-lanes.yaml` -- one ConfigMap read by the door **and** the probe | a second copy of the lane list appears |
| D3 | "an instrument nobody can trust is not an instrument" (LAW 28) | RECEIPTED | `router-lanes.yaml:22-24` | the lane list drifts from the door's route |
| D4 | the founder must be able to see the work live, on the work surface | OWNED | #7447 -- the doctor's rows reach the work surface; `/fleet` shows claims and gates today | the work surface shows no Otto verdict |
| D5 | a spec, a BDD and an eval harness that proves Otto beats a baseline ("beat Muse") | OWNED | #6921 | -- |

## E. The estate's human-in-the-loop

| # | wish | status | where | falsifier |
|---|---|---|---|---|
| E1 | a stuck agent escalates to the founder on the `otto numum` channel with the blocker named | OWNED | #7388 | -- |
| E2 | a structured decision: Otto asks, the founder answers with a comment, the build continues | RECEIPTED | **landed 2026-10-28** -- PR #7384 -> `1cd65e8b1` on `main`: `sovereign/otto/decision.py`, `bin/founder-decision`, `platform/estate/intents/founder.decision.yaml`, `sovereign/otto/hermes_plugin/__init__.py`, `features/founder-decision/founder-decision.feature`, `tests/test_founder_decision_door.py`, `docs/runbooks/founder-decision-door.md`; the intent is in `catalog/estate-capability-registry.json`. Measured: message id 2056, decision id `dec-306c912e`, expiry fail-closed (`option: null`), the webhook restored | the intent is missing from the registry, or a decision that expired is read as a yes |
| E3 | approvals and applies reachable from anywhere the founder is | OWNED | #7388 | -- |

## F. The estate's law (the constraints the wishes live inside)

| # | law | status | where | falsifier |
|---|---|---|---|---|
| F1 | one of each layer: routing, traces, identity, secrets, scheduling, catalog, execution boundary, evidence, verification, memory (AGENTS.md section 6) | ENFORCED | `bin/otto-conformance-gate` -- R1 (a retired memory plane), R2 (the door's default route), R3 (a shell in a secret-holding container), R4 (a credential literal); it runs in `bin/idp-ci` | a new manifest names a layer the estate owns and the gate stays green -- the baseline may only shrink |
| F2 | the cloud router is the default; the laptop is the fallback; a capability that only works on the laptop is not done (AGENTS.md section 7a, 2026-10-26) | ENFORCED (baseline) + OWNED | R2 of the conformance gate holds today's violation (`deployment.yaml:327`) as debt; #7445 retires it | a new manifest points its default route at a loopback |
| F3 | the founder's own subscription lanes stay local; they are not a pattern to copy (AGENTS.md section 7a) | RECEIPTED | read 2026-10-29 from `three-homes.yaml` and `deployment.yaml`: the three homes are the cluster router, a direct MiniMax line with the door's own vault key, and Groq -- no founder subscription lane appears. **Not yet gated** | an Otto lane calls Claude Code or the `gemini` CLI |
| F4 | never hand-apply; heal through Flux (AGENTS.md section 2) | RECEIPTED | Otto's manifests are a Flux Kustomization: `clusters/oke/platform.yaml:373` -> `./platform/otto-gateway` | a path applies Otto's manifests by hand |

---

## The five contradictions, and who owns each

The spec's section 3.6 lists them; this is the same table with the owner attached.

| # | the architecture today | the founder's later ruling | owner | status |
|---|---|---|---|---|
| 1 | the door's default route is a pod-local lifeboat; the estate router is a rung | cloud router is the default (2026-10-26) | #7445 | OWNED |
| 2 | Otto keeps its own memory planes (`deployment.yaml:269,291`, `memory-store-job.yaml`) | one memory plane (ADR 0036, 2026-10-02) | #6162, #6163, #6165, #6229 -- all four still open, 27 days later | OWNED, stale |
| 3 | `terminal` runs beside the bot token, the DB password and the GitHub token (`deployment.yaml:356`) | a model-driven shell never runs in that process | #7446 | OWNED |
| 4 | a private verification plane (probe, reconciler, parity tick) | one verification layer; the estate has a doctor family | #7354, #7447 | OWNED |
| 5 | the answer path assumes the cluster's router and cluster services (`deployment.yaml:291`) | no door assumes a laptop; the cloud is the default route | #7445, #7448 | OWNED |

## The gaps -- the wishes nothing owns

These are the rows that need a decision, not another document.

1. **B1 -- the showcase.** The founder asked for a page that wows. The seam exists; the page does
   not; nothing owns it. This is the largest unclaimed wish.
2. **B3 -- the missing channels.** Slack, email, QR/camera and portal are named in the spec and
   owned by nothing. Wave 6 of the spec ("one binding and one registry row") is the shape of the
   work; no ticket holds it.
3. **B5 -- the edge voice loop.** ADR 0033 names the target; no ticket, no wave, no owner. It is
   the only wish whose *architecture* has never been started.
4. **Contradiction 2 -- the memory planes.** ADR 0036 is 27 days stale and the four tickets that
   execute it are all open. This is not a new wish; it is a decision that was written and never
   executed, which is the more expensive kind of gap.

## What the map says about the programme's next move

The next move is not a new capability. It is **contradiction 2** (the memory planes, four open
tickets, one 27-day-old ADR) and **#7445** (the router default), because they are the two
things standing between Otto and the estate's own layers -- and because both are bounded by
tickets that already exist.

Wave 4 (one verification plane) is in flight in the same programme: the parity tick is being
made to conclude (#7354), and the doctor's rows are to be its input (#7447).

## The receipts, and where to check them

| what | where | read |
|---|---|---|
| the three homes, in the founder's own words | `platform/otto-gateway/three-homes.yaml:1-47` | 2026-10-29 |
| the founder-decision door, landed | `git show 1cd65e8b1 --stat`; `platform/estate/intents/founder.decision.yaml` | 2026-10-29 |
| the conformance gate, in CI | `bin/otto-conformance-gate`, `bin/idp-ci` | 2026-10-29 |
| the one binding + one registry entry | `hermes-v2/otto/ingress/plugins.py:237-242` | 2026-10-29 |
| Otto's manifests under Flux | `clusters/oke/platform.yaml:373` | 2026-10-29 |
| the four memory tickets still open | #6162, #6163, #6165, #6229 -- GitHub API, `state: open` | 2026-10-29 |

### Read the `RECEIPTED` rows with one caveat (measured 2026-10-30)

The estate's substrate changed under this map after it was written. Measured 2026-10-30T03:20Z
from the laptop; the full receipts are in the epic's addendum
(`docs/epics/2026-10-28-otto-minimum-viable-programme.md`):

- `oci ce cluster list --compartment-id ocid1.compartment.oc1..aaaaaaaaynd3mq5nhnccywzbmwfdevpkmvyzwcsxm7kyevei5s72ikyge5oq --all`
  -> one cluster, `estate`, `lifecycle-state: DELETED`.
- `oci lb load-balancer list --compartment-id ... --all` -> one load balancer, `ACTIVE`, public IP
  `193.123.184.22` -- the edge exists, and nothing answers behind it.
- `curl https://mcp.mumchimp.com/` -> `curl: (35) TLS connect error: error:0A000126:SSL routines::unexpected eof while reading`
  (the same for `https://llm.mumchimp.com/`; `https://api.github.com/` -> `200`, so the laptop's
  internet is not the fault).

So a `RECEIPTED` row whose receipt was a live cluster is **dated**: it was true on the date in
its row, and it cannot be re-run until the substrate is back (#7387, #7393). That is what
`RECEIPTED` means here -- a dated measurement, re-runnable when the estate answers. Rows whose
receipt is a file in the tree, a test, or a GitHub API read are unaffected and re-runnable
today.
