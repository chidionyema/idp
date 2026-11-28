# THE BEAST — Sovereign Reference Kernel & Unsleeping Estate Governor (`MERIDIAN-BEAST-V1`)

**Classification:** P0 — Sovereign Root Runtime  
**Organisation:** Meridian Intelligence  
**Status:** SPECIFICATION + RUST KERNEL (`operational_yield = 0` until compiled & proven live on Zone B)  
**Architectural Mandate:** Unify every deterministic and non-deterministic organ of the Meridian Estate under one unsleeping, economy-obsessed, zero-LLM-hot-path Rust reference kernel.

---

## 1. The Psyche of the Machine (Jeff Dean Systems Translation)

1. **The Mark (`SovereignMark` — Complete Mediation):** No process—LLM, cron, webhook, CI runner, or human surface—buys inference, sells a commit to `main`, mutates state, or touches an external sink without presenting a live, Ed25519-signed `SovereignMark` bound to `(domain_id, actor_urn, billing_class, footprint_hash, reservation_id, revocation_epoch, lease_epoch, expires_utc)`. Unmarked calls fail closed in microseconds with zero side effect.
2. **Zero LLM in the Hot Path:** The Beast never calls an LLM to decide safety, escrow, scope, or closure. LLMs are untrusted stochastic heat engines trapped inside the Beast's cylinders; the Beast itself is compiled, deterministic Rust.
3. **Adversarial Dual Governance (Non-Deterministic + Deterministic):**
   - *Non-deterministic workers* are fenced by minor-unit escrow, billing-class isolation, Ring taint lattices, split-authority certification, and zero-note / zero-blocker closure traps.
   - *Deterministic infrastructure* (CI gates, `bin/*` permissions, probes, DNS/TLS, schedules, WAL chains) is continuously falsified on every event—never trusted on historical faith.
4. **Domain Bulkheads (Maximally Permissive Severity):** The Beast is sharded per `domain_id` (matching Cloudflare Durable Object single-writer linearizability). Compromising or freezing `prospector` at `L3` never stalls `idp-core` or `memory-zoneb`.
5. **The Beast of Burden Law (Zero Founder Toil):** Every machine-resolvable fault triggers an immediate sub-millisecond reflex (`DrainLane`, `FailoverSameClass`, `AutoSpawnDirectAttack`, `DofNarrow`, `EpochBump`, `RollbackCheckpoint`). The Founder receives ONLY verified operational yield receipts or irreducible Class A external boundaries (exact `SEED_*` secret / external billing).
6. **Watch the Watchman (`LAW 50` + Split Compilation):** The live Beast binary is built strictly from signed `origin/main` + Founder Ed25519 seal, monitored by an orthogonal external dead-man's canary. If the Beast goes silent, cooperative sinks freeze (`BEAST_BLIND`) rather than failing open.

---

## 2. Organ Map (Zero Competing Engines — One Sovereign Nervous System)

| Organ | Crate / Subsystem | Role Under the Beast |
|---|---|---|
| **Sovereign King / Nervous System** | `meridian-beast-core` + `meridian-beastd` | Unsleeping event loop, `SovereignMark` verifier, Merkle-WAL causal bus, sub-millisecond reflex table, per-domain NPV accounting |
| **Heart & Circulatory System** | `meridian-ledger` (`BudgetLedgerDO` + `RoutingStateDO`) | Linearizable minor-unit escrow & signed `estate.lane-fitness.v1` oxygen routing |
| **Skeletal & Muscular Army** | `meridian-battalion` + `meridian-legion` + `meridian-muster` | 5 execution kernels (`K1–K5`), 8 canonical formations (`Sniper`..`Sieve`), same-class failover |
| **Sensory & Epistemic Cortex** | `meridian-greenlane` + `meridian-karma` + Zone B Memory | Presubmit parity, `3/3` blackbox probes, causal debt ledger, bi-temporal truth + negative antibodies |
| **Immune System & Reflex Arc** | `meridian-dof` + `meridian-gate` | `L0–L3` capability leases, `1-down/3-up` hysteresis, note-ban, inverse no-blocker closure |
| **Intent Router** | `meridian-flow` | 6-phase reuse-before-invent dispatch |
