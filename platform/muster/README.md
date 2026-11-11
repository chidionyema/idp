# Muster

Muster is Legion's orchestration engine. It turns a goal into a receipt-gated
run: select a formation, execute its kernels, stop at approval or budget gates,
and refuse to advance when the previous step's proof is missing.

It does not provision infrastructure. Intercloud chooses and operationalises
the lane; Muster schedules the work that runs there. It also does not hold model
credentials or call providers directly. Pennyd is the sole model door.

## Kernels

- K1 Chain: topological execution with nested formations.
- K2 Scatter: bounded map-reduce.
- K3 Debate: bounded adversarial rounds with a judge receipt.
- K4 Tournament: cost-aware utility rather than raw pass@k.
- K5 Gate: deterministic or approval veto.

Formations are data. The same engine can operate phalanx, cohort, wedge,
pincer, obsidian, red-team, inquisitor and composed formations.

## Proof

Receipts and events are SHA-256 chained. Receipts carry the Pennyd request IDs
that funded each model step, allowing dual-chain verification against Pennyd's
decision log. The run can resume from its completed-step map without repeating
verified work.

## Status

The imported core passes:

```text
11 passed; 0 failed
```

Run:

```bash
CARGO_TARGET_DIR=/tmp/muster-target cargo test
```

This proves the core kernels and receipt mechanics. Production integration with
Intercloud placement receipts, Pennyd request IDs and a controller-owned run
store remains a separate delivery.
