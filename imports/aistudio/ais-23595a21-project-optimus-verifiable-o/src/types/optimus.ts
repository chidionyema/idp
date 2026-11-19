/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type SurfaceType =
  | 'git_commit_push'
  | 'ci_cd_pipeline'
  | 'microservice_engine'
  | 'infra_as_code'
  | 'scheduled_job'
  | 'autonomous_agent'
  | 'network_ingress_egress'
  | 'runnable_script';

export interface SurfaceDefinition {
  id: SurfaceType;
  name: string;
  tagline: string;
  category: string;
  instrumentationTechnique: string;
  antiCircumventionMechanism: string;
  activeNodes: number;
  meteredCoveragePct: number;
  hardInvariantsCount: number;
  iconName: string;
}

export type InvariantOperator = '>=' | '<=' | '==' | '!=' | 'not_contains' | 'strict_boolean';

export interface InvariantRule {
  id: string;
  name: string;
  metricKey: string;
  operator: InvariantOperator;
  threshold: number | string | boolean;
  unit: string;
  description: string;
  applicableSurfaces: SurfaceType[];
  isHardGate: boolean; // if false, still blocking if violated in zealous mode
}

export interface InvariantEvaluationResult {
  ruleId: string;
  ruleName: string;
  metricKey: string;
  actualValue: number | string | boolean;
  threshold: number | string | boolean;
  passed: boolean;
  deviation: string;
  reason: string;
}

export interface MetricPayload {
  surface: SurfaceType;
  entityId: string;
  actor: string;
  branchOrEnv?: string;
  metrics: Record<string, number | string | boolean>;
  bypassFlagsDetected?: string[];
  rawCodeSnippet?: string;
}

export interface GateVerificationOutcome {
  allowed: boolean;
  status: 'RATIFIED_AND_SIGNED' | 'REJECTED_BLOCKED';
  rejectionReasons: string[];
  evaluationResults: InvariantEvaluationResult[];
  computedHash: string;
  merkleLeaf: string;
  cryptographicSignature?: string;
  signedPushToken?: string;
  timestamp: string;
  surface: SurfaceType;
  entityId: string;
  actor: string;
  isCircumventionAttempt: boolean;
}

export interface MerkleLedgerBlock {
  index: number;
  timestamp: string;
  surface: SurfaceType;
  entityId: string;
  actor: string;
  blockHash: string;
  previousHash: string;
  merkleRoot: string;
  status: 'RATIFIED_AND_SIGNED' | 'REJECTED_BLOCKED';
  signature: string;
  metricsSnapshot: Record<string, number | string | boolean>;
  violationCount: number;
  rejectionSummary?: string;
  attestationSummary: string;
}

export interface EstateExecutiveSummary {
  overallCoverageRate: number;
  totalSurfacesMonitored: number;
  totalInvariantsEnforced: number;
  circumventionAttemptsBlocked: number;
  verifiedAttestationsCount: number;
  merkleChainHeight: number;
  lastRatifiedTimestamp: string;
  bypassToleranceRate: number; // Always 0.000%
  zeroTrustStatus: 'ABSOLUTE_INTEGRITY' | 'ALERT_DETECTED';
}

export interface HistoricalAttemptComparison {
  generation: string;
  name: string;
  description: string;
  vulnerabilityToBypass: string;
  mathematicalProof: string;
  estateBreadth: string;
  whyFailedOrSuperseded: string;
  status: 'VULNERABLE' | 'OBSOLETE' | 'OPTIMUS_ACTIVE';
}

export interface TelemetryTimeSeriesPoint {
  timestamp: string;
  label: string;
  ratified: number;
  circumventions: number;
  p99LatencyMs: number;
  p50LatencyMs: number;
  tokenVelocityAvg: number;
  driftIndexAvg: number;
  anomalyFlagCount: number;
}

export interface DetectedAnomaly {
  id: string;
  surface: SurfaceType;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  title: string;
  description: string;
  detectedAt: string;
  metricObserved: string;
  threshold: string;
  rootCauseAnalysis: string;
  mathematicalRemediation: string;
}

export interface UltraOptimizationPrescription {
  id: string;
  domain: 'KERNEL_EBPF' | 'AST_PARSER' | 'OTEL_RINGBUFFER' | 'TOKEN_CACHE' | 'NETWORK_MESH';
  title: string;
  currentLatencyCost: string;
  projectedLatencySavings: string;
  impactDescription: string;
  cliCommandOrConfig: string;
}

export interface LatencyHeatmapCell {
  surfaceId: SurfaceType;
  surfaceName: string;
  timeLabel: string;
  timestamp: string;
  p50Ms: number;
  p95Ms: number;
  p99Ms: number;
  requestCount: number;
  isBottleneckCluster: boolean;
  clusterSeverity: 'CRITICAL' | 'WARNING' | 'NOMINAL';
  bottleneckRootCause?: string;
  prescribedOptimization?: string;
}

export interface DayZeroSecurityAlert {
  id: string;
  surface: SurfaceType;
  surfaceName: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  dayZeroBaselineMetric: string;
  realTimeObservedMetric: string;
  deviationPercent: string;
  threatVector: string;
  rootCause: string;
  mitigationEnforced: string;
  status: 'ACTIVE_INTERCEPTED' | 'QUARANTINED' | 'RESOLVED';
  timestamp: string;
}

export interface SurfaceLatencyCapConfig {
  surfaceId: SurfaceType;
  surfaceName: string;
  category: string;
  baselineLatencyMs: number;
  maxLatencyCapMs: number;
  enforcementMode: 'HARD_KILL_SWITCH' | 'AUTO_QUARANTINE' | 'WARN_AUDIT_LOG';
  activeViolationsCount: number;
  lastBreachedTimestamp?: string;
  autoRemediationAction: string;
  threatDescription: string;
}


