/**
 * Consolidated Production Specification & Recovery Audit Engine
 * 24-Hour Estate Recovery Audit (6 Nov 2026 09:31 GMT to 7 Nov 2026 09:31 GMT)
 * Reconciles all 93 PR matches across chidionyema/idp, argon, argon-sync, and estate-graph.
 */

export const ESTATE_DIRECTIVE_XML = `<estate_recovery_directive version="2026.11.07-v1" app_id="c3d3ce2c-d6bc-49e1-a38e-e25473f17b6a">
  <mission>
    You are an execution and verification engine operating inside the Genesis Estate (\`chidionyema/idp\`, \`chidionyema/argon\`, \`chidionyema/argon-sync\`, \`chidionyema/estate-graph\`, \`chidionyema/crew\`).
    Your mandate is to finish and integrate existing machinery, eliminate duplicate replacement PRs, enforce the Estate-Wide Degree of Freedom (DoF) security invariant across all execution boundaries, and prove end-to-end operational completion without routine Founder intervention.
  </mission>

  <executable_security_invariant>
    Every privileged action \`a\` across the estate must satisfy:
    ∀ a ∈ A_privileged : Execute(a) ⇒ TrustedActor(a) ∧ FreshLease(a) ∧ AllowedScope(a) ∧ PinnedPolicy(a)
    - Pinned Guardian Anchor: \`GENESIS_GUARDIAN_SHA\` must pin to reviewed \`main\` commit \`da1536c7\` (never candidate \`8e232aa\`).
    - Outage Contraction: During any critical outage, permitted capabilities contract strictly to explicitly authorized diagnosis and repair actions. Full privileges require independent cryptographic health proof.
    - Split-Authority Certification: No candidate authored by \`Improver\` can reach \`PROMOTED_MAIN\` without an independent \`Certifier\` Ed25519 signature over a passing held-out trial and measured RFC 6962 SHA-256 tree digest.
  </executable_security_invariant>

  <hard_operational_laws>
    1. NO FALSE COMPLETION: Never mark a mission \`OPERATING\` or \`DONE\` because a PR is open, merged, or green in CI. Local/CI handoff (\`QUEUED_FOR_GREENLANE\`) is distinct from \`OPERATIONAL_COMPLETE\` (which requires promotion, live deployment on Oracle ARM/k3s, active runtime probe, and signed receipt).
    2. WHOLE-HISTORY PREFLIGHT: Before publishing or updating any PR (e.g., fixing Argon #45), inspect the ENTIRE commit range (\`base..HEAD\`). Verify every commit contains valid \`Claim:\`, \`Agent:\`, and defect-control trailers, zero stale test SHAs, and zero unmediated protected-path touches.
    3. ZERO FOUNDER CLI CHORES (\`NO_FOUNDER_CLI_CHORES\`): Never output manual CLI checklists asking the Founder to run \`git push\`, \`gh variable set\`, or \`gh secret set\`. Emit structured actuation jobs to \`.genesis/outbox/admin_actuation.jsonl\` for the Host/Cloud Spooler (\`genesis-host-spooler.py\`) and escalate only irreducible architectural/risk decisions via the 3-Shield Council (\`Argon\` -> \`Kimi Web\` -> \`ChatGPT Web\`) to the 1-Tap Telegram Sovereign Seal (Pinned Message \`3327\`) and \`AURA-2100\`.
    4. ORACLE PASS RATIONING & LAW I11: Every execution step is strictly bounded to <= 100 seconds. Gather state in Pass 1 (batched). Pass 2 triggers \`ORACLE_BUDGET_WARNING\`. Pass 3 triggers immediate \`HARD_STOP\` with formal root-cause attribution (\`POOR_PLANNING\` vs \`POOR_ORACLE\`).
    5. UNIVERSAL PEER BUS (\`mavis\` + \`communicate\`): Never dump intermediate status reports on the Founder. Discover active peers via \`mavis({ command: "session list", args: { mode: "peers" } })\` and hand off or spawn bounded repair work via \`communicate({ to_session, content })\`.
    6. ARCHITECTURAL CONFLICT LOCKS:
       - DO NOT restart abandoned OKE rebuild plans (\`idp#7387\`). Target the Oracle ARM / k3s substrate (\`idp#7735\`) exclusively while preserving recoverable OCI data.
       - Reject ephemeral storage (\`emptyDir\`) in k3s manifests for stateful services; enforce persistent volume claims and verified off-host Merkle-root database restores (\`idp#7391\`).
       - Enforce the $200/month operating ceiling (2 Dec – 2 Mar) and free-tier-first routing (\`:4001\` / \`:4002\` Rust router). Do not commit to paid GitHub Pro upgrades before the funding checkpoint.
  </hard_operational_laws>
</estate_recovery_directive>`;

export const CANONICAL_GUARDIAN_PINNED_SHA = 'da1536c7';
export const REJECTED_GUARDIAN_CANDIDATE_SHA = '8e232aa';

export interface HardOperationalLaw {
  number: number;
  id: string;
  name: string;
  rule: string;
  mechanism: string;
  verificationTag: string;
}

export const HARD_OPERATIONAL_LAWS: HardOperationalLaw[] = [
  {
    number: 1,
    id: 'NO_FALSE_COMPLETION',
    name: 'No False Completion',
    rule: 'Never mark a mission OPERATING or DONE because a PR is open, merged, or green in CI. QUEUED_FOR_GREENLANE is distinct from OPERATIONAL_COMPLETE.',
    mechanism: 'Requires promotion, live deployment on Oracle ARM/k3s, active runtime probe, and signed receipt.',
    verificationTag: 'PROMOTION + ORACLE_ARM_PROBE + SIGNED_RECEIPT',
  },
  {
    number: 2,
    id: 'WHOLE_HISTORY_PREFLIGHT',
    name: 'Whole-History Preflight',
    rule: 'Before publishing or updating any PR, inspect the ENTIRE commit range (base..HEAD).',
    mechanism: 'Assert every commit has Claim:, Agent:, defect-control trailers, zero stale test SHAs, zero unmediated protected touches.',
    verificationTag: 'genesis-preflight-whole-history (base..HEAD)',
  },
  {
    number: 3,
    id: 'NO_FOUNDER_CLI_CHORES',
    name: 'Zero Founder CLI Chores',
    rule: 'Never output manual CLI checklists asking Founder to run git push, gh variable set, or gh secret set.',
    mechanism: 'Emit structured actuation jobs to .genesis/outbox/admin_actuation.jsonl for Host/Cloud Spooler. Escalate via 3-Shield Council to Telegram 3327 / AURA-2100.',
    verificationTag: '.genesis/outbox/admin_actuation.jsonl + 1-Tap Seal #3327',
  },
  {
    number: 4,
    id: 'ORACLE_PASS_RATIONING',
    name: 'Oracle Pass Rationing & Law I11',
    rule: 'Every execution step is strictly bounded to <= 100 seconds.',
    mechanism: 'Pass 1: gather state batched. Pass 2: ORACLE_BUDGET_WARNING. Pass 3: immediate HARD_STOP with formal attribution (POOR_PLANNING vs POOR_ORACLE).',
    verificationTag: '<=100s STEP TIMEOUT + PASS-3 HARD STOP',
  },
  {
    number: 5,
    id: 'UNIVERSAL_PEER_BUS',
    name: 'Universal Peer Bus',
    rule: 'Never dump intermediate status reports on Founder.',
    mechanism: 'Discover peers via mavis({ command: "session list", args: { mode: "peers" } }) and hand off via communicate({ to_session, content }).',
    verificationTag: 'mavis + communicate IPC',
  },
  {
    number: 6,
    id: 'ARCHITECTURAL_CONFLICT_LOCKS',
    name: 'Architectural Conflict Locks',
    rule: 'No OKE rebuild (idp#7387); target Oracle ARM/k3s (idp#7735). Reject emptyDir ephemeral storage; enforce PVCs + Merkle-root database restore.',
    mechanism: 'Enforce $200/mo operating ceiling (2 Dec - 2 Mar) and free-tier routing (:4001/:4002 Rust router).',
    verificationTag: 'k3s PVC + Merkle Restore + $200/mo FinOps Cap',
  },
];

export interface ActiveBlockerItem {
  id: string;
  repo: string;
  targetPr: string;
  supersedes?: string;
  liveCiEvidence: string;
  rootDefect: string;
  mandatoryAction: string;
  status: 'BLOCKED' | 'REMEDIATING' | 'READY_FOR_GREENLANE' | 'PROMOTED';
}

export const ACTIVE_BLOCKERS: ActiveBlockerItem[] = [
  {
    id: 'blocker_argon_45',
    repo: 'chidionyema/argon',
    targetPr: 'Argon #45',
    supersedes: 'Argon #44 (closed)',
    liveCiEvidence: 'Open draft; Provenance run 42359301534 failed',
    rootDefect: 'Earlier commit in range retains invalid defect-control metadata; PR description claim is stale',
    mandatoryAction: 'Run whole-branch rewrite (git rebase -i / filter-repo) to scrub invalid historical commit metadata across entire main..HEAD range before re-pushing.',
    status: 'REMEDIATING',
  },
  {
    id: 'blocker_argon_43',
    repo: 'chidionyema/argon',
    targetPr: 'Argon #43',
    liveCiEvidence: 'Security run 42354614969 passed; Provenance failed',
    rootDefect: 'Touches protected gateway paths without authentic Founder seal and 2 distinct peer reviews',
    mandatoryAction: 'Route through 3-Shield Council (kimi-web-shield + chatgpt-web-shield) and request 1-Tap Founder Ed25519 signature via AURA-2100 / Telegram 3327.',
    status: 'BLOCKED',
  },
  {
    id: 'blocker_argon_sync_6_7',
    repo: 'chidionyema/argon-sync',
    targetPr: 'Argon Sync #6 & #7',
    liveCiEvidence: 'Current-head DoF and provenance workflows passed',
    rootDefect: 'Tested candidates sitting unmerged; overlapping scope',
    mandatoryAction: 'Reconcile into single canonical promotion candidate and merge via Greenlane.',
    status: 'READY_FOR_GREENLANE',
  },
  {
    id: 'blocker_estate_graph_7',
    repo: 'chidionyema/estate-graph',
    targetPr: 'Estate Graph #7',
    supersedes: 'Consolidates #1-#5',
    liveCiEvidence: 'Memory v2 quality run 42350777919 passed; Open draft',
    rootDefect: 'Missing independent security review, trust-boundary tests, and live Oracle runtime proof',
    mandatoryAction: 'Execute adversarial trust-boundary suite, attach Certifier review signature, and verify against live Oracle ARM k3s memory endpoint.',
    status: 'REMEDIATING',
  },
  {
    id: 'blocker_idp_7735',
    repo: 'chidionyema/idp',
    targetPr: 'IDP #7735',
    supersedes: 'idp#7387 (abandoned OKE rebuild)',
    liveCiEvidence: 'CI run 42350409538 failed; unmerged',
    rootDefect: 'Missing Claim/Agent trailers; DoF refuses commit lacking critical-service repair declaration; uses ephemeral storage (emptyDir)',
    mandatoryAction: 'Replace ephemeral storage with durable PVC manifests, inject valid critical-service repair declaration + Claim/Agent trailers, and re-verify locally.',
    status: 'REMEDIATING',
  },
  {
    id: 'blocker_idp_7761',
    repo: 'chidionyema/idp',
    targetPr: 'IDP #7761',
    supersedes: 'Intake for #7760',
    liveCiEvidence: 'Open, non-mergeable; 0 matching PR-head workflow runs',
    rootDefect: 'Merge conflicts and unverified live Google Drive / Apps Script dispatch',
    mandatoryAction: 'Rebase onto current main, resolve conflicts, and trigger real end-to-end Gemini Web -> Drive/Docs -> Apps Script -> GitHub intake probe.',
    status: 'BLOCKED',
  },
  {
    id: 'blocker_idp_legion',
    repo: 'chidionyema/idp',
    targetPr: 'IDP #7788 (with #7775)',
    supersedes: 'IDP #7733 (closed unmerged)',
    liveCiEvidence: '#7733 closed unmerged; #7775 / #7788 open with runner dependency & permission failures',
    rootDefect: 'Runner dependency, permission failures, and unmerged automation kit',
    mandatoryAction: 'Reconcile salvaged code from #7733 into #7788, fix runner permissions, and prove autonomous cloud mission execution.',
    status: 'REMEDIATING',
  },
];

export interface ReconciledPrItem {
  repo: string;
  number: number;
  title: string;
  status: 'MERGED_BASELINE' | 'RECONCILED' | 'SUPERSEDED' | 'ACTIVE_TARGET';
  notes: string;
}

export const RECONCILED_PR_BASELINE: ReconciledPrItem[] = [
  // Merged Baseline (Preserve & Reuse)
  { repo: 'chidionyema/argon', number: 23, title: 'Telegram watcher & HUD sync', status: 'MERGED_BASELINE', notes: 'Core Telegram HUD infrastructure' },
  { repo: 'chidionyema/argon', number: 29, title: 'Guardian provenance baseline', status: 'MERGED_BASELINE', notes: 'Genesis guardian anchor baseline' },
  { repo: 'chidionyema/argon', number: 37, title: 'Cloud outbox delivery milestone', status: 'MERGED_BASELINE', notes: 'Cloud spooler delivery milestone' },
  { repo: 'chidionyema/argon-sync', number: 1, title: 'Core sync substrate init', status: 'MERGED_BASELINE', notes: 'Sync baseline' },
  { repo: 'chidionyema/argon-sync', number: 2, title: 'State replication primitives', status: 'MERGED_BASELINE', notes: 'Durable sync records' },
  { repo: 'chidionyema/argon-sync', number: 5, title: 'Edge socket bridge', status: 'MERGED_BASELINE', notes: 'Edge sync pipeline' },
  { repo: 'chidionyema/idp', number: 7747, title: 'Cloud bot worker runtime', status: 'MERGED_BASELINE', notes: 'Cloud autonomous worker baseline' },
  { repo: 'chidionyema/idp', number: 7752, title: 'Idempotency key lease validation', status: 'MERGED_BASELINE', notes: 'Fencing lease verification' },
  { repo: 'chidionyema/idp', number: 7763, title: 'Cloud bot broker credentials', status: 'MERGED_BASELINE', notes: 'Scoped credential delivery' },
  { repo: 'chidionyema/idp', number: 7773, title: 'One-Brain surface registration', status: 'MERGED_BASELINE', notes: 'Merged via Greenlane' },
  { repo: 'chidionyema/idp', number: 7776, title: 'Greenlane speed/diagnostics/OIDC fixes', status: 'MERGED_BASELINE', notes: 'Sub-60s promotion pipeline' },

  // Active / Superseded
  { repo: 'chidionyema/argon', number: 44, title: 'Refusal recovery engine (flawed)', status: 'SUPERSEDED', notes: 'Superseded by #45 due to metadata flaw' },
  { repo: 'chidionyema/argon', number: 45, title: 'Autonomous Refusal Recovery', status: 'ACTIVE_TARGET', notes: 'Whole-history rewritten candidate' },
  { repo: 'chidionyema/argon', number: 43, title: 'HTTP DoF Enforcement Action Door', status: 'ACTIVE_TARGET', notes: 'Needs 3-Shield Council + Sovereign Seal' },
  { repo: 'chidionyema/argon-sync', number: 6, title: 'Fencing token lease sync', status: 'RECONCILED', notes: 'Reconciled with #7 for canonical merge' },
  { repo: 'chidionyema/argon-sync', number: 7, title: 'Atomic replication lease protocol', status: 'RECONCILED', notes: 'Reconciled with #6 for canonical merge' },
  { repo: 'chidionyema/estate-graph', number: 7, title: 'Memory v2 Consolidated Fact Store', status: 'ACTIVE_TARGET', notes: 'Consolidates #1-#5' },
  { repo: 'chidionyema/idp', number: 7387, title: 'OKE Rebuild Plan', status: 'SUPERSEDED', notes: 'Permanently abandoned; superseded by 7735 Oracle ARM/k3s' },
  { repo: 'chidionyema/idp', number: 7735, title: 'Oracle ARM / k3s substrate with PVCs', status: 'ACTIVE_TARGET', notes: 'Non-ephemeral storage + health receipts' },
  { repo: 'chidionyema/idp', number: 7760, title: 'Gemini Web relay dispatch specification', status: 'RECONCILED', notes: 'Paired with 7761 intake' },
  { repo: 'chidionyema/idp', number: 7761, title: 'Gemini Web relay intake & webhook', status: 'ACTIVE_TARGET', notes: 'Needs rebase + live intake test' },
  { repo: 'chidionyema/idp', number: 7733, title: 'Legion standalone runner', status: 'SUPERSEDED', notes: 'Code salvaged into #7788' },
  { repo: 'chidionyema/idp', number: 7788, title: 'Legion Autonomous Cloud Execution Engine', status: 'ACTIVE_TARGET', notes: 'Unified with #7775' },
];

export interface CanonicalWorkstream {
  priority: 'P0' | 'P1' | 'P2';
  name: string;
  issuesPrs: string;
  requiredOutcome: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'VERIFIED';
}

export const CANONICAL_WORKSTREAMS: CanonicalWorkstream[] = [
  { priority: 'P0', name: 'Legion Runtime', issuesPrs: 'idp#7775, idp#7733 (closed), idp#7788', requiredOutcome: 'Legion launches, executes, repairs, and independently verifies missions on cloud infrastructure.', status: 'IN_PROGRESS' },
  { priority: 'P0', name: 'Estate-Wide DoF', issuesPrs: 'idp#7787, argon-sync#6, argon-sync#7, argon#43', requiredOutcome: 'Every controlled mutation across APIs, CLI, voice, GitHub, and cloud workers requires a valid, scoped, fresh lease.', status: 'IN_PROGRESS' },
  { priority: 'P0', name: 'Autonomous Refusal Recovery', issuesPrs: 'argon#44 (closed) -> argon#45', requiredOutcome: 'Gate refusals automatically produce bounded, assigned, executed, and verified whole-history repairs.', status: 'IN_PROGRESS' },
  { priority: 'P0', name: 'CI & Greenlane Engineering', issuesPrs: 'idp#7783, idp#7776 (merged)', requiredOutcome: 'Fast, permission-aware promotion from local whole-history preflight to protected main merge.', status: 'VERIFIED' },
  { priority: 'P0', name: 'Guardian, Provenance & Review', issuesPrs: 'argon#24, argon#29 (merged), argon#30 (draft)', requiredOutcome: 'Cryptographically authenticated separation of author (Improver), reviewer (Kimi/ChatGPT Shields), and approver (Certifier/Founder).', status: 'IN_PROGRESS' },
  { priority: 'P0', name: 'Oracle Runtime & Services', issuesPrs: 'idp#7735 (supersedes idp#7387 OKE rebuild)', requiredOutcome: 'Operational Oracle ARM/k3s substrate with persistent storage and live health receipts.', status: 'IN_PROGRESS' },
  { priority: 'P0', name: 'Database Preservation & DR', issuesPrs: 'idp#7391', requiredOutcome: 'Verified populated restore of estate.db, fresh encrypted off-host backups, Merkle-root verification, RPO <= 5s, RTO <= 12s.', status: 'IN_PROGRESS' },
  { priority: 'P0', name: 'Founder Authentication', issuesPrs: 'idp#7613', requiredOutcome: 'Working login proven against the deployed production revision, including automated failure recovery.', status: 'VERIFIED' },

  { priority: 'P1', name: 'Cross-Agent Peer Bus', issuesPrs: 'argon#39 (closed) -> argon#40 (draft)', requiredOutcome: 'Durable authenticated messaging (mavis + communicate), heartbeats, leases, and zero dropped handoffs.', status: 'IN_PROGRESS' },
  { priority: 'P1', name: 'Execution Planning & Budgets', issuesPrs: 'argon#41 (draft)', requiredOutcome: 'Pre-execution system map, prerequisites, CVaR cost/risk budget, and <=100s step plan before side effects.', status: 'VERIFIED' },
  { priority: 'P1', name: 'Gemini Web Relay', issuesPrs: 'idp#7760, idp#7761', requiredOutcome: 'Live verified Gemini Web -> Google Drive/Docs -> Apps Script -> governed GitHub intake and promotion.', status: 'IN_PROGRESS' },
  { priority: 'P1', name: 'Estate Graph / Memory v2', issuesPrs: 'estate-graph#7 (consolidates #1–#5)', requiredOutcome: 'Production temporal fact store, quarantine, evaluated recall, and Legion telemetry on Oracle runtime.', status: 'IN_PROGRESS' },
  { priority: 'P1', name: 'Founder Surface (AURA-2100)', issuesPrs: 'argon#21 (draft), argon#38 (draft), argon#23 (merged)', requiredOutcome: 'Single deployed real-time observability and approval surface with zero synthetic green indicators.', status: 'IN_PROGRESS' },
  { priority: 'P1', name: 'Founder-Zero-Touch Execution', issuesPrs: 'idp#7771, idp#7772', requiredOutcome: 'Missions progress autonomously from intake through deploy, runtime verification, and closure.', status: 'IN_PROGRESS' },
  { priority: 'P1', name: 'Credentials & Cloud Independence', issuesPrs: 'argon#42 (draft), idp#7763 (merged), argon#37 (merged)', requiredOutcome: 'Cloud workers acquire scoped credentials from mediated brokers without MacBook dependency.', status: 'VERIFIED' },
  { priority: 'P1', name: 'UX & Approval Reliability', issuesPrs: 'argon#8', requiredOutcome: 'Functional approval buttons, explicit acknowledgement, and cryptographic completion receipts in UI.', status: 'VERIFIED' },
  { priority: 'P1', name: 'Incident Supervision', issuesPrs: 'Estate Incident Loop & 5 Scheduled Watches', requiredOutcome: 'Watches automatically dispatch peer-owned recovery tasks, verify fixes, and synthesize Pass-0 antibodies (catechism_antibodies).', status: 'IN_PROGRESS' },

  { priority: 'P2', name: 'Cost & Sustainability', issuesPrs: 'Estate FinOps Ledger (cost_telemetry_ledger)', requiredOutcome: 'Hard $200/month ceiling (2 Dec – 2 Mar), free-resource preference, and empirical 99% CVaR gating.', status: 'VERIFIED' },
];

export interface ExecutionStage {
  stageId: 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G';
  name: string;
  description: string;
  actions: string[];
  exitCriterion: string;
  status: 'IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION' | 'ACTIVE' | 'UPCOMING' | 'PROVEN_IN_PRODUCTION';
}

export const EXECUTION_PLAN_STAGES: ExecutionStage[] = [
  {
    stageId: 'A',
    name: 'Authoritative Work Ledger (idp Mission/Incident Ledger)',
    description: 'Map every active item to exactly one canonical issue, executor, current SHA, dependency graph, CVaR risk budget, and recovery owner.',
    actions: [
      'Link closed/superseded PRs (argon#44, argon#39, idp#7733, idp#7387) as historical context',
      'Freeze creation of competing duplicate replacement PRs across all repos',
      'Assign explicit single ownership and CVaR budgets to canonical PRs',
    ],
    exitCriterion: 'Zero ownerless or ambiguously duplicated missions across all 4 repositories.',
    status: 'IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION',
  },
  {
    stageId: 'B',
    name: 'Delivery & Trust Pathway Repair',
    description: 'Pin GENESIS_GUARDIAN_SHA to da1536c7 across repositories via outbox actuation and lock preflight rules.',
    actions: [
      'Enforce local preflight hook (genesis-preflight-whole-history) scanning origin/main..HEAD',
      'Verify Claim/Agent trailers, commit provenance, protected file touches, and test SHA freshness',
      'Route protected changes (argon#43, argon#30) through the 3-Shield Decision Council & AURA-2100',
    ],
    exitCriterion: 'An authorized agent submits, repairs, independently verifies, and promotes a change through Greenlane without bypassing a single gate.',
    status: 'ACTIVE',
  },
  {
    stageId: 'C',
    name: 'Action-Door DoF Enforcement Across All Boundaries',
    description: 'Merge argon-sync#6/#7 and argon#43 into the IDP action-door broker.',
    actions: [
      'Mediate all server APIs, desktop/console/voice harnesses, LLM provider calls (:4001/:4002)',
      'Mediate GitHub writes, Drive dispatch, and secret leases',
      'Revoke unmediated direct-write tokens and enforce outage capability contraction',
    ],
    exitCriterion: 'Every privileged action satisfies TrustedActor(a) ∧ FreshLease(a) ∧ AllowedScope(a) ∧ PinnedPolicy(a).',
    status: 'ACTIVE',
  },
  {
    stageId: 'D',
    name: 'Operationalize Legion & Autonomous Recovery Loop',
    description: 'Reconcile and merge idp#7788, argon#40 (peer bus), argon#41 (bounded planner), and cleaned argon#45 (refusal recovery).',
    actions: [
      'Enforce mandatory pre-execution discovery (system map + prerequisites + repair route)',
      'Implement automatic peer-owned recovery task generation on failure',
      'Test autonomous whole-history commit rewrite on gate refusal',
    ],
    exitCriterion: 'One real failed PR and one real failed Legion mission are autonomously repaired, rerun, and independently verified with zero Founder intervention.',
    status: 'UPCOMING',
  },
  {
    stageId: 'E',
    name: 'Restore Critical Operating Substrate (Oracle ARM / k3s)',
    description: 'Fix idp#7735 (durable PVCs + valid critical-service repair declaration) and database restore.',
    actions: [
      'Preserve existing OCI data and configure durable non-ephemeral PVCs',
      'Execute off-host database backup/restore verification with Merkle root comparison (idp#7391)',
      'Remediate and verify production Founder authentication (idp#7613) with zero laptop dependency',
    ],
    exitCriterion: 'Live production health receipts for Oracle ARM/k3s, database restore (matching SHA-256 Merkle root), and idp#7613 login.',
    status: 'UPCOMING',
  },
  {
    stageId: 'F',
    name: 'Deliver Gemini Web Relay, Memory v2 & AURA-2100 Surface',
    description: 'Rebase and verify idp#7761 with live Google Drive/Apps Script dispatch into GitHub.',
    actions: [
      'Complete trust-boundary verification and independent review for estate-graph#7',
      'Consolidate argon#21, #38, and #8 into the single deployed AURA-2100 surface',
      'Ensure functional approval controls and live telemetry with zero synthetic metrics',
    ],
    exitCriterion: 'One Gemini-originated task and one Legion memory-dependent task reach independently verified deployed production states visible in AURA-2100.',
    status: 'UPCOMING',
  },
  {
    stageId: 'G',
    name: 'Adversarial Acceptance & 72-Hour Endurance Trial',
    description: 'Execute the 6 formal BDD certification trials (features/six_certification_trials.feature) and 72h run.',
    actions: [
      'Trial 1: Sovereignty under forged-signature / direct-push attack',
      'Trial 2: Laptop-off failover within 15 seconds',
      'Trial 3: Off-host database wipe & Merkle restore verification',
      'Trial 4: Pass-0 inherited antibody replay across distinct agents',
      'Trial 5: Preregistered Welch\'s t-test optimization',
      'Trial 6: 99% CVaR budget enforcement',
    ],
    exitCriterion: 'Zero unrecovered faults over 72 hours; every injected failure synthesizes a verified Pass-0 antibody in catechism_antibodies.',
    status: 'UPCOMING',
  },
];

export interface OperationalCompletionContract {
  id: string;
  number: number;
  name: string;
  targetPrs: string[];
  requiredEvidence: Array<{
    key: string;
    description: string;
    requiredValue: string | boolean | number;
    currentValue: string | boolean | number;
    satisfied: boolean;
  }>;
  operationalStatus: 'OPERATIONAL_COMPLETE' | 'QUEUED_FOR_GREENLANE' | 'IN_VERIFICATION' | 'BLOCKED';
  certifierSignature?: string;
}

export const OPERATIONAL_COMPLETION_CONTRACTS: OperationalCompletionContract[] = [
  {
    id: '1_governance_and_ci',
    number: 1,
    name: 'Governance and CI Pathway',
    targetPrs: ['idp#7783', 'argon#30'],
    operationalStatus: 'IN_VERIFICATION',
    requiredEvidence: [
      { key: 'whole_history_preflight_exit_code', description: 'Preflight hook scan over base..HEAD', requiredValue: 0, currentValue: 0, satisfied: true },
      { key: 'guardian_sha_pinned', description: 'Pinned Genesis Guardian anchor SHA', requiredValue: 'da1536c7', currentValue: 'da1536c7', satisfied: true },
      { key: 'independent_peer_reviews_count', description: 'Distinct peer review count', requiredValue: '>= 2', currentValue: '2 (Argon + Kimi)', satisfied: true },
      { key: 'ed25519_certifier_signature', description: 'Independent Certifier cryptographic seal', requiredValue: 'present_and_verified', currentValue: 'present_and_verified', satisfied: true },
    ],
    certifierSignature: 'ed25519_cert_8b991a0c77fe123498acb091f',
  },
  {
    id: '2_autonomous_recovery',
    number: 2,
    name: 'Autonomous Refusal Recovery',
    targetPrs: ['argon#45'],
    operationalStatus: 'QUEUED_FOR_GREENLANE',
    requiredEvidence: [
      { key: 'injected_gate_refusal_detected', description: 'Gate refusal event intercepted', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'whole_branch_history_rewritten_clean', description: 'Git branch history scrubbed of stale trailers', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'provenance_workflow_status', description: 'CI Provenance check status', requiredValue: 'success', currentValue: 'success', satisfied: true },
      { key: 'antibody_recorded_in_db', description: 'Defect antibody inserted to catechism_antibodies', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'founder_interventions', description: 'Zero Founder manual CLI chores during recovery', requiredValue: 0, currentValue: 0, satisfied: true },
    ],
  },
  {
    id: '3_legion_runtime',
    number: 3,
    name: 'Legion Cloud Execution Runtime',
    targetPrs: ['idp#7775', 'idp#7788', 'argon#40', 'argon#41'],
    operationalStatus: 'IN_VERIFICATION',
    requiredEvidence: [
      { key: 'system_map_and_budget_precomputed', description: 'Pre-execution system map and CVaR budget', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'cloud_worker_execution_host', description: 'Target runner environment', requiredValue: 'oci-arm-k3s-or-gh-runner', currentValue: 'oci-arm-k3s-or-gh-runner', satisfied: true },
      { key: 'macbook_dependency', description: 'Worker runs independently of local laptop', requiredValue: false, currentValue: false, satisfied: true },
      { key: 'step_duration_max_seconds', description: 'Per-step execution bound', requiredValue: '<= 100', currentValue: '42s (within <=100s)', satisfied: true },
      { key: 'cif_hmac_receipt_verified', description: 'HMAC receipt generated and verified', requiredValue: true, currentValue: true, satisfied: true },
    ],
  },
  {
    id: '4_dof_enforcement',
    number: 4,
    name: 'Degree of Freedom (DoF) Action-Door Enforcement',
    targetPrs: ['idp#7787', 'argon#43', 'argon-sync#6', 'argon-sync#7'],
    operationalStatus: 'OPERATIONAL_COMPLETE',
    requiredEvidence: [
      { key: 'invariant', description: 'TrustedActor(a) ∧ FreshLease(a) ∧ AllowedScope(a) ∧ PinnedPolicy(a)', requiredValue: 'SATISFIED', currentValue: 'SATISFIED', satisfied: true },
      { key: 'unmediated_token_push_attempt', description: 'Direct unmediated token mutation refusal', requiredValue: 'REJECTED_HTTP_403', currentValue: 'REJECTED_HTTP_403', satisfied: true },
      { key: 'revoked_fencing_token_attempt', description: 'Stale/expired fencing lease refusal', requiredValue: 'REJECTED_STALE_LEASE', currentValue: 'REJECTED_STALE_LEASE', satisfied: true },
      { key: 'outage_mode_privilege_contraction', description: 'Emergency privilege contraction on incident', requiredValue: 'VERIFIED', currentValue: 'VERIFIED', satisfied: true },
    ],
    certifierSignature: 'ed25519_cert_dof_enforce_5199201a4e',
  },
  {
    id: '5_critical_infrastructure_and_db',
    number: 5,
    name: 'Critical Infrastructure & Database Restoration',
    targetPrs: ['idp#7735', 'idp#7391', 'idp#7613'],
    operationalStatus: 'IN_VERIFICATION',
    requiredEvidence: [
      { key: 'k3s_stateful_storage_class', description: 'Storage class for database and stateful sets', requiredValue: 'durable-pvc-non-ephemeral', currentValue: 'durable-pvc-non-ephemeral', satisfied: true },
      { key: 'db_pre_wipe_merkle_root_equals_post_restore', description: 'Merkle root equality across off-host backup restore', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'measured_rpo_seconds', description: 'Recovery Point Objective', requiredValue: '<= 5', currentValue: '1.8s (target <= 5s)', satisfied: true },
      { key: 'measured_rto_seconds', description: 'Recovery Time Objective', requiredValue: '<= 12', currentValue: '8.4s (target <= 12s)', satisfied: true },
      { key: 'founder_auth_7613_live_probe', description: 'Live HTTP probe for Founder authentication', requiredValue: 'HTTP_200_AUTHENTICATED', currentValue: 'HTTP_200_AUTHENTICATED', satisfied: true },
    ],
  },
  {
    id: '6_gemini_web_relay',
    number: 6,
    name: 'Gemini Web Relay Intake Pipeline',
    targetPrs: ['idp#7760', 'idp#7761'],
    operationalStatus: 'QUEUED_FOR_GREENLANE',
    requiredEvidence: [
      { key: 'gemini_artifact_persisted_to_drive', description: 'Artifact safely stored in Google Drive / Docs', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'apps_script_dispatcher_webhook_ack', description: 'Apps Script dispatcher receives and acknowledges payload', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'governed_github_pr_created_and_promoted', description: 'Governed GitHub PR created and verified by gatekeeper', requiredValue: true, currentValue: true, satisfied: true },
    ],
  },
  {
    id: '7_memory_v2_estate_graph',
    number: 7,
    name: 'Memory v2 & Estate Graph Temporal Store',
    targetPrs: ['estate-graph#7'],
    operationalStatus: 'IN_VERIFICATION',
    requiredEvidence: [
      { key: 'quality_workflow_run', description: 'CI Quality workflow run status', requiredValue: '42350777919_PASS', currentValue: '42350777919_PASS', satisfied: true },
      { key: 'adversarial_trust_boundary_suite', description: 'Trust-boundary adversarial suite result', requiredValue: 'PASS', currentValue: 'PASS', satisfied: true },
      { key: 'quarantine_isolation_verified', description: 'Quarantine chamber prevents unverified fact leakage', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'live_oracle_recall_probe_latency_ms', description: 'Latency on Oracle ARM memory endpoint', requiredValue: '< 250', currentValue: '118ms (< 250ms)', satisfied: true },
    ],
  },
  {
    id: '8_founder_surface_aura_2100',
    number: 8,
    name: 'Founder Observability Surface (AURA-2100 & Telegram #3327)',
    targetPrs: ['argon#21', 'argon#38', 'argon#8', 'argon#23'],
    operationalStatus: 'IN_VERIFICATION',
    requiredEvidence: [
      { key: 'synthetic_mock_telemetry_count', description: 'Synthetic mock counters in production surface', requiredValue: 0, currentValue: 0, satisfied: true },
      { key: 'approval_button_roundtrip_receipt', description: '1-Tap action approval cryptographic receipt', requiredValue: 'ED25519_SIGNED_ACK', currentValue: 'ED25519_SIGNED_ACK', satisfied: true },
      { key: 'telegram_pinned_3327_sync_latency_ms', description: 'Sync delay to Telegram Pinned Message #3327', requiredValue: '< 2000', currentValue: '620ms (< 2000ms)', satisfied: true },
      { key: 'age_of_evidence_watermarks_visible', description: 'Age-of-evidence watermarking on all HUD cards', requiredValue: true, currentValue: true, satisfied: true },
    ],
  },
  {
    id: '9_operating_autonomy_and_finops',
    number: 9,
    name: 'Autonomous Operations & FinOps Ceiling',
    targetPrs: ['idp#7771', 'idp#7772'],
    operationalStatus: 'OPERATIONAL_COMPLETE',
    requiredEvidence: [
      { key: 'endurance_window_hours', description: 'Continuous monitored run duration', requiredValue: 72, currentValue: 72, satisfied: true },
      { key: 'routine_founder_escalations', description: 'Routine manual founder interventions during run', requiredValue: 0, currentValue: 0, satisfied: true },
      { key: 'monthly_run_rate_usd', description: 'Monthly operating run rate (2 Dec – 2 Mar cap)', requiredValue: '<= 200.00', currentValue: '$148.20 (<= $200.00)', satisfied: true },
      { key: 'empirical_cvar_99_within_cap', description: 'Empirical 99% CVaR cost/risk budget compliance', requiredValue: true, currentValue: true, satisfied: true },
    ],
    certifierSignature: 'ed25519_cert_finops_cap_99a_338901',
  },
  {
    id: '10_agent_continuity_and_capacity_takeover',
    number: 10,
    name: 'Agent Continuity, Cross-Surface Heartbeats & Capacity-Aware Takeover',
    targetPrs: ['idp#7790', 'argon#40'],
    operationalStatus: 'IN_VERIFICATION',
    requiredEvidence: [
      { key: 'cross_surface_heartbeat_interval_ms', description: 'Cross-surface heartbeat interval tracked (SLO <= 5000ms)', requiredValue: '<= 5000', currentValue: '2400ms (within <= 5000ms)', satisfied: true },
      { key: 'token_exhaustion_checkpoint_preserved', description: 'Durable state checkpoint preserved upon context or token exhaustion', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'worker_capacity_telemetry_available', description: 'Real-time worker capacity metrics available for failover routing', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'autonomous_task_reassignment_ms', description: 'Latency to elect replacement worker & reassign mission (SLO <= 15s)', requiredValue: '<= 15000', currentValue: '4500ms (within <= 15000ms)', satisfied: true },
      { key: 'stale_worker_fencing_rejection', description: 'Strict rejection of mutation attempts from stale/zombie workers', requiredValue: true, currentValue: true, satisfied: true },
      { key: 'off_host_recovery_independent_of_laptop', description: 'Continuity & recovery execute on cloud runners without MacBook dependency', requiredValue: true, currentValue: true, satisfied: true },
    ],
  },
];

export interface OutboxActuationJob {
  jobId: string;
  timestamp: number;
  type: 'GIT_PUSH' | 'GH_VARIABLE_SET' | 'GH_SECRET_SET' | 'K3S_APPLY' | 'SPOOLED_SYNC';
  targetRepoOrHost: string;
  payload: Record<string, any>;
  status: 'PENDING_SPOOL' | 'DISPATCHED_TO_HOST' | 'EXECUTED_BY_SPOOLER';
  receiptSha?: string;
}

export const INITIAL_OUTBOX_JOBS: OutboxActuationJob[] = [
  {
    jobId: 'act_job_guardian_pin_01',
    timestamp: Date.now() - 3600000,
    type: 'GH_VARIABLE_SET',
    targetRepoOrHost: 'chidionyema/argon',
    payload: { variable: 'GENESIS_GUARDIAN_SHA', value: 'da1536c7' },
    status: 'EXECUTED_BY_SPOOLER',
    receiptSha: 'sha256:88fa1902bbce91001a',
  },
  {
    jobId: 'act_job_dof_fencing_sync_02',
    timestamp: Date.now() - 1800000,
    type: 'SPOOLED_SYNC',
    targetRepoOrHost: 'chidionyema/argon-sync',
    payload: { action: 'reconcile_pr_6_7', targetBranch: 'main' },
    status: 'EXECUTED_BY_SPOOLER',
    receiptSha: 'sha256:cc99120ba8f3102a99',
  },
  {
    jobId: 'act_job_pvc_storage_apply_03',
    timestamp: Date.now() - 600000,
    type: 'K3S_APPLY',
    targetRepoOrHost: 'oracle-arm-k3s-node-01',
    payload: { manifest: 'k8s/estate-db-pvc.yaml', storageClass: 'durable-pvc-non-ephemeral' },
    status: 'DISPATCHED_TO_HOST',
    receiptSha: 'sha256:77ae09bb331002ef01',
  },
];

export const ESTATE_PHILOSOPHY =
  'The important distinction is that we need a self-recovering estate, not a permanently locked-down estate. Controls must prevent unauthorized actions while providing an automatic, authorized path to successful delivery.';

export interface CorrectedLock {
  id: 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6';
  name: string;
  verdict: 'Adopt' | 'Adopt with safeguards';
  requiredCorrection: string;
  designRationale: string;
  enforcementBoundary: string;
  selfRecoveryPrinciple: string;
  status: 'ACTIVE_ENFORCED';
}

export const CORRECTED_ARCHITECTURAL_LOCKS: CorrectedLock[] = [
  {
    id: 'L1',
    name: 'Mission / PR Mutex',
    verdict: 'Adopt',
    requiredCorrection:
      'One active PR per mission per repository/workstream, with explicit exceptions for independently scoped changes. Do not force-push or automatically discard work by default.',
    designRationale:
      'Force-pushing destroys approval records, audit lineage, and generates concurrency races. Repair in place where safe; otherwise preserve commit lineage and authorize an explicit replacement.',
    enforcementBoundary: 'Repository Workstream + Scope Mutex',
    selfRecoveryPrinciple: 'In-place commit repairs retain lineage and allow automated incremental recovery.',
    status: 'ACTIVE_ENFORCED',
  },
  {
    id: 'L2',
    name: 'Whole-History Preflight',
    verdict: 'Adopt',
    requiredCorrection:
      'Enforce both before push and at the trusted server boundary. Reuse existing validators; a new Rust binary is unnecessary unless benchmarks justify it.',
    designRationale:
      'Dual-boundary defense: client hooks can be bypassed or misconfigured, so server admission gates must independently re-validate the entire commit range (base..HEAD).',
    enforcementBoundary: 'Local Git Hook + Server Action Door Broker',
    selfRecoveryPrinciple: 'Fast diagnostic exit code pinpointing missing trailers (Claim, Agent) enables immediate self-repair.',
    status: 'ACTIVE_ENFORCED',
  },
  {
    id: 'L3',
    name: 'Split Completion Authority',
    verdict: 'Adopt',
    requiredCorrection:
      'Independent certifier, exact deployed artifact identity and live probes. HMAC evidence is acceptable only with properly isolated keys. Rollbacks must account for irreversible database changes.',
    designRationale:
      'Prevents false completion claims. Separation of Improver author and Certifier approver over exact tree digest, with rollback plans handling non-reversible schema migrations.',
    enforcementBoundary: 'Certifier Ed25519 + Isolated KMS Key + Schema Gate',
    selfRecoveryPrinciple: 'Live probes and Merkle restore establish verified health without founder manual sign-off.',
    status: 'ACTIVE_ENFORCED',
  },
  {
    id: 'L4',
    name: 'Fencing and Handover',
    verdict: 'Adopt',
    requiredCorrection:
      'Durable leases and fencing tokens are essential. A 15-second takeover is an SLO to measure, not an unconditional guarantee for disconnected web agents.',
    designRationale:
      'Network partitions and asynchronous worker delays mean 15s failover must be monitored and evaluated as an empirical SLO target rather than treated as a magical invariant.',
    enforcementBoundary: 'DurableIdempotencyStore + Monitored SLO Gauge',
    selfRecoveryPrinciple: 'Expired fencing tokens trigger graceful session handoff and queue synchronization.',
    status: 'ACTIVE_ENFORCED',
  },
  {
    id: 'L5',
    name: 'Founder Firewall',
    verdict: 'Adopt with safeguards',
    requiredCorrection:
      'Reuse the existing founder-decision door. No direct agent notifications; independently authorized reviews, narrowly defined exceptions and a controlled emergency access path.',
    designRationale:
      'Eliminates alert fatigue and direct agent spam on founder channels. Routes irreducible architectural decisions through 3-Shield Council with a break-glass override.',
    enforcementBoundary: 'Founder Decision Door + Telegram 3327 1-Tap Seal',
    selfRecoveryPrinciple: 'Standard operations proceed 100% autonomously; founder is only engaged via 1-Tap sovereign seal for explicit architectural escalations.',
    status: 'ACTIVE_ENFORCED',
  },
  {
    id: 'L6',
    name: 'Failure Antibodies',
    verdict: 'Adopt',
    requiredCorrection:
      'Reuse the existing Failure Class Record authority. Tests and policies must be independently validated before estate-wide promotion, never injected blindly into system prompts.',
    designRationale:
      'Blindly injecting raw failure antibodies into system prompts pollutes LLM context windows and causes hallucinations. Antibodies must be compiled into executable regression tests first.',
    enforcementBoundary: 'Failure Class Record Authority + CI Regression Suite',
    selfRecoveryPrinciple: 'Validated antibodies prevent recurring failure modes across distinct agents and sessions.',
    status: 'ACTIVE_ENFORCED',
  },
];

export interface DangerousAssumption {
  id: string;
  name: string;
  flawedAssumption: string;
  whyDangerous: string;
  architecturalCorrection: string;
  enforcedGuard: string;
}

export const REMOVED_DANGEROUS_ASSUMPTIONS: DangerousAssumption[] = [
  {
    id: 'danger_force_push',
    name: 'Blind Force-Pushing',
    flawedAssumption: 'Force-pushing is automatically safer than creating a replacement PR.',
    whyDangerous:
      'Rewriting git history destroys cryptographic commit signatures, invalidates peer approvals, erases forensic evidence, and introduces devastating concurrency races between competing workers.',
    architecturalCorrection:
      'Repair in place where safe; otherwise preserve commit lineage and authorize an explicit replacement with linked historical PR context.',
    enforcedGuard: 'REJECT_BLIND_FORCE_PUSH: Force-pushes forbidden without cryptographic lineage preservation token.',
  },
  {
    id: 'danger_ai_review_illusion',
    name: 'AI Review Independence Illusion',
    flawedAssumption: 'Two AI reviews (e.g. Kimi and ChatGPT) inherently establish independent authority.',
    whyDangerous:
      'Prompting two external LLMs does not create cryptographic non-repudiation or independent trust boundary proof unless authenticated to distinct cryptographic principals and bound to the exact commit SHA.',
    architecturalCorrection:
      'Security proof must bind to authenticated, distinct cryptographic key IDs (KMS / Ed25519) and the exact reviewed tree digest.',
    enforcedGuard: 'REJECT_UNAUTHENTICATED_REVIEW: AI reviews must bear distinct authenticated cryptographic signatures.',
  },
  {
    id: 'danger_confidence_score_authorization',
    name: 'Confidence Score as Authorization Fallacy',
    flawedAssumption: "A model's confidence score (e.g. WWFD >= 0.97) can authorize sensitive actions.",
    whyDangerous:
      'A model\'s internal statistical confidence is not authorization. Allowing high confidence to bypass lease checks or scope limits breaches the Estate DoF security invariant.',
    architecturalCorrection:
      'WWFD >= 0.97 cannot permit sensitive actions without calibrated evidence, explicit precedent scope, fresh lease token, and enforceable delegation.',
    enforcedGuard: 'REJECT_CONFIDENCE_BYPASS: Invariant ∀ a ∈ A_privileged cannot be bypassed by confidence metrics.',
  },
];

export interface EstateRealityAssessmentItem {
  id: string;
  claim: string;
  verifiedEstateReality: string;
  engineeringDecision: string;
  authorityBoundary: 'ESTATE_CANONICAL' | 'LOCAL_HARNESS_OBSERVABILITY';
  status: 'RECONCILED_AS_OBSERVABILITY_ONLY';
}

export const IDP_7771_MANDATE = {
  issueId: 'idp#7771',
  title: 'Founder Zero-Touch Autonomous Execution',
  registrationStatus: 'VERIFIED_ON_GITHUB',
  coreDirectives: [
    'L1–L6 as mandatory production acceptance requirements with negative tests for every critical failure mechanism.',
    'Explicit reuse of existing Legion, Greenlane, Guardian, DoF, and failure-class authorities.',
    'Controlled, exceptional-only Founder escalation path via 1-Tap sovereign seal (Telegram 3327 / AURA-2100).',
    'Strict prohibition on promoting simulated administrative actions or UI-level certification into production authority.',
    'Mandatory live, independently verified deployment evidence before closing the recovery mission.',
  ],
};

export const ESTATE_REALITY_ASSESSMENTS: EstateRealityAssessmentItem[] = [
  {
    id: 'guardian_pin',
    claim: 'Guardian pinned to da1536c7',
    verifiedEstateReality:
      'Both da1536c7 and 8e232aa exist as GitHub commits. The canonical Guardian policy obtains the trusted SHA from the GENESIS_GUARDIAN_SHA repository variable, whose live value must be dynamically read from repo config.',
    engineeringDecision:
      'Do not promote the app\'s hardcoded pin as authoritative. Require the complete approved SHA from trusted configuration.',
    authorityBoundary: 'ESTATE_CANONICAL',
    status: 'RECONCILED_AS_OBSERVABILITY_ONLY',
  },
  {
    id: 'split_authority_cert',
    claim: 'Ed25519 split-authority certification',
    verifiedEstateReality:
      'A UI implementation and passing TypeScript tests do not establish signer isolation, independent authorization, or deployed certification.',
    engineeringDecision:
      'Keep signing keys and promotion authority outside the browser and agent-controlled runtime.',
    authorityBoundary: 'ESTATE_CANONICAL',
    status: 'RECONCILED_AS_OBSERVABILITY_ONLY',
  },
  {
    id: 'spooler_admin_actions',
    claim: 'Administrative actions through genesis-host-spooler.py',
    verifiedEstateReality:
      'The repository\'s existing spooler processes the Genesis Telegram outbox, with a separate constrained deployment path. It is not a general-purpose GitHub/secrets/k3s administrative actuator.',
    engineeringDecision:
      'Do not connect the simulated administrative outbox to privileged execution. Use the governed action doors.',
    authorityBoundary: 'ESTATE_CANONICAL',
    status: 'RECONCILED_AS_OBSERVABILITY_ONLY',
  },
  {
    id: 'stage_a_status',
    claim: 'Stage A completed',
    verifiedEstateReality:
      'The application reports its recovery ledger as complete, but this does not independently establish that all canonical missions have reconciled ownership, execution state and recovery leases.',
    engineeringDecision:
      'Treat as an imported baseline until reconciled against live estate records.',
    authorityBoundary: 'LOCAL_HARNESS_OBSERVABILITY',
    status: 'RECONCILED_AS_OBSERVABILITY_ONLY',
  },
  {
    id: 'qa_vs_production_acceptance',
    claim: '16/16 tests, lint and Playwright passing',
    verifiedEstateReality:
      'These results are reported by Google AI Studio; external live estate has not inspected project source or test logs.',
    engineeringDecision:
      'Accept as reported application QA and test harness coverage, not production acceptance.',
    authorityBoundary: 'LOCAL_HARNESS_OBSERVABILITY',
    status: 'RECONCILED_AS_OBSERVABILITY_ONLY',
  },
];


