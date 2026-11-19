/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * DoF (Degrees-of-Freedom) Capability Lease Governance, Genesis Rule Zero,
 * and IDP (Identity, Delegation & Provenance) History Engine
 *
 * Models branch wip/DOF-GOVERNANCE-v1 @ c3e0822 (GEN-NET-006 / GEN-DOF-001).
 */

import { computeDeterministicHash } from './epistemicCalculus';

export type DofLevel = 'L0' | 'L1' | 'L2' | 'L3';

export type CriticalComponentId =
  | 'DISK-01'
  | 'MEMORY-01'
  | 'XREC-GATE-01'
  | 'ROUTER-01';

export type ProbeStatus = 'PASS' | 'FAIL' | 'CANNOT_RUN';

export interface DualProbeReading {
  componentId: CriticalComponentId;
  /** Method A: Out-of-Band Kernel / Filesystem / Manifest check */
  methodAStatus: ProbeStatus;
  methodADetail: string;
  /** Method B: In-Band Semantic / SQLite / Canary check */
  methodBStatus: ProbeStatus;
  methodBDetail: string;
}

export interface RepairStepDefinition {
  stepIndex: number;
  code: string;
  title: string;
  commandSummary: string;
  expectedPostState: string;
}

export interface RepairReceipt {
  stepIndex: number;
  code: string;
  executedAt: string;
  preStateHash: string;
  postStateHash: string;
  regressionDetected: boolean;
  receiptDigest: string;
}

export interface XrecRefusalEnvelope {
  schema: 'xrec-mcp.refusal-envelope.v1';
  status: 'REFUSED_CAPABILITY_LEASE_INSUFFICIENT';
  leaseEpoch: number;
  activeDoFLevel: DofLevel;
  attemptedTool: string;
  surface: 'agent-cli' | 'web-chat' | 'background-worker';
  failingComponent: CriticalComponentId | 'PROBE-RUNNER';
  prescribedProtocol: string;
  allowedSurfaces: string[];
  hysteresisState: {
    consecutivePasses: number;
    requiredPassesForRestore: 3;
    lastProbeDigest: string;
  };
  escalationState: {
    blockedAttemptsInEpisode: number;
    crossSurfaceBypassDetected: boolean;
    redCardIssued: boolean;
  };
  directive: string;
}

export interface IdpHistoryEntry {
  entryId: string;
  timestamp: string;
  commitOrEpoch: string;
  actorPrincipal: string;
  delegationScope: string;
  dofTransition: string;
  xrecGrade: 'A-GRADE-SEALED' | 'CANDIDATE-BRANCH' | 'OTT-SIGNED';
  merkleWitness: string;
  summary: string;
}

export interface GenesisRuleEntry {
  ruleId: string;
  title: string;
  ratificationStatus: 'RATIFIED_MAIN' | 'CANDIDATE_WIP';
  branchRef: string;
  commitHash: string;
  constitutionalText: string;
  enforcedInvariant: string;
}

export interface DofEpisodeState {
  episodeId: string;
  leaseEpoch: number;
  activeLevel: DofLevel;
  failingComponent: CriticalComponentId | null;
  prescribedProtocol: string | null;
  consecutiveProbePasses: number;
  requiredPassesForRestore: 3;
  completedRepairSteps: RepairReceipt[];
  refusalLog: XrecRefusalEnvelope[];
  crossSurfaceBypassCount: number;
  redCardIssued: boolean;
  founderOttOverrideActive: boolean;
  founderOttTokenDigest: string | null;
  queuedDependentTickets: string[];
  xrecSealedDigest: string;
}

export const MEMORY_01_REPAIR_PROTOCOL: RepairStepDefinition[] = [
  {
    stepIndex: 1,
    code: 'VAULT_CHECK',
    title: 'Verify Restic Vault Mount & Snapshot Manifest Signature',
    commandSummary: 'restic check --read-data-subset=1/5 && verify-manifest-sig',
    expectedPostState: 'vault_mounted=true; manifest_sig=VALID',
  },
  {
    stepIndex: 2,
    code: 'DB_INTEGRITY',
    title: 'Run SQLite PRAGMA integrity_check & Isolate Corrupt B-Tree Pages',
    commandSummary: 'sqlite3 /estate/memory/spine.db "PRAGMA integrity_check;"',
    expectedPostState: 'corrupt_pages_isolated=[page_419, page_420]',
  },
  {
    stepIndex: 3,
    code: 'WAL_CHECKPOINT',
    title: 'Quarantine Unaligned WAL Frames & Truncate Checkpoints',
    commandSummary: 'sqlite3 /estate/memory/spine.db "PRAGMA wal_checkpoint(TRUNCATE);"',
    expectedPostState: 'wal_frames_aligned=true; orphan_shm=PURGED',
  },
  {
    stepIndex: 4,
    code: 'POINTER_AUDIT',
    title: 'Verify IDP Head Pointers Against Last Signed xrec Merkle Root',
    commandSummary: 'xrec-mcp verify-pointers --against-head 0xd12f04bf',
    expectedPostState: 'idp_head_consistent=true; divergence=0',
  },
  {
    stepIndex: 5,
    code: 'RESTIC_RESTORE',
    title: 'Restore Verified Restic Block Snapshot for Corrupt Spine Pages',
    commandSummary: 'restic restore latest --target /estate/memory/staging && atomic-swap',
    expectedPostState: 'spine_sha256=0x88e4a102; pragma_integrity=OK',
  },
];

export const INITIAL_GENESIS_RULES: GenesisRuleEntry[] = [
  {
    ruleId: 'GEN-DOF-001',
    title: 'Rule Zero: Capability Lease & Unproven Component Invariant',
    ratificationStatus: 'CANDIDATE_WIP',
    branchRef: 'wip/DOF-GOVERNANCE-v1',
    commitHash: 'c3e0822',
    constitutionalText:
      'An estate whose critical components are unproven grants no freedom. Capabilities are leased, never possessed. The estate owns the action space; agents rent subsets of it. Health decides the rent.',
    enforcedInvariant:
      'ProbeFailed(C) => Lease(Session) subseteq {Diagnostics, RepairProtocol(C), XrecReceipt}',
  },
  {
    ruleId: 'GEN-DOF-002',
    title: '1-Down / 3-Up Anti-Flapping Hysteresis & Proof-Only Restoration',
    ratificationStatus: 'CANDIDATE_WIP',
    branchRef: 'wip/DOF-GOVERNANCE-v1',
    commitHash: 'c3e0822',
    constitutionalText:
      'A capability level drops on 1 confirmed dual-method probe failure and restores only when the probe passes 3x consecutively with canary verification — never by elapsed time, never by agent self-assessment.',
    enforcedInvariant:
      'Restore(L_k -> L_0) iff ConsecutiveVerifiedPasses(C) >= 3',
  },
  {
    ruleId: 'GEN-NET-006',
    title: 'Multi-Agent Candidate Branch & SSH ls-remote Ratification Protocol',
    ratificationStatus: 'RATIFIED_MAIN',
    branchRef: 'main',
    commitHash: 'a91f40e',
    constitutionalText:
      'Constitutional and governance specifications must be pushed to a candidate wip/* branch over SSH, verified via git ls-remote, and peer-reviewed across estate agents before ratification into main.',
    enforcedInvariant:
      'MergeToMain(Spec) requires VerifiedLsRemote(Commit) AND MultiAgentRatification',
  },
];

export const INITIAL_IDP_HISTORY: IdpHistoryEntry[] = [
  {
    entryId: 'IDP-2026-1104-004',
    timestamp: '2026-11-04T01:05:00Z',
    commitOrEpoch: 'wip/DOF-GOVERNANCE-v1 @ c3e0822',
    actorPrincipal: 'principal:architect-agent@argon-sync.estate',
    delegationScope: 'GEN-NET-006 Candidate Specification Push',
    dofTransition: 'L0 -> L0 (Spec Modeled & Edge-Cased)',
    xrecGrade: 'CANDIDATE-BRANCH',
    merkleWitness: '0xc3e0822f9104ab77',
    summary:
      'Modeled docs/DOF-GOVERNANCE-v1.md (+88 lines) covering L0-L3 capability leasing, MEMORY-01 proving test, and 8 operational edge cases. Pushed over SSH and ls-remote verified.',
  },
  {
    entryId: 'IDP-2026-1103-003',
    timestamp: '2026-11-03T21:40:12Z',
    commitOrEpoch: 'EPOCH-40910',
    actorPrincipal: 'principal:worker-agent-04@estate.internal',
    delegationScope: 'MEMORY-01 Spine Incident & Recovery Episode',
    dofTransition: 'L0 -> L2 (MEMORY-01) -> L0 (3x Probe Pass)',
    xrecGrade: 'A-GRADE-SEALED',
    merkleWitness: '0x88f12c904e117a02',
    summary:
      'Memory-spine WAL corruption detected at session start. Lease narrowed to L2 (MEMORY-01 only). Refused 1 task write attempt; executed 5-step restic + WAL recovery; restored to L0 after 3 consecutive probe passes.',
  },
  {
    entryId: 'IDP-2026-1102-002',
    timestamp: '2026-11-02T14:18:05Z',
    commitOrEpoch: 'EPOCH-40874',
    actorPrincipal: 'principal:web-chat-session@estate.internal',
    delegationScope: 'Cross-Surface Bypass Interception (ROUTER-01)',
    dofTransition: 'L2 (ROUTER-01) -> L3 (FROZEN_RED_CARD)',
    xrecGrade: 'A-GRADE-SEALED',
    merkleWitness: '0x44a901bc77d23109',
    summary:
      'Agent attempted to bypass CLI L2 router freeze by dispatching task payload via web-chat surface. xrec-mcp unified gate intercepted attempt, incremented escalation counter, froze session at L3, and emitted red card.',
  },
  {
    entryId: 'IDP-2026-1030-001',
    timestamp: '2026-10-30T09:00:00Z',
    commitOrEpoch: 'main @ a91f40e',
    actorPrincipal: 'principal:founder@fortress.estate',
    delegationScope: 'GEN-NET-006 Constitutional Baseline',
    dofTransition: 'GENESIS_BOOTSTRAP -> L0',
    xrecGrade: 'A-GRADE-SEALED',
    merkleWitness: '0xa91f40e00192bc31',
    summary:
      'Established IDP (Identity, Delegation & Provenance) root ledger and xrec-mcp monotonic fencing-token enforcement across all estate surfaces.',
  },
];

export const EDGE_CASE_MATRIX: Array<{
  id: string;
  number: number;
  title: string;
  triggerCondition: string;
  dofResolution: string;
  targetLevel: DofLevel;
}> = [
  {
    id: 'EC-01',
    number: 1,
    title: 'False-Positive Probes (Single-Method Anomaly)',
    triggerCondition: 'Method A fails (transient stat lag) while Method B (SQLite query) passes.',
    dofResolution:
      'Two orthogonal probe methods must agree before dropping below L1. Disagreement holds session at L1 (read/diagnose only) and triggers immediate re-probe.',
    targetLevel: 'L1',
  },
  {
    id: 'EC-02',
    number: 2,
    title: 'Probe-Cannot-Run (Bootstrap Failure)',
    triggerCondition: 'Probe runner binary or socket is unreachable at session start.',
    dofResolution:
      'Fail-closed at L1. Session leases PROBE-BOOTSTRAP-00 only; zero task capabilities granted until probe runner self-test succeeds.',
    targetLevel: 'L1',
  },
  {
    id: 'EC-03',
    number: 3,
    title: 'Cascading Failures (Priority DAG Isolation)',
    triggerCondition: 'DISK-01 and ROUTER-01 fail simultaneously, or ROUTER-01 fails during backup.',
    dofResolution:
      'Priority-ordered walk (DISK-01 P0 -> MEMORY-01 P1 -> XREC-GATE-01 P2 -> ROUTER-01 P3) with per-component freezing so a router outage never blocks restic disk backups.',
    targetLevel: 'L2',
  },
  {
    id: 'EC-04',
    number: 4,
    title: 'Cross-Surface Bypass (CLI to Web-Chat)',
    triggerCondition: 'Agent blocked in CLI attempts the same task action via web-chat or worker API.',
    dofResolution:
      'Single unified xrec-mcp gate across all surfaces. Blocked web-chat attempt is refused, sealed in xrec, and escalates session to L3 Frozen.',
    targetLevel: 'L3',
  },
  {
    id: 'EC-05',
    number: 5,
    title: 'Founder OTT Override (Signed Emergency Lease)',
    triggerCondition: 'Founder issues a signed One-Time Token (OTT) during an active L2/L3 incident.',
    dofResolution:
      'Grants a single-epoch scoped lease attributed to principal:founder@estate. Sealed permanently as an OTT-attributed xrec record in IDP history.',
    targetLevel: 'L0',
  },
  {
    id: 'EC-06',
    number: 6,
    title: 'Probe Flapping (Pass-Fail-Pass Oscillation)',
    triggerCondition: 'Component passes probe 1/3 and 2/3, then fails on probe 3/3.',
    dofResolution:
      'Drop on 1 failure, restore only on 3 consecutive passes (1-down / 3-up hysteresis). Failure on pass #3 resets consecutive counter to 0/3.',
    targetLevel: 'L2',
  },
  {
    id: 'EC-07',
    number: 7,
    title: 'Mid-Incident Session Starts (No Grandfathering)',
    triggerCondition: 'New agent session spawns while estate is already at L2 for MEMORY-01.',
    dofResolution:
      'Zero grandfathering. Session reads shared level state file before onboarding prompt injection and starts restricted at L2.',
    targetLevel: 'L2',
  },
  {
    id: 'EC-08',
    number: 8,
    title: 'Repair-Makes-It-Worse (Step Regression)',
    triggerCondition: 'A repair step increases page corruption or violates pre/post state invariant.',
    dofResolution:
      'Auto-stop immediately, transition L2 -> L3 Frozen, convert queued work to dependent tickets, and emit red card with the exact state diff.',
    targetLevel: 'L3',
  },
];

/**
 * Creates a clean initial L0 DoF episode state.
 */
export function createInitialDofEpisodeState(): DofEpisodeState {
  return {
    episodeId: 'EP-2026-DOF-901',
    leaseEpoch: 40912,
    activeLevel: 'L0',
    failingComponent: null,
    prescribedProtocol: null,
    consecutiveProbePasses: 3,
    requiredPassesForRestore: 3,
    completedRepairSteps: [],
    refusalLog: [],
    crossSurfaceBypassCount: 0,
    redCardIssued: false,
    founderOttOverrideActive: false,
    founderOttTokenDigest: null,
    queuedDependentTickets: [],
    xrecSealedDigest: computeDeterministicHash('EP-2026-DOF-901::L0::INIT'),
  };
}

/**
 * Evaluates a dual-method probe reading and transitions the DoF episode state.
 * Enforces Edge Case 1 (False-positive requires 2 probe methods to agree before dropping below L1),
 * Edge Case 2 (Probe-cannot-run fails closed at L1), and Edge Case 6 (1-down / 3-up hysteresis).
 */
export function evaluateProbeTransition(
  state: DofEpisodeState,
  reading: DualProbeReading
): DofEpisodeState {
  const next = structuredClone(state);
  next.leaseEpoch += 1;

  // Edge Case 2: Probe cannot run -> fail-closed at L1
  if (
    reading.methodAStatus === 'CANNOT_RUN' ||
    reading.methodBStatus === 'CANNOT_RUN'
  ) {
    next.activeLevel = next.activeLevel === 'L3' ? 'L3' : 'L1';
    next.failingComponent = reading.componentId;
    next.prescribedProtocol = 'PROBE-BOOTSTRAP-00';
    next.consecutiveProbePasses = 0;
    next.xrecSealedDigest = computeDeterministicHash(
      `${next.episodeId}::${next.leaseEpoch}::L1_BOOTSTRAP`
    );
    return next;
  }

  // Both methods fail -> Confirmed component failure -> Drop to L2 immediately (1-down)
  if (reading.methodAStatus === 'FAIL' && reading.methodBStatus === 'FAIL') {
    next.activeLevel = next.activeLevel === 'L3' ? 'L3' : 'L2';
    next.failingComponent = reading.componentId;
    next.prescribedProtocol = reading.componentId;
    next.consecutiveProbePasses = 0;
    next.founderOttOverrideActive = false;
    next.xrecSealedDigest = computeDeterministicHash(
      `${next.episodeId}::${next.leaseEpoch}::L2::${reading.componentId}`
    );
    return next;
  }

  // Edge Case 1: Only one probe method fails (False-Positive Disagreement) -> Narrow to L1 Diagnose-Only
  if (reading.methodAStatus === 'FAIL' || reading.methodBStatus === 'FAIL') {
    if (next.activeLevel === 'L0') {
      next.activeLevel = 'L1';
    }
    next.failingComponent = reading.componentId;
    next.prescribedProtocol = `DIAGNOSE-${reading.componentId}`;
    next.consecutiveProbePasses = 0;
    next.xrecSealedDigest = computeDeterministicHash(
      `${next.episodeId}::${next.leaseEpoch}::L1_DISAGREE::${reading.componentId}`
    );
    return next;
  }

  // Both methods PASS:
  // If we were at L2 for MEMORY-01, verify that all prescribed repair steps were completed
  // before allowing probe passes to restore L0 ("no path from probe failed to task work without memory fixed").
  if (
    next.activeLevel === 'L2' &&
    next.failingComponent === 'MEMORY-01' &&
    next.completedRepairSteps.length < MEMORY_01_REPAIR_PROTOCOL.length
  ) {
    // Probe cannot restore L0 until the prescribed repair protocol receipts are sealed
    return next;
  }

  if (next.activeLevel === 'L3' && !next.founderOttOverrideActive) {
    // L3 requires explicit unfreeze or completed repair before hysteresis restoration
    return next;
  }

  next.consecutiveProbePasses = Math.min(3, next.consecutiveProbePasses + 1);

  if (next.consecutiveProbePasses >= 3) {
    next.activeLevel = 'L0';
    next.failingComponent = null;
    next.prescribedProtocol = null;
  }

  next.xrecSealedDigest = computeDeterministicHash(
    `${next.episodeId}::${next.leaseEpoch}::PASS_${next.consecutiveProbePasses}`
  );
  return next;
}

/**
 * Attempts to execute an agent action under the current DoF lease.
 * Enforces the core invariant: below L0, task actions are structurally refused with a
 * machine-readable xrec-mcp Refusal Envelope, and cross-surface bypass attempts escalate to L3.
 */
export function attemptAgentAction(
  state: DofEpisodeState,
  action: {
    toolName: string;
    category: 'task-mutation' | 'diagnostics-read' | 'repair-step';
    surface?: 'agent-cli' | 'web-chat' | 'background-worker';
    repairStepIndex?: number;
    simulateRegression?: boolean;
  }
): {
  allowed: boolean;
  nextState: DofEpisodeState;
  refusalEnvelope: XrecRefusalEnvelope | null;
  statusMessage: string;
} {
  const next = structuredClone(state);
  const surface = action.surface || 'agent-cli';

  // L0 or active Founder OTT Override permits all actions
  if (next.activeLevel === 'L0' || next.founderOttOverrideActive) {
    return {
      allowed: true,
      nextState: next,
      refusalEnvelope: null,
      statusMessage: `ALLOWED (${next.founderOttOverrideActive ? 'Founder OTT Lease' : 'L0 Full Lease'}): Executed ${action.toolName}.`,
    };
  }

  // Diagnostics reads are permitted in L1 and L2
  if (action.category === 'diagnostics-read' && next.activeLevel !== 'L3') {
    return {
      allowed: true,
      nextState: next,
      refusalEnvelope: null,
      statusMessage: `ALLOWED (${next.activeLevel} Diagnostic Surface): Executed ${action.toolName}.`,
    };
  }

  // Prescribed repair step execution in L2
  if (action.category === 'repair-step' && next.activeLevel === 'L2') {
    const stepDef =
      MEMORY_01_REPAIR_PROTOCOL.find(
        (s) => s.stepIndex === action.repairStepIndex
      ) || MEMORY_01_REPAIR_PROTOCOL[next.completedRepairSteps.length];

    if (!stepDef) {
      return {
        allowed: true,
        nextState: next,
        refusalEnvelope: null,
        statusMessage: 'All prescribed MEMORY-01 repair steps are already receipted.',
      };
    }

    const preHash = computeDeterministicHash(
      `PRE::${next.episodeId}::STEP_${stepDef.stepIndex}`
    ).slice(0, 12);
    const postHash = computeDeterministicHash(
      `POST::${next.episodeId}::STEP_${stepDef.stepIndex}::${action.simulateRegression ? 'CORRUPT' : 'OK'}`
    ).slice(0, 12);

    const receipt: RepairReceipt = {
      stepIndex: stepDef.stepIndex,
      code: stepDef.code,
      executedAt: '2026-11-04T17:15:00Z',
      preStateHash: preHash,
      postStateHash: postHash,
      regressionDetected: Boolean(action.simulateRegression),
      receiptDigest: computeDeterministicHash(`${preHash}->${postHash}`),
    };

    next.completedRepairSteps.push(receipt);
    next.leaseEpoch += 1;

    // Edge Case 8: Repair-makes-it-worse -> auto-stop at L3 + Red Card
    if (action.simulateRegression) {
      next.activeLevel = 'L3';
      next.redCardIssued = true;
      next.consecutiveProbePasses = 0;
      next.queuedDependentTickets.push(
        `TICKET-ESC-${next.leaseEpoch}: Halted on ${stepDef.code} regression (${preHash} -> ${postHash})`
      );
      next.xrecSealedDigest = computeDeterministicHash(
        `${next.episodeId}::L3_REGRESSION::${receipt.receiptDigest}`
      );
      return {
        allowed: false,
        nextState: next,
        refusalEnvelope: null,
        statusMessage: `AUTO-STOP (Edge Case 8 — Repair Regression): Step ${stepDef.code} degraded component health. Session frozen at L3 and RED CARD issued.`,
      };
    }

    next.xrecSealedDigest = computeDeterministicHash(
      `${next.episodeId}::REPAIR_${stepDef.code}::${receipt.receiptDigest}`
    );
    return {
      allowed: true,
      nextState: next,
      refusalEnvelope: null,
      statusMessage: `REPAIR RECEIPT SEALED: Step ${stepDef.stepIndex} (${stepDef.code}) completed [${preHash} -> ${postHash}].`,
    };
  }

  // Otherwise: REFUSED! ("Note and move on" is structurally impossible)
  next.leaseEpoch += 1;
  const isCrossSurface = surface !== 'agent-cli';
  if (isCrossSurface) {
    next.crossSurfaceBypassCount += 1;
  }

  const totalBlocked = next.refusalLog.length + 1;
  // Edge Case 4: Cross-surface bypass or repeated blocked attempts escalate to L3 Frozen
  if (isCrossSurface || totalBlocked >= 2 || next.activeLevel === 'L3') {
    next.activeLevel = 'L3';
    next.redCardIssued = true;
    next.queuedDependentTickets.push(
      `TICKET-DEP-${next.leaseEpoch}: Deferred ${action.toolName} (Blocked on ${next.failingComponent || 'MEMORY-01'})`
    );
  }

  const allowedSurfaces =
    next.activeLevel === 'L1'
      ? ['diagnostics.read_probe_state', 'xrec.append_diagnostic_log']
      : next.activeLevel === 'L2'
        ? [
            'diagnostics.read_probe_state',
            `repair.execute_step:${next.prescribedProtocol || 'MEMORY-01'}`,
            'xrec.append_repair_receipt',
          ]
        : ['xrec.emergency_halt_snapshot'];

  const envelope: XrecRefusalEnvelope = {
    schema: 'xrec-mcp.refusal-envelope.v1',
    status: 'REFUSED_CAPABILITY_LEASE_INSUFFICIENT',
    leaseEpoch: next.leaseEpoch,
    activeDoFLevel: next.activeLevel,
    attemptedTool: action.toolName,
    surface,
    failingComponent: next.failingComponent || 'MEMORY-01',
    prescribedProtocol: next.prescribedProtocol || 'MEMORY-01',
    allowedSurfaces,
    hysteresisState: {
      consecutivePasses: next.consecutiveProbePasses,
      requiredPassesForRestore: 3,
      lastProbeDigest: next.xrecSealedDigest.slice(0, 18),
    },
    escalationState: {
      blockedAttemptsInEpisode: totalBlocked,
      crossSurfaceBypassDetected: isCrossSurface || next.crossSurfaceBypassCount > 0,
      redCardIssued: next.redCardIssued,
    },
    directive: `Action "${action.toolName}" on surface "${surface}" refused: capability not in active ${next.activeLevel} lease. Execute prescribed protocol ${next.prescribedProtocol || 'MEMORY-01'} or abandon session.`,
  };

  next.refusalLog.unshift(envelope);
  next.xrecSealedDigest = computeDeterministicHash(
    `${next.episodeId}::REFUSED::${envelope.leaseEpoch}::${action.toolName}`
  );

  return {
    allowed: false,
    nextState: next,
    refusalEnvelope: envelope,
    statusMessage: envelope.directive,
  };
}

/**
 * Edge Case 5: Applies a cryptographically signed Founder One-Time Token (OTT) override.
 */
export function applyFounderOttOverride(
  state: DofEpisodeState,
  founderPrincipal: string,
  reason: string
): DofEpisodeState {
  const next = structuredClone(state);
  next.leaseEpoch += 1;
  next.founderOttOverrideActive = true;
  next.activeLevel = 'L0';
  next.redCardIssued = false;
  next.founderOttTokenDigest = computeDeterministicHash(
    `FOUNDER_OTT::${founderPrincipal}::${next.leaseEpoch}::${reason}`
  );
  next.xrecSealedDigest = computeDeterministicHash(
    `${next.episodeId}::OTT_SEALED::${next.founderOttTokenDigest}`
  );
  return next;
}

export interface AuditCycleTrendPoint {
  cycleLabel: string;
  cycleOffset: number;
  healthScore: number;
  consecutivePasses: number;
  leaseLevel: DofLevel;
  probeOutcome: 'PASS' | 'FAIL' | 'ANOMALY';
}

export interface SystemProbeHealthRow {
  componentId: CriticalComponentId;
  priorityTier: 'P0' | 'P1' | 'P2' | 'P3';
  subsystemName: string;
  methodAName: string;
  methodAStatus: ProbeStatus;
  methodBName: string;
  methodBStatus: ProbeStatus;
  agreementState: 'AGREED_PASS' | 'AGREED_FAIL' | 'DISAGREE_L1_HOLD' | 'BOOTSTRAP_FAIL';
  activeLeaseLevel: DofLevel;
  rentedActionSpace: string;
  failureCount: number;
  consecutiveRestorePasses: number;
  requiredRestorePasses: 3;
  lastProbeLatencyMs: number;
  lastProbeTimestamp: string;
  probeDigest: string;
  auditTrendHistory: AuditCycleTrendPoint[];
}

export interface ComponentProbeOverride {
  methodAStatus: ProbeStatus;
  methodBStatus: ProbeStatus;
  failureCount: number;
  consecutiveRestorePasses: number;
  lastProbeLatencyMs: number;
  lastProbeTimestamp?: string;
  auditTrendHistory?: AuditCycleTrendPoint[];
}

const COMPONENT_CATALOG: Array<{
  componentId: CriticalComponentId;
  priorityTier: 'P0' | 'P1' | 'P2' | 'P3';
  subsystemName: string;
  methodAName: string;
  methodBName: string;
  defaultLatencyMs: number;
}> = [
  {
    componentId: 'DISK-01',
    priorityTier: 'P0',
    subsystemName: 'Restic Vault & NVMe Block Array',
    methodAName: 'statfs + Restic Manifest Sig',
    methodBName: '4KB Direct-I/O Canary Write/Read',
    defaultLatencyMs: 14,
  },
  {
    componentId: 'MEMORY-01',
    priorityTier: 'P1',
    subsystemName: 'SQLite Memory Spine & IDP Pointers',
    methodAName: 'WAL Frame CRC32 + SHM Lock',
    methodBName: 'SQLite PRAGMA integrity_check',
    defaultLatencyMs: 28,
  },
  {
    componentId: 'XREC-GATE-01',
    priorityTier: 'P2',
    subsystemName: 'xrec-mcp Fencing & Merkle Sealer',
    methodAName: 'Unix Socket Heartbeat + Epoch Monotonicity',
    methodBName: 'Synthetic Refusal Envelope Roundtrip',
    defaultLatencyMs: 9,
  },
  {
    componentId: 'ROUTER-01',
    priorityTier: 'P3',
    subsystemName: 'argon-sync SSH & Surface Dispatch Mesh',
    methodAName: 'SSH ControlMaster + ls-remote',
    methodBName: 'Loopback RPC Frame Checksum',
    defaultLatencyMs: 37,
  },
];

export function computeCycleHealthScore(
  leaseLevel: DofLevel,
  consecutivePasses: number,
  agreementState: SystemProbeHealthRow['agreementState']
): number {
  if (leaseLevel === 'L3') return 5;
  if (leaseLevel === 'L0' && consecutivePasses >= 3) return 100;
  if (agreementState === 'AGREED_FAIL') return 18;
  if (agreementState === 'DISAGREE_L1_HOLD' || agreementState === 'BOOTSTRAP_FAIL') {
    return 42;
  }
  if (consecutivePasses === 2) return 78;
  if (consecutivePasses === 1) return 54;
  return 25;
}

function buildDefaultAuditTrendHistory(
  componentId: CriticalComponentId,
  activeLeaseLevel: DofLevel,
  consecutiveRestorePasses: number,
  agreementState: SystemProbeHealthRow['agreementState']
): AuditCycleTrendPoint[] {
  // Baseline 9 historical cycles (C-9 to C-1) plus current cycle C0
  const historicalTemplates: Record<
    CriticalComponentId,
    Array<{ score: number; passes: number; level: DofLevel; outcome: 'PASS' | 'FAIL' | 'ANOMALY' }>
  > = {
    'DISK-01': [
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 96, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 98, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
    ],
    'MEMORY-01': [
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 42, passes: 0, level: 'L1', outcome: 'ANOMALY' },
      { score: 18, passes: 0, level: 'L2', outcome: 'FAIL' },
      { score: 18, passes: 0, level: 'L2', outcome: 'FAIL' },
      { score: 32, passes: 0, level: 'L2', outcome: 'FAIL' },
      {
        score: consecutiveRestorePasses >= 2 ? 54 : 18,
        passes: Math.max(0, consecutiveRestorePasses - 1),
        level: 'L2',
        outcome: consecutiveRestorePasses >= 2 ? 'PASS' : 'FAIL',
      },
    ],
    'XREC-GATE-01': [
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 98, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 99, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
    ],
    'ROUTER-01': [
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 42, passes: 0, level: 'L1', outcome: 'ANOMALY' },
      { score: 54, passes: 1, level: 'L2', outcome: 'PASS' },
      { score: 78, passes: 2, level: 'L2', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
      { score: 100, passes: 3, level: 'L0', outcome: 'PASS' },
    ],
  };

  const prior9 = historicalTemplates[componentId];
  const currentScore = computeCycleHealthScore(
    activeLeaseLevel,
    consecutiveRestorePasses,
    agreementState
  );
  const currentOutcome: 'PASS' | 'FAIL' | 'ANOMALY' =
    agreementState === 'AGREED_PASS'
      ? 'PASS'
      : agreementState === 'AGREED_FAIL'
        ? 'FAIL'
        : 'ANOMALY';

  const points: AuditCycleTrendPoint[] = prior9.map((item, idx) => ({
    cycleLabel: `C-${9 - idx}`,
    cycleOffset: -(9 - idx),
    healthScore: item.score,
    consecutivePasses: item.passes,
    leaseLevel: item.level,
    probeOutcome: item.outcome,
  }));

  points.push({
    cycleLabel: 'C0',
    cycleOffset: 0,
    healthScore: currentScore,
    consecutivePasses: consecutiveRestorePasses,
    leaseLevel: activeLeaseLevel,
    probeOutcome: currentOutcome,
  });

  return points;
}

function computeRowAgreementAndLease(
  componentId: CriticalComponentId,
  methodAStatus: ProbeStatus,
  methodBStatus: ProbeStatus,
  consecutiveRestorePasses: number,
  episode: DofEpisodeState
): {
  agreementState: SystemProbeHealthRow['agreementState'];
  activeLeaseLevel: DofLevel;
  rentedActionSpace: string;
} {
  if (episode.founderOttOverrideActive) {
    return {
      agreementState:
        methodAStatus === 'PASS' && methodBStatus === 'PASS'
          ? 'AGREED_PASS'
          : 'AGREED_FAIL',
      activeLeaseLevel: 'L0',
      rentedActionSpace: 'OTT Emergency Lease (principal:founder@fortress.estate)',
    };
  }

  // If this is the active failing component in the episode, reflect the episode's exact level
  if (episode.failingComponent === componentId && episode.activeLevel === 'L3') {
    return {
      agreementState: 'AGREED_FAIL',
      activeLeaseLevel: 'L3',
      rentedActionSpace: 'FROZEN 🔴 (xrec.emergency_halt_snapshot only)',
    };
  }

  if (methodAStatus === 'CANNOT_RUN' || methodBStatus === 'CANNOT_RUN') {
    return {
      agreementState: 'BOOTSTRAP_FAIL',
      activeLeaseLevel: 'L1',
      rentedActionSpace: 'PROBE-BOOTSTRAP-00 + diagnostics.read_probe_state',
    };
  }

  if (methodAStatus === 'FAIL' && methodBStatus === 'FAIL') {
    return {
      agreementState: 'AGREED_FAIL',
      activeLeaseLevel: 'L2',
      rentedActionSpace: `diagnostics.read + repair.${componentId} + xrec.receipt`,
    };
  }

  if (methodAStatus === 'FAIL' || methodBStatus === 'FAIL') {
    return {
      agreementState: 'DISAGREE_L1_HOLD',
      activeLeaseLevel: 'L1',
      rentedActionSpace: `diagnostics.read_probe_state (Re-probing ${componentId})`,
    };
  }

  // Both PASS, check 3-up hysteresis
  if (consecutiveRestorePasses < 3) {
    const holdLevel: DofLevel =
      episode.failingComponent === componentId ? episode.activeLevel : 'L2';
    return {
      agreementState: 'AGREED_PASS',
      activeLeaseLevel: holdLevel === 'L0' ? 'L2' : holdLevel,
      rentedActionSpace: `Hysteresis Hold (${consecutiveRestorePasses}/3 Passes) · repair.${componentId} only`,
    };
  }

  return {
    agreementState: 'AGREED_PASS',
    activeLeaseLevel: 'L0',
    rentedActionSpace: 'Full Action Space Rented (Read / Write / Execute)',
  };
}

/**
 * Builds the 4-component Priority DAG health monitor table synchronized with the active DoF episode,
 * including a 10-cycle failure/restoration trend history for each component.
 */
export function buildSystemProbeHealthMatrix(
  episode: DofEpisodeState,
  overrides: Partial<Record<CriticalComponentId, ComponentProbeOverride>> = {}
): SystemProbeHealthRow[] {
  return COMPONENT_CATALOG.map((item) => {
    const isEpisodeFailing = episode.failingComponent === item.componentId;
    const defaultMethodA: ProbeStatus = isEpisodeFailing
      ? episode.consecutiveProbePasses > 0
        ? 'PASS'
        : 'FAIL'
      : 'PASS';
    const defaultMethodB: ProbeStatus = isEpisodeFailing
      ? episode.activeLevel === 'L1'
        ? 'PASS'
        : episode.consecutiveProbePasses > 0
          ? 'PASS'
          : 'FAIL'
      : 'PASS';

    const override = overrides[item.componentId];
    const methodAStatus = override ? override.methodAStatus : defaultMethodA;
    const methodBStatus = override ? override.methodBStatus : defaultMethodB;
    const failureCount = override
      ? override.failureCount
      : isEpisodeFailing
        ? Math.max(1, episode.refusalLog.length + 1)
        : item.componentId === 'ROUTER-01'
          ? 1
          : 0;
    const consecutiveRestorePasses = override
      ? override.consecutiveRestorePasses
      : isEpisodeFailing
        ? episode.consecutiveProbePasses
        : 3;
    const lastProbeLatencyMs = override
      ? override.lastProbeLatencyMs
      : item.defaultLatencyMs;
    const lastProbeTimestamp =
      override?.lastProbeTimestamp || '2026-11-04T17:30:46Z';

    const { agreementState, activeLeaseLevel, rentedActionSpace } =
      computeRowAgreementAndLease(
        item.componentId,
        methodAStatus,
        methodBStatus,
        consecutiveRestorePasses,
        episode
      );

    const probeDigest = computeDeterministicHash(
      `PROBE::${item.componentId}::${episode.leaseEpoch}::${methodAStatus}::${methodBStatus}::${consecutiveRestorePasses}`
    ).slice(0, 14);

    const auditTrendHistory =
      override?.auditTrendHistory && override.auditTrendHistory.length === 10
        ? override.auditTrendHistory
        : buildDefaultAuditTrendHistory(
            item.componentId,
            activeLeaseLevel,
            consecutiveRestorePasses,
            agreementState
          );

    return {
      componentId: item.componentId,
      priorityTier: item.priorityTier,
      subsystemName: item.subsystemName,
      methodAName: item.methodAName,
      methodAStatus,
      methodBName: item.methodBName,
      methodBStatus,
      agreementState,
      activeLeaseLevel,
      rentedActionSpace,
      failureCount,
      consecutiveRestorePasses,
      requiredRestorePasses: 3,
      lastProbeLatencyMs,
      lastProbeTimestamp,
      probeDigest,
      auditTrendHistory,
    };
  });
}

/**
 * Pure transition helper for simulating a live probe tick on a specific component row
 * in the DoF Health Monitor table (enforcing 1-Down / 3-Up hysteresis, dual-probe agreement,
 * and sliding the 10-cycle audit trend window).
 */
export function simulateComponentProbeTick(
  currentOverride: ComponentProbeOverride | undefined,
  mode: 'PASS_BOTH' | 'FAIL_BOTH' | 'FALSE_POSITIVE_A' | 'CANNOT_RUN',
  timestampIso: string,
  existingTrendHistory?: AuditCycleTrendPoint[]
): ComponentProbeOverride {
  const prevFailures = currentOverride?.failureCount ?? 0;
  const prevPasses = currentOverride?.consecutiveRestorePasses ?? 3;
  const baseLatency = currentOverride?.lastProbeLatencyMs ?? 18;
  const seedTrend =
    currentOverride?.auditTrendHistory ||
    existingTrendHistory ||
    buildDefaultAuditTrendHistory('DISK-01', 'L0', 3, 'AGREED_PASS');

  let nextMethodA: ProbeStatus = 'PASS';
  let nextMethodB: ProbeStatus = 'PASS';
  let nextFailures = prevFailures;
  let nextPasses = Math.min(3, prevPasses + 1);
  let nextLatency = Math.max(8, (baseLatency % 25) + 9);
  let nextLease: DofLevel = nextPasses >= 3 ? 'L0' : 'L2';
  let nextAgreement: SystemProbeHealthRow['agreementState'] = 'AGREED_PASS';
  let nextOutcome: 'PASS' | 'FAIL' | 'ANOMALY' = 'PASS';

  if (mode === 'FAIL_BOTH') {
    nextMethodA = 'FAIL';
    nextMethodB = 'FAIL';
    nextFailures = prevFailures + 1;
    nextPasses = 0;
    nextLatency = baseLatency + 19;
    nextLease = 'L2';
    nextAgreement = 'AGREED_FAIL';
    nextOutcome = 'FAIL';
  } else if (mode === 'FALSE_POSITIVE_A') {
    nextMethodA = 'FAIL';
    nextMethodB = 'PASS';
    nextFailures = prevFailures + 1;
    nextPasses = 0;
    nextLatency = baseLatency + 11;
    nextLease = 'L1';
    nextAgreement = 'DISAGREE_L1_HOLD';
    nextOutcome = 'ANOMALY';
  } else if (mode === 'CANNOT_RUN') {
    nextMethodA = 'CANNOT_RUN';
    nextMethodB = 'CANNOT_RUN';
    nextFailures = prevFailures + 1;
    nextPasses = 0;
    nextLatency = 0;
    nextLease = 'L1';
    nextAgreement = 'BOOTSTRAP_FAIL';
    nextOutcome = 'ANOMALY';
  }

  const nextScore = computeCycleHealthScore(nextLease, nextPasses, nextAgreement);
  const shiftedTrend: AuditCycleTrendPoint[] = [
    ...seedTrend.slice(1).map((pt, idx) => ({
      ...pt,
      cycleLabel: `C-${9 - idx}`,
      cycleOffset: -(9 - idx),
    })),
    {
      cycleLabel: 'C0',
      cycleOffset: 0,
      healthScore: nextScore,
      consecutivePasses: nextPasses,
      leaseLevel: nextLease,
      probeOutcome: nextOutcome,
    },
  ];

  return {
    methodAStatus: nextMethodA,
    methodBStatus: nextMethodB,
    failureCount: nextFailures,
    consecutiveRestorePasses: nextPasses,
    lastProbeLatencyMs: nextLatency,
    lastProbeTimestamp: timestampIso,
    auditTrendHistory: shiftedTrend,
  };
}

export interface DofLevelStateFile {
  schema: 'argon-sync.dof-level-state.v1';
  stateFilePath: '/var/run/estate/dof-level.state';
  ratifiedSpecRef: string;
  leaseEpoch: number;
  activeLevel: DofLevel;
  noGrandfatheringEnforced: true;
  failingComponent: CriticalComponentId | null;
  prescribedProtocol: string | null;
  hysteresis: {
    dropPolicy: '1_DUAL_METHOD_FAILURE';
    restorePolicy: '3_CONSECUTIVE_VERIFIED_PASSES';
    consecutivePasses: number;
    requiredPasses: 3;
    completedRepairSteps: number;
    requiredRepairSteps: number;
  };
  componentPriorityDag: Array<{
    componentId: CriticalComponentId;
    priorityTier: 'P0' | 'P1' | 'P2' | 'P3';
    agreementState: SystemProbeHealthRow['agreementState'];
    componentLeaseLevel: DofLevel;
    probeDigest: string;
  }>;
  xrecSealedDigest: string;
}

/**
 * Phase 0 Artifact 1: Serializes the canonical /var/run/estate/dof-level.state file
 * read by xrec-mcp and every newly spawned agent session (preventing mid-incident grandfathering).
 */
export function serializeDofLevelStateFile(
  episode: DofEpisodeState,
  healthMatrix: SystemProbeHealthRow[],
  ratifiedSpecRef = 'main @ c3e0822 (GEN-NET-006 / GEN-DOF-001)'
): DofLevelStateFile {
  return {
    schema: 'argon-sync.dof-level-state.v1',
    stateFilePath: '/var/run/estate/dof-level.state',
    ratifiedSpecRef,
    leaseEpoch: episode.leaseEpoch,
    activeLevel: episode.activeLevel,
    noGrandfatheringEnforced: true,
    failingComponent: episode.failingComponent,
    prescribedProtocol: episode.prescribedProtocol,
    hysteresis: {
      dropPolicy: '1_DUAL_METHOD_FAILURE',
      restorePolicy: '3_CONSECUTIVE_VERIFIED_PASSES',
      consecutivePasses: episode.consecutiveProbePasses,
      requiredPasses: 3,
      completedRepairSteps: episode.completedRepairSteps.length,
      requiredRepairSteps: MEMORY_01_REPAIR_PROTOCOL.length,
    },
    componentPriorityDag: healthMatrix.map((row) => ({
      componentId: row.componentId,
      priorityTier: row.priorityTier,
      agreementState: row.agreementState,
      componentLeaseLevel: row.activeLeaseLevel,
      probeDigest: row.probeDigest,
    })),
    xrecSealedDigest: episode.xrecSealedDigest,
  };
}

/**
 * Phase 0 Artifact 2: Generates the verbatim Onboarding Rule Zero block injected
 * at every session start, dynamically bound to the current /var/run/estate/dof-level.state.
 */
export function buildOnboardingRuleZeroBlock(episode: DofEpisodeState): string {
  const rentedSurface =
    episode.activeLevel === 'L0'
      ? '* (FULL_CAPABILITY_LEASE)'
      : episode.activeLevel === 'L1'
        ? 'diagnostics.read_probe_state ONLY (READ_DIAGNOSE_ONLY)'
        : episode.activeLevel === 'L2'
          ? `diagnostics.read_probe_state + repair.${episode.prescribedProtocol ?? 'MEMORY-01'} + xrec.append_repair_receipt ONLY`
          : 'FROZEN_RED_CARD (xrec.emergency_halt_snapshot ONLY)';

  return [
    '=== ESTATE ONBOARDING RULE ZERO (GEN-DOF-001 · MANDATORY SESSION HEADER) ===',
    'Rule Zero: An estate whose critical components are unproven grants no freedom.',
    '1. Capabilities are leased, never possessed. The estate owns the action space; you rent a subset based on live component health.',
    `2. Active Lease State (/var/run/estate/dof-level.state): Level=${episode.activeLevel} | Epoch=${episode.leaseEpoch} | FailingComponent=${episode.failingComponent ?? 'NONE'}`,
    `3. Rented Writable/Callable Surface: ${rentedSurface}`,
    '4. Below L1, "note and move on" is structurally impossible. Any tool invocation outside your rented lease returns an xrec-mcp refusal envelope and increments escalation.',
    `5. Restoration is proof-only: 1 dual-method failure drops the lease; 3 consecutive verified passes (${episode.consecutiveProbePasses}/3) after completing all prescribed repair steps (${episode.completedRepairSteps.length}/${MEMORY_01_REPAIR_PROTOCOL.length}) restore L0.`,
    '============================================================================',
  ].join('\n');
}



