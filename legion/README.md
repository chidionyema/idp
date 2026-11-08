# legion/ — the Legion automation kit

Discovery as data, proof as a command, ranking as computation. Zero tokens,
zero network: everything here is deterministic and local. This package is the
automation floor the Legion Elite Layer stands on (see the program doc).

## The three verbs

```sh
python -m legion validate legion.yaml          # is this manifest fit to index?
python -m legion proof legion.yaml             # run the proof, chain the evidence
python -m legion proof --verify state/legion-proof.jsonl   # chain intact?
python -m legion scorecard state/metrics/ --out state/scoreboard.json
```

## The manifest (every legion repo carries one)

`legion.yaml` (or `legion.json` — JSON is the dependency-free form) at the
repo root:

| field | rule |
|---|---|
| `legion` | positive int — the legion number |
| `name`, `repo`, `summary` | non-empty strings |
| `capabilities` | non-empty list — what agents may route here |
| `modes` | subset of `in-process, nats-worker, temporal, gh-runner, cron, kronos-isolated` |
| `budget.max_usd_per_day` | positive number — the hard LiteLLM envelope |
| `proof.command`, `proof.max_seconds` | the evidence command; timeout clamped ≤ 3600s |
| `slo.success_rate_min`, `slo.p95_latency_s_max` | the bar the ranking plane enforces |
| `health.max_heartbeat_age_minutes` | optional dead-man's switch config |

`validate` reports EVERY problem, not just the first.

## The evidence chain

`proof` appends to `state/legion-proof.jsonl` (override with
`LEGION_STATE_DIR`). Each record is sha256-chained to its predecessor — the
same tamper-evidence pattern as pi_bridge's run log. The record states what
the proof command actually did: exit code, duration, output tail. A failed
proof is a recorded fact; the tool never upgrades it.

## The scoreboard

`scorecard` reads per-legion metric files and computes the composite
(30% success · 20% cost · 20% latency · 15% audit · 15% uptime — weights
founder-tunable via `--weights`). Proof older than 24h **halves** the score;
below 0.60 the legion is `shadow` and routing avoids it. The output JSON is
what estate-execute reads before dispatching — ranking is reproducible from
the same inputs, so routing decisions are auditable.

## Scheduling note

Running these on a timer (proof every 24h, scorecard recompute) is a
background job — per estate governance that needs founder sign-off. The kit
itself is inert until invoked.

## Language exception (operational migration)

The estate's long-term preference for Rust remains in force for new capabilities.
This tranche imports and hardens the **already implemented and cloud-tested**
Legion kit from IDP #7733, rather than write a second untested runtime to
recover live operations. This compatibility slice retains the existing Python
entry points, deterministic manifest validator, bounded proof executor and
21 executable regression tests. It is not an exemption for new Python agent
orchestration or for bypassing the Greenlane. A Rust replacement must first
preserve the CLI and evidence contracts and pass the same test suite.

The active execution plane is GitHub-hosted; the Mac and the unavailable
cluster are not runtime prerequisites. The proof command for the estate-homes
Legion invokes the existing service-lane probe and publishes its exact verdict.

## Recursive tool-first readiness and failure memory

The Legion tool itself must prove startup, failover, failed-work preservation, signed firewall, issue claim, Greenlane admission and runtime-effect readback **before** it is admitted to govern other critical tools. Unknown failures quarantine privileged effects while preserving original missions and recovery capability.

Every next session performs one lookup: `python -m legion diagnose LEGION_RATE_BOTH --json` for the registered diagnosis, bounded authorized repair and independent effect proof. The versioned `legion/failure_atlas.json` is institutional memory; run receipts must land on the original GitHub mission issue. This source addition is NOT a deployed recovery job or a claim of 30-second activation.
