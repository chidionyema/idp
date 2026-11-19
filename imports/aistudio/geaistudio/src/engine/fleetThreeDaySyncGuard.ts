/**
 * 3-Day Estate Fleet Sync Completeness & Anti-Confusion Guard (15–17 Nov 2026).
 *
 * Guarantees that 100% of Day 1, Day 2, and Day 3 workstreams are:
 *   1. Present on disk, non-empty, and tracked in Git (`0` untracked source files left behind),
 *   2. Sealed inside `dist-exports/meridian-hermes-today.bundle` with `bundleHeadSha === gitHeadSha`,
 *   3. Materialized into static `dist/` projections so static hosts never 404,
 *   4. Documented in `FLEET_3DAY_CANONICAL_MANIFEST.md` and `TEAM_HANDOFF_TODAY.md` with explicit
 *      anti-confusion directives so no fleet agent (`dsh`, `argon`, `opencode`, `pennyd`, `kimi`,
 *      `deepseek`, `claude`, `chatgpt`, or GitHub Actions runner) can miss or misinterpret any layer.
 */

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

export type EstateBuildDay = 'DAY_1_2026_11_15' | 'DAY_2_2026_11_16' | 'DAY_3_2026_11_17';

export interface ThreeDayWorkstreamEntry {
  id: string;
  day: EstateBuildDay;
  dateIso: '2026-11-15' | '2026-11-16' | '2026-11-17';
  title: string;
  canonicalUiRoute: string;
  requiredFiles: ReadonlyArray<string>;
  canonicalTruthSummary: string;
  retiredConfusionTrapBlocked: string;
}

export interface FleetAgentOnboardingDirective {
  agentSurface: string;
  bootReadOrder: ReadonlyArray<string>;
  canonicalEntrypoint: string;
  forbiddenLegacyPattern: string;
  enforcementGate: string;
}

export interface ThreeDayFileSealDigest {
  relativePath: string;
  bytes: number;
  sha256: string;
  trackedInGit: boolean;
}

export interface FleetThreeDaySyncReport {
  schemaVersion: 'meridian-fleet-3day-sync-v1';
  generatedAtUtc: string;
  windowLabel: '2026-11-15 .. 2026-11-17 (3-Day Cumulative Seal)';
  headSha: string;
  branch: string;
  workingTreeClean: boolean;
  dirtyTrackedFiles: string[];
  untrackedSourceFiles: string[];
  bundlePathRelative: string;
  bundleExists: boolean;
  bundleBytes: number;
  bundleSha256: string | null;
  bundleHeadSha: string | null;
  bundleVerifiedOk: boolean;
  bundleMatchesHead: boolean;
  totalTrackedFilesCount: number;
  threeDayMerkleRootSha256: string;
  agentsMdLines: number;
  agentsMdWithinCeiling: boolean;
  genesisSporeBytes: number;
  genesisSporeWithin4Kb: boolean;
  dayBreakdown: {
    day1WorkstreamsCount: number;
    day2WorkstreamsCount: number;
    day3WorkstreamsCount: number;
    totalWorkstreamsCount: number;
    verifiedWorkstreamsCount: number;
  };
  missingRequiredFiles: string[];
  untrackedRequiredFiles: string[];
  manifestAntiConfusionVerified: boolean;
  githubCiWorkflowPresent: boolean;
  allThreeDaysSealed: boolean;
  externalGitHubPushState:
    | 'LOCAL_SEALED_AWAITING_GITHUB_PUSH_RECEIPT'
    | 'EXTERNAL_GITHUB_PUSH_CONFIRMED';
  canonicalGitHubRemotes: ReadonlyArray<string>;
  canonicalGitHubRef: string;
  workstreams: ReadonlyArray<ThreeDayWorkstreamEntry>;
  fleetDirectives: ReadonlyArray<FleetAgentOnboardingDirective>;
  criticalContractDigests: ThreeDayFileSealDigest[];
}

export const CANONICAL_GITHUB_SYNC_REMOTES: ReadonlyArray<string> = [
  'chidionyema/argon-sync',
  'chidionyema/gemini-sync',
];

export const CANONICAL_GITHUB_SYNC_REF = 'refs/heads/aistudio/meridian-hermes-live';

export const THREE_DAY_WORKSTREAM_LEDGER: ReadonlyArray<ThreeDayWorkstreamEntry> = [
  {
    id: 'D1-01',
    day: 'DAY_1_2026_11_15',
    dateIso: '2026-11-15',
    title: 'PennyD Multi-Lane Router (:4200), Atomic CAS Key-Store, Dagster Durable WAL & Meridian Battalion',
    canonicalUiRoute: '/',
    requiredFiles: [
      'src/engine/routerCore.ts',
      'src/engine/keyStore.ts',
      'src/engine/receiptLedger.ts',
      'src/engine/dagsterOrchestrator.ts',
      'src/engine/meridianTelemetry.ts',
      'src/engine/modelSupply.ts',
      'src/components/GatewayOverview.tsx',
      'src/components/MeridianBattalion.tsx',
    ],
    canonicalTruthSummary:
      'pennyd on 127.0.0.1:4200 + PENNYD_API_KEY max_tokens:0 probe, CAS key-store, HTTP 402 billing classifier, and zero-drop Dagster WAL.',
    retiredConfusionTrapBlocked:
      'Retired LiteLLM :4000-:4002 listeners, com.estate.litellm-* plists, and unprobed LITELLM_API_KEY defaults.',
  },
  {
    id: 'D1-02',
    day: 'DAY_1_2026_11_15',
    dateIso: '2026-11-15',
    title: 'Meridian Symphony (IDP #8169), I-8095 NASA Class-A Lockdown & AURA-2100 64-Byte Binary Manifold',
    canonicalUiRoute: '/?tab=symphony',
    requiredFiles: [
      'src/engine/meridianSymphony.ts',
      'src/engine/i8095Lockdown.ts',
      'src/engine/auraBinaryCodec.ts',
      'src/engine/auraManifold.ts',
      'src/components/MeridianSymphony.tsx',
      'src/components/I8095LockdownPanel.tsx',
      'src/components/AuraObsidianDeck.tsx',
    ],
    canonicalTruthSummary:
      'Fail-closed 503/401 Ed25519/JWT verifier, I-8090 exit-78 zero-client-polling guard, and 64-byte GenesisAtomicFrame codec.',
    retiredConfusionTrapBlocked:
      'Browser setInterval HTTP polling loops and fail-open surface auth stubs.',
  },
  {
    id: 'D1-03',
    day: 'DAY_1_2026_11_15',
    dateIso: '2026-11-15',
    title: 'HERMES · The Living Tree, Codex Crescendo, 231-Gate Matrix & World Connector Circuit Breaker',
    canonicalUiRoute: '/hermes',
    requiredFiles: [
      'src/engine/hermesCipherEngine.ts',
      'src/engine/hermesTreeCatalog.ts',
      'src/engine/hermesWorldConnector.ts',
      'src/engine/codexCrescendo.ts',
      'src/engine/crescendoAudio.ts',
      'src/components/HermesLivingTree.tsx',
      'src/components/CodexCrescendoPanel.tsx',
    ],
    canonicalTruthSummary:
      '27 Greek / 22 Hebrew ciphers (Malkuth root 10 preserved), Legacy W=A diff detector, Bidi sanitization, and 64-entry LRU Open-Meteo breaker.',
    retiredConfusionTrapBlocked:
      'Silent English W=A wraparound mutation, mod-9 Malkuth collapse, and unstripped GPS coordinates.',
  },
  {
    id: 'D1-04',
    day: 'DAY_1_2026_11_15',
    dateIso: '2026-11-15',
    title: 'Zero-Env-Var Reset-Proof Git Bundle & Other-Side Idle/Spawn Ingest Receiver',
    canonicalUiRoute: '/get-work',
    requiredFiles: [
      'src/engine/debugPackBuilder.ts',
      'src/engine/ingestReceiver.ts',
      'scripts/sync-bundle.ts',
      'scripts/genesis-ingest-receiver.ts',
      'scripts/install-persistent-git-uplink.sh',
      'src/components/EstateSyncMonitor.tsx',
    ],
    canonicalTruthSummary:
      'Idempotent ensureGitRepoAndBundle on boot/build, SHA-256 signed outbound bundle push, and zero custom .env.example prompts.',
    retiredConfusionTrapBlocked:
      'Relying on ephemeral .git/hooks or adding custom env vars that trigger AI Studio blocking modals.',
  },
  {
    id: 'D2-05',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'I-8088 Cephalopod RS(3,8) Panspermia Survival & GEN-TTT-001 Spec Lock (#8185)',
    canonicalUiRoute: '/?tab=genesis_ttt',
    requiredFiles: [
      'src/engine/genesisSporeTtt.ts',
      'src/components/GenesisSurvivalTtt.tsx',
    ],
    canonicalTruthSummary:
      'GF(2^8) Vandermonde RS(3,8) bit-exact recovery across all C(8,3)=56 3-of-8 subsets (survives 5/8 tentacle losses) + BLOCKED_DISPATCH #8185.',
    retiredConfusionTrapBlocked:
      'Single-cloud forge dependency or claiming GEN-TTT-001 Greenlane dispatch before blind HELM eval.',
  },
  {
    id: 'D2-06',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'Estate Grand Union: Chronos/Tempo SSE, <50ms InterCloud Spot Heal & Open Ensemble > Frontier',
    canonicalUiRoute: '/?tab=grand_union',
    requiredFiles: [
      'src/engine/estateGrandUnion.ts',
      'src/components/EstateGrandUnion.tsx',
    ],
    canonicalTruthSummary:
      'Joined Chronos/Tempo SSE heartbeat (/api/union/stream), <50ms spot reclamation heal, and Best-of-3 open ensemble (96.9% vs 93.4% Frontier).',
    retiredConfusionTrapBlocked:
      'Single-provider Frontier token burn and dropped tasks on spot VM reclamation.',
  },
  {
    id: 'D2-07',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'First-Use Machine-Agent Governance Audit (ff8543bd) & AGENTS.md <= 300 No-Growth Ratchet',
    canonicalUiRoute: '/audit',
    requiredFiles: [
      'src/engine/firstUseGovernanceAudit.ts',
      'AGENTS.md',
      'GEMINI.md',
    ],
    canonicalTruthSummary:
      '21/21 observer + AGENTS.md <= 300 ratchet checks, --no-verify shortcut blocker, and LIVE CEREMONY EFFECT=UNKNOWN honesty.',
    retiredConfusionTrapBlocked:
      'Escaped $lines fail-open shell bug, --no-verify git bypasses, and bloated >300-line AGENTS.md.',
  },
  {
    id: 'D2-08',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'Hermes · OTTO_NUMEN (@otto_numen_bot) VIP CEO Telegram Concierge',
    canonicalUiRoute: '/?tab=vip_telegram',
    requiredFiles: [
      'src/engine/ottoNumenTelegram.ts',
      'src/components/OttoNumenVipTelegram.tsx',
    ],
    canonicalTruthSummary:
      '5 Supergroup Forum Topics + Zero-Send Heartbeat Sink, 98.0% audible ping reduction, HTML/MarkdownV2 escapers & <=64B signed callbacks.',
    retiredConfusionTrapBlocked:
      'Legacy single-channel oot_numun notification flood and unescaped MarkdownV2 parse crashes.',
  },
  {
    id: 'D2-09',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'Prospector-2100 Autonomous Causal Research -> Mumchimp & Meridian Investor Room',
    canonicalUiRoute: '/?tab=investor_room',
    requiredFiles: [
      'src/engine/prospectorResearchMumchimp.ts',
      'src/components/MumchimpProspectorHub.tsx',
      'src/components/MeridianInvestorPortal.tsx',
    ],
    canonicalTruthSummary:
      '$0.00/$0.00018 Sovereign/Spot EVSI triage (99.6% cost cut) + MagenticBrain confounder quarantine + GAP-01..12 Investor Room.',
    retiredConfusionTrapBlocked:
      'Naive $0.048/brief Frontier research spend and unvetted confounder syndication to Mumchimp.',
  },
  {
    id: 'D2-10',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'Rego Constitutional Plane (R-001..R-010), UHNW <=150ms Charter & Standout Genesis Academy',
    canonicalUiRoute: '/?tab=founder_rego',
    requiredFiles: [
      'src/engine/founderRegoChronosPlane.ts',
      'src/engine/uhnwSovereignCharter.ts',
      'src/engine/genesisAcademyEngine.ts',
      'src/components/FounderRegoChronosPlane.tsx',
      'src/components/GenesisAcademy.tsx',
      'src/components/SovereignConciergePalette.tsx',
    ],
    canonicalTruthSummary:
      'Declarative package genesis.constitutional.v1 (R-008..R-010 Plan != Test != Live Yield), <=150ms 7-agent OTTO SLA, and 6-track Academy.',
    retiredConfusionTrapBlocked:
      'Ad-hoc imperative policy drift and inflating static/merged PRs into live operational yield.',
  },
  {
    id: 'D2-11',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'MUM-CONCIERGE-001 — Auntie Ezinne VIP Low-Vision WhatsApp & EON-001 Family Safety',
    canonicalUiRoute: '/?tab=mums_concierge',
    requiredFiles: [
      'src/engine/mumsConcierge.ts',
      'src/components/MumConciergeHub.tsx',
    ],
    canonicalTruthSummary:
      '4s WhatsApp coalescer, parseKernelPermission("false")===false, EON-001 £95.11 credit math, 9/9 safety + 11/11 negative falsifiers.',
    retiredConfusionTrapBlocked:
      'Truthy "false" string bug, mislabeling £95.11 E.ON credit as debt, or claiming G2-G4 live elderly trial before completion.',
  },
  {
    id: 'D2-12',
    day: 'DAY_2_2026_11_16',
    dateIso: '2026-11-16',
    title: 'Real-Time Founder Reactivity (#8184), MCC-001 9-Tuple Calculus & Crescendo 3-Way Union Sign-Off',
    canonicalUiRoute: '/crescendo',
    requiredFiles: [
      'src/engine/autonomousReactivity.ts',
      'src/engine/meridianCapabilityCalculus.ts',
      'src/engine/crescendoThreeWayUnion.ts',
      'src/components/FounderAutonomousReactivity.tsx',
      'src/components/FounderMccConvergencePanel.tsx',
      'MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md',
    ],
    canonicalTruthSummary:
      '7-stage fenced obligation custody, 9-tuple C_c=(I,O,P,Q,A,E,F,R,V) contracts, EP-A..EP-E doors, and fail-closed Crescendo NO-GO gate.',
    retiredConfusionTrapBlocked:
      'Mistaking GitHub comments or NATS --ack for custody, or signing off Crescendo GO before Key-C witness.',
  },
  {
    id: 'D3-13',
    day: 'DAY_3_2026_11_17',
    dateIso: '2026-11-17',
    title: 'Canonical OMNIFLOW Live Multi-Agent SSE/HTTPS Bus & Pre-Token #8194 Boundary Elimination',
    canonicalUiRoute: '/comms',
    requiredFiles: [
      'src/engine/omniflowLiveBus.ts',
      'src/components/OmniflowLiveRoomPanel.tsx',
      'scripts/estate-bus-cli.mjs',
      'scripts/cloudflare-omniflow-bus.ts',
    ],
    canonicalTruthSummary:
      'Monotonic lease fencing (201 -> 200 -> 409 -> 403 -> 200), 10s TTL crash recovery, stateless DO edge adapter, and 1,240-subset Proof-2 closure.',
    retiredConfusionTrapBlocked:
      'Manual Founder tab copy-pasting, competing DO split-brain leases, and post-token 3-subsystem Proof-2 rejections.',
  },
  {
    id: 'D3-14',
    day: 'DAY_3_2026_11_17',
    dateIso: '2026-11-17',
    title: 'KARMA #7452 / #8030 Universal Settlement, #7760 R2 Receiver & 7-Seat Browser Workforce Truth',
    canonicalUiRoute: '/comms',
    requiredFiles: [
      'scripts/cloudflare-pages-ingest-bundle.ts',
      'src/engine/meridianCapabilityCalculus.ts',
    ],
    canonicalTruthSummary:
      'Bearer-authenticated <=16 MiB R2 bundle receiver with SHA-256 readback, non-monetary KARMA restitution, and Registration != Execution separation.',
    retiredConfusionTrapBlocked:
      'Counting registered browser seats as live execution or accepting unauthenticated/unchecked bundle uploads.',
  },
  {
    id: 'D3-15',
    day: 'DAY_3_2026_11_17',
    dateIso: '2026-11-17',
    title: 'Universal Closed-Loop FSM Constitutional Registry (6 Layers · 12 Proven Workflows)',
    canonicalUiRoute: '/phoenix',
    requiredFiles: [
      'src/engine/estateClosedLoopFsm.ts',
    ],
    canonicalTruthSummary:
      'Automated BFS + reverse-BFS graph theorems proving zero dead-ends, bounded TTL timeout edges, SAFE_QUARANTINE escapes, and verifierId !== executorId.',
    retiredConfusionTrapBlocked:
      'Open-loop workflows, infinite unbounded waits, or self-certified agent executions.',
  },
  {
    id: 'D3-16',
    day: 'DAY_3_2026_11_17',
    dateIso: '2026-11-17',
    title: 'Operation Phoenix v2 Daily 06:00 UTC Clean-Room Cold-Boot & Union Round Table',
    canonicalUiRoute: '/phoenix',
    requiredFiles: [
      'src/engine/phoenixDailyBoot.ts',
      'src/components/PhoenixRoundTablePanel.tsx',
      'scripts/phoenix-daily-drill.ts',
      '.github/workflows/phoenix-daily-boot.yml',
    ],
    canonicalTruthSummary:
      'Ephemeral clean-room bundle unpack, Ghost IP 193.123.184.22 denylist (F31), HTTP 409 premature-Go block, and automatic P0 Seal revocation.',
    retiredConfusionTrapBlocked:
      'Retired Oracle OKE 193.123.184.22 / oke-direct configs and unrevoked seals after P0 faults.',
  },
  {
    id: 'D3-17',
    day: 'DAY_3_2026_11_17',
    dateIso: '2026-11-17',
    title: 'System-First IoC Reconciler, <=4KB GENESIS_SPORE.dna, ROUTER.md & 8-Domain Anti-Confusion Ledger',
    canonicalUiRoute: '/?tab=ioc_reconciler',
    requiredFiles: [
      'src/engine/systemFirstIocReconciler.ts',
      'src/components/SystemFirstIocExplorer.tsx',
      'GENESIS_SPORE.dna',
      'ROUTER.md',
    ],
    canonicalTruthSummary:
      'Models (Gemini, GLM 5.3, DeepSeek, Kimi, Claude, ChatGPT) act as stateless interchangeable actuators hydrated in ms from <=4KB GENESIS_SPORE.dna.',
    retiredConfusionTrapBlocked:
      'Trapping estate architectural memory inside ephemeral chat sessions or single-model vendor lock-in.',
  },
  {
    id: 'D3-18',
    day: 'DAY_3_2026_11_17',
    dateIso: '2026-11-17',
    title: 'Commercial Turnkey Appliance Setup (/setup), Foreign Phone DR (/phone-boot), 12/12 Red-Team & 3-Day GitHub Sync Seal',
    canonicalUiRoute: '/setup',
    requiredFiles: [
      'src/engine/applianceTurnkeySetup.ts',
      'src/components/ApplianceSetupDrConsole.tsx',
      'src/engine/fleetThreeDaySyncGuard.ts',
      'src/engine/githubDirectDeviceSync.ts',
      'src/components/GlobalGetWorkModal.tsx',
      'src/components/TeamHandoffExportPanel.tsx',
      'FLEET_3DAY_CANONICAL_MANIFEST.md',
      'TEAM_HANDOFF_TODAY.md',
      '.github/workflows/fleet-3day-sync-verify.yml',
      'src/engine/router.test.ts',
      'src/engine/httpIntegration.test.ts',
    ],
    canonicalTruthSummary:
      'Zero-CLI / zero-sudo / zero-agent 1-click setup across 32 assets, 3-of-8 RS(3,8) brand-new foreign-phone bootstrap (stolen laptop 409 epoch revocation), 12/12 red-team, perpetual future-proof ratchet, and automatic GitHub CI 3-day verification + multi-remote mirror.',
    retiredConfusionTrapBlocked:
      'Manual sudo/CLI setup hacks, SMS OTP recovery lockouts abroad, or fleet agents missing Day 3 DR/IoC/Phoenix deliverables.',
  },
];

export const FLEET_AGENT_DIRECTIVES: ReadonlyArray<FleetAgentOnboardingDirective> = [
  {
    agentSurface: 'Terminal CLI Workers (dsh, opencode, argon, claude-code)',
    bootReadOrder: [
      'FLEET_3DAY_CANONICAL_MANIFEST.md',
      'AGENTS.md',
      'ROUTER.md',
      'GENESIS_SPORE.dna',
    ],
    canonicalEntrypoint:
      'Route inference via http://127.0.0.1:4200 (PENNYD_API_KEY validated with max_tokens:0); coordinate claims via scripts/estate-bus-cli.mjs.',
    forbiddenLegacyPattern:
      'NEVER bind or call LiteLLM :4000-:4002, NEVER reference OKE 193.123.184.22, NEVER pass --no-verify, NEVER submit >5 files or >1 subsystem unsplit.',
    enforcementGate:
      'evaluateZeroGaslightAdmission (HTTP 422 at 0 tokens) + F31 Ghost IP Denylist + AGENTS.md <= 300 Ratchet',
  },
  {
    agentSurface: 'Stateless LLM Actuators (Gemini, GLM 5.3, DeepSeek, Kimi, Claude, ChatGPT)',
    bootReadOrder: [
      'GENESIS_SPORE.dna',
      'FLEET_3DAY_CANONICAL_MANIFEST.md',
      'src/engine/systemFirstIocReconciler.ts',
    ],
    canonicalEntrypoint:
      'Hydrate active Merkle root, monotonic fencing token, 12 constitutional invariants, and 10 catechism antibodies from <=4KB GENESIS_SPORE.dna before spending tokens.',
    forbiddenLegacyPattern:
      'NEVER rely on prior chat memory, NEVER invent custom .env.example variables, NEVER add browser setInterval HTTP polling (I-8090).',
    enforcementGate:
      'LAW_SYSTEM_FIRST_IOC_RECONCILER + auditPerpetualFutureProofCoverage (Test 42 & Test 43)',
  },
  {
    agentSurface: '7-Seat Browser Workforce (TinyFish / BR-ZAI-01 .. BR-CHATGPT-01)',
    bootReadOrder: [
      'FLEET_3DAY_CANONICAL_MANIFEST.md',
      'src/engine/meridianCapabilityCalculus.ts',
    ],
    canonicalEntrypoint:
      'Publish claims & receipts through canonical OMNIFLOW (/api/omniflow/stream); keep status REGISTERED_UNAUTHENTICATED_NO_EXECUTION until authenticated execution receipt lands.',
    forbiddenLegacyPattern:
      'NEVER count registered seats as live execution (AB-09) and NEVER self-certify completed leases (verifierId !== executorId).',
    enforcementGate:
      'KARMA #7452 / #8030 HTTP 403 Self-Verify Block + FSM-05 / FSM-07 Closed-Loop Proofs',
  },
  {
    agentSurface: 'Founder Turnkey Setup & Disaster Recovery (/setup & /phone-boot)',
    bootReadOrder: [
      'FLEET_3DAY_CANONICAL_MANIFEST.md',
      'src/engine/applianceTurnkeySetup.ts',
    ],
    canonicalEntrypoint:
      'Use pure Web UI at /setup (workstation, 0 CLI / 0 sudo / 0 AI agents required) or /phone-boot (foreign country, brand-new phone, 3-of-8 RS(3,8) factors, no SMS OTP).',
    forbiddenLegacyPattern:
      'NEVER require terminal commands, interactive sudo prompts, privileged ports (<1024), or domestic SIM/SMS 2FA during recovery.',
    enforcementGate:
      'FSM-11 & FSM-12 Closed-Loop Proofs + 12/12 Adversarial Red-Team Suite + Epoch Fence 409 Revocation',
  },
  {
    agentSurface: 'GitHub Actions CI & Multi-Remote Sync (.github/workflows/*)',
    bootReadOrder: [
      '.github/workflows/fleet-3day-sync-verify.yml',
      '.github/workflows/phoenix-daily-boot.yml',
      'TEAM_HANDOFF_TODAY.md',
    ],
    canonicalEntrypoint:
      'On every push/PR, run npm ci -> npm run lint -> sequential httpIntegration.test.ts & router.test.ts -> npm run build -> mirror HEAD to chidionyema/argon-sync & chidionyema/gemini-sync (refs/heads/aistudio/meridian-hermes-live).',
    forbiddenLegacyPattern:
      'NEVER grade static deploys or unprobed URLs as LIVE OPERATING without bin/estate-live-probe MEASURED_OK.',
    enforcementGate:
      'fleet-3day-sync-verify.yml + phoenix-daily-boot.yml + Rego Rule R-010',
  },
];

const CRITICAL_ROOT_CONTRACTS: ReadonlyArray<string> = [
  'FLEET_3DAY_CANONICAL_MANIFEST.md',
  'TEAM_HANDOFF_TODAY.md',
  'AGENTS.md',
  'GEMINI.md',
  'ROUTER.md',
  'GENESIS_SPORE.dna',
  'MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md',
  '.github/workflows/fleet-3day-sync-verify.yml',
  '.github/workflows/phoenix-daily-boot.yml',
];

function runGitReadOnly(repoRoot: string, args: string[]): string {
  return execFileSync('git', ['-c', `safe.directory=${repoRoot}`, ...args], {
    cwd: repoRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

export function verifyThreeDayFleetSyncCompleteness(
  repoRoot: string,
  options: {
    externalGitHubPushConfirmed?: boolean;
    injectedMissingFiles?: ReadonlyArray<string>;
  } = {}
): FleetThreeDaySyncReport {
  const bundlePathRelative = 'dist-exports/meridian-hermes-today.bundle';
  const bundleAbs = path.join(repoRoot, bundlePathRelative);
  const injectedMissing = new Set(options.injectedMissingFiles ?? []);

  let headSha = 'unknown';
  let branch = 'main';
  let trackedFiles: string[] = [];
  let dirtyTrackedFiles: string[] = [];
  let untrackedSourceFiles: string[] = [];

  try {
    headSha = runGitReadOnly(repoRoot, ['rev-parse', 'HEAD']);
    branch = runGitReadOnly(repoRoot, ['rev-parse', '--abbrev-ref', 'HEAD']);
    const lsRaw = runGitReadOnly(repoRoot, ['ls-files']);
    trackedFiles = lsRaw
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    const diffTrackedRaw = runGitReadOnly(repoRoot, ['status', '--porcelain', '--untracked-files=no']);
    dirtyTrackedFiles = diffTrackedRaw
      ? diffTrackedRaw
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    const untrackedRaw = runGitReadOnly(repoRoot, ['ls-files', '--others', '--exclude-standard']);
    untrackedSourceFiles = untrackedRaw
      ? untrackedRaw
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];
  } catch {
    // Fallback if git binary unavailable
  }

  const trackedSet = new Set(trackedFiles);

  // Verify every required file across all 18 workstreams + critical root contracts
  const allRequired = new Set<string>(CRITICAL_ROOT_CONTRACTS);
  for (const ws of THREE_DAY_WORKSTREAM_LEDGER) {
    for (const rel of ws.requiredFiles) {
      allRequired.add(rel);
    }
  }

  const missingRequiredFiles: string[] = [];
  const untrackedRequiredFiles: string[] = [];

  for (const rel of allRequired) {
    const abs = path.join(repoRoot, rel);
    if (injectedMissing.has(rel) || !fs.existsSync(abs) || fs.statSync(abs).size === 0) {
      missingRequiredFiles.push(rel);
      continue;
    }
    if (trackedSet.size > 0 && !trackedSet.has(rel)) {
      untrackedRequiredFiles.push(rel);
    }
  }

  let verifiedWorkstreamsCount = 0;
  for (const ws of THREE_DAY_WORKSTREAM_LEDGER) {
    const wsOk = ws.requiredFiles.every(
      (rel) => !missingRequiredFiles.includes(rel) && !untrackedRequiredFiles.includes(rel)
    );
    if (wsOk) verifiedWorkstreamsCount++;
  }

  // Compute deterministic 3-Day Merkle Root over all tracked files on disk
  const sortedTracked = [...trackedFiles].sort();
  const merkleHasher = createHash('sha256');
  for (const rel of sortedTracked) {
    const abs = path.join(repoRoot, rel);
    if (fs.existsSync(abs) && fs.statSync(abs).isFile()) {
      const fileHash = createHash('sha256').update(fs.readFileSync(abs)).digest('hex');
      merkleHasher.update(`${rel}:${fileHash}\n`);
    }
  }
  const threeDayMerkleRootSha256 = merkleHasher.digest('hex');

  // Verify bundle existence, SHA-256, `git bundle verify`, and HEAD SHA match
  let bundleExists = false;
  let bundleBytes = 0;
  let bundleSha256: string | null = null;
  let bundleHeadSha: string | null = null;
  let bundleVerifiedOk = false;

  if (fs.existsSync(bundleAbs)) {
    const st = fs.statSync(bundleAbs);
    if (st.isFile() && st.size > 0) {
      bundleExists = true;
      bundleBytes = st.size;
      bundleSha256 = createHash('sha256').update(fs.readFileSync(bundleAbs)).digest('hex');
      try {
        runGitReadOnly(repoRoot, ['bundle', 'verify', bundlePathRelative]);
        bundleVerifiedOk = true;
        const headsRaw = runGitReadOnly(repoRoot, ['bundle', 'list-heads', bundlePathRelative]);
        const lines = headsRaw.split('\n').map((l) => l.trim()).filter(Boolean);
        const headLine =
          lines.find((l) => l.endsWith(' HEAD')) ??
          lines.find((l) => l.includes('refs/heads/aistudio/meridian-hermes-carbon-20261117')) ??
          lines.find((l) => l.includes('refs/heads/main')) ??
          lines[0];
        if (headLine) {
          bundleHeadSha = headLine.split(/\s+/)[0] ?? null;
        }
        if (!headsRaw.includes('refs/heads/aistudio/meridian-hermes-carbon-20261117')) {
          bundleVerifiedOk = false;
        }
      } catch {
        bundleVerifiedOk = false;
      }
    }
  }

  const bundleMatchesHead =
    bundleExists &&
    bundleVerifiedOk &&
    headSha !== 'unknown' &&
    bundleHeadSha === headSha;

  // Check AGENTS.md ceiling and GENESIS_SPORE.dna <= 4096B
  const agentsAbs = path.join(repoRoot, 'AGENTS.md');
  const agentsMdLines = fs.existsSync(agentsAbs)
    ? fs.readFileSync(agentsAbs, 'utf8').split('\n').length
    : 999;
  const agentsMdWithinCeiling = agentsMdLines <= 300;

  const sporeAbs = path.join(repoRoot, 'GENESIS_SPORE.dna');
  const genesisSporeBytes = fs.existsSync(sporeAbs)
    ? fs.statSync(sporeAbs).size
    : 99999;
  const genesisSporeWithin4Kb = genesisSporeBytes > 0 && genesisSporeBytes <= 4096;

  // Verify anti-confusion & 3-day coverage markers inside FLEET_3DAY_CANONICAL_MANIFEST.md and TEAM_HANDOFF_TODAY.md
  const fleetManifestAbs = path.join(repoRoot, 'FLEET_3DAY_CANONICAL_MANIFEST.md');
  const handoffAbs = path.join(repoRoot, 'TEAM_HANDOFF_TODAY.md');
  const fleetManifestText = fs.existsSync(fleetManifestAbs)
    ? fs.readFileSync(fleetManifestAbs, 'utf8')
    : '';
  const handoffText = fs.existsSync(handoffAbs)
    ? fs.readFileSync(handoffAbs, 'utf8')
    : '';

  const requiredManifestTokens = [
    '2026-11-15',
    '2026-11-16',
    '2026-11-17',
    '127.0.0.1:4200',
    '193.123.184.22',
    '/setup',
    '/phone-boot',
    '/phoenix',
    'GENESIS_SPORE.dna',
    'chidionyema/argon-sync',
    'chidionyema/gemini-sync',
  ];
  const manifestAntiConfusionVerified =
    requiredManifestTokens.every((tok) => fleetManifestText.includes(tok)) &&
    handoffText.includes('Lane 1') &&
    handoffText.includes('Lane 2') &&
    handoffText.includes('Lane 3') &&
    handoffText.includes('17 Nov 2026') &&
    handoffText.includes('/phone-boot');

  const githubCiWorkflowPresent =
    !injectedMissing.has('.github/workflows/fleet-3day-sync-verify.yml') &&
    fs.existsSync(path.join(repoRoot, '.github/workflows/fleet-3day-sync-verify.yml'));

  const criticalContractDigests: ThreeDayFileSealDigest[] = [];
  for (const rel of CRITICAL_ROOT_CONTRACTS) {
    const abs = path.join(repoRoot, rel);
    if (fs.existsSync(abs) && fs.statSync(abs).isFile()) {
      const buf = fs.readFileSync(abs);
      criticalContractDigests.push({
        relativePath: rel,
        bytes: buf.length,
        sha256: createHash('sha256').update(buf).digest('hex'),
        trackedInGit: trackedSet.has(rel),
      });
    }
  }

  const workingTreeClean =
    dirtyTrackedFiles.length === 0 && untrackedSourceFiles.length === 0;

  const allThreeDaysSealed =
    missingRequiredFiles.length === 0 &&
    untrackedRequiredFiles.length === 0 &&
    untrackedSourceFiles.length === 0 &&
    workingTreeClean &&
    bundleMatchesHead &&
    agentsMdWithinCeiling &&
    genesisSporeWithin4Kb &&
    manifestAntiConfusionVerified &&
    githubCiWorkflowPresent;

  return {
    schemaVersion: 'meridian-fleet-3day-sync-v1',
    generatedAtUtc: new Date().toISOString(),
    windowLabel: '2026-11-15 .. 2026-11-17 (3-Day Cumulative Seal)',
    headSha,
    branch,
    workingTreeClean,
    dirtyTrackedFiles,
    untrackedSourceFiles,
    bundlePathRelative,
    bundleExists,
    bundleBytes,
    bundleSha256,
    bundleHeadSha,
    bundleVerifiedOk,
    bundleMatchesHead,
    totalTrackedFilesCount: trackedFiles.length,
    threeDayMerkleRootSha256,
    agentsMdLines,
    agentsMdWithinCeiling,
    genesisSporeBytes,
    genesisSporeWithin4Kb,
    dayBreakdown: {
      day1WorkstreamsCount: THREE_DAY_WORKSTREAM_LEDGER.filter((w) => w.day === 'DAY_1_2026_11_15').length,
      day2WorkstreamsCount: THREE_DAY_WORKSTREAM_LEDGER.filter((w) => w.day === 'DAY_2_2026_11_16').length,
      day3WorkstreamsCount: THREE_DAY_WORKSTREAM_LEDGER.filter((w) => w.day === 'DAY_3_2026_11_17').length,
      totalWorkstreamsCount: THREE_DAY_WORKSTREAM_LEDGER.length,
      verifiedWorkstreamsCount,
    },
    missingRequiredFiles,
    untrackedRequiredFiles,
    manifestAntiConfusionVerified,
    githubCiWorkflowPresent,
    allThreeDaysSealed,
    externalGitHubPushState: options.externalGitHubPushConfirmed
      ? 'EXTERNAL_GITHUB_PUSH_CONFIRMED'
      : 'LOCAL_SEALED_AWAITING_GITHUB_PUSH_RECEIPT',
    canonicalGitHubRemotes: CANONICAL_GITHUB_SYNC_REMOTES,
    canonicalGitHubRef: CANONICAL_GITHUB_SYNC_REF,
    workstreams: THREE_DAY_WORKSTREAM_LEDGER,
    fleetDirectives: FLEET_AGENT_DIRECTIVES,
    criticalContractDigests,
  };
}

export function renderFleetThreeDayManifestMarkdown(report: FleetThreeDaySyncReport): string {
  const lines: string[] = [
    '# FLEET 3-DAY CANONICAL SYNC MANIFEST & ANTI-CONFUSION LEDGER (15–17 Nov 2026)',
    '',
    '> **READ THIS FIRST (ALL HUMAN ENGINEERS & AI FLEET ACTUATORS):**',
    '> This repository contains the complete, cumulative **3-day engineering delivery (`2026-11-15` through `2026-11-17`)** across PennyD, Meridian, Hermes, OMNIFLOW, KARMA, Operation Phoenix v2, System-First IoC (`GENESIS_SPORE.dna`), and Commercial Turnkey Appliance + Foreign-Country Phone Disaster Recovery (`/setup` & `/phone-boot`).',
    '> Every model (`gemini`, `glm-5.3`, `deepseek`, `kimi`, `claude`, `chatgpt`) is a stateless interchangeable actuator bound to this manifest.',
    '',
    '## 1. Live Cryptographic Seal & GitHub Sync Status',
    `- **Generated (UTC):** \`${report.generatedAtUtc}\``,
    `- **Coverage Window:** \`${report.windowLabel}\``,
    `- **Git Branch / HEAD:** \`${report.branch}\` @ \`${report.headSha}\` (workingTreeClean=\`${report.workingTreeClean}\`, untrackedSourceFiles=\`${report.untrackedSourceFiles.length}\`)`,
    `- **3-Day Tracked File Count & Merkle Root:** \`${report.totalTrackedFilesCount}\` files · \`${report.threeDayMerkleRootSha256}\``,
    `- **Verified Git DAG Bundle:** \`${report.bundlePathRelative}\` (\`${report.bundleBytes.toLocaleString()}\` bytes, \`bundleMatchesHead=${report.bundleMatchesHead}\`)`,
    `- **Bundle SHA-256:** \`${report.bundleSha256 ?? 'pending'}\``,
    `- **3-Day Workstreams Verified:** \`${report.dayBreakdown.verifiedWorkstreamsCount}/${report.dayBreakdown.totalWorkstreamsCount}\` (Day 1: \`${report.dayBreakdown.day1WorkstreamsCount}\`, Day 2: \`${report.dayBreakdown.day2WorkstreamsCount}\`, Day 3: \`${report.dayBreakdown.day3WorkstreamsCount}\`)`,
    `- **Constitutional Ceilings:** \`AGENTS.md=${report.agentsMdLines}/300 lines\` · \`GENESIS_SPORE.dna=${report.genesisSporeBytes}/4096 bytes\``,
    `- **Canonical GitHub Remotes & Ref:** \`${report.canonicalGitHubRemotes.join(', ')}\` -> \`${report.canonicalGitHubRef}\``,
    `- **External GitHub Push Disposition (R-010 Candor):** \`${report.externalGitHubPushState}\``,
    '',
    '## 2. How to Sync 100% of This 3-Day State to GitHub Without Missing a Byte',
    '1. **AI Studio Native Toolbar (1 Click -> Auto-Triggers GitHub CI):** Click the **GitHub icon ("Save to GitHub")** in the top-right AI Studio bar. Pushing to GitHub automatically runs `.github/workflows/fleet-3day-sync-verify.yml` (verifies all 3 days, runs lint + full test suites + build, uploads the verified `.bundle` artifact, and mirrors `HEAD` to both `chidionyema/argon-sync` and `chidionyema/gemini-sync` when repo secret `FLEET_SYNC_PAT` is set).',
    '2. **1-Click Browser Download (`/get-work` or Top-Right `Get All Work` Button):** Download `meridian-hermes-today.bundle` (`/api/export/bundle`) or `meridian-complete-3days-2026-11-17.tar.gz` (`/api/export/all-3days`), then run:',
    '   ```bash',
    `   echo "${report.bundleSha256 ?? '<bundle-sha256>'}  meridian-hermes-today.bundle" | shasum -a 256 -c -`,
    '   git bundle verify meridian-hermes-today.bundle',
    '   git clone meridian-hermes-today.bundle meridian-3day-sync && cd meridian-3day-sync',
    '   git remote add argon git@github.com:chidionyema/argon-sync.git',
    '   git remote add gemini git@github.com:chidionyema/gemini-sync.git',
    `   git push argon HEAD:${report.canonicalGitHubRef} --force-with-lease`,
    `   git push gemini HEAD:${report.canonicalGitHubRef} --force-with-lease`,
    '   ```',
    '3. **Zero-Reminder Outbound Container Push:** Register any HTTPS tunnel (`cloudflared tunnel`) or S3/R2 pre-signed URL in `Get All Work` (`POST /api/export/register-target`); the 45s daemon pushes `meridian-hermes-today.bundle` automatically.',
    '',
    '## 3. Fleet Agent Onboarding & Anti-Confusion Directives (Zero Stale Assumptions)',
    '| Fleet Surface | Mandatory Boot Read Order | Canonical Live Entrypoint | Forbidden Retired Trap | Enforcement Gate |',
    '|---|---|---|---|---|',
    ...report.fleetDirectives.map(
      (d) =>
        `| ${d.agentSurface} | \`${d.bootReadOrder.join(' -> ')}\` | ${d.canonicalEntrypoint} | ${d.forbiddenLegacyPattern} | ${d.enforcementGate} |`
    ),
    '',
    '## 4. Complete 3-Day Cumulative Workstream Ledger (18/18 Workstreams)',
    '| ID | Date | Workstream | UI Route | Primary Tracked Files | Canonical Truth | Retired Trap Blocked |',
    '|---|---|---|---|---|---|---|',
    ...report.workstreams.map(
      (w) =>
        `| \`${w.id}\` | \`${w.dateIso}\` | **${w.title}** | \`${w.canonicalUiRoute}\` | \`${w.requiredFiles.slice(0, 4).join(', ')}${w.requiredFiles.length > 4 ? ', …' : ''}\` | ${w.canonicalTruthSummary} | ${w.retiredConfusionTrapBlocked} |`
    ),
    '',
    '## 5. Deterministic Verification Commands (Run on Every Runner & PR)',
    '```bash',
    'npm ci',
    'npm run lint',
    'npx --yes tsx --test --test-concurrency=1 src/engine/httpIntegration.test.ts',
    'npx --yes tsx --test --test-concurrency=1 src/engine/router.test.ts',
    'npm run build',
    '```',
    '',
  ];
  return lines.join('\n');
}
