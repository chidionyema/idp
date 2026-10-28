# The Telegram agent doctor: one door any agent can call

**Date:** 2026-10-28 · **Claim:** idp#7347 · agent `pi`
**Door:** `estate-invoke telegram-agent.doctor` (`platform/estate/intents/telegram-agent.doctor.yaml`)

## The founder's requirement, in one sentence

> "it needs to be seamless for any agent to monitor live, diagnose and resolve any issues with
> any telegram agent/otto" — 2026-10-28

Three verbs: **monitor live**, **diagnose**, **resolve**. A door that only diagnoses is half of
it; a door that only monitors is a dashboard. This spec is for the door that does all three and
can be called by any agent, without a browser and without a founder.

## What exists today, and why it does not answer the question

Measured 2026-10-28 in this repository:

| door | what it answers | what it cannot answer |
|---|---|---|
| `founder-surfaces-probe` | is `https://otto.${ESTATE_ZONE}/healthz` up? | which of the four links behind that 200 is broken |
| `otto-registration-reconciler` (CronJob, 5 min) | does the Telegram vendor point its webhook at us? | is the door answering, or only receiving? |
| `otto-answer-probe` (CronJob, 15 min) | did a real question come back a real answer? | is the failure in the webhook, the deployment, or the lane? |
| `voice-doctor` | is the voice chain whole? | anything about Telegram |
| `router-doctor` | is the laptop router healthy? | anything about Telegram |
| `k8s-diag` | what does the cluster say? | whether Telegram works |
| `silence-audit` | does every workload have an alert? | what is broken right now |

Every one of them is a probe of a **surface**. None of them answers the question an agent has
at 02:00: *"is the Telegram agent healthy right now, which link broke, and what do I run?"*
The estate already owns the shape of the answer — `voice-doctor` walks a chain and names the
first broken link with the action that fixes it. It is simply not built for the Telegram agent.

**There is no single door for the Telegram agents today.** That is the gap this closes. Not a
second copy of the reconciler or the answer probe: both keep their jobs, both keep their
receipts; this door reads their truth and adds the one thing neither has — a single answer, and
the first broken link.

## The chain

A message meets a Telegram agent through four links, in this order. The registry in
`platform/estate/libexec/telegram-agent-doctor.py` is the **one** place that says what healthy
means for a Telegram agent.

| link | what it proves | how it is read | the failure it exists for |
|---|---|---|---|
| `edge` | the public door answers | HTTPS `GET /healthz` | the edge is down or the hostname moved |
| `workload` | the deployment the bot answers from is ready | the cluster, via the read-only `kubectl` intent | the pod is not ready, or was never deployed |
| `registration` | the vendor's webhook points at us | the reconciler's last run | the webhook is stale, so Telegram delivers to nobody |
| `answer` | a real completion comes back | the answer probe's last run | the door answers 200 and says nothing |

**The edge link proves the edge, not the door.** On `otto.${ESTATE_ZONE}` the `/healthz` path is
answered by `otto-golden`; `otto-gateway` has no public health path by design. The doctor says
so in the link's own description rather than pretending otherwise.

**The `answer` link is the one that matters most and the one the estate had the least of.** A
Telegram agent that receives a message and never answers is indistinguishable from a healthy
one if you only probe the edge. `otto-answer-probe` asks the real lanes and writes its result
into the job's own status; the doctor reads that status.

## Three states, and the one that is easy to get wrong

- `ok` — the link answered and the answer was good.
- `FAIL` — the link answered and the answer was bad. The first `FAIL` in a chain is the
  **first broken link**: the chain stopped being meaningful there, so the links after it are
  not read (a door that broke at the edge cannot be judged at the answer).
- `BLIND` — the link **could not be read**. The cluster is dark, kubectl timed out, the
  executor is missing. This is neither a failure nor a pass.

`BLIND` is the state most likely to be got wrong, and getting it wrong is the estate's oldest
error: an unreadable source is not zero. A doctor that reports "the answer link failed" when it
merely could not look would send every agent chasing a failure that does not exist. So:

- The doctor SCRIPT exits **3** for blind, **1** for broken, **0** for healthy. The INTENT
  that fronts it does not propagate that code — see *Two exits* below.
- A blind link does **not** stop the walk: a later link may still be broken, and that is the
  more actionable fact. The walk stops only at a `FAIL`.
- A blind link is **not** healed: repairing what you cannot read is a blind action. The doctor
  says so instead of guessing.

## The heal

`--heal` applies the fix the broken link **declares**, through the estate's intent layer, and
re-reads the link afterwards. The fix is always `flux-reconcile` (kind `kustomization`, the row
that owns the drifted object), because a hand-applied change is forbidden: the reconciler that
owns the row repairs it, and the repair is recorded. There is no `kubectl apply` anywhere in
this doctor, and there never will be.

The heal returns a **receipt** — the intent's ticket id — so the repair is a fact someone can
point at, not a sentence.

## The scheduled plane, read and not duplicated

The estate already runs a scheduled verdict for Otto: `.github/workflows/otto-parity.yml`, every
fifteen minutes. It mints a kubeconfig through OCI's OIDC, grades both Ottos and the layers
under them (Flux rows, router, bus, memory, the door, Telegram's own webhook verdict, the
in-cluster answer probe), and **alerts the founder on Telegram** when a tick turns red or
green again.

That is the scheduler and the alerter, and it is good work. The doctor does **not** grade the
same thing a second time: it **reads** that verdict and puts it next to its own chain, so
there is one set of rows and two planes — the scheduled one (parity, which alerts) and the
callable one (this doctor, which an agent can ask and which can heal).

The scheduled verdict is **context, not a link**. A red tick is not proof about a Telegram
agent, because that tick grades the layers under the Ottos too; so a red tick never becomes
some agent's "first broken link". It is reported, with its workflow, next to the chain.

The merge this implies is in the programme (Wave 1): the parity playbook should ask this
doctor for the Telegram rows rather than keeping its own.

## The contract

```
$ estate-invoke telegram-agent.doctor
telegram-agent-doctor  2026-10-28T19:41:07Z  zone=mumchimp.com

otto-gateway  Otto's Telegram door (the estate's one bot, @Ottototbot)
  ok    edge         200 in 0.21s  https://otto.mumchimp.com/healthz
  ok    workload     1/1 ready  deployment/otto-gateway
  FAIL  registration the last run of otto-registration-reconciler-283794x failed (1 failed, 0 succeeded)
  FIRST BROKEN LINK: registration -- the vendor's truth: the reconciler is the only writer of the webhook
  FIX: flux-reconcile  kind=kustomization name=otto-gateway namespace=flux-system
```

Every agent in the estate is in that output, whether it is healthy or not. `agent=<id>` narrows
it; `json=true` gives the same facts as JSON for another agent to consume.

## Two exits: the finding and the answer

There are two exit codes in this door, and they answer two different questions.

**The doctor's script exits on what it found.** `0` healthy, `1` a link is broken, `2` the
registry of agents could not be read, `3` blind. That is the machine contract another agent
consumes, and it is a *finding*.

**The intent exits on whether the door answered.** `0` whenever the doctor answered — healthy,
broken or blind — and the doctor's own exit code only when the doctor itself could not run. The
verdict is the last line of the output (`verdict: OK -- ...`, `verdict: FAIL -- ...`,
`verdict: BLIND -- ...`); with `json=true`, stdout stays a pure JSON document and the verdict
line goes to stderr.

The reason is measured, not stylistic. The estate's policy reads an intent's own 30-day
not-ok rate and **refuses** a verb whose failure probability reaches 0.8
(`platform/estate/bin/estate-execute`, `policy_decide`). A doctor's non-zero exit means "a
Telegram agent is broken" or "the estate is dark" — exactly the states the door exists to
report — so a door that exited on its verdict would be refused precisely when it is needed.
Measured on 2026-10-28, with the estate already dark from this laptop, the shadow policy said:

```
[estate] policy shadow: would refuse telegram-agent.doctor -- 5/5 runs not ok in 30d, p_fail=0.86
```

A door that dies when the estate is broken does not serve the founder's requirement. The
general fix belongs to the executor, which already knows the defect: its per-intent
`exit_is_finding` flag (`docs/specs/2026-09-29-machine-learning-dept.md` §6a) is where a
diagnostic verb's non-zero exit is labelled a finding, estate-wide, for `voice-doctor`,
`router-doctor` and the rest. Until that flag exists, the translation lives in the intent,
where it can be read and removed in one place.

The one case where the intent does fail is the one case that is a failure of the door: the
doctor could not be run at all (no interpreter, no script, a crash). Then the exit code is the
doctor's own, and it says so on stderr.

## What this door is not

- **Not a second probe.** The reconciler still owns the webhook. The answer probe still asks the
  real lanes. This door reads their receipts.
- **Not a new store.** Health lives where health lives (the cluster, the job status, the edge).
  The doctor holds no state of its own.
- **Not a new UI.** The estate's work surface is `/fleet`; surfacing the doctor's verdict there
  is a later wave, and it reuses this verdict rather than inventing a second one.
- **Not a hand-apply.** Every action it takes is an intent.

## The proof

`tests/test_telegram_agent_doctor.py` pins the four things that make this a door and not a
sentence:

1. the first broken link is named, and the links after it are not read;
2. an unreadable source is `BLIND`, never `FAIL` and never `ok`;
3. a blind link does not hide a broken link later in the chain;
4. the heal runs the **declared** intent with the **declared** args, and re-reads the link.

Plus: every fix in the registry names an intent that exists in `platform/estate/intents/`, and
every agent's source manifest is a file that exists — a registry that names a door nobody can
run is a registry that lies.

## The agents it covers, and the one it declares out

| agent | what it is | links |
|---|---|---|
| `otto-gateway` | the estate's one Telegram bot, `@Ottototbot` (`platform/otto-gateway/OWNER.yaml`) | edge, workload, registration, answer |
| `otto-golden` | the staging bot, `@numun_bot` — answers `/healthz` only | edge, workload |
| `jit-broker` | reads a mirrored copy of every inbound POST; must never touch the Bot API | workload |

`hermes-agent` is **declared out**, with the declaration that says why: its Telegram token is
removed (`platform/otto-gateway/OWNER.yaml`), so it is not a Telegram agent — the gateway runs
the same image. The door prints that, so "what about hermes-agent?" has one answer in one
place, and adding a Telegram agent later is one registry entry, not a new doctor.
