# Implementation Plan: Estate recursive adversarial assurance
**Branch**: research candidate (no promotion) | **Date**: 2026-11-19 | **Spec**: spec.md
## Summary
Harden existing NSVEE/verification contract, judge statistics, mutation execution and Greenlane before PR creation. Use native estate identity, evidence and recovery machinery.
## Technical Context
**Language/Version**: existing Python modules, shell/YAML and existing Argon Node adapter. **Dependencies**: existing pytest/pytest-bdd, NumPy, QUAD cryptographic verifier, runner adapters. **Storage**: existing evidence/FLOW/KARMA, no new store. **Target**: trusted Linux CI plus approved estate execution. **Performance**: risk-scoped mandatory checks, deduplication by full context digest; measure rather than assume latency. **Constraints**: no direct PR/main push, no unsigned lane, no production test secrets exposed to candidates, no single dependency on target cluster.
## Constitution Check
Reuse ADR 0046, AGENTS.md, claim and lane-submit; no replacement control plane. Code packet is not signed admission. Independent release proof must run on real path. Recheck after integration.
## Project Structure
Existing `nsvee/engine.py`, `platform/estate/nsvee_enforcement.py`, `platform/eval/judge_drift.py`, `platform/eval/judge_worker.py`, `platform/eval/pareval_layer.py`, `bin/mutation-orchestrator`, `greenlane/github.py`, candidate workflows and `features/assurance/` with corresponding `sovereign/tests/bdd/` bindings. Argon `ops/review/` uses the same receipt, not an alternate gate.
## Execution order
1. Reproduce failures at pinned main 99420ce372fa53dc859553e1f414c85ab2f62854. Apply local core packet only after claim overlap check. Run negative/positive tests and existing sibling suites.
2. Bind trusted verification authority and explicit required check selection. Split candidate execution from test/controller/signing identity. Fix mutation orchestration and schedule. Verify actual pre-PR calls, not markers.
3. Wire Greenlane final per-head proof before PR effect. Remove circular PR-only mandatory inputs by moving checks to immutable queue candidates. Verify base/head CAS/fence and atomic idempotency; no automatic acceptance of changed head. Protect recovery.
4. Exercise Legion red team/fixer/solver and supervisor on real authorized runner, independent holdouts, matched baseline. Integrate existing Argon admission adapter and capability registry; evidence indexed by FLOW/QUAD and surfaced in Genesis.
5. Canary then staged promotion through signed lane-submit. Close only after exact landed revision and independently observed operational effect.
## Complexity Tracking
None justified: extensions only, no new service.
