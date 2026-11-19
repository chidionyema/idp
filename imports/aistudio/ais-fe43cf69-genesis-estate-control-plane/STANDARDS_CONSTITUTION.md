# MERIDIAN ESTATE — SOVEREIGN ENGINEERING, DELIVERY, WHITE-BOX MEMORY & BDD CONSTITUTION

- **Accountable Principal**: Chidi Onyema (`chidionyema@gmail.com`)
- **Enforcing Kernel**: `@meridian-estate/beast-governor` (`./bin/standards`, `./bin/beast`, `./bin/io`, `./bin/omega`)
- **Live UI & API Doors**: `#standards`, `GET /standards`, `POST /api/standards/compile-bdd`, `POST /api/standards/onboard-agent`, `POST /api/standards/memory-query`, `POST /api/standards/intercept-blocker`
- **Escape Room**: **ZERO (`MAXIMUM_LOCKDOWN` Default)** — Every rule below is deterministically enforced by AST, Git, Rego, or Kernel Ingress gates.

---

## 1. Stack Coding & Architectural Purity Standards (`STD-01`)
1. **Pure Logic Decoupling**: All state machines, policy evaluators, memory ledgers, financial/compute routers, and BDD compilers live in pure, zero-DOM TypeScript/C99 modules (`packages/*`, `src/engine/*`) tested in `< 300 ms` via `npx --yes tsx --test`.
2. **Strict Type & Wire Safety**: `tsc --noEmit` with zero `any`, zero `@ts-ignore`, and mandatory runtime schema validation at Express/CLI boundaries.
3. **Anti-Slop & Accessibility Discipline**: Zero `window.alert`, zero `setInterval` fake telemetry, zero static pill badges on metadata, zero `border-l-4` callouts, mandatory `tabular-nums` on numeric columns, and native accessible HTML controls (`<button>`, `<nav>`, `<main>`).
4. **Canonical Engine Reuse**: Never rebuild `PACK-15` (`@meridian-estate/io-engine`) or `PACK-02` (`@meridian-estate/omega-core` 3-symbol HAL: `sense`, `actuate`, `link`).

## 2. Intent-to-Formal-Spec & On-the-Fly Executable BDD Gate (`STD-02`)
1. **Zero Raw Prompt Propagation**: No raw prompt or ambiguous instruction may cross into `INS-*` packets, Legion workers, or git commits (`BLOCKED_RAW_UNSPECIFIED_PROMPT`).
2. **4-Stage SpecGate Pipeline**:
   - **De-Noise & Hydrate**: Resolve domain terms automatically from White-Box Memory (`M0..M4`) and Tombstones (`TOMB-01..TOMB-07`).
   - **Bounded Clarification**: Ask the Founder *only* when genuine novel product/destructive ambiguity exists (`entropy > 0.25`); never re-ask solved questions.
   - **Formal Contract**: Emit explicit `preconditions`, `invariants`, `postconditions`, `forbiddenSideEffects`, and `blastRadiusCap`.
   - **Executable Gherkin BDD**: Emit `>= 3` `Given / When / Then` scenarios mapped to deterministic shell/test assertions and seal `specMerkleSha256`.

## 3. Git, Greenlane & CI/CD Delivery Standards (`STD-03`, `STD-04`)
1. **Line-1 Session & Commit Trailers**: Every session starts with `./bin/io session-start`. Every commit carries `Session-Id`, `Pack-Id`, and `Spec-Sha256`. Zero parked git stashes or unmerged orphan branches.
2. **Merge-Base Delta Isolation (`INS-07957`)**: Pre-push gates evaluate `git merge-base origin/main HEAD` with `collected >= 10` tests so moving `main` noise never causes false negatives, followed by fast-forward Greenlane Merge Queue sealing.
3. **Continuous 14-Surface Production CI**: Every 6-second Beast sweep verifies all 6 Fractal Layers (`L0..L5`) and all 14 UI routes (`0` console errors, `0` failed HTTP calls), triggering `< 15 ms` disruptive all-surface wake-up across Browser, Mac Console, and Cloud on any breach.

## 4. Deterministic Open-Source Toolchain Across Laptop & Cloud (`STD-05`)
- **Formatting & Linting**: `@biomejs/biome` (`< 45 ms` Rust single binary).
- **Dead-Code & Legacy Reaper**: `knip --strict` (zero orphan files, unused exports, or dead dependencies).
- **Structural AST & Layer Boundaries**: `ast-grep (sg)` + `dependency-cruiser` (enforcing Ring-0 $\leftarrow$ Ring-1 $\leftarrow$ Ring-2 DAG).
- **Property-Based Falsification**: `node:test` + `fast-check` shrinking counterexamples for Geburah tribunal gates.
- **Hermetic Multi-Machine Parity**: `mise.toml` + `lefthook` + `Open Policy Agent (estate.rego)` + `Playwright CLI`.

## 5. 5-Tier White-Box Memory Architecture (`STD-06` — Zero Dumb Cache)
Agents are **strictly forbidden** from writing unverified prose notes into memory (`REJECTED_UNVERIFIED_DUMB_CACHE_WRITE`). Memory is operated exclusively by the Beast Kernel across 5 auditable tiers in `.ops/whitebox-memory-ledger.json`:
- **M0 — Constitutional & Tombstone ROM**: `AGENTS.md`, `estate.rego`, and `TOMB-01..TOMB-07` (`IMMUTABLE_ROM`).
- **M1 — Active Working Spec Frame**: Current `FormalIntentBddSpec` & fencing lease (`SESSION_SCOPED_LEASE`).
- **M2 — Episodic Cryptographic WAL**: `.ops/register.jsonl` + `.ops/evidence/*.json` (`HASH_CHAINED_PERMANENT`).
- **M3 — Semantic Antibody & Invariant Graph**: Verified root causes & Pass-0 antibodies with `retrievalHitCount`, `causalLiftPct`, and 30-day confidence decay.
- **M4 — Dreams Counterfactual & SFT/DPO Distillation**: `.ops/realtime-training-dataset.jsonl` consolidated on `$0.00` Free Lanes.

## 6. Mandatory Pre-Session Agent Onboarding & Tombstone Anti-Pester Gate (`STD-07`)
Before any session transitions to `CERTIFIED_SESSION_READY`, `./bin/standards onboard` verifies all 6 gates and binds all **7 Sealed Tombstones** (`Telegram 3327`, `Cloudflare scratch`, `OCI OKE #2468`, `protocolEngine.ts:17129`, `~/.estate`, `32 stashes / 92 branches`, `agent self-memory`). Any attempt to re-ask the Founder about a tombstoned blocker is deterministically intercepted in `< 1 ms`.

## 7. Centralized Data Governance, Incident Runbooks & 3-2-1 Backup (`STD-08`)
Zero state is permitted to live solely on a single laptop. All 7 operational stores are classified (`SOVEREIGN_PUBLIC_SAFE`, `OPERATIONAL_AUDIT_CHAIN`, `VAULT_SCOPED_EPHEMERAL`), scrubbed of plaintext secrets (`bw-estate-sovereign` ephemeral TTL leases only), bound into `GENESIS_SPORE.dna` (`<= 4,096 B`), and mirrored to `chidionyema/argon`, `chidionyema/idp`, and `/api/argon/export.tar.gz`.
