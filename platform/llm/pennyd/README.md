# pennyd — 24/7 autonomy at pennies

## Platform home

This is the canonical source under the `idp` platform, not a downloaded package:

    platform/llm/pennyd/

`Cargo.lock` is committed. The platform manifest is `kustomization.yaml`; it renders the
router Deployment, provider ConfigMap, edge-key ExternalSecret, persistent audit/budget volume,
Service and ServiceMonitor. LiteLLM remains the live listener until the traffic migration is
proven; compiling and rendering pennyd does not move traffic.

OpenAI-compatible edge daemon. Pure Rust, zero Python. Token savings are
structural: the daemon enforces them for every client; clients cannot opt out.

## Model-agnostic by construction

Providers and models are **data**, not code:

    providers/
      ollama.toml      # dialect, base_url, auth, [[models]] with prices + aliases
      deepseek.toml
      anthropic.toml

**Add a provider** (OpenAI-compatible — DeepSeek, OpenRouter, Groq, Together,
Mistral, vLLM, llama.cpp, ollama, …): drop one TOML file. Zero code.
**Add a model**: one `[[models]]` block. Zero code.
The provider's `request_path` is mandatory and exact; pennyd never infers or
rewrites a vendor API version. Founder-first onboarding:
[`providers/README.md`](providers/README.md).
**Retarget an agent**: change which alias it calls, or change what the alias
points at — clients never change.

- Hot reload: edit a file, live within `reload_interval_s` (default 5s).
  A broken file keeps the last good registry (loud error log, never silent).
- Cascade order is computed: `(class, price_in)` — Local < Free < Paid, then
  cheapest input price. Never hand-ordered.
- Laws enforced at load: filename == provider id, globally unique model ids
  and aliases, known dialects only. All failures are loud.
- Discovery: `GET /v1/models` lists the registry; unknown models get a 400
  listing available aliases.
- Dialects: `openai` (passthrough, covers most of the world) and `anthropic`
  (native Messages API, translated structurally). A genuinely new dialect is
  one `impl Dialect` in `crates/penny-core/src/dialect.rs`.
- Cache keys use the canonical `provider/model` id, so aliases never
  fragment the cache namespace.

## Pipeline

    auth -> resolve model (alias|provider/model) -> exact cache -> shape
         -> cheap-first cascade (circuit breakers) -> hard budget -> decision log

## Run

    cargo test
    cargo run --release -- config.example.toml

Clients point at `http://<host>:4000/v1` with `Authorization: Bearer sk-<agent>`.
Lane env vars (e.g. `DEEPSEEK_API_KEY`) must be set; `auth = { kind = "none" }`
for local lanes.

## Founder visibility

- `/dash` — live HTML: spend, saved, hit rate, floor alert
- `/metrics` — Prometheus text
- decision log — hash-chained JSONL, `/health` verifies the chain

## Adversarial-review status (old sovereign-router pitfalls → pennyd)

| Pitfall | Status |
|---|---|
| Claude Code→GLM dialect rejection | Anthropic-ingress edge adapter not yet built — tracked, not faked |
| Routes through LiteLLM | No LiteLLM dependency; lanes are direct providers |
| Stale installed binary | `/health` reports CARGO_PKG_VERSION + GIT_SHA build stamp |
| Silent cross-model substitution | Impossible by construction: resolved model → its own lane; escalation only via explicit `fallbacks` declared in data; unknown fallback refuses at load |
| No streaming (32MB buffers) | SSE passthrough on streaming-capable lanes; non-streaming lanes skipped, never silently buffered; streams never cached; budget charged on flagged estimate |
| Efficiency layer adds tokens | Zero added context; shaping subtracts |
| No per-request accounting | Decision log records req id, latency, tokens, cost, lane, fallback path per request |
| No client auth | Bearer keys; unknown keys → 401 by default (`allow_unknown_keys` opt-in) |
| Synthetic health evidence | `/health` verifies the real hash chain; no fabricated preflight |

## Commercial package

`Makefile` (ci/test/clippy/audit/sbom/image) · `Dockerfile` + `docker-compose.yml`
· `deploy/` (systemd, launchd, kustomize + ServiceMonitor) ·
`.github/workflows/ci.yml` · `AGENTS.md` repo laws · `ADOPTION.md` (founder
15-minute + enterprise + proof protocol) · `RELEASE.md` checklist ·
`FAILURE_MODES.md` FMEA with per-row test mapping. `make ci` is the
adoption gate: fmt + clippy -D warnings + tests + audit.

## Verification status

Structural verification (59 checks: module pairing, brace balance, field
exactness, no stubs) is green. `cargo test` on a Rust 1.75+ host is the
compile/runtime proof — no toolchain existed in the authoring sandbox.
