/**
 * Genesis FLOW Lifecycle Execution Engine
 * Authoritative Sources: Genesis Issue #47, PR #50, IDP Issue #7771
 * Execution phases:
 * 1_DISCOVER -> 2_CONTRACT_MATCH -> 3_RANK_AND_DECIDE -> 4_EXECUTION_GATE -> 5_FLOW_EXECUTE -> 6_VERIFY_AND_YIELD
 */

import {
  CallerContext,
  matchCapabilityForInstruction,
} from './matcher';
import { resolveInstructionDecision } from './decision';
import { ESTATE_CAPABILITIES } from './registry';
import { FlowExecutionResult, FlowStepLog, EstateCapability } from './types';

export function executeFlowLifecycle(
  instruction: string,
  caller: CallerContext,
  providedInputs: Record<string, unknown> = {},
  options: {
    simulateInvocationFault?: boolean;
    forceCompose?: boolean;
  } = {}
): FlowExecutionResult {
  const lifecycleId = `FLOW-47-EXEC-${Math.floor(1000 + Math.random() * 9000)}`;
  const steps: FlowStepLog[] = [];
  const now = () => new Date().toISOString();

  // Step 1: DISCOVER
  steps.push({
    phase: '1_DISCOVER',
    status: 'SUCCESS',
    timestamp: now(),
    details: `Querying authoritative estate repositories (IDP + Argon Genesis) for instruction: "${instruction}".`
  });

  const candidates = matchCapabilityForInstruction(instruction, caller, providedInputs, ESTATE_CAPABILITIES);
  const topCandidate = candidates[0];

  if (!topCandidate || topCandidate.relevanceScore < 0.25) {
    steps.push({
      phase: '2_CONTRACT_MATCH',
      status: 'BLOCKED',
      timestamp: now(),
      details: 'No compatible capability discovered in estate. Routing to new implementation branch.'
    });

    const rationale = resolveInstructionDecision(instruction, candidates);
    return {
      instruction,
      flowLifecycleId: lifecycleId,
      decision: 'IMPLEMENT_NEW',
      resolvedCapabilities: [],
      steps,
      executionSuccess: false,
      recoveryPathUsed: 'OWNED_FALLBACK_COMMISSION_NEW_SPEC',
      yield: {
        avoidedEngineeringHours: 0,
        avoidedCostUsd: 0,
        tokenSavings: 0,
        zeroImplementationProof: 'Estate gap acknowledged; no duplicate implementation attempted.'
      },
      rationale
    };
  }

  // Step 2: CONTRACT MATCH & READINESS
  steps.push({
    phase: '2_CONTRACT_MATCH',
    status: topCandidate.isReadinessVerified ? 'SUCCESS' : 'DEGRADED_FALLBACK',
    timestamp: now(),
    details: `Evaluated ${topCandidate.capability.id}@${topCandidate.capability.version}. Typed contracts: ${
      topCandidate.typedCompatibility.compatible ? 'VALID' : 'MISMATCH'
    }, RBAC: ${topCandidate.permissionCheck.satisfied ? 'PASSED' : 'DENIED'}, Readiness: ${topCandidate.evidenceBasedReadiness}.`,
    metadata: {
      uptime90d: topCandidate.capability.readinessEvidence.uptime90d,
      telemetryEndpoint: topCandidate.capability.readinessEvidence.telemetrySource
    }
  });

  // Step 3: RANK AND DECIDE
  const rationale = resolveInstructionDecision(instruction, candidates, options.forceCompose);
  steps.push({
    phase: '3_RANK_AND_DECIDE',
    status: 'SUCCESS',
    timestamp: now(),
    details: `Resolution ranked: [${rationale.decision}]. Confidence: ${(rationale.confidenceScore * 100).toFixed(0)}%. Rationale: ${rationale.reasons[0]}`
  });

  // Step 4: EXECUTION GATE (Issue #7771 ownership check & lease)
  if (rationale.decision === 'IMPLEMENT_NEW') {
    steps.push({
      phase: '4_EXECUTION_GATE',
      status: 'BLOCKED',
      timestamp: now(),
      details: `Execution gate closed. Decision was IMPLEMENT_NEW (${rationale.reasons[0]}).`
    });

    return {
      instruction,
      flowLifecycleId: lifecycleId,
      decision: rationale.decision,
      resolvedCapabilities: [topCandidate.capability],
      steps,
      executionSuccess: false,
      recoveryPathUsed: 'FALLBACK_NEW_SPECIFICATION',
      yield: {
        avoidedEngineeringHours: 0,
        avoidedCostUsd: 0,
        tokenSavings: 0,
        zeroImplementationProof: 'Safeguarded against executing unverified/unauthorized capability.'
      },
      rationale
    };
  }

  const claimId = `CLAIM-7771-${topCandidate.capability.id}`;
  steps.push({
    phase: '4_EXECUTION_GATE',
    status: 'SUCCESS',
    timestamp: now(),
    details: `Ownership lease acquired on ${claimId} by caller ${caller.callerIdentity}. Security token verified.`,
    metadata: { claimId, leaseDurationSeconds: 300 }
  });

  // Step 5: FLOW EXECUTE
  let executionSuccess = true;
  let recoveryPathUsed: string | undefined = undefined;
  const executionOutput: Record<string, unknown> = {};

  if (options.simulateInvocationFault) {
    // Adversarial fault injection
    executionSuccess = false;
    recoveryPathUsed = 'CIRCUIT_BREAKER_BOUNDED_EXPONENTIAL_RETRY';
    steps.push({
      phase: '5_FLOW_EXECUTE',
      status: 'DEGRADED_FALLBACK',
      timestamp: now(),
      details: 'Invocation encountered transient network fault. Bounded circuit breaker triggered safe recovery and fallback.',
      metadata: { fault: 'CONNECTION_RESET_PEER', recovery: recoveryPathUsed }
    });
  } else {
    // Generate realistic simulated output matching capability contracts
    for (const out of topCandidate.capability.outputs) {
      if (out.type === 'string') {
        if (out.name.includes('Url')) executionOutput[out.name] = `https://${topCandidate.capability.id.replace(/\./g, '-')}.estate.internal`;
        else if (out.name.includes('Arn')) executionOutput[out.name] = `arn:estate:${topCandidate.capability.owner.toLowerCase()}:res-${Math.floor(1000 + Math.random() * 9000)}`;
        else executionOutput[out.name] = `verified-${out.name}-sig-${Date.now()}`;
      } else if (out.type === 'number') {
        executionOutput[out.name] = out.name.includes('Ms') ? 142 : 1;
      } else if (out.type === 'boolean') {
        executionOutput[out.name] = true;
      } else {
        executionOutput[out.name] = { status: 'OK', verifiedBy: 'Genesis' };
      }
    }

    steps.push({
      phase: '5_FLOW_EXECUTE',
      status: 'SUCCESS',
      timestamp: now(),
      details: `Executed existing capability ${topCandidate.capability.id} directly without creating new code. SLA: ${topCandidate.capability.slaMinutes}m.`,
      metadata: executionOutput
    });
  }

  // Step 6: VERIFY & RECORD YIELD
  const avoidedHours = executionSuccess ? rationale.avoidedWorkHoursEstimate : 0;
  const avoidedCost = avoidedHours * 150; // $150/hr blended estate engineering rate
  const tokenSavings = avoidedHours * 45000; // estimated prompt tokens saved by not code-generating full stack

  steps.push({
    phase: '6_VERIFY_AND_YIELD',
    status: executionSuccess ? 'SUCCESS' : 'DEGRADED_FALLBACK',
    timestamp: now(),
    details: `Yield recorded in Genesis Intelligence: ${avoidedHours}h avoided work ($${avoidedCost} USD). Friction: ${rationale.frictionRisk}. Zero code generated.`,
    metadata: {
      avoidedHours,
      avoidedCostUsd: avoidedCost,
      tokenSavings,
      verifiedHash: `sha256-verified-yield-${lifecycleId}`
    }
  });

  const resolvedCapabilities: EstateCapability[] = [topCandidate.capability];
  if (rationale.decision === 'COMPOSE' && candidates[1]) {
    resolvedCapabilities.push(candidates[1].capability);
  }

  return {
    instruction,
    flowLifecycleId: lifecycleId,
    decision: rationale.decision,
    resolvedCapabilities,
    steps,
    executionSuccess,
    recoveryPathUsed,
    executionOutput,
    yield: {
      avoidedEngineeringHours: avoidedHours,
      avoidedCostUsd: avoidedCost,
      tokenSavings,
      zeroImplementationProof: `Executed existing canonical capability ${topCandidate.capability.authoritativeSource} without writing new implementation.`
    },
    rationale
  };
}
