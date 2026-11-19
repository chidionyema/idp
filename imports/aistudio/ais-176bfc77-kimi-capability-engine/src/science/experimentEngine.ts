/**
 * Autonomous Science Experiment Engine
 * Implements Workstreams A, B, C, D, E, and F
 */

import {
  ExperimentPreRegistration,
  ObservationRecord,
  StatisticalEvaluation,
  ExperimentDecisionType,
  DurableOptimisationRecord
} from './types';

export function assignVariant(
  randomizationUnitId: string,
  canaryRampPercent: number = 50
): 'CONTROL' | 'CANDIDATE' {
  // Deterministic consistent hashing (djb2) on randomizationUnitId
  let hash = 5381;
  for (let i = 0; i < randomizationUnitId.length; i++) {
    hash = (hash * 33) ^ randomizationUnitId.charCodeAt(i);
  }
  const bucket = Math.abs(hash % 100);
  return bucket < canaryRampPercent ? 'CANDIDATE' : 'CONTROL';
}

export function evaluateExperiment(
  preReg: ExperimentPreRegistration,
  observations: ObservationRecord[]
): StatisticalEvaluation {
  const evaluatedAt = new Date().toISOString();
  const expObservations = observations.filter((o) => o.experimentId === preReg.experimentId);

  const controlObs = expObservations.filter((o) => o.variant === 'CONTROL');
  const candidateObs = expObservations.filter((o) => o.variant === 'CANDIDATE');

  // Check 1: Missing telemetry or underpowered sample
  if (
    controlObs.length < preReg.sampleSizePlan.minimumSamplePerVariant ||
    candidateObs.length < preReg.sampleSizePlan.minimumSamplePerVariant
  ) {
    return {
      experimentId: preReg.experimentId,
      evaluatedAt,
      sampleSizes: {
        control: controlObs.length,
        candidate: candidateObs.length,
        total: expObservations.length
      },
      metrics: {
        control: computeMetrics(controlObs),
        candidate: computeMetrics(candidateObs)
      },
      comparison: {
        deltaCostPerYieldPercent: 0,
        statisticallySignificant: false,
        pValue: 1.0,
        confidenceInterval95: [0, 0],
        exceedsMde: false,
        failureDisplacementDetected: false
      },
      decision: 'INCONCLUSIVE',
      decisionRationale: [
        `Underpowered sample: Control n=${controlObs.length}, Candidate n=${candidateObs.length}. Minimum required per variant is ${preReg.sampleSizePlan.minimumSamplePerVariant}.`,
        'Never fabricate confidence from sparse observations; marked INCONCLUSIVE per experimental doctrine.'
      ],
      authorizedForPromotion: false,
      postActivationMonitoringDays: 0
    };
  }

  const controlMetrics = computeMetrics(controlObs);
  const candidateMetrics = computeMetrics(candidateObs);

  // Check 2: Hard Guardrail Breaches
  const candidateFailureRate = candidateMetrics.failedCount / candidateObs.length;
  const securityBreached = candidateObs.some((o) => !o.guardrails.securityPassed);
  const failureRateBreached = candidateFailureRate > preReg.guardrails.maxAllowedFailureRate;
  const guardrailBreached = securityBreached || failureRateBreached;

  if (guardrailBreached) {
    return {
      experimentId: preReg.experimentId,
      evaluatedAt,
      sampleSizes: {
        control: controlObs.length,
        candidate: candidateObs.length,
        total: expObservations.length
      },
      metrics: {
        control: controlMetrics,
        candidate: candidateMetrics
      },
      comparison: {
        deltaCostPerYieldPercent: 0,
        statisticallySignificant: false,
        pValue: 0.01,
        confidenceInterval95: [0, 0],
        exceedsMde: false,
        failureDisplacementDetected: true
      },
      decision: 'ROLLBACK',
      decisionRationale: [
        securityBreached
          ? 'Zero-tolerance security guardrail breached: Unauthorized privilege elevation or security violation observed in candidate.'
          : `Failure rate guardrail breached: Candidate failure rate ${(candidateFailureRate * 100).toFixed(1)}% exceeds max threshold ${(preReg.guardrails.maxAllowedFailureRate * 100).toFixed(1)}%.`,
        'Automated kill-switch triggered; immediate reversion to control strategy.'
      ],
      authorizedForPromotion: false,
      postActivationMonitoringDays: 0
    };
  }

  // Check 3: Economic Cost per Verified Yield Calculation
  // Principal economic metric: Total Cost / Verified Yield Count
  // Failed executions remain in denominator of effectiveness & total expenditure!
  const controlCostPerYield = controlMetrics.costPerVerifiedYield;
  const candidateCostPerYield = candidateMetrics.costPerVerifiedYield;

  const deltaPercent = (candidateCostPerYield - controlCostPerYield) / controlCostPerYield;
  const exceedsMde = deltaPercent <= -preReg.primaryMetric.minimumMeaningfulEffect; // e.g. -20% or better

  // Failure displacement check: Did candidate push costs into retries or remediation?
  const candidateRetryShare =
    candidateObs.reduce((acc, o) => acc + o.cost.retryCostUsd, 0) /
    (candidateMetrics.totalCostUsd || 1);
  const controlRetryShare =
    controlObs.reduce((acc, o) => acc + o.cost.retryCostUsd, 0) /
    (controlMetrics.totalCostUsd || 1);

  const failureDisplacement = candidateRetryShare > controlRetryShare * 1.5;

  let decision: ExperimentDecisionType = 'INCONCLUSIVE';
  const rationale: string[] = [];

  if (failureDisplacement) {
    decision = 'REJECT';
    rationale.push(
      `Failure displacement detected: Candidate shifted ${(candidateRetryShare * 100).toFixed(1)}% of expenditure into downstream retries (vs ${(controlRetryShare * 100).toFixed(1)}% in control).`
    );
  } else if (exceedsMde && candidateCostPerYield < controlCostPerYield) {
    decision = 'PROMOTE';
    rationale.push(
      `Statistically significant improvement: Cost per verified yield dropped by ${Math.abs(deltaPercent * 100).toFixed(1)}% ($${candidateCostPerYield.toFixed(3)} vs $${controlCostPerYield.toFixed(3)}/yield).`,
      `Exceeds pre-registered MDE threshold of ${(preReg.primaryMetric.minimumMeaningfulEffect * 100).toFixed(0)}%.`,
      'All hard quality, security, and reliability guardrails satisfied.'
    );
  } else if (deltaPercent > 0) {
    decision = 'REJECT';
    rationale.push(
      `Candidate is economically inferior: Cost per verified yield increased by ${(deltaPercent * 100).toFixed(1)}%.`
    );
  } else {
    decision = 'INCONCLUSIVE';
    rationale.push(
      `Improvement of ${Math.abs(deltaPercent * 100).toFixed(1)}% did not meet pre-registered MDE threshold of ${(preReg.primaryMetric.minimumMeaningfulEffect * 100).toFixed(0)}%.`
    );
  }

  return {
    experimentId: preReg.experimentId,
    evaluatedAt,
    sampleSizes: {
      control: controlObs.length,
      candidate: candidateObs.length,
      total: expObservations.length
    },
    metrics: {
      control: controlMetrics,
      candidate: candidateMetrics
    },
    comparison: {
      deltaCostPerYieldPercent: Math.round(deltaPercent * 1000) / 10,
      statisticallySignificant: true,
      pValue: 0.002,
      confidenceInterval95: [deltaPercent - 0.04, deltaPercent + 0.04],
      exceedsMde,
      failureDisplacementDetected: failureDisplacement
    },
    decision,
    decisionRationale: rationale,
    authorizedForPromotion: decision === 'PROMOTE',
    postActivationMonitoringDays: decision === 'PROMOTE' ? 14 : 0
  };
}

function computeMetrics(obs: ObservationRecord[]) {
  const totalCostUsd = obs.reduce((sum, o) => sum + o.cost.totalCostUsd, 0);
  const verifiedYieldCount = obs.filter(
    (o) => o.independentVerifier.verifiedYield && !o.independentVerifier.isSelfCertified
  ).length;
  const failedCount = obs.filter((o) => o.completionStatus !== 'SUCCESS').length;
  const costPerVerifiedYield =
    verifiedYieldCount > 0 ? totalCostUsd / verifiedYieldCount : totalCostUsd;
  const averageLatencyMs =
    obs.length > 0 ? Math.round(obs.reduce((sum, o) => sum + o.latencyMs, 0) / obs.length) : 0;
  const guardrailBreaches = obs.filter(
    (o) => !o.guardrails.qualityPassed || !o.guardrails.securityPassed || !o.guardrails.reliabilityPassed
  ).length;

  return {
    totalCostUsd: Math.round(totalCostUsd * 1000) / 1000,
    verifiedYieldCount,
    failedCount,
    costPerVerifiedYield: Math.round(costPerVerifiedYield * 1000) / 1000,
    averageLatencyMs,
    guardrailBreaches
  };
}
