export type SystemStatus = 'NOMINAL' | 'RED_LINE_WARNING' | 'CRITICAL_DRIFT' | 'FROZEN_CONTAINMENT';

export interface EstateNode {
  id: string;
  name: string;
  category: 'FOUNDER_CORE' | 'AUTONOMOUS_AGENT' | 'ARTIFACT_VAULT' | 'CAPITAL_TREASURY' | 'PROTOCOL_GATE' | 'INFRASTRUCTURE_ROUTER' | 'LOCAL_MACBOOK';
  status: 'ACTIVE' | 'IDLE' | 'DRIFTING' | 'LOCKED' | 'OFFLINE_CRASHED';
  x: number;
  y: number;
  loadPercent: number;
  openLoopsCount: number;
  lastPing: string;
  assignedDecree?: string;
}

export interface EstateArtifact {
  id: string;
  title: string;
  type: 'VISUAL_MOCKUP' | 'ARCHITECTURAL_BLUEPRINT' | 'SOVEREIGN_EDICT' | 'FINANCIAL_LEDGER' | 'DELIVERY_SPEC' | 'INCIDENT_POST_MORTEM' | 'RECOVERY_SCRIPT';
  status: 'VERIFIED_ACTIVE' | 'IN_TRANSIT' | 'ORPHANED_RECOVERED' | 'LOCKED_VAULT';
  depositLocation: string;
  originAgent: string;
  checksum: string;
  updatedAt: string;
  version: string;
  description: string;
  contentSummary: string;
  metadata: {
    resolution?: string;
    fileFormat?: string;
    targetStage?: string;
    derivationChain: string[];
  };
}

export interface EstateEdict {
  id: string;
  code: string;
  title: string;
  decreeText: string;
  status: 'ENFORCED' | 'UNDER_REVIEW' | 'BREACHED_ALERT';
  enactedDate: string;
  governingInvariant: string;
  violationPenalty: string;
}

export type MotionProtocolStage = 
  | 'STAGE_1_ALGORITHMIC_FORMULATION'
  | 'STAGE_2_CLOSED_LOOP_METRIC'
  | 'STAGE_3_RISK_CAPITAL_CLEARANCE'
  | 'STAGE_4_DELIVERY_EXECUTION'
  | 'STAGE_5_VERIFIED_CLOSED_LOOP';

export interface EstateMotion {
  id: string;
  title: string;
  sponsor: string;
  decreeRef: string;
  currentStage: MotionProtocolStage;
  closedLoopMetric: string;
  currentMetricValue: number;
  targetMetricValue: number;
  capitalAllocatedUSD: number;
  capitalConsumedUSD: number;
  founderCognitiveImpact: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  convergenceScore: number; // 0 - 100
  registeredArtifactIds: string[];
  lastAuditDate: string;
  auditVerdict: 'APPROVED_CONVERGENT' | 'REQUIRES_ANCHORING' | 'REJECTED_CHAOS_PATTERN';
  deliverableSummary: string;
}

export interface FinancialHealthMetrics {
  totalTreasuryUSD: number;
  monthlyBurnUSD: number;
  runwayMonths: number;
  dailyBurnUSD: number;
  capitalEfficiencyRatio: number;
  redLineThresholdDays: number;
  founderRestHoursPerNight: number;
  founderCognitiveLoadIndex: number; // 0 - 100
  founderContinuousDriftHours: number;
  unanchoredAgentThreads: number;
  closedFeedbackLoopsCount: number;
  openFeedbackLoopsCount: number;
}

// Concrete Infrastructure & Incident Types (MacBook, Cline, Router)
export interface KilledSessionRecord {
  id: string;
  agentName: string;
  costGBP: number;
  tokensConsumed: number;
  killReason: 'ENOSPC_DISK_FULL' | 'OOM_MACOS_MEMORY_PRESSURE' | 'ROUTER_TIMEOUT_HANGUP' | 'UNBOUNDED_DISCOVERY_LOOP';
  durationMinutes: number;
  salvageableDiffsFound: boolean;
  unindexedScansRun: number;
  timestamp: string;
  lastKnownPrompt: string;
}

export interface RouterProbeStatus {
  endpoint: string;
  port: number;
  protocol: 'HTTP' | 'WEBSOCKET' | 'TCP';
  state: 'OFFLINE_REFUSED' | 'PORT_NOT_BOUND' | 'TIMED_OUT' | 'LISTENING_OK';
  lastChecked: string;
  latencyMs: number | null;
  errorDetail: string;
  suggestedFix: string;
}

export interface MacBookResourceSnapshot {
  diskFreeGB: number;
  diskTotalGB: number;
  diskUsedPercent: number;
  memoryPressureStatus: 'CRITICAL_RED' | 'WARN_YELLOW' | 'NOMINAL_GREEN';
  activeClineSessions: number;
  maxRecommendedSessions: number;
  runawayNodeProcessesCount: number;
  reclaimableCacheGB: number;
}
