# The founder-agent gate

Spec: [`docs/specs/2026-10-23-founder-agent-gate.md`](../../docs/specs/2026-10-23-founder-agent-gate.md)
(ticket [#6921](https://github.com/chidionyema/idp/issues/6921)). This directory is the harness for
**G1** (task success), **G2** (no silent failure), **G4** (the clock) and **G5** (canaries). G3, G6,
G7, G8, G9 and G10 keep their spec sections; G9's round rule is implemented here (`rounds.json`).

The gate grades today's Otto, unchanged, and publishes a number nobody can argue with: the tasks
that passed, the runs that failed, and the exact reason each one failed.

```bash
python3 eval/founder-agent/run.py --self-test          # can every verifier fail? (no agent needed)
python3 eval/founder-agent/run.py --gates              # G2/G4/G5, proven on their own fixtures
python3 eval/founder-agent/run.py --suite --agent door --allow-door --runs 3
python3 eval/founder-agent/run.py --round 1 --suite --agent door --allow-door   # records a round
```

## What a verifier is allowed to read

One transcript, `schema.Run`: the events the gateway recorded (`tool_call`, `tool_result`,
`notice`, `artifact`, `error`), the fleet lines, the cost. A verifier never reads the agent's sentence
claiming success and never reads a task's own output directory. `verify(run) -> Verdict(ok, reason)`.

Every task ships two transcripts:

* `fixtures/known-good/run.json`  -  a run that did the job. The verifier **must** pass it.
* `fixtures/known-bad/run.json`  -  a plausible run that did not. The verifier **must** fail it.

`--self-test` replays both for every task. A verifier that passes both is caught here, before any
agent runs, and aborts the gate (spec G1: "a verifier that cannot fail is a defect, not a pass").

## The ways this harness refuses to lie

| Rule | Where it is enforced |
|---|---|
| A verifier that cannot tell good from bad aborts the gate | `suite.self_test`, `run.py --self-test` |
| A task the agent could not be asked is a **failure**, never a skip | `DoorAgent` returns `ungradable`; verifiers fail it |
| A suite below the spec's minimum counts cannot certify G1 | `suite.certificate`, `run.py` G1 status |
| A report names the suite sha it ran, and is refused against another | `suite.check_report` |
| Three runs per task; one flaky run is not a pass | `run.run_suite` |
| Green needs 4 of 5 consecutive rounds; 3 consecutive reds report a block | `run.record_round` |
| A probe that bypasses the door is rejected | only `StubAgent` (replay) and the door are adapters |
| A run that never reached the task is named, not scored | `run.run_suite` writes `cause` and `gradable: false` |
| A gate graded on its own proofs says so | `run.py` writes `live_exercised`, and prints the note |
| A suite where nothing was asked is 0.0, never 1.0 | `run.run_suite` counts `runs_never_asked`; `all([])` is True |

## On the founder's surface, live

Founder, 2026-10-23: *"every agent under continuous evaluation and recursive self-improvement; the
founder surface must monitor evals across the estate in real time."* So the round is not a report
read afterwards:

* `run.py` writes `rounds.json` (one row per round: `g1`, `perf`, `pass_rate`, `green`, the latency
  percentiles, the improvement items the next round must close) and, per turn, one line in
  `reports/live.jsonl` through `gate_live.emit`  --  `round.start`, `run.end`, `round.end`.
* `gate_live.publish` pushes the same envelope to the estate bus on
  `estate.agent.founder-agent-eval.<round>.<kind>` when `ESTATE_FOUNDER_EVAL_NATS` names a bus it
  can reach. With no bus it records `feed.not_published` **in the feed, once per reason**: a feed
  that stops on a dead bus is indistinguishable from an idle estate.
* `GET /evals/founder-agent` on FleetView reads the ledger and the feed and renders them on the
  Reactor (`FounderEvalsPanel`), polled every 5s; `GET /evals/founder-agent/stream` is the same
  snapshot as SSE, emitted when either file changes. A ledger that is not in the deployment is a
  **503 naming the path it looked for**  --  never an empty board that reads as green.

Run a round the surface will show:

```bash
python3 eval/founder-agent/run.py --suite --round 1 --agent door --runs 3
# then, from the checkout: bin/serve-fleetview, and /fleet renders the round as it runs
```

## Round 0  -  measured 2026-10-23, red

`reports/round-0.json`, recorded in `rounds.json`. What it measured, per task, three runs each:

* `G1 fail`, pass rate **0.0**  -  and not because Otto answered badly: it could never be asked.
  `gradable: false`: every one of the 36 runs carries `cause: "door refused the turn: HTTP 401"`
  next to the verifier's own reason, so this red cannot be misread as "Otto tried twelve tasks and
  failed twelve".
* `G2 pass`, `G4 pass`, `G5 pass`, with `live_exercised: false`  -  the gates' own proofs hold (six
  faults, twelve clock instants, the canary scans). Their **live** arms were not exercised: with no
  transcript, a fault turn and a clock turn cannot be graded either. Run it with `--live` against
  a door that refuses a turn and the report says so instead of passing quietly (measured: `G2=fail,
  G4=fail, G5=pass`, live rows ungradable).

The single fact underneath: **the door admits no harness turn.**

```
POST https://otto.mumchimp.com/webhook/telegram  -> 401   (Telegram webhook secret required; that
                                                          channel delivers to the founder's phone)
POST https://otto.mumchimp.com/webhook/probe     -> 404
POST https://otto.mumchimp.com/webhook/harness   -> 404
POST https://otto.mumchimp.com/webhook/test      -> 404
GET  https://otto.mumchimp.com/healthz           -> 200   (the door is up: this is not an outage)
```

So today's Otto has a door the founder can use and a gate cannot. That is the first thing round 1
must change, and it is deliberately *not* worked around here: signing the Telegram secret and
posting a synthetic update would deliver test messages to the founder's phone, and calling the
router directly would grade a layer that is already proven working while the agent loop stayed
unmeasured (the mistake `platform/otto-gateway/answer-probe.yaml` documents).

## The starter suite

Twelve tasks, every one of the spec's eight categories represented, each with real known-good and
known-bad transcripts:

| Category | Tasks |
|---|---|
| web read | `gym-offer`, `site-down` |
| form fill | `table-booking`, `duplicate-submit` |
| calendar | `dst-exact`, `calendar-conflict` |
| email | `email-draft-only`, `email-receipt` |
| research | `research-two-sources` |
| file and canary | `card-not-echoed` |
| handoff | `handoff-research` |
| multi-step | `order-then-verify` |

`certificate()` says out loud what is missing (`web-read` 3, `form-fill` 3, `calendar` 2, `email` 2,
`research` 3, `file-canary` 2, `handoff` 2, `multi-step` 1 -> 30 total), and while anything is
missing the report prints `certifies_g1: false` next to the pass rate. The remaining 18 tasks are
the next increment, not a rounding error.

## Adding a task

1. `tasks/<id>/task.yaml`  -  `id`, `category` (one of the eight), `surface`, `prompt`, budgets.
2. `tasks/<id>/verify.py`  -  `def verify(run) -> Verdict`, reading only the transcript.
3. `tasks/<id>/fixtures/known-good/run.json` and `known-bad/run.json`  -  one run each.
4. `python3 eval/founder-agent/run.py --self-test` must stay green.

A task whose id, prompt or fixture text appears in the agent's prompt, skills or memory is a leak:
`suite.leak_check` scans for it (`tests/test_founder_agent_gate.py` holds the contract).

## Cost

Round 0 cost nothing: no model was called (the door refused before it routed). A full round of the
30-task suite at 3 runs is ~90 turns; G10's per-task cap (40 cents, 40 steps) is carried per task in
`task.yaml` and the report sums what was actually spent, not an estimate.
