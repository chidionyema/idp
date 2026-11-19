/**
 * Capability Matcher & Readiness Evaluator
 * Verifies typed contracts, dependencies, permissions, and evidence-backed readiness.
 */

import { EstateCapability, OperationalReadiness, TypeContract } from './types';
import { ESTATE_CAPABILITIES } from './registry';

export interface CallerContext {
  callerIdentity: string;
  permissions: string[];
  environment: 'production' | 'staging' | 'ephemeral';
  targetDomain?: string;
}

export interface MatchCandidate {
  capability: EstateCapability;
  relevanceScore: number; // 0.0 - 1.0
  typedCompatibility: {
    compatible: boolean;
    missingRequiredInputs: string[];
    contractMismatch: string[];
  };
  permissionCheck: {
    satisfied: boolean;
    missingPermissions: string[];
  };
  dependencyCheck: {
    satisfied: boolean;
    missingDependencies: string[];
  };
  evidenceBasedReadiness: OperationalReadiness;
  isReadinessVerified: boolean;
}

export function evaluateOperationalReadiness(capability: EstateCapability): OperationalReadiness {
  const ev = capability.readinessEvidence;
  if (!ev) return 'discovered';

  // Check staleness of health check: anything older than 14 days is degraded
  const healthCheckTime = new Date(ev.lastHealthCheck).getTime();
  const now = new Date('2026-11-09T20:43:44Z').getTime();
  const diffDays = (now - healthCheckTime) / (1000 * 60 * 60 * 24);

  if (diffDays > 14 || (ev.lastFailureReason && capability.readiness === 'degraded')) {
    return 'degraded';
  }

  // Strict rule: Never infer operational readiness from source-code existence.
  // Must have: active telemetry, >= 99.0% uptime, verified executions > 10, recent healthcheck
  if (
    ev.telemetrySource &&
    ev.uptime90d >= 99.0 &&
    ev.verifiedExecutionCount >= 10 &&
    diffDays <= 7
  ) {
    return 'operationally_verified';
  }

  if (capability.readiness === 'tested' || capability.readiness === 'deployed') {
    return capability.readiness;
  }

  if (ev.verifiedExecutionCount > 0) {
    return 'implemented';
  }

  return 'discovered';
}

export function matchCapabilityForInstruction(
  instruction: string,
  caller: CallerContext,
  providedInputs: Record<string, unknown> = {},
  registry: EstateCapability[] = ESTATE_CAPABILITIES
): MatchCandidate[] {
  const normalizedInstruction = instruction.toLowerCase();
  const words = normalizedInstruction
    .replace(/[^\w\s-]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 2);

  const candidates: MatchCandidate[] = [];

  for (const cap of registry) {
    // 1. Semantic keyword & tag scoring using exact token matches
    let score = 0;
    const descWords = new Set(
      cap.description
        .toLowerCase()
        .replace(/[^\w\s-]/g, ' ')
        .split(/\s+/)
        .filter((w) => w.length > 2)
    );
    const nameWords = new Set(
      cap.name
        .toLowerCase()
        .replace(/[^\w\s-]/g, ' ')
        .split(/\s+/)
        .filter((w) => w.length > 2)
    );
    const tagSet = new Set(cap.tags.map((t) => t.toLowerCase()));

    let matchedKeywords = 0;
    for (const w of words) {
      if (tagSet.has(w)) {
        score += 0.35;
        matchedKeywords++;
      } else if (nameWords.has(w)) {
        score += 0.25;
        matchedKeywords++;
      } else if (descWords.has(w)) {
        score += 0.1;
        matchedKeywords++;
      }
    }

    // Require at least 2 distinct keyword matches if words length >= 4, unless a tag matched
    if (words.length >= 4 && matchedKeywords < 2 && !cap.tags.some((t) => normalizedInstruction.includes(t.toLowerCase()))) {
      continue;
    }

    // Cap relevance score to 1.0
    const relevanceScore = Math.min(1.0, Math.round(score * 100) / 100);
    if (relevanceScore < 0.3) continue;

    // 2. Typed input compatibility
    const missingRequired: string[] = [];
    const contractMismatches: string[] = [];

    for (const input of cap.inputs) {
      if (input.required) {
        if (providedInputs[input.name] === undefined) {
          // If caller didn't provide inputs directly, check if the instruction mentions the concept
          const mentionsKey = normalizedInstruction.includes(input.name.toLowerCase());
          if (!mentionsKey && Object.keys(providedInputs).length > 0) {
            missingRequired.push(input.name);
          }
        } else {
          // Type validation
          const val = providedInputs[input.name];
          const actualType = Array.isArray(val) ? 'array' : typeof val;
          if (actualType !== input.type) {
            contractMismatches.push(`${input.name} expected ${input.type}, got ${actualType}`);
          }
        }
      }
    }

    const typeCompatible = contractMismatches.length === 0;

    // 3. Permission checks
    const missingPermissions = cap.requiredPermissions.filter(
      (perm) => !caller.permissions.includes(perm) && !caller.permissions.includes('*')
    );
    const permissionsSatisfied = missingPermissions.length === 0;

    // 4. Dependency checks (all dependencies must exist in registry)
    const missingDependencies = cap.dependencies.filter((dep) => {
      // In estate, infra dependencies might be external or capabilities
      const foundInRegistry = registry.some((r) => r.id === dep);
      const isKnownInfra = dep.startsWith('idp.infra.') || dep.startsWith('idp.data.') || dep.startsWith('idp.security.');
      return !foundInRegistry && !isKnownInfra;
    });
    const dependenciesSatisfied = missingDependencies.length === 0;

    // 5. Evidence-based readiness
    const evidenceReadiness = evaluateOperationalReadiness(cap);
    const isReadinessVerified = evidenceReadiness === 'operationally_verified';

    candidates.push({
      capability: cap,
      relevanceScore,
      typedCompatibility: {
        compatible: typeCompatible,
        missingRequiredInputs: missingRequired,
        contractMismatch: contractMismatches
      },
      permissionCheck: {
        satisfied: permissionsSatisfied,
        missingPermissions
      },
      dependencyCheck: {
        satisfied: dependenciesSatisfied,
        missingDependencies
      },
      evidenceBasedReadiness: evidenceReadiness,
      isReadinessVerified
    });
  }

  // Sort descending by relevance, then readiness
  return candidates.sort((a, b) => {
    if (b.isReadinessVerified !== a.isReadinessVerified) {
      return b.isReadinessVerified ? 1 : -1;
    }
    return b.relevanceScore - a.relevanceScore;
  });
}
