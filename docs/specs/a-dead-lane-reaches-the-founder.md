# A grader whose failure cannot leave the runner is not a gate

Founder, 2026-09-10, verbatim: *"THE POINT IS THE SYSTEM DOES ALL THAT … WE HAVE MULTIPLE
FALLBACK, NEEDS TO BE SEAMLESS."* and then *"lets address in one swoop and clamp down so it never
happens again."*

That is the requirement, and it is not about fallbacks. The estate has multiple fallbacks and
multiple graders. The defect is that **a grader can fail and nobody finds out**, and it is a
class, not a lane.

## The measurement, 2026-09-10

Google retired the embedding model the router's `embed` lane named. Two services died:

- `otto-memory-store-6`: `Error`, 20 hours, log ending at `otto/memory/backfill.py:102` with
  `urllib.error.URLError: <urlopen error timed out>`.
- `hindsight-api`: **168 restarts in 18 hours**, each container dying at 329s of a 600s startup
  budget with two 120s router timeouts inside it.

`bin/idp-router-lanes` measures every lane and grades each one `ok` / `FAIL` / `UNKNOWN`. It had
every fact on the first failure. Nobody was told, because:

**1. The probe always reports success.** `bin/idp-router-lanes:145` — `return 0`, whatever it
found. Every lane could be dead and it exits green.

**2. The workflow cannot see a non-zero exit anyway.** `.github/workflows/estate-state.yml:163` —
`set -uo pipefail`, no `-e`.

## The class, censused

Two halves make a dead grader: the command's exit code is produced and then discarded. Three
mechanisms discard it, verified in bash on this machine:

```
$ false | tee /dev/null >/dev/null; echo $?
0                      # pipe without pipefail: the LAST command's status wins
$ set -o pipefail; false | tee /dev/null >/dev/null; echo $?
1
```

A sweep of every workflow step that runs a `bin/idp-*` grader found **13 steps whose verdict
cannot fail the run**:

| workflow | step | why |
|---|---|---|
| `conscience.yml` | `bin/idp-conscience` | `set -uo pipefail`, no `-e` |
| `estate-bootstrap-preflight.yml` | `run the gate` | verdict piped away |
| `estate-escrow.yml` | `bin/idp-escrow` | `set -o pipefail`, no `-e` |
| `estate-inventory.yml` | `bin/idp-inventory` | `set -uo pipefail`, no `-e` |
| `estate-state.yml` | `bin/idp-router-lanes` | `set -uo pipefail`, no `-e` |
| `oke-check.yml` | `bin/idp-fits-a-node` | no `-e`, `\|\| true` |
| `oke-check.yml` | `bin/idp-agent-workforce-drill` | no `-e`, `\|\| true` |
| `portability-drill.yml` | `grade against the floor` | `\|\| true` |
| `portability-drill.yml` | `grade against the floor … wall-clock and cost` | `\|\| true` |
| `ticket-verification.yml` | `bin/idp-ticket-verify as the prover App` | `set -o pipefail`, no `-e` |
| `verdict-backstage.yml` | `bin/idp-prove backstage` | `set -o pipefail`, no `-e` |
| `verdict-langfuse.yml` | `bin/idp-prove langfuse` | `set -o pipefail`, no `-e` |
| `verdict-signoz.yml` | `bin/idp-prove signoz` | `set -o pipefail`, no `-e` |

**Not every one is a defect.** `|| true` on an optional leg is documented estate behaviour (a
leg that is allowed to be absent), and `probe-mutations`/`catalog-render` pipe for a reason. The
defect is narrower and it is this:

> A step whose **purpose is to grade** — its command is a grader — and whose exit code is
> **discarded**, is not a gate. It is a log line.

That is LAW 28 (an instrument nobody reads), and it is the same shape as
`bin/idp-pipeverdict`'s rung, which already exists for scripts that take a verdict from a pipe in
shell.

## The fix, and it is a guard rather than thirteen patches

The estate's rule is that a law without a protocol is a wish (LAW 44) and a mistake ends as a
guard no session can walk past (LAW 45). So:

### Part A — the guard, and it covers the class

New `bin/idp-grader-exit-gate`: parses every `.github/workflows/*.yml`, finds each step whose
`run` invokes a grader (`bin/idp-prove`, `bin/idp-root-trust`, `bin/idp-conscience`,
`bin/idp-escrow`, `bin/idp-inventory`, `bin/idp-router-lanes`, `bin/idp-fits-a-node`,
`bin/idp-ticket-verify`, `bin/idp-agent-workforce-drill`, `bin/idp-mechanism-gate`,
`bin/idp-rule-coverage`, `bin/idp-one-scheduler`, `bin/idp-drill-heartbeat`,
`bin/idp-portability-drill`), and **fails** when that step cannot propagate a non-zero exit —
meaning the step has no `-e`, or pipes the grader without `pipefail`, or ends it in `|| true`
without an `# optional:` marker.

An escape hatch exists and is explicit: a step carrying the comment
`# optional: <reason>` is allowed to swallow its exit, because "this leg is genuinely allowed to
be absent" is a real and different statement from "I forgot". The marker is the same shape as
`bin/idp-portal-buttons`'s NOT-generated sentinel: a literal string, so a weakened rule cannot
silently un-flag it.

Fixture pair, both ways, under `tests/fixtures/grader-exit/`:
- `bad/` — a workflow piping a grader's verdict with no `pipefail`
- `good/` — the same step with `pipefail`, and one `# optional:` step that legitimately swallows

### Part B — the thirteen, made honest

Each of the seven `set -o pipefail`-without-`-e` grading steps gains `-e`, or the grader's exit is
captured and re-raised with the reason. The `|| true` steps either gain an `# optional:` marker
naming why the leg may be absent, or the `|| true` comes off.

### Part C — the probe tells the truth about itself

`bin/idp-router-lanes` exits non-zero when any lane is `FAIL`. `UNKNOWN` stays exit 0: a probe
that could not run is not a lane that is down (LAW 21 already distinguishes those). `--quiet`
keeps the report-only behaviour for callers that legitimately want a document.

### Part D — a dead lane reaches the founder

New `RouterLaneDown` in `platform/monitoring/rules/estate.yaml`, beside `GatewayRefusals`, which
is the established shape for "a refusal is an incident, not a log line in SigNoz" (crew#498):
severity `warning`, `owner: idp`, the lane name and the vendor's own words in the annotation,
routed through the **existing** Alertmanager → Telegram receiver. No second notification path.

## Out of scope

- No new probe. `bin/idp-router-lanes` is the measurement; this makes its verdict travel.
- No change to `|| true` where a leg is genuinely optional — the marker is how that is said.

## Acceptance

```
python3 bin/idp-grader-exit-gate                    # exit 0 on the tree
python3 bin/idp-grader-exit-gate tests/fixtures/grader-exit/bad   # exit 1, names the step
python3 bin/idp-grader-exit-gate tests/fixtures/grader-exit/good  # exit 0
python3 -m pytest tests/test_router_lanes_reports_failure.py tests/test_router_lane_alert_exists.py -q
```

Then the end-to-end, which is the only proof that counts (THE EMPIRICAL PROOF RULE): with a lane
pointed at a dead model, the scheduled run goes **red** and a Telegram message arrives naming the
lane; when the lane is restored, the alert clears. Until that message is quoted, this is not
working.

---

# Layers 1 and 3, measured after the census

The census above found the exit-code class. Three more layers were checked against the estate
rather than assumed, and two of them are missing. Both belong in this sweep.

## Layer 1 — the runner's own shell, which nobody chose

GitHub Actions' default shell for a `run:` step is `bash -e {0}` **without** `pipefail` [1.1.1].
So every one of the 13 steps found in the census was already running under `-e`, and the exit was
still lost — because a pipe's status is the *last* command's without `pipefail`.

Measured in this estate:

```
$ grep -rn "shell:\|defaults:" .github/workflows/*.yml | head -8
demo-sandbox.yml:147:        shell: bash
```

One workflow names a shell, and it names plain `bash`. Nothing declares
`bash --noprofile --norc -euo pipefail {0}` anywhere, which is the elite CI standard precisely
because it removes the author's discretion [1.2.1].

**So Part F of this sweep:** a workflow-level `defaults.run.shell` of
`bash --noprofile --norc -euo pipefail {0}` on every workflow that runs an estate grader. That is
the clamp that makes Part A's gate the second line of defence rather than the only one — the gate
catches an author who writes a pipe, and the shell catches it even if the gate is bypassed.

`bin/idp-grader-exit-gate` extends to refuse a workflow that runs a grader while declaring a
weaker shell, so the two cannot drift apart.

## Layer 3 — a fallback that engages silently is an invisibility cloak

The founder's requirement is seamless failover. Seamless **to the person using it** does not mean
invisible **to the estate**. Today a lane falling over produces no event anywhere:

```
$ grep -rn "fallback\|Fallback" platform/monitoring/ --include="*.yaml"
(no matches)
```

No rule, no alert, no counter. The router logged `No fallback model group found for original
model_group=embed` and 26 rate-limit lines in its last 100 lines, and none of it was an event.

That is the exact mechanism that let this run 20 hours: the fallback is what *removes the symptom*,
so the only signal was the symptom, and the fallback deleted it.

**So Part G of this sweep:** `RouterFallbackEngaged` in `platform/monitoring/rules/estate.yaml`,
beside `GatewayRefusals`. It fires when the router serves a request from a fallback rather than
the primary, at `severity: warning`, `owner: idp`, routed through the existing Alertmanager →
Telegram receiver.

**The data source, measured rather than assumed.** The router exposes no Prometheus metrics to
this estate: `platform/llm/litellm.yaml` declares only `containerPort: 4000` with no metrics
listener, and `kubectl get servicemonitor -A` lists twelve monitors and **none for litellm**. So a
rule written against a `litellm_*` counter would match nothing forever, which is a wish wearing a
rule's clothes (LAW 44).

The honest source is the one that already exists and is already measured: **`bin/idp-router-lanes`
probes every lane on a schedule and grades each `ok` / `FAIL` / `UNKNOWN`.** A lane that is `FAIL`
is a fallback that has engaged. Part D makes that verdict fail the run; this makes it an alert.

So Part G is delivered as two things that cannot drift apart:

1. `bin/idp-router-lanes` writes its verdict as a **Prometheus textfile** at a path given by
   `--textfile <path>` (the `node_exporter` textfile-collector convention), one gauge per lane:
   `estate_router_lane_up{lane="embed"} 0`. This is a file the estate controls, needs no new
   scrape target, and is proved by running the probe and reading the metric back.
2. `RouterFallbackEngaged` reads that gauge: a primary lane at 0 while a fallback lane is up is a
   fallback carrying production, which is exactly the event nobody was told about.

If the textfile collector is not present in this cluster's node-exporter, then this Part ships as
**the name of the gap and nothing else** — no `expr`, no rule — because a rule with no data source
is worse than a rule that is absent: it makes the estate look covered when it is not. The Builder
must measure which of these two is true and say which in the PR body.

## Layer 4 — the Watchdog, and it is already real

Correcting the assumption this sweep started from: the estate **has** the dead man's switch, and
it is further along than expected.

- `kps-general.rules` carries `Watchdog` with `expr: vector(1)` and no `for`. It fires forever [1.3.1].
- `platform/monitoring/alertmanager-config.yaml` routes `alertname = "Watchdog"` to the `null`
  receiver **on purpose** — it is meant to fire always, so it must never be a message.
- `bin/idp-cluster-state:109-116` grades the receipt: `alert_watchdog == 0` is `FAIL` with its own
  ticket, not `UNKNOWN`.
- `.github/workflows/oke-check.yml` runs `bin/idp-cluster-state --json` on a daily cron.

So the heartbeat fires, the absence is graded, and the grade runs on a clock. **What is missing is
the snitch**: the grade reaches a CI log, and if the whole pipeline hangs there is no external
service that pages on the *silence* [1.4.1]. That is the one real gap in Layer 4, and it is a
follow-up, not part of this sweep — it needs a third-party endpoint, which is a founder decision
and a credential the estate does not hold.
