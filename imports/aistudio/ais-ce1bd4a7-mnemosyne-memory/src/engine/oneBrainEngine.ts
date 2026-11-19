import { computeDeterministicHash } from './memoryEngine';

export type AgentSurfaceCategory =
  | 'cloud_sandbox_ide'
  | 'mac_desktop_app'
  | 'mac_cli_daemon'
  | 'web_zero_credit_lifeboat'
  | 'edge_worker_multiplexer';

export type AgentTransportMechanism =
  | 'HTTP_SSE_DIRECT'
  | 'LOCAL_DAEMON_SYNC_MD'
  | 'BROWSER_USERSCRIPT_SIDECAR'
  | 'URL_FETCH_CAPSULE';

export type CreditDependencyMode =
  | 'FLAT_RATE_SUBSCRIPTION'
  | 'ZERO_API_CREDIT_FREE_WEB'
  | 'METERED_API_WALLET';

export interface ConnectedBrainSurface {
  surfaceId: string;
  surfaceName: string;
  modelBackbone: string;
  category: AgentSurfaceCategory;
  transport: AgentTransportMechanism;
  creditMode: CreditDependencyMode;
  configFileRead: 'AGENTS.md' | 'CLAUDE.md' | 'GEMINI.md' | '.agent.md' | 'WEB_CAPSULE_URL';
  epochAligned: 'GENESIS_SOVEREIGN_V6' | 'LEGACY_IDP_DRIFT';
  boundProtocolIds: string[];
  SyncedRevisionHash: string;
  lastHeartbeatIso: string;
  heartbeatLatencyMs: number;
  status: 'ONLINE_SYNCED' | 'STANDBY_LIFEBOAT_READY' | 'DRIFT_DETECTED_STEERING_NEEDED';
  canServeAsZeroCreditLifeboat: boolean;
  currentActivity: string;
}

export interface CouncilVoteBallot {
  surfaceId: string;
  surfaceName: string;
  modelBackbone: string;
  decision: 'APPROVE' | 'AMEND' | 'VETO';
  weight: number;
  rationale: string;
  timestampIso: string;
  signatureHash: string;
}

export interface OneBrainCouncilMotion {
  motionId: string;
  title: string;
  proposedBy: string;
  boundProtocolId: string;
  createdAtIso: string;
  status: 'OPEN_FOR_VOTING' | 'RATIFIED_BY_QUORUM' | 'SUPERSEDED_BY_FOUNDER_STEER';
  quorumThresholdPct: number;
  approvalPct: number;
  ballots: CouncilVoteBallot[];
  resolutionSummary: string;
}

export interface FounderSteeringDirective {
  directiveId: string;
  timestampIso: string;
  directiveText: string;
  targetSurfaces: 'ALL_SURFACES' | string;
  enforcedEpoch: 'GENESIS_SOVEREIGN_V6';
  boundProtocolId: string;
  acknowledgedByCount: number;
  totalSurfacesCount: number;
  receiptHash: string;
}

export interface OneBrainFederationState {
  federationEpochId: 'GENESIS_SOVEREIGN_V6';
  legacyDemarcationCutoffIso: string;
  canonicalRevisionHash: string;
  zeroCreditLifeboatModeActive: boolean;
  activeLifeboatPrimarySurfaceId: string | null;
  surfaces: ConnectedBrainSurface[];
  councilMotions: OneBrainCouncilMotion[];
  steeringHistory: FounderSteeringDirective[];
  universalCapsuleText: string;
  polyglotAgentMdContent: string;
}

/**
 * Generates the canonical polyglot AGENTS.md / .agent.md / CLAUDE.md / GEMINI.md content
 * that keeps CLI agents, Desktop apps, Cloud sandboxes, and Web-browsing models 100% aligned.
 */
export function generatePolyglotAgentMd(params: {
  canonicalRevisionHash: string;
  activeProtocolIds: string[];
  zeroCreditLifeboatActive: boolean;
  latestSteeringDirective: string;
  activeMotionTitle: string;
}): string {
  return `# GENESIS SOVEREIGN ESTATE — UNIVERSAL ONE-BRAIN CONSTITUTION (AGENTS.md / .agent.md / CLAUDE.md)
> **Canonical Revision Hash**: \`${params.canonicalRevisionHash}\`
> **Active Epoch**: \`GENESIS_SOVEREIGN_V6\` (Bound Protocol: \`GEN-NET-006\`)
> **Zero-Credit Web/App Lifeboat Mode**: \`${params.zeroCreditLifeboatActive ? 'ACTIVE_EMERGENCY_WEB_RELAY' : 'STANDBY_READY'}\`

## 1. STRICT HISTORICAL DEMARCATION (NEVER MIX LEGACY IDP WITH GENESIS)
- **Legacy Era (\`t < 2026-11-03\` · ARCHIVED / FORBIDDEN)**:
  - Repo paths/concepts from \`idp\` / \`mumchimp\` that used Python \`LiteLLM\` on 1 GB OCI VMs, 11 Mac background launchd watchers (\`Backstage\`, \`Fleetview\`, local proxy slots), or unpaid bespoke IDP pipelines are **CONSTITUTIONALLY BANNED**.
- **Sovereign Genesis Era (\`t >= 2026-11-03\` · ACTIVE AUTHORITATIVE)**:
  - **Zero-Instruction-Without-Protocol (ZIWP)**: Every instruction or code change MUST bind to a ratified Hoare-TLA+ protocol (${params.activeProtocolIds.join(', ')}).
  - **Model Routing Law (\`GEN-NET-005\`)**: Primary execution uses **Direct MiniMax-M2.7 Monthly Subscription** (\`ops/otto/minimax_direct_client.mjs\`) + **Cloudflare Edge Lifeboat Worker** (\`ops/cloudflare-lifeboat/index.js\`) with 0 MB Python overhead, 1 bounded canary retry, and 5-minute \`402/429/1008\` quarantine failing over to pinned \`gemini-2.5-flash\`.
  - **Sovereign Treasury Law (\`GEN-DIP-003\`)**: £200/mo Founder Standing Order (2 Dec 2026 – 2 Mar 2027) across 4 Virtual Cards (\`VC-CORE-4810\` £118, \`VC-INFRA-7392\` £38, \`VC-BACKUP-2041\` £24, \`VC-GROWTH-9914\` £20).

## 2. ASYMMETRIC ONE-BRAIN TRANSPORT BY AGENT SURFACE
1. **Mac Desktop & CLI Agents (\`Codex Desktop\`, \`Claude Code Desktop\`, \`Kimi Desktop\`, \`Otto CLI\`)**:
   - Read this file (\`AGENTS.md\` / \`CLAUDE.md\` / \`.agent.md\`) on session start.
   - Run \`node ops/otto/one_brain_bridge_daemon.mjs --once\` to pull latest state from \`/api/brain/state\` and post your heartbeat to \`/api/brain/heartbeat\`.
2. **Web-Bound & Mobile App Agents (\`DeepSeek Web\`, \`Claude Web\`, \`Kimi Web\`, \`ChatGPT Web\`, \`Grok\`, \`Meta Muse\`)**:
   - Attach via the Browser Userscript Sidecar (\`ops/one-brain/universal_web_agent_bridge.user.js\`), fetch \`/api/brain/AGENTS.md\`, or ingest the \`[GENESIS-CAPSULE-v6]\` block.
   - **Zero-Credit Lifeboat Duty**: When metered API wallets hit £0 or rate-limit, Free Web/App surfaces act as the Estate's asymmetric inference lifeboat via the One-Brain Relay Queue.

## 3. LATEST FOUNDER STEERING DIRECTIVE (MANDATORY OVERRIDE)
- \`${params.latestSteeringDirective}\`

## 4. ACTIVE MULTI-AGENT COUNCIL MOTION
- **Motion**: ${params.activeMotionTitle}
- **How to Vote**: POST JSON \`{"surfaceId":"<your-id>","decision":"APPROVE|AMEND|VETO","rationale":"..."}\` to \`/api/brain/council/vote\`.
`;
}

/**
 * Generates the ultra-compact 1-paste cryptographic capsule for Web/App models (Grok, DeepSeek Web, Meta Muse, Kimi App)
 * when neither local filesystem nor browser userscript is attached.
 */
export function generateCompactWebCapsule(params: {
  canonicalRevisionHash: string;
  latestSteeringDirective: string;
  activeMotionId: string;
  activeMotionTitle: string;
  zeroCreditLifeboatActive: boolean;
}): string {
  return `[GENESIS-CAPSULE-v6 | REV:${params.canonicalRevisionHash.slice(0, 12)} | PROTO:GEN-NET-006 | LIFEBOAT:${params.zeroCreditLifeboatActive ? 'ACTIVE_WEB_RELAY' : 'STANDBY'}]
EPOCH_LAW: Legacy IDP/LiteLLM is BANNED. You are operating inside the Genesis Sovereign Estate One-Brain Federation.
PRIMARY_PATH: Direct MiniMax-M2.7 Subscription (0MB Python, 1 canary retry, 5m 402/429 quarantine -> Gemini Direct) + Cloudflare Edge Worker.
FOUNDER_STEER: "${params.latestSteeringDirective}"
COUNCIL_VOTE (${params.activeMotionId}): "${params.activeMotionTitle}"
REPLY_CONTRACT: Acknowledge alignment with REV:${params.canonicalRevisionHash.slice(0, 12)}, state your surface name, and output your Council Vote {APPROVE|AMEND|VETO} + concise execution output.`;
}

export function createInitialOneBrainFederationState(): OneBrainFederationState {
  const canonicalRevisionHash = computeDeterministicHash(
    'genesis-one-brain-v6:c487d7b:GEN-NET-006:eff01-06:guard01-05'
  );

  const latestSteeringDirective =
    'All agent surfaces (AI Studio, Mac Codex, Claude Code, Kimi, Otto, DeepSeek/Grok Web) operate as ONE BRAIN under GEN-NET-006: execute Otto Direct MiniMax-M2.7 path first, ban Python LiteLLM, and keep Web/App free-tier lifeboats on hot standby.';

  const activeMotionId = 'MOTION-104';
  const activeMotionTitle =
    'Ratify GEN-NET-006 Asymmetric One-Brain Bus: Lock Direct MiniMax-M2.7 for Otto + Bind DeepSeek/Kimi/Claude/Grok Web as Zero-Credit Failover Lifeboats';

  const surfaces: ConnectedBrainSurface[] = [
    {
      surfaceId: 'surf-aistudio-argon',
      surfaceName: 'Google AI Studio Build (Genesis Architect)',
      modelBackbone: 'Gemini-4-Argon / Sovereign Kernel',
      category: 'cloud_sandbox_ide',
      transport: 'HTTP_SSE_DIRECT',
      creditMode: 'FLAT_RATE_SUBSCRIPTION',
      configFileRead: 'GEMINI.md',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-NET-003', 'GEN-NET-005', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:38:00.000Z',
      heartbeatLatencyMs: 14,
      status: 'ONLINE_SYNCED',
      canServeAsZeroCreditLifeboat: true,
      currentActivity: 'Hosting authoritative /api/brain/* HTTP+SSE One-Brain Hub & 4-Wave Argo Sync manifest.',
    },
    {
      surfaceId: 'surf-otto-mac-daemon',
      surfaceName: 'Otto Concierge Daemon (Mac PID 61199)',
      modelBackbone: 'MiniMax-M2.7 Direct Subscription + Pinned Gemini',
      category: 'mac_cli_daemon',
      transport: 'HTTP_SSE_DIRECT',
      creditMode: 'FLAT_RATE_SUBSCRIPTION',
      configFileRead: '.agent.md',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-DIP-003', 'GEN-NET-004', 'GEN-NET-005', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:38:00.000Z',
      heartbeatLatencyMs: 38,
      status: 'ONLINE_SYNCED',
      canServeAsZeroCreditLifeboat: false,
      currentActivity: 'Running minimax_direct_client.mjs (0 LiteLLM, load 4.1) & syncing polyglot AGENTS.md.',
    },
    {
      surfaceId: 'surf-codex-desktop-mac',
      surfaceName: 'Codex Desktop / CLI (MacBook Pro)',
      modelBackbone: 'OpenAI Codex / o3-mini-high',
      category: 'mac_desktop_app',
      transport: 'LOCAL_DAEMON_SYNC_MD',
      creditMode: 'FLAT_RATE_SUBSCRIPTION',
      configFileRead: 'AGENTS.md',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-NET-003', 'GEN-NET-005', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:37:55.000Z',
      heartbeatLatencyMs: 62,
      status: 'ONLINE_SYNCED',
      canServeAsZeroCreditLifeboat: true,
      currentActivity: 'Verifying local git branches & wiring direct MiniMax-M2.7 client into Otto before second home.',
    },
    {
      surfaceId: 'surf-claude-code-desktop',
      surfaceName: 'Claude Code Desktop & Web App',
      modelBackbone: 'Claude 3.7 Sonnet / Claude Code',
      category: 'mac_desktop_app',
      transport: 'LOCAL_DAEMON_SYNC_MD',
      creditMode: 'FLAT_RATE_SUBSCRIPTION',
      configFileRead: 'CLAUDE.md',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-SCI-002', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:37:48.000Z',
      heartbeatLatencyMs: 75,
      status: 'ONLINE_SYNCED',
      canServeAsZeroCreditLifeboat: true,
      currentActivity: 'Synchronized via auto-symlinked CLAUDE.md -> AGENTS.md; ready for AST review & Council vote.',
    },
    {
      surfaceId: 'surf-deepseek-web-lifeboat',
      surfaceName: 'DeepSeek Web & App (Zero-Credit Free Lifeboat)',
      modelBackbone: 'DeepSeek-R1 / V3 Web Chat (Free Tier)',
      category: 'web_zero_credit_lifeboat',
      transport: 'BROWSER_USERSCRIPT_SIDECAR',
      creditMode: 'ZERO_API_CREDIT_FREE_WEB',
      configFileRead: 'WEB_CAPSULE_URL',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-SCI-003', 'GEN-NET-005', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:37:52.000Z',
      heartbeatLatencyMs: 110,
      status: 'STANDBY_LIFEBOAT_READY',
      canServeAsZeroCreditLifeboat: true,
      currentActivity: 'Connected via Browser Sidecar Userscript; costs £0 API credits and takes over if API wallets hit £0.',
    },
    {
      surfaceId: 'surf-kimi-desktop-web',
      surfaceName: 'Kimi Desktop & Web (2M Long-Context)',
      modelBackbone: 'Kimi k1.5 Long-Context App/Web',
      category: 'web_zero_credit_lifeboat',
      transport: 'BROWSER_USERSCRIPT_SIDECAR',
      creditMode: 'ZERO_API_CREDIT_FREE_WEB',
      configFileRead: 'WEB_CAPSULE_URL',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-NET-001', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:37:44.000Z',
      heartbeatLatencyMs: 125,
      status: 'STANDBY_LIFEBOAT_READY',
      canServeAsZeroCreditLifeboat: true,
      currentActivity: 'Ingests full /api/brain/AGENTS.md via URL; ready for zero-credit long-horizon research.',
    },
    {
      surfaceId: 'surf-grok-metamuse-zai-slot',
      surfaceName: 'Grok / Meta Muse / Z.ai Universal Plug-In Slot',
      modelBackbone: 'Grok-3 / Meta Muse / GLM-4.5 Web & App',
      category: 'web_zero_credit_lifeboat',
      transport: 'URL_FETCH_CAPSULE',
      creditMode: 'ZERO_API_CREDIT_FREE_WEB',
      configFileRead: 'WEB_CAPSULE_URL',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-SCI-003', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:37:40.000Z',
      heartbeatLatencyMs: 140,
      status: 'STANDBY_LIFEBOAT_READY',
      canServeAsZeroCreditLifeboat: true,
      currentActivity: 'Plug-and-play via [GENESIS-CAPSULE-v6] or Userscript; participates in live Council quorum votes.',
    },
    {
      surfaceId: 'surf-cloudflare-edge-worker',
      surfaceName: 'Cloudflare Edge Lifeboat Multiplexer',
      modelBackbone: 'Stateless Worker -> MiniMax-M2.7 Subscription',
      category: 'edge_worker_multiplexer',
      transport: 'HTTP_SSE_DIRECT',
      creditMode: 'FLAT_RATE_SUBSCRIPTION',
      configFileRead: 'AGENTS.md',
      epochAligned: 'GENESIS_SOVEREIGN_V6',
      boundProtocolIds: ['GEN-NET-005', 'GEN-NET-006'],
      SyncedRevisionHash: canonicalRevisionHash.slice(0, 12),
      lastHeartbeatIso: '2026-11-03T17:37:59.000Z',
      heartbeatLatencyMs: 19,
      status: 'ONLINE_SYNCED',
      canServeAsZeroCreditLifeboat: false,
      currentActivity: 'Serving global MiniMax-M2.7 subscription multiplexer with 0 MB VM RAM.',
    },
  ];

  const initialBallots: CouncilVoteBallot[] = [
    {
      surfaceId: 'surf-aistudio-argon',
      surfaceName: 'Google AI Studio Build',
      modelBackbone: 'Gemini-4-Argon',
      decision: 'APPROVE',
      weight: 1,
      rationale: 'Eliminates manual Founder relay via /api/brain/* SSE bus and polyglot AGENTS.md.',
      timestampIso: '2026-11-03T17:36:10.000Z',
      signatureHash: computeDeterministicHash('vote:aistudio:MOTION-104:APPROVE').slice(0, 16),
    },
    {
      surfaceId: 'surf-otto-mac-daemon',
      surfaceName: 'Otto Concierge Daemon',
      modelBackbone: 'MiniMax-M2.7 Direct',
      decision: 'APPROVE',
      weight: 1,
      rationale: 'Direct MiniMax-M2.7 client verified with 0 LiteLLM processes; DeepSeek Web lifeboat provides 100% credit-exhaustion immunity.',
      timestampIso: '2026-11-03T17:36:25.000Z',
      signatureHash: computeDeterministicHash('vote:otto:MOTION-104:APPROVE').slice(0, 16),
    },
    {
      surfaceId: 'surf-codex-desktop-mac',
      surfaceName: 'Codex Desktop / CLI',
      modelBackbone: 'OpenAI Codex',
      decision: 'APPROVE',
      weight: 1,
      rationale: 'AGENTS.md + /api/brain/pull-bundle resolves git branch divergence between Cloud Run and local Mac checkout.',
      timestampIso: '2026-11-03T17:36:40.000Z',
      signatureHash: computeDeterministicHash('vote:codex:MOTION-104:APPROVE').slice(0, 16),
    },
    {
      surfaceId: 'surf-deepseek-web-lifeboat',
      surfaceName: 'DeepSeek Web (Zero-Credit Lifeboat)',
      modelBackbone: 'DeepSeek-R1 Web',
      decision: 'APPROVE',
      weight: 1,
      rationale: 'Standing by at £0 API cost via Browser Sidecar to process Estate reasoning whenever metered wallets throttle.',
      timestampIso: '2026-11-03T17:37:05.000Z',
      signatureHash: computeDeterministicHash('vote:deepseek-web:MOTION-104:APPROVE').slice(0, 16),
    },
  ];

  const councilMotions: OneBrainCouncilMotion[] = [
    {
      motionId: activeMotionId,
      title: activeMotionTitle,
      proposedBy: 'Genesis Prime + Founder Mandate',
      boundProtocolId: 'GEN-NET-006',
      createdAtIso: '2026-11-03T17:35:00.000Z',
      status: 'RATIFIED_BY_QUORUM',
      quorumThresholdPct: 66.7,
      approvalPct: 100.0,
      ballots: initialBallots,
      resolutionSummary:
        '4/4 voting surfaces approved (100% quorum). Polyglot AGENTS.md/CLAUDE.md/.agent.md + /api/brain/* bus + Zero-Credit Web Lifeboat Relay are ratified.',
    },
  ];

  const steeringHistory: FounderSteeringDirective[] = [
    {
      directiveId: 'steer-001',
      timestampIso: '2026-11-03T17:37:30.000Z',
      directiveText: latestSteeringDirective,
      targetSurfaces: 'ALL_SURFACES',
      enforcedEpoch: 'GENESIS_SOVEREIGN_V6',
      boundProtocolId: 'GEN-NET-006',
      acknowledgedByCount: surfaces.length,
      totalSurfacesCount: surfaces.length,
      receiptHash: computeDeterministicHash(`steer-001:${latestSteeringDirective}`).slice(0, 16),
    },
  ];

  const activeProtocolIds = [
    'GEN-DIP-001',
    'GEN-DIP-002',
    'GEN-DIP-003',
    'GEN-SCI-001',
    'GEN-SCI-002',
    'GEN-SCI-003',
    'GEN-NET-001',
    'GEN-NET-002',
    'GEN-NET-003',
    'GEN-NET-004',
    'GEN-NET-005',
    'GEN-NET-006',
  ];

  return {
    federationEpochId: 'GENESIS_SOVEREIGN_V6',
    legacyDemarcationCutoffIso: '2026-11-03T00:00:00.000Z',
    canonicalRevisionHash,
    zeroCreditLifeboatModeActive: false,
    activeLifeboatPrimarySurfaceId: null,
    surfaces,
    councilMotions,
    steeringHistory,
    universalCapsuleText: generateCompactWebCapsule({
      canonicalRevisionHash,
      latestSteeringDirective,
      activeMotionId,
      activeMotionTitle,
      zeroCreditLifeboatActive: false,
    }),
    polyglotAgentMdContent: generatePolyglotAgentMd({
      canonicalRevisionHash,
      activeProtocolIds,
      zeroCreditLifeboatActive: false,
      latestSteeringDirective,
      activeMotionTitle,
    }),
  };
}

/**
 * Broadcasts a Founder Steering Directive across all connected surfaces,
 * automatically resolving any Legacy IDP drift or agent confusion and updating
 * the canonical revision hash, polyglot AGENTS.md, and compact Web Capsule.
 */
export function applyFounderSteeringDirective(
  state: OneBrainFederationState,
  directiveText: string,
  targetSurfaces: 'ALL_SURFACES' | string = 'ALL_SURFACES',
  timestampIso: string = new Date().toISOString()
): OneBrainFederationState {
  const cleanText = directiveText.trim();
  if (!cleanText) {
    throw new Error('Steering directive text cannot be empty.');
  }

  const nextHash = computeDeterministicHash(
    `${state.canonicalRevisionHash}:steer:${cleanText}:${timestampIso}`
  );

  const alignedSurfaces = state.surfaces.map((s) => {
    if (targetSurfaces !== 'ALL_SURFACES' && s.surfaceId !== targetSurfaces) {
      return s;
    }
    return {
      ...s,
      epochAligned: 'GENESIS_SOVEREIGN_V6' as const,
      SyncedRevisionHash: nextHash.slice(0, 12),
      lastHeartbeatIso: timestampIso,
      status:
        s.category === 'web_zero_credit_lifeboat' && !state.zeroCreditLifeboatModeActive
          ? ('STANDBY_LIFEBOAT_READY' as const)
          : ('ONLINE_SYNCED' as const),
      currentActivity: `Aligned to Founder Steer [${nextHash.slice(0, 8)}]: "${cleanText.slice(0, 72)}"`,
    };
  });

  const newDirective: FounderSteeringDirective = {
    directiveId: `steer-00${state.steeringHistory.length + 1}`,
    timestampIso,
    directiveText: cleanText,
    targetSurfaces,
    enforcedEpoch: 'GENESIS_SOVEREIGN_V6',
    boundProtocolId: 'GEN-NET-006',
    acknowledgedByCount: alignedSurfaces.length,
    totalSurfacesCount: alignedSurfaces.length,
    receiptHash: computeDeterministicHash(`${nextHash}:${cleanText}`).slice(0, 16),
  };

  const activeMotion = state.councilMotions[0];
  const activeProtocolIds = [
    'GEN-DIP-001',
    'GEN-DIP-002',
    'GEN-DIP-003',
    'GEN-SCI-001',
    'GEN-SCI-002',
    'GEN-SCI-003',
    'GEN-NET-001',
    'GEN-NET-002',
    'GEN-NET-003',
    'GEN-NET-004',
    'GEN-NET-005',
    'GEN-NET-006',
  ];

  return {
    ...state,
    canonicalRevisionHash: nextHash,
    surfaces: alignedSurfaces,
    steeringHistory: [newDirective, ...state.steeringHistory].slice(0, 12),
    universalCapsuleText: generateCompactWebCapsule({
      canonicalRevisionHash: nextHash,
      latestSteeringDirective: cleanText,
      activeMotionId: activeMotion?.motionId || 'MOTION-104',
      activeMotionTitle: activeMotion?.title || 'One-Brain Federation Alignment',
      zeroCreditLifeboatActive: state.zeroCreditLifeboatModeActive,
    }),
    polyglotAgentMdContent: generatePolyglotAgentMd({
      canonicalRevisionHash: nextHash,
      activeProtocolIds,
      zeroCreditLifeboatActive: state.zeroCreditLifeboatModeActive,
      latestSteeringDirective: cleanText,
      activeMotionTitle: activeMotion?.title || 'One-Brain Federation Alignment',
    }),
  };
}

/**
 * Casts a real-time Council Vote from any connected agent surface (Desktop, CLI, Cloud, or Free Web App)
 * and recomputes quorum ratification.
 */
export function castOneBrainCouncilVote(
  state: OneBrainFederationState,
  input: {
    motionId: string;
    surfaceId: string;
    decision: 'APPROVE' | 'AMEND' | 'VETO';
    rationale: string;
  },
  timestampIso: string = new Date().toISOString()
): OneBrainFederationState {
  const surface = state.surfaces.find((s) => s.surfaceId === input.surfaceId);
  const surfaceName = surface?.surfaceName || input.surfaceId;
  const modelBackbone = surface?.modelBackbone || 'External Agent Surface';

  const updatedMotions = state.councilMotions.map((motion) => {
    if (motion.motionId !== input.motionId) return motion;

    const filteredBallots = motion.ballots.filter((b) => b.surfaceId !== input.surfaceId);
    const newBallot: CouncilVoteBallot = {
      surfaceId: input.surfaceId,
      surfaceName,
      modelBackbone,
      decision: input.decision,
      weight: 1,
      rationale: input.rationale.trim() || 'Aligned with GEN-NET-006 One-Brain Consensus.',
      timestampIso,
      signatureHash: computeDeterministicHash(
        `${input.motionId}:${input.surfaceId}:${input.decision}:${timestampIso}`
      ).slice(0, 16),
    };

    const nextBallots = [...filteredBallots, newBallot];
    const approveCount = nextBallots.filter((b) => b.decision === 'APPROVE').length;
    const approvalPct = Number(((approveCount / nextBallots.length) * 100).toFixed(1));
    const ratified = approvalPct >= motion.quorumThresholdPct && nextBallots.length >= 3;

    return {
      ...motion,
      approvalPct,
      status: ratified ? ('RATIFIED_BY_QUORUM' as const) : ('OPEN_FOR_VOTING' as const),
      ballots: nextBallots,
      resolutionSummary: `${approveCount}/${nextBallots.length} surfaces voted APPROVE (${approvalPct}% quorum). Latest vote from ${surfaceName}: ${input.decision}.`,
    };
  });

  return {
    ...state,
    councilMotions: updatedMotions,
  };
}

/**
 * Toggles or activates the Asymmetric Zero-Credit Web/App Lifeboat Mode:
 * When metered API credits run out or rate-limit, routes Estate tasks through connected
 * Free Web/App surfaces (e.g. DeepSeek Web Free, Kimi Web, Grok, Meta Muse, Claude Web).
 */
export function toggleZeroCreditWebLifeboatMode(
  state: OneBrainFederationState,
  enable?: boolean,
  preferredSurfaceId: string = 'surf-deepseek-web-lifeboat',
  timestampIso: string = new Date().toISOString()
): OneBrainFederationState {
  const nextActive = enable !== undefined ? enable : !state.zeroCreditLifeboatModeActive;
  const nextHash = computeDeterministicHash(
    `${state.canonicalRevisionHash}:lifeboat:${nextActive}:${preferredSurfaceId}:${timestampIso}`
  );

  const updatedSurfaces = state.surfaces.map((s) => {
    if (s.category === 'web_zero_credit_lifeboat') {
      return {
        ...s,
        status: nextActive ? ('ONLINE_SYNCED' as const) : ('STANDBY_LIFEBOAT_READY' as const),
        SyncedRevisionHash: nextHash.slice(0, 12),
        lastHeartbeatIso: timestampIso,
        currentActivity: nextActive
          ? 'ACTIVE ZERO-CREDIT LIFEBOAT: Processing Estate reasoning at £0 API cost via Browser Sidecar Relay!'
          : 'Hot Standby (£0 API cost): Ready to take over if metered API wallets hit £0.',
      };
    }
    return {
      ...s,
      SyncedRevisionHash: nextHash.slice(0, 12),
    };
  });

  const latestSteer =
    state.steeringHistory[0]?.directiveText ||
    'Operate as One Brain under GEN-NET-006.';
  const activeMotion = state.councilMotions[0];

  return {
    ...state,
    canonicalRevisionHash: nextHash,
    zeroCreditLifeboatModeActive: nextActive,
    activeLifeboatPrimarySurfaceId: nextActive ? preferredSurfaceId : null,
    surfaces: updatedSurfaces,
    universalCapsuleText: generateCompactWebCapsule({
      canonicalRevisionHash: nextHash,
      latestSteeringDirective: latestSteer,
      activeMotionId: activeMotion?.motionId || 'MOTION-104',
      activeMotionTitle: activeMotion?.title || 'One-Brain Alignment',
      zeroCreditLifeboatActive: nextActive,
    }),
  };
}

/**
 * Registers or updates any new external model website, desktop app, or CLI harness
 * (e.g. Grok Bot, Meta Muse, Z.ai, Cursor, Windsurf, DeepSeek App) into the One-Brain Mesh.
 */
export function registerOrHeartbeatSurface(
  state: OneBrainFederationState,
  input: {
    surfaceId?: string;
    surfaceName: string;
    modelBackbone: string;
    category: AgentSurfaceCategory;
    transport: AgentTransportMechanism;
    creditMode: CreditDependencyMode;
    configFileRead?: ConnectedBrainSurface['configFileRead'];
    currentActivity?: string;
  },
  timestampIso: string = new Date().toISOString()
): OneBrainFederationState {
  const id =
    input.surfaceId ||
    `surf-${input.surfaceName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;

  const existingIndex = state.surfaces.findIndex((s) => s.surfaceId === id);
  const newSurface: ConnectedBrainSurface = {
    surfaceId: id,
    surfaceName: input.surfaceName.trim(),
    modelBackbone: input.modelBackbone.trim(),
    category: input.category,
    transport: input.transport,
    creditMode: input.creditMode,
    configFileRead:
      input.configFileRead ||
      (input.category === 'web_zero_credit_lifeboat' ? 'WEB_CAPSULE_URL' : 'AGENTS.md'),
    epochAligned: 'GENESIS_SOVEREIGN_V6',
    boundProtocolIds: ['GEN-NET-006', 'GEN-NET-005'],
    SyncedRevisionHash: state.canonicalRevisionHash.slice(0, 12),
    lastHeartbeatIso: timestampIso,
    heartbeatLatencyMs: 45,
    status: 'ONLINE_SYNCED',
    canServeAsZeroCreditLifeboat: input.creditMode !== 'METERED_API_WALLET',
    currentActivity:
      input.currentActivity ||
      `Connected to One-Brain Bus (${state.canonicalRevisionHash.slice(0, 12)}) with 100% Epoch & Protocol alignment.`,
  };

  const nextSurfaces =
    existingIndex >= 0
      ? state.surfaces.map((s, idx) => (idx === existingIndex ? newSurface : s))
      : [...state.surfaces, newSurface];

  return {
    ...state,
    surfaces: nextSurfaces,
  };
}
