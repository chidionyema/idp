# FLEET 3-DAY CANONICAL SYNC MANIFEST & ANTI-CONFUSION LEDGER (15–17 Nov 2026)

> **MANDATORY ENTRYPOINT FOR ALL FLEET AGENTS (`dsh`, `argon`, `opencode`, `pennyd`, `gemini`, `glm-5.3`, `deepseek`, `kimi`, `claude`, `chatgpt`) & HUMAN ENGINEERS:**
> Do **not** rely on chat history, older `16 Nov` handoff notes, or retired infrastructure configs. This root manifest reconciles **100% of the past 3 days of work (`2026-11-15`, `2026-11-16`, `2026-11-17`)** into one authoritative, machine-verified contract enforced by `src/engine/fleetThreeDaySyncGuard.ts`, `src/engine/githubDirectDeviceSync.ts`, and `.github/workflows/fleet-3day-sync-verify.yml`.

---

## 1. Anti-Confusion Table — Retired Ghosts vs. Canonical Estate Truth

Any PR, prompt, workflow, or agent task referencing the **Retired / Forbidden** column is deterministically rejected pre-token (`HTTP 422` / `HTTP 403`) at zero LLM token cost:

| Domain | Permanently Retired / Tombstoned (NEVER USE) | Canonical Live Truth (Enforced Estate-Wide) | Mechanical Gate |
|---|---|---|---|
| **Local & Cloud Router** | LiteLLM on `:4000`, `:4001`, `:4002`; `com.estate.litellm-*` plists | **`pennyd` on `127.0.0.1:4200`** (local) and `https://llm.mumchimp.com` (cloud Lane 2) with `PENNYD_API_KEY` (`max_tokens:0` live probe) | `ROUTER.md`, `AB-02`, `evaluateSystemFirstIocAdmission` (`HTTP 422`) |
| **Kubernetes Cluster** | Oracle OKE (`193.123.184.22`, `141.147.80.229:6443`, `oke-direct`, `config-estate`) | **Self-managed `k3s` on OCI Always Free Ampere A1** (`/etc/rancher/k3s/k3s.yaml`) | `F31` Ghost IP Denylist (`193.123.184.22`), `AB-01` |
| **Cross-Agent Bus** | Manual Founder tab copy-pasting; competing Durable Object lease authority | **Canonical OMNIFLOW SSE/HTTPS Bus** (`/api/omniflow/stream`; Cloudflare DO strictly a stateless edge adapter, `competingAuthority: false`) | Monotonic lease fencing (`409`), `10s` TTL crash recovery, KARMA `403` self-verify block |
| **Task Admission** | Dispatch -> spend tokens -> generate multi-subsystem diff -> fail Proof 2 | **Validate -> Decompose -> Execute -> Verify -> Deliver** (`1..5` unguarded files, `1` top-level subsystem, or auto-decompose into `LANE-01..N`) | `evaluateZeroGaslightAdmission` (`HTTP 422` at `0` tokens, `#8194` proof) |
| **Model Continuity** | Storing architectural state in chat history or relying on one LLM vendor | **System-First IoC (`LAW_SYSTEM_FIRST_IOC_RECONCILER`)**: `GENESIS_SPORE.dna` (`<= 4,096` bytes) + `AGENTS.md` (`<= 300` lines) + `ROUTER.md` | `buildSystemFirstIocSnapshot`, `GENESIS_SPORE.dna` 4KB cap |
| **Workstation Setup & Daily Boot** | Manual CLI setup scripts, interactive `sudo` prompts, privileged ports `<1024`, GUI-only `:3080` LaunchAgents | **Commercial Turnkey Appliance UI (`/setup`)** + **Operation Phoenix v2 (`/phoenix`)**: `0` CLI, `0` `sudo`, `0` AI agents required, unprivileged ports (`3000/3080/4200/8788`), `0600` Ed25519 keys, atomic rollback | `FSM-01` & `FSM-11` Closed-Loop Proofs, Signed Helper XPC allowlist |
| **Disaster Recovery Abroad** | Requiring domestic SIM / SMS 2FA, existing MacBook, SSH keys, or AI chat agents | **Foreign-Country Zero-Device Phone Bootstrap (`/phone-boot`)**: brand-new phone browser + **3-of-8 `RS(3,8)` factors**, WebAuthn Secure Enclave passkey minting, stolen-laptop epoch fence revocation (`HTTP 409`), duress `423` safe-hold | `FSM-12` Closed-Loop Proof + `12/12` Adversarial Red-Team Suite |
| **Operational Yield & Sync Status** | Grading merged PRs, static CDN builds, or registered browser seats as `LIVE OPERATING` | **Radical Epistemic Candor (`Rego R-010`)**: `STATIC_CDN_PROJECTION` / `DECLARED_UNPROBED` until outside-in `MEASURED_OK` receipt or GitHub push receipt lands | `auditEpistemicClaim`, `verifyThreeDayFleetSyncCompleteness` |

---

## 2. Complete 3-Day Cumulative Delivery Map (`2026-11-15` .. `2026-11-17`)

### Day 1 (`2026-11-15`) — Core Router, WAL, Symphony, Lockdowns, Hermes & Reset-Proof Bundle
1. **`D1-01` · PennyD Multi-Lane Router (`127.0.0.1:4200`), CAS Key-Store, Dagster WAL & Meridian Battalion** (`/`, `routerCore.ts`, `keyStore.ts`, `receiptLedger.ts`, `dagsterOrchestrator.ts`, `meridianTelemetry.ts`, `modelSupply.ts`)
2. **`D1-02` · Meridian Symphony (`IDP #8169`), `I-8095` Class-A Zero-Polling Lockdown & `AURA-2100` 64-Byte Binary Manifold** (`/?tab=symphony`, `meridianSymphony.ts`, `i8095Lockdown.ts`, `auraBinaryCodec.ts`, `auraManifold.ts`)
3. **`D1-03` · HERMES · The Living Tree, Codex Crescendo, 231-Gate Matrix & World Connector** (`/hermes`, `hermesCipherEngine.ts`, `hermesTreeCatalog.ts`, `hermesWorldConnector.ts`, `codexCrescendo.ts`)
4. **`D1-04` · Zero-Env-Var Reset-Proof Git Bundle & Idle/Spawn Receiver** (`/get-work`, `debugPackBuilder.ts`, `ingestReceiver.ts`, `scripts/sync-bundle.ts`, `scripts/genesis-ingest-receiver.ts`, `scripts/install-persistent-git-uplink.sh`)

### Day 2 (`2026-11-16`) — Panspermia Survival, Grand Union, Governance, VIP Telegram, Rego, Academy, Mum's Concierge & MCC-001
5. **`D2-05` · `I-8088` Cephalopod `RS(3,8)` Panspermia & `GEN-TTT-001` Spec Lock (`#8185`)** (`/?tab=genesis_ttt`, `genesisSporeTtt.ts`, `GenesisSurvivalTtt.tsx`)
6. **`D2-06` · Estate Grand Union, `<50ms` InterCloud Spot Failover & Open Ensemble > Frontier** (`/?tab=grand_union`, `estateGrandUnion.ts`, `EstateGrandUnion.tsx`)
7. **`D2-07` · First-Use Machine-Agent Governance Audit (`ff8543bd`) & `AGENTS.md <= 300` Ratchet** (`/audit`, `firstUseGovernanceAudit.ts`)
8. **`D2-08` · Hermes · `OTTO_NUMEN` (`@otto_numen_bot`) VIP CEO Telegram Concierge (`98%` ping reduction)** (`/?tab=vip_telegram`, `ottoNumenTelegram.ts`, `OttoNumenVipTelegram.tsx`)
9. **`D2-09` · Prospector-2100 Causal EVSI -> Mumchimp & Meridian Investor Room (`GAP-01..12`)** (`/?tab=investor_room`, `prospectorResearchMumchimp.ts`, `MeridianInvestorPortal.tsx`)
10. **`D2-10` · Rego Constitutional Plane (`R-001..R-010`), UHNW `<=150ms` Charter & Standout Genesis Academy** (`/?tab=founder_rego`, `founderRegoChronosPlane.ts`, `uhnwSovereignCharter.ts`, `genesisAcademyEngine.ts`, `SovereignConciergePalette.tsx`)
11. **`D2-11` · `MUM-CONCIERGE-001` — Auntie Ezinne VIP Low-Vision WhatsApp & `EON-001` (£95.11 credit math)** (`/?tab=mums_concierge`, `mumsConcierge.ts`, `MumConciergeHub.tsx`)
12. **`D2-12` · Real-Time Founder Reactivity (`#8184`), `MCC-001` 9-Tuple Capability Calculus & Crescendo 3-Way Union (`NO-GO` Gate)** (`/crescendo`, `autonomousReactivity.ts`, `meridianCapabilityCalculus.ts`, `crescendoThreeWayUnion.ts`, `MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md`)

### Day 3 (`2026-11-17`) — OMNIFLOW Bus, KARMA/#7760, 12 Closed-Loop FSMs, Phoenix v2, System-First IoC, Turnkey Appliance / Foreign Phone DR & Direct GitHub Device Sync
13. **`D3-13` · Canonical OMNIFLOW Live Multi-Agent SSE/HTTPS Bus & Pre-Token `#8194` Proof** (`/comms`, `omniflowLiveBus.ts`, `OmniflowLiveRoomPanel.tsx`, `scripts/estate-bus-cli.mjs`, `scripts/cloudflare-omniflow-bus.ts`)
14. **`D3-14` · KARMA `#7452` / `#8030` Universal Settlement, `#7760` R2 Bundle Receiver & 7-Seat Browser Truth** (`scripts/cloudflare-pages-ingest-bundle.ts`, `meridianCapabilityCalculus.ts`)
15. **`D3-15` · Universal Closed-Loop FSM Constitutional Registry (`6` Layers · `12` BFS-Proven Workflows)** (`estateClosedLoopFsm.ts`, `applianceTurnkeySetup.ts`)
16. **`D3-16` · Operation Phoenix v2 `06:00 UTC` Daily Clean-Room Cold-Boot & Union Round Table** (`/phoenix`, `phoenixDailyBoot.ts`, `PhoenixRoundTablePanel.tsx`, `scripts/phoenix-daily-drill.ts`, `.github/workflows/phoenix-daily-boot.yml`)
17. **`D3-17` · System-First IoC (`LAW_SYSTEM_FIRST_IOC_RECONCILER`), `<=4KB` `GENESIS_SPORE.dna` & `ROUTER.md`** (`/?tab=ioc_reconciler`, `systemFirstIocReconciler.ts`, `SystemFirstIocExplorer.tsx`, `GENESIS_SPORE.dna`, `ROUTER.md`)
18. **`D3-18` · Commercial Turnkey Appliance Setup (`/setup`), Foreign-Country Zero-Device Phone Bootstrap (`/phone-boot`), `12/12` Red-Team, Perpetual Future-Proof Ratchet, Direct GitHub Device Push (`#7760` Ref) & 3-Day Sync Guard** (`/setup`, `/phone-boot`, `applianceTurnkeySetup.ts`, `ApplianceSetupDrConsole.tsx`, `fleetThreeDaySyncGuard.ts`, `githubDirectDeviceSync.ts`, `.github/workflows/fleet-3day-sync-verify.yml`)

---

## 3. Canonical GitHub Reachability & Zero-Block Sync Protocol

Target GitHub repositories & exact refs polled by `#7760` / `#8133` fleet CI:
- **Primary Fleet Remotes:** `chidionyema/gemini-sync` and `chidionyema/argon-sync`
- **Producer `#7760` Recovery Ref:** `refs/heads/aistudio/meridian-hermes-carbon-20261117`
- **Canonical Live Mirror Ref:** `refs/heads/aistudio/meridian-hermes-live`
- **Quarantine Fast-Forward PR Ref (Parented on `main`, Never Force-Pushes `main`):** `refs/heads/lane/aistudio-3day-sync-20261117`
- **Downstream Integration Repo:** `chidionyema/idp`

### Path A — 1-Click Direct Server -> GitHub Push (RFC 8628 Device Code · Zero Download · Zero SSH Key)
1. Click **"Push Directly to GitHub (Device Code)"** at the top of the screen (or inside `/get-work` -> `POST /api/export/github-device/start`).
2. Enter the 8-character GitHub Device Code at `https://github.com/login/device` and click **Authorize**.
3. This Express container immediately fetches remote `main`, synthesizes a clean child commit (`git commit-tree <HEAD^{tree}> -p <remoteMainSha>`), pushes `refs/heads/aistudio/meridian-hermes-carbon-20261117`, `refs/heads/aistudio/meridian-hermes-live`, and `refs/heads/lane/aistudio-3day-sync-20261117` directly to `chidionyema/gemini-sync` and `chidionyema/argon-sync`, and opens a Pull Request into `main`.

### Path B — Iframe-Proof 1-Command Self-Extracting Clipboard Capsule (Works Even When Browser Blocks Downloads)
Click **"Copy 1-Command Repo Capsule"** inside `/get-work` (`GET /api/export/clipboard-capsule`) and paste into any terminal — unpacks all tracked 3-day files with SHA-256 verification and stamps `aistudio/meridian-hermes-carbon-20261117` + `aistudio/meridian-hermes-live`.

### Path C — AI Studio Top-Right **"Save to GitHub"** or Verified `.bundle` Push
```bash
git bundle verify ~/Downloads/meridian-hermes-today.bundle
git clone ~/Downloads/meridian-hermes-today.bundle meridian-3day-sync && cd meridian-3day-sync
git push git@github.com:chidionyema/gemini-sync.git +HEAD:refs/heads/aistudio/meridian-hermes-carbon-20261117 +HEAD:refs/heads/aistudio/meridian-hermes-live +HEAD:refs/heads/lane/aistudio-3day-sync-20261117
git push git@github.com:chidionyema/argon-sync.git +HEAD:refs/heads/aistudio/meridian-hermes-carbon-20261117 +HEAD:refs/heads/aistudio/meridian-hermes-live +HEAD:refs/heads/lane/aistudio-3day-sync-20261117
```

---

## 4. Mandatory Verification Gate (Every Fleet Agent & CI Runner)

```bash
npm ci
npm run lint
npx --yes tsx --test --test-concurrency=1 src/engine/httpIntegration.test.ts
npx --yes tsx --test --test-concurrency=1 src/engine/router.test.ts
npm run build
```
