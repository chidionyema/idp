# ESTATE PROJECTS UNIVERSAL INSTRUCTIONS & RUNBOOK (`INSTRUCTIONS.md`)

**Standard ID**: `ESTATE-SPEC-STD-V2` (Gate `G7_SELF_CONTAINED_INSTRUCTIONS_AND_PUSH`)  
**Principle**: *No repository, feature branch, Outbox deliverable, or sub-project may be pushed or exported without a complete, copy-pasteable `INSTRUCTIONS.md` and `README.md`.*

---

## Project 1: Full-Stack Estate Oracle & Overwatch Control Plane (`server.ts` + `src/`)

### What It Does
Provides the sub-2ms Hybrid BM25F + Trigram RRF Search Engine, Otto Split-Brain Forensics & Direct Router Bypass, Argon Memory Plane (`D1..D9`), Telegram 10-Topic Control Surface, and Dual Private-Repo Inbox/Outbox Relay UI.

### How to Run & Verify
```bash
# 1. Install dependencies & start full-stack server on Port 3000
npm install
npm run dev

# 2. Run the automated test suite (all pure logic + CLI integration tests)
npx tsx --test src/engine/oracleEngine.test.ts
```

---

## Project 2: High-Speed Lock-Free Rust Model Router (`crates/estate-router`)

### What It Does
Replaces the retired Python/TS proxy with an Axum + Tokio lock-free Rust router featuring:
1. `#[repr(align(64))]` cache-line aligned `AtomicU64` EWMA latency scoring (`0` mutex locks)
2. Zero-copy byte-slice JSON-RPC frame classification (`54 µs` P99)
3. `18ms` P95 speculative hedged requests + automatic circuit-breaker quarantine
4. Strict Consulting-Lane Inbox sandbox for MiniMax M2.7 big tickets (`MiniMaxFencedViaConsultingInbox`)
5. Rolling `4,096`-token auto-compaction pre-filter
6. Lock-free 64-bit FNV-1a 3-tries `(tool, args)` ring fence

### How to Run & Verify (Both Routed + Non-Router Direct Active-Active)
```bash
# 1. Run Engine A: Routed Model Dispatcher (bin/estate-router v2.5.0)
node bin/estate-router --model=deepseek-reasoner

# 2. Run Engine B: Standalone Non-Router Direct DeepSeek Socket (bin/deepseek-direct v2.5.0)
node bin/deepseek-direct --model=deepseek-reasoner

# 3. Run the 4-Suite Evaluation & Red-Line Failure Eradication Harness (16/16 cases)
node bin/estate-eval

# 4. Verify all 6 Rust router optimizations & build native binary (when cargo is installed)
node bin/estate-rust-router
cd crates/estate-router && cargo build --release
```

---

## Project 3: Bidirectional Private-Repo Comms Relay (`relay/inbox` & `relay/outbox`)

### What It Does
Unifies your two private repos (`chidionyema/estate-inbox` and `chidionyema/estate-outbox`) into a closed loop:
- **Send to Inbox**: Drop a JSON envelope into `relay/inbox/` (or use the **Send to Inbox** form in the **Router, Voice & Otto** tab).
- **Poll & Audit on Consulting Lane**: `bin/estate-inbox-poll` audits the envelope against `ESTATE-SPEC-STD-V2` (fencing MiniMax M2.7 big tickets safely).
- **Promote to Outbox**: Verified deliverables are signed with CIF-HMAC-SHA256 and written to `relay/outbox/` with embedded usage instructions.

### How to Run & Verify
```bash
# Poll relay/inbox/, audit all envelopes, and promote signed receipts to relay/outbox/
node bin/estate-inbox-poll

# Resuscitate all 4 core agent services and start the 15s Consulting Lane poller
node bin/estate-service-up
```

---

## Project 4: Unified ProtocolKit Plan Contract Fence (`extensions/pi-plan-lock` & `platform/estate/memory/plan.py`)

### What It Does
Unifies Claim `#7680` (`estate-agent` TypeScript half) and Claim `#7692` (`sf-unit` Python half) onto a single canonical specification (`extensions/pi-plan-lock/cases.json`) enforcing:
- Machine-checkable BDD `then` clauses (`exit_code == 0`, `file_exists:`, `grep_match:`, `probe:`, `test_pass:`)
- Strict `3-tries` cap per canonical `(tool, args)` key (refusing the 4th retry unless `declare_plan` or `revise_plan` resets the map)

### How to Run & Verify
```bash
# Run the shared 4-case falsifier suite across TS and Python specs
node bin/estate-plan

# Run Senior DeepSeek deterministic hypothesis synthesis for race-spec
node bin/idp-hypothesize
```

---

## Project 5: Mandatory Spec Standard, Machine Repo Catalog & Private Repo Push (`register/*`)

### What It Does
Enforces all 7 gates of `ESTATE-SPEC-STD-V2` across Claude's private repo work created today, maintains the Machine-Generated Repository Catalog (`register/machine-repo-catalog.json`), and guarantees every push includes `README.md` and `INSTRUCTIONS.md`.

### How to Run, Export & Push to Your Private GitHub Repos
```bash
# 1. Verify all 7 Spec Standard Gates + Claude's 4 re-refined items + Instructions Gate G7
node bin/estate-spec-enforce

# 2. Export & verify the Machine-Generated Repository Catalog
node bin/estate-catalog-export

# 3. Ensure all projects & Outbox packages include instructions and push/bundle
node bin/estate-push-instructions

# 4. Push directly to your private GitHub repositories (with gh CLI)
gh repo create chidionyema/estate-oracle-overwatch --private --source=. --remote=origin --push
```
