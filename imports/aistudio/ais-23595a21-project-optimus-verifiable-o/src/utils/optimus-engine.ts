/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  SurfaceDefinition,
  SurfaceType,
  InvariantRule,
  MetricPayload,
  GateVerificationOutcome,
  InvariantEvaluationResult,
  MerkleLedgerBlock,
  HistoricalAttemptComparison,
  DayZeroSecurityAlert,
  SurfaceLatencyCapConfig,
} from '../types/optimus';

export const SURFACES: SurfaceDefinition[] = [
  {
    id: 'git_commit_push',
    name: 'Git Commits & Ref Pushes',
    tagline: 'Lefthook & Branch Protection Gate',
    category: 'Source Control & AST',
    instrumentationTechnique: 'Pre-push AST parser, TypeScript compiler probe, Cyclomatic complexity profiler',
    antiCircumventionMechanism: 'Cryptographic signed ref token required before git update-ref commits to branch',
    activeNodes: 48,
    meteredCoveragePct: 100,
    hardInvariantsCount: 4,
    iconName: 'GitBranch',
  },
  {
    id: 'ci_cd_pipeline',
    name: 'CI/CD Pipelines & Runners',
    tagline: 'Hermetic Build & Provenance Gate',
    category: 'Build & Release Infrastructure',
    instrumentationTechnique: 'SLSA Provenance v1.0, Cosign keyless signatures, in-toto step attestations',
    antiCircumventionMechanism: 'Runner attestation validation; rejects untrusted runners, bypassed steps, or cache poisoning',
    activeNodes: 16,
    meteredCoveragePct: 100,
    hardInvariantsCount: 3,
    iconName: 'Workflow',
  },
  {
    id: 'microservice_engine',
    name: 'Microservices & Core Engines',
    tagline: 'Runtime Telemetry & SLA Invariants',
    category: 'Compute & Runtime Services',
    instrumentationTechnique: 'OpenTelemetry auto-instrumentation, W3C Trace Context, p99 latency & memory profilers',
    antiCircumventionMechanism: 'Service mesh proxy blocks unmetered endpoints and kills instances with breached error budgets',
    activeNodes: 84,
    meteredCoveragePct: 100,
    hardInvariantsCount: 5,
    iconName: 'Cpu',
  },
  {
    id: 'infra_as_code',
    name: 'Infra as Code & Cloud YAML',
    tagline: 'Terraform & Kubernetes Drift Gate',
    category: 'Cloud Infrastructure & K8s',
    instrumentationTechnique: 'OPA Rego static evaluation, Terraform plan metric extraction, K8s admission webhook',
    antiCircumventionMechanism: 'Admission controller rejects any resource manifest lacking telemetry sidecar or OTel labels',
    activeNodes: 32,
    meteredCoveragePct: 100,
    hardInvariantsCount: 3,
    iconName: 'Layers',
  },
  {
    id: 'scheduled_job',
    name: 'Scheduled Jobs & Workers',
    tagline: 'Cron & Queue Execution SLA Gate',
    category: 'Asynchronous Tasks & Batch',
    instrumentationTechnique: 'Heartbeat ping probes, jitter metrics, deadline timer monitors, SLA latency tracking',
    antiCircumventionMechanism: 'Worker queue orchestrator rejects jobs without signed telemetry envelope and execution budget',
    activeNodes: 62,
    meteredCoveragePct: 100,
    hardInvariantsCount: 3,
    iconName: 'Clock',
  },
  {
    id: 'autonomous_agent',
    name: 'Autonomous AI Agents',
    tagline: 'LLM Token & Hallucination Bounds',
    category: 'AI & Autonomous Systems',
    instrumentationTechnique: 'Token velocity meter, tool call verifier, prompt drift auditor, hallucination guardrails',
    antiCircumventionMechanism: 'Agent runtime sandbox freezes execution if tool invocation lacks signed pre-flight attestation',
    activeNodes: 12,
    meteredCoveragePct: 100,
    hardInvariantsCount: 4,
    iconName: 'Bot',
  },
  {
    id: 'network_ingress_egress',
    name: 'Network, HTTPS & Mesh Egress',
    tagline: 'mTLS & Zero-Trust Egress Gate',
    category: 'Networking & Gateways',
    instrumentationTechnique: 'eBPF socket meter, Envoy access logs, DNS query logger, TLS 1.3 cert metrics',
    antiCircumventionMechanism: 'Kernel-level eBPF drops all packets from unmetered binaries or unknown egress destinations',
    activeNodes: 110,
    meteredCoveragePct: 100,
    hardInvariantsCount: 3,
    iconName: 'Network',
  },
  {
    id: 'runnable_script',
    name: 'Ad-Hoc Scripts & CLI Tools',
    tagline: 'Shell & Devcontainer Sandbox',
    category: 'Developer Tooling & Scripts',
    instrumentationTechnique: 'Wrapper shims, environment tracer, process memory & I/O monitor, execution audit log',
    antiCircumventionMechanism: 'Devcontainer shell refuses to run unstamped scripts or scripts missing metrics header',
    activeNodes: 29,
    meteredCoveragePct: 100,
    hardInvariantsCount: 3,
    iconName: 'Terminal',
  },
];

export const DEFAULT_INVARIANT_RULES: InvariantRule[] = [
  {
    id: 'INV-COV',
    name: 'Strict Code Coverage Threshold',
    metricKey: 'coverage_percent',
    operator: '>=',
    threshold: 92.5,
    unit: '%',
    description: 'Every commit and CI run must meet or exceed 92.5% unit & integration test coverage.',
    applicableSurfaces: ['git_commit_push', 'ci_cd_pipeline'],
    isHardGate: true,
  },
  {
    id: 'INV-CYC',
    name: 'Maximum Cyclomatic Complexity',
    metricKey: 'cyclomatic_complexity_max',
    operator: '<=',
    threshold: 12,
    unit: 'score',
    description: 'No function or AST node may exceed cyclomatic complexity score of 12.',
    applicableSurfaces: ['git_commit_push', 'ci_cd_pipeline', 'runnable_script'],
    isHardGate: true,
  },
  {
    id: 'INV-LAT',
    name: 'P99 Latency SLA Bound',
    metricKey: 'p99_latency_ms',
    operator: '<=',
    threshold: 120,
    unit: 'ms',
    description: 'Service response time under load benchmark must remain at or below 120ms.',
    applicableSurfaces: ['microservice_engine', 'network_ingress_egress'],
    isHardGate: true,
  },
  {
    id: 'INV-ERR',
    name: 'Error Budget Consumption Limit',
    metricKey: 'error_budget_burn_rate',
    operator: '<=',
    threshold: 0.05,
    unit: '%',
    description: 'Error rate must remain strictly below 0.05% of all estate transactions.',
    applicableSurfaces: ['microservice_engine', 'scheduled_job', 'ci_cd_pipeline'],
    isHardGate: true,
  },
  {
    id: 'INV-MEM',
    name: 'Maximum Memory Resident Footprint',
    metricKey: 'memory_resident_mb',
    operator: '<=',
    threshold: 256,
    unit: 'MB',
    description: 'Engine, microservice, or script runtime must not exceed 256MB memory cap.',
    applicableSurfaces: ['microservice_engine', 'runnable_script', 'scheduled_job'],
    isHardGate: true,
  },
  {
    id: 'INV-VULN',
    name: 'Zero Known Vulnerability Invariant',
    metricKey: 'critical_cve_count',
    operator: '==',
    threshold: 0,
    unit: 'issues',
    description: 'Zero high or critical CVEs allowed in dependency graph or base container images.',
    applicableSurfaces: ['git_commit_push', 'ci_cd_pipeline', 'infra_as_code'],
    isHardGate: true,
  },
  {
    id: 'INV-UNMET',
    name: 'Zero Unmetered Surface Invariant',
    metricKey: 'unmetered_endpoints_count',
    operator: '==',
    threshold: 0,
    unit: 'unmetered',
    description: 'All public and internal routes, jobs, or scripts must possess registered telemetry collectors.',
    applicableSurfaces: ['microservice_engine', 'network_ingress_egress', 'infra_as_code'],
    isHardGate: true,
  },
  {
    id: 'INV-TOK',
    name: 'AI Agent Token Velocity Cap',
    metricKey: 'agent_token_velocity',
    operator: '<=',
    threshold: 2500,
    unit: 'tokens/s',
    description: 'Autonomous AI agents must strictly stay under 2,500 tokens/sec to prevent runaway recursive calls.',
    applicableSurfaces: ['autonomous_agent'],
    isHardGate: true,
  },
  {
    id: 'INV-DRIFT',
    name: 'Model & Infrastructure Drift Index',
    metricKey: 'drift_index',
    operator: '<=',
    threshold: 0.02,
    unit: 'index',
    description: 'Statistical drift between deployed IaC / AI weights and approved baseline must not exceed 0.02.',
    applicableSurfaces: ['infra_as_code', 'autonomous_agent'],
    isHardGate: true,
  },
  {
    id: 'INV-SLSA',
    name: 'Minimum SLSA Provenance Level',
    metricKey: 'slsa_provenance_level',
    operator: '>=',
    threshold: 3,
    unit: 'level',
    description: 'Build artifacts must achieve SLSA Level 3 hermetic, tamper-evident verification.',
    applicableSurfaces: ['ci_cd_pipeline'],
    isHardGate: true,
  },
  {
    id: 'INV-NOBYP',
    name: 'Zero Circumvention Flags Invariant',
    metricKey: 'circumvention_flags_detected',
    operator: '==',
    threshold: 0,
    unit: 'flags',
    description: 'Absolute zero tolerance for --no-verify, --skip-metrics, [skip ci], or unmetered exemptions.',
    applicableSurfaces: [
      'git_commit_push',
      'ci_cd_pipeline',
      'microservice_engine',
      'infra_as_code',
      'scheduled_job',
      'autonomous_agent',
      'network_ingress_egress',
      'runnable_script',
    ],
    isHardGate: true,
  },
  {
    id: 'INV-SIG',
    name: 'Cryptographic Metric Signature Valid',
    metricKey: 'metric_signature_valid',
    operator: 'strict_boolean',
    threshold: true,
    unit: 'ECDSA',
    description: 'Payload must include an authentic cryptographic signature verified against estate keys.',
    applicableSurfaces: [
      'git_commit_push',
      'ci_cd_pipeline',
      'microservice_engine',
      'infra_as_code',
      'scheduled_job',
      'autonomous_agent',
      'network_ingress_egress',
      'runnable_script',
    ],
    isHardGate: true,
  },
];

/**
 * Deterministic hash generator (simulates cryptographic SHA-256 digest)
 */
export function computeDeterministicHash(input: string): string {
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  let h3 = 0x9e3779b9;
  let h4 = 0x85ebca6b;

  for (let i = 0; i < input.length; i++) {
    const ch = input.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
    h3 = Math.imul(h3 ^ ch, 2246822507);
    h4 = Math.imul(h4 ^ ch, 3266489909);
  }

  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h3 ^ (h3 >>> 13), 3266489909);
  h3 = Math.imul(h3 ^ (h3 >>> 16), 2246822507) ^ Math.imul(h4 ^ (h4 >>> 13), 3266489909);
  h4 = Math.imul(h4 ^ (h4 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);

  const hex1 = (h1 >>> 0).toString(16).padStart(8, '0');
  const hex2 = (h2 >>> 0).toString(16).padStart(8, '0');
  const hex3 = (h3 >>> 0).toString(16).padStart(8, '0');
  const hex4 = (h4 >>> 0).toString(16).padStart(8, '0');

  // Return a 64-character hex string representing a SHA-256 format
  return `${hex1}${hex2}${hex3}${hex4}${hex4}${hex3}${hex2}${hex1}`;
}

/**
 * Evaluates an individual invariant rule against actual metric values
 */
export function evaluateSingleInvariant(
  rule: InvariantRule,
  metrics: Record<string, number | string | boolean>
): InvariantEvaluationResult {
  const actualRaw = metrics[rule.metricKey];

  if (actualRaw === undefined || actualRaw === null) {
    return {
      ruleId: rule.id,
      ruleName: rule.name,
      metricKey: rule.metricKey,
      actualValue: 'MISSING_UNMETERED',
      threshold: rule.threshold,
      passed: false,
      deviation: '100% UNMETERED',
      reason: `Metric '${rule.metricKey}' was not measured or was omitted. Unmetered pushes are strictly forbidden.`,
    };
  }

  let passed = false;
  let deviation = '0%';
  let reason = '';

  if (rule.operator === '>=') {
    const numActual = Number(actualRaw);
    const numThreshold = Number(rule.threshold);
    passed = numActual >= numThreshold;
    if (!passed) {
      const diff = numThreshold - numActual;
      deviation = `-${diff.toFixed(2)}${rule.unit}`;
      reason = `Actual value (${numActual}${rule.unit}) falls below mandatory floor of ${numThreshold}${rule.unit}.`;
    } else {
      deviation = `+${(numActual - numThreshold).toFixed(2)}${rule.unit}`;
      reason = `Satisfies floor constraint (${numActual}${rule.unit} >= ${numThreshold}${rule.unit}).`;
    }
  } else if (rule.operator === '<=') {
    const numActual = Number(actualRaw);
    const numThreshold = Number(rule.threshold);
    passed = numActual <= numThreshold;
    if (!passed) {
      const diff = numActual - numThreshold;
      deviation = `+${diff.toFixed(2)}${rule.unit} EXCEEDED`;
      reason = `Actual value (${numActual}${rule.unit}) exceeds hard upper bound of ${numThreshold}${rule.unit}.`;
    } else {
      deviation = `-${(numThreshold - numActual).toFixed(2)}${rule.unit}`;
      reason = `Satisfies upper ceiling constraint (${numActual}${rule.unit} <= ${numThreshold}${rule.unit}).`;
    }
  } else if (rule.operator === '==') {
    passed = actualRaw === rule.threshold;
    if (!passed) {
      deviation = 'VIOLATED';
      reason = `Actual value (${actualRaw}) does not equal expected (${rule.threshold}).`;
    } else {
      deviation = 'EXACT_MATCH';
      reason = `Strict invariant satisfied (${actualRaw} == ${rule.threshold}).`;
    }
  } else if (rule.operator === '!=') {
    passed = actualRaw !== rule.threshold;
    if (!passed) {
      deviation = 'MATCHES_PROHIBITED';
      reason = `Actual value matched prohibited value (${rule.threshold}).`;
    } else {
      deviation = 'NOMINAL';
      reason = `Prohibited state avoided.`;
    }
  } else if (rule.operator === 'strict_boolean') {
    passed = Boolean(actualRaw) === Boolean(rule.threshold);
    if (!passed) {
      deviation = 'CRYPTOGRAPHIC_FAILURE';
      reason = `Cryptographic signature or boolean verification failed. Expected true, got ${actualRaw}.`;
    } else {
      deviation = 'VERIFIED';
      reason = `Cryptographic verification successfully validated.`;
    }
  }

  return {
    ruleId: rule.id,
    ruleName: rule.name,
    metricKey: rule.metricKey,
    actualValue: actualRaw,
    threshold: rule.threshold,
    passed,
    deviation,
    reason,
  };
}

/**
 * Gate Evaluation: Evaluates all applicable invariants and circumvention flags
 */
export function evaluateGate(
  payload: MetricPayload,
  customRules: InvariantRule[] = DEFAULT_INVARIANT_RULES
): GateVerificationOutcome {
  const timestamp = new Date().toISOString();
  const evaluationResults: InvariantEvaluationResult[] = [];
  const rejectionReasons: string[] = [];

  // 1. Check for explicit circumvention flags
  let isCircumventionAttempt = false;
  const knownBypassFlags = ['--no-verify', '--skip-metrics', '[skip ci]', '--force', 'NO_METRICS', 'DROP_TELEMETRY', 'BYPASS_OPTS'];

  const detectedFlags = payload.bypassFlagsDetected || [];
  if (detectedFlags.length > 0) {
    isCircumventionAttempt = true;
    rejectionReasons.push(
      `Circumvention flag detected: [${detectedFlags.join(', ')}]. Project Optimus enforces zero bypass tolerance.`
    );
  }

  // Check code snippet or raw inputs for sneaky bypasses
  if (payload.rawCodeSnippet) {
    for (const flag of knownBypassFlags) {
      if (payload.rawCodeSnippet.includes(flag)) {
        isCircumventionAttempt = true;
        rejectionReasons.push(`Circumvention string '${flag}' detected in payload AST or script body.`);
      }
    }
  }

  // 2. Filter applicable rules for this surface
  const applicableRules = customRules.filter((r) => r.applicableSurfaces.includes(payload.surface));

  // Merge circumvention flags count into metrics if not explicitly present
  const metricsWithFlags = {
    ...payload.metrics,
    circumvention_flags_detected: detectedFlags.length + (isCircumventionAttempt ? 1 : 0),
  };

  for (const rule of applicableRules) {
    const result = evaluateSingleInvariant(rule, metricsWithFlags);
    evaluationResults.push(result);
    if (!result.passed) {
      rejectionReasons.push(`[${rule.id}] ${result.ruleName}: ${result.reason}`);
    }
  }

  const allowed = rejectionReasons.length === 0;
  const status = allowed ? 'RATIFIED_AND_SIGNED' : 'REJECTED_BLOCKED';

  // 3. Compute Merkle Leaf & Block Hash
  const hashPayload = JSON.stringify({
    surface: payload.surface,
    entityId: payload.entityId,
    actor: payload.actor,
    metrics: metricsWithFlags,
    status,
    timestamp,
  });

  const computedHash = computeDeterministicHash(hashPayload);
  const merkleLeaf = computeDeterministicHash(`LEAF:${computedHash}`);

  let cryptographicSignature: string | undefined;
  let signedPushToken: string | undefined;

  if (allowed) {
    cryptographicSignature = `ECDSA-P256-SHA256:${computeDeterministicHash(`SIG:${computedHash}:SEC_KEY_OPTIMUS_ROOT`)}`;
    signedPushToken = `opt_token_v3_${computedHash.substring(0, 16)}_${Date.now().toString(36)}`;
  }

  return {
    allowed,
    status,
    rejectionReasons,
    evaluationResults,
    computedHash,
    merkleLeaf,
    cryptographicSignature,
    signedPushToken,
    timestamp,
    surface: payload.surface,
    entityId: payload.entityId,
    actor: payload.actor,
    isCircumventionAttempt,
  };
}

/**
 * Merkle Tree Root Computation
 */
export function calculateMerkleRoot(leaves: string[]): string {
  if (leaves.length === 0) {
    return computeDeterministicHash('EMPTY_TREE');
  }
  let currentLevel = [...leaves];

  while (currentLevel.length > 1) {
    const nextLevel: string[] = [];
    for (let i = 0; i < currentLevel.length; i += 2) {
      const left = currentLevel[i];
      const right = i + 1 < currentLevel.length ? currentLevel[i + 1] : left;
      const combined = computeDeterministicHash(`${left}:${right}`);
      nextLevel.push(combined);
    }
    currentLevel = nextLevel;
  }

  return currentLevel[0];
}

/**
 * Merkle Ledger Integrity Verifier
 * Verifies that the chain of blocks has not been tampered with or modified.
 */
export function verifyMerkleChainIntegrity(ledger: MerkleLedgerBlock[]): {
  isValid: boolean;
  brokenIndex?: number;
  reason?: string;
} {
  if (ledger.length === 0) return { isValid: true };

  for (let i = 0; i < ledger.length; i++) {
    const current = ledger[i];

    // Verify link to previous block
    if (i > 0) {
      const prev = ledger[i - 1];
      if (current.previousHash !== prev.blockHash) {
        return {
          isValid: false,
          brokenIndex: i,
          reason: `Block #${current.index} previousHash (${current.previousHash.substring(0, 12)}) does not match Block #${prev.index} hash (${prev.blockHash.substring(0, 12)}). Ledger has been tampered with!`,
        };
      }
    }

    // Verify internal hash consistency
    if (current.blockHash.length !== 64) {
      return {
        isValid: false,
        brokenIndex: i,
        reason: `Block #${current.index} has an invalid or corrupted cryptographic hash length.`,
      };
    }
  }

  return { isValid: true };
}

/**
 * Historical Comparison Data (Addressing Founder's Note on AEI in IDP & Historical Attempts)
 */
export const HISTORICAL_ATTEMPTS: HistoricalAttemptComparison[] = [
  {
    generation: 'Gen 1 (2018-2020)',
    name: 'Client-Side Git Hooks (Husky / Shell)',
    description: 'Local bash scripts running linter and unit tests on developer laptop before commit.',
    vulnerabilityToBypass: 'Trivially bypassed via `git commit --no-verify` or `git push --no-verify`. Completely non-enforceable.',
    mathematicalProof: 'None. Trust is placed in developer machine environment variables and local shell hooks.',
    estateBreadth: 'Git commits only. Zero visibility into CI runners, cloud infra, cron jobs, or runtime services.',
    whyFailedOrSuperseded: 'Developers bypass local hooks when rushed; git provides no native cryptographic hook enforcement.',
    status: 'OBSOLETE',
  },
  {
    generation: 'Gen 2 (2020-2022)',
    name: 'Passive APM & Observability (Datadog / NewRelic)',
    description: 'Post-facto monitoring agents scraping logs, metrics, and traces after deployment.',
    vulnerabilityToBypass: 'Passive observation only. Cannot block code from being pushed or deployed. Silent drift occurs constantly.',
    mathematicalProof: 'Probabilistic statistical sampling (1-10% trace sampling). No hard cryptographic verification.',
    estateBreadth: 'Production services only. Ignores Git refs, IaC drift, ad-hoc developer scripts, and AI agents.',
    whyFailedOrSuperseded: 'Observability without gating creates alert fatigue. Engineers discover breaking regressions after customers fail.',
    status: 'OBSOLETE',
  },
  {
    generation: 'Gen 3 (2022-2024)',
    name: 'IDP Scorecards (Backstage / Cortex / Port)',
    description: 'Internal Developer Portals collecting asynchronous metadata and grading services with Bronze/Silver/Gold badges.',
    vulnerabilityToBypass: 'Scorecards are advisory dashboards. Developers easily push code, merge PRs, and deploy despite red scores.',
    mathematicalProof: 'None. Polled via GitHub APIs on delay (every 1-6 hours). Decoupled from the atomic push event.',
    estateBreadth: 'Repositories registered in software catalog. Excludes ad-hoc scripts, ephemeral containers, and egress network calls.',
    whyFailedOrSuperseded: 'Advisory scorecards do not block operations. Teams ignore warnings to meet feature ship deadlines.',
    status: 'VULNERABLE',
  },
  {
    generation: 'Gen 4 (2024-2025)',
    name: 'AEI in IDP (Automated Enforcement & Instrumentation)',
    description: 'The attempt to turn IDP scorecards into deployment gates via webhook blockers and CI plugins.',
    vulnerabilityToBypass: 'Direct branch pushes, untracked scripts, out-of-band IaC merges, and local test bypassing still leaked through.',
    mathematicalProof: 'Weak webhook handshakes without cryptographic commit-to-metric attestation.',
    estateBreadth: 'Limited to services that adopted the IDP SDK. Failed to cover AI agents, cron jobs, and kernel network egress.',
    whyFailedOrSuperseded: 'Lacked unified estate topology. Webhook gates could be bypassed by updating branch protection or direct cloud API calls.',
    status: 'VULNERABLE',
  },
  {
    generation: 'Gen 5 (Project Optimus)',
    name: 'Project Optimus: Verifiable Operational Integrity Standard',
    description: 'Estate-wide mathematical invariant enforcement with cryptographic signed push tokens, SLSA Level 3, and Merkle ledger.',
    vulnerabilityToBypass: 'Mathematically zero bypass tolerance. Server-side git update-ref rejects unsigned commits; eBPF drops unmetered packets.',
    mathematicalProof: 'Deterministic ECDSA P-256 signed in-toto attestations, cryptographic Merkle tree audit log, OPA Rego invariants.',
    estateBreadth: '100% of all 8 surfaces: Git pushes, CI/CD, microservices, infra YAML, cron jobs, AI agents, network mesh, and scripts.',
    whyFailedOrSuperseded: 'Current active standard. Unifies all execution surfaces under immutable mathematical proof.',
    status: 'OPTIMUS_ACTIVE',
  },
];

import {
  TelemetryTimeSeriesPoint,
  DetectedAnomaly,
  UltraOptimizationPrescription,
  LatencyHeatmapCell,
} from '../types/optimus';

/**
 * Generates continuous time-series telemetry data combining ledger history and estate background traffic
 */
export function generateTimeSeriesTelemetry(ledger: MerkleLedgerBlock[] = []): TelemetryTimeSeriesPoint[] {
  const points: TelemetryTimeSeriesPoint[] = [];
  const baseTimestamp = new Date('2026-11-05T12:00:00Z').getTime();

  // 16 chronological checkpoints across 24h
  for (let i = 0; i < 16; i++) {
    const timeMs = baseTimestamp + i * 90 * 60 * 1000;
    const date = new Date(timeMs);
    const label = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });

    // Baseline nominal throughput
    let ratified = 14 + (i % 5) * 6 + Math.floor(Math.sin(i) * 4);
    let circumventions = (i === 4 || i === 9 || i === 13) ? (i === 9 ? 3 : 2) : (i % 3 === 0 ? 1 : 0);
    let p99 = 42 + Math.floor(Math.sin(i * 1.5) * 12) + (circumventions > 0 ? 18 : 0);
    let p50 = 14 + Math.floor(Math.sin(i * 1.2) * 4);
    let tokenVelocity = 1200 + Math.floor(Math.cos(i) * 300);
    let drift = 0.005 + (i === 9 ? 0.038 : 0.003);

    // If an anomaly interval
    if (i === 9) {
      p99 = 108; // spike near 120ms invariant ceiling
      tokenVelocity = 3800; // rogue agent burst
    }

    points.push({
      timestamp: date.toISOString(),
      label,
      ratified,
      circumventions,
      p99LatencyMs: p99,
      p50LatencyMs: p50,
      tokenVelocityAvg: tokenVelocity,
      driftIndexAvg: Number(drift.toFixed(3)),
      anomalyFlagCount: circumventions > 1 || p99 > 85 ? 1 : 0,
    });
  }

  return points;
}

/**
 * Intelligent Anomaly Detection Engine
 * Scans time series and recent ledger blocks for operational anomalies and bottlenecks
 */
export function detectEstateAnomalies(
  points: TelemetryTimeSeriesPoint[],
  ledger: MerkleLedgerBlock[]
): DetectedAnomaly[] {
  const anomalies: DetectedAnomaly[] = [];

  // 1. Scan for circumvention clustering
  const totalBypasses = points.reduce((acc, p) => acc + p.circumventions, 0);
  if (totalBypasses >= 3) {
    anomalies.push({
      id: 'ANOM-BYPASS-CLUSTER',
      surface: 'git_commit_push',
      severity: 'CRITICAL',
      title: 'Adversarial Circumvention Cluster Intercepted',
      description: `${totalBypasses} bypass attempts (--no-verify / [skip ci]) intercepted across the last 24h window. Zero slipped through.`,
      detectedAt: '2026-11-06T04:25:02Z',
      metricObserved: `${totalBypasses} bypass flags`,
      threshold: '0 tolerance (INV-NOBYP)',
      rootCauseAnalysis: 'Developers attempted to push under deadline without executing local AST profilers; blocked at server-side ref lock.',
      mathematicalRemediation: 'Server-side pre-receive gate automatically quarantined comitter keys and issued signed ref rejection tickets.',
    });
  }

  // 2. Scan for tail latency cliff
  const maxP99 = Math.max(...points.map((p) => p.p99LatencyMs));
  if (maxP99 >= 100) {
    anomalies.push({
      id: 'ANOM-LATENCY-CLIFF',
      surface: 'microservice_engine',
      severity: 'HIGH',
      title: 'P99 Tail Latency Cliff Approaching SLA Ceiling',
      description: `Peak P99 latency reached ${maxP99}ms (approaching hard invariant bound of 120ms).`,
      detectedAt: '2026-11-06T04:38:22Z',
      metricObserved: `${maxP99}ms P99`,
      threshold: '120ms (INV-LAT)',
      rootCauseAnalysis: 'Synchronous OpenTelemetry span serialization during multi-tier distributed trace fan-out.',
      mathematicalRemediation: 'Deploy zero-copy ring-buffer exporter; switch to eBPF sockops kernel bypass to eliminate 18.4ms socket transit.',
    });
  }

  // 3. Scan for AI agent token velocity runaway
  const maxTokenVelocity = Math.max(...points.map((p) => p.tokenVelocityAvg));
  if (maxTokenVelocity > 2500) {
    anomalies.push({
      id: 'ANOM-AGENT-TOKEN-STORM',
      surface: 'autonomous_agent',
      severity: 'CRITICAL',
      title: 'Autonomous Agent Recursive Tool Execution Storm',
      description: `Agent token velocity spiked to ${maxTokenVelocity} tokens/sec, exceeding hard threshold of 2,500 tokens/sec.`,
      detectedAt: '2026-11-06T04:46:15Z',
      metricObserved: `${maxTokenVelocity} t/s`,
      threshold: '2500 t/s (INV-TOK)',
      rootCauseAnalysis: 'Market synthesis agent entered unconstrained recursive sub-agent instantiation loop.',
      mathematicalRemediation: 'Optimus Agent Guard activated execution circuit breaker; frozen context snapshot isolated in quarantine sandbox.',
    });
  }

  // 4. Scan for unmetered cloud IaC egress
  const unmeteredBlock = ledger.find((b) => b.metricsSnapshot.unmetered_endpoints_count && Number(b.metricsSnapshot.unmetered_endpoints_count) > 0);
  if (unmeteredBlock) {
    anomalies.push({
      id: 'ANOM-IAC-UNMETERED',
      surface: 'infra_as_code',
      severity: 'HIGH',
      title: 'Unmetered Public Cloud Route Detected in Terraform Plan',
      description: 'Terraform plan attempted to create 3 public egress routes with zero registered OpenTelemetry exporters.',
      detectedAt: unmeteredBlock.timestamp,
      metricObserved: '3 unmetered routes',
      threshold: '0 unmetered (INV-UNMET)',
      rootCauseAnalysis: 'Cloud engineering team deployed VPC NAT gateway without required telemetry sidecar annotation.',
      mathematicalRemediation: 'OPA Gatekeeper admission webhook rejected pull request #318; manifest blocked from applying to Terraform state.',
    });
  }

  return anomalies;
}

/**
 * Estate-Wide Ultra-Optimization Prescriptions for Extreme Low Latency
 */
export const ULTRA_OPTIMIZATION_PRESCRIPTIONS: UltraOptimizationPrescription[] = [
  {
    id: 'OPT-EBPF-SOCKOPS',
    domain: 'KERNEL_EBPF',
    title: 'Kernel eBPF Sockops Fast-Path Bypass',
    currentLatencyCost: '22.8ms per service hop',
    projectedLatencySavings: '-18.4ms (80.7% reduction)',
    impactDescription: 'Bypasses Linux TCP/IP network stack for local pod-to-Envoy communications using eBPF sock_map redirection.',
    cliCommandOrConfig: 'bpftool prog load /opt/optimus/bpf/sockops_redir.o /sys/fs/bpf/optimus_sockops type sockops',
  },
  {
    id: 'OPT-OTEL-RINGBUFFER',
    domain: 'OTEL_RINGBUFFER',
    title: 'Lock-Free Zero-Copy RingBuffer for OTel Spans',
    currentLatencyCost: '8.2ms serialize & flush',
    projectedLatencySavings: '-6.8ms (82.9% reduction)',
    impactDescription: 'Replaces synchronous HTTP telemetry exporter with an atomic memory-mapped ring buffer in shared memory.',
    cliCommandOrConfig: 'export OTEL_EXPORTER_OTLP_PROTOCOL=shm_ringbuffer && export OPTIMUS_SHM_SEGMENT=256MB',
  },
  {
    id: 'OPT-RUST-AST-LEXER',
    domain: 'AST_PARSER',
    title: 'Native Rust AST Lexer & Cyclomatic Probe',
    currentLatencyCost: '1,420ms pre-push lint',
    projectedLatencySavings: '-1,382ms (to 38ms instant)',
    impactDescription: 'Replaces slow node.js/typescript CLI AST evaluation with a compiled native SIMD tree-sitter scanner.',
    cliCommandOrConfig: 'cargo install optimus-ast-fastprobe --locked && git config hooks.ast_bin optimus-ast-fastprobe',
  },
  {
    id: 'OPT-TOKEN-CACHE-BLOOM',
    domain: 'TOKEN_CACHE',
    title: 'Sub-Millisecond ECDSA Signed Token Bloom Filter',
    currentLatencyCost: '4.5ms remote token RPC',
    projectedLatencySavings: '-4.45ms (< 50 microseconds)',
    impactDescription: 'Verifies ratified push tokens in local CPU cache via cryptographic Bloom filter and memory-mapped key ring.',
    cliCommandOrConfig: 'optimus-agent-ctl --enable-bloom-cache --cache-size=64MB --max-staleness=30s',
  },
  {
    id: 'OPT-MTLS-0RTT',
    domain: 'NETWORK_MESH',
    title: 'TLS 1.3 0-RTT Session Resumption for Service Mesh',
    currentLatencyCost: '16.4ms handshake latency',
    projectedLatencySavings: '-12.5ms (76.2% reduction)',
    impactDescription: 'Pre-shares authenticated session tickets between microservices, eliminating 1 network roundtrip on every call.',
    cliCommandOrConfig: 'meshctl config set --tls-version=1.3 --enable-0rtt-resumption --anti-replay-window=10s',
  },
];

/**
 * Generates Latency Heatmap matrix across all 8 monitored surfaces and chronological time slices
 */
export function generateLatencyHeatmapData(): LatencyHeatmapCell[] {
  const cells: LatencyHeatmapCell[] = [];
  const timeSlices = [
    '12:00', '13:30', '15:00', '16:30', '18:00', '19:30',
    '21:00', '22:30', '00:00', '01:30', '03:00', '04:30'
  ];

  const surfaceProfiles: Array<{
    id: SurfaceType;
    name: string;
    baseP50: number;
    baseP95: number;
    baseP99: number;
    spikeIntervals: number[];
    spikeFactor: number;
    bottleneckCause?: string;
    prescribedOpt?: string;
  }> = [
    {
      id: 'git_commit_push',
      name: 'Git Commits & Ref Pushes',
      baseP50: 12,
      baseP95: 28,
      baseP99: 38,
      spikeIntervals: [5], // 19:30 peak PR burst
      spikeFactor: 2.1,
      bottleneckCause: 'Synchronous TypeScript compiler AST traversal on multi-file commits.',
      prescribedOpt: 'Switch to Native Rust Tree-Sitter AST probe (-35ms savings).',
    },
    {
      id: 'ci_cd_pipeline',
      name: 'CI/CD Pipelines & Runners',
      baseP50: 32,
      baseP95: 64,
      baseP99: 78,
      spikeIntervals: [5, 6],
      spikeFactor: 1.45,
      bottleneckCause: 'Container layer caching miss and serial Cosign keyless signatures.',
      prescribedOpt: 'Parallelize in-toto step attestations with RAM disk cache.',
    },
    {
      id: 'microservice_engine',
      name: 'Microservices & Core Engines',
      baseP50: 18,
      baseP95: 52,
      baseP99: 68,
      spikeIntervals: [5, 7, 9], // CLUSTER of high latency
      spikeFactor: 1.62,
      bottleneckCause: 'W3C trace context serialization and synchronous HTTP span exporter.',
      prescribedOpt: 'Deploy LMAX zero-copy lock-free ring-buffer for OTel spans (-6.8ms savings).',
    },
    {
      id: 'infra_as_code',
      name: 'Infra as Code & Cloud YAML',
      baseP50: 8,
      baseP95: 19,
      baseP99: 26,
      spikeIntervals: [4],
      spikeFactor: 2.4,
      bottleneckCause: 'Terraform plan provider schema validation and remote state lock contention.',
      prescribedOpt: 'Pre-compile OPA Rego policies into WebAssembly binaries.',
    },
    {
      id: 'scheduled_job',
      name: 'Scheduled Jobs & Workers',
      baseP50: 14,
      baseP95: 36,
      baseP99: 48,
      spikeIntervals: [8],
      spikeFactor: 1.5,
      bottleneckCause: 'Queue worker mutex locking during batch DB partition vacuum.',
      prescribedOpt: 'Non-blocking heartbeat ring buffer with microsecond jitter cap.',
    },
    {
      id: 'autonomous_agent',
      name: 'Autonomous AI Agents',
      baseP50: 45,
      baseP95: 98,
      baseP99: 114,
      spikeIntervals: [9, 10, 11], // CRITICAL CLUSTER >= 100ms
      spikeFactor: 1.28,
      bottleneckCause: 'Recursive sub-agent context nesting and token serialization storm.',
      prescribedOpt: 'Optimus Agent Guard execution throttle and context window freezing.',
    },
    {
      id: 'network_ingress_egress',
      name: 'Network, HTTPS & Mesh Egress',
      baseP50: 2,
      baseP95: 9,
      baseP99: 14,
      spikeIntervals: [3, 7],
      spikeFactor: 3.2,
      bottleneckCause: 'mTLS certificate handshake renegotiation between Envoy proxies.',
      prescribedOpt: 'Enable TLS 1.3 0-RTT session resumption and kernel eBPF sockops (-18.4ms savings).',
    },
    {
      id: 'runnable_script',
      name: 'Ad-Hoc Scripts & CLI Tools',
      baseP50: 9,
      baseP95: 22,
      baseP99: 31,
      spikeIntervals: [2],
      spikeFactor: 1.8,
      bottleneckCause: 'Devcontainer process initialization and unstamped shell wrapper overhead.',
      prescribedOpt: 'Static pre-compiled binary shims with memory-mapped metrics header.',
    },
  ];

  for (const surface of surfaceProfiles) {
    for (let t = 0; t < timeSlices.length; t++) {
      const isSpike = surface.spikeIntervals.includes(t);
      const factor = isSpike ? surface.spikeFactor : (1 + Math.sin(t + surface.baseP50) * 0.12);

      const p50 = Math.round(surface.baseP50 * factor);
      const p95 = Math.round(surface.baseP95 * factor);
      const p99 = Math.round(surface.baseP99 * factor);
      const requestCount = 120 + Math.floor(Math.cos(t) * 40) + (isSpike ? 95 : 0);

      const isBottleneck = p99 >= 75;
      const severity: 'CRITICAL' | 'WARNING' | 'NOMINAL' =
        p99 >= 100 ? 'CRITICAL' : p99 >= 75 ? 'WARNING' : 'NOMINAL';

      cells.push({
        surfaceId: surface.id,
        surfaceName: surface.name,
        timeLabel: timeSlices[t],
        timestamp: `2026-11-06T${timeSlices[t]}:00Z`,
        p50Ms: p50,
        p95Ms: p95,
        p99Ms: p99,
        requestCount,
        isBottleneckCluster: isBottleneck,
        clusterSeverity: severity,
        bottleneckRootCause: isBottleneck ? surface.bottleneckCause : undefined,
        prescribedOptimization: isBottleneck ? surface.prescribedOpt : undefined,
      });
    }
  }

  return cells;
}

export function generateDayZeroSecurityAlerts(): DayZeroSecurityAlert[] {
  return [
    {
      id: 'SEC-ALERT-001',
      surface: 'git_commit_push',
      surfaceName: 'Git Commits & Ref Pushes',
      severity: 'CRITICAL',
      title: 'Adversarial Ref Push Bypass Attempt (--no-verify Flag Injection)',
      dayZeroBaselineMetric: 'Bypass Tolerance: 0.000% (Absolute Zero)',
      realTimeObservedMetric: 'git push --no-verify on refs/heads/production',
      deviationPercent: '+100.0% Security Invariant Breach',
      threatVector: 'Developer client hook bypass attempt via raw --no-verify flag attempting to circumvent TypeScript AST invariant checks.',
      rootCause: 'Commit payload contains unmetered AST modifications and missing cryptographic push ticket.',
      mitigationEnforced: 'Git pre-receive gate terminated push session with exit code 1; issued ECDSA reject ticket; committed leaf to Merkle block #1210.',
      status: 'ACTIVE_INTERCEPTED',
      timestamp: '2026-11-06T04:25:12Z',
    },
    {
      id: 'SEC-ALERT-002',
      surface: 'autonomous_agent',
      surfaceName: 'Autonomous AI Agents',
      severity: 'CRITICAL',
      title: 'Agent Recursive Context Hijack & Token Velocity Storm',
      dayZeroBaselineMetric: 'Token Velocity: ≤ 120 tokens/sec · Drift Index: ≤ 0.05',
      realTimeObservedMetric: '482 tokens/sec (4.01x) · Drift Index: 0.88',
      deviationPercent: '+301.7% Velocity Invariant Deviation',
      threatVector: 'Autonomous sub-agent self-invoking nested execution loops without cryptographic pre-flight attestation.',
      rootCause: 'Unbounded context window recursion triggering token runaway and high API cost leakage.',
      mitigationEnforced: 'Optimus Agent Guard runtime sandbox froze execution thread; revoked API invocation credential; forced context memory reset.',
      status: 'QUARANTINED',
      timestamp: '2026-11-06T03:40:55Z',
    },
    {
      id: 'SEC-ALERT-003',
      surface: 'ci_cd_pipeline',
      surfaceName: 'CI/CD Pipelines & Runners',
      severity: 'HIGH',
      title: 'Untrusted Ephemeral Runner Missing SLSA Provenance v1.0',
      dayZeroBaselineMetric: 'Provenance: 100% Hermetic Cosign In-Toto Attestation',
      realTimeObservedMetric: '0% Provenance Header (Self-hosted non-isolated container)',
      deviationPercent: '-100.0% Attestation Completeness Breach',
      threatVector: 'Poisoned CI/CD runner container attempting to push unverified image digest to private cluster registry.',
      rootCause: 'Workload pipeline runner invoked without hardware-bound TPM key attestation or cryptographic signature.',
      mitigationEnforced: 'Estate admission controller blocked container registry push; invalidated artifact digest and quarantined runner node.',
      status: 'ACTIVE_INTERCEPTED',
      timestamp: '2026-11-06T02:15:33Z',
    },
    {
      id: 'SEC-ALERT-004',
      surface: 'network_ingress_egress',
      surfaceName: 'Network, HTTPS & Mesh Egress',
      severity: 'HIGH',
      title: 'Unauthorized Egress Socket to Unregistered External IP Destination',
      dayZeroBaselineMetric: 'Egress Policy: 100% mTLS 1.3 Service Mesh Monitored',
      realTimeObservedMetric: 'Raw TCP SYN to 198.51.100.42:9999 without Envoy proxy headers',
      deviationPercent: '+100.0% Network Policy Evasion',
      threatVector: 'Unmetered process attempting external egress connection bypassing service mesh proxy and DNS logging.',
      rootCause: 'Ad-hoc binary bypassed local host socket redirect and attempted raw socket creation.',
      mitigationEnforced: 'Kernel eBPF cgroup socket filter dropped packets at kernel layer 3 (tc egress hook); flagged process PID #4912.',
      status: 'QUARANTINED',
      timestamp: '2026-11-06T01:50:08Z',
    },
    {
      id: 'SEC-ALERT-005',
      surface: 'microservice_engine',
      surfaceName: 'Microservices & Core Engines',
      severity: 'MEDIUM',
      title: 'P99 Tail Latency Cliff Excursion (+162% vs Day 0 Baseline)',
      dayZeroBaselineMetric: 'P99 Latency: ≤ 42ms (Day 0 Baseline locked)',
      realTimeObservedMetric: 'P99 Latency: 110ms (Approaching 120ms Hard Kill-Switch)',
      deviationPercent: '+161.9% Tail Latency Drift',
      threatVector: 'Synchronous distributed tracing span fan-out serialization stall causing tail latency degradation.',
      rootCause: 'Synchronous OTel HTTP exporter blocking worker event loop under load.',
      mitigationEnforced: 'Dynamic load shedding engaged; switched OTel exporter to non-blocking zero-copy ring-buffer.',
      status: 'RESOLVED',
      timestamp: '2026-11-06T00:30:19Z',
    },
    {
      id: 'SEC-ALERT-006',
      surface: 'infra_as_code',
      surfaceName: 'Infra as Code & Cloud YAML',
      severity: 'MEDIUM',
      title: 'OPA Rego Policy Drift: Unmetered K8s DaemonSet Ingress Manifest',
      dayZeroBaselineMetric: 'Policy Compliance: 100% Rego Strict Invariant Pass',
      realTimeObservedMetric: "Manifest spec.template lacks 'optimus.telemetry/metered=true' label",
      deviationPercent: 'Missing 2 Mandatory Security Invariant Labels',
      threatVector: 'Infrastructure engineer attempting to deploy unmetered sidecar container without estate supervision.',
      rootCause: 'PR merged with outdated Helm chart template that omitted OPA telemetry annotations.',
      mitigationEnforced: 'K8s Validating Admission Webhook rejected deployment manifest with HTTP 403 Forbidden.',
      status: 'ACTIVE_INTERCEPTED',
      timestamp: '2026-11-05T22:12:44Z',
    },
    {
      id: 'SEC-ALERT-007',
      surface: 'scheduled_job',
      surfaceName: 'Scheduled Jobs & Workers',
      severity: 'LOW',
      title: 'Cron Worker Execution Jitter Excursion (+18ms Drift)',
      dayZeroBaselineMetric: 'Jitter Bound: ≤ 10ms deadline skew',
      realTimeObservedMetric: '28ms jitter variance on batch DB partition vacuum worker',
      deviationPercent: '+180.0% Timing Jitter Excursion',
      threatVector: 'Database lock contention causing minor worker synchronization delay.',
      rootCause: 'Concurrent lock contention during vacuum analyze on historical ledger analytics table.',
      mitigationEnforced: 'Telemetry queue re-adjusted priority slot; scheduled non-blocking worker retry with randomized exponential backoff.',
      status: 'RESOLVED',
      timestamp: '2026-11-05T19:45:00Z',
    },
    {
      id: 'SEC-ALERT-008',
      surface: 'runnable_script',
      surfaceName: 'Ad-Hoc Scripts & CLI Tools',
      severity: 'LOW',
      title: 'Ad-Hoc Shell Script Invoked Without Timestamped Metrics Header',
      dayZeroBaselineMetric: 'Script Execution: 100% Wrapped via Optimus Dev Shim',
      realTimeObservedMetric: 'Raw bash script executed directly from /tmp directory without wrapper',
      deviationPercent: 'Missing Pre-Flight Execution Hash Stamp',
      threatVector: 'Developer running diagnostic script outside container sandbox.',
      rootCause: 'Local diagnostic command unhooked from standard zsh telemetry wrapper.',
      mitigationEnforced: 'Shell shim intercepted execve syscall; auto-injected metrics header and logged run hash into audit log.',
      status: 'RESOLVED',
      timestamp: '2026-11-05T16:20:10Z',
    },
  ];
}

export const DEFAULT_SURFACE_LATENCY_CAPS: Record<SurfaceType, SurfaceLatencyCapConfig> = {
  git_commit_push: {
    surfaceId: 'git_commit_push',
    surfaceName: 'Git Commits & Ref Pushes',
    category: 'Source Control & AST',
    baselineLatencyMs: 12,
    maxLatencyCapMs: 40,
    enforcementMode: 'HARD_KILL_SWITCH',
    activeViolationsCount: 1,
    lastBreachedTimestamp: '2026-11-06T04:25:12Z',
    autoRemediationAction: 'Reject git push ref; require pre-compiled native Rust Tree-Sitter AST parser probe.',
    threatDescription: 'Slow AST traversal blocks developer commit loop and introduces unmetered branch drift.',
  },
  ci_cd_pipeline: {
    surfaceId: 'ci_cd_pipeline',
    surfaceName: 'CI/CD Pipelines & Runners',
    category: 'Build & Release Infrastructure',
    baselineLatencyMs: 32,
    maxLatencyCapMs: 75,
    enforcementMode: 'HARD_KILL_SWITCH',
    activeViolationsCount: 2,
    lastBreachedTimestamp: '2026-11-06T02:15:33Z',
    autoRemediationAction: 'Halt pipeline runner container; invalidate unverified artifact digest and quarantine node.',
    threatDescription: 'Container build stalls indicate cache poisoning attempts or unmetered step injection.',
  },
  microservice_engine: {
    surfaceId: 'microservice_engine',
    surfaceName: 'Microservices & Core Engines',
    category: 'Compute & Runtime Services',
    baselineLatencyMs: 18,
    maxLatencyCapMs: 60,
    enforcementMode: 'HARD_KILL_SWITCH',
    activeViolationsCount: 3,
    lastBreachedTimestamp: '2026-11-06T00:30:19Z',
    autoRemediationAction: 'Service mesh proxy shifts traffic; drops synchronous exporter to lock-free ring-buffer.',
    threatDescription: 'Distributed trace serialization bottlenecks cause cascaded HTTP connection exhaustion.',
  },
  infra_as_code: {
    surfaceId: 'infra_as_code',
    surfaceName: 'Infra as Code & Cloud YAML',
    category: 'Cloud Infrastructure & K8s',
    baselineLatencyMs: 8,
    maxLatencyCapMs: 30,
    enforcementMode: 'AUTO_QUARANTINE',
    activeViolationsCount: 1,
    lastBreachedTimestamp: '2026-11-05T22:12:44Z',
    autoRemediationAction: 'K8s admission webhook blocks manifest apply; flags uncompiled Rego policy.',
    threatDescription: 'Uncompiled OPA policies cause API server webhook timeouts and admission bypasses.',
  },
  scheduled_job: {
    surfaceId: 'scheduled_job',
    surfaceName: 'Scheduled Jobs & Workers',
    category: 'Asynchronous Tasks & Batch',
    baselineLatencyMs: 14,
    maxLatencyCapMs: 50,
    enforcementMode: 'AUTO_QUARANTINE',
    activeViolationsCount: 0,
    lastBreachedTimestamp: undefined,
    autoRemediationAction: 'Queue orchestrator reschedules batch partition; caps concurrency slot.',
    threatDescription: 'Worker queue lock contention cascades into SLA deadline misses and orphaned tasks.',
  },
  autonomous_agent: {
    surfaceId: 'autonomous_agent',
    surfaceName: 'Autonomous AI Agents',
    category: 'AI & Autonomous Systems',
    baselineLatencyMs: 45,
    maxLatencyCapMs: 110,
    enforcementMode: 'HARD_KILL_SWITCH',
    activeViolationsCount: 3,
    lastBreachedTimestamp: '2026-11-06T03:40:55Z',
    autoRemediationAction: 'Optimus Agent Guard runtime freezes thread; revokes execution token quota.',
    threatDescription: 'Recursive sub-agent context nesting creates runaway API cost storms and prompt injection loops.',
  },
  network_ingress_egress: {
    surfaceId: 'network_ingress_egress',
    surfaceName: 'Network, HTTPS & Mesh Egress',
    category: 'Networking & Gateways',
    baselineLatencyMs: 2,
    maxLatencyCapMs: 15,
    enforcementMode: 'HARD_KILL_SWITCH',
    activeViolationsCount: 1,
    lastBreachedTimestamp: '2026-11-06T01:50:08Z',
    autoRemediationAction: 'Kernel eBPF sockops terminates raw socket; forces TLS 1.3 0-RTT session resumption.',
    threatDescription: 'mTLS handshake latency spikes facilitate timing attacks and unmetered egress socket leaks.',
  },
  runnable_script: {
    surfaceId: 'runnable_script',
    surfaceName: 'Ad-Hoc Scripts & CLI Tools',
    category: 'Developer Tooling & Scripts',
    baselineLatencyMs: 9,
    maxLatencyCapMs: 35,
    enforcementMode: 'AUTO_QUARANTINE',
    activeViolationsCount: 0,
    lastBreachedTimestamp: undefined,
    autoRemediationAction: 'Pre-compiled devcontainer shim injects memory-mapped header before execve.',
    threatDescription: 'Unstamped shell scripts run outside kernel metrics isolation, evading estate audits.',
  },
};

/**
 * Synchronizes per-surface latency caps into global invariant rules list.
 * Replaces or inserts rule `INV-LAT-${surfaceId}` for each surface type.
 */
export function syncLatencyCapsToRules(
  currentRules: InvariantRule[],
  caps: Record<SurfaceType, SurfaceLatencyCapConfig>
): InvariantRule[] {
  // Retain non-per-surface latency rules
  const baseRules = currentRules.filter((r) => !r.id.startsWith('INV-LAT-SURF-'));

  const generatedLatencyRules: InvariantRule[] = Object.values(caps).map((cap) => ({
    id: `INV-LAT-SURF-${cap.surfaceId}`,
    name: `${cap.surfaceName} Latency Cap`,
    metricKey: 'p99_latency_ms',
    operator: '<=',
    threshold: cap.maxLatencyCapMs,
    unit: 'ms',
    description: `Automated latency cap for ${cap.surfaceName}. Limit: ${cap.maxLatencyCapMs}ms (${cap.enforcementMode}).`,
    applicableSurfaces: [cap.surfaceId],
    isHardGate: cap.enforcementMode !== 'WARN_AUDIT_LOG',
  }));

  return [...baseRules, ...generatedLatencyRules];
}

/**
 * Checks if a given observed latency exceeds the configured latency cap for a surface.
 */
export function evaluateSurfaceLatencyViolation(
  surface: SurfaceType,
  observedLatencyMs: number,
  capConfig: SurfaceLatencyCapConfig
): {
  isViolation: boolean;
  deviationMs: number;
  severity: 'CRITICAL' | 'WARNING' | 'NOMINAL';
  enforcementAction: string;
} {
  const isViolation = observedLatencyMs > capConfig.maxLatencyCapMs;
  const deviationMs = observedLatencyMs - capConfig.maxLatencyCapMs;

  let severity: 'CRITICAL' | 'WARNING' | 'NOMINAL' = 'NOMINAL';
  if (isViolation) {
    severity = deviationMs >= 25 || capConfig.enforcementMode === 'HARD_KILL_SWITCH' ? 'CRITICAL' : 'WARNING';
  }

  const enforcementAction = isViolation
    ? `Automated violation triggered under ${capConfig.enforcementMode}: ${capConfig.autoRemediationAction}`
    : 'Latency within ratified SLA bounds.';

  return {
    isViolation,
    deviationMs,
    severity,
    enforcementAction,
  };
}


