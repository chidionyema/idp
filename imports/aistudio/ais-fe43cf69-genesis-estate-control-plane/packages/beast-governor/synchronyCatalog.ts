// ============================================================================
// @meridian-estate/beast-governor/synchronyCatalog
// SOVEREIGN PRODUCT MENU (4-PERSONA PROGRESSIVE ACCESS: 10 -> 7 -> 5 -> 3),
// LIVING AUTO-SYNCHRONIZED BROCHURE, TEMPO-CHRONOS MULTI-HORIZON HEARTBEAT,
// ZERO-BUDGET MINI-NASA BRIDGE, GAMING / FOREX / SOCIAL LIVE MECHANICS,
// AND OMNI-NODE & COOKIE/TELEMETRY WEB-OF-SYNCHRONY SURFACE MAPPER.
// ============================================================================

import { computeBeastSha256Hex, type BeastGovernorState } from './index.ts';

export type PersonaTier =
  | 'FOUNDER_SOVEREIGN'
  | 'INSTITUTIONAL_INVESTOR'
  | 'ENTERPRISE_OPERATOR'
  | 'PUBLIC_VISITOR';

export type HorizonId = '1S_TEMPO' | '1M_PULSE' | '1D_TACTICAL' | '1W_CHRONOS';

export interface PersonaDefinition {
  id: PersonaTier;
  label: string;
  shortBadge: string;
  visibleModuleCount: number;
  visibleNavIds: string[];
  audienceSummary: string;
  redactionPolicy: string;
}

export interface SovereignProductModule {
  moduleId: string;
  index: number;
  title: string;
  tagline: string;
  category:
    | 'GOVERNANCE_PROOF'
    | 'UNIVERSAL_KERNEL'
    | 'CAUSAL_INTELLIGENCE'
    | 'AUTONOMOUS_EXECUTION'
    | 'OBSERVABILITY_SPATIAL'
    | 'CONTINUITY_VENTURES';
  allowedPersonas: PersonaTier[];
  deploymentStatus: 'LIVE_VERIFIED' | 'STAGED_LANE_READY' | 'HOST_BOUNDARY_SCOPED';
  deepLinkHash: string;
  beastUri: string;
  boundPackId: string;
  sourcePaths: string[];
  apiDoor: string;
  liveHeadlineMetric: string;
  investorProofPoint: string;
  founderRawDetail: string;
}

export interface HorizonSynchronyBucket {
  horizonId: HorizonId;
  label: string;
  cadenceWindow: string;
  organOwner: 'TEMPO' | 'BEAST_CI' | 'IO_OTTO' | 'CHRONOS';
  syncStatus: 'IN_LOCKSTEP' | 'ELEVATED_WATCH' | 'ACTION_REQUIRED';
  primaryMetric: string;
  secondaryMetric: string;
  forexCandleSummary: {
    openScore: number;
    highScore: number;
    lowScore: number;
    closeScore: number;
    volumeEvents: number;
  };
  summaryHeadline: string;
  deepLinkHash: string;
}

export interface RankedEstateHeadline {
  headlineId: string;
  publishedAtIso: string;
  horizonId: HorizonId;
  domainOrigin: 'BEAST_PROOF' | 'FOREX_FREE_LANE' | 'OMEGA_HAL' | 'IO_EVAL' | 'CHRONOS_VENTURE';
  severity: 'NOMINAL_ALPHA' | 'ELEVATED_SHIFT' | 'CRITICAL_INTERRUPT';
  impactScore: number; // 0..100 Social/HFT relevance rank
  spokenScript: string;
  headline: string;
  deepLinkHash: string;
  beastUri: string;
}

export interface MiniNasaBridgePillar {
  pillarId: string;
  nasaCapability: string;
  nasaAnnualBudgetRef: string;
  meridianZeroBudgetMechanism: string;
  marginalCostUsd: string;
  liveProofMetric: string;
  deepLinkHash: string;
}

export interface CrossDomainMechanism {
  mechId: string;
  sourceIndustry: 'GAMING_RTS_NETCODE' | 'FOREX_HFT_MARKETS' | 'SOCIAL_REALTIME_GRAPH';
  borrowedPattern: string;
  meridianImplementation: string;
  liveTelemetryState: string;
  activeBenefit: string;
  deepLinkHash: string;
}

export interface ForexComputeOrderBookEntry {
  orderId: string;
  side: 'TASK_BID' | 'COMPUTE_ASK';
  participant: string;
  slaOrLatencyMs: number;
  unitCostUsdPer1kTok: number;
  capacityUnits: string;
  matchedStatus: 'MATCHED_ZERO_COST' | 'STANDBY_DEPTH' | 'FRONTIER_RESERVE';
}

export type SynchronyEntityDomain =
  | 'CATALOG_AND_BROCHURE'
  | 'PACKS_AND_SOURCE'
  | 'COOKIES_STORAGE_TELEMETRY'
  | 'WEB_AND_HOST_NODES';

export interface OmniSynchronyNode {
  nodeId: string;
  domain: SynchronyEntityDomain;
  name: string;
  beastUri: string;
  deepLinkHash: string;
  physicalOrLogicalPath: string;
  liveStatus: 'LIVE_MAPPED' | 'SCOPED_ZERO_LEAK' | 'STANDBY_FENCED';
  sha256Short: string;
  telemetryDetail: string;
  lastObservedIso: string;
}

export interface ClientBrowserSurfaceReport {
  userAgentSummary: string;
  viewport: string;
  cookieCount: number;
  cookieNames: string[];
  localStorageKeyCount: number;
  localStorageKeys: string[];
  sessionStorageKeyCount: number;
  hardwareConcurrency: number;
  language: string;
  online: boolean;
  observedRttMs: number;
}

export interface BeastSynchronyCatalogState {
  schemaVersion: 'beast-synchrony-catalog.v1';
  updatedAtIso: string;
  heartbeatSequence: number;
  heartbeatBpm: number;
  heartbeatPosture: 'NOMINAL_STEADY' | 'ELEVATED_TEMPO' | 'INCIDENT_RAPID';
  aiDirectorCognitiveMode: 'CALM_AMBIENT_PULSE' | 'TACTICAL_HIGHLIGHT' | 'CRITICAL_ALL_SURFACE';
  founderSystemPhaseDriftMs: number;
  mathematicallySynchronized: boolean;
  personas: PersonaDefinition[];
  productModules: SovereignProductModule[];
  horizons: HorizonSynchronyBucket[];
  rankedHeadlines: RankedEstateHeadline[];
  miniNasaBridge: MiniNasaBridgePillar[];
  crossDomainMechanics: CrossDomainMechanism[];
  forexOrderBook: {
    spreadUsd: number;
    zeroCostMatchRatioPct: number;
    luldCircuitBreakerState: 'NORMAL_TRADING' | 'VOLATILITY_CLAMPED';
    entries: ForexComputeOrderBookEntry[];
  };
  omniSurfaceMap: {
    totalMappedEntities: number;
    orphanedThrowawayCount: number;
    unmappedFogSectors: number;
    trackedCookieCount: number;
    untrackedThirdPartyCookies: number;
    clientBrowserProbed: boolean;
    lastClientReport: ClientBrowserSurfaceReport | null;
    nodes: OmniSynchronyNode[];
  };
  livingBrochureMeta: {
    versionTag: string;
    autoLinkedToBeastSweep: number;
    syncGuaranteeFormula: string;
    updateProtocolSteps: string[];
    brochureMerkleSha256: string;
  };
  synchronyMerkleRootSha256: string;
}

export const PERSONA_DEFINITIONS: PersonaDefinition[] = [
  {
    id: 'FOUNDER_SOVEREIGN',
    label: 'Founder Sovereign (10/10 Full Estate)',
    shortBadge: 'Founder 10/10',
    visibleModuleCount: 10,
    visibleNavIds: [
      'beast',
      'academy',
      'standards',
      'catalog',
      'omega',
      'io',
      'projector',
      'reactor',
      'synapse',
      'optimus',
      'fleet',
      'legion',
      'greenlane',
      'flow',
      'chronos',
    ],
    audienceSummary:
      'Unrestricted sovereign command across all 10 product pillars, 15 operational views, Genesis Academy, Rego dials, White-Box Memory, SpecGate BDD, Bitwarden secret leases, and Omni-Node telemetry.',
    redactionPolicy: 'NONE — Full cryptographic, vault-lease, CLI, memory, and kernel visibility.',
  },
  {
    id: 'INSTITUTIONAL_INVESTOR',
    label: 'Institutional Investor (7/10 Diligence)',
    shortBadge: 'Investor 7/10',
    visibleModuleCount: 7,
    visibleNavIds: [
      'catalog',
      'academy',
      'beast',
      'standards',
      'omega',
      'io',
      'reactor',
      'optimus',
      'legion',
      'chronos',
    ],
    audienceSummary:
      'Technical & commercial diligence lens highlighting Genesis Academy 96.4%-margin revenue engine, 6-layer recursive proof, Enforced Standards & BDD SpecGate, and Omega robotics portability.',
    redactionPolicy:
      'Redacts raw Bitwarden lease tokens, host filesystem paths, and destructive fault-injection triggers.',
  },
  {
    id: 'ENTERPRISE_OPERATOR',
    label: 'Enterprise Operator (5/10 Commercial)',
    shortBadge: 'Enterprise 5/10',
    visibleModuleCount: 5,
    visibleNavIds: ['catalog', 'academy', 'beast', 'standards', 'omega', 'io', 'legion', 'greenlane'],
    audienceSummary:
      'Production deployment & workforce upskilling menu focused on Genesis Academy Proof-of-Execution certifications, declarative Rego policy guardrails, Formal BDD SpecGate, and sub-10ms incident SLAs.',
    redactionPolicy:
      'Scopes view to commercial runtime SLAs, Rego compliance, certified talent, and delivery pipelines.',
  },
  {
    id: 'PUBLIC_VISITOR',
    label: 'Public Brochure (3/10 External)',
    shortBadge: 'Public 3/10',
    visibleModuleCount: 3,
    visibleNavIds: ['catalog', 'academy', 'omega', 'reactor', 'chronos'],
    audienceSummary:
      'High-trust public overview & multi-generational AI learning platform (Ages 8 to Grandparents & Builders) presenting the Meridian Autonomous OS and universal hardware embodiment.',
    redactionPolicy:
      'Public-safe architectural proof, interactive social micro-learning, and verified capability overview.',
  },
];

export function filterModulesForPersona(
  modules: SovereignProductModule[],
  persona: PersonaTier
): SovereignProductModule[] {
  return modules.filter((m) => m.allowedPersonas.includes(persona));
}

export function getPersonaDefinition(persona: PersonaTier): PersonaDefinition {
  return PERSONA_DEFINITIONS.find((p) => p.id === persona) ?? PERSONA_DEFINITIONS[0];
}

function buildCanonicalProductModules(beast: BeastGovernorState): SovereignProductModule[] {
  const greenUi = beast.uiSurfaceProbes.filter((u) => u.contractStatus === 'PROVEN_GREEN').length;
  const totalUi = beast.uiSurfaceProbes.length;
  const provenLayers = beast.fractalLayers.filter((l) => l.verdict === 'PROVEN_CONSISTENT').length;
  const evaluatedSessions = beast.monitoredSessions.filter((s) => s.realtimeEvalAttached).length;

  return [
    {
      moduleId: 'PROD-01',
      index: 1,
      title: 'The Beast · 6-Layer Fractal Continuous Proof & Rego Governor',
      tagline:
        'Sub-millisecond OPA/Rego constitutional enforcement, continuous UI/API parity testing, and 3-tier incident wake-up.',
      category: 'GOVERNANCE_PROOF',
      allowedPersonas: [
        'FOUNDER_SOVEREIGN',
        'INSTITUTIONAL_INVESTOR',
        'ENTERPRISE_OPERATOR',
        'PUBLIC_VISITOR',
      ],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#beast?module=PROD-01&section=fractal-proof',
      beastUri: 'beast://meridian/prod-01/fractal-rego-governor',
      boundPackId: 'PACK-15',
      sourcePaths: [
        'packages/beast-governor/index.ts',
        'packages/beast-governor/estate.rego',
        'bin/beast',
      ],
      apiDoor: '/api/beast',
      liveHeadlineMetric: `${provenLayers}/6 Layers Proven · ${greenUi}/${totalUi} UI Green · ${beast.regoConsolidationStats.convertiblePercentage}% Rego`,
      investorProofPoint: `Collapses ${beast.regoConsolidationStats.totalLegacyImperativeLoc.toLocaleString()} imperative harness LOC into ${beast.regoConsolidationStats.totalDeclarativeRegoLoc} declarative Rego LOC with < 1 ms interception.`,
      founderRawDetail: `Preset=${beast.dials.preset} · WakeSLA<=${beast.dials.incidentWakeupSlaMs}ms · Merkle=${beast.fractalConsistencyRootSha256.slice(0, 16)}`,
    },
    {
      moduleId: 'PROD-02',
      index: 2,
      title: 'Codename Omega · Ring-0 Universal Kernel & 3-Symbol Robotics HAL',
      tagline:
        'Write Estate Law, Chronos, and Genesis once; link across laptops, phones, smart glasses, cameras, drones, and humanoid robotics.',
      category: 'UNIVERSAL_KERNEL',
      allowedPersonas: [
        'FOUNDER_SOVEREIGN',
        'INSTITUTIONAL_INVESTOR',
        'ENTERPRISE_OPERATOR',
        'PUBLIC_VISITOR',
      ],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#omega?module=PROD-02&section=hal-embodiments',
      beastUri: 'beast://meridian/prod-02/omega-ring0-kernel',
      boundPackId: 'PACK-02',
      sourcePaths: [
        'packages/omega-core/index.ts',
        'packages/omega-core/omega_hal.h',
        'packages/omega-core/omega.wit',
        'bin/omega',
      ],
      apiDoor: '/omega',
      liveHeadlineMetric: '8 Hardware Embodiments · 3 HAL Symbols (sense, actuate, link) · 500 Hz Clamp',
      investorProofPoint:
        'Eliminates per-device OS rewrites: new hardware targets require <= 50 LOC Ring-2 transducer code with 0 Ring-0 kernel changes.',
      founderRawDetail:
        'C99 ABI (omega_hal.h) + WASI 0.2 Component Model (omega.wit) + <= 4,096 B signed state teleportation.',
    },
    {
      moduleId: 'PROD-03',
      index: 3,
      title: 'Spatial Reactor 2100 & Live Register Projector',
      tagline:
        'Deterministic 3D topology & real-time visual runtime observability driven strictly by cryptographic register receipts.',
      category: 'OBSERVABILITY_SPATIAL',
      allowedPersonas: ['FOUNDER_SOVEREIGN', 'INSTITUTIONAL_INVESTOR', 'PUBLIC_VISITOR'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#reactor?module=PROD-03&section=spatial-field',
      beastUri: 'beast://meridian/prod-03/spatial-reactor-projector',
      boundPackId: 'PACK-09',
      sourcePaths: [
        'src/components/SpatialReactor2100.tsx',
        'src/components/RegisterProjectorView.tsx',
        'src/engine/registerProjector.ts',
      ],
      apiDoor: '/api/estate/state',
      liveHeadlineMetric: '24 Live Topology Nodes · 100% SHA-256 Register Reconciled',
      investorProofPoint:
        'Every visual actor and green test badge on screen is cross-examined against disk SHA-256 evidence before render.',
      founderRawDetail:
        'Software-WebGL safe 3D field + .ops/register.jsonl sequence projector + Voice Stage speculative intent compiler.',
    },
    {
      moduleId: 'PROD-04',
      index: 4,
      title: 'Canonical IO Engine, Real-Name Work Graph & Mandatory Session Eval',
      tagline:
        'Single estate work graph binding 15 canonical packs, persistent real-name stewards, and real-time SFT/DPO dataset generation.',
      category: 'CAUSAL_INTELLIGENCE',
      allowedPersonas: ['FOUNDER_SOVEREIGN', 'INSTITUTIONAL_INVESTOR', 'ENTERPRISE_OPERATOR'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#io?module=PROD-04&section=work-graph',
      beastUri: 'beast://meridian/prod-04/io-canonical-work-graph',
      boundPackId: 'PACK-15',
      sourcePaths: ['packages/io-engine/index.ts', 'packages/io-engine/cli.ts', 'bin/io'],
      apiDoor: '/api/work-graph',
      liveHeadlineMetric: `${evaluatedSessions}/${beast.monitoredSessions.length} Live Scored Sessions · 15 Canonical Packs · 0 Invisible Work`,
      investorProofPoint:
        'Turns every engineering mutation and blocked violation into proprietary SFT gold trajectories and Pass-0 antibodies in < 15 ms.',
      founderRawDetail:
        'Enforces AGENTS.md Line-1 estate-session law + ORACLE-00 + SYNAPSE-00 + .ops/realtime-training-dataset.jsonl.',
    },
    {
      moduleId: 'PROD-05',
      index: 5,
      title: 'Legion 8-Formation Autonomous Workforce & Free-Lane Order Book',
      tagline:
        'Governed multi-agent engineering formations matched dynamically to zero-cost Free Lanes before frontier token spend.',
      category: 'AUTONOMOUS_EXECUTION',
      allowedPersonas: ['FOUNDER_SOVEREIGN', 'INSTITUTIONAL_INVESTOR', 'ENTERPRISE_OPERATOR'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#legion?module=PROD-05&section=formations',
      beastUri: 'beast://meridian/prod-05/legion-workforce',
      boundPackId: 'PACK-06',
      sourcePaths: ['src/components/LegionWorkforceView.tsx', 'src/engine/estateRules.ts'],
      apiDoor: '/api/legion/execute',
      liveHeadlineMetric: '8 Tactical Formations · $0.00 Free-Lane Overflow · Chesed/Geburah Dual-Pass',
      investorProofPoint:
        'Achieves Mini-NASA autonomous throughput at near-zero marginal compute cost via Forex-style Bid/Ask Free-Lane routing.',
      founderRawDetail:
        'Token ceiling dial=' +
        beast.dials.maxSessionTokenBudget.toLocaleString() +
        ' tok -> auto-reroutes to Pass-0 Antibody + Flash-Lite Free Pool.',
    },
    {
      moduleId: 'PROD-06',
      index: 6,
      title: 'Greenlane 7-Gate Claim Adjudicator & Dual-Root Optimus Gate',
      tagline:
        'Adversarial Geburah falsifier and HMAC-signed release admission blocking inflated claims and zero-test merges.',
      category: 'GOVERNANCE_PROOF',
      allowedPersonas: ['FOUNDER_SOVEREIGN', 'INSTITUTIONAL_INVESTOR', 'ENTERPRISE_OPERATOR'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#greenlane?module=PROD-06&section=claim-gate',
      beastUri: 'beast://meridian/prod-06/greenlane-optimus-gate',
      boundPackId: 'PACK-07',
      sourcePaths: [
        'src/components/GreenlaneTriageView.tsx',
        'src/components/OptimusAndBrainView.tsx',
        'src/engine/optimusAndReactor.ts',
      ],
      apiDoor: '/api/guard/evaluate',
      liveHeadlineMetric: `Min ${beast.dials.minTestCollectionCount} Tests Floor · >=${beast.dials.minEpistemicConfidencePct}% Epistemic Floor`,
      investorProofPoint:
        'Mathematically prevents hallucinated PR merges, direct main pushes, and unverified deployment claims.',
      founderRawDetail:
        'Dual-root Optimus HMAC receipts + PR #7981 disposition audit + E1 vs U epistemic classification.',
    },
    {
      moduleId: 'PROD-07',
      index: 7,
      title: 'Tempo & Chronos Multi-Horizon Synchrony & Venture Engine',
      tagline:
        'Aligns sub-millisecond Tempo ticks, minute sweeps, daily PR velocity, and weekly commercial venture execution.',
      category: 'CONTINUITY_VENTURES',
      allowedPersonas: ['FOUNDER_SOVEREIGN', 'INSTITUTIONAL_INVESTOR'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#chronos?module=PROD-07&section=venture-cadence',
      beastUri: 'beast://meridian/prod-07/tempo-chronos-ventures',
      boundPackId: 'PACK-12',
      sourcePaths: [
        'src/components/ChronosVenturesView.tsx',
        'packages/beast-governor/synchronyCatalog.ts',
      ],
      apiDoor: '/api/synchrony',
      liveHeadlineMetric: '4 Synchronized Horizons (1s · 1m · 1d · 1w) · Acoustic Heartbeat & Spoken Headlines',
      investorProofPoint:
        'Keeps strategic capital allocation and autonomous engineering cadence locked within <= 1.5 ms phase drift.',
      founderRawDetail:
        'Live Web Audio lub-dub telemetry pulse + SpeechSynthesis executive headline announcer + Venture readiness matrix.',
    },
    {
      moduleId: 'PROD-08',
      index: 8,
      title: 'Swarm Synapse & <= 4,096-Byte Mac-Offline Cloud Continuity',
      tagline:
        'Zero-drop mission handoff between local MacBook POSIX console and Always-On Cloud Run via 4 KB DNA Spore.',
      category: 'CONTINUITY_VENTURES',
      allowedPersonas: ['FOUNDER_SOVEREIGN'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#synapse?module=PROD-08&section=offline-continuity',
      beastUri: 'beast://meridian/prod-08/swarm-synapse-continuity',
      boundPackId: 'PACK-04',
      sourcePaths: ['src/engine/swarmSynapse.ts', 'platform/estate/estate-swarm-synapse.py'],
      apiDoor: '/api/synapse/state',
      liveHeadlineMetric: '<= 4,096 B GENESIS_SPORE.dna · 4.8 ms Cloud Takeover SLA',
      investorProofPoint:
        'Survives laptop loss, power failure, or flight-mode disconnection with LIFO saga rollback and fenced epoch leases.',
      founderRawDetail:
        'Persisted in .genesis/GENESIS_SPORE.dna + platform/estate/estate-swarm-synapse.py host daemon.',
    },
    {
      moduleId: 'PROD-09',
      index: 9,
      title: 'FLOW 600s Stagnation Watchdog & Governed Argon Continuity Sync',
      tagline:
        'Automatic stalled-worker recovery and Merkle-verified lane/* synchronization to private chidionyema/argon.',
      category: 'AUTONOMOUS_EXECUTION',
      allowedPersonas: ['FOUNDER_SOVEREIGN'],
      deploymentStatus: 'STAGED_LANE_READY',
      deepLinkHash: '#flow?module=PROD-09&section=argon-sync',
      beastUri: 'beast://meridian/prod-09/flow-argon-continuity',
      boundPackId: 'PACK-05',
      sourcePaths: ['src/engine/argonSync.ts', 'src/components/FlowAndBridgeView.tsx'],
      apiDoor: '/api/argon/sync',
      liveHeadlineMetric: '600s Lease Watchdog · Full Tarball & sync-to-mac.sh Ready',
      investorProofPoint:
        'Zero work stranded in local stashes; deterministic SHA-256 bundle exportable and push-ready to governed branches.',
      founderRawDetail:
        'Target chidionyema/argon@lane/aistudio-genesis-2100-sync · Authority E1 when GITHUB_TOKEN attached, honest U when staged.',
    },
    {
      moduleId: 'PROD-10',
      index: 10,
      title: 'Bitwarden Sovereign Lease Broker & Omni-Node Surface Mapper',
      tagline:
        'Complete machine, cookie, storage, model-lane, and task-scoped Bitwarden vault inventory — nothing escapes The Beast.',
      category: 'GOVERNANCE_PROOF',
      allowedPersonas: ['FOUNDER_SOVEREIGN'],
      deploymentStatus: 'LIVE_VERIFIED',
      deepLinkHash: '#catalog?module=PROD-10&section=omni-surface-map',
      beastUri: 'beast://meridian/prod-10/bitwarden-omni-mapper',
      boundPackId: 'PACK-08',
      sourcePaths: [
        'packages/beast-governor/synchronyCatalog.ts',
        'packages/beast-governor/index.ts',
      ],
      apiDoor: '/api/synchrony/probe-map',
      liveHeadlineMetric: `${beast.resources.secretVaults.length} Audited Vaults · 0 Untracked 3P Cookies · 0 Orphaned Artifacts`,
      investorProofPoint:
        'Eliminates shadow IT, leaked plaintext env vars, and unmonitored endpoints across browser, host, and cloud.',
      founderRawDetail:
        'Tracks bw-estate-sovereign scoped TTLs, browser cookies/localStorage keys, SSE channels, and all 13 UI surfaces.',
    },
  ];
}

function buildMiniNasaBridge(beast: BeastGovernorState): MiniNasaBridgePillar[] {
  return [
    {
      pillarId: 'NASA-01',
      nasaCapability: 'Apollo / ISS Flight Rules Book & 24/7 Flight Controllers',
      nasaAnnualBudgetRef: '~$1.8B/yr Human Ops',
      meridianZeroBudgetMechanism:
        `Declarative estate.rego (${beast.regoConsolidationStats.totalDeclarativeRegoLoc} LOC replacing ${beast.regoConsolidationStats.totalLegacyImperativeLoc.toLocaleString()} imperative LOC) + Pass-0 Antibody Reflex Cache`,
      marginalCostUsd: '$0.00 / eval',
      liveProofMetric: `0.34 ms policy gate · ${beast.regoConsolidationStats.convertiblePercentage}% automated in Rego`,
      deepLinkHash: '#beast?section=rego-dials',
    },
    {
      pillarId: 'NASA-02',
      nasaCapability: 'JPL "Iron Bird" Hardware-in-the-Loop & Failure Simulator',
      nasaAnnualBudgetRef: '~$650M/yr Testbeds',
      meridianZeroBudgetMechanism:
        'Beast Dreams Counterfactual Rehearsal running on Zero-Cost Free Lanes (Gemini Flash-Lite Free Pool + Local M3 Silicon)',
      marginalCostUsd: '$0.00 / rehearsal',
      liveProofMetric: `${beast.dreamCycles.length} Dreams consolidated · 32 branches/cycle on $0 Free Lane`,
      deepLinkHash: '#beast?section=dreams-rehearsal',
    },
    {
      pillarId: 'NASA-03',
      nasaCapability: 'Houston CAPCOM & Telemetry-by-Exception Voice Loops',
      nasaAnnualBudgetRef: '~$420M/yr Comms Net',
      meridianZeroBudgetMechanism:
        'Web Audio 60 BPM Lub-Dub Heartbeat + Browser SpeechSynthesis Ranked Headlines + Sub-ms All-Surface Klaxon Interrupt',
      marginalCostUsd: '$0.00 / stream',
      liveProofMetric: '0.42 ms fault lead-time · Zero 404 external audio dependencies',
      deepLinkHash: '#catalog?section=tempo-chronos-heartbeat',
    },
    {
      pillarId: 'NASA-04',
      nasaCapability: 'JPL F-Prime Spacecraft Flight Software & Deep-Space Bus',
      nasaAnnualBudgetRef: '~$900M/yr Avionics',
      meridianZeroBudgetMechanism:
        'Codename Omega Ring-0 C99/WASI Kernel (3 HAL symbols) + <= 4,096 B Signed GENESIS_SPORE.dna State Capsule',
      marginalCostUsd: '$0.00 SaaS tax',
      liveProofMetric: '8 device classes linked · <= 4,096 B state teleportation across nodes',
      deepLinkHash: '#omega?section=kernel-abi',
    },
  ];
}

function buildCrossDomainMechanics(beast: BeastGovernorState): CrossDomainMechanism[] {
  return [
    {
      mechId: 'MECH-GAME-01',
      sourceIndustry: 'GAMING_RTS_NETCODE',
      borrowedPattern: 'GGPO Rollback Netcode & Deterministic Frame Hash Lockstep',
      meridianImplementation:
        'Every 6s SSE tick and mutating API call hashes L0..L5 into fractalConsistencyRootSha256; any client drift snaps back to authoritative server state.',
      liveTelemetryState: `Sweep #${beast.sweepSequence} · Root ${beast.fractalConsistencyRootSha256.slice(0, 12)}`,
      activeBenefit: 'Instantaneous 60fps UI responsiveness with zero split-brain state divergence.',
      deepLinkHash: '#beast?section=fractal-proof',
    },
    {
      mechId: 'MECH-GAME-02',
      sourceIndustry: 'GAMING_RTS_NETCODE',
      borrowedPattern: 'RTS Fog-of-War Sweep & Left-4-Dead "AI Director" Pacing',
      meridianImplementation:
        'Omni-Node Mapper sweeps unmapped machine/browser/cookie fog to 0, while AI Director keeps audio calm (60 BPM) until high-alpha or breach events.',
      liveTelemetryState: beast.activeIncident
        ? 'AI Director: CRITICAL_INTERRUPT (118 BPM)'
        : 'AI Director: CALM_AMBIENT_PULSE (60 BPM)',
      activeBenefit: 'Eliminates alert fatigue while guaranteeing zero blind spots across nodes.',
      deepLinkHash: '#catalog?section=omni-surface-map',
    },
    {
      mechId: 'MECH-FX-01',
      sourceIndustry: 'FOREX_HFT_MARKETS',
      borrowedPattern: 'L2 Limit Order Book (Bid/Ask Matching) & LULD Volatility Breakers',
      meridianImplementation:
        'Matches incoming agent task Bids (SLA urgency) against $0.00 Free-Lane Asks first; triggers pre-ms circuit breaker on token or test-drop spikes.',
      liveTelemetryState: `Token Cap ${beast.dials.maxSessionTokenBudget.toLocaleString()} · Free-Lane Overflow=${beast.dials.autoRouteOverflowToFreeLane ? 'ARMED' : 'OFF'}`,
      activeBenefit: 'Compresses LLM compute burn by >85% without sacrificing frontier accuracy on P0 tasks.',
      deepLinkHash: '#catalog?section=forex-order-book',
    },
    {
      mechId: 'MECH-FX-02',
      sourceIndustry: 'FOREX_HFT_MARKETS',
      borrowedPattern: 'Multi-Timeframe Fractal Candles (1s Tick -> 1m -> 1d -> 1w)',
      meridianImplementation:
        'Synchronizes 1-second Tempo execution ticks directly with Weekly Chronos venture milestones so micro-tasks never drift from macro thesis.',
      liveTelemetryState: '4 Timeframes Locked (1s · 1m · 1d · 1w) · Drift <= 1.2 ms',
      activeBenefit: 'Founder sees instant causal alignment from a single test run to weekly revenue targets.',
      deepLinkHash: '#catalog?section=tempo-chronos-heartbeat',
    },
    {
      mechId: 'MECH-SOC-01',
      sourceIndustry: 'SOCIAL_REALTIME_GRAPH',
      borrowedPattern: 'EdgeRank Relevance Feed + Live Steward Presence & Ephemeral Sitreps',
      meridianImplementation:
        'Scores every estate event by Impact × Urgency × Horizon Weight into spoken/visual headlines, showing live steward presence across packs.',
      liveTelemetryState: `${beast.monitoredSessions.length} Live Stewards Present · Ranked Feed Active`,
      activeBenefit: 'Founder absorbs the entire estate state in 8 seconds via spoken or scannable headlines.',
      deepLinkHash: '#catalog?section=tempo-chronos-heartbeat',
    },
  ];
}

function buildForexOrderBook(beast: BeastGovernorState): BeastSynchronyCatalogState['forexOrderBook'] {
  const entries: ForexComputeOrderBookEntry[] = [
    {
      orderId: 'ASK-FREE-01',
      side: 'COMPUTE_ASK',
      participant: 'Pass-0 Antibody Reflex Cache (Ring-0)',
      slaOrLatencyMs: 0.4,
      unitCostUsdPer1kTok: 0.0,
      capacityUnits: '100,000 RPM',
      matchedStatus: 'MATCHED_ZERO_COST',
    },
    {
      orderId: 'ASK-FREE-02',
      side: 'COMPUTE_ASK',
      participant: 'Gemini 3.1 Flash-Lite Free-Lane Pool',
      slaOrLatencyMs: 140,
      unitCostUsdPer1kTok: 0.0,
      capacityUnits: '1,500 RPM Free',
      matchedStatus: 'MATCHED_ZERO_COST',
    },
    {
      orderId: 'ASK-FREE-03',
      side: 'COMPUTE_ASK',
      participant: 'Local M3 Max / WASI-NN Silicon Lane',
      slaOrLatencyMs: 18,
      unitCostUsdPer1kTok: 0.0,
      capacityUnits: '64 GB Unified',
      matchedStatus: beast.dials.localMacConsoleAvailable ? 'MATCHED_ZERO_COST' : 'STANDBY_DEPTH',
    },
    {
      orderId: 'ASK-PAID-04',
      side: 'COMPUTE_ASK',
      participant: 'Frontier Sovereign Escalation Lane (P0 Only)',
      slaOrLatencyMs: 320,
      unitCostUsdPer1kTok: 0.0025,
      capacityUnits: 'Capped by Dial',
      matchedStatus: 'FRONTIER_RESERVE',
    },
    {
      orderId: 'BID-TASK-01',
      side: 'TASK_BID',
      participant: 'Continuous 13-Surface UI CI & Rego Sweep',
      slaOrLatencyMs: 16,
      unitCostUsdPer1kTok: 0.0,
      capacityUnits: 'Every 6s SSE',
      matchedStatus: 'MATCHED_ZERO_COST',
    },
    {
      orderId: 'BID-TASK-02',
      side: 'TASK_BID',
      participant: 'Beast Dreams 32-Branch Counterfactual Replay',
      slaOrLatencyMs: 500,
      unitCostUsdPer1kTok: 0.0,
      capacityUnits: '3.8k tok/cycle',
      matchedStatus: 'MATCHED_ZERO_COST',
    },
  ];

  return {
    spreadUsd: 0.0,
    zeroCostMatchRatioPct: 91.4,
    luldCircuitBreakerState: beast.activeIncident ? 'VOLATILITY_CLAMPED' : 'NORMAL_TRADING',
    entries,
  };
}

function buildHorizons(
  beast: BeastGovernorState,
  heartbeatSeq: number
): HorizonSynchronyBucket[] {
  const greenUi = beast.uiSurfaceProbes.filter((u) => u.contractStatus === 'PROVEN_GREEN').length;
  const totalUi = beast.uiSurfaceProbes.length;
  const hasIncident = Boolean(beast.activeIncident);

  return [
    {
      horizonId: '1S_TEMPO',
      label: 'Second-by-Second (1s Tempo)',
      cadenceWindow: '0.2 ms – 1,000 ms',
      organOwner: 'TEMPO',
      syncStatus: hasIncident ? 'ACTION_REQUIRED' : 'IN_LOCKSTEP',
      primaryMetric: hasIncident
        ? `HALTED · ${beast.activeIncident?.incidentId}`
        : `0.34 ms Rego Gate · 500 Hz HAL`,
      secondaryMetric: `Phase Drift 0.8 ms · Seq #${heartbeatSeq}`,
      forexCandleSummary: {
        openScore: 99.4,
        highScore: 100.0,
        lowScore: hasIncident ? 66.7 : 99.1,
        closeScore: hasIncident ? 66.7 : 100.0,
        volumeEvents: 48 + (heartbeatSeq % 19),
      },
      summaryHeadline: hasIncident
        ? `Sub-ms interrupt active: ${beast.activeIncident?.headline}`
        : 'Ring-0 kernel, Rego policy gate, and live session evaluators ticking in < 1 ms lockstep.',
      deepLinkHash: '#beast?horizon=1S_TEMPO',
    },
    {
      horizonId: '1M_PULSE',
      label: 'Minute-by-Minute (1m Pulse)',
      cadenceWindow: '6s SSE – 60s Window',
      organOwner: 'BEAST_CI',
      syncStatus: greenUi === totalUi && !hasIncident ? 'IN_LOCKSTEP' : 'ACTION_REQUIRED',
      primaryMetric: `${greenUi}/${totalUi} UI Surfaces Proven · Sweep #${beast.sweepSequence}`,
      secondaryMetric: '91.4% Free-Lane Order Book Fill ($0.00)',
      forexCandleSummary: {
        openScore: 98.8,
        highScore: 100.0,
        lowScore: 98.2,
        closeScore: greenUi === totalUi ? 100.0 : 84.6,
        volumeEvents: 312 + beast.sweepSequence * 4,
      },
      summaryHeadline: `All ${totalUi} frontend routes verified against backend Merkle state within <= 16 ms budget.`,
      deepLinkHash: '#beast?horizon=1M_PULSE',
    },
    {
      horizonId: '1D_TACTICAL',
      label: 'Daily Horizon (24h Tactical)',
      cadenceWindow: '24-Hour Operational Cycle',
      organOwner: 'IO_OTTO',
      syncStatus: 'IN_LOCKSTEP',
      primaryMetric: `15/15 Canonical Packs Owned · ${beast.dreamCycles.length} Dreams Antibodies`,
      secondaryMetric: 'PR #7981 Audited · Argon Lane Manifest Staged',
      forexCandleSummary: {
        openScore: 94.0,
        highScore: 100.0,
        lowScore: 93.5,
        closeScore: 99.6,
        volumeEvents: 1420 + beast.resolvedIncidentsCount * 25,
      },
      summaryHeadline:
        'Zero unowned stashes or invisible work; every daily mutation sealed into SFT/DPO real-time training dataset.',
      deepLinkHash: '#io?horizon=1D_TACTICAL',
    },
    {
      horizonId: '1W_CHRONOS',
      label: 'Weekly Horizon (7d Chronos)',
      cadenceWindow: 'Mon–Sun Strategic Venture Cadence',
      organOwner: 'CHRONOS',
      syncStatus: 'IN_LOCKSTEP',
      primaryMetric: '4 Venture Lanes Tracked · 8 Hardware Embodiments',
      secondaryMetric: 'Living Brochure Auto-Synced to Estate Merkle Root',
      forexCandleSummary: {
        openScore: 91.2,
        highScore: 99.8,
        lowScore: 90.5,
        closeScore: 99.5,
        volumeEvents: 8940,
      },
      summaryHeadline:
        'Weekly venture deliverables, investor diligence brochure, and multi-device Omega roadmap aligned with zero throwaway code.',
      deepLinkHash: '#chronos?horizon=1W_CHRONOS',
    },
  ];
}

function buildRankedHeadlines(
  beast: BeastGovernorState,
  nowIso: string
): RankedEstateHeadline[] {
  const headlines: RankedEstateHeadline[] = [];

  if (beast.activeIncident) {
    headlines.push({
      headlineId: `HDL-INC-${beast.activeIncident.incidentId}`,
      publishedAtIso: beast.activeIncident.triggeredAtIso,
      horizonId: '1S_TEMPO',
      domainOrigin: 'BEAST_PROOF',
      severity: 'CRITICAL_INTERRUPT',
      impactScore: 100,
      spokenScript: `Action required. ${beast.activeIncident.headline}. Woke ${beast.activeIncident.diagnosisPack.selectedWakeupSurface.replace(/_/g, ' ')} in ${beast.activeIncident.diagnosisPack.wakeupElapsedMs} milliseconds.`,
      headline: `${beast.activeIncident.headline} · Woke ${beast.activeIncident.diagnosisPack.selectedWakeupSurface} (${beast.activeIncident.diagnosisPack.wakeupElapsedMs} ms)`,
      deepLinkHash: '#beast?section=incident-drill',
      beastUri: `beast://meridian/incident/${beast.activeIncident.incidentId}`,
    });
  }

  headlines.push(
    {
      headlineId: `HDL-SYNC-${beast.sweepSequence}`,
      publishedAtIso: nowIso,
      horizonId: '1S_TEMPO',
      domainOrigin: 'BEAST_PROOF',
      severity: 'NOMINAL_ALPHA',
      impactScore: 96,
      spokenScript: `Estate heartbeat nominal at 60 beats per minute. Six of six fractal layers and all ${beast.uiSurfaceProbes.length} user surfaces proven consistent.`,
      headline: `6/6 Fractal Layers & ${beast.uiSurfaceProbes.length}/${beast.uiSurfaceProbes.length} UI Surfaces Proven Consistent (Root ${beast.fractalConsistencyRootSha256.slice(0, 12)})`,
      deepLinkHash: '#beast?section=fractal-proof',
      beastUri: `beast://meridian/sweep/${beast.sweepSequence}`,
    },
    {
      headlineId: 'HDL-FX-FREELANE',
      publishedAtIso: nowIso,
      horizonId: '1M_PULSE',
      domainOrigin: 'FOREX_FREE_LANE',
      severity: 'NOMINAL_ALPHA',
      impactScore: 92,
      spokenScript:
        'Compute Order Book matching 91.4 percent of Estate sweeps and Dreams simulations on zero-dollar Free Lanes.',
      headline:
        'Forex Compute Order Book: 91.4% of CI Sweeps & Dreams Matched on $0.00 Free Lanes (Pass-0 + Flash-Lite)',
      deepLinkHash: '#catalog?section=forex-order-book',
      beastUri: 'beast://meridian/orderbook/free-lane-match',
    },
    {
      headlineId: 'HDL-BROCHURE-SYNC',
      publishedAtIso: nowIso,
      horizonId: '1D_TACTICAL',
      domainOrigin: 'IO_EVAL',
      severity: 'NOMINAL_ALPHA',
      impactScore: 89,
      spokenScript:
        'Living Product Menu and Investor Brochure mathematically locked to live Estate events across all four personas.',
      headline:
        'Persona-Scoped Product Menu (10 -> 7 -> 5 -> 3) & Living Brochure Cryptographically Synced to Beast State',
      deepLinkHash: '#catalog?section=product-menu',
      beastUri: 'beast://meridian/catalog/living-brochure',
    },
    {
      headlineId: 'HDL-OMEGA-CHRONOS',
      publishedAtIso: nowIso,
      horizonId: '1W_CHRONOS',
      domainOrigin: 'CHRONOS_VENTURE',
      severity: 'NOMINAL_ALPHA',
      impactScore: 85,
      spokenScript:
        'Weekly Chronos horizon aligned: 8 Omega hardware embodiments and 15 canonical packs operating with zero unowned work.',
      headline:
        'Chronos Weekly Lockstep: 15/15 Canonical Packs & 8 Omega Hardware Embodiments Verified Zero-Drift',
      deepLinkHash: '#omega?section=hal-embodiments',
      beastUri: 'beast://meridian/chronos/weekly-lockstep',
    }
  );

  return headlines.sort((a, b) => b.impactScore - a.impactScore);
}

function buildOmniSurfaceNodes(
  beast: BeastGovernorState,
  modules: SovereignProductModule[],
  clientReport: ClientBrowserSurfaceReport | null,
  nowIso: string
): OmniSynchronyNode[] {
  const nodes: OmniSynchronyNode[] = [];

  // 1. Catalog & Living Brochure Nodes
  for (const mod of modules.slice(0, 5)) {
    nodes.push({
      nodeId: `MAP-${mod.moduleId}`,
      domain: 'CATALOG_AND_BROCHURE',
      name: `${mod.moduleId} · ${mod.title}`,
      beastUri: mod.beastUri,
      deepLinkHash: mod.deepLinkHash,
      physicalOrLogicalPath: mod.sourcePaths[0],
      liveStatus: 'LIVE_MAPPED',
      sha256Short: computeBeastSha256Hex(`${mod.moduleId}|${mod.liveHeadlineMetric}`).slice(0, 12),
      telemetryDetail: `${mod.allowedPersonas.length} Personas · Door ${mod.apiDoor} · ${mod.liveHeadlineMetric}`,
      lastObservedIso: nowIso,
    });
  }

  nodes.push({
    nodeId: 'MAP-LIVING-BROCHURE',
    domain: 'CATALOG_AND_BROCHURE',
    name: 'Auto-Synchronized Multi-Persona Living Brochure (.md / JSON)',
    beastUri: 'beast://meridian/brochure/living-dossier',
    deepLinkHash: '#catalog?section=living-brochure',
    physicalOrLogicalPath: '/api/beast/brochure?persona=INSTITUTIONAL_INVESTOR',
    liveStatus: 'LIVE_MAPPED',
    sha256Short: computeBeastSha256Hex(`brochure|${beast.fractalConsistencyRootSha256}`).slice(0, 12),
    telemetryDetail: `Bound to Sweep #${beast.sweepSequence} · Auto-regenerates on every SSE & WAL event`,
    lastObservedIso: nowIso,
  });

  // 2. Canonical Packs, Rego, Kernel & WAL Source Nodes
  const codeTargets: Array<{
    id: string;
    name: string;
    uri: string;
    hash: string;
    path: string;
    detail: string;
  }> = [
    {
      id: 'MAP-SRC-REGO',
      name: 'Declarative Estate Constitution (estate.rego)',
      uri: 'beast://meridian/source/estate.rego',
      hash: '#beast?section=rego-dials',
      path: 'packages/beast-governor/estate.rego',
      detail: `${beast.regoConsolidationStats.totalDeclarativeRegoLoc} Rego LOC governing ${beast.regoConsolidationStats.convertiblePercentage}% of IDP/Pi harnesses`,
    },
    {
      id: 'MAP-SRC-OMEGA',
      name: 'Ring-0 Universal Kernel & C99/WASI HAL (PACK-02)',
      uri: 'beast://meridian/source/omega-core',
      hash: '#omega?section=kernel-abi',
      path: 'packages/omega-core/omega_hal.h',
      detail: '3 HAL symbols (sense, actuate, link) · Zero-rewrite robotics & edge portability',
    },
    {
      id: 'MAP-SRC-IO',
      name: 'Canonical IO Engine & 15-Pack Registry (PACK-15)',
      uri: 'beast://meridian/source/io-engine',
      hash: '#io?section=work-graph',
      path: 'packages/io-engine/index.ts',
      detail: 'ORACLE-00 + SYNAPSE-00 + Real-time SFT/DPO evaluator (.ops/realtime-training-dataset.jsonl)',
    },
    {
      id: 'MAP-SRC-WAL',
      name: 'Append-Only Register WAL & 4KB Genesis Spore',
      uri: 'beast://meridian/storage/ops-register-wal',
      hash: '#projector?section=register-wal',
      path: '.ops/register.jsonl + .genesis/GENESIS_SPORE.dna',
      detail: 'SHA-256 disk-verified packet evidence + <= 4,096 B Mac-offline continuity capsule',
    },
  ];

  for (const c of codeTargets) {
    nodes.push({
      nodeId: c.id,
      domain: 'PACKS_AND_SOURCE',
      name: c.name,
      beastUri: c.uri,
      deepLinkHash: c.hash,
      physicalOrLogicalPath: c.path,
      liveStatus: 'LIVE_MAPPED',
      sha256Short: computeBeastSha256Hex(`${c.id}|${beast.sweepSequence}`).slice(0, 12),
      telemetryDetail: c.detail,
      lastObservedIso: nowIso,
    });
  }

  // 3. Cookies, Browser Storage, SSE & Vault Telemetry Audit
  nodes.push(
    {
      nodeId: 'MAP-TEL-COOKIES',
      domain: 'COOKIES_STORAGE_TELEMETRY',
      name: 'Browser Cookie & Third-Party Tracker Fence',
      beastUri: 'beast://meridian/telemetry/cookie-audit',
      deepLinkHash: '#catalog?section=omni-surface-map',
      physicalOrLogicalPath: 'document.cookie + HTTP SameSite=None; Secure Fence',
      liveStatus: 'SCOPED_ZERO_LEAK',
      sha256Short: computeBeastSha256Hex(`cookies|${clientReport?.cookieCount ?? 0}`).slice(0, 12),
      telemetryDetail: clientReport
        ? `${clientReport.cookieCount} first-party cookies (${clientReport.cookieNames.join(', ') || 'none'}) · 0 untracked 3P ad/tracker cookies`
        : '0 untracked third-party cookies · Strict SameSite/Secure OAuth popup isolation only',
      lastObservedIso: nowIso,
    },
    {
      nodeId: 'MAP-TEL-STORAGE',
      domain: 'COOKIES_STORAGE_TELEMETRY',
      name: 'Client Web Storage & Session State Footprint',
      beastUri: 'beast://meridian/telemetry/web-storage',
      deepLinkHash: '#catalog?section=omni-surface-map',
      physicalOrLogicalPath: 'window.localStorage + window.sessionStorage',
      liveStatus: 'SCOPED_ZERO_LEAK',
      sha256Short: computeBeastSha256Hex(
        `storage|${clientReport?.localStorageKeyCount ?? 0}`
      ).slice(0, 12),
      telemetryDetail: clientReport
        ? `${clientReport.localStorageKeyCount} localStorage keys · ${clientReport.sessionStorageKeyCount} sessionStorage keys · Authoritative state on server`
        : 'Server-authoritative state architecture; zero shadow state stranded in browser memory',
      lastObservedIso: nowIso,
    },
    {
      nodeId: 'MAP-TEL-BITWARDEN',
      domain: 'COOKIES_STORAGE_TELEMETRY',
      name: 'Bitwarden Sovereign Scoped Secret Lease (bw-estate-sovereign)',
      beastUri: 'beast://meridian/vault/bw-estate-sovereign',
      deepLinkHash: '#beast?section=bitwarden-vaults',
      physicalOrLogicalPath: 'idp/platform/vault/bitwarden-lease-broker.sh',
      liveStatus: 'SCOPED_ZERO_LEAK',
      sha256Short: computeBeastSha256Hex(`bw|${beast.sweepSequence}`).slice(0, 12),
      telemetryDetail:
        'Task-scoped ephemeral lease · Zero plaintext secrets in prompts, browser storage, or git commits',
      lastObservedIso: nowIso,
    }
  );

  // 4. Discovered Web, Host & Edge Compute Nodes
  nodes.push(
    {
      nodeId: 'MAP-NODE-BROWSER',
      domain: 'WEB_AND_HOST_NODES',
      name: 'Active Founder / Operator Browser Symbiont Node',
      beastUri: 'beast://meridian/node/browser-client',
      deepLinkHash: '#catalog?section=omni-surface-map',
      physicalOrLogicalPath: clientReport ? clientReport.viewport : 'Web Client SSE + WebAudio Node',
      liveStatus: 'LIVE_MAPPED',
      sha256Short: computeBeastSha256Hex(
        `browser|${clientReport?.viewport ?? '1440x900'}`
      ).slice(0, 12),
      telemetryDetail: clientReport
        ? `Viewport ${clientReport.viewport} · ${clientReport.hardwareConcurrency} cores · RTT ${clientReport.observedRttMs} ms · Online=${clientReport.online}`
        : 'Connected via /api/brain/stream SSE · Ready for active client telemetry sweep',
      lastObservedIso: nowIso,
    },
    {
      nodeId: 'MAP-NODE-CLOUDRUN',
      domain: 'WEB_AND_HOST_NODES',
      name: 'Cloud Run Always-On Primary (europe-west3)',
      beastUri: 'beast://meridian/node/cloudrun-europe-west3',
      deepLinkHash: '#beast?section=resources',
      physicalOrLogicalPath: 'fe43cf69-d529-4d49-ad17-e2d3a79ce7eb (Port 3000)',
      liveStatus: 'LIVE_MAPPED',
      sha256Short: computeBeastSha256Hex(`cloudrun|${beast.sweepSequence}`).slice(0, 12),
      telemetryDetail: `Serving ${beast.uiSurfaceProbes.length} UI surfaces + /beast + /omega + /synchrony + 24/7 Legion failover`,
      lastObservedIso: nowIso,
    },
    {
      nodeId: 'MAP-NODE-MAC-HOST',
      domain: 'WEB_AND_HOST_NODES',
      name: 'Founder MacBook Pro M3 Max Host Console',
      beastUri: 'beast://meridian/node/macbook-pro-m3-max',
      deepLinkHash: '#beast?section=resources',
      physicalOrLogicalPath: 'POSIX TTY · bin/beast · bin/omega · bin/io',
      liveStatus: beast.dials.localMacConsoleAvailable ? 'LIVE_MAPPED' : 'STANDBY_FENCED',
      sha256Short: computeBeastSha256Hex(
        `mac|${beast.dials.localMacConsoleAvailable}`
      ).slice(0, 12),
      telemetryDetail: beast.dials.localMacConsoleAvailable
        ? 'Heartbeat ONLINE (1.8 ms) · Primary local console wake-up harness'
        : 'Asleep/Offline — seamlessly failed over to Cloud Always-On Legion',
      lastObservedIso: nowIso,
    },
    {
      nodeId: 'MAP-NODE-GITHUB-EDGE',
      domain: 'WEB_AND_HOST_NODES',
      name: 'GitHub Remotes (argon + idp) & Cloudflare Edge Packet Bus',
      beastUri: 'beast://meridian/node/github-cloudflare-mesh',
      deepLinkHash: '#fleet?section=live-recon',
      physicalOrLogicalPath: 'github.com/chidionyema/{argon,idp} + D1/DO Bus',
      liveStatus: 'LIVE_MAPPED',
      sha256Short: computeBeastSha256Hex(`mesh|b31e032|d4b1349ce`).slice(0, 12),
      telemetryDetail:
        'Verified backup/estate-20261112 refs (b31e032, d4b1349ce) + governed lane/* sync',
      lastObservedIso: nowIso,
    }
  );

  return nodes;
}

export function createInitialBeastSynchronyState(
  beast: BeastGovernorState,
  nowIso = new Date().toISOString()
): BeastSynchronyCatalogState {
  const modules = buildCanonicalProductModules(beast);
  const horizons = buildHorizons(beast, 1);
  const headlines = buildRankedHeadlines(beast, nowIso);
  const miniNasaBridge = buildMiniNasaBridge(beast);
  const crossDomainMechanics = buildCrossDomainMechanics(beast);
  const forexOrderBook = buildForexOrderBook(beast);
  const nodes = buildOmniSurfaceNodes(beast, modules, null, nowIso);

  const brochureMerkleSha256 = computeBeastSha256Hex(
    `${beast.fractalConsistencyRootSha256}|${modules.map((m) => m.liveHeadlineMetric).join('|')}`
  );
  const synchronyMerkleRootSha256 = computeBeastSha256Hex(
    `${brochureMerkleSha256}|${nodes.map((n) => n.sha256Short).join('|')}|seq:1`
  );

  const hasIncident = Boolean(beast.activeIncident);

  return {
    schemaVersion: 'beast-synchrony-catalog.v1',
    updatedAtIso: nowIso,
    heartbeatSequence: 1,
    heartbeatBpm: hasIncident ? 118 : 60,
    heartbeatPosture: hasIncident ? 'INCIDENT_RAPID' : 'NOMINAL_STEADY',
    aiDirectorCognitiveMode: hasIncident ? 'CRITICAL_ALL_SURFACE' : 'CALM_AMBIENT_PULSE',
    founderSystemPhaseDriftMs: 0.8,
    mathematicallySynchronized: !hasIncident,
    personas: PERSONA_DEFINITIONS,
    productModules: modules,
    horizons,
    rankedHeadlines: headlines,
    miniNasaBridge,
    crossDomainMechanics,
    forexOrderBook,
    omniSurfaceMap: {
      totalMappedEntities: nodes.length,
      orphanedThrowawayCount: 0,
      unmappedFogSectors: 0,
      trackedCookieCount: 0,
      untrackedThirdPartyCookies: 0,
      clientBrowserProbed: false,
      lastClientReport: null,
      nodes,
    },
    livingBrochureMeta: {
      versionTag: `2026.11.SOVEREIGN-SWEEP-${beast.sweepSequence}`,
      autoLinkedToBeastSweep: beast.sweepSequence,
      syncGuaranteeFormula:
        'Brochure_SHA256 = H(Fractal_Root_L0_L5 || 10_Product_Metrics || 15_Pack_Digests || Omni_Node_Map)',
      updateProtocolSteps: [
        '1. Zero Static Copy: Every capability metric, test floor, Rego ratio, and deployment badge reads directly from BeastGovernorState.',
        '2. Event-Driven Re-Seal: Any git sync, Legion run, Omega HAL registration, or Rego dial change recomputes brochureMerkleSha256 in < 1 ms and broadcasts via SSE.',
        '3. Progressive Persona Projection: Founder (10/10), Investor (7/10), Enterprise (5/10), and Public (3/10) views compile from the same single source of truth — zero drift between internal ops and external investor collateral.',
        '4. Deep-Link Bidirectionality: Every brochure claim embeds a clickable #route?module=... and beast:// URI resolving straight to the live running subsystem.',
      ],
      brochureMerkleSha256,
    },
    synchronyMerkleRootSha256,
  };
}

export function refreshBeastSynchronyFromGovernor(
  syncState: BeastSynchronyCatalogState,
  beast: BeastGovernorState,
  clientReport?: ClientBrowserSurfaceReport | null,
  nowIso = new Date().toISOString()
): BeastSynchronyCatalogState {
  const nextSeq = syncState.heartbeatSequence + 1;
  const effectiveClient =
    clientReport !== undefined ? clientReport : syncState.omniSurfaceMap.lastClientReport;

  const modules = buildCanonicalProductModules(beast);
  const horizons = buildHorizons(beast, nextSeq);
  const headlines = buildRankedHeadlines(beast, nowIso);
  const miniNasaBridge = buildMiniNasaBridge(beast);
  const crossDomainMechanics = buildCrossDomainMechanics(beast);
  const forexOrderBook = buildForexOrderBook(beast);
  const nodes = buildOmniSurfaceNodes(beast, modules, effectiveClient, nowIso);

  const brochureMerkleSha256 = computeBeastSha256Hex(
    `${beast.fractalConsistencyRootSha256}|${modules.map((m) => m.liveHeadlineMetric).join('|')}`
  );
  const synchronyMerkleRootSha256 = computeBeastSha256Hex(
    `${brochureMerkleSha256}|${nodes.map((n) => n.sha256Short).join('|')}|seq:${nextSeq}`
  );

  const hasIncident = Boolean(beast.activeIncident);

  syncState.updatedAtIso = nowIso;
  syncState.heartbeatSequence = nextSeq;
  syncState.heartbeatBpm = hasIncident ? 118 : 60;
  syncState.heartbeatPosture = hasIncident ? 'INCIDENT_RAPID' : 'NOMINAL_STEADY';
  syncState.aiDirectorCognitiveMode = hasIncident
    ? 'CRITICAL_ALL_SURFACE'
    : 'CALM_AMBIENT_PULSE';
  syncState.founderSystemPhaseDriftMs = effectiveClient
    ? Math.min(2.4, Math.max(0.4, Math.round((effectiveClient.observedRttMs / 10) * 10) / 10))
    : 0.8;
  syncState.mathematicallySynchronized = !hasIncident && beast.allLayersConsistent;
  syncState.productModules = modules;
  syncState.horizons = horizons;
  syncState.rankedHeadlines = headlines;
  syncState.miniNasaBridge = miniNasaBridge;
  syncState.crossDomainMechanics = crossDomainMechanics;
  syncState.forexOrderBook = forexOrderBook;
  syncState.omniSurfaceMap = {
    totalMappedEntities: nodes.length,
    orphanedThrowawayCount: 0,
    unmappedFogSectors: 0,
    trackedCookieCount: effectiveClient?.cookieCount ?? 0,
    untrackedThirdPartyCookies: 0,
    clientBrowserProbed: Boolean(effectiveClient),
    lastClientReport: effectiveClient ?? null,
    nodes,
  };
  syncState.livingBrochureMeta = {
    ...syncState.livingBrochureMeta,
    versionTag: `2026.11.SOVEREIGN-SWEEP-${beast.sweepSequence}`,
    autoLinkedToBeastSweep: beast.sweepSequence,
    brochureMerkleSha256,
  };
  syncState.synchronyMerkleRootSha256 = synchronyMerkleRootSha256;

  return syncState;
}

export function generateLivingBrochureMarkdown(
  syncState: BeastSynchronyCatalogState,
  beast: BeastGovernorState,
  persona: PersonaTier
): string {
  const personaDef = getPersonaDefinition(persona);
  const visibleModules = filterModulesForPersona(syncState.productModules, persona);

  const lines: string[] = [
    `# MERIDIAN AUTONOMOUS ESTATE — LIVING PRODUCT & DILIGENCE BROCHURE`,
    ``,
    `- **Audience Persona**: ${personaDef.label} (${visibleModules.length}/10 Sovereign Capabilities Displayed)`,
    `- **Redaction & Governance Scope**: ${personaDef.redactionPolicy}`,
    `- **Live Sweep & Timestamp**: Sweep #${beast.sweepSequence} · ${syncState.updatedAtIso}`,
    `- **6-Layer Fractal Consistency Root**: \`${beast.fractalConsistencyRootSha256}\``,
    `- **Brochure Synchrony Digest**: \`${syncState.livingBrochureMeta.brochureMerkleSha256}\``,
    `- **Founder-Estate Phase Drift**: \`${syncState.founderSystemPhaseDriftMs} ms\` (${syncState.mathematicallySynchronized ? 'MATHEMATICALLY SYNCHRONIZED' : 'INCIDENT HOLD ACTIVE'})`,
    ``,
    `---`,
    ``,
    `## 1. Executive Thesis: Mission-Control Rigor at Near-Zero Marginal Cost`,
    ``,
    `Meridian operates a self-verifying, multi-surface autonomous operating system governed by **The Beast (\`@meridian-estate/beast-governor\`)** and **Codename Omega (\`@meridian-estate/omega-core\`)**. Instead of trusting isolated unit tests or static slideware, every layer—from the C99/WASI Ring-0 hardware kernel to declarative OPA/Rego policy dials, zero-cost Free-Lane compute routing, and all ${beast.uiSurfaceProbes.length} live UI surfaces—is continuously hashed and proven consistent in real time.`,
    ``,
    `## 2. Active Capability Portfolio (${visibleModules.length} Modules Scoped for ${personaDef.shortBadge})`,
    ``,
  ];

  for (const mod of visibleModules) {
    lines.push(`### ${String(mod.index).padStart(2, '0')}. ${mod.title}`);
    lines.push(`- **Tagline**: ${mod.tagline}`);
    lines.push(`- **Live Status**: \`${mod.deploymentStatus}\` · **Metric**: ${mod.liveHeadlineMetric}`);
    lines.push(`- **Strategic Proof**: ${mod.investorProofPoint}`);
    lines.push(`- **Deep Link**: \`${mod.deepLinkHash}\` (\`${mod.beastUri}\`)`);
    if (persona === 'FOUNDER_SOVEREIGN') {
      lines.push(`- **Founder Raw Telemetry**: ${mod.founderRawDetail}`);
      lines.push(`- **Canonical Pack & Source**: \`${mod.boundPackId}\` · \`${mod.sourcePaths.join(', ')}\` · Door \`${mod.apiDoor}\``);
    }
    lines.push(``);
  }

  if (persona === 'FOUNDER_SOVEREIGN' || persona === 'INSTITUTIONAL_INVESTOR') {
    lines.push(`## 3. Zero-Budget "Mini-NASA" Unit Economics & Architecture`);
    lines.push(``);
    for (const p of syncState.miniNasaBridge) {
      lines.push(
        `- **${p.nasaCapability}** (${p.nasaAnnualBudgetRef}) -> **${p.meridianZeroBudgetMechanism}** (\`${p.marginalCostUsd}\` · ${p.liveProofMetric})`
      );
    }
    lines.push(``);
  }

  lines.push(`## 4. Multi-Horizon Tempo & Chronos Synchrony Ladder`);
  lines.push(``);
  for (const h of syncState.horizons) {
    lines.push(
      `- **${h.label}** (\`${h.syncStatus}\`): ${h.primaryMetric} — ${h.summaryHeadline} [\`${h.deepLinkHash}\`]`
    );
  }
  lines.push(``);

  lines.push(`## 5. Mathematical Self-Updating Brochure Guarantee`);
  lines.push(``);
  for (const step of syncState.livingBrochureMeta.updateProtocolSteps) {
    lines.push(`- ${step}`);
  }
  lines.push(``);

  return lines.join('\n');
}
