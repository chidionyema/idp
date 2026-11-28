# Unified Work Fan-Out Process -- Any Instruction to Verified Yield

- **Status:** active operating process (2026-11-28)
- **Authority:** `docs/decisions/2026-11-28-unified-programme-d1-d11-and-open-infra.md` (`#8812`), `AGENTS.md`, `ADR 0012`, `ADR 0048`, `R43`
- **Rule (AGENTS.md section 6):** zero new orchestrators. This process composes the estate's existing canonical doors so any mission can be fanned out across Desktop, Cloud, Web, and Mobile surfaces with deterministic proofs.

---

## 1. The Six-Stage Fan-Out Pipeline (Repeatable for Any Work)

Every non-trivial instruction follows the exact same 6 stages, whether initiated by the founder on Telegram/Mobile, a desktop harness (Antigravity, Claude Code, Codex, OpenCode, Kimi, Pi), or a cloud runner:

### Stage 1 -- Hydrate Context (One Shared Brain)
Before acting, every worker reads the same live state and shared memory instead of guessing:
- **Memory & plans:** MCP `estate-memory` (`brief`, `recall`, `declare_plan`) via `bin/estate-memory-mcp` (installed uniformly across harnesses from `platform/estate/memory/runtimes.json`).
- **Knowledge graph:** `growmos --root ~/Documents/code/estate-graph context --brief` and `growmos query "<topic>"` (prove a capability does not already exist before building).
- **Live state:** `GET https://live.meridianlabs.cloud/snapshot` (`estate-live-state.v1`, `seq` + `sha256` + explicit `BLIND`) and NATS JetStream (`127.0.0.1:4222` local leaf or off-Mac hub via `bus-ensure.sh` + `platform/estate-live-state/scripts/nats-bridge.mjs`).

### Stage 2 -- Decompose into Single-Subsystem Slices (Parallel-Ready)
Split any mission into independent slices that each obey the machine-enforced lane contract (`bin/verify_three_proofs.py`):
- **1 top-level code subsystem** (`crates/`, `platform/`, `bin/`, `docs/`, etc.) + companion tests under `tests/`.
- **<= 5 files per slice.**
- **Zero guarded paths** (`.github/workflows/`, `AGENTS.md`, `catalog/dof-registry.json`, `catalog/genesis-protocols.json`, `.github/CODEOWNERS`) unless carrying an explicit founder-signed seal.
- **Exact `Scope:` file list** (never globs) so slices never collide and can execute in parallel.

### Stage 3 -- Declare Claim & Ship Contract (Zero Collisions)
Every slice declares ownership on a GitHub issue before writing code:
1. Open/reuse issue with a valid `SHIP-CONTRACT` (`accept: GET https://...` on a real production endpoint -- never GitHub proxy hosts -- plus registered `optimus:`, `failure-classes:`, `debug-pack:`).
2. Post live heartbeat comment: `CLAIM agent=<unique-id> paths=<exact,comma,paths> heartbeat=<UTC-ISO>`.
3. Verify zero collision locally: `python3 bin/claim-gate <base> <head>` -> `exit 0`.

### Stage 4 -- Fan Out Execution Across the Right Surface
Route each independent slice to the cheapest fit execution plane (all sharing the same contracts):

| Slice Type | Canonical Execution Door | Transport / Routing |
|---|---|---|
| **Cloud autonomous slice (off-Mac, default)** | `estate-execute agent-sandbox-dispatch task_file=<file> harness=auto issue=<N>` (`agent-sandbox.yml` + `meridian-fitness` `#8810`) | `llm.meridianlabs.cloud` / `SEED_OPENROUTER_API_KEY` (zero laptop dependency) |
| **Desktop multi-harness slice** | Antigravity (`agy`), Claude Code, Codex, OpenCode, Kimi, Pi -- each operating on its own slice with `Claim: #<N>` and `Agent: <id>` commit trailers | Local NATS JetStream (`ESTATE_FLEET`) bridged to `live.meridianlabs.cloud` |
| **Multi-model deliberation / review (Council v1)** | Trigger-gated (~15% fire rate, abstention-not-failure) across Kimi, ChatGPT/Codex, Gemini/Carbon, Claude | Budgeted on `llm.meridianlabs.cloud`, verdicts posted to the shared live ledger |
| **Web AI / AI Studio intake** | `meridian-membrane` egress gate + `#8702` Drive outbox ingest | Quarantined validation before any `lane/*` landing |

### Stage 5 -- Deterministic Shift-Left Verification & Greenlane Convergence
Never hand-merge `idp` lanes and never bypass hooks:
1. **TDD falsifier first:** prove the test fails before the fix and passes after.
2. **Shift-left checks (Python 3.12 via `~/.estate/venv-ci/bin`):**
   - `ruff check --select E9,F,B,S <py-files>` and `ruff format --check <py-files>`
   - Pure ASCII check on added lines
   - `Language-Exception: <path> -- <reason>` trailer if adding a new non-test Python file (`bin/language-gate`)
   - `bin/capability-index emit --write` as a companion commit if a new capability is discovered
   - `bin/claim-gate <base> <head>` -> `exit 0`
3. **Push to `refs/heads/lane/<slug>`** through `.githooks/pre-push` (`lane-preflight` + `idp-production-readiness` + `idp-fast-gate`).
4. **Greenlane converges automatically:** rebases onto `origin/main`, runs CI batch, opens & merges PR, updates commit status (`gh api repos/chidionyema/idp/commits/<sha>/status`).

### Stage 6 -- Settle, Distill & Surface (Malkuth Proof)
A merged PR is **landed**, not **operating**. Closure requires:
1. **Production observation:** real run URL / live probe / production log line (never synthetic HTTP 200 alone).
2. **Multi-plane asymmetric attestation (`EPISTEMIC-ATTEST-V2`):** `platform/estate/epistemic/attest.py` verifies >= 3 independent control planes (GitHub OIDC/Sigstore + SPIFFE/SPIRE SVID with ghost revocation + independent Ed25519 prober/tempo-node) with zero verifier secrets.
3. **Shared memory update:** `growmos --root ~/Documents/code/estate-graph journal "<fact + SHA + proof>"` and `estate-memory` `remember` so every other surface wakes up knowing the new state.
4. **Calm founder surface:** only `DECISION`-class blockers or morning digest reach Telegram Sovereign Board v2; routine convergence flows silently to `live.meridianlabs.cloud`.

---

## 2. Quick-Start Fan-Out Checklist (Copy-Paste)

1. Hydrate: `growmos --root ~/Documents/code/estate-graph context --brief` + `estate-memory` `brief`
2. Split work into N disjoint slices (1 subsystem, <= 5 files, exact `Scope:` list, 0 guarded paths)
3. Claim each slice on GitHub (`SHIP-CONTRACT` + `CLAIM agent=<id> paths=... heartbeat=<UTC>`)
4. Fan out in parallel:
   - Off-Mac slices -> `estate-execute agent-sandbox-dispatch task_file=<slice.md> harness=auto issue=<N>`
   - Local/complex slices -> parallel harnesses pushing `refs/heads/lane/<slug>` through `.githooks/pre-push`
5. Track convergence: `git fetch origin main` + `gh api repos/chidionyema/idp/commits/<sha>/status`
6. Confirm real production log line, journal in `growmos`, close loop.
