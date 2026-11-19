/**
 * Genesis Standout Academy Engine — Tri-Representational Convergence,
 * Interactive Boundary Counterexample Laboratory, and Post-Submission
 * Objective Unseen Transfer Pilot.
 *
 * Pedagogical & Epistemic Architecture:
 *  1. Tri-Representational Convergence: Every track presents (I) Structural Physical
 *     Isomorphism (with explicit analogy limits), (II) Formal Mathematical & Boundary Law,
 *     and (III) Live Estate Production Binding — adapted across 4 depth lenses
 *     (Total Novice -> Practitioner -> Principal / Expert -> Founder & Architect).
 *  2. Boundary Counterexample Lab: Learners toggle concrete dependency/precondition
 *     violations (missing key, uncaptured external API, split-brain writes, escaped $lines,
 *     correlated blindspots, sub-quorum < k) to witness why instructions or green badges
 *     alone never guarantee recovery.
 *  3. Objective Unseen Transfer Pilot: 3 unseen transfer problems in novel real-world
 *     domains per track, scored strictly AFTER submission with zero premature answer
 *     leakage and explicit research-pilot epistemic honesty (no inflated claim of
 *     established long-term mastery or teaching efficacy from a single pilot check).
 */

import { pureSha256Hex } from './pureSha256';
import type { AcademyCurvePoint, AcademyLevel } from './founderRegoChronosPlane';
import type { NavTabId } from '../types/api';

export type StandoutTrackId =
  | 'reproducibility_transfer_boundaries'
  | 'machine_agent_ratchet_doctrine'
  | 'condorcet_ensemble_economics'
  | 'bayesian_evsi_prospector'
  | 'reed_solomon_continuity'
  | 'rego_harmonic_synchronicity';

export interface ConvergingRepresentation {
  id: 'physical_isomorphism' | 'formal_boundary_law' | 'estate_production_binding';
  label: string;
  title: string;
  body: string;
  explicitBoundaryLimit: string;
}

export interface BoundaryFaultToggle {
  id: string;
  label: string;
  consequenceSummary: string;
}

export interface UnseenTransferItem {
  id: string;
  domainKicker: string;
  title: string;
  scenario: string;
  options: [string, string, string, string];
  correctIndex: number;
  transferExplanation: string;
  distractorDiagnosis: string;
}

export interface TransferPilotEvaluation {
  trackId: StandoutTrackId;
  submittedAtUtc: string;
  complete: boolean;
  validationError: string | null;
  score: number;
  totalItems: 3;
  epistemicDisclaimer: string;
  receiptSha256: string;
  itemResults: Array<{
    itemId: string;
    title: string;
    selectedOptionIndex: number;
    correctOptionIndex: number;
    correct: boolean;
    selectedText: string;
    correctText: string;
    transferExplanation: string;
    distractorDiagnosis: string;
  }>;
}

export interface StandoutTrackSimulation {
  trackId: StandoutTrackId;
  indexLabel: string;
  shortTitle: string;
  title: string;
  level: AcademyLevel;
  linkedTab: NavTabId;
  linkedTabLabel: string;
  sharedPrincipleStatement: string;
  governingEquation: string;
  sliderLabel: string;
  sliderUnit: string;
  defaultSliderValue: number;
  representations: [ConvergingRepresentation, ConvergingRepresentation, ConvergingRepresentation];
  levelSynthesis: string;
  boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle];
  activeFaultIds: string[];
  boundaryViolated: boolean;
  primaryMetricLabel: string;
  primaryMetricValue: string;
  secondaryMetricLabel: string;
  secondaryMetricValue: string;
  equilibriumStatusLabel: string;
  activeViolationConsequences: string[];
  curvePoints: AcademyCurvePoint[];
  unseenTransferItems: [UnseenTransferItem, UnseenTransferItem, UnseenTransferItem];
}

function chooseCount(n: number, k: number): number {
  if (k < 0 || k > n) return 0;
  if (k === 0 || k === n) return 1;
  let res = 1;
  for (let i = 1; i <= k; i++) {
    res = (res * (n - i + 1)) / i;
  }
  return res;
}

export const STANDOUT_TRACK_CATALOG: Array<{
  id: StandoutTrackId;
  indexLabel: string;
  shortTitle: string;
  subtitle: string;
  defaultSliderValue: number;
  linkedTab: NavTabId;
  linkedTabLabel: string;
}> = [
  {
    id: 'reproducibility_transfer_boundaries',
    indexLabel: '01',
    shortTitle: 'History, Keys & Transfer Boundaries',
    subtitle: 'Why instructions alone cannot reproduce missing dependencies',
    defaultSliderValue: 92,
    linkedTab: 'packets',
    linkedTabLabel: 'Inspect WAL & Vault Forensics',
  },
  {
    id: 'machine_agent_ratchet_doctrine',
    indexLabel: '02',
    shortTitle: 'Machine-Agent Boundary & Ratchets',
    subtitle: '13-Pin Doctrine, fail-open $lines bug & no-growth ratchets',
    defaultSliderValue: 90,
    linkedTab: 'union',
    linkedTabLabel: 'Inspect 13-Pin Audit & Ratchet',
  },
  {
    id: 'condorcet_ensemble_economics',
    indexLabel: '03',
    shortTitle: 'Specialist Ensembles vs Frontier',
    subtitle: 'Uncorrelated Best-of-3 + AST verifier & error correlation bounds',
    defaultSliderValue: 84,
    linkedTab: 'supply',
    linkedTabLabel: 'Open Model Supply & Legion',
  },
  {
    id: 'bayesian_evsi_prospector',
    indexLabel: '04',
    shortTitle: 'Bayesian EVSI & Causal Research',
    subtitle: 'Expected value of sample info & confounder quarantine',
    defaultSliderValue: 88,
    linkedTab: 'mumchimp_research',
    linkedTabLabel: 'Open Prospector-2100 & Mumchimp',
  },
  {
    id: 'reed_solomon_continuity',
    indexLabel: '05',
    shortTitle: 'GF(2^8) Reed-Solomon Continuity',
    subtitle: 'Vandermonde RS(3,8) survival, k>=3 quorum & epoch fencing',
    defaultSliderValue: 82,
    linkedTab: 'genesis_ttt',
    linkedTabLabel: 'Open I-8088 Cephalopod Lab',
  },
  {
    id: 'rego_harmonic_synchronicity',
    indexLabel: '06',
    shortTitle: 'Chronos Harmonics & Rego Policy',
    subtitle: '5-ring phase-locked clockwork & declarative policy-as-code',
    defaultSliderValue: 96,
    linkedTab: 'founder_plane',
    linkedTabLabel: 'Open Founder & Rego Plane',
  },
];

export function simulateStandoutAcademyTrack(params: {
  trackId: StandoutTrackId;
  level: AcademyLevel;
  sliderParam: number;
  activeFaultIds?: string[];
}): StandoutTrackSimulation {
  const { trackId, level } = params;
  const clamped = Math.max(55, Math.min(98, Number(params.sliderParam) || 86));
  const faultSet = new Set(params.activeFaultIds ?? []);

  // -------------------------------------------------------------------------
  // TRACK 01: INSTRUCTIONS, MISSING HISTORY & DEPENDENCY BOUNDARIES
  // -------------------------------------------------------------------------
  if (trackId === 'reproducibility_transfer_boundaries') {
    const boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle] = [
      {
        id: 'missing_key',
        label: 'Lose Historical Encryption Key',
        consequenceSummary:
          'Signed checkpoints and ordered ciphertexts cannot invert AES/PBKDF2 without the authorised key or trusted plaintext (H(K|C) = H(K)).',
      },
      {
        id: 'uncaptured_external_api',
        label: 'Omit Historical External Oracle Inputs',
        consequenceSummary:
          'Replaying deterministic code against today’s live API rates diverges from historical totals whenever external responses were not recorded.',
      },
      {
        id: 'unreconciled_replica_divergence',
        label: 'Allow Divergent Replica & Primary Writes',
        consequenceSummary:
          'Matching initial checkpoints do not prevent split-brain; diverged branches require authorised reconciliation and independent verification.',
      },
    ];

    const activeViolations = boundaryToggles.filter((t) => faultSet.has(t.id));
    const boundaryViolated = activeViolations.length > 0;
    const captureCompleteness = clamped;

    const exactRecoveryPct = boundaryViolated
      ? 0
      : Number(Math.min(100, Math.pow(captureCompleteness / 100, 2) * 100).toFixed(1));

    const curvePoints: AcademyCurvePoint[] = [60, 70, 80, 88, 94, 100].map((cap) => ({
      x: cap,
      xLabel: `${cap}%`,
      primaryY: boundaryViolated ? 0 : Number((Math.pow(cap / 100, 2) * 100).toFixed(1)),
      baselineY: cap, // Naive "code + green dashboard" assumption
    }));

    const levelSynthesisMap: Record<AcademyLevel, string> = {
      novice:
        'Having the exact recipe and oven (software instructions) cannot recreate yesterday’s locked ledger if you lost the safe combination, forgot to write down yesterday’s market prices, or let two cashiers keep separate notebooks.',
      practitioner:
        'Deterministic replay is a pure function State_T = F(Seed_0, Key, Events_1..T, ExternalInputs_1..T). Dropping any argument turns a reproducible state machine into an underdetermined system.',
      expert:
        'By Shannon’s secrecy bound and state-machine linearizability, software binaries + signed checkpoints carry zero mutual information with lost secret keys or unlogged external non-determinism, and forked histories require causal conflict resolution + fencing.',
      founder:
        'Protects Meridian from catastrophic enterprise SLA & audit illusions: we never let a green "VERIFIED" UI badge mask missing vault keys (GENVAULT1), uncaptured external feeds, or unfenced multi-node writes.',
    };

    return {
      trackId,
      indexLabel: '01',
      shortTitle: 'History, Keys & Transfer Boundaries',
      title: 'State Reproducibility, Missing Dependencies & Fork Reconciliation',
      level,
      linkedTab: 'packets',
      linkedTabLabel: 'Inspect WAL & Vault Forensics',
      sharedPrincipleStatement:
        'The shared principle: instructions alone cannot reproduce missing history or missing dependencies. All three representations converge on that conditional relationship — never on an unconditional guarantee.',
      governingEquation:
        'ExactReplay(T) ⇔ HasKey(K) ∧ Captured(Inputs_1..T, Versions) ∧ Reconciled(Fork_A, Fork_B)',
      sliderLabel: 'Captured Dependency & Input Completeness',
      sliderUnit: '%',
      defaultSliderValue: 92,
      representations: [
        {
          id: 'physical_isomorphism',
          label: 'Representation I · Structural Analogy',
          title: 'Locked Ledger, Changing Market Board & Split Notebooks',
          body: 'An audited accounting rulebook plus a stamped morning balance cannot reveal locked safe contents without the key, recalculate noon foreign-exchange invoices if noon exchange rates went unrecorded, or merge two clerks’ independent afternoon edits automatically.',
          explicitBoundaryLimit:
            'Analogy limit: even two or ten agreeing analogies only illustrate structural dependence — analogies never recover missing cryptographic entropy.',
        },
        {
          id: 'formal_boundary_law',
          label: 'Representation II · Formal Law',
          title: 'Information-Theoretic & Linearizability Preconditions',
          body: 'Given transition operator δ, S_t = δ(S_{t-1}, e_t, ω_t) over encrypted payload Dec(K, c_t). If K is erased, H(m_t | c_t, δ, S_0) = H(m_t). If external oracle ω_t is unrecorded or histories H_A ≠ H_B diverge post-checkpoint, unique deterministic reconstruction does not exist.',
          explicitBoundaryLimit:
            'Formal limit: passing unit tests proves δ is well-formed on synthetic inputs; it never proves K, ω_t, or single-writer authority exist in production.',
        },
        {
          id: 'estate_production_binding',
          label: 'Representation III · Live Estate Engine',
          title: 'PennyD WAL, GENVAULT1 MAC & Cephalopod Fence Tokens',
          body: 'RouterEngine logs exact provider rate-card versions per packet (F6), Dagster verifies vault key hydration on reboot (F3), WorldConnector stamps observed snapshot metadata (F15), and I-8088 rejects stale or divergent shards unless fenced and reconciled (F18).',
          explicitBoundaryLimit:
            'Operational limit: if GENVAULT1 passphrase is absent or a lane is unprobed (BLIND), the UI fails closed (503 / BLIND) rather than showing a false VERIFIED state.',
        },
      ],
      levelSynthesis: levelSynthesisMap[level],
      boundaryToggles,
      activeFaultIds: Array.from(faultSet),
      boundaryViolated,
      primaryMetricLabel: 'Guaranteed Bit-Exact Recovery',
      primaryMetricValue: `${exactRecoveryPct}%`,
      secondaryMetricLabel: 'Missing Dependency Violations',
      secondaryMetricValue: `${activeViolations.length} / 3`,
      equilibriumStatusLabel: boundaryViolated
        ? 'BOUNDARY VIOLATED — INSTRUCTIONS ALONE CANNOT RECOVER MISSING STATE'
        : 'PRECONDITIONS SATISFIED — DETERMINISTIC REPLAY & RECOVERY SOUND',
      activeViolationConsequences: activeViolations.map((v) => v.consequenceSummary),
      curvePoints,
      unseenTransferItems: [
        {
          id: 'tr-01-missing-key',
          domainKicker: 'Unseen Domain 1 · Municipal Transit Archive',
          title: '1. The missing key',
          scenario:
            "A city's transit archive has a signed checkpoint, all ordered transactions and correct software, but has lost the encryption key for historical records. What follows?",
          options: [
            'The checkpoint can derive any missing key.',
            'Exact recovery of encrypted details needs the authorised key or equivalent trusted plaintext.',
            'Two agreeing analogies guarantee recovery.',
            'A VERIFIED dashboard is sufficient.',
          ],
          correctIndex: 1,
          transferExplanation:
            'Strong encryption binds confidentiality to key possession: correct software, ordered ciphertexts, and signed checkpoints verify integrity of the ciphertext container, but cannot decrypt historical records without the authorised key or an independent trusted plaintext record.',
          distractorDiagnosis:
            'Checkpoints, agreeing analogies, and green "VERIFIED" status indicators contain zero bits of the lost secret key.',
        },
        {
          id: 'tr-01-external-service',
          domainKicker: 'Unseen Domain 2 · Multi-Currency Billing',
          title: '2. The changing external service',
          scenario:
            'A billing system replays all invoice events, but never captured the historical responses from its changing exchange-rate API.',
          options: [
            'The historical totals will always match.',
            'A larger event database solves it automatically.',
            'Exact replay needs the original external inputs and their versions.',
            'The latest snapshot proves all earlier inputs.',
          ],
          correctIndex: 2,
          transferExplanation:
            'When transition output depends on time-varying external inputs (FX rates), deterministic event replay reproduces historical totals if and only if those original external responses (or versioned immutable rate tables) were captured alongside the events.',
          distractorDiagnosis:
            'Database size and final snapshots neither record intermediate external API responses nor prevent historical rate drift.',
        },
        {
          id: 'tr-01-disconnected-fleet',
          domainKicker: 'Unseen Domain 3 · Distributed Replica Operations',
          title: '3. The disconnected fleet',
          scenario:
            'A fleet replica restores successfully, then both the replica and the original accept different new updates. Can they rejoin automatically without divergence?',
          options: [
            'Yes, if the local tests pass.',
            'Yes, because their original checkpoint matched.',
            'Yes, because the replica inherits all authority.',
            'Not without reconciling authorised changes and independently verifying the result.',
          ],
          correctIndex: 3,
          transferExplanation:
            'Once two live nodes accept distinct post-restore writes, their causal histories have forked (split-brain). Rejoining safely requires explicit conflict/authority reconciliation plus independent post-merge verification.',
          distractorDiagnosis:
            'Local unit tests and shared ancestor checkpoints say nothing about conflicting writes accepted after the fork.',
        },
      ],
    };
  }

  // -------------------------------------------------------------------------
  // TRACK 02: MACHINE-AGENT BOUNDARY & FAIL-CLOSED CONTROL RATCHETS
  // -------------------------------------------------------------------------
  if (trackId === 'machine_agent_ratchet_doctrine') {
    const boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle] = [
      {
        id: 'escaped_lines_fail_open',
        label: 'Inject Escaped $lines Shell Bug (Fail-Open)',
        consequenceSummary:
          'Passing literal "$lines" to Bash integer test prints an error yet exits 0 — letting 500-line bloat slip past a green check.',
      },
      {
        id: 'shortcut_no_verify',
        label: 'Apply Old Installer --no-verify Shortcut',
        consequenceSummary:
          'Bypassing pre-push hooks or rewriting multi-agent history breaks authenticated IDP provenance (blocked by Pin 3 & OBS-09).',
      },
      {
        id: 'promote_test_to_yield',
        label: 'Claim Live Yield From Local Audit Tests',
        consequenceSummary:
          'Conflates 21/21 local engineering acceptance with live operational effect (violating Rego R-010 & Pin 13).',
      },
    ];

    const activeViolations = boundaryToggles.filter((t) => faultSet.has(t.id));
    const boundaryViolated = activeViolations.length > 0;
    const preventionScore = boundaryViolated
      ? Number(Math.max(12, 48 - activeViolations.length * 14).toFixed(1))
      : Number(Math.min(99.4, 54 + (clamped - 50) * 0.95).toFixed(1));

    const curvePoints: AcademyCurvePoint[] = [55, 65, 75, 85, 92, 98].map((mp) => ({
      x: mp,
      xLabel: `${mp}%`,
      primaryY: boundaryViolated
        ? Number(Math.max(14, 52 - activeViolations.length * 14).toFixed(1))
        : Number(Math.min(99.4, 54 + (mp - 50) * 0.95).toFixed(1)),
      baselineY: Number(Math.max(38, 74 - (100 - mp) * 0.42).toFixed(1)),
    }));

    const levelSynthesisMap: Record<AcademyLevel, string> = {
      novice:
        'Machines should enforce exact countable rules (and we must test the alarm with a known violation first!), freeing human and AI judgement for real trade-offs.',
      practitioner:
        'When canonical AGENTS.md is already 348 lines (>300 target), a tested fail-closed no-growth ratchet blocks line 349 immediately without halting legitimate 0-growth commits during staged consolidation.',
      expert:
        'Candidate ff8543bd (+7 ahead of IDP main d03f5d59) retains Pi declare_plan, BDD, edge cases, and second-order effects while proving 12/12 observer + 9/9 ratchet adversarial checks and holding LIVE_CEREMONY_EFFECT = UNKNOWN.',
      founder:
        'Turns our internal reliability doctrine into enterprise-grade training & consulting IP — where every marketed claim independently earns its operational proof.',
    };

    return {
      trackId,
      indexLabel: '02',
      shortTitle: 'Machine-Agent Boundary & Ratchets',
      title: '13-Pin Machine-Agent Doctrine & Fail-Closed No-Growth Ratchets',
      level,
      linkedTab: 'union',
      linkedTabLabel: 'Inspect 13-Pin Audit & Ratchet',
      sharedPrincipleStatement:
        'The shared principle: a gate never proven to fail on known-bad input offers zero protection, and local engineering acceptance never substitutes for independently verified operational yield.',
      governingEquation:
        'TrustedControl(G) ⇔ G(known_bad) = EXIT_1 ∧ x_t ≤ max(Target, Baseline_{t-1}) ∧ Yield ≠ TestPass',
      sliderLabel: 'Deterministic Mechanics Assigned to Machine Producers',
      sliderUnit: '%',
      defaultSliderValue: 90,
      representations: [
        {
          id: 'physical_isomorphism',
          label: 'Representation I · Structural Analogy',
          title: 'Circuit Breaker With a Physical Test-Trip Button',
          body: 'Electricians never trust a breaker label alone — they press the physical TEST button to prove current actually cuts off, and use a one-way ratchet wrench when tightening a heavy load step by step.',
          explicitBoundaryLimit:
            'Analogy limit: testing the trip switch proves local cutoff mechanics, not city-wide grid reliability until measured under real load.',
        },
        {
          id: 'formal_boundary_law',
          label: 'Representation II · Formal Law',
          title: 'Fail-Closed Input Parsing & Monotonic Ratchet Inequality',
          body: 'Parse n, b ∈ Z>=0 strictly (non-integers -> exit 1). Define C_eff = max(300, b). Require n <= C_eff, and update b_{next} = max(300, min(b, n)) so every consolidation step permanently lowers the ceiling toward 300.',
          explicitBoundaryLimit:
            'Formal limit: mathematical soundness of the ratchet script still requires signed branch enforcement on main before claiming estate-wide protection.',
        },
        {
          id: 'estate_production_binding',
          label: 'Representation III · Live Estate Engine',
          title: 'firstUseGovernanceAudit.ts (ff8543bd) & Rego Rule R-010',
          body: 'Reproduces the legacy escaped $lines fail-open bug, runs 21/21 adversarial checks (OBS-01..12 + RAT-01..09), blocks --no-verify shortcuts, and keeps LIVE_CEREMONY_EFFECT = UNKNOWN.',
          explicitBoundaryLimit:
            'Operational limit: audit/first-use-machine-agent-20261116 remains an unmerged VERIFIED_CANDIDATE until authorised Greenlane integration.',
        },
      ],
      levelSynthesis: levelSynthesisMap[level],
      boundaryToggles,
      activeFaultIds: Array.from(faultSet),
      boundaryViolated,
      primaryMetricLabel: 'First-Use Defect Prevention',
      primaryMetricValue: `${preventionScore}%`,
      secondaryMetricLabel: 'Epistemic / Gate Violations',
      secondaryMetricValue: `${activeViolations.length} / 3`,
      equilibriumStatusLabel: boundaryViolated
        ? 'CONTROL COMPROMISED — FAIL-OPEN OR PROVENANCE SHORTCUT DETECTED'
        : 'PRODUCER-FIRST VERIFIED — RATCHET & CEREMONY INTACT',
      activeViolationConsequences: activeViolations.map((v) => v.consequenceSummary),
      curvePoints,
      unseenTransferItems: [
        {
          id: 'tr-02-flight-check',
          domainKicker: 'Unseen Domain 1 · Avionics Pre-Flight Script',
          title: '1. The silent green check',
          scenario:
            'An airline telemetry gate checks fuel margin using a shell variable typo that prints a warning to stderr but still returns exit code 0 to CI. What is true before deployment?',
          options: [
            'The warning text guarantees bad flights will be blocked.',
            'Because CI stayed green for six months, the check is battle-tested.',
            'The control is fail-open and untrustworthy until proven to return non-zero against a deliberate bad fuel input.',
            'Agents should manually read stderr on every flight instead of fixing the gate.',
          ],
          correctIndex: 2,
          transferExplanation:
            'CI pipelines gate on process exit codes, not human reading of warning text. Any check that exits 0 on invalid/missing variables is fail-open and must be falsified against a deliberate bad input.',
          distractorDiagnosis:
            'Six months of green runs on a fail-open gate measures zero prevented defects, not reliability.',
        },
        {
          id: 'tr-02-hospital-ratchet',
          domainKicker: 'Unseen Domain 2 · Clinical Formulary Consolidation',
          title: '2. The inherited over-limit baseline',
          scenario:
            'A hospital wants drug-interaction exceptions capped at 100, but today’s live formulary already has 142 active exceptions. Urgent patient updates still arrive daily. Which control is safest?',
          options: [
            'Turn on an immediate hard 100-item block that halts all urgent updates today.',
            'Disable validation hooks with --no-verify until next quarter.',
            'Enforce a fail-closed no-growth ratchet at <=142 that ratchets downward as items are consolidated toward 100.',
            'Rewrite audit history so older exceptions disappear from the count.',
          ],
          correctIndex: 2,
          transferExplanation:
            'A tested no-growth ratchet prevents any new bloat (>142) immediately while allowing safe daily operations and locking in every consolidation step toward the 100-item target.',
          distractorDiagnosis:
            'Blind hard gates block legitimate urgent care against an inherited baseline, while hook bypasses and history rewrites destroy audit provenance.',
        },
        {
          id: 'tr-02-warehouse-yield',
          domainKicker: 'Unseen Domain 3 · Autonomous Warehouse Robotics',
          title: '3. The candidate audit vs live floor claim',
          scenario:
            'A robotics team builds a new collision observer on an unmerged branch that passes 25/25 adversarial simulator tests, with zero live warehouse hours logged yet. What can be claimed to customers?',
          options: [
            'Certified 40% reduction in live warehouse collisions.',
            'Verified engineering candidate passing 25/25 simulator tests, with live operational effect explicitly unmeasured.',
            'Full estate-wide enforcement across all warehouses.',
            'Proof that existing safety checklists can now be deleted.',
          ],
          correctIndex: 1,
          transferExplanation:
            'Plan completion, local adversarial test pass, and live operational yield are distinct epistemic tiers. Unmerged simulator candidates cannot be marketed as live floor yield.',
          distractorDiagnosis:
            'Deleting existing safety steps before measuring live protective value risks removing real safeguards without evidence.',
        },
      ],
    };
  }

  // -------------------------------------------------------------------------
  // TRACK 03: CONDORCET SPECIALIST ENSEMBLES VS FRONTIER
  // -------------------------------------------------------------------------
  if (trackId === 'condorcet_ensemble_economics') {
    const boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle] = [
      {
        id: 'correlated_clones',
        label: 'Use 3 Identical Model Clones (High ρ_corr)',
        consequenceSummary:
          'Sampling the same model family 3 times shares identical training blindspots — error correlation ρ_corr jumps from 0.012 to 0.16.',
      },
      {
        id: 'no_ast_verifier',
        label: 'Disable Executable AST / Test Verifier',
        consequenceSummary:
          'Plurality voting without an objective verifier falls for confident, plausible-sounding hallucinations.',
      },
      {
        id: 'ignore_quota_drain',
        label: 'Remove 15% Pre-Exhaustion Quota Rotation',
        consequenceSummary:
          'Free/Sovereign pools hit hard 429 rate-limit cliffs mid-burst instead of draining smoothly across sibling providers.',
      },
    ];

    const activeViolations = boundaryToggles.filter((t) => faultSet.has(t.id));
    const boundaryViolated = activeViolations.length > 0;
    const p = clamped / 100;
    const corrPenalty =
      (faultSet.has('correlated_clones') ? 0.14 : 0.012) +
      (faultSet.has('no_ast_verifier') ? 0.07 : 0) +
      (faultSet.has('ignore_quota_drain') ? 0.05 : 0);

    const verifiedEnsemblePct = Number(
      Math.max(45, Math.min(99.6, (1 - Math.pow(1 - p, 3) - corrPenalty) * 100)).toFixed(1)
    );
    const frontierSinglePct = 93.4;

    const curvePoints: AcademyCurvePoint[] = [60, 68, 75, 82, 88, 94].map((xPct) => {
      const px = xPct / 100;
      const ens = Number(
        Math.max(40, Math.min(99.6, (1 - Math.pow(1 - px, 3) - corrPenalty) * 100)).toFixed(1)
      );
      return {
        x: xPct,
        xLabel: `${xPct}%`,
        primaryY: ens,
        baselineY: frontierSinglePct,
      };
    });

    const levelSynthesisMap: Record<AcademyLevel, string> = {
      novice:
        'Three fast specialists trained differently — plus an automated answer checker — beat one expensive generalist for a fraction of a penny, as long as they don’t copy each other’s blindspots.',
      practitioner:
        'Independent failure shrinks cubically as (1 - p)^3, crossing the 93.4% Frontier bar at p >= 78% only when architecture diversity keeps ρ_corr <= 0.012 and an AST/test verifier filters candidates.',
      expert:
        'Combining Nemotron-Small + DeepSeek-V4.1 + Qwen3-Coder with deterministic verification achieves 96.9% pass rate at $0.024/1M blended COGS (99.8% cheaper than single Frontier calls).',
      founder:
        'Creates Meridian’s >85% SaaS gross-margin moat while eliminating single-vendor Frontier pricing and outage lock-in.',
    };

    return {
      trackId,
      indexLabel: '03',
      shortTitle: 'Specialist Ensembles vs Frontier',
      title: 'Uncorrelated Best-of-3 Open Ensembles & Verifier Economics',
      level,
      linkedTab: 'supply',
      linkedTabLabel: 'Open Model Supply & Legion',
      sharedPrincipleStatement:
        'The shared principle: ensemble amplification requires uncorrelated failure modes and an objective verifier — repeating correlated guesses without verification merely amplifies shared error.',
      governingEquation:
        'P_verified = 1 - (1 - p)^3 - ρ_corr(diversity, verifier)  >  P_frontier (93.4%)',
      sliderLabel: 'Individual Specialist Pass Accuracy (p)',
      sliderUnit: '%',
      defaultSliderValue: 84,
      representations: [
        {
          id: 'physical_isomorphism',
          label: 'Representation I · Structural Analogy',
          title: 'Three Independent Navigation Sensors + Altimeter Lock',
          body: 'Aircraft combine GPS, inertial gyroscopes, and barometric sensors — three different physical mechanisms — rather than installing three identical GPS receivers that all fail together in the same canyon.',
          explicitBoundaryLimit:
            'Analogy limit: diverse sensors still fail if the arbitration computer has no physical plausibility check to reject out-of-bounds readings.',
        },
        {
          id: 'formal_boundary_law',
          label: 'Representation II · Formal Law',
          title: 'Condorcet Variance Reduction & Shared-Mode Bound',
          body: 'For k=3 candidates with pass rate p and pairwise failure covariance ρ_corr, P(all fail or unverified slip) = (1 - p)^3 + ρ_corr. If ρ_corr -> (1 - p), the ensemble collapses back to single-model accuracy at 3x compute.',
          explicitBoundaryLimit:
            'Formal limit: open-ended tasks without a decidable or high-precision verifier cannot achieve zero-false-positive selection from generation count alone.',
        },
        {
          id: 'estate_production_binding',
          label: 'Representation III · Live Estate Engine',
          title: 'Legion ModelSupplyRegistry & GrandUnion Ensemble Proof (F19)',
          body: 'Routes across Nemotron ($0), DeepSeek/GLM Free Pool ($0), and Qwen3/InterCloud Spot ($0.042/1M) with 15% pre-exhaustion rotation and executable test verification.',
          explicitBoundaryLimit:
            'Operational limit: tasks failing specialist verification escalate transparently to the <12% Frontier reserve rather than returning unverified output.',
        },
      ],
      levelSynthesis: levelSynthesisMap[level],
      boundaryToggles,
      activeFaultIds: Array.from(faultSet),
      boundaryViolated,
      primaryMetricLabel: `Ensemble Verified Pass @ p=${clamped}%`,
      primaryMetricValue: `${verifiedEnsemblePct}%`,
      secondaryMetricLabel: 'Delta vs Single Frontier (93.4%)',
      secondaryMetricValue: `${verifiedEnsemblePct >= frontierSinglePct ? '+' : ''}${(verifiedEnsemblePct - frontierSinglePct).toFixed(1)} pp`,
      equilibriumStatusLabel:
        verifiedEnsemblePct >= frontierSinglePct && !boundaryViolated
          ? 'SURPASSES FRONTIER AT >99% LOWER INFERENCE COGS'
          : 'CORRELATION / VERIFIER PENALTY — RESTORE DIVERSITY & AST GATE',
      activeViolationConsequences: activeViolations.map((v) => v.consequenceSummary),
      curvePoints,
      unseenTransferItems: [
        {
          id: 'tr-03-radiology',
          domainKicker: 'Unseen Domain 1 · Diagnostic Imaging Triage',
          title: '1. The cloned ensemble',
          scenario:
            'A clinic replaces one expensive diagnostic model with three checkpoints trained on the exact same hospital scanner dataset, using majority vote and no independent pathology calibration. What happens on scanner-specific artifacts?',
          options: [
            'Error drops cubically to near zero on those artifacts.',
            'All three checkpoints share the same dataset blindspot, so majority voting confidently repeats the error.',
            'Running three copies guarantees regulatory compliance.',
            'Latency drops by 3x automatically.',
          ],
          correctIndex: 1,
          transferExplanation:
            'Without training/architecture diversity and an independent calibration check, correlated blindspots (high ρ_corr) cause all three copies to fail on the exact same artifact.',
          distractorDiagnosis:
            'Cubic error reduction (1 - p)^3 applies only when failure modes are statistically independent.',
        },
        {
          id: 'tr-03-structural-cad',
          domainKicker: 'Unseen Domain 2 · Automated Truss Synthesis',
          title: '2. Generation paired with deterministic physics check',
          scenario:
            'An engineering firm runs three distinct lightweight geometry generators ($0.001/run) and checks every candidate with a deterministic finite-element load solver before accepting any design.',
          options: [
            'Unsafe designs slip through whenever two generators hallucinate.',
            'The deterministic physics verifier rejects invalid candidates so any single valid specialist solution wins safely at low cost.',
            'A single unverified $2.00 generalist LLM is safer than a physics solver.',
            'The physics solver can invent missing soil survey data.',
          ],
          correctIndex: 1,
          transferExplanation:
            'Pairing diverse cheap generators with a sound deterministic verifier turns generation into verified search: only one candidate needs to satisfy the load equations.',
          distractorDiagnosis:
            'Even a sound solver still depends on accurate external soil inputs (Track 01 boundary!).',
        },
        {
          id: 'tr-03-quota-cliff',
          domainKicker: 'Unseen Domain 3 · Multi-Exchange Order Routing',
          title: '3. Pre-exhaustion quota rotation',
          scenario:
            'A trading gateway uses four zero-fee regional liquidity venues, each capped at 10,000 messages/hour. Why rotate traffic at 85% capacity instead of waiting for HTTP 429 rejections at 100%?',
          options: [
            'Waiting for 429 errors has zero latency or tail-drop impact.',
            'Rotating at 85% drains bursts smoothly into healthy sibling venues before hard rate-limit cliffs trigger tail-latency spikes.',
            'Rotating at 85% doubles the venue fee.',
            'HTTP 429 responses automatically retry for free in 0ms.',
          ],
          correctIndex: 1,
          transferExplanation:
            'Concurrent in-flight bursts overshoot a 99% full quota window; draining at an 85% threshold absorbs burst concurrency with zero 429 tail stalls (Falsifier F8).',
          distractorDiagnosis:
            'Reactive failover after hitting 100% still incurs round-trip timeout/retry penalties on in-flight packets.',
        },
      ],
    };
  }

  // -------------------------------------------------------------------------
  // TRACK 04: BAYESIAN EVSI & CAUSAL FALSIFICATION (PROSPECTOR-2100)
  // -------------------------------------------------------------------------
  if (trackId === 'bayesian_evsi_prospector') {
    const boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle] = [
      {
        id: 'benchmark_leakage',
        label: 'Admit Benchmark-Contaminated Claim',
        consequenceSummary:
          'Test-set memorization looks like a +18% breakthrough on public leaderboards but collapses on held-out production tasks.',
      },
      {
        id: 'confounder_hype_spike',
        label: 'Drop Rego R-005 Causal Gate Below 85%',
        consequenceSummary:
          'Raw mention volume and coordinated social hype leak straight into Mumchimp commercial briefs.',
      },
      {
        id: 'naive_frontier_burn',
        label: 'Revert to Unfiltered Frontier Scraping ($0.048/brief)',
        consequenceSummary:
          'Wastes 266x more compute summarizing low-EVSI duplicate announcements that never change a decision.',
      },
    ];

    const activeViolations = boundaryToggles.filter((t) => faultSet.has(t.id));
    const boundaryViolated = activeViolations.length > 0;
    const confGate = clamped;
    const leakPenalty = activeViolations.length * 22 + Math.max(0, (86 - confGate) * 0.9);
    const netYieldScore = Number(Math.max(8, 97.5 - leakPenalty).toFixed(1));

    const curvePoints: AcademyCurvePoint[] = [55, 65, 75, 85, 90, 96].map((gate) => {
      const baseLeak = Math.max(0, (86 - gate) * 0.9);
      const y = Math.max(8, 97.5 - baseLeak - activeViolations.length * 20);
      return {
        x: gate,
        xLabel: `${gate}%`,
        primaryY: Number(y.toFixed(1)),
        baselineY: Number(Math.max(25, 88 - Math.abs(88 - gate) * 0.6).toFixed(1)),
      };
    });

    const levelSynthesisMap: Record<AcademyLevel, string> = {
      novice:
        'Just because 10,000 posts repeat a claim doesn’t make it true. Prospector-2100 sends a skeptic agent to test alternative explanations before Mumchimp ever publishes a brief.',
      practitioner:
        'Expected Value of Sample Information (EVSI) ranks hypotheses by decision-value gain per sovereign micro-dollar, then requires P_causal >= 85% (Rego R-005) on held-out checks.',
      expert:
        'Eliminates all 5 legacy scraper failure modes (ERR-NAIVE-01..05), cutting research COGS from $0.048 to $0.00018/cycle (99.6%+ reduction) with SHA-256 deduplication.',
      founder:
        'Powers an autonomous 24/7 commercial & technical intelligence desk that feeds verified enterprise briefs into Mumchimp at near-zero marginal cost.',
    };

    return {
      trackId,
      indexLabel: '04',
      shortTitle: 'Bayesian EVSI & Causal Research',
      title: 'Expected Value of Sample Information & Adversarial Confounder Quarantine',
      level,
      linkedTab: 'mumchimp_research',
      linkedTabLabel: 'Open Prospector-2100 & Mumchimp',
      sharedPrincipleStatement:
        'The shared principle: correlation volume and leaderboard scores do not establish causal utility — autonomous research yields value only when confounders and leakage are falsified before syndication.',
      governingEquation:
        'EVSI(h) = [ E[max_a U(a, θ|z)] - max_a E[U(a, θ)] ] / Cost_sov  ∧  Admit ⇔ P_causal ≥ 0.85',
      sliderLabel: 'Adversarial Causal Confidence Gate (Rego R-005)',
      sliderUnit: '%',
      defaultSliderValue: 88,
      representations: [
        {
          id: 'physical_isomorphism',
          label: 'Representation I · Structural Analogy',
          title: 'Assay Fire-Testing Ore Before Minting Bullion',
          body: 'A gold mint does not weigh shiny Fool’s Gold (pyrite) by truckload volume; a cheap acid-and-density assay rejects pyrite at the gate before smelting.',
          explicitBoundaryLimit:
            'Analogy limit: an assay only catches impurities it physically tests for — novel synthetics require updated held-out falsifiers.',
        },
        {
          id: 'formal_boundary_law',
          label: 'Representation II · Formal Law',
          title: 'Decision-Theoretic EVSI & Backdoor Confounder Identification',
          body: 'If signal Z does not change optimal action a* (EVSI = 0) or is d-connected via confounder U (e.g., test-set leakage), P(Y | do(X)) ≠ P(Y | X). Admitting unadjusted correlations degrades downstream policy.',
          explicitBoundaryLimit:
            'Formal limit: observational data alone cannot prove causality without valid exclusion restrictions or controlled held-out interventions.',
        },
        {
          id: 'estate_production_binding',
          label: 'Representation III · Live Estate Engine',
          title: 'Prospector2100Engine + MagenticBrain Critic -> Mumchimp (F22)',
          body: 'Fires every Chronos H2 beat on $0.00 Sovereign / $0.00018 Spot lanes, quarantines confounder traps, and syndicates SHA-256 pinned briefs into Mumchimp.',
          explicitBoundaryLimit:
            'Operational limit: quarantined findings remain inspectable in audit logs rather than silently deleted, preventing blindspot hiding.',
        },
      ],
      levelSynthesis: levelSynthesisMap[level],
      boundaryToggles,
      activeFaultIds: Array.from(faultSet),
      boundaryViolated,
      primaryMetricLabel: 'Verified Commercial Epistemic Yield',
      primaryMetricValue: `${netYieldScore} pts`,
      secondaryMetricLabel: 'Active Research Faults',
      secondaryMetricValue: `${activeViolations.length} / 3`,
      equilibriumStatusLabel:
        confGate >= 85 && !boundaryViolated
          ? 'CAUSAL GATE LOCKED — ZERO CONFOUNDERS ADMITTED TO MUMCHIMP'
          : 'CONTAMINATION RISK — RESTORE >=85% CAUSAL GATE & LEAKAGE CHECK',
      activeViolationConsequences: activeViolations.map((v) => v.consequenceSummary),
      curvePoints,
      unseenTransferItems: [
        {
          id: 'tr-04-agritech-leak',
          domainKicker: 'Unseen Domain 1 · Satellite Crop Forecasting',
          title: '1. The suspiciously perfect forecast',
          scenario:
            'A crop-yield model achieves 99.4% accuracy on historical backtests, but an audit finds one input table included post-harvest tax adjustments updated months after harvest. What follows?',
          options: [
            'Deploy immediately because 99.4% backtest accuracy is proven.',
            'Average it with a second model trained on the same tax table.',
            'Quarantine the model for target leakage and re-evaluate strictly on point-in-time held-out data.',
            'Summarize the backtest in a customer newsletter first.',
          ],
          correctIndex: 2,
          transferExplanation:
            'Future information leaking into historical features (target/benchmark leakage) invalidates backtest accuracy; only point-in-time held-out evaluation measures real predictive power.',
          distractorDiagnosis:
            'Ensembling two models that share the same leaked feature preserves the exact same causal invalidity.',
        },
        {
          id: 'tr-04-evsi-budget',
          domainKicker: 'Unseen Domain 2 · Battery Chemistry Screening',
          title: '2. Zero-EVSI research spend',
          scenario:
            'An R&D lab spends $4,000/day running expensive simulations on a cathode material they have already ruled out on toxicity grounds regardless of conductivity results. What is the EVSI of those runs?',
          options: [
            'High, because the simulator uses frontier GPUs.',
            'Zero (negative net value after compute cost), because no simulation outcome can change the action taken.',
            'Positive as long as reports are formatted cleanly.',
            'Infinite if three agents summarize the PDFs.',
          ],
          correctIndex: 1,
          transferExplanation:
            'By definition, Expected Value of Sample Information (EVSI) is zero whenever the sampled signal cannot alter the downstream decision — making any non-zero compute spend pure waste.',
          distractorDiagnosis:
            'Compute cost or formatting polish never creates decision value where action invariance holds.',
        },
        {
          id: 'tr-04-retail-confounder',
          domainKicker: 'Unseen Domain 3 · Retail Demand Attribution',
          title: '3. Seasonal confounder vs causal lift',
          scenario:
            'An e-commerce agent changes button color on Black Friday and observes a 4x sales jump, claiming the color caused +300% conversion. What is missing?',
          options: [
            'More social media scraping about button colors.',
            'Controlling for the Black Friday demand confounder via a randomized holdout or counterfactual control group.',
            'Rewriting the CSS in Rust.',
            'Lowering the confidence threshold to 50%.',
          ],
          correctIndex: 1,
          transferExplanation:
            'Holiday traffic is a classic common-cause confounder affecting both timing of the change and sales volume; separating causal lift requires a contemporaneous holdout or valid counterfactual.',
          distractorDiagnosis:
            'Raw before/after correlation during a macro demand shock tells nothing about treatment effect.',
        },
      ],
    };
  }

  // -------------------------------------------------------------------------
  // TRACK 05: GF(2^8) REED-SOLOMON RS(3,8) CONTINUITY
  // -------------------------------------------------------------------------
  if (trackId === 'reed_solomon_continuity') {
    const boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle] = [
      {
        id: 'sub_quorum_2_of_8',
        label: 'Destroy 6 of 8 Clouds (Only 2 Shards Left < k=3)',
        consequenceSummary:
          'A degree-2 polynomial over GF(2^8) has 3 unknown coefficients — 2 shards leave 256 equally valid solutions per byte (fails closed).',
      },
      {
        id: 'corrupt_png_crc',
        label: 'Flip Carrier Byte Without Validating CRC32 / MAC',
        consequenceSummary:
          'Interpolating unauthenticated corrupted bytes produces garbage plaintext unless CRC32 & PBKDF2-HMAC-SHA256 reject tampered shards first.',
      },
      {
        id: 'stale_zombie_epoch',
        label: 'Disable Monotonic Fencing Token on Resurrection',
        consequenceSummary:
          'A resurrected node from an older spore epoch can overwrite newer WAL transactions (split-brain regression).',
      },
    ];

    const activeViolations = boundaryToggles.filter((t) => faultSet.has(t.id));
    const boundaryViolated = activeViolations.length > 0;
    const q = (100 - clamped) / 100;
    let survivalProb = 0;
    for (let k = 3; k <= 8; k++) {
      survivalProb += chooseCount(8, k) * Math.pow(1 - q, k) * Math.pow(q, 8 - k);
    }
    const survivalPct = faultSet.has('sub_quorum_2_of_8')
      ? 0
      : boundaryViolated
        ? Number((survivalProb * 35).toFixed(2))
        : Number((survivalProb * 100).toFixed(4));

    const curvePoints: AcademyCurvePoint[] = [5, 15, 25, 35, 45, 55].map((failPct) => {
      const fq = failPct / 100;
      let s = 0;
      for (let k = 3; k <= 8; k++) {
        s += chooseCount(8, k) * Math.pow(1 - fq, k) * Math.pow(fq, 8 - k);
      }
      return {
        x: failPct,
        xLabel: `${failPct}% out`,
        primaryY: faultSet.has('sub_quorum_2_of_8')
          ? 0
          : boundaryViolated
            ? Number((s * 40).toFixed(1))
            : Number((s * 100).toFixed(2)),
        baselineY: Number(((1 - fq) * 100).toFixed(1)),
      };
    });

    const levelSynthesisMap: Record<AcademyLevel, string> = {
      novice:
        'Three points uniquely lock a parabola: split state across 8 clouds so any 3 survivors rebuild 100% — but if only 2 survive, the system honestly halts instead of guessing.',
      practitioner:
        'An 8x3 Vandermonde matrix over GF(2^8) guarantees all C(8,3) = 56 3-shard subsets are invertible, paired with CRC32 carrier checks and HMAC authentication.',
      expert:
        'Combines 4KB Ed25519 spores, 200,000-iteration PBKDF2-HMAC-SHA256 GENVAULT1 envelopes, and monotonic fencing tokens so resurrected nodes never regress live WAL state.',
      founder:
        'Delivers sovereign catastrophe insurance: Meridian survives simultaneous loss of 5 cloud providers while remaining mathematically candid about k=3 quorum limits.',
    };

    return {
      trackId,
      indexLabel: '05',
      shortTitle: 'GF(2^8) Reed-Solomon Continuity',
      title: 'Vandermonde RS(3,8) Erasure Coding, Quorum Bounds & Epoch Fencing',
      level,
      linkedTab: 'genesis_ttt',
      linkedTabLabel: 'Open I-8088 Cephalopod Lab',
      sharedPrincipleStatement:
        'The shared principle: erasure coding guarantees bit-exact survival up to n - k erasures, but strictly requires >= k authenticated shards and monotonic fencing upon recovery.',
      governingEquation:
        'Recover(S) ⇔ |ValidShards| ≥ 3 ∧ MAC_ok(GENVAULT1) ∧ Fence_new > Fence_committed',
      sliderLabel: 'Per-Cloud Availability Rate (1 - q)',
      sliderUnit: '%',
      defaultSliderValue: 82,
      representations: [
        {
          id: 'physical_isomorphism',
          label: 'Representation I · Structural Analogy',
          title: 'Three Survey Benchmarks Locking a Parabolic Arch',
          body: 'Any 3 intact survey markers out of 8 along a parabolic bridge let engineers redraw the exact arch; 2 markers leave infinitely many curves, and a moved marker ruins the fit unless inspected first.',
          explicitBoundaryLimit:
            'Analogy limit: geometric markers do not protect confidentiality — real spores still require authenticated encryption keys.',
        },
        {
          id: 'formal_boundary_law',
          label: 'Representation II · Formal Law',
          title: 'GF(2^8) MDS Vandermonde Invertibility & Quorum Lower Bound',
          body: 'Maximum Distance Separable RS(k=3, n=8) has minimum Hamming distance d = n - k + 1 = 6, correcting up to 5 erasures. Below k=3 erasures exceed d - 1, so rank(V_sub) < 3 and unique inversion is impossible.',
          explicitBoundaryLimit:
            'Formal limit: unauthenticated interpolation treats silent byte corruption (errors, not erasures) as valid points unless CRC/HMAC filters shards first.',
        },
        {
          id: 'estate_production_binding',
          label: 'Representation III · Live Estate Engine',
          title: 'genesisSporeTtt.ts (I-8088 Panspermia Simulator, F18)',
          body: 'Verifies all C(8,3) = 56 shard combinations bit-exact, enforces PNG CRC32 + 200k-iter PBKDF2 MAC, fails closed (HTTP 409) below 3 shards, and increments fencing tokens on heal.',
          explicitBoundaryLimit:
            'Operational limit: correlated simultaneous credential compromise across all 8 clouds still requires offline cold-vault key rotation.',
        },
      ],
      levelSynthesis: levelSynthesisMap[level],
      boundaryToggles,
      activeFaultIds: Array.from(faultSet),
      boundaryViolated,
      primaryMetricLabel: 'Authenticated Quorum Survival',
      primaryMetricValue: `${survivalPct}%`,
      secondaryMetricLabel: 'Continuity Boundary Faults',
      secondaryMetricValue: `${activeViolations.length} / 3`,
      equilibriumStatusLabel: boundaryViolated
        ? 'QUORUM / FENCE BOUNDARY VIOLATED — FAIL-CLOSED HALT ENGAGED'
        : 'ALL 56 SUBSETS INVERTIBLE — 5-CLOUD EXTINCTION SAFE',
      activeViolationConsequences: activeViolations.map((v) => v.consequenceSummary),
      curvePoints,
      unseenTransferItems: [
        {
          id: 'tr-05-subsea-quorum',
          domainKicker: 'Unseen Domain 1 · Subsea Custody Vault',
          title: '1. Below the k-of-n threshold',
          scenario:
            'A clearinghouse splits a master settlement ledger using RS(k=4, n=9) across nine coastal vaults. A tsunami severs six vaults, leaving three intact authenticated shards. Can the ledger be reconstructed from those three shards alone?',
          options: [
            'Yes, because three shards worked in RS(3,8).',
            'No — with k=4, three shards are below quorum and cannot uniquely determine a degree-3 polynomial without at least one additional shard or backup.',
            'Yes, if the server retries interpolation 1,000 times.',
            'Yes, if the remaining three vaults pass a ping check.',
          ],
          correctIndex: 1,
          transferExplanation:
            'In any RS(k, n) code, k is the strict information-theoretic minimum number of shards required to invert the k×k Vandermonde submatrix; 3 < 4 leaves one free degree of freedom per symbol.',
          distractorDiagnosis:
            'Memorizing "3 shards" from RS(3,8) without transferring the general threshold k fails on RS(4,9).',
        },
        {
          id: 'tr-05-corrupt-shard',
          domainKicker: 'Unseen Domain 2 · Archival Tape Recovery',
          title: '2. Erasure vs unauthenticated corruption',
          scenario:
            'Four shards of an RS(3,8) archive are retrieved, but Shard #2 suffered silent bit-rot in transit and checksum verification was skipped before feeding Shards #0, #1, and #2 into the decoder. What happens?',
          options: [
            'The decoder outputs a corrupted reconstruction because it interpolated through a silently altered point instead of discarding Shard #2 and using intact Shard #3.',
            'Galois fields automatically ignore bit-rot without checksums when given exactly k=3 shards.',
            'The file size shrinks by 50%.',
            'Encryption keys rotate automatically.',
          ],
          correctIndex: 0,
          transferExplanation:
            'Given exactly k shards, polynomial interpolation fits every supplied point; per-shard CRC/MAC verification is essential to convert silent corruption into a known erasure so an intact 4th shard (#3) is used instead.',
          distractorDiagnosis:
            'Without authentication or extra parity syndrome decoding, k-point interpolation blindly fits corrupted bytes.',
        },
        {
          id: 'tr-05-zombie-leader',
          domainKicker: 'Unseen Domain 3 · Automated Rail Dispatch',
          title: '3. The resurrected stale controller',
          scenario:
            'Regional Controller A goes offline at epoch #41; Controller B takes over at epoch #42 and clears three train movements. Controller A then reboots from its valid epoch #41 backup and sends a track command. What prevents a collision state?',
          options: [
            'Controller A’s backup had a valid SHA-256 hash, so its command should execute.',
            'Track switches must enforce monotonic fencing tokens (>= #42) and reject stale epoch #41 writes until A reconciles current state.',
            'Running local unit tests on Controller A before boot.',
            'Compressing epoch #41 into a smaller packet.',
          ],
          correctIndex: 1,
          transferExplanation:
            'A cryptographically valid backup from an older epoch is still causally stale; monotonic fencing tokens at the storage/actuator boundary block zombie writes from overwriting newer state.',
          distractorDiagnosis:
            'Valid hashes on historical snapshots prove past authenticity, not current write authority.',
        },
      ],
    };
  }

  // -------------------------------------------------------------------------
  // TRACK 06: CHRONOS HARMONICS & DECLARATIVE REGO POLICY-AS-CODE
  // -------------------------------------------------------------------------
  const boundaryToggles: [BoundaryFaultToggle, BoundaryFaultToggle, BoundaryFaultToggle] = [
    {
      id: 'imperative_policy_bypass',
      label: 'Scatter Inline if(isAdmin) Bypassing Rego',
      consequenceSummary:
        'Imperative policy branches drift across services and bypass constitutional audit trails (flagged immediately by Rule R-008).',
    },
    {
      id: 'client_http_polling',
      label: 'Introduce Client setInterval HTTP Polling',
      consequenceSummary:
        'Violates Instruction I-8090 & Rego R-001, creating thundering-herd load and stale split-screen telemetry.',
    },
    {
      id: 'unjoined_orphan_cron',
      label: 'Spawn Unmonitored Background Worker Outside Chronos',
      consequenceSummary:
        'Orphaned cron tasks execute outside harmonic rings H0..H4 and break the 8-leaf SHA-256 Merkle synchronicity proof.',
    },
  ];

  const activeViolations = boundaryToggles.filter((t) => faultSet.has(t.id));
  const boundaryViolated = activeViolations.length > 0;
  const regoCoveragePct = boundaryViolated
    ? Number(Math.max(20, clamped - activeViolations.length * 24).toFixed(1))
    : clamped;

  const curvePoints: AcademyCurvePoint[] = [55, 65, 75, 85, 92, 98].map((cov) => ({
    x: cov,
    xLabel: `${cov}%`,
    primaryY: boundaryViolated
      ? Number(Math.max(18, cov - activeViolations.length * 22).toFixed(1))
      : cov,
    baselineY: Number((100 - (100 - cov) * 0.85).toFixed(1)),
  }));

  const levelSynthesisMap: Record<AcademyLevel, string> = {
    novice:
      'Every part of the platform marches to one shared metronome (Chronos) and checks one rulebook (Rego) before changing anything — no secret backdoors or out-of-step timers.',
    practitioner:
      'Harmonic beat divisors (1x, 2x, 4x, 8x) prevent thundering-herd contention, while pre-commit Rego evaluation returns HTTP 422 before any unsafe mutation touches state.',
    expert:
      'Folds 5 harmonic rings (H0..H4) and 8 subsystem state digests into a deterministic SHA-256 Merkle root every beat alongside Rule R-008 static policy-extraction checks.',
    founder:
      'Guarantees permanent UHNW private-office governance: you configure the estate from one signed Founder Plane with zero policy drift forever.',
  };

  return {
    trackId,
    indexLabel: '06',
    shortTitle: 'Chronos Harmonics & Rego Policy',
    title: 'Multi-Ring Harmonic Synchronicity & Declarative Rego Governance',
    level,
    linkedTab: 'founder_plane',
    linkedTabLabel: 'Open Founder & Rego Plane',
    sharedPrincipleStatement:
      'The shared principle: declarative policy and harmonic scheduling guarantee whole-estate coherence only when zero imperative backdoors bypass the policy gate and zero background loops run unjoined.',
    governingEquation:
      'Coherent(t) ⇔ |deny_Rego(ΔConfig)| = 0 ∧ ∀s ∈ Organs: Phase(s, Beat_t) = 0 ∧ Polling = 0',
    sliderLabel: 'Declarative Rego Gate & Harmonic Coverage',
    sliderUnit: '%',
    defaultSliderValue: 96,
    representations: [
      {
        id: 'physical_isomorphism',
        label: 'Representation I · Structural Analogy',
        title: 'Mechanical Escapement Gear Train & Interlock Key',
        body: 'In a chronometer, the seconds, minutes, and hours wheels gear directly off one escapement at exact integer ratios, while a mechanical railway signal interlock physically blocks conflicting track levers before movement.',
        explicitBoundaryLimit:
          'Analogy limit: a railway interlock only protects levers wired through its frame — an unwired manual siding switch still causes collisions.',
      },
      {
        id: 'formal_boundary_law',
        label: 'Representation II · Formal Law',
        title: 'Total Pre-Commit Mediation & Binary Merkle Commitment',
        body: 'Reference monitor soundness requires complete mediation: ∀ mutation m, Apply(m) executes iff EvaluateRego(m).allow == true. Synchronicity root R_t = Merkle(L_0..L_7) commits all 8 estate domains at beat t.',
        explicitBoundaryLimit:
          'Formal limit: Rego guarantees policy consistency wrt declared inputs; if an upstream sensor lies about its input state, garbage-in still requires producer verification.',
      },
      {
        id: 'estate_production_binding',
        label: 'Representation III · Live Estate Engine',
        title: 'FounderConfigEngine (R-001..R-010) & Chronos SSE Bus (F23, F24)',
        body: 'Evaluates 10 constitutional Rego rules pre-commit (HTTP 422 fail-closed), audits TypeScript snippets via classifyCodeForRegoGovernance, and streams beat snapshots over SSE.',
        explicitBoundaryLimit:
          'Operational limit: client UI sliders preview state locally, but authoritative estate behavior changes only when signed server-side revision # increments.',
      },
    ],
    levelSynthesis: levelSynthesisMap[level],
    boundaryToggles,
    activeFaultIds: Array.from(faultSet),
    boundaryViolated,
    primaryMetricLabel: 'Effective Constitutional Mediation',
    primaryMetricValue: `${regoCoveragePct}%`,
    secondaryMetricLabel: 'Governance Bypass Faults',
    secondaryMetricValue: `${activeViolations.length} / 3`,
    equilibriumStatusLabel: boundaryViolated
      ? 'BYPASS / DRIFT DETECTED — CLOSE IMPERATIVE BACKDOOR & JOIN CHRONOS'
      : '10/10 REGO RULES MEDIATED · 0.00 RAD HARMONIC PHASE LOCK',
    activeViolationConsequences: activeViolations.map((v) => v.consequenceSummary),
    curvePoints,
    unseenTransferItems: [
      {
        id: 'tr-06-bank-bypass',
        domainKicker: 'Unseen Domain 1 · Core Banking Entitlements',
        title: '1. The incomplete reference monitor',
        scenario:
          'A digital bank writes a clean Rego policy bundle for wire limits, enforced on mobile transfers, but an internal partner API checks wire limits using a hardcoded `if (partnerTier > 2)` branch in Go. What holds?',
        options: [
          'The bank has 100% policy-as-code assurance because the Rego file passed unit tests.',
          'Complete mediation is broken: updating the Rego wire limit leaves the hardcoded Go branch drifting until partner API admission also delegates to Rego.',
          'Adding a green SOC2 badge to the partner portal fixes the drift.',
          'Go `if` statements automatically sync with Rego files.',
        ],
        correctIndex: 1,
        transferExplanation:
          'Policy-as-code provides a single source of truth only under complete mediation — any inline imperative policy branch outside the policy engine creates silent governance drift (Rule R-008).',
        distractorDiagnosis:
          'Unit-testing a policy file proves the rules inside it, not that every service endpoint actually calls it.',
      },
      {
        id: 'tr-06-substation-polling',
        domainKicker: 'Unseen Domain 2 · Power Grid Telemetry',
        title: '2. Harmonic push vs uncoordinated polling',
        scenario:
          '400 operator consoles each run an independent 500ms `setInterval` HTTP poll against a central substation controller, causing CPU spikes every time an alarm fires. What architectural shift eliminates the polling storm while keeping operators live?',
        options: [
          'Randomize `setInterval` between 400ms and 600ms and add more spinners.',
          'Stream server-authoritative state transitions over a shared SSE/event push channel synchronized to the controller’s harmonic beat.',
          'Cache stale alarm states for 24 hours so consoles never update.',
          'Hide CPU metrics from the operator dashboard.',
        ],
        correctIndex: 1,
        transferExplanation:
          'Server-authoritative SSE push synchronized to deterministic harmonic beats scales O(1) in controller state computation rather than O(N_clients × poll_rate), eliminating client polling storms (I-8090).',
        distractorDiagnosis:
          'Jittering client timers still multiplies redundant HTTP requests per connected console.',
      },
      {
        id: 'tr-06-orphan-daemon',
        domainKicker: 'Unseen Domain 3 · Clearinghouse Settlement',
        title: '3. The unjoined background script',
        scenario:
          'Seven settlement services commit their state hashes into an hourly Merkle audit root, while an eighth fee-rebate cron runs privately on a developer VM with no beat binding or receipt emission. What can the Merkle root prove?',
        options: [
          'It proves all eight services including the private VM fee rebates are accurate.',
          'It proves state coherence across the seven joined leaves only; the unjoined eighth script remains a blind spot until bound into the beat and ledger.',
          'Hashing the seven leaves twice covers the eighth service.',
          'Nothing at all about any of the seven joined services.',
        ],
        correctIndex: 1,
        transferExplanation:
          'A cryptographic Merkle stamp commits strictly to the leaves folded into its tree; any unjoined subsystem outside the scheduler and receipt bus must either be joined or explicitly surfaced as BLIND.',
        distractorDiagnosis:
          'Repeating hashes adds zero information about an external uninstrumented process.',
      },
    ],
  };
}

/**
 * Evaluates a learner's 3-item unseen transfer submission strictly AFTER all 3 answers
 * are selected, issuing a SHA-256 pilot receipt and preserving strict research-pilot honesty.
 */
export function evaluateUnseenTransferPilot(params: {
  trackId: StandoutTrackId;
  selectedAnswers: Record<string, number | undefined>;
}): TransferPilotEvaluation {
  const sim = simulateStandoutAcademyTrack({
    trackId: params.trackId,
    level: 'practitioner',
    sliderParam: 86,
  });

  const unanswered = sim.unseenTransferItems.filter((item) => {
    const pick = params.selectedAnswers[item.id];
    return typeof pick !== 'number' || pick < 0 || pick >= item.options.length;
  });

  const epistemicDisclaimer =
    'Research pilot · Three objective unseen transfer items · Measures immediate structural transfer on this novel scenario set only — no claim of established long-term mastery or certified teaching efficacy without longitudinal cohort evidence.';

  if (unanswered.length > 0) {
    return {
      trackId: params.trackId,
      submittedAtUtc: new Date().toISOString(),
      complete: false,
      validationError: `Please select an answer for all 3 unseen transfer items before scoring (${unanswered.length} remaining).`,
      score: 0,
      totalItems: 3,
      epistemicDisclaimer,
      receiptSha256: '',
      itemResults: [],
    };
  }

  const itemResults = sim.unseenTransferItems.map((item) => {
    const selectedOptionIndex = params.selectedAnswers[item.id] as number;
    const correct = selectedOptionIndex === item.correctIndex;
    return {
      itemId: item.id,
      title: item.title,
      selectedOptionIndex,
      correctOptionIndex: item.correctIndex,
      correct,
      selectedText: item.options[selectedOptionIndex],
      correctText: item.options[item.correctIndex],
      transferExplanation: item.transferExplanation,
      distractorDiagnosis: item.distractorDiagnosis,
    };
  });

  const score = itemResults.filter((r) => r.correct).length;
  const submittedAtUtc = new Date().toISOString();
  const receiptSha256 = pureSha256Hex(
    `${params.trackId}|${score}/3|${itemResults.map((r) => r.selectedOptionIndex).join(',')}|${submittedAtUtc}`
  );

  return {
    trackId: params.trackId,
    submittedAtUtc,
    complete: true,
    validationError: null,
    score,
    totalItems: 3,
    epistemicDisclaimer,
    receiptSha256,
    itemResults,
  };
}
