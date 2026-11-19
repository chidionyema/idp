/**
 * Types for Greenlane Failure-Class Elimination (Owner: Gemini)
 * Priority: P0 — delivery throughput
 * Scope: IDP + Argon Genesis
 * Operating doctrine: FLOW
 */

export interface GreenlaneFailureClass {
  id: string; // e.g. "GL-FAIL-042"
  canonicalName: string;
  subsystem: 'PRE_COMMIT' | 'AGENT_SANDBOX' | 'CI_RUNNER' | 'INTEGRATION_TEST' | 'CONTAINER_BUILD';
  rootCause: string;
  baselineMetrics: {
    failureSharePercent: number; // Share of all Greenlane failures
    failedRunCount: number;
    wastedCiMinutes: number;
    averageRetriesPerBranch: number;
    blockedDeliveriesCount: number;
    estimatedCostUsd: number;
  };
  recurrenceRisk: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  remedyStrategy: string;
  preventionBoundary: 'PRE_COMMIT' | 'PRE_PUSH' | 'AGENT_SANDBOX_EXIT' | 'CI_GATE';
}

export interface StagedPatchAuditResult {
  patchId: string;
  branchName: string;
  driftDetected: boolean;
  driftDetails?: {
    filesWithUnstagedFormatting: string[];
    whitespaceDifferencesCount: number;
    lintViolationsFound: string[];
  };
  remediationAttempted: boolean;
  remediationSuccessful: boolean;
  remediationActionTaken: 'BOUNDED_AUTO_STAGE_REPAIR' | 'EMIT_ONE_PASS_FEEDBACK' | 'NO_OP';
  boundedIterationsCount: number; // Strictly <= 1 to avoid infinite loops
  isolatedWorktreeCompilation: 'PASSED' | 'FAILED' | 'SKIPPED';
  executionDurationMs: number;
  actionableAgentFeedback?: {
    summary: string;
    preciseFileLocations: { file: string; line: number; message: string; suggestedFix: string }[];
  };
}

export interface GreenlaneRegressionTest {
  id: string;
  name: string;
  environment: 'Python 3.9' | 'Python 3.12' | 'Node 22 LTS';
  category: 'STAGED_PATCH_ISOLATION' | 'BOUNDED_REPAIR' | 'ONE_PASS_DIAGNOSTICS' | 'NEGATIVE_SYNTAX_GUARD';
  status: 'PASSED' | 'FAILED';
  executionTimeMs: number;
  assertion: string;
}

export interface GreenlaneReportData {
  failureClassId: string;
  canonicalName: string;
  rootCause: string;
  baselineFrequency: string;
  baselineWastedMinutes: number;
  baselineCostUsd: number;
  correctionChangedFiles: string[];
  commitSha: string;
  deployedSha: string;
  testSuiteCommands: string[];
  githubActionsUrl: string;
  greenlaneLandingRef: string;
  effect: {
    recurrenceReduction: string;
    retriesReduction: string;
    wastedMinutesSaved: number;
    remainingUncertainty: string;
  };
  nextLeverageOpportunity: {
    id: string;
    name: string;
    projectedSavingsMinutes: number;
    priority: 'P0' | 'P1';
  };
}
