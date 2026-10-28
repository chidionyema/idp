# One doctor door for every Telegram agent

- **Date:** 2026-10-28
- **Claim:** idp#7347 · agent `pi`
- **Gate:** `bin/idp-ci`; the doctor's own contract is pinned by `tests/test_telegram_agent_doctor.py`
- **Spec:** `docs/specs/2026-10-28-the-telegram-agent-doctor.md`

## Context

The founder's standing requirement (2026-10-28): *"it needs to be seamless for any agent to
monitor live, diagnose and resolve any issues with any telegram agent/otto."*

The estate already has the pieces and not the door. Measured 2026-10-28 in this repository:

- `platform/otto-gateway/OWNER.yaml` declares **one** Telegram bot owner: `otto-gateway` in
  namespace `otto-gateway`. The `otto-registration-reconciler` is the only writer of the
  webhook. `jit-broker` (namespace `jit`) receives mirrored copies and must never touch the
  Bot API. `otto-golden` serves `GET /healthz`. `hermes-agent`'s Telegram token is removed, so it
  is not a Telegram agent.
- The probes exist and run: the registration reconciler every 5 minutes, the answer probe every
  15 minutes, the founder-surfaces probe against `https://otto.${ESTATE_ZONE}/healthz`.
- The estate's doors are each narrow: `voice-doctor` (voice), `router-doctor` (the laptop
  router), `k8s-diag` (the cluster), `silence-audit` (alert coverage), `flux-doctor` (Flux).
- **Nothing joins them for a Telegram agent.** An agent that is told "Otto is not answering" has
  to re-derive, from scratch, which of four links broke — using whichever door it guesses.

Two failures of this class are already in the estate's record, and both are the same defect:

1. The **edge** was probed (a 200) while the **webhook** was stale. The door was "up" and
   Telegram was delivering to nobody.
2. A **200 on the answer path** was treated as an answer. The door answered and said nothing.

Both are the same mistake: probing a surface instead of proving the outcome.

And from today, 2026-10-28, the estate's own health surfaces are dark from this laptop: the
cluster did not answer (`kubectl` hit the 100 s door ceiling), the memory door refused the
connection (`URLError: EOF occurred in violation of protocol`), and the executor refused every
job with `the volume has 594 MB free, under this door's 1500 MB floor`. A doctor that cannot
tell "broken" from "cannot see" would have reported three failures that do not exist.

## Decisions

**D1. One doctor, generalized — not a doctor per agent.**
`telegram-agent.doctor` walks a **chain** per agent and names the **first broken link** with
the fix that repairs it, the shape `voice-doctor` already uses. A second doctor for the next
agent would be a second layer of the same thing; the next agent is a **registry entry**, not a
new door.

**D2. The registry is the one place that says what healthy means.**
The chain per agent (edge → workload → registration → answer) and the fix per link live in one
place, `platform/estate/libexec/telegram-agent-doctor.py`. Nothing else has to know what
"healthy Telegram agent" means, and the registry cannot silently drift: the test asserts every
declared fix is a real intent and every declared source manifest is a real file.

**D3. BLIND is a first-class state. An unreadable source is not a failure and not a pass.**
Exit **3** for blind, **1** for broken, **0** for healthy. A blind link is never healed —
repairing what you cannot read is a blind action, and the doctor says so instead of guessing.
This is the estate's oldest rule (`a skipped leg is not a failed leg`, 2026-09-04) applied to
health.

**D4. The walk stops at a FAIL, not at a BLIND.**
A broken chain cannot be judged past the break. But a blind link may be followed by a broken
one, and the broken one is the actionable fact. Blindness short-circuits the *cluster* links
only (the cluster is one source, so it is blind once), never the walk as a whole.

**D5. Heal only through the intent layer.**
The declared fix is `flux-reconcile` — the reconciler that owns the row repairs it, and the
repair is recorded with a receipt. There is no `kubectl apply` in this door, and there never
will be. A doctor that heals by hand is a hand-apply with a nicer name.

**D6. No new store, no new UI.**
Health lives where health lives: the edge, the cluster, the job status. The doctor holds no
state. `/fleet` will show this verdict later, reusing it — the estate's work surface is the
place a founder watches, not a new page.

**D7. The door is agent-facing first.**
`estate-invoke telegram-agent.doctor` is the whole interface: `agent=<id>` to narrow, `heal=true`
to repair, `json=true` to consume. No browser, no founder present, no new MCP tool — the intent
layer already is the agent interface.

**D8. The scheduled plane is READ, not duplicated.**
Measured 2026-10-28: `.github/workflows/otto-parity.yml` already runs every fifteen minutes,
mints a kubeconfig through OCI's OIDC, grades both Ottos and the layers under them, and alerts
the founder on Telegram when a tick turns red. That is the scheduler and the alerter, and it
stays. The doctor **reads** that verdict — one `gh api` call, the last run's conclusion — and
reports it next to its own chain, so there is one set of rows and two planes: the scheduled one
and the callable one. The scheduled verdict is **context, not a link**: that tick grades the
layers under the Ottos too, so a red tick is not proof about a Telegram agent and never becomes
one agent's "first broken link". The merge direction is fixed: the parity playbook asks this
doctor for the Telegram rows (Wave 1 of the programme) rather than keeping its own.

**D9. The doctor's exit code is a FINDING; the door's exit code is the ANSWER.**
The script keeps the four-state contract (0 healthy / 1 broken / 2 registry unreadable / 3
blind): that is what another agent consumes. The intent does not propagate it — the intent
exits 0 whenever the door answered, and prints the verdict as its last line. Measured reason,
not taste: the estate's policy refuses a verb whose 30-day not-ok probability reaches 0.8
(`platform/estate/bin/estate-execute`, `policy_decide`), and a doctor's non-zero exit means
"a Telegram agent is broken" or "the estate is dark" — the states the door exists to report.
With the estate already dark from this laptop, the shadow policy said on 2026-10-28:
`would refuse telegram-agent.doctor -- 5/5 runs not ok in 30d, p_fail=0.86`. A door that
dies exactly when the estate is broken does not serve the founder's requirement. The general
fix stays with the executor, which already knows this defect: its per-intent
`exit_is_finding` flag (`docs/specs/2026-09-29-machine-learning-dept.md` §6a) is where a
diagnostic verb's non-zero exit is labelled a finding estate-wide — for `voice-doctor`,
`router-doctor` and the rest. Until that flag exists, the translation lives in the intent,
where it is readable and removable in one place. The one exit that is a real failure of the
door is the doctor not running at all.

## Consequences

- **Cost:** one more door in the intent set, and a small script in `platform/estate/libexec/`.
  Both land in `bin/estate-runtime-sync`'s staged directories, so the door exists on the next
  runtime sync without a release.
- **What this makes harder:** the doctor is a new thing that can be wrong. It is pinned by tests
  that drive the walk with a fake probe — no cluster, no network, no executor — so the contract
  is falsifiable without the estate being up. The intent's own exit semantics are pinned the
  same way: the step is run against a stubbed interpreter, so "the door answers even when the
  estate is broken" and "the door fails when the doctor cannot run" are measured, not assumed.
- **What it does not fix:** the cluster being dark, the memory door being down, and a laptop
  under its disk floor are three separate estate incidents. The doctor reports them honestly as
  blind; it does not repair a cluster from a laptop. A scheduled run of this door on a machine
  that can reach the cluster is the next wave, and it is where "monitor live" becomes a fact
  rather than a capability.
- **What this deliberately leaves alone:** the reconciler and the answer probe keep their jobs and
  their receipts, and the parity tick keeps its schedule and its Telegram alert. If this door
  ever duplicates them, it is wrong and the duplication is the defect to remove.
