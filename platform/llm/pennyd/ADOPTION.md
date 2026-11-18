# pennyd — adoption guide

## Founder/estate (15 minutes)

1. `cargo build --workspace --release` → copy `target/release/pennyd` to
   `~/.estate/bin/pennyd`.
2. `mkdir -p ~/.estate/config ~/.estate/providers`; copy `config.example.toml`
   → `~/.estate/config/pennyd.toml`; copy `providers/*.toml`.
3. Set lane env vars (`DEEPSEEK_API_KEY`, …) in your launcher environment.
4. Install the service unit (`deploy/systemd/pennyd.service` or
   `deploy/launchd/com.estate.pennyd.plist`) and start it.
5. Point one agent at `http://127.0.0.1:4000/v1` with its key. Watch
   `/dash`. Migrate the rest per-plane, one key each.

Migration from sovereign-router/LiteLLM: same port, same env contract —
clients change only base URL + key. Keep old router running until per-plane
keys show expected traffic in `/metrics`.

## Enterprise

- Image: `docker build` / compose / kustomize (`deploy/`). Providers as
  ConfigMap, lane keys as Secret, Prometheus via ServiceMonitor, audit via
  the PVC-backed decision log.
- Per-tenant keys with `daily_budget_usd` + `allowed_models` (ACL).
- Due-diligence bundle: `FAILURE_MODES.md`, hash-chained decision log
  (per-request tokens/cost/lane/latency), build stamps in `/health`, SBOM
  (`make sbom`).

## Proof protocol (how you know it works)

1. **Baseline ~1 week**: all traffic on per-plane keys, no changes. Metric:
   cost per successful task per key.
2. **One intervention per key-cohort per phase** (cache+shaping →
   event-driven wakeup → per-key ACLs → compaction). Keys are experimental
   units; the decision log diff is the experiment.
3. **Pre-registered rule** before each phase: adopt if cost/task drops ≥30%
   with no p95 regression and no budget-exhaustion increase.
4. **Rollback = config revert + hot reload** (≤5s). Weekly founder review
   renders the experiment table from the log (see README jq one-liner).

## Harness-side practices (client concern, not gateway)

Plan-mode-before-edits (20–35% cheaper), programmatic tool calling (PTC,
~77% input-token cut), developer-written skills (41.7% cut), event-driven
wakeup (95%+ of wait cost) live in the agent harness. pennyd is the ground
truth that measures them: if the log can't show the effect, it didn't happen.
