# ADR 2026-11-28 — Unified Estate Programme (D1–D11) & Open-Infrastructure Architecture

- **Status:** ratified by founder (`2026-11-28T17:10Z`), execution in progress via `lane/*`
- **Refines:** ADR 0012 (messaging day 0), ADR 0034 (free-tier placement), ADR 0048 (one node + admission list), R43 (`platform/edge/provider-independence.yaml`), `2026-11-17-the-estate-runs-without-any-one-device.md`
- **Related issues:** `chidionyema/idp#8759`, `chidionyema/idp#8705`, `chidionyema/idp#8067`, `chidionyema/idp#6156`, `chidionyema/idp#3525`, `chidionyema/argon#82`, `chidionyema/argon#114`, `chidionyema/argon#139`

## Context

Two independent audits on 2026-11-28 converged on one structural diagnosis: the estate produces
architecture and code at high velocity, but stalls at settlement, synchronization, certification,
and retirement. Measured on the estate's own Greenlane tick (`idp#8759`, run `46130641052`):

- **110 landed lanes** sit in `recovery_required` and **0** pass operational certification because
  `greenlane/github.py` requires `EPISTEMIC-EFFECT-V1` receipts verified by symmetric HMAC secrets
  nothing produces or provisions, and symmetric HMAC cannot prove multi-principal independence.
- Cloud executor dispatch (`agent-sandbox-dispatch`, run `46132706055`) halted in
  `crates/meridian-fitness/src/main.rs` with `ESCALATE/1` on unset optional provider keys even when
  `SEED_OPENROUTER_API_KEY` had already passed `FIT (readiness-1)`.
- Surfaces across **Web, Desktop, Cloud, and Mobile** are disconnected: local NATS JetStream
  (`127.0.0.1:4222`, 8 streams, 78 consumers) shuts down or stays loopback-only; the cloud MCP door
  (`mcp.mumchimp.com` / `mcp.meridianlabs.cloud`) is unreachable (`000` / `525`); `runtimes.json`
  omits newer desktop/agent harnesses (`antigravity`, `kimi`); and `live.meridianlabs.cloud`
  (`estate-live-state.v1`, HTTP `200` on Zone B edge) and `llm.meridianlabs.cloud` (HTTP `200`)
  need clean, vendor-neutral bridges rather than single-vendor lock-in.

## Architectural Law: Locked Open Contracts, Open Infra Options (R43)

No plane may couple the estate to one cloud vendor or one device. Every plane locks an open wire
contract and keeps multiple hosting options swappable behind it:

1. **Messaging & Real-Time Comms (ADR 0012 + `estate-live-state.v1`):**
   - **NATS JetStream** remains the vendor-neutral durable message fabric (CloudEvents 1.0,
     `{domain}.{kind}.{aggregate}.{action}.{version}`, durable pull consumers, explicit ack,
     Mac leaf node syncing to an off-Mac hub — Synadia NGS free tier, OCI ARM A1, or k3s).
   - **`live.meridianlabs.cloud` (`EstateLiveStateDO`)** acts as a thin public edge snapshot &
     WebSocket fan-out projector (`seq` + `sha256` + explicit `BLIND`), bridged cleanly from
     JetStream via `platform/estate-live-state/scripts/nats-bridge.mjs` — never a proprietary
     replacement for the durable event bus.
2. **Identity & QUAD Authority (SPIFFE/SPIRE + Multi-Plane Attestation):**
   - `greenlane/github.py` mathematically requires **3 distinct principals across 3 distinct control
     planes** (`ERR_QUAD_CUSTODY_NOT_ISOLATED`). Multi-plane infra diversity is a QUAD security
     requirement.
   - Symmetric HMAC secrets (`EPISTEMIC_*`) are superseded in design by **asymmetric, short-lived,
     control-plane-issued attestations** (GitHub Actions OIDC + Sigstore/Rekor for landed proofs,
     **SPIFFE/SPIRE SVIDs** via `sovereign/trust/spiffe.py` on standalone ARM VM or k3s for running
     workloads with 3-missed-heartbeat ghost revocation, and `tempo-node` Ed25519 quorum / edge
     verifier for observed proofs).
   - **SPIRE does not require k3s:** standalone SPIRE Server + Agent on a single Linux/ARM VM
     provides full SVID attestation today and plugs into k3s later with zero contract change.
3. **Model Routing & Spend (`AGENTS.md §7a`):**
   - OpenAI + Anthropic wire contract with `gen_ai.*` OTel spans and per-lane budget ceilings.
   - Active cloud default: `https://llm.meridianlabs.cloud` (`meridian-router-edge`, Zone B edge).
   - Self-hosted Rust/Go gateway (`pennyd`) remains an open off-Mac/ARM/k3s option; laptop routing
     is strictly thin failover.
4. **Unified Memory & Cross-Surface Onboarding (`#6156`):**
   - One MCP door (`tools` + `resources`, 4 context kinds: `estate`, `catalog`, `constraint`,
     `workaround`) backed by `estate-graph` + `MITP consolidationd` (`#8803`).
   - `platform/estate/memory/runtimes.json` registers every active local harness (`claude-code`,
     `opencode`, `pi`, `cursor`, `gemini`, `codex`, `antigravity`, and `kimi` as adapters land),
     while `meridian-membrane` covers Web AI surfaces.

## Ratified Founder Rulings (D1–D11, 2026-11-28)

| # | Ruling | Ratified Direction |
|---|---|---|
| D1 | Programme priority | P0 over mandate feature order until connective tissue + settlement operate; collapse onto open contracts so surfaces connect immediately. |
| D2 | Distiller budget tier | Enforce minimal budget ceiling on the cloud router contract (`llm.meridianlabs.cloud` active now; portable to self-hosted gateway — never laptop-only). |
| D3 | PR queue triage | Triage instead of blanket hand-merge: security hygiene (`argon#139`), `consolidationd` (`idp#8803`), `#8430`; retire stale Nov 13–15 branches; let Greenlane land `idp`. |
| D4 | Agent-to-agent comms | Permitted on provisioned, receipted channels over ADR 0012 envelopes (off-Mac JetStream + `live.meridianlabs.cloud` bridge). |
| D5 | Mandate §11 operating instruction | Delegated to hardened Council v1's first receipted deliberation, gated on founder sign-off. |
| D6 | Certification ladder | AL-0→AL-5 with pass^k gates and error-budget auto-demotion adopted as certification law. |
| D7 | Beast assembly & authority kernel | Assemble existing organs; promote `tempo-node` Ed25519 quorum/time-lock contract as authority kernel integrated with SPIFFE/QUAD. |
| D8 | AI Studio frontier sync | Top-5 apps first (`estate-sovereign`, `control-plane`, `omega-codex`, `mnemosyne`, `kimi-capability-engine`) + `#8702` outbox bridge. |
| D9 | Council v1 seats | Kimi, ChatGPT/Codex, Gemini/Carbon (API), Claude where entitled; trigger-gated, abstention-not-failure, publishing to the shared live ledger. |
| D10 | Legacy gravity wells | Mass-close frozen planes (`haworks-platform`, legacy `crew` / `prospector` backlog) with archive pointers. |
| D11 | Epistemic / QUAD custody | Three distinct principals and control planes; graduate from static keys to asymmetric OIDC + SPIFFE/SPIRE + `tempo-node` quorum (zero static verifier secrets). |

## Consequences

- Any single cloud vendor (Cloudflare, OCI, GitHub, Synadia) can be replaced without rewriting
  agent harnesses, messaging contracts, QUAD verifiers, or founder surfaces.
- Guarded-path edits (`.github/workflows/`, `AGENTS.md`, `greenlane/github.py` seal transitions)
  follow the existing founder-sealed process; all non-guarded implementation slices land through
  normal single-subsystem `lane/*` submissions with falsifiers.
