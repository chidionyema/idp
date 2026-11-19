import { EstateArtifact, EstateEdict, EstateMotion, EstateNode, FinancialHealthMetrics } from '../types/estate';

export const INITIAL_ARTIFACTS: EstateArtifact[] = [
  {
    id: 'ART-001',
    title: 'Real-Time Visual Intelligence & Estate Topology Mockup',
    type: 'VISUAL_MOCKUP',
    status: 'ORPHANED_RECOVERED',
    depositLocation: '/vault/visual-telemetry/interactive-estate-grid-v1.json',
    originAgent: 'Agent-Zephyr-4402',
    checksum: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    updatedAt: '2026-10-30T22:15:00Z',
    version: '1.4.0',
    description: 'The lost visual intelligence screen tracked down and indexed. Renders the live interactive graph of estate operations, agent vectors, feedback loops, and real-time state transitions.',
    contentSummary: 'Complete multi-layered SVG & state machine mapping 12 autonomous sub-routines, closed-loop telemetry feeds, and founder focal orientation matrix.',
    metadata: {
      resolution: '3840x2160 UHD',
      fileFormat: 'Interactive Canvas / Vector Manifold',
      targetStage: 'Operational Visual Command',
      derivationChain: ['Decree-01-Algorithmic-First', 'Founder-Edict-Orientation', 'PRD-Visual-Anchor-Rev4']
    }
  },
  {
    id: 'ART-002',
    title: 'Autonomous Estate Sovereign Decree & Delivery Protocol Spec',
    type: 'SOVEREIGN_EDICT',
    status: 'VERIFIED_ACTIVE',
    depositLocation: '/vault/protocol/sovereign-edict-charter.md',
    originAgent: 'Founder-Core-01',
    checksum: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    updatedAt: '2026-10-31T00:10:00Z',
    version: '2.0.1',
    description: 'The foundational legal and algorithmic constitution of the estate. Mandates mathematical state formulation before any motion code or agenda text is generated.',
    contentSummary: 'Strict 5-stage motion delivery pipeline, Lyapunov stability constraints on treasury burn, and zero-tolerance for open-loop speculative tasks.',
    metadata: {
      fileFormat: 'RFC-Spec-Document',
      targetStage: 'Estate Law & Invariants',
      derivationChain: ['Founder-Mandate-Redline-Oct2026']
    }
  },
  {
    id: 'ART-003',
    title: 'Treasury Burn & Capital Runway Closed-Loop Ledger',
    type: 'FINANCIAL_LEDGER',
    status: 'VERIFIED_ACTIVE',
    depositLocation: '/vault/financials/ledger-q4-2026-closed-loop.csv',
    originAgent: 'Agent-Fiscal-Audit',
    checksum: 'sha256:2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae',
    updatedAt: '2026-10-31T00:30:00Z',
    version: '3.1.0',
    description: 'Audited financial ledger mapping every dollar of burn to validated delivered motions. Tracks red-line threshold date and stops unanchored agent bleed.',
    contentSummary: 'Real-time burn breakdown: Agent inference cost, infrastructure compute, legal filings, and direct founder health contingency reserves.',
    metadata: {
      fileFormat: 'Tabular Ledger',
      targetStage: 'Financial Defense',
      derivationChain: ['Bank-Statement-Mirror', 'Agent-Inference-Meter-v2']
    }
  },
  {
    id: 'ART-004',
    title: 'Closed-Loop Algorithmic Convergence Engine Blueprint',
    type: 'ARCHITECTURAL_BLUEPRINT',
    status: 'VERIFIED_ACTIVE',
    depositLocation: '/vault/architecture/closed-loop-feedback-engine.drawio',
    originAgent: 'Agent-SysArch-9',
    checksum: 'sha256:fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9',
    updatedAt: '2026-10-30T18:00:00Z',
    version: '1.2.0',
    description: 'State machine architecture enforcing that no task or agenda can exit to completion without an automated telemetry proof of delivered value.',
    contentSummary: 'Feedback controller with automated deviation alarms, dead-band filters, and autonomous shutdown triggers for errant agents.',
    metadata: {
      fileFormat: 'State Machine XML/Vector',
      targetStage: 'Runtime Architecture',
      derivationChain: ['Edict-02-Closed-Loop-Law']
    }
  },
  {
    id: 'ART-005',
    title: 'Founder Cognitive Restoration & Biological Risk Protocol',
    type: 'DELIVERY_SPEC',
    status: 'VERIFIED_ACTIVE',
    depositLocation: '/vault/health/executive-restoration-protocol.json',
    originAgent: 'Founder-Health-Sentinel',
    checksum: 'sha256:a5438865668e178128330768c67929d14660eb9fa0ea9ee118bf537759a40510',
    updatedAt: '2026-10-31T00:05:00Z',
    version: '1.0.0',
    description: 'Biometric and cognitive guardrails limiting continuous drift. Enforces quiet hours, cuts down agent notifications to zero-noise digests, and bounds founder stress.',
    contentSummary: 'Threshold parameters: Max 4 hours continuous high-intensity audit, 7.5 hours uninterrupted biological recovery, and automatic delegation freeze during sleep cycles.',
    metadata: {
      fileFormat: 'Health Protocol JSON',
      targetStage: 'Founder Protection',
      derivationChain: ['Red-Line-Intervention-Decree']
    }
  }
];

export const INITIAL_EDICTS: EstateEdict[] = [
  {
    id: 'EDICT-01',
    code: 'DEC-001',
    title: 'Decree to Think Algorithmically First',
    decreeText: 'No motion, agent prompt, code repository, or capital expenditure shall be initiated without an explicit mathematical state transition model, convergence proof, and target destination invariant.',
    status: 'ENFORCED',
    enactedDate: '2026-10-28',
    governingInvariant: 'State-space reachability: Proof that final state S_target is reachable from current state S_0 within bounded cost C_max.',
    violationPenalty: 'Immediate process termination and quarantine of initiating agent.'
  },
  {
    id: 'EDICT-02',
    code: 'DEC-002',
    title: 'Closed-Loop Telemetry & Zero Missing Artifact Law',
    decreeText: 'Every agent motion must register its output artifacts in the immutable Vault registry with a cryptographic checksum. If an artifact is missing or untraceable, the motion is classified as null and capital allocation is revoked.',
    status: 'ENFORCED',
    enactedDate: '2026-10-29',
    governingInvariant: 'Artifact provenance invariant: Traceability matrix must map 100% of generated outputs to a specific Founder verification gate.',
    violationPenalty: 'Revocation of agent API authorization and full estate audit.'
  },
  {
    id: 'EDICT-03',
    code: 'DEC-003',
    title: 'Founder Health & Treasury Red-Line Shield',
    decreeText: 'The autonomous estate exists to multiply sovereign wealth and peace of mind, not to drain founder life force. When financial runway drops below 90 days or cognitive overload exceeds safe bounds, non-critical agents are frozen immediately.',
    status: 'ENFORCED',
    enactedDate: '2026-10-30',
    governingInvariant: 'Survival invariant: Treasury runway >= 120 days AND Founder Cognitive Strain <= 65/100.',
    violationPenalty: 'Autonomous estate freeze into emergency defensive standby.'
  }
];

export const INITIAL_MOTIONS: EstateMotion[] = [
  {
    id: 'MOT-01',
    title: 'Recover Lost Visual Intelligence Artifact & Deploy Live Founder Command UI',
    sponsor: 'Founder Executive',
    decreeRef: 'EDICT-01 & EDICT-02',
    currentStage: 'STAGE_4_DELIVERY_EXECUTION',
    closedLoopMetric: 'Founder visual blind-spot metric (1 = blind, 0 = complete real-time visibility)',
    currentMetricValue: 0.15,
    targetMetricValue: 0.0,
    capitalAllocatedUSD: 2400,
    capitalConsumedUSD: 1100,
    founderCognitiveImpact: 'LOW',
    convergenceScore: 96,
    registeredArtifactIds: ['ART-001', 'ART-004'],
    lastAuditDate: '2026-10-31',
    auditVerdict: 'APPROVED_CONVERGENT',
    deliverableSummary: 'Interactive real-time visual canvas tracking all estate topology nodes, artifacts, and closed feedback loops.'
  },
  {
    id: 'MOT-02',
    title: 'Dismantle Reactive "Build-New-Things" Failure Pattern & Institute Algorithmic Pre-Audit',
    sponsor: 'Algorithmic Architect Agent',
    decreeRef: 'EDICT-01',
    currentStage: 'STAGE_3_RISK_CAPITAL_CLEARANCE',
    closedLoopMetric: 'Unanchored initiative failure rate (%)',
    currentMetricValue: 74,
    targetMetricValue: 5,
    capitalAllocatedUSD: 4500,
    capitalConsumedUSD: 1800,
    founderCognitiveImpact: 'MODERATE',
    convergenceScore: 89,
    registeredArtifactIds: ['ART-002'],
    lastAuditDate: '2026-10-30',
    auditVerdict: 'APPROVED_CONVERGENT',
    deliverableSummary: 'Gatekeeping pipeline requiring state-space convergence check before any developer or agent task starts.'
  },
  {
    id: 'MOT-03',
    title: 'Treasury Burn Containment & Red-Line Runway Extension to 180 Days',
    sponsor: 'Treasury Steward',
    decreeRef: 'EDICT-03',
    currentStage: 'STAGE_2_CLOSED_LOOP_METRIC',
    closedLoopMetric: 'Daily burn rate reduction ($/day)',
    currentMetricValue: 340,
    targetMetricValue: 140,
    capitalAllocatedUSD: 3000,
    capitalConsumedUSD: 850,
    founderCognitiveImpact: 'LOW',
    convergenceScore: 82,
    registeredArtifactIds: ['ART-003'],
    lastAuditDate: '2026-10-29',
    auditVerdict: 'APPROVED_CONVERGENT',
    deliverableSummary: 'Automated shutdown of idling compute instances and elimination of duplicate agent runs.'
  },
  {
    id: 'MOT-04',
    title: 'Quarantine Mindless Agent Text Generators & Enforce Delivery Protocols',
    sponsor: 'Protocol Warden',
    decreeRef: 'EDICT-02',
    currentStage: 'STAGE_1_ALGORITHMIC_FORMULATION',
    closedLoopMetric: 'Ratio of concrete delivered code/assets vs idle conversational agenda text',
    currentMetricValue: 1.2,
    targetMetricValue: 8.5,
    capitalAllocatedUSD: 1800,
    capitalConsumedUSD: 350,
    founderCognitiveImpact: 'LOW',
    convergenceScore: 91,
    registeredArtifactIds: [],
    lastAuditDate: '2026-10-31',
    auditVerdict: 'APPROVED_CONVERGENT',
    deliverableSummary: 'Replaces unstructured chat conversations with structured JSON motions and concrete artifact delivery receipts.'
  }
];

export const INITIAL_NODES: EstateNode[] = [
  {
    id: 'NODE-01',
    name: 'Founder Sovereign Anchor',
    category: 'FOUNDER_CORE',
    status: 'ACTIVE',
    x: 180,
    y: 220,
    loadPercent: 78,
    openLoopsCount: 2,
    lastPing: '2s ago',
    assignedDecree: 'DEC-001 (Chief Arbiter)'
  },
  {
    id: 'NODE-02',
    name: 'Algorithmic Convergence Gate',
    category: 'PROTOCOL_GATE',
    status: 'ACTIVE',
    x: 440,
    y: 130,
    loadPercent: 42,
    openLoopsCount: 0,
    lastPing: '1s ago',
    assignedDecree: 'DEC-001 (Think Algorithmically First)'
  },
  {
    id: 'NODE-03',
    name: 'Immutable Artifact Vault',
    category: 'ARTIFACT_VAULT',
    status: 'ACTIVE',
    x: 720,
    y: 180,
    loadPercent: 28,
    openLoopsCount: 0,
    lastPing: '4s ago',
    assignedDecree: 'DEC-002 (Zero Missing Artifacts)'
  },
  {
    id: 'NODE-04',
    name: 'Autonomous Agent Fleet (7 Sub-Agents)',
    category: 'AUTONOMOUS_AGENT',
    status: 'DRIFTING',
    x: 420,
    y: 330,
    loadPercent: 88,
    openLoopsCount: 5,
    lastPing: 'Just now',
    assignedDecree: 'DEC-002 (Enforcing Structured Motions)'
  },
  {
    id: 'NODE-05',
    name: 'Capital Runway & Treasury Reserve',
    category: 'CAPITAL_TREASURY',
    status: 'ACTIVE',
    x: 680,
    y: 370,
    loadPercent: 62,
    openLoopsCount: 1,
    lastPing: '10s ago',
    assignedDecree: 'DEC-003 (Financial & Health Shield)'
  }
];

export const INITIAL_METRICS: FinancialHealthMetrics = {
  totalTreasuryUSD: 84500,
  monthlyBurnUSD: 9400,
  runwayMonths: 9.0,
  dailyBurnUSD: 313.33,
  capitalEfficiencyRatio: 2.8,
  redLineThresholdDays: 120,
  founderRestHoursPerNight: 5.2,
  founderCognitiveLoadIndex: 78, // High strain - approaching red line
  founderContinuousDriftHours: 14.5,
  unanchoredAgentThreads: 3,
  closedFeedbackLoopsCount: 18,
  openFeedbackLoopsCount: 4
};

// MacBook Hardware & Infrastructure Incident State
export const INITIAL_MACBOOK_RESOURCES = {
  diskFreeGB: 1.4,
  diskTotalGB: 512.0,
  diskUsedPercent: 99.7, // Critical red line
  memoryPressureStatus: 'CRITICAL_RED' as const,
  activeClineSessions: 0,
  maxRecommendedSessions: 1, // Never swarm 20 locally
  runawayNodeProcessesCount: 14,
  reclaimableCacheGB: 46.8
};

// £30 Cline Agent Burn Post-Mortem (20 Killed Sessions)
export const KILLED_CLINE_SESSIONS = [
  {
    id: 'CLINE-SESS-01',
    agentName: 'Cline Agent #1 (Root Discovery)',
    costGBP: 2.85,
    tokensConsumed: 142000,
    killReason: 'ENOSPC_DISK_FULL' as const,
    durationMinutes: 4.2,
    salvageableDiffsFound: false,
    unindexedScansRun: 18,
    timestamp: '2026-10-31 00:15:10',
    lastKnownPrompt: 'Find all router configurations and audit state'
  },
  {
    id: 'CLINE-SESS-02',
    agentName: 'Cline Agent #2 (Recursive Grep)',
    costGBP: 2.40,
    tokensConsumed: 121000,
    killReason: 'ENOSPC_DISK_FULL' as const,
    durationMinutes: 3.8,
    salvageableDiffsFound: false,
    unindexedScansRun: 24,
    timestamp: '2026-10-31 00:18:22',
    lastKnownPrompt: 'Scan whole repository for router entry point'
  },
  {
    id: 'CLINE-SESS-03',
    agentName: 'Cline Agent #3 (Unbounded Loop)',
    costGBP: 3.10,
    tokensConsumed: 155000,
    killReason: 'OOM_MACOS_MEMORY_PRESSURE' as const,
    durationMinutes: 5.1,
    salvageableDiffsFound: true,
    unindexedScansRun: 31,
    timestamp: '2026-10-31 00:22:45',
    lastKnownPrompt: 'Inspect all node_modules dependencies'
  },
  {
    id: 'CLINE-SESS-04-20',
    agentName: 'Cline Swarm Batch (Agents #4 through #20)',
    costGBP: 21.65,
    tokensConsumed: 1085000,
    killReason: 'OOM_MACOS_MEMORY_PRESSURE' as const,
    durationMinutes: 12.0,
    salvageableDiffsFound: true,
    unindexedScansRun: 142,
    timestamp: '2026-10-31 00:35:12',
    lastKnownPrompt: 'Simultaneous uncoordinated discovery runs across local MacBook'
  }
];

export const INITIAL_ROUTER_PROBE = {
  endpoint: 'http://127.0.0.1:8000',
  port: 8000,
  protocol: 'HTTP' as const,
  state: 'PORT_NOT_BOUND' as const,
  lastChecked: '2026-10-31 00:58:14',
  latencyMs: null,
  errorDetail: 'Connection refused: No router process listening on 127.0.0.1:8000. Agents bypassed router to direct endpoints.',
  suggestedFix: 'Run `lsof -i :8000` to verify port. If using LiteLLM/custom gateway, start it with `python -m litellm --port 8000`.'
};

