import type {
  EvidenceClass,
  FlowPhase,
  FormationId,
  SevenGateAssessment,
  ClaimViolation,
  ReconciledPullRequest,
} from '../engine/estateRules.ts';
import type {
  OptimusEvidenceRecord,
  OptimusDeterministicSignal,
  OptimusAdmissionResult,
  ReactorNodeDatum,
} from '../engine/optimusAndReactor.ts';
import type {
  OpsRegisterEntry,
  OpsEvidenceFile,
} from '../engine/registerProjector.ts';
import type {
  ArgonSyncManifest,
  ArgonRemotePushReceipt,
  ArgonSyncReadinessState,
} from '../engine/argonSync.ts';
import type { SwarmSynapseState } from '../engine/swarmSynapse.ts';
import type { IoCanonicalWorkGraphState } from '../engine/ioCanonicalEngine.ts';
import type { OmegaCoreState } from '../engine/omegaCore.ts';
import type {
  BeastGovernorState,
  BeastSynchronyCatalogState,
  SovereignStandardsGovernanceState,
  GenesisAcademyState,
} from '../engine/beastGovernor.ts';

export interface HandoverReceipt {
  receiptId: string;
  acceptedAt: string;
  handoverFile: string;
  handoverSha256: string;
  handoverBytes: number;
  handoverLines: number;
  executorIdentity: string;
  accountableLanes: Array<{
    laneId: string;
    title: string;
    priority: 'P0' | 'P1';
    status: 'OPERATING' | 'AUDIT_ACTIVE' | 'BOUNDARY_LOGGED';
    proofPointer: string;
  }>;
  explicitBoundaries: Array<{
    capability: string;
    authority: EvidenceClass;
    status: string;
    remediation: string;
  }>;
}

export interface SurfaceProbeResult {
  id: string;
  name: string;
  url: string;
  observedAt: string;
  httpStatus: number | null;
  latencyMs: number;
  bytes: number;
  authority: EvidenceClass;
  verdict: 'VERIFIED_LIVE' | 'DEGRADED_CONTRACT' | 'UNREACHABLE';
  extractedTitle: string;
  contractNotes: string;
}

export interface RepoCommitObservation {
  repo: string;
  visibility: 'public' | 'private';
  handoverMainSha: string | null;
  liveMainSha: string | null;
  liveCommittedAt: string | null;
  liveMessage: string | null;
  driftDetected: boolean;
  authority: EvidenceClass;
}

export interface LegionExecutionRun {
  executionId: string;
  instructionId: string;
  formation: FormationId;
  formationName: string;
  posture: string;
  helmShots: number;
  degreesOfFreedom: number;
  repo: string;
  laneBranch: string;
  workerId: string;
  leaseEpoch: number;
  modelId: string;
  startedAt: string;
  completedAt: string;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  summary: string;
  patchArtifact: string;
  proposedCommands: string[];
  testAssertions: string[];
  sevenGates: SevenGateAssessment;
  geburahFalsifierNotes: string;
  geburahCounterexamples: string[];
  claimGateVerdict: 'PASS' | 'CLAIM_REJECTED' | 'DOWNGRADED_TO_UNVERIFIED';
  epistemicScore: number;
  effectiveAuthority: EvidenceClass;
  violations: ClaimViolation[];
  artifactSha256: string;
}

export interface SafeguardDecisionEvent {
  eventId: string;
  timestamp: string;
  gateName:
    | 'CLAIM_GATE'
    | 'INBOUND_FIREWALL'
    | 'ARGON_SYNC_FENCE'
    | 'GREENLANE_GUARD'
    | 'LEGION_ROUTER'
    | 'OPTIMUS_ADMISSION'
    | 'REGISTER_RECONCILE'
    | 'ARGON_LANE_SYNC'
    | 'SWARM_SYNAPSE'
    | 'OFFLINE_CONTINUITY'
    | 'IO_CANONICAL_EVAL'
    | 'OMEGA_SAFETY_GATE'
    | 'BEAST_REGO_GOVERNOR';
  action: 'PASS' | 'REFUSE' | 'RECOVER';
  subject: string;
  authority: EvidenceClass;
  detail: string;
  decider: string;
}

export interface ChronosCadenceSlot {
  id: string;
  day: 'Monday' | 'Tuesday' | 'Wednesday' | 'Continuous';
  windowUtc: string;
  lane: string;
  ownerFormation: FormationId;
  objective: string;
  deliverableContract: string;
  ventureTarget: string;
  status: 'ACTIVE' | 'SCHEDULED' | 'NEEDS_SECRET';
}

export interface VentureSurfaceStatus {
  id: string;
  name: string;
  role: string;
  primaryRepo: string;
  liveUrl: string | null;
  authority: EvidenceClass;
  readinessState: 'LIVE_VERIFIED' | 'REGRESSION_WATCH' | 'STAGED_PR_BACKLOG' | 'HISTORICAL_HOLD';
  revenueMechanism: string;
  currentBlocker: string;
  nextAction: string;
}

export interface OneBrainIntelligenceSummary {
  observedAt: string;
  processRssMb: number;
  nodeUptimeSec: number;
  totalTokensProcessed: number;
  totalCumulativeCostUsd: number;
  activeLeaseCount: number;
  stagnantLeaseCount: number;
  verifiedSurfaceRatio: string;
  greenlaneReadyCount: number;
  providerRoster: Array<{
    slot: string;
    modelAlias: string;
    role: string;
    authority: EvidenceClass;
    status: 'LIVE_CLOUD' | 'DETERMINISTIC_FALLBACK' | 'EXTERNAL_REPO_LANE';
  }>;
}

export interface OptimusSnapshotBundle {
  writable: boolean;
  signerMode: 'ESTATE_RECEIPT_KEY_PROVISIONED' | 'EPHEMERAL_RUNTIME_HMAC';
  keyFingerprint: string;
  eventCursor: number;
  records: OptimusEvidenceRecord[];
  signals: OptimusDeterministicSignal[];
  latestAdmission: OptimusAdmissionResult;
  oneBrain: OneBrainIntelligenceSummary;
}

export interface EstateStateSnapshot {
  observedAt: string;
  receipt: HandoverReceipt;
  repos: RepoCommitObservation[];
  surfaces: SurfaceProbeResult[];
  remoteLegionMissions: Array<{
    id: string;
    title: string;
    phase: string;
    issueUrl: string;
    operationalYieldVerified: boolean;
    evidenceLimitation: string;
  }>;
  vaultIncident2468: {
    issueNumber: number;
    title: string;
    state: string;
    updatedAt: string;
    manifestPath: string;
    missingKey: string;
    authority: EvidenceClass;
  };
  reconciledPullRequests: ReconciledPullRequest[];
  flowInstructions: Array<{
    instructionId: string;
    idempotencyKey: string;
    title: string;
    body: string;
    repo: string;
    formation: FormationId;
    helmShots: number;
    phase: FlowPhase;
    leaseEpoch: number;
    assignedWorkerId: string | null;
    executionId: string | null;
    laneBranch: string | null;
    sourceSha: string | null;
    receiptHash: string | null;
    authorityClass: EvidenceClass;
    createdAtMs: number;
    lastHeartbeatMs: number;
    recoveryCount: number;
    stagnationReason?: string | null;
    falsifierSummary?: string | null;
  }>;
  executions: LegionExecutionRun[];
  safeguardDecisions: SafeguardDecisionEvent[];
  cadence: ChronosCadenceSlot[];
  ventures: VentureSurfaceStatus[];
  optimus: OptimusSnapshotBundle;
  reactorNodes: ReactorNodeDatum[];
  projector: {
    registerPath: string;
    evidenceDir: string;
    registerEntries: OpsRegisterEntry[];
    evidenceBySeq: Record<number, OpsEvidenceFile>;
    diskSha256BySeq: Record<number, string>;
  };
  argonSync: {
    readiness: ArgonSyncReadinessState;
    manifest: ArgonSyncManifest;
    lastRemoteReceipt: ArgonRemotePushReceipt | null;
    stagedOutboxPath: string;
    devCallbackUrl: string;
    sharedCallbackUrl: string;
  };
  swarmSynapse: SwarmSynapseState;
  ioWorkGraph: IoCanonicalWorkGraphState;
  omegaCore: OmegaCoreState;
  beastGovernor: BeastGovernorState;
  beastSynchrony: BeastSynchronyCatalogState;
  sovereignStandards: SovereignStandardsGovernanceState;
  genesisAcademy: GenesisAcademyState;
}
