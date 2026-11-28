# Compile & Land on `chidionyema/idp` (Rust-First)

1. Unpack into `chidionyema/idp` on `lane/rust-ctrl001-kernel-and-gate`.
2. Run:
   - `cargo test --workspace` (all 21 Rust `#[test]` functions covering E01-E23)
   - `cargo build --release -p meridian-gate`
   - `./target/release/meridian-gate --optimus` (must print `optimus.kernel.rust_invariant_gate_enforced=1`, exit `0`)
   - `python3 tests/verify_all_24_edge_cases.py --rust-bin ./target/release/meridian-gate` (runs all 24 wire + bridge + Ed25519 edge cases against the real compiled Rust binary!)
3. Wire `sovereign/engine/workflow.py` `_retain_instruction()` to call `sovereign/engine/rust_gate_bridge.py`, run `pytest sovereign/engine/test_instruction_id.py` + `./bin/estate-gate`, post non-proxy `SHIP-CONTRACT`, push, and stop.
