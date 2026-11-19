# Estate Oracle & Overwatch Control Plane (`estate-oracle-overwatch`)

**Cryptographic Estate Search Engine (SQLite WAL + FTS5 BM25F + Trigram RRF), Argon Memory Plane (18/18 Lanes), Lock-Free Rust Model Router (`crates/estate-router` v2.4.0), Unified ProtocolKit (`#7680` TS + `#7692` Python), and Bidirectional Private-Repo Comms Relay (`INBOX` -> Consulting Poller -> `OUTBOX`).**

> **Mandatory Project Standard (`ESTATE-SPEC-STD-V2` · Gate G7)**: Every repository, subsystem, and Outbox delivery pushed across the Estate ships with self-contained `README.md` and `INSTRUCTIONS.md` runbooks so the Founder or any agent can boot, verify, and operate the project in under 30 seconds with zero guesswork.

---

## 1. 30-Second Quickstart (3 Zero-Friction Paths)

### Path A — 1-Line Terminal Bootstrap (macOS / Linux)
```bash
curl -sSL http://localhost:3000/install.sh | bash -s -- estate-oracle-overwatch
```

### Path B — Whole-Repo Archive (`.tar.gz`) or Git Bundle (`.bundle`)
```bash
# Option 1: Full Working Tree Source Archive (.tar.gz)
curl -sSL http://localhost:3000/api/deploy/estate-oracle-overwatch.tar.gz -o estate-oracle-overwatch.tar.gz
tar -xzf estate-oracle-overwatch.tar.gz && cd estate-oracle-overwatch
npm install && npm run dev

# Option 2: Self-Contained Git Bundle with Full Commit History (.bundle)
curl -sSL http://localhost:3000/api/deploy/estate-overwatch.bundle -o estate.bundle
git clone estate.bundle estate-oracle-overwatch && cd estate-oracle-overwatch
npm install && npm run dev
```

### Path C — Resuscitate All 4 Local Agent Services Immediately
```bash
node bin/estate-service-up
```
Brings up all 4 core operational agent loops (`argon-consulting-01`, `deepseek-protocol-01`, `claude-catalog-auditor-01`, `minimax-fenced-worker-01`), verifies `18/18` memory lanes, and triggers an immediate Consulting Lane Inbox -> Outbox poll cycle.

---

## 2. All 12 Production CLI Binaries (`bin/*`)

Every project capability is decoupled into a standalone executable CLI in `bin/` that supports `--json` for machine pipelines and human-readable output for terminal inspection:

| CLI Binary | Purpose & Subsystem | Quick Run Command |
| :--- | :--- | :--- |
| `bin/estate-service-up` | Resuscitates all 4 core operational agent loops (`0 -> 4/4 ONLINE`) and starts Inbox polling | `node bin/estate-service-up` |
| `bin/estate-inbox-poll` | Polls `relay/inbox/` (`chidionyema/estate-inbox`), audits specs on Consulting Lane, promotes signed receipts to `relay/outbox/` | `node bin/estate-inbox-poll` |
| `bin/estate-rust-router` | Verifies & benchmarks all 6 optimizations in `crates/estate-router/src/main.rs` (`54 µs` ingress, `18ms` hedge, MiniMax Inbox sandbox) | `node bin/estate-rust-router` |
| `bin/estate-spec-enforce` | Enforces all 7 gates of `ESTATE-SPEC-STD-V2` (including Gate G7 self-contained instructions) & audits Claude's private repo work | `node bin/estate-spec-enforce` |
| `bin/estate-catalog-export` | Exports & verifies the Machine-Generated Repository Catalog (`register/machine-repo-catalog.json`) & whole-repo channels | `node bin/estate-catalog-export` |
| `bin/estate-push-instructions` | Verifies `README.md` + `INSTRUCTIONS.md` across all projects, attaches runbooks to Outbox receipts, and commits/pushes to private remotes | `node bin/estate-push-instructions` |
| `bin/estate-plan` | Evaluates the unified `#7680` (TS) + `#7692` (Python) 3-tries `(tool, args)` fence & `cases.json` falsifiers (`4/4 PASS`) | `node bin/estate-plan` |
| `bin/idp-hypothesize` | Runs Senior DeepSeek deterministic hypothesis synthesis for `race-spec` (`exit 0`) | `node bin/idp-hypothesize` |
| `bin/estate-memory-audit` | Audits all 18 operational memory lanes (`register/memory-lanes-18.json` · `18/18 OPERATING`) | `node bin/estate-memory-audit` |
| `bin/estate-decide` | Verifies Argon Governance Decree (`DECISION-ARGON-MEMORY-0021`) across ballots `D1..D9` | `node bin/estate-decide` |
| `bin/estate-claim-brief` | Generates token-budgeted (`<= 220 tok`), staleness-gated Claim-Open Memory Briefs | `node bin/estate-claim-brief --ticket=TICKET-42` |
| `bin/memory-dream` | Runs bounded Dreaming V3+ episodic-to-semantic memory consolidation | `node bin/memory-dream` |

---

## 3. Dual Private-Repo Comms Relay (`INBOX` -> Consulting Poller -> `OUTBOX`)

1. **Inbound Queue (`chidionyema/estate-inbox` / `relay/inbox/*.json`)**:
   - Receives work dispatches from the Founder, Claude's private repo, and **MiniMax M2.7 Big Tickets (`BIG_TICKET_FENCED`)**.
2. **Consulting Lane Poller (`bin/estate-inbox-poll`)**:
   - Runs automatically on a 15-second timer (and background cron) on the Consulting Lane (`argon-consulting-01` + `deepseek-protocol-01`).
   - Verifies that the envelope satisfies all 7 gates of `ESTATE-SPEC-STD-V2` (including machine-checkable BDD `then` predicate, 3-tries fence, 4096-token compaction, and self-contained instructions).
3. **Outbound Verified Ledger (`chidionyema/estate-outbox` / `relay/outbox/*.json`)**:
   - Writes a CIF-HMAC-SHA256 signed receipt + step-by-step instructions runbook to `relay/outbox/`.

---

## 4. Verification & Deterministic Rollback

```bash
# Run full unit & integration test suite (node:test)
npx tsx --test src/engine/oracleEngine.test.ts

# Verify production TypeScript + Vite build
npm run build

# Single-command deterministic rollback to clean main
git checkout main -- . && node bin/estate-service-up
```
