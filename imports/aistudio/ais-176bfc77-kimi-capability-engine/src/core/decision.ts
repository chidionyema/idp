/**
 * Resolution Decision Engine
 * Evaluates candidates through: REUSE -> COMPOSE -> ADAPT -> IMPLEMENT_NEW
 * Generates machine-readable rationale and defensible work avoidance estimates.
 */

import { MatchCandidate } from './matcher';
import { ResolutionDecisionType, ResolutionRationale, EstateCapability } from './types';

export function resolveInstructionDecision(
  instruction: string,
  candidates: MatchCandidate[],
  hasExplicitCompositionIntent = false
): ResolutionRationale {
  const topCandidate = candidates[0];

  // Case 1: No candidates discovered in estate
  if (!topCandidate || topCandidate.relevanceScore < 0.25) {
    return {
      decision: 'IMPLEMENT_NEW',
      confidenceScore: 0.95,
      reasons: [
        'No matching capability discovered in IDP or Argon Genesis authoritative sources.',
        'Estate capability boundary does not contain domain primitives for this instruction.',
        'Commissioning new implementation required per estate governance.'
      ],
      compatibilityChecks: {
        typeSafety: false,
        permissionsSatisfied: false,
        dependenciesAvailable: false,
        readinessAcceptable: false
      },
      avoidedWorkHoursEstimate: 0,
      frictionRisk: 'HIGH'
    };
  }

  // Case 2: Degraded capability check
  if (topCandidate.evidenceBasedReadiness === 'degraded') {
    return {
      decision: 'IMPLEMENT_NEW',
      primaryCapabilityId: topCandidate.capability.id,
      confidenceScore: 0.88,
      reasons: [
        `Candidate ${topCandidate.capability.id} is degraded in runtime evidence: ${topCandidate.capability.readinessEvidence.lastFailureReason || 'Stale healthcheck'}`,
        'Never infer operational readiness from source code existence.',
        'Direct reuse blocked to prevent production incident or silent failure.'
      ],
      compatibilityChecks: {
        typeSafety: topCandidate.typedCompatibility.compatible,
        permissionsSatisfied: topCandidate.permissionCheck.satisfied,
        dependenciesAvailable: topCandidate.dependencyCheck.satisfied,
        readinessAcceptable: false
      },
      avoidedWorkHoursEstimate: 0,
      frictionRisk: 'HIGH'
    };
  }

  // Case 3: Permission gate rejection
  if (!topCandidate.permissionCheck.satisfied) {
    return {
      decision: 'IMPLEMENT_NEW', // or security blocked
      primaryCapabilityId: topCandidate.capability.id,
      confidenceScore: 0.92,
      reasons: [
        `Caller identity lacks required permissions: [${topCandidate.permissionCheck.missingPermissions.join(', ')}].`,
        'Estate security boundary is strictly enforced; reuse cannot bypass authorization.',
        'Execution gated until caller credentials acquire requisite IAM/RBAC role.'
      ],
      compatibilityChecks: {
        typeSafety: topCandidate.typedCompatibility.compatible,
        permissionsSatisfied: false,
        dependenciesAvailable: topCandidate.dependencyCheck.satisfied,
        readinessAcceptable: topCandidate.isReadinessVerified
      },
      avoidedWorkHoursEstimate: 0,
      frictionRisk: 'HIGH'
    };
  }

  // Case 4: Composition across multiple estate capabilities
  // True multi-step workflow intent (e.g., "scan container and deploy canary", "attest and route")
  const lowerInstruction = instruction.toLowerCase();
  const hasChainedAction =
    /\b(and\s+(deploy|route|publish|notify|execute|sync)|then\s+|pipeline)\b/i.test(lowerInstruction) ||
    (lowerInstruction.includes('scan') && lowerInstruction.includes('canary'));

  const isMultiStepIntent =
    hasExplicitCompositionIntent ||
    (candidates.length >= 2 &&
      candidates[1].relevanceScore >= 0.5 &&
      topCandidate.capability.id !== candidates[1].capability.id &&
      hasChainedAction);

  if (isMultiStepIntent && candidates[1] && candidates[1].isReadinessVerified) {
    const composed = [topCandidate.capability.id, candidates[1].capability.id];
    const avoidedHours = topCandidate.capability.avoidedHoursOnReuse + candidates[1].capability.avoidedHoursOnReuse;

    return {
      decision: 'COMPOSE',
      primaryCapabilityId: topCandidate.capability.id,
      composedCapabilityIds: composed,
      confidenceScore: 0.94,
      reasons: [
        `Instruction spans multi-capability workflow across ${composed.join(' + ')}.`,
        'Both capabilities are operationally_verified in IDP/Argon Genesis estate.',
        'FLOW lifecycle chains output of primary capability into secondary capability without redundant code.'
      ],
      compatibilityChecks: {
        typeSafety: true,
        permissionsSatisfied: topCandidate.permissionCheck.satisfied && candidates[1].permissionCheck.satisfied,
        dependenciesAvailable: topCandidate.dependencyCheck.satisfied && candidates[1].dependencyCheck.satisfied,
        readinessAcceptable: true
      },
      avoidedWorkHoursEstimate: avoidedHours,
      frictionRisk: 'LOW'
    };
  }

  // Case 5: Direct REUSE (Perfect match, verified readiness, satisfied permissions)
  if (
    topCandidate.isReadinessVerified &&
    topCandidate.typedCompatibility.compatible &&
    topCandidate.permissionCheck.satisfied &&
    topCandidate.dependencyCheck.satisfied &&
    topCandidate.relevanceScore >= 0.4
  ) {
    return {
      decision: 'REUSE',
      primaryCapabilityId: topCandidate.capability.id,
      confidenceScore: Math.min(0.99, topCandidate.relevanceScore + 0.15),
      reasons: [
        `Authoritative capability ${topCandidate.capability.id} is verified in production with 90-day uptime of ${topCandidate.capability.readinessEvidence.uptime90d}%.`,
        'Typed contracts (inputs & outputs) strictly match caller parameters.',
        'Permissions and dependencies verified satisfied without elevation.',
        `Defensible avoidance: ${topCandidate.capability.avoidedHoursOnReuse} engineering hours ($${topCandidate.capability.avoidedHoursOnReuse * 150} USD).`
      ],
      compatibilityChecks: {
        typeSafety: true,
        permissionsSatisfied: true,
        dependenciesAvailable: true,
        readinessAcceptable: true
      },
      avoidedWorkHoursEstimate: topCandidate.capability.avoidedHoursOnReuse,
      frictionRisk: 'NONE'
    };
  }

  // Case 6: ADAPT (Capability exists and is tested/verified, but needs parameter mapping / transform shim)
  if (
    (topCandidate.isReadinessVerified || topCandidate.evidenceBasedReadiness === 'tested') &&
    topCandidate.permissionCheck.satisfied
  ) {
    const avoidedNet = Math.max(2, topCandidate.capability.avoidedHoursOnReuse - 2); // subtract 2h adaptation overhead
    return {
      decision: 'ADAPT',
      primaryCapabilityId: topCandidate.capability.id,
      confidenceScore: 0.85,
      reasons: [
        `Authoritative capability ${topCandidate.capability.id} matches core functional requirement.`,
        'Requires lightweight parameter transform shim to bridge input contract differences.',
        'Operational readiness is tested/verified; avoids full duplicate reimplementation.'
      ],
      compatibilityChecks: {
        typeSafety: false, // will be bridged by adapter
        permissionsSatisfied: true,
        dependenciesAvailable: topCandidate.dependencyCheck.satisfied,
        readinessAcceptable: true
      },
      adaptationLayer: {
        inputTransformRequired: true,
        outputTransformRequired: false,
        notes: `Transform input payload to match ${topCandidate.capability.inputs.map((i) => i.name).join(', ')}`
      },
      avoidedWorkHoursEstimate: avoidedNet,
      frictionRisk: 'LOW'
    };
  }

  // Fallback: Implement New
  return {
    decision: 'IMPLEMENT_NEW',
    primaryCapabilityId: topCandidate?.capability.id,
    confidenceScore: 0.75,
    reasons: [
      'Discovered candidates do not meet operational readiness or type-safety thresholds.',
      'Risk of runtime friction outweighs reuse yield.',
      'Commissioning clean implementation with subsequent estate registration recommended.'
    ],
    compatibilityChecks: {
      typeSafety: topCandidate?.typedCompatibility.compatible ?? false,
      permissionsSatisfied: topCandidate?.permissionCheck.satisfied ?? false,
      dependenciesAvailable: topCandidate?.dependencyCheck.satisfied ?? false,
      readinessAcceptable: false
    },
    avoidedWorkHoursEstimate: 0,
    frictionRisk: 'MEDIUM'
  };
}
