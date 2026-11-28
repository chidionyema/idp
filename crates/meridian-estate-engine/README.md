# meridian-estate-engine

Compiled FLOW -> DOF -> LEGION (Muster) -> KARMA workspace. Five crates, one binary.

| Crate | Owns |
|-------|------|
| `meridian-karma` | causal debt ledger; strict parent order; no self-graded yield; ancestral failure survives handover |
| `meridian-dof` | L0-L3 capability lease; dual probe; 1-down/3-up hysteresis; epoch fencing; L3 red card |
| `meridian-muster` | 5 kernels, 8 formations as data, fractal recursion with depth/fan-out/budget caps, SHA-256 receipt chain, scorecard |
| `meridian-flow` | reuse-before-invent, DOF gate, Muster dispatch, KARMA settlement by an independent oracle |
| `meridian-army` | one binary that exercises the chain and prints the sentinel |

```bash
cd crates/meridian-estate-engine
cargo test --workspace --locked
cargo run -q --locked -p meridian-army   # optimus.estate.karma_dof_legion_flow_unified=1
```

## Status: built, not operating

Verified by `cargo test` in CI (`.github/workflows/meridian-estate-engine.yml`). Not yet true:

- FLOW reads a hard-coded registry, not the capability registry.
- Nothing calls this from Greenlane, `agent-sandbox.yml` or any scheduler, so no production log line exists.
- DOF's epoch fence is only as strong as the caller: FLOW passes the engine's current epoch, so a stale lease is not detected across a run. A lease captured at grant time is the next change.
- `catalog/dof-registry.json` still carries retired OKE paths; this workspace does not read it.
- `clippy -D warnings` is not in CI yet.

## Defects found by the first real tests (each test failed on the unfixed code)

1. A failed unit in a K2+K5 formation (Phalanx) returned `Ok` receipts and FLOW settled it.
2. Re-accepting an instruction id reset its ledger and erased ancestral failures.
3. FLOW could re-run, and re-settle, an existing instruction id.
