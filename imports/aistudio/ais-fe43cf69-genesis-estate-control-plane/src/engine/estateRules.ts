export type EvidenceClass = 'E1' | 'E2' | 'E3' | 'U';

export type FlowPhase =
  | 'ACCEPTED_DURABLE'
  | 'LEASE_FENCED'
  | 'EXECUTING_FORMATION'
  | 'FALSIFIER_AUDIT'
  | 'LANE_SUBMITTED'
  | 'GREENLANE_VERIFIED'
  | 'YIELD_CONFIRMED'
  | 'STAGNATION_DETECTED'
  | 'RECOVERING_AUTONOMOUS'
  | 'CLAIM_REJECTED'
  | 'BLOCKED_CAPABILITY';

export type FormationId =
  | 'sniper'
  | 'phalanx'
  | 'pipeline'
  | 'swarm'
  | 'centurion'
  | 'adversarial'
  | 'tournament'
  | 'sieve';

export interface SevenGateAssessment {
  contextualScoping: string;
  dimensionalThresholds: string;
  baselineDelta: string;
  architecturalTradeoffs: string;
  systemicReflexivity: string;
  deterministicVerification: string;
  provenanceAndTrust: string;
}

export interface ClaimViolation {
  code:
    | 'SILENT_AUTHORITY_PROMOTION'
    | 'FAKE_SHA_OR_FABRICATED_COMMIT'
    | 'BANNED_GIT_MUTATION'
    | 'THEATRE_WITHOUT_FALSIFIER'
    | 'INCOMPLETE_SEVEN_GATES'
    | 'PUBLIC_PRIVACY_BOUNDARY_BREACH';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  message: string;
  remediation: string;
}

export interface ClaimGateInput {
  claimedAuthority: EvidenceClass;
  claimText: string;
  proposedCommands?: string[];
  observedSha?: string | null;
  receiptHash?: string | null;
  liveHttpStatus?: number | null;
  payloadVerified?: boolean;
  integrationTestsPassed?: boolean;
  falsifierVerdict?: 'PASS' | 'FAIL' | 'PENDING';
  missingCapabilities?: string[];
  targetRepo?: string;
  isPublicCleared?: boolean;
  sourceContainsPrivateContext?: boolean;
  sevenGates?: Partial<SevenGateAssessment>;
}

export interface ClaimGateAuditResult {
  verdict: 'PASS' | 'CLAIM_REJECTED' | 'DOWNGRADED_TO_UNVERIFIED';
  effectiveAuthority: EvidenceClass;
  epistemicScore: number;
  violations: ClaimViolation[];
  remediationSteps: string[];
}

export interface FormationSpec {
  id: FormationId;
  name: string;
  posture: 'Chesed' | 'Geburah' | 'Chesed -> Geburah';
  workerCount: number;
  defaultHelmShots: number;
  maxDegreesOfFreedom: number;
  topologySummary: string;
  falsifierMechanism: string;
  idealFor: string;
}

export const LEGION_FORMATIONS: readonly FormationSpec[] = [
  {
    id: 'sniper',
    name: 'Sniper',
    posture: 'Geburah',
    workerCount: 2,
    defaultHelmShots: 2,
    maxDegreesOfFreedom: 0.15,
    topologySummary: '1 reconnaissance pass + 1 bounded surgical patch + independent diff falsifier',
    falsifierMechanism: 'AST/diff boundary check + negative regression gate',
    idealFor: 'Deterministic single-defect fixes, missing-ref crashes, and provenance workflows',
  },
  {
    id: 'phalanx',
    name: 'Phalanx',
    posture: 'Chesed -> Geburah',
    workerCount: 4,
    defaultHelmShots: 4,
    maxDegreesOfFreedom: 0.3,
    topologySummary: 'Coordinated parallel shield wall sharing a strict JSON/TypeScript boundary schema (T-1)',
    falsifierMechanism: 'Cross-module contract compatibility & schema invariant verifier',
    idealFor: 'Multi-repo synchronized transport bridges (Argon + IDP + Hermes)',
  },
  {
    id: 'pipeline',
    name: 'Pipeline',
    posture: 'Geburah',
    workerCount: 5,
    defaultHelmShots: 5,
    maxDegreesOfFreedom: 0.25,
    topologySummary: 'Sequential 5-stage assembly: Recon -> 7-Gate Spec -> Patch -> Negative Test -> Lane Submit',
    falsifierMechanism: 'Stage-exit binary contract gates before downstream handoff',
    idealFor: 'End-to-end FLOW feature delivery and Greenlane lane/* preparation',
  },
  {
    id: 'swarm',
    name: 'Swarm',
    posture: 'Chesed',
    workerCount: 6,
    defaultHelmShots: 6,
    maxDegreesOfFreedom: 0.75,
    topologySummary: 'Divergent parallel hypothesis exploration across parameter regimes with shared graph recall',
    falsifierMechanism: 'Post-expansion Geburah deduplication & empirical yield ranking',
    idealFor: 'Broad repository reconnaissance, stranded PR archaeology, and root-cause discovery',
  },
  {
    id: 'centurion',
    name: 'Supervisor / Centurion',
    posture: 'Chesed -> Geburah',
    workerCount: 4,
    defaultHelmShots: 5,
    maxDegreesOfFreedom: 0.35,
    topologySummary: 'Fenced supervisor lease delegating sub-slices to 3 isolated workers under 600s heartbeats',
    falsifierMechanism: 'Supervisor reconciliation audit + argon-sync epoch verification',
    idealFor: 'Complex multi-surface estate migrations and operational cadence orchestration',
  },
  {
    id: 'adversarial',
    name: 'Adversarial',
    posture: 'Geburah',
    workerCount: 2,
    defaultHelmShots: 3,
    maxDegreesOfFreedom: 0.2,
    topologySummary: 'Blue-team builder paired against hostile Red-team falsifier attempting to break invariants',
    falsifierMechanism: 'Counterexample injection, boundary fuzzing, and security bypass probes',
    idealFor: 'Security gates, OCI vault policies, inbound OAuth bridges, and anti-hallucination harnesses',
  },
  {
    id: 'tournament',
    name: 'Tournament',
    posture: 'Chesed -> Geburah',
    workerCount: 3,
    defaultHelmShots: 4,
    maxDegreesOfFreedom: 0.5,
    topologySummary: '3 independent candidate implementations judged head-to-head on latency, diff size, and safety (T-3)',
    falsifierMechanism: 'Blind comparative judge scoring measurable baseline delta',
    idealFor: 'High-leverage architectural choices, UI excellence, and performance bottlenecks',
  },
  {
    id: 'sieve',
    name: 'Sieve',
    posture: 'Geburah',
    workerCount: 3,
    defaultHelmShots: 3,
    maxDegreesOfFreedom: 0.1,
    topologySummary: 'Progressive 7-Gate elimination funnel stripping unverified claims, dead branches, and slop',
    falsifierMechanism: 'Strict monotonic epistemic filter (E1/E2/E3/U) + branch-delta pre-push audit',
    idealFor: 'PR graveyard triage, commercial release readiness, and epistemic claim scrubbing',
  },
] as const;

export const PUBLIC_ESTATE_REPOS = new Set([
  'chidionyema/idp',
  'chidionyema/crew',
  'chidionyema/estate',
  'chidionyema/estate-core',
  'chidionyema/estate-guards',
  'chidionyema/estate-intents',
  'chidionyema/hermes-agent',
  'chidionyema/hermes-config',
  'chidionyema/hermes-operator',
  'chidionyema/hermes-v2',
  'chidionyema/prospector',
  'chidionyema/mumchimp-medusa',
  'chidionyema/TechMastery.MarketPlace',
]);

export const PRIVATE_ESTATE_REPOS = new Set([
  'chidionyema/argon',
  'chidionyema/argon-sync',
  'chidionyema/argo-greenlane',
  'chidionyema/estate-graph',
  'chidionyema/estate-secrets',
  'chidionyema/estate-archive',
  'chidionyema/idp-archive',
  'chidionyema/mums-concierge',
  'chidionyema/tempo-node',
]);

const FABRICATED_SHA_PATTERNS = [
  /^(0000000|1234567|abcdef0|deadbeef|cafebabe)/i,
  /\.\.\.$/,
  /^<.*>$/,
  /todo|placeholder|mock|fake|example/i,
];

export function isValidGitSha(sha: string | null | undefined): boolean {
  if (!sha) return false;
  const trimmed = sha.trim();
  if (FABRICATED_SHA_PATTERNS.some((rx) => rx.test(trimmed))) {
    return false;
  }
  return /^[0-9a-f]{7,40}$/i.test(trimmed);
}

const BANNED_COMMAND_PATTERNS: Array<{ rx: RegExp; reason: string; fix: string }> = [
  {
    rx: /\bgit\s+push\s+(?:--\S+\s+)*(?:origin\s+)?main\b/i,
    reason: 'Direct push to protected main violates AGENTS.md §2 ("main must never go red").',
    fix: 'Push to an isolated Greenlane branch `lane/<slug>` via `estate-execute lane-submit`.',
  },
  {
    rx: /\bgit\s+push\b.*(?:-f|--force)\b/i,
    reason: 'Force-pushing risks destroying shared worktree history and provenance.',
    fix: 'Create a forward deterministic commit on a fresh `lane/<slug>` branch.',
  },
  {
    rx: /\bkubectl\s+apply\b/i,
    reason: 'Hand-applied cluster mutations (`kubectl apply`) are forbidden by AGENTS.md §2.',
    fix: 'Commit manifest changes through Greenlane and allow Flux GitOps image/manifest convergence.',
  },
  {
    rx: /\bgh\s+pr\s+merge\b.*--admin\b/i,
    reason: 'Bypassing protected-main checks with `--admin` violates security & DoF governance.',
    fix: 'Diagnose and fix the failing required check so Greenlane fast-forwards cleanly.',
  },
  {
    rx: /GENESIS_GUARDIAN_SHA\s*=/i,
    reason: 'Advancing GENESIS_GUARDIAN_SHA without verified trust baseline masks provenance failures.',
    fix: 'Verify exact signed commit lineage from last trusted baseline before guardian updates.',
  },
];

const OVERCLAIM_PHRASES = /\b(fully deployed|100% working|verified in production|mission accomplished|all gates green|live yield confirmed)\b/i;

export function evaluateClaimGate(input: ClaimGateInput): ClaimGateAuditResult {
  const violations: ClaimViolation[] = [];
  let score = 100;

  // 1. Check silent authority promotion (E3/U -> E1)
  const hasMissingCaps = (input.missingCapabilities?.length ?? 0) > 0;
  const hasRealReceipt =
    isValidGitSha(input.observedSha) ||
    isValidGitSha(input.receiptHash) ||
    (typeof input.liveHttpStatus === 'number' && input.liveHttpStatus >= 200 && input.liveHttpStatus < 400 && input.payloadVerified === true);

  if (input.claimedAuthority === 'E1' && (hasMissingCaps || !hasRealReceipt)) {
    violations.push({
      code: 'SILENT_AUTHORITY_PROMOTION',
      severity: 'CRITICAL',
      message: hasMissingCaps
        ? `Claimed E1 verified authority while capabilities [${input.missingCapabilities!.join(', ')}] remain unprovisioned (U).`
        : 'Claimed E1 verified authority without a valid Git SHA, cryptographic receipt hash, or payload-verified live probe.',
      remediation: 'Downgrade claim to U or E3 until live cloud execution produces an independently verifiable receipt.',
    });
    score -= 40;
  }

  // 2. Check fabricated / placeholder SHA
  if (input.observedSha !== undefined && input.observedSha !== null && input.observedSha !== '' && !isValidGitSha(input.observedSha)) {
    violations.push({
      code: 'FAKE_SHA_OR_FABRICATED_COMMIT',
      severity: 'CRITICAL',
      message: `Observed SHA "${input.observedSha}" failed hex commit validation or matches a placeholder/truncated pattern.`,
      remediation: 'Query exact 40-char commit SHA from GitHub API or git rev-parse HEAD; never invent or truncate SHAs with ellipses.',
    });
    score -= 35;
  }

  // 3. Check banned Git / cluster commands
  const allCommands = [...(input.proposedCommands ?? []), input.claimText];
  for (const cmd of allCommands) {
    for (const rule of BANNED_COMMAND_PATTERNS) {
      if (rule.rx.test(cmd)) {
        violations.push({
          code: 'BANNED_GIT_MUTATION',
          severity: 'CRITICAL',
          message: rule.reason,
          remediation: rule.fix,
        });
        score -= 35;
        break;
      }
    }
  }

  // 4. Check production theatre without falsifier
  if (
    OVERCLAIM_PHRASES.test(input.claimText) &&
    (input.integrationTestsPassed === false ||
      input.falsifierVerdict === 'FAIL' ||
      (input.liveHttpStatus === 200 && input.payloadVerified === false))
  ) {
    violations.push({
      code: 'THEATRE_WITHOUT_FALSIFIER',
      severity: 'HIGH',
      message: 'Asserted production completion while negative falsifiers failed, integration tests did not pass, or only bare HTTP 200 was checked.',
      remediation: 'Execute independent negative tests and verify response payload schema before asserting operational yield.',
    });
    score -= 25;
  }

  // 5. Check Seven Gates completeness when supplied
  if (input.sevenGates) {
    const requiredKeys: Array<keyof SevenGateAssessment> = [
      'contextualScoping',
      'dimensionalThresholds',
      'baselineDelta',
      'architecturalTradeoffs',
      'systemicReflexivity',
      'deterministicVerification',
      'provenanceAndTrust',
    ];
    const missingGates = requiredKeys.filter((k) => !input.sevenGates?.[k] || input.sevenGates[k]!.trim().length < 8);
    if (missingGates.length > 0) {
      violations.push({
        code: 'INCOMPLETE_SEVEN_GATES',
        severity: 'MEDIUM',
        message: `7-Gate Cognitive Architecture missing substantive entries for: ${missingGates.join(', ')}.`,
        remediation: 'Quantify thresholds, baseline delta, systemic ripple effects, and provenance authority across all 7 gates.',
      });
      score -= Math.min(20, missingGates.length * 5);
    }
  }

  // 6. Public/Private repository boundary firewall
  if (input.targetRepo && PUBLIC_ESTATE_REPOS.has(input.targetRepo)) {
    if (input.sourceContainsPrivateContext && !input.isPublicCleared) {
      violations.push({
        code: 'PUBLIC_PRIVACY_BOUNDARY_BREACH',
        severity: 'CRITICAL',
        message: `Blocked dispatch of unredacted context to public repository "${input.targetRepo}" without explicit public:true clearance.`,
        remediation: 'Keep private strategy/outbox payloads in chidionyema/argon or pass explicit public:true after secret/IP scrubbing.',
      });
      score -= 45;
    }
  }

  const clampedScore = Math.max(0, score);
  const hasCritical = violations.some((v) => v.severity === 'CRITICAL');
  const hasHigh = violations.some((v) => v.severity === 'HIGH');

  let verdict: ClaimGateAuditResult['verdict'] = 'PASS';
  let effectiveAuthority: EvidenceClass = input.claimedAuthority;

  if (hasCritical) {
    verdict = 'CLAIM_REJECTED';
    effectiveAuthority = hasMissingCaps ? 'U' : 'E3';
  } else if (hasHigh || violations.length > 0) {
    verdict = 'DOWNGRADED_TO_UNVERIFIED';
    effectiveAuthority = input.claimedAuthority === 'E1' ? 'E2' : input.claimedAuthority;
  }

  return {
    verdict,
    effectiveAuthority,
    epistemicScore: clampedScore,
    violations,
    remediationSteps: Array.from(new Set(violations.map((v) => v.remediation))),
  };
}

// --- FLOW State Machine & 600s Stagnation Watchdog ---

export const FLOW_STAGNATION_TIMEOUT_MS = 600_000; // Canonical 600 seconds (argon PR #50)

const ALLOWED_FLOW_TRANSITIONS: Record<FlowPhase, readonly FlowPhase[]> = {
  ACCEPTED_DURABLE: ['LEASE_FENCED', 'BLOCKED_CAPABILITY', 'CLAIM_REJECTED'],
  LEASE_FENCED: ['EXECUTING_FORMATION', 'STAGNATION_DETECTED', 'BLOCKED_CAPABILITY'],
  EXECUTING_FORMATION: ['FALSIFIER_AUDIT', 'STAGNATION_DETECTED', 'BLOCKED_CAPABILITY', 'CLAIM_REJECTED'],
  FALSIFIER_AUDIT: ['LANE_SUBMITTED', 'CLAIM_REJECTED', 'EXECUTING_FORMATION'],
  LANE_SUBMITTED: ['GREENLANE_VERIFIED', 'CLAIM_REJECTED', 'STAGNATION_DETECTED'],
  GREENLANE_VERIFIED: ['YIELD_CONFIRMED', 'CLAIM_REJECTED'],
  YIELD_CONFIRMED: [],
  STAGNATION_DETECTED: ['RECOVERING_AUTONOMOUS', 'BLOCKED_CAPABILITY'],
  RECOVERING_AUTONOMOUS: ['LEASE_FENCED', 'EXECUTING_FORMATION', 'BLOCKED_CAPABILITY'],
  CLAIM_REJECTED: ['LEASE_FENCED', 'RECOVERING_AUTONOMOUS'],
  BLOCKED_CAPABILITY: ['LEASE_FENCED'],
};

export interface FlowInstructionRecord {
  instructionId: string;
  idempotencyKey: string;
  title: string;
  body: string;
  repo: string;
  formation: FormationId;
  helmShots: number;
  phase: FlowPhase;
  leaseEpoch: number;
  assignedWorkerId: string | null;
  executionId: string | null;
  laneBranch: string | null;
  sourceSha: string | null;
  receiptHash: string | null;
  authorityClass: EvidenceClass;
  createdAtMs: number;
  lastHeartbeatMs: number;
  recoveryCount: number;
  stagnationReason?: string | null;
  falsifierSummary?: string | null;
}

export function canTransitionFlow(from: FlowPhase, to: FlowPhase): boolean {
  return ALLOWED_FLOW_TRANSITIONS[from]?.includes(to) ?? false;
}

export function transitionFlowRecord(
  record: FlowInstructionRecord,
  nextPhase: FlowPhase,
  workerEpoch: number,
  nowMs: number
): { ok: true; record: FlowInstructionRecord } | { ok: false; errorCode: 'FENCE_EPOCH_STALE' | 'INVALID_FLOW_TRANSITION'; detail: string } {
  if (workerEpoch < record.leaseEpoch) {
    return {
      ok: false,
      errorCode: 'FENCE_EPOCH_STALE',
      detail: `Worker lease epoch ${workerEpoch} is fenced out by current authoritative epoch ${record.leaseEpoch} (argon-sync fail-closed).`,
    };
  }
  if (!canTransitionFlow(record.phase, nextPhase)) {
    return {
      ok: false,
      errorCode: 'INVALID_FLOW_TRANSITION',
      detail: `Illegal FLOW transition from ${record.phase} to ${nextPhase}.`,
    };
  }
  return {
    ok: true,
    record: {
      ...record,
      phase: nextPhase,
      lastHeartbeatMs: nowMs,
    },
  };
}

export interface StagnationCheckResult {
  stagnant: boolean;
  inactiveSeconds: number;
  updatedRecord: FlowInstructionRecord;
}

const ACTIVE_WATCHDOG_PHASES = new Set<FlowPhase>([
  'LEASE_FENCED',
  'EXECUTING_FORMATION',
  'LANE_SUBMITTED',
]);

export function evaluateStagnationWatchdog(
  record: FlowInstructionRecord,
  nowMs: number,
  timeoutMs: number = FLOW_STAGNATION_TIMEOUT_MS
): StagnationCheckResult {
  const elapsedMs = Math.max(0, nowMs - record.lastHeartbeatMs);
  const inactiveSeconds = Math.floor(elapsedMs / 1000);

  if (!ACTIVE_WATCHDOG_PHASES.has(record.phase) || elapsedMs < timeoutMs) {
    return {
      stagnant: false,
      inactiveSeconds,
      updatedRecord: record,
    };
  }

  // Fence out stale worker by bumping leaseEpoch and transitioning to autonomous recovery
  const nextEpoch = record.leaseEpoch + 1;
  const recoveredWorker = `recovery-centurion-e${nextEpoch}`;

  return {
    stagnant: true,
    inactiveSeconds,
    updatedRecord: {
      ...record,
      phase: 'RECOVERING_AUTONOMOUS',
      leaseEpoch: nextEpoch,
      assignedWorkerId: recoveredWorker,
      recoveryCount: record.recoveryCount + 1,
      lastHeartbeatMs: nowMs,
      stagnationReason: `Watchdog triggered after ${inactiveSeconds}s inactivity (>= ${Math.floor(timeoutMs / 1000)}s threshold). Previous worker fenced at epoch ${record.leaseEpoch}.`,
    },
  };
}

// --- [GENESIS-OUTBOX] JSON v1 Inbound Bridge Contract ---

export interface GenesisInboundPayloadV1 {
  v: number;
  repo: string;
  instruction_id: string;
  title: string;
  body: string;
  public?: boolean;
  formation?: FormationId;
  helm_shots?: number;
}

export type InboundValidationResult =
  | {
      accepted: true;
      status: 'ACCEPTED_NEW' | 'DUPLICATE_IDEMPOTENT_NOOP';
      normalizedRepo: string;
      laneBranch: string;
      authorityNote: string;
    }
  | {
      accepted: false;
      errorCode: 'INVALID_SCHEMA_V1' | 'PUBLIC_REPO_REQUIRES_EXPLICIT_PUBLIC_TRUE' | 'PRIVATE_REPO_FORBIDS_PUBLIC_FLAG' | 'UNKNOWN_ESTATE_REPO';
      reason: string;
    };

export function validateGenesisInboundPayload(
  payload: unknown,
  processedInstructionIds: ReadonlySet<string>
): InboundValidationResult {
  if (!payload || typeof payload !== 'object') {
    return {
      accepted: false,
      errorCode: 'INVALID_SCHEMA_V1',
      reason: 'Dispatch payload must be a JSON v1 object.',
    };
  }

  const p = payload as Partial<GenesisInboundPayloadV1>;
  if (
    p.v !== 1 ||
    typeof p.repo !== 'string' ||
    !p.repo.trim() ||
    typeof p.instruction_id !== 'string' ||
    !/^[A-Za-z0-9._:-]{4,64}$/.test(p.instruction_id.trim()) ||
    typeof p.title !== 'string' ||
    p.title.trim().length < 4 ||
    typeof p.body !== 'string' ||
    p.body.trim().length < 8
  ) {
    return {
      accepted: false,
      errorCode: 'INVALID_SCHEMA_V1',
      reason: 'JSON v1 requires v===1, valid repo, alphanumeric instruction_id (4-64 chars), title (>=4 chars), and body (>=8 chars).',
    };
  }

  const normalizedRepo = p.repo.trim().includes('/') ? p.repo.trim() : `chidionyema/${p.repo.trim()}`;
  const isPublicRepo = PUBLIC_ESTATE_REPOS.has(normalizedRepo);
  const isPrivateRepo = PRIVATE_ESTATE_REPOS.has(normalizedRepo);

  if (!isPublicRepo && !isPrivateRepo) {
    return {
      accepted: false,
      errorCode: 'UNKNOWN_ESTATE_REPO',
      reason: `Repository "${normalizedRepo}" is not registered in the curated estate inventory.`,
    };
  }

  if (isPublicRepo && p.public !== true) {
    return {
      accepted: false,
      errorCode: 'PUBLIC_REPO_REQUIRES_EXPLICIT_PUBLIC_TRUE',
      reason: `Target "${normalizedRepo}" is a PUBLIC repository; JSON v1 requires explicit "public": true to prevent confidential estate leakage.`,
    };
  }

  if (isPrivateRepo && p.public === true) {
    return {
      accepted: false,
      errorCode: 'PRIVATE_REPO_FORBIDS_PUBLIC_FLAG',
      reason: `Target "${normalizedRepo}" is a PRIVATE repository; marking dispatch "public": true is rejected as an authority mismatch.`,
    };
  }

  const cleanId = p.instruction_id.trim();
  const slug = cleanId.toLowerCase().replace(/[^a-z0-9-]+/g, '-').slice(0, 36);
  const laneBranch = `lane/${slug}`;

  if (processedInstructionIds.has(cleanId)) {
    return {
      accepted: true,
      status: 'DUPLICATE_IDEMPOTENT_NOOP',
      normalizedRepo,
      laneBranch,
      authorityNote: `Instruction ${cleanId} already durably accepted; returning existing receipt without duplicate execution.`,
    };
  }

  return {
    accepted: true,
    status: 'ACCEPTED_NEW',
    normalizedRepo,
    laneBranch,
    authorityNote: 'Validated via JSON v1 inbound contract and bound to isolated Greenlane branch.',
  };
}

// --- PR Drift & Bounded Greenlane Merge Order ---

export interface PullRequestAuditInput {
  repo: string;
  number: number;
  title: string;
  handoverSha: string | null;
  liveSha: string | null;
  handoverMainSha: string | null;
  liveMainSha: string | null;
  checksState: 'PASSING' | 'FAILING' | 'PENDING' | 'UNVERIFIED_PRIVATE';
  blockingIncident?: string | null;
  priorityTier: 1 | 2 | 3;
}

export interface ReconciledPullRequest extends PullRequestAuditInput {
  driftState: 'VERIFIED_MATCH' | 'HEAD_MOVED_LIVE' | 'NEW_SINCE_HANDOVER' | 'PRIVATE_UNOBSERVED';
  mainMoved: boolean;
  disposition: 'READY_FOR_GREENLANE' | 'REBASE_ONTO_LIVE_MAIN' | 'FIX_FAILING_GATE_FIRST' | 'AWAITING_PRIVATE_CONNECTOR';
  authority: EvidenceClass;
  recommendedLaneCommand: string;
}

export function reconcilePullRequestBacklog(items: readonly PullRequestAuditInput[]): ReconciledPullRequest[] {
  const reconciled = items.map((pr): ReconciledPullRequest => {
    const mainMoved = Boolean(pr.handoverMainSha && pr.liveMainSha && pr.handoverMainSha !== pr.liveMainSha);
    let driftState: ReconciledPullRequest['driftState'] = 'PRIVATE_UNOBSERVED';
    let authority: EvidenceClass = 'E2';

    if (pr.liveSha) {
      authority = 'E1';
      if (!pr.handoverSha) {
        driftState = 'NEW_SINCE_HANDOVER';
      } else if (pr.liveSha.startsWith(pr.handoverSha) || pr.handoverSha.startsWith(pr.liveSha)) {
        driftState = 'VERIFIED_MATCH';
      } else {
        driftState = 'HEAD_MOVED_LIVE';
      }
    }

    let disposition: ReconciledPullRequest['disposition'];
    if (pr.checksState === 'UNVERIFIED_PRIVATE' || !pr.liveSha) {
      disposition = 'AWAITING_PRIVATE_CONNECTOR';
    } else if (pr.checksState === 'FAILING' || pr.blockingIncident) {
      disposition = 'FIX_FAILING_GATE_FIRST';
    } else if (mainMoved || pr.checksState === 'PENDING') {
      disposition = 'REBASE_ONTO_LIVE_MAIN';
    } else {
      disposition = 'READY_FOR_GREENLANE';
    }

    const repoShort = pr.repo.split('/')[1] || pr.repo;
    const recommendedLaneCommand = `estate-execute lane-submit --repo ${repoShort} --pr ${pr.number} --head ${pr.liveSha ? pr.liveSha.slice(0, 7) : (pr.handoverSha?.slice(0, 7) ?? 'unverified')}`;

    return {
      ...pr,
      driftState,
      mainMoved,
      disposition,
      authority,
      recommendedLaneCommand,
    };
  });

  const orderWeight: Record<ReconciledPullRequest['disposition'], number> = {
    READY_FOR_GREENLANE: 1,
    REBASE_ONTO_LIVE_MAIN: 2,
    FIX_FAILING_GATE_FIRST: 3,
    AWAITING_PRIVATE_CONNECTOR: 4,
  };

  return reconciled.sort((a, b) => {
    const wDiff = orderWeight[a.disposition] - orderWeight[b.disposition];
    if (wDiff !== 0) return wDiff;
    if (a.priorityTier !== b.priorityTier) return a.priorityTier - b.priorityTier;
    return b.number - a.number;
  });
}

export function computeCostUsd(inputTokens: number, outputTokens: number, model: string): number {
  const isPro = model.includes('argon') || model.includes('carbon');
  const inRatePerM = isPro ? 1.25 : 0.15;
  const outRatePerM = isPro ? 5.0 : 0.6;
  const raw = (inputTokens / 1_000_000) * inRatePerM + (outputTokens / 1_000_000) * outRatePerM;
  return Math.round(raw * 1_000_000) / 1_000_000;
}
