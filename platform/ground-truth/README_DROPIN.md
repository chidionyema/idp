# genesis-ground-truth v0.9.1 — Real-Time Ground Truth & Universal Agent Prerequisite

Drop-in Rust crate compatible with `genesis-kernel` v0.8.0+ (`/var/lib/genesis/genesis.db`, `kernel_fence_state`, `realtime_event_ring`, Axum 0.7, SQLite WAL).

## Zero-Friction Integration (3 Steps for Claude Code)

1. **Mount into `idp` workspace:** Place this directory at `platform/ground-truth` (or merge `ground_truth_router(engine)` into `genesis-kernel` `:4001`).
2. **Verify locally & on `ubuntu-latest`:**
   - `cargo test --tests` (runs all 5 differential & adversarial falsifier suites in `tests/differential_falsifiers.rs`)
   - `cargo build --release --bins`
3. **Wire Universal Prerequisite across all surfaces:**
   - Register GitHub App/Org webhook (`push`, `workflow_run`, `check_run`, `pull_request`, `issues`) to `POST /api/webhooks/github` with `GITHUB_WEBHOOK_SECRET`.
   - Set `FOUNDER_ED25519_PUBLIC_KEY` (32-byte hex) and `GITHUB_READ_TOKEN` (used strictly for one-shot cold-boot hydration, zero polling).
   - Every CLI/CI agent boots with `genesis-truth-boot <url> <surface> <role> <repo> <paths...>` (prints live 6-block Markdown + issues fenced `lease_id` & `scope_sha256`, exits 2 if stale/degraded/unadmitted).
   - Every web surface (`FounderConciergeSurface.tsx`, `platform/brain-hub`) subscribes to `GET /api/realtime/ws` and fetches `GET /api/truth/live` or `GET /api/truth/live.md`.
