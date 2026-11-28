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

Verified by `cargo test --workspace --locked`, run from the root suite by `tests/test_meridian_estate_engine.py`
(which also requires the army sentinel). Not yet true:

- FLOW reads a hard-coded registry, not the capability registry.
- Nothing calls this from Greenlane, `agent-sandbox.yml` or any scheduler, so no production log line exists.
- Token usage is not measured: FLOW records 0 tokens, never an invented count.
- DOF refuses a second failing component by going to L3 with a red card; it does not model more than one concurrent repair.
- DOF path rules are lexical. They do not resolve symlinks or check what is on disk.
- `catalog/dof-registry.json` still carries retired OKE paths; this workspace does not read it.
- `clippy -D warnings` is not in CI yet.

## Defects found by the first real tests (each test failed on the unfixed code)

1. A failed unit in a K2+K5 formation (Phalanx) returned `Ok` receipts and FLOW settled it.
2. Re-accepting an instruction id reset its ledger and erased ancestral failures.
3. FLOW could re-run, and re-settle, an existing instruction id.

## Failure modes closed by the hardening pass (each test failed on the unfixed code)

- Muster: negative cost or ceiling refused; receipt hashes length-prefixed (no `|` collisions); NaN or out-of-range scorecard input is shadow, unknown proof age is stale.
- Karma: blank ids refused; every refused event leaves a gap; settled is terminal; an ancestral failure reopens a settled debt; anyone who ever held the debt cannot certify a correction or verify the yield; negative money refused.
- DOF: paths normalised (`./`, `//`, `..`, case, absolute) before every rule; a safe-doc action must name a path; only distinct repair steps count; only the failing component's passes restore it; a second failing component fails closed.
- FLOW: a lease epoch captured by the caller is fenced by DOF; no units or an empty receipt chain is not yield; a failed run leaves a failure on the debt; a refused acceptance stops before work runs; empty keywords match nothing.
