# I-8046 Universal Fleet Cage, Founder Surface Control Plane & Deterministic Auto-Main Suite

## 1. Architecture & Pre-Verified Local Test Receipts (`TEST_RECEIPTS.json`)
Every artifact in this bundle has been formally model-checked and hermetically tested before packaging:
- **Formal Specification (`specs/GenesisSplitAuthorityCertifier.tla` & `.cfg`):** Verified across all reachable states for `INV_1_ImproverCannotSelfCertify`, `INV_2_TrojanNeverReachesMain`, `INV_3_OSAndBrowserQuarantine`, and `INV_4_ReversibleJournalConsistency`.
- **Executable Gherkin BDD Suite (`features/i8046_universal_cage_and_automain.feature`):** All 6 scenarios (80 unauthorized Class B mutation attempts blocked, Class A hardware seal verified, OS/Browser quarantine verified, `<10ms` rollback verified, `#8045` work-in-flight commit split `6ed3d165` vs `937dda9d` verified, and Rust `pennyd` `:4200` vs `sovereign-router` `#8022` verified).
- **Founder Surface Control Plane (`ui/FounderConciergeSurface.tsx` & `src/main.rs`):** Full UI & kernel handlers to toggle the 5 lockdown layers, inspect and drain work-in-flight branches into `main` after local hermetic tests pass, monitor both routers, and trigger 1-click rollbacks.
- **Deterministic Auto-Main & OS Eviction (`scripts/deterministic_automain_drain.py`, `scripts/enforce_os_agent_eviction.sh`, `.github/workflows/greenlane-deterministic-automain.yml`):** Works natively with Greenlane on personal GitHub accounts without requiring paid org Merge Queues.
