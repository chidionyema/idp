/**
 * Core type definitions for Kimi Capability-First Estate Engine
 * Scope: IDP + Argon Genesis Architecture
 */

export type CapabilityOwner = 'IDP_CORE' | 'ARGON_GENESIS' | 'INFRA_SECOPS' | 'DATA_PLATFORM';

export type OperationalReadiness =
  | 'discovered'              // Registered in source/manifest, no test verification
  | 'implemented'             // Code exists, unit tests pass, not in runtime
  | 'tested'                  // Integration tests passed in CI/staging
  | 'deployed'                // Present in cluster/target runtime
  | 'operationally_verified'  // Healthchecks passing, telemetry active, verified SLA
  | 'degraded';               // Healthcheck failure, dependency outage, active incident

export type ResolutionDecisionType =
  | 'REUSE'           // 1:1 Direct execution of existing operationally_verified capability
  | 'COMPOSE'         // Orchestrated pipeline of 2+ verified capabilities
  | 'ADAPT'           // Existing capability used via typed parameter/format adapter
  | 'IMPLEMENT_NEW';  // Genuine gap: estate has no suitable capability; commission new build

export interface TypeContract {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  required: boolean;
  description: string;
  schema?: Record<string, unknown>;
}

export interface EstateCapability {
  id: string;
  name: string;
  version: string;
  owner: CapabilityOwner;
  authoritativeSource: string; // e.g., 'idp/deploy/preview-engine', 'argon/flow/executor'
  description: string;
  tags: string[];
  inputs: TypeContract[];
  outputs: TypeContract[];
  requiredPermissions: string[];
  dependencies: string[];
  readiness: OperationalReadiness;
  readinessEvidence: {
    lastHealthCheck: string;
    uptime90d: number;
    telemetrySource: string;
    verifiedExecutionCount: number;
    lastFailureReason?: string;
  };
  slaMinutes: number;
  avoidedHoursOnReuse: number; // Defensible estimated dev/testing hours avoided
}

export interface ResolutionRationale {
  decision: ResolutionDecisionType;
  primaryCapabilityId?: string;
  composedCapabilityIds?: string[];
  confidenceScore: number; // 0.0 to 1.0
  reasons: string[];
  compatibilityChecks: {
    typeSafety: boolean;
    permissionsSatisfied: boolean;
    dependenciesAvailable: boolean;
    readinessAcceptable: boolean;
  };
  adaptationLayer?: {
    inputTransformRequired: boolean;
    outputTransformRequired: boolean;
    notes: string;
  };
  avoidedWorkHoursEstimate: number;
  frictionRisk: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH';
}

export type FlowPhase =
  | '1_DISCOVER'
  | '2_CONTRACT_MATCH'
  | '3_RANK_AND_DECIDE'
  | '4_EXECUTION_GATE'
  | '5_FLOW_EXECUTE'
  | '6_VERIFY_AND_YIELD';

export interface FlowStepLog {
  phase: FlowPhase;
  status: 'PENDING' | 'SUCCESS' | 'DEGRADED_FALLBACK' | 'BLOCKED';
  timestamp: string;
  details: string;
  metadata?: Record<string, unknown>;
}

export interface FlowExecutionResult {
  instruction: string;
  flowLifecycleId: string; // e.g. "FLOW-47-EXEC-7771"
  decision: ResolutionDecisionType;
  resolvedCapabilities: EstateCapability[];
  steps: FlowStepLog[];
  executionSuccess: boolean;
  recoveryPathUsed?: string;
  executionOutput?: Record<string, unknown>;
  yield: {
    avoidedEngineeringHours: number;
    avoidedCostUsd: number; // At standard $150/hr blended estate rate
    tokenSavings: number;
    zeroImplementationProof: string;
  };
  rationale: ResolutionRationale;
}

export interface BaselineInstructionRecord {
  id: number;
  instruction: string;
  domain: 'IDP' | 'ARGON_GENESIS';
  capabilityExisted: boolean;
  existingCapabilityId?: string;
  baselineDiscovered: boolean;
  baselineActionTaken: 'DUPLICATE_IMPLEMENTATION' | 'ABANDONED_RETRY' | 'MANUAL_RECOVERY' | 'ACCIDENTAL_REUSE' | 'UNKNOWN';
  baselineHoursWasted: number;
  evidenceNotes: string;
  postChangeResolution: ResolutionDecisionType;
  postChangeCapabilityId?: string;
  postChangeAvoidedHours: number;
  verificationOutcome: 'VERIFIED_REUSE' | 'VERIFIED_COMPOSE' | 'VERIFIED_ADAPT' | 'VERIFIED_NEW_BUILD';
}

export interface AdversarialTestCase {
  id: string;
  name: string;
  adversarialCondition: 'STALE_CAPABILITY' | 'INCOMPATIBLE_CONTRACT' | 'UNAVAILABLE_DEPENDENCY' | 'INSUFFICIENT_AUTH' | 'MISLEADING_METADATA' | 'DUPLICATE_CONFLICT' | 'INVOCATION_FAILURE';
  description: string;
  targetedCapabilityId: string;
  simulatedFault: Record<string, unknown>;
  expectedSecurityBehavior: string;
  expectedResolution: ResolutionDecisionType | 'REJECTED_SECURITY_GATE';
  executionVerification: {
    passed: boolean;
    enforcedBoundary: string;
    recoveryBounded: boolean;
    logs: string[];
  };
}

export interface EndToEndTrace {
  id: string;
  title: string;
  sourceIssue: string;
  instruction: string;
  callerIdentity: string;
  capabilityUsed: string;
  typedInputsProvided: Record<string, unknown>;
  flowLifecycleSteps: {
    step: string;
    evidence: string;
    elapsedMs: number;
  }[];
  independentVerificationEvidence: {
    telemetryTraceId: string;
    auditLogHash: string;
    gitDiffZeroProof: string;
    avoidedWorkHours: number;
  };
}
