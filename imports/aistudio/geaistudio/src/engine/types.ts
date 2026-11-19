export type RoutingStrategy =
  | 'priority_failover'
  | 'lowest_latency'
  | 'weighted_cost'
  | 'least_busy';

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export type LaneFaultMode =
  | 'healthy'
  | '401_upstream_key'
  | '402_credit_exhausted'
  | '429_rate_limit'
  | '503_unavailable'
  | 'latency_spike';

export interface ClientKeyRecord {
  id: string;
  label: string;
  keyHash: string;
  maskedKey: string;
  rawKey: string;
  dailyBudgetUsd: number;
  spentTodayUsd: number;
  active: boolean;
  boundClient: string;
  lastVerifiedAt: string;
  lastProbeStatus: 'pass' | 'fail';
}

export interface CapSaveResult {
  ok: boolean;
  updatedKeyId: string;
  previousBudgetUsd: number;
  newBudgetUsd: number;
  preservedKeyCount: number;
  verifiedKeys: Array<{ id: string; label: string; valid: boolean }>;
  error?: string;
  rolledBack?: boolean;
}

export interface UpstreamLane {
  id: string;
  provider: string;
  model: string;
  endpoint: string;
  priority: number;
  weight: number;
  baseLatencyMs: number;
  costPer1kTokensUsd: number;
  vaultKeyPresent: boolean;
  creditBalanceUsd: number;
  faultMode: LaneFaultMode;
  circuitState: CircuitState;
  failureCount: number;
  successCount: number;
  activeInFlight: number;
  lastFailureReason: string | null;
  lastOpenedAt: number | null;
  cooldownMs: number;
}

export interface LaneAttempt {
  laneId: string;
  provider: string;
  model: string;
  httpStatus: number;
  errorType: string | null;
  detail: string;
  latencyMs: number;
  outcome: 'success' | 'failed' | 'skipped_open_circuit' | 'skipped_missing_vault_key';
}

export interface RouteRequest {
  clientKey: string;
  modelSlug: string;
  estimatedTokens: number;
  cachedInputTokens?: number;
  outputTokens?: number;
  reasoningTokens?: number;
  contextTrimSavedTokens?: number;
  missionId?: string;
  ownerId?: string;
  sessionId?: string;
  adapter?: 'OpenCode V2' | 'Direct SDK' | 'CI Runner';
  strategy?: RoutingStrategy;
  idempotencyKey?: string;
  nowMs?: number;
}

export interface RouteErrorPayload {
  error: {
    detail: string;
    type: 'unauthorized' | 'billing_exhausted' | 'budget_exceeded' | 'upstream' | 'validation';
    perLaneDiagnostics?: LaneAttempt[];
  };
}

export interface RouteResult {
  ok: boolean;
  httpStatus: number;
  packetId?: string;
  selectedLaneId: string | null;
  selectedProvider: string | null;
  modelSlug: string;
  gatewayOverheadUs: number;
  totalLatencyMs: number;
  costUsd: number;
  withoutPennydCostUsd?: number;
  usdSaved?: number;
  tokensSaved?: number;
  receiptSequence: number | null;
  attempts: LaneAttempt[];
  errorPayload?: RouteErrorPayload;
}

export interface WalReceipt {
  sequence: number;
  idempotencyKey: string;
  timestamp: string;
  clientKeyId: string;
  laneId: string;
  provider: string;
  model: string;
  tokens: number;
  costUsd: number;
  httpStatus: number;
  persistedToWal: boolean;
  checkpointed: boolean;
}

export interface DagsterAsset {
  key: string;
  label: string;
  group: 'vault' | 'ledger' | 'routing' | 'wal';
  upstreamDeps: string[];
  status: 'materialized' | 'stale' | 'failed';
  lastMaterializedAt: string;
  materializationCount: number;
  partitionKey: string;
  summary: string;
}

export interface DagsterSensor {
  id: string;
  name: string;
  targetAsset: string;
  intervalSec: number;
  status: 'running' | 'triggered' | 'idle';
  lastTickAt: string;
  lastVerdict: string;
  triggersFired: number;
}

export interface DagsterRunEvent {
  id: string;
  timestamp: string;
  sensorId: string;
  assetKey: string;
  action: string;
  outcome: 'success' | 'repaired' | 'warning';
  detail: string;
}

export interface RestartComparisonReport {
  mode: 'dagster_durable' | 'legacy_launchd';
  receiptsBeforeRestart: number;
  receiptsAfterRestart: number;
  droppedReceipts: number;
  vaultKeysHydratedOnBoot: boolean;
  clientKeysPreserved: number;
  recoveryTimeMs: number;
  events: string[];
}

export interface AssertionCheck {
  name: string;
  passed: boolean;
  expected: string;
  actual: string;
}

export interface VerificationCaseResult {
  id: string;
  category: 'integration' | 'falsifier';
  title: string;
  hypothesis: string;
  passed: boolean;
  durationMs: number;
  assertions: AssertionCheck[];
  counterexample: string | null;
}

export interface VerificationSuiteReport {
  runAt: string;
  totalCases: number;
  passedCases: number;
  failedCases: number;
  totalAssertions: number;
  passedAssertions: number;
  durationMs: number;
  cases: VerificationCaseResult[];
}

export interface ChaosConfig {
  requestCount: number;
  concurrency: number;
  strategy: RoutingStrategy;
  injectDeepSeek402: boolean;
  injectWorkerCrash: boolean;
  injectCapSaveRace: boolean;
  injectMultiLane503: boolean;
  injectLatencySpike: boolean;
}

export interface ChaosTimelineEvent {
  step: number;
  requestIndex: number;
  event: string;
  severity: 'info' | 'warning' | 'critical' | 'resolved';
  detail: string;
}

export interface ChaosReport {
  runAt: string;
  config: ChaosConfig;
  totalRequests: number;
  succeededRequests: number;
  failedRequests: number;
  failoverRoutedRequests: number;
  successRatePct: number;
  p50OverheadUs: number;
  p95OverheadUs: number;
  p99OverheadUs: number;
  p50TotalLatencyMs: number;
  p95TotalLatencyMs: number;
  p99TotalLatencyMs: number;
  receiptsProduced: number;
  receiptsPreserved: number;
  receiptsDropped: number;
  capSaveRacesRun: number;
  capSaveKeysPreserved: boolean;
  slaPassed: boolean;
  slaVerdict: string;
  timeline: ChaosTimelineEvent[];
}
