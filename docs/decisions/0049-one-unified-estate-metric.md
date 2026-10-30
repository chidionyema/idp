# 0049. One unified estate metric: the critical-function registry, its probes, its judge, and the fleet queue

- Status: DECIDED 2026-10-30. Founder: "we need to get a metric unified across the board ...
  we need to be able to measure it ... ambiently ... evaluated and judged ... and it has to
  prioritise founder concerns ... and move idle agents to the highest value work for the
  estate"; "we need to know this when our underlying assumptions break"; "we dont have to
  degrade the services".
- Date: 2026-10-30
- Deciders: founder (direction), estate-agent (implementation)
- Amends: [0044](0044-machine-first-agent-action.md) (the decider must be
  named; this names the metric the decider reads), the critical-function spine
  (`platform/estate/libexec/critical-watch.py`, built 2026-10-28)
- Related: [the founder's judgement as fleet training material](../training/2026-10-30-founder-judgement.md)

## The problem

The estate had a critical-function spine that watched three functions and nothing else. On
2026-10-30, all three were green while three of the founder's own stressed surfaces were not
watched at all, and two of them were down:

| what | watched before? | state, measured 2026-10-30 |
|---|---|---|
| disk-guardian | yes | green -- 2261MB free (goal 1500MB), the guardian alive and reclaiming |
| executor | yes | green -- `~/.estate/executor.sock` accepts a connection |
| estate-bus | yes | green -- 127.0.0.1:4222 accepts a connection |
| **memory-plane** | **no** | **DOWN** -- TCP 443 to `mcp.mumchimp.com` opens, the TLS handshake dies (`TLSv1.3 (OUT), TLS alert, decode error (562)`; `unexpected eof while reading`); the estate's own client says `memory door unreachable: URLError: EOF occurred in violation of protocol` |
| **the default route (`llm.mumchimp.com`)** | **no** | **DOWN from the laptop** -- the same TLS failure (`curl` exit 35, 0.09 s). The laptop fallback answers `/v1/models` in 0.07 s, so the estate was flying on its fallback while the founder's default route was dead |
| **router-lanes** | **no** | **DEGRADED** -- the running router does not serve 4 declared lanes (`cerebras`, `glm`, `nvidia`, `sambanova`); each declares `api_key: os.environ/<KEY>` and those variables are unset in the running router's environment, so the model is dropped at load |
| **spend-bound** | **no** | green -- every chain ends in a free lane, a zero-cost floor exists, the ceiling is set |
| **estate-substrate** | **no** | **RED** -- the cluster-state receipt is 4160 min old (max 60): the last receipt (2026-10-27T11:00:45Z) recorded `nodes=2 ready=2 pods=320 pods_not_ready=18 flux=364 flux_not_ready=21` |

Three facts make this a structural defect, not a missing entry:

1. **The elephant is the gap.** The founder's continuously stressed capabilities were the
   unmonitored ones, and the spine's three were the easy three.
2. **There was no metric.** Three verdicts in three places cannot be summed, ranked or judged.
   Nobody could say "how is the estate", and nobody could point an idle agent at the highest
   value work because there was no ordering to point it at.
3. **Alive is not healthy.** The disk guardian was alive and ticking and freed -2 MB on its
   last step. A watcher that measures a process instead of the job it exists to do is a
   heartbeat for nothing.

## Decision

### 1. The registry is data, and the spine is the only detector

`catalog/critical-functions.json` lists the functions the estate cannot work without. The
spine (`platform/estate/libexec/critical-watch.py`, already scheduled at a 60-second
cadence) is the one implementation that reads it: liveness through the function's own door,
and a GOAL where one exists -- alive but not doing its job is FAILING, because that is the
failure the disk watcher was. Adding a function is a file edit; there is no second watcher
and no second detector.

### 2. Registry order is priority order; the weight is how the metric counts

The spine walks the registry in order, raises the incident of the first failing function
first, and wakes the agent for it first. So the founder's own surfaces sit at the top:
**memory-plane, router-lanes, spend-bound, estate-substrate**, then the three that were
already watched. In the one metric, founder-critical entries carry **weight 2** and the rest
carry 1, so a founder surface failing moves the number twice as far as a satellite service
failing.

### 3. One metric: `estate_health`

```
estate_health = 100 x (weighted share of registry entries that PASS)
```

Read off the spine's own verdicts, never re-implemented:

```bash
python3 platform/estate/libexec/critical-probe.py estate-health
```

It prints the number, the founder-critical sub-score, and the **queue**: the failing entries
in registry order -- the estate's highest-value work, founder-first. It writes
`$ESTATE_STATE_DIR/heartbeats/estate-health.json` (default `~/.estate/heartbeats/`). The
spine's own heartbeat stays the lightweight 60-second cadence record; the metric is the
readout over it.

### 4. The metric is judged, and the judge can fail

`tests/test_critical_functions_registry.py` is the judge, and `bin/idp-ci` runs it as a scoped
rung (`8g critical-registry`). It refuses a registry that:

- names a liveness or goal type the spine cannot measure (BLIND is not a pass);
- has an entry with no structured remedy (runner, repo, budget, task) -- a failure must always
  have a next action;
- puts a founder-critical entry below a non-founder one, or gives it weight 1;
- omits a function the estate cannot work without;
- declares a probe type the spine does not know.

Every rule is checked against a fixture that breaks it, so the judge is proven able to fail.

### 5. Each probe measures through the thing's own door, and cannot pass by being blind

`platform/estate/libexec/critical-probe.py` holds the probes for the functions whose health
cannot be read off a socket or a heartbeat file: the memory plane (through
`platform/estate/memory/door.py`, requiring `brief`, `recall` and `remember` -- a door that
answers without them is DEGRADED, and degraded is red), the router's lanes (the running
router's own `/v1/models`, against the lanes the estate declares), the cost bound (a hard
ceiling, a zero-cost floor, and no chain that terminates in a paid lane), and the substrate
(the cluster's own state receipt, with the exact line it printed). A probe that cannot
measure exits non-zero: an unmeasurable probe is not a passing probe.

### 6. The queue is the fleet's work order

The spine already raises a structured incident for a failing function, alerts, and invokes an
agent with the incident attached. Because the registry order is the priority order, the head
of the metric's queue is where an idle agent belongs: the first failing entry is the first
incident and the first agent the estate wakes. The metric and the queue are therefore the
same thing, not two features.

### 7. Assumptions are measured too

The registry carries assumptions as well as functions. Today: **runtime-tree-on-main** -- the
estate runs its own code from the runtime tree, and when that tree is not main the estate is
running code nobody landed and every proof it produces is about the wrong binary. The founder:
"we need to know this when our underlying assumptions break".

## Consequences

- **The spine's tick costs about 8.5 s more** (the four command probes measured at 0.5 s,
  0.4 s, 0.5 s and 7.1 s) against a 60-second cadence, and stays inside the executor's 100 s
  ceiling.
- **The metric will be red today.** That is the honest reading, not a regression: the memory
  door is unreachable, the default route's TLS handshake fails, four lanes are dropped and the
  cluster-state receipt is 69 hours old. A metric that went green over that would be the
  defect.
- **The metric routes; it does not repair.** Each registry entry carries a structured remedy
  (runner, repo, budget, task) naming the door to work and the file to never edit. The
  woken agent works the entry; the metric moves when the measurement moves.
- **No second door.** The memory plane's remedy names the one door
  (`platform/estate/memory/door.py`) and the local tier behind it; a second memory door is
  the failure mode this whole change exists to prevent.
- **The spend assumption is not yet a number.** The capacity goal needs a measured
  per-agent marginal cost; until that is measured, the registry carries no guessed constant.

## Rejected

- **A second watcher for the founder's surfaces.** The spine already runs every 60 s; a
  competing watcher is the stitching the estate forbids, and two watchers would disagree.
- **A separate "founder score".** The founder asked for ONE metric that prioritises founder
  concerns. The weight and the order do that inside one number; two numbers would need a
  second judgement.
- **Editing the spine to add the new functions.** The spine is claimed by focus #7530; the
  registry is the data-driven extension point, and it is the better bar: a function becomes
  watched by a file edit, reviewed like any other data.
- **A probe that reports "could not measure" as healthy.** That is the fail-open class the
  estate already paid for (R1): unknown is refuse.

## Proof

The measurement is the estate's own, re-runnable:

```bash
python3 platform/estate/libexec/critical-probe.py estate-health
python3 -m pytest -q tests/test_critical_functions_registry.py
```

On 2026-10-30 the judge passed (13 tests) and the probes measured: memory-plane DOWN
(TLS), router-lanes DEGRADED (4 lanes dropped), spend-bound ok, estate-substrate RED
(receipt 4160 min old). The receipts are in `~/.estate/heartbeats/`.
