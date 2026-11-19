/**
 * P0 Autonomous Science & Optimisation Lane — Core Types
 * Doctrine: FLOW (Fractal Lifecycle of Operational Work)
 * Scope: Genesis, Merian Lab, IDP Telemetry, Feature Flags, Forge Experiment Records
 */

export type ExperimentState =
  | 'PROPOSED'
  | 'REGISTERED'
  | 'RUNNING'
  | 'EVALUATING'
  | 'DECIDED'
  | 'PROMOTED'
  | 'REJECTED'
  | 'INCONCLUSIVE'
  | 'MONITORING'
  | 'CLOSED'
  | 'ROLLED_BACK';

export type ExperimentDecisionType = 'PROMOTE' | 'REJECT' | 'INCONCLUSIVE' | 'ROLLBACK';

export interface GuardrailStatus {
  passed: boolean;
  metric: string;
  observedValue: number;
  threshold: number;
  breached: boolean;
}

export interface ObservationRecord {
  observationId: string;
  timestamp: string;
  instructionId: string;
  instructionClass: string;
  executionPath: string;
  model: string;
  environment: 'production' | 'staging' | 'canary' | 'ephemeral';

  experimentId: string;
  variant: 'CONTROL' | 'CANDIDATE';
  randomizationUnitId: string;
  exposureRecorded: boolean;

  configVersion: string;
  implementationSha: string;

  // Fully accounted cost breakdown
  cost: {
    executionCostUsd: number;
    verificationCostUsd: number;
    retryCostUsd: number;
    remediationCostUsd: number;
    totalCostUsd: number;
  };

  latencyMs: number;
  completionStatus: 'SUCCESS' | 'FAILED' | 'RETRY_EXHAUSTED' | 'TIMED_OUT';

  // Independent verification
  independentVerifier: {
    verifierId: string;
    isSelfCertified: boolean; // Must be FALSE
    evidenceReference: string;
    verifiedYield: boolean;
  };

  guardrails: {
    qualityPassed: boolean;
    securityPassed: boolean;
    reliabilityPassed: boolean;
  };
}

export interface ExperimentPreRegistration {
  experimentId: string;
  version: number;
  registrationHash: string; // Cryptographic SHA of pre-registration
  createdAt: string;
  owner: string;

  hypothesis: string;
  expectedOperationalValue: string;

  instructionPopulation: string;
  eligibilityCriteria: string[];

  controlStrategy: {
    name: string;
    description: string;
    configKey: string;
    configValue: unknown;
  };

  candidateStrategy: {
    name: string;
    description: string;
    configKey: string;
    configValue: unknown;
  };

  primaryMetric: {
    name: 'cost_per_verified_yield';
    direction: 'MINIMIZE';
    unit: 'USD_per_yield';
    minimumMeaningfulEffect: number; // e.g. 0.20 (20% reduction)
  };

  secondaryDiagnostics: string[];

  guardrails: {
    maxAllowedFailureRate: number; // e.g. 0.05 (5%)
    maxLatencyP99Ms: number;
    securityViolationTolerance: 0;
  };

  rollbackConditions: string[];

  randomisationUnit: 'INSTRUCTION_ID' | 'BRANCH_NAME' | 'AGENT_SESSION';
  exposureMechanism: 'DYNAMIC_FEATURE_FLAG';

  sampleSizePlan: {
    minimumSamplePerVariant: number;
    plannedDurationHours: number;
    budgetLimitUsd: number;
    maxBlastRadiusPercent: number; // Canary cap, e.g. 25%
  };

  stoppingPolicy: {
    sequentialBoundaryAlpha: number;
    allowEarlyStopForHarm: true;
    allowEarlyStopForFutility: true;
  };
}

export interface StatisticalEvaluation {
  experimentId: string;
  evaluatedAt: string;
  sampleSizes: {
    control: number;
    candidate: number;
    total: number;
  };

  metrics: {
    control: {
      totalCostUsd: number;
      verifiedYieldCount: number;
      failedCount: number;
      costPerVerifiedYield: number;
      averageLatencyMs: number;
      guardrailBreaches: number;
    };
    candidate: {
      totalCostUsd: number;
      verifiedYieldCount: number;
      failedCount: number;
      costPerVerifiedYield: number;
      averageLatencyMs: number;
      guardrailBreaches: number;
    };
  };

  comparison: {
    deltaCostPerYieldPercent: number; // negative = cheaper
    statisticallySignificant: boolean;
    pValue: number;
    confidenceInterval95: [number, number];
    exceedsMde: boolean;
    failureDisplacementDetected: boolean;
  };

  decision: ExperimentDecisionType;
  decisionRationale: string[];
  authorizedForPromotion: boolean;
  postActivationMonitoringDays: number;
}

export interface DurableOptimisationRecord {
  recordId: string;
  experimentId: string;
  instructionClass: string;
  completedAt: string;
  decision: ExperimentDecisionType;
  verifiedSavingsUsdPerYield: number;
  promotedConfigKey?: string;
  promotedConfigValue?: unknown;
  promotedSha?: string;
  independentEvidenceReceipt: string;
  rollbackTriggerConditions: string[];
  monitoringWindowStatus: 'ACTIVE' | 'PASSED' | 'ROLLED_BACK';
  institutionalLearningNotes: string[];
}
