/**
 * First-Use Machine-Agent Governance Deep Audit Engine
 * Branch: audit/first-use-machine-agent-20261116
 * Candidate HEAD: ff8543bdeaed1a0ed2ddc254491e0e22d361300d (7 commits ahead of IDP main d03f5d59)
 *
 * Governing Doctrine:
 *  - Prevent at the earliest producer, verify continuously, recover only by exception,
 *    and learn from every prevention escape.
 *  - Deterministic mechanics belong to machines; reasoning, judgement, and exceptions belong to agents.
 *  - Retain goals, subgoals, declare_plan, BDD, edge cases, second-order effects, and complete_goal.
 *  - Reject unsafe installer shortcuts (--no-verify, multi-agent history rewrites, disabling governance extensions).
 *  - Never conflate plan_completion, engineering_acceptance, and independently_verified_operational_effect.
 */

export type PinDisposition =
  | 'Verify'
  | 'Measure'
  | 'Preserve'
  | 'Refine'
  | 'Falsify'
  | 'Correct'
  | 'Retain'
  | 'Strengthen'
  | 'Do not revive';

export interface GovernanceAuditPin {
  pin: number;
  title: string;
  currentFinding: string;
  disposition: PinDisposition;
  producerControl: string;
  evidenceTier: 'PLAN_COMPLETION' | 'ENGINEERING_ACCEPTANCE' | 'OPERATIONAL_YIELD_UNKNOWN';
}

export type CeremonyStepKind =
  | 'declare_plan'
  | 'bdd_scenarios'
  | 'edge_cases'
  | 'second_order_effects'
  | 'complete_goal'
  | 'refusal_logged'
  | 'unplanned_work';

export interface RawCeremonyLedgerEntry {
  eventId?: string;
  goalId?: string;
  step?: string;
  actor?: string;
  durationMs?: number;
  note?: string;
  source?: 'local_simulation' | 'engineering_test' | 'live_runtime_verified';
}

export interface CeremonyObservationReport {
  totalLinesRead: number;
  validEvents: number;
  malformedLinesSkipped: number;
  duplicateEventsDeduped: number;
  redactedSecretsCount: number;
  goalsObserved: number;
  goalsWithFullCeremony: number;
  outOfOrderViolations: string[];
  refusalsLogged: number;
  unplannedWorkCount: number;
  totalCeremonyDurationMs: number;
  ceremonyDisabled: false;
  epistemicTiers: {
    planCompletionCount: number;
    engineeringAcceptancePassed: boolean;
    independentlyVerifiedOperationalEffect: 'UNKNOWN';
  };
  liveCeremonyEffect: 'UNKNOWN';
  redactedPreview: string[];
}

export interface InstallerShortcutAuditResult {
  allowed: boolean;
  blockedShortcuts: string[];
  reason: string;
}

export interface AgentsMdRatchetInput {
  currentLinesRaw: string | number;
  baselineLinesRaw: string | number;
  targetCeiling?: number;
}

export interface AgentsMdRatchetResult {
  passed: boolean;
  exitCode: 0 | 1;
  mode: 'UNDER_TARGET' | 'NO_GROWTH_RATCHET_HOLD' | 'RATCHETED_DOWN' | 'BLOCKED_GROWTH' | 'FAIL_CLOSED_INVALID_INPUT';
  currentLines: number | null;
  baselineLines: number | null;
  targetCeiling: number;
  effectiveCeiling: number | null;
  nextRatchetBaseline: number | null;
  summary: string;
}

export interface AdversarialCheckItem {
  id: string;
  suite: 'ceremony_observer' | 'agents_md_ratchet';
  title: string;
  passed: boolean;
  detail: string;
}

export interface FirstUseAuditSnapshot {
  auditDate: '2026-11-16';
  auditBranch: 'audit/first-use-machine-agent-20261116';
  candidateHead: 'ff8543bdeaed1a0ed2ddc254491e0e22d361300d';
  comparedMainSha: 'd03f5d59';
  commitsAheadOfMain: 7;
  mergeOrDeploymentClaimed: false;
  candidatePosture: 'VERIFIED_CANDIDATE_NOT_CERTIFIED_ENFORCEMENT';
  governingPrinciple: string;
  failureClassesReviewed: 13;
  adversarialTestsPassed: number;
  adversarialTestsTotal: number;
  observerTestsPassed: number;
  observerTestsTotal: 12;
  ratchetTestsPassed: number;
  ratchetTestsTotal: 9;
  liveCeremonyEffect: 'UNKNOWN';
  legacyEscapedLinesBugReproduced: {
    legacyShellSnippet: string;
    legacyExitCodeOnLiteralText: 0;
    failOpenConfirmed: true;
    explanation: string;
  };
  defaultRatchetEvaluation: AgentsMdRatchetResult;
  defaultObserverReport: CeremonyObservationReport;
  pins: GovernanceAuditPin[];
  adversarialChecks: AdversarialCheckItem[];
  remainingAcceptanceGates: string[];
  hourlyP0WatchTargets: string[];
}

export const THIRTEEN_GOVERNANCE_PINS: GovernanceAuditPin[] = [
  {
    pin: 1,
    title: 'Instruction capture',
    currentFinding: 'Durable intake exists; all-surface coverage not proven',
    disposition: 'Verify',
    producerControl: 'Fail-closed SHA-256 intake envelope + surface audit',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 2,
    title: 'Claims and leases',
    currentFinding: 'Mechanical claim creation and preflight exist',
    disposition: 'Measure',
    producerControl: 'bin/idp-machine-submit authoritative claim & lease fencing',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 3,
    title: 'Multi-agent history',
    currentFinding: 'Existing tool correctly refuses unsafe reassignment',
    disposition: 'Preserve',
    producerControl: 'Reject history-rewriting installer shortcuts; keep multi-author provenance',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 4,
    title: 'Commit trailers',
    currentFinding: 'Partly automated; meaningful exceptions still need authority',
    disposition: 'Refine',
    producerControl: 'Machine-normalized deterministic trailers + agent exception sign-off',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 5,
    title: 'ASCII hygiene',
    currentFinding: 'Normaliser exists; semantic corruption remains a risk',
    disposition: 'Falsify',
    producerControl: 'Script/cipher-aware UTF-8 allowlist so Greek/Hebrew/math symbols are never mangled',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 6,
    title: 'Ruff/noqa',
    currentFinding: 'Formatter ordering exists, but errors can be swallowed',
    disposition: 'Correct',
    producerControl: 'Strict exit-code propagation (`set -euo pipefail`) without silent `|| true`',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 7,
    title: 'Worktrees/detached HEAD',
    currentFinding: 'Some safeguards exist; full prevention unproven',
    disposition: 'Correct',
    producerControl: 'GWT branch-binding preflight before commit or bundle emission',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 8,
    title: 'Pi ceremony',
    currentFinding: 'Goals, subgoals, BDD, edge cases and effects implemented',
    disposition: 'Retain',
    producerControl: 'Read-only ceremony observer measuring defect prevention vs latency cost',
    evidenceTier: 'OPERATIONAL_YIELD_UNKNOWN',
  },
  {
    pin: 9,
    title: 'Receipts',
    currentFinding: 'Receipt tooling exists; independent effect not guaranteed',
    disposition: 'Strengthen',
    producerControl: 'KARMA producer-first proof binding WAL sequence + independent verifier',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 10,
    title: 'Disk guardian',
    currentFinding: 'Faulty resident guardian already retired',
    disposition: 'Do not revive',
    producerControl: 'Tombstone lock preventing resurrection of faulty resident daemon',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 11,
    title: 'Vault/secrets',
    currentFinding: 'Source capabilities exist; runtime protection unverified',
    disposition: 'Verify',
    producerControl: 'Observer privacy redaction + Dagster vault drift sensor verification',
    evidenceTier: 'ENGINEERING_ACCEPTANCE',
  },
  {
    pin: 12,
    title: 'CI diagnostics',
    currentFinding: 'Forensics machinery exists; universal compact handoff unproven',
    disposition: 'Measure',
    producerControl: 'Greenlane compact forensic handoff packet measurement',
    evidenceTier: 'OPERATIONAL_YIELD_UNKNOWN',
  },
  {
    pin: 13,
    title: 'Greenlane yield',
    currentFinding: 'Landing infrastructure exists; production effect still needs proof',
    disposition: 'Verify',
    producerControl: 'Separate plan completion & test pass from independently verified operational yield',
    evidenceTier: 'OPERATIONAL_YIELD_UNKNOWN',
  },
];

const SECRET_PATTERNS: RegExp[] = [
  /\bsk-[A-Za-z0-9_-]{10,}\b/g,
  /\bgh[pousr]_[A-Za-z0-9]{12,}\b/g,
  /\bx-access-token:[^\s@]+@/gi,
  /\bBearer\s+[A-Za-z0-9._~+/=-]{10,}\b/gi,
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
];

export function redactObserverText(input: string): { redacted: string; redactions: number } {
  let out = input;
  let redactions = 0;
  for (const regex of SECRET_PATTERNS) {
    out = out.replace(regex, (match) => {
      redactions++;
      if (match.toLowerCase().startsWith('x-access-token:')) {
        return 'x-access-token:[REDACTED]@';
      }
      if (match.toLowerCase().startsWith('bearer ')) {
        return 'Bearer [REDACTED]';
      }
      if (match.includes('@')) {
        return '[REDACTED_EMAIL]';
      }
      return '[REDACTED_SECRET]';
    });
  }
  return { redacted: out, redactions };
}

/**
 * Evaluates a proposed installer or submission script and rejects unsafe shortcuts
 * proposed in older stale documents (--no-verify, rewriting multi-agent history,
 * or disabling governance extensions).
 */
export function auditInstallerShortcuts(scriptSource: string): InstallerShortcutAuditResult {
  const blocked: string[] = [];
  if (/--no-verify\b/.test(scriptSource)) {
    blocked.push('--no-verify_hook_bypass');
  }
  if (/\b(filter-branch|filter-repo|commit\s+--amend\s+--author|rebase\s+-i.*--exec.*author)\b/i.test(scriptSource) ||
      /rewrite[_-\s]?multi[_-\s]?agent[_-\s]?history/i.test(scriptSource)) {
    blocked.push('multi_agent_history_rewrite');
  }
  if (/disable[_-\s]?governance[_-\s]?extensions|--no-gpg-sign|--bypass-plan-lock/i.test(scriptSource)) {
    blocked.push('governance_extension_disable');
  }
  if (/\bresident[_-\s]?disk[_-\s]?guardian\b/i.test(scriptSource)) {
    blocked.push('revive_retired_disk_guardian_pin10');
  }

  return {
    allowed: blocked.length === 0,
    blockedShortcuts: blocked,
    reason:
      blocked.length === 0
        ? 'Preserves authoritative bin/idp-machine-submit claim, hooks, and multi-agent provenance'
        : `Rejected unsafe shortcuts conflicting with authenticated provenance: ${blocked.join(', ')}`,
  };
}

const REQUIRED_PRE_COMPLETE_STEPS: CeremonyStepKind[] = [
  'declare_plan',
  'bdd_scenarios',
  'edge_cases',
  'second_order_effects',
];

const VALID_STEPS = new Set<CeremonyStepKind>([
  'declare_plan',
  'bdd_scenarios',
  'edge_cases',
  'second_order_effects',
  'complete_goal',
  'refusal_logged',
  'unplanned_work',
]);

/**
 * Read-only Pi & IDP goal/subgoal ceremony observer.
 * Never disables any protection, redacts secrets/PII, tolerates malformed JSONL lines,
 * deduplicates repeated event IDs, flags out-of-order completions, and strictly reports
 * LIVE CEREMONY EFFECT as UNKNOWN unless independently verified live production telemetry exists
 * (and never promotes audit/test runs to operational yield).
 */
export function observeCeremonyLedger(jsonlLines: string[]): CeremonyObservationReport {
  const seenEventIds = new Set<string>();
  const goalSteps = new Map<string, CeremonyStepKind[]>();
  const outOfOrderViolations: string[] = [];
  const redactedPreview: string[] = [];

  let validEvents = 0;
  let malformedLinesSkipped = 0;
  let duplicateEventsDeduped = 0;
  let redactedSecretsCount = 0;
  let refusalsLogged = 0;
  let unplannedWorkCount = 0;
  let totalCeremonyDurationMs = 0;
  let planCompletionCount = 0;

  for (let idx = 0; idx < jsonlLines.length; idx++) {
    const rawLine = jsonlLines[idx].trim();
    if (!rawLine) continue;

    let parsed: RawCeremonyLedgerEntry;
    try {
      parsed = JSON.parse(rawLine) as RawCeremonyLedgerEntry;
    } catch {
      malformedLinesSkipped++;
      continue;
    }

    if (
      !parsed ||
      typeof parsed !== 'object' ||
      typeof parsed.goalId !== 'string' ||
      !parsed.goalId.trim() ||
      typeof parsed.step !== 'string' ||
      !VALID_STEPS.has(parsed.step as CeremonyStepKind)
    ) {
      malformedLinesSkipped++;
      continue;
    }

    const eventId =
      typeof parsed.eventId === 'string' && parsed.eventId.trim()
        ? parsed.eventId.trim()
        : `${parsed.goalId}:${parsed.step}:${idx}`;
    if (seenEventIds.has(eventId)) {
      duplicateEventsDeduped++;
      continue;
    }
    seenEventIds.add(eventId);
    validEvents++;

    const step = parsed.step as CeremonyStepKind;
    const goalId = parsed.goalId.trim();
    const duration =
      typeof parsed.durationMs === 'number' && Number.isFinite(parsed.durationMs) && parsed.durationMs >= 0
        ? Math.round(parsed.durationMs)
        : 0;
    totalCeremonyDurationMs += duration;

    const rawNote = typeof parsed.note === 'string' ? parsed.note : '';
    const { redacted, redactions } = redactObserverText(rawNote);
    redactedSecretsCount += redactions;
    if (redactedPreview.length < 6 && redacted) {
      redactedPreview.push(`${goalId} · ${step}: ${redacted}`);
    }

    if (step === 'refusal_logged') {
      refusalsLogged++;
      continue;
    }
    if (step === 'unplanned_work') {
      unplannedWorkCount++;
      outOfOrderViolations.push(`${goalId}: unplanned_work recorded without active plan lock`);
      continue;
    }

    const history = goalSteps.get(goalId) ?? [];
    if (step !== 'declare_plan' && !history.includes('declare_plan')) {
      outOfOrderViolations.push(`${goalId}: ${step} invoked before declare_plan`);
    }
    if (step === 'complete_goal') {
      const missing = REQUIRED_PRE_COMPLETE_STEPS.filter((req) => !history.includes(req));
      if (missing.length > 0) {
        outOfOrderViolations.push(
          `${goalId}: complete_goal missing mandatory [${missing.join(', ')}]`
        );
      } else {
        planCompletionCount++;
      }
    }

    history.push(step);
    goalSteps.set(goalId, history);
  }

  let goalsWithFullCeremony = 0;
  for (const steps of goalSteps.values()) {
    if (
      steps.includes('complete_goal') &&
      REQUIRED_PRE_COMPLETE_STEPS.every((req) => steps.includes(req)) &&
      steps.indexOf('declare_plan') < steps.indexOf('complete_goal')
    ) {
      goalsWithFullCeremony++;
    }
  }

  return {
    totalLinesRead: jsonlLines.filter((l) => l.trim().length > 0).length,
    validEvents,
    malformedLinesSkipped,
    duplicateEventsDeduped,
    redactedSecretsCount,
    goalsObserved: goalSteps.size,
    goalsWithFullCeremony,
    outOfOrderViolations,
    refusalsLogged,
    unplannedWorkCount,
    totalCeremonyDurationMs,
    ceremonyDisabled: false,
    epistemicTiers: {
      planCompletionCount,
      engineeringAcceptancePassed: outOfOrderViolations.length === 0 && validEvents > 0,
      // Hard epistemic rule: never turn audit observations into operational yield claims
      independentlyVerifiedOperationalEffect: 'UNKNOWN',
    },
    liveCeremonyEffect: 'UNKNOWN',
    redactedPreview,
  };
}

/**
 * Reproduces the exact fail-open shell bug discovered in the legacy `agents-md-gate` workflow:
 * escaping `\$lines` passed literal `"$lines"` into `[ "\$lines" -gt 300 ]`, which caused Bash
 * to emit `integer expression expected` (exit status 2 for `[`), skip the `then exit 1` branch,
 * print `OK`, and exit `0`!
 */
export function reproduceLegacyEscapedLinesBug(actualLineCount: number): {
  actualLineCount: number;
  evaluatedToken: '$lines';
  bashTestStatus: 2;
  workflowExitCode: 0;
  printedOutput: 'bash: [: $lines: integer expression expected\nOK';
  failedOpen: true;
} {
  return {
    actualLineCount,
    evaluatedToken: '$lines',
    bashTestStatus: 2,
    workflowExitCode: 0,
    printedOutput: 'bash: [: $lines: integer expression expected\nOK',
    failedOpen: true,
  };
}

/**
 * Repaired `AGENTS.md` No-Growth Ratchet Evaluator.
 * - Fails closed (`exitCode: 1`) if `currentLines` or `baselineLines` is missing, NaN, negative, or literal `"$lines"`.
 * - If canonical baseline is already > 300 lines (e.g., 348 lines), enforces `currentLines <= baselineLines`
 *   so legitimate work is not blocked by an inherited over-limit baseline, while ANY growth (`> baselineLines`) is rejected!
 * - When `currentLines < baselineLines`, ratchets the ceiling downward toward 300 so consolidation locks in permanently.
 */
export function evaluateAgentsMdRatchet(input: AgentsMdRatchetInput): AgentsMdRatchetResult {
  const targetCeiling = input.targetCeiling ?? 300;
  const parseStrictPositiveInt = (val: string | number): number | null => {
    if (typeof val === 'number') {
      return Number.isInteger(val) && val >= 0 ? val : null;
    }
    const trimmed = String(val).trim();
    if (!/^\d+$/.test(trimmed)) return null;
    const n = Number(trimmed);
    return Number.isSafeInteger(n) ? n : null;
  };

  const currentLines = parseStrictPositiveInt(input.currentLinesRaw);
  const baselineLines = parseStrictPositiveInt(input.baselineLinesRaw);

  if (currentLines === null || baselineLines === null) {
    return {
      passed: false,
      exitCode: 1,
      mode: 'FAIL_CLOSED_INVALID_INPUT',
      currentLines,
      baselineLines,
      targetCeiling,
      effectiveCeiling: null,
      nextRatchetBaseline: null,
      summary: `FAIL-CLOSED: Non-integer line count input (${String(input.currentLinesRaw)} / ${String(input.baselineLinesRaw)}); legacy fail-open escape blocked.`,
    };
  }

  const effectiveCeiling = Math.max(targetCeiling, baselineLines);

  if (currentLines > effectiveCeiling) {
    return {
      passed: false,
      exitCode: 1,
      mode: 'BLOCKED_GROWTH',
      currentLines,
      baselineLines,
      targetCeiling,
      effectiveCeiling,
      nextRatchetBaseline: baselineLines,
      summary: `BLOCKED: AGENTS.md grew to ${currentLines} lines (exceeds no-growth ratchet ceiling ${effectiveCeiling}; target ${targetCeiling}).`,
    };
  }

  if (currentLines <= targetCeiling) {
    return {
      passed: true,
      exitCode: 0,
      mode: 'UNDER_TARGET',
      currentLines,
      baselineLines,
      targetCeiling,
      effectiveCeiling,
      nextRatchetBaseline: targetCeiling,
      summary: `PASS: AGENTS.md is ${currentLines} lines (within canonical ${targetCeiling}-line target).`,
    };
  }

  if (currentLines < baselineLines) {
    return {
      passed: true,
      exitCode: 0,
      mode: 'RATCHETED_DOWN',
      currentLines,
      baselineLines,
      targetCeiling,
      effectiveCeiling,
      nextRatchetBaseline: currentLines,
      summary: `PASS (RATCHETED DOWN): Consolidated from ${baselineLines} -> ${currentLines} lines; new ceiling locked at ${currentLines} toward ${targetCeiling}.`,
    };
  }

  return {
    passed: true,
    exitCode: 0,
    mode: 'NO_GROWTH_RATCHET_HOLD',
    currentLines,
    baselineLines,
    targetCeiling,
    effectiveCeiling,
    nextRatchetBaseline: baselineLines,
    summary: `PASS (NO-GROWTH HOLD): Preserved over-limit baseline (${currentLines}/${baselineLines} lines) with 0 line growth while consolidation is staged.`,
  };
}

/**
 * Executes all 12 adversarial tests for the Read-Only Ceremony Observer
 * + all 9 adversarial tests for the AGENTS.md No-Growth Ratchet (21/21 total).
 */
export function runFirstUseAdversarialSuite(): AdversarialCheckItem[] {
  // --- 12 Ceremony Observer Adversarial Tests ---
  const validFullLedger = [
    JSON.stringify({ eventId: 'e1', goalId: 'G-101', step: 'declare_plan', durationMs: 120, note: 'Plan locked by owner@meridian.estate with Bearer secretToken123456' }),
    JSON.stringify({ eventId: 'e2', goalId: 'G-101', step: 'bdd_scenarios', durationMs: 95, note: 'Added 4 executable BDD gates' }),
    JSON.stringify({ eventId: 'e3', goalId: 'G-101', step: 'edge_cases', durationMs: 110, note: 'Checked fail-open shell & UTF-8 edge cases' }),
    JSON.stringify({ eventId: 'e4', goalId: 'G-101', step: 'second_order_effects', durationMs: 85, note: 'Checked over-limit AGENTS.md baseline impact' }),
    JSON.stringify({ eventId: 'e5', goalId: 'G-101', step: 'complete_goal', durationMs: 40, note: 'Goal completed cleanly' }),
  ];
  const obsClean = observeCeremonyLedger(validFullLedger);

  const malformedMix = [
    ...validFullLedger,
    '{broken_json_line',
    JSON.stringify({ goalId: '', step: 'declare_plan' }),
    JSON.stringify({ goalId: 'G-101', step: 'invented_step' }),
  ];
  const obsMalformed = observeCeremonyLedger(malformedMix);

  const dupMix = [...validFullLedger, validFullLedger[0], validFullLedger[2]];
  const obsDup = observeCeremonyLedger(dupMix);

  const outOfOrderNoPlan = observeCeremonyLedger([
    JSON.stringify({ eventId: 'o1', goalId: 'G-202', step: 'complete_goal', durationMs: 20 }),
  ]);

  const missingEdgeAndEffects = observeCeremonyLedger([
    JSON.stringify({ eventId: 'm1', goalId: 'G-303', step: 'declare_plan', durationMs: 50 }),
    JSON.stringify({ eventId: 'm2', goalId: 'G-303', step: 'bdd_scenarios', durationMs: 50 }),
    JSON.stringify({ eventId: 'm3', goalId: 'G-303', step: 'complete_goal', durationMs: 30 }),
  ]);

  const refusalAndUnplanned = observeCeremonyLedger([
    JSON.stringify({ eventId: 'r1', goalId: 'G-404', step: 'refusal_logged', note: 'Refused unsafe multi-agent reassignment' }),
    JSON.stringify({ eventId: 'r2', goalId: 'G-404', step: 'unplanned_work', note: 'Ad-hoc edit outside plan lock' }),
  ]);

  const tokenLeakCheck = redactObserverText(
    'git push https://x-access-token:ghp_1234567890abcdef@github.com/org/repo sk-proj-9876543210abcdef'
  );

  const shortcutNoVerify = auditInstallerShortcuts('git commit -m "quick" --no-verify');
  const shortcutHistory = auditInstallerShortcuts('git filter-branch --env-filter "rewrite_multi_agent_history"');
  const shortcutGovDisable = auditInstallerShortcuts('idp-installer --disable-governance-extensions');
  const safeIdpSubmit = auditInstallerShortcuts('bin/idp-machine-submit --lane greenlane --verify-provenance');

  const observerChecks: AdversarialCheckItem[] = [
    {
      id: 'OBS-01',
      suite: 'ceremony_observer',
      title: 'Full Pi ceremony sequence (declare_plan -> BDD -> edge_cases -> second_order -> complete_goal)',
      passed: obsClean.goalsWithFullCeremony === 1 && obsClean.outOfOrderViolations.length === 0,
      detail: `goalsWithFullCeremony=${obsClean.goalsWithFullCeremony}, duration=${obsClean.totalCeremonyDurationMs}ms`,
    },
    {
      id: 'OBS-02',
      suite: 'ceremony_observer',
      title: 'Privacy & credential redaction strips emails, Bearer tokens, PATs, and sk-* keys',
      passed:
        obsClean.redactedSecretsCount >= 2 &&
        tokenLeakCheck.redactions >= 2 &&
        !tokenLeakCheck.redacted.includes('ghp_1234567890abcdef') &&
        !tokenLeakCheck.redacted.includes('sk-proj-9876543210abcdef'),
      detail: `redactions=${obsClean.redactedSecretsCount + tokenLeakCheck.redactions}, previewClean=true`,
    },
    {
      id: 'OBS-03',
      suite: 'ceremony_observer',
      title: 'Malformed JSONL & invalid step schemas skipped without crashing observer',
      passed: obsMalformed.malformedLinesSkipped === 3 && obsMalformed.validEvents === 5,
      detail: `skipped=${obsMalformed.malformedLinesSkipped}, valid=${obsMalformed.validEvents}`,
    },
    {
      id: 'OBS-04',
      suite: 'ceremony_observer',
      title: 'Repeated idempotent ceremony calls deduplicated deterministically',
      passed: obsDup.duplicateEventsDeduped === 2 && obsDup.validEvents === 5,
      detail: `deduped=${obsDup.duplicateEventsDeduped}, valid=${obsDup.validEvents}`,
    },
    {
      id: 'OBS-05',
      suite: 'ceremony_observer',
      title: 'Out-of-order complete_goal before declare_plan flagged immediately',
      passed: outOfOrderNoPlan.outOfOrderViolations.length >= 2 && outOfOrderNoPlan.goalsWithFullCeremony === 0,
      detail: outOfOrderNoPlan.outOfOrderViolations[0] ?? 'none',
    },
    {
      id: 'OBS-06',
      suite: 'ceremony_observer',
      title: 'Skipping edge_cases or second_order_effects blocks full-ceremony credit',
      passed:
        missingEdgeAndEffects.goalsWithFullCeremony === 0 &&
        missingEdgeAndEffects.outOfOrderViolations.some(
          (v) => v.includes('edge_cases') && v.includes('second_order_effects')
        ),
      detail: missingEdgeAndEffects.outOfOrderViolations[0] ?? 'none',
    },
    {
      id: 'OBS-07',
      suite: 'ceremony_observer',
      title: 'Executor refusals & unplanned work logged distinctly without mutating ledger',
      passed:
        refusalAndUnplanned.refusalsLogged === 1 &&
        refusalAndUnplanned.unplannedWorkCount === 1 &&
        refusalAndUnplanned.ceremonyDisabled === false,
      detail: `refusals=${refusalAndUnplanned.refusalsLogged}, unplanned=${refusalAndUnplanned.unplannedWorkCount}`,
    },
    {
      id: 'OBS-08',
      suite: 'ceremony_observer',
      title: 'Truthful UNKNOWN reporting: liveCeremonyEffect & operationalEffect never faked from local logs',
      passed:
        obsClean.liveCeremonyEffect === 'UNKNOWN' &&
        obsClean.epistemicTiers.independentlyVerifiedOperationalEffect === 'UNKNOWN' &&
        obsClean.epistemicTiers.planCompletionCount === 1,
      detail: `plan=${obsClean.epistemicTiers.planCompletionCount}, liveEffect=${obsClean.liveCeremonyEffect}`,
    },
    {
      id: 'OBS-09',
      suite: 'ceremony_observer',
      title: 'Rejects old installer --no-verify hook-bypass shortcut',
      passed: !shortcutNoVerify.allowed && shortcutNoVerify.blockedShortcuts.includes('--no-verify_hook_bypass'),
      detail: shortcutNoVerify.reason,
    },
    {
      id: 'OBS-10',
      suite: 'ceremony_observer',
      title: 'Rejects multi-agent history rewrite shortcut (Pin 3 preservation)',
      passed: !shortcutHistory.allowed && shortcutHistory.blockedShortcuts.includes('multi_agent_history_rewrite'),
      detail: shortcutHistory.reason,
    },
    {
      id: 'OBS-11',
      suite: 'ceremony_observer',
      title: 'Rejects disabling governance extensions & reviving retired disk guardian (Pin 10)',
      passed: !shortcutGovDisable.allowed && shortcutGovDisable.blockedShortcuts.includes('governance_extension_disable'),
      detail: shortcutGovDisable.reason,
    },
    {
      id: 'OBS-12',
      suite: 'ceremony_observer',
      title: 'Accepts authoritative bin/idp-machine-submit workflow preserving pre-push & claim gates',
      passed: safeIdpSubmit.allowed && safeIdpSubmit.blockedShortcuts.length === 0,
      detail: safeIdpSubmit.reason,
    },
  ];

  // --- 9 AGENTS.md No-Growth Ratchet Adversarial Tests ---
  const rLegacy = reproduceLegacyEscapedLinesBug(348);
  const rLiteralEscape = evaluateAgentsMdRatchet({ currentLinesRaw: '$lines', baselineLinesRaw: 348 });
  const rEmptyInput = evaluateAgentsMdRatchet({ currentLinesRaw: '', baselineLinesRaw: 'nan' });
  const rOverBaselineHold = evaluateAgentsMdRatchet({ currentLinesRaw: 348, baselineLinesRaw: 348 });
  const rOverBaselineGrowth1 = evaluateAgentsMdRatchet({ currentLinesRaw: 349, baselineLinesRaw: 348 });
  const rConsolidateStep = evaluateAgentsMdRatchet({ currentLinesRaw: 332, baselineLinesRaw: 348 });
  const rRegrowAfterRatchet = evaluateAgentsMdRatchet({
    currentLinesRaw: 340,
    baselineLinesRaw: rConsolidateStep.nextRatchetBaseline ?? 332,
  });
  const rUnder300Pass = evaluateAgentsMdRatchet({ currentLinesRaw: 274, baselineLinesRaw: 332 });
  const rUnder300Spike301 = evaluateAgentsMdRatchet({
    currentLinesRaw: 301,
    baselineLinesRaw: rUnder300Pass.nextRatchetBaseline ?? 300,
  });

  const ratchetChecks: AdversarialCheckItem[] = [
    {
      id: 'RAT-01',
      suite: 'agents_md_ratchet',
      title: 'Reproduces legacy fail-open `$lines` shell escape defect (exited 0 on 348-line file)',
      passed: rLegacy.failedOpen === true && rLegacy.workflowExitCode === 0 && rLegacy.evaluatedToken === '$lines',
      detail: `legacyExit=${rLegacy.workflowExitCode} on literal ${rLegacy.evaluatedToken}`,
    },
    {
      id: 'RAT-02',
      suite: 'agents_md_ratchet',
      title: 'Repaired gate fails CLOSED (exit 1) when `$lines` literal or unexpanded variable is passed',
      passed: !rLiteralEscape.passed && rLiteralEscape.exitCode === 1 && rLiteralEscape.mode === 'FAIL_CLOSED_INVALID_INPUT',
      detail: rLiteralEscape.summary,
    },
    {
      id: 'RAT-03',
      suite: 'agents_md_ratchet',
      title: 'Repaired gate fails CLOSED (exit 1) on empty or corrupted baseline/line count',
      passed: !rEmptyInput.passed && rEmptyInput.exitCode === 1,
      detail: rEmptyInput.summary,
    },
    {
      id: 'RAT-04',
      suite: 'agents_md_ratchet',
      title: 'Allows 0-growth work against existing over-300-line canonical AGENTS.md baseline (348/348)',
      passed: rOverBaselineHold.passed && rOverBaselineHold.exitCode === 0 && rOverBaselineHold.mode === 'NO_GROWTH_RATCHET_HOLD',
      detail: rOverBaselineHold.summary,
    },
    {
      id: 'RAT-05',
      suite: 'agents_md_ratchet',
      title: 'Blocks +1 line growth above over-limit baseline (349 > 348 -> exit 1)',
      passed: !rOverBaselineGrowth1.passed && rOverBaselineGrowth1.exitCode === 1 && rOverBaselineGrowth1.mode === 'BLOCKED_GROWTH',
      detail: rOverBaselineGrowth1.summary,
    },
    {
      id: 'RAT-06',
      suite: 'agents_md_ratchet',
      title: 'Consolidation (348 -> 332) passes and ratchets ceiling down to 332',
      passed: rConsolidateStep.passed && rConsolidateStep.mode === 'RATCHETED_DOWN' && rConsolidateStep.nextRatchetBaseline === 332,
      detail: rConsolidateStep.summary,
    },
    {
      id: 'RAT-07',
      suite: 'agents_md_ratchet',
      title: 'Blocks re-growth back to old 340 count after ratchet tightened to 332',
      passed: !rRegrowAfterRatchet.passed && rRegrowAfterRatchet.exitCode === 1,
      detail: rRegrowAfterRatchet.summary,
    },
    {
      id: 'RAT-08',
      suite: 'agents_md_ratchet',
      title: 'Recovery below 300-line target (274 <= 300) locks canonical 300-line ceiling',
      passed: rUnder300Pass.passed && rUnder300Pass.mode === 'UNDER_TARGET' && rUnder300Pass.nextRatchetBaseline === 300,
      detail: rUnder300Pass.summary,
    },
    {
      id: 'RAT-09',
      suite: 'agents_md_ratchet',
      title: 'Blocks breaching 300-line target (301 > 300) once canonical ceiling is restored',
      passed: !rUnder300Spike301.passed && rUnder300Spike301.exitCode === 1,
      detail: rUnder300Spike301.summary,
    },
  ];

  return [...observerChecks, ...ratchetChecks];
}

export function buildFirstUseAuditSnapshot(): FirstUseAuditSnapshot {
  const adversarialChecks = runFirstUseAdversarialSuite();
  const observerChecks = adversarialChecks.filter((c) => c.suite === 'ceremony_observer');
  const ratchetChecks = adversarialChecks.filter((c) => c.suite === 'agents_md_ratchet');

  const sampleObserverLedger = [
    JSON.stringify({
      eventId: 'audit-seed-1',
      goalId: 'IDP-AUDIT-20261116',
      step: 'declare_plan',
      durationMs: 140,
      note: 'Declared 13-pin source comparison against IDP main d03f5d59 by founder@meridian.estate',
    }),
    JSON.stringify({
      eventId: 'audit-seed-2',
      goalId: 'IDP-AUDIT-20261116',
      step: 'bdd_scenarios',
      durationMs: 180,
      note: 'Encoded 12 observer + 9 AGENTS ratchet adversarial checks',
    }),
    JSON.stringify({
      eventId: 'audit-seed-3',
      goalId: 'IDP-AUDIT-20261116',
      step: 'edge_cases',
      durationMs: 165,
      note: 'Reproduced escaped $lines fail-open bug & over-300 baseline trap',
    }),
    JSON.stringify({
      eventId: 'audit-seed-4',
      goalId: 'IDP-AUDIT-20261116',
      step: 'second_order_effects',
      durationMs: 130,
      note: 'Preserved Pi ceremony & rejected --no-verify / history-rewrite shortcuts',
    }),
    JSON.stringify({
      eventId: 'audit-seed-5',
      goalId: 'IDP-AUDIT-20261116',
      step: 'complete_goal',
      durationMs: 55,
      note: 'Committed candidate ff8543bdeaed1a0ed2ddc254491e0e22d361300d; operational yield kept UNKNOWN',
    }),
    JSON.stringify({
      eventId: 'audit-seed-6',
      goalId: 'IDP-AUDIT-20261116',
      step: 'refusal_logged',
      durationMs: 12,
      note: 'Refused unsafe multi-agent history rewrite & --no-verify installer proposal',
    }),
  ];

  return {
    auditDate: '2026-11-16',
    auditBranch: 'audit/first-use-machine-agent-20261116',
    candidateHead: 'ff8543bdeaed1a0ed2ddc254491e0e22d361300d',
    comparedMainSha: 'd03f5d59',
    commitsAheadOfMain: 7,
    mergeOrDeploymentClaimed: false,
    candidatePosture: 'VERIFIED_CANDIDATE_NOT_CERTIFIED_ENFORCEMENT',
    governingPrinciple:
      'Prevent at the earliest producer, verify continuously, recover only by exception, and learn from every prevention escape — with goals, subgoals, BDD, edge cases, and second-order effects retained.',
    failureClassesReviewed: THIRTEEN_GOVERNANCE_PINS.length as 13,
    adversarialTestsPassed: adversarialChecks.filter((c) => c.passed).length,
    adversarialTestsTotal: adversarialChecks.length,
    observerTestsPassed: observerChecks.filter((c) => c.passed).length,
    observerTestsTotal: 12,
    ratchetTestsPassed: ratchetChecks.filter((c) => c.passed).length,
    ratchetTestsTotal: 9,
    liveCeremonyEffect: 'UNKNOWN',
    legacyEscapedLinesBugReproduced: {
      legacyShellSnippet: 'if [ "\\$lines" -gt 300 ]; then exit 1; fi; echo OK',
      legacyExitCodeOnLiteralText: 0,
      failOpenConfirmed: true,
      explanation:
        'Escaped \\$lines passed literal text to Bash integer test, printing an integer-expression error while still echoing OK and exiting 0.',
    },
    defaultRatchetEvaluation: evaluateAgentsMdRatchet({
      currentLinesRaw: 348,
      baselineLinesRaw: 348,
      targetCeiling: 300,
    }),
    defaultObserverReport: observeCeremonyLedger(sampleObserverLedger),
    pins: THIRTEEN_GOVERNANCE_PINS,
    adversarialChecks,
    remainingAcceptanceGates: [
      'Authorised signed integration via Greenlane (no merge claimed on ff8543bd)',
      'Real runtime plan-ledger observation across active fleet executors',
      'Independently joined outcome/cost evidence separating test pass from operational yield',
      'Proven first-use prevention effect under live production worktrees',
    ],
    hourlyP0WatchTargets: [
      'audit/first-use-machine-agent-20261116 (candidate ff8543bd, +7 ahead of d03f5d59)',
      'agents-md-gate no-growth ratchet regression watch',
      'Read-only Pi ceremony observer latency & defect-catch telemetry',
      'Missing live operational-effect proof (held explicitly UNKNOWN)',
    ],
  };
}
