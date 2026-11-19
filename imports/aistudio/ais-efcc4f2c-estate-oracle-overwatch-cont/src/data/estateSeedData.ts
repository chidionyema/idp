import {
  computeCifHmac,
  type EstateEntity,
  type CifStepReceipt,
  type TelegramForumTopic,
  type OttoInstanceState,
  type ComposableIntent,
} from '../engine/oracleEngine';

export interface EstateLayerRow {
  id: string;
  layer: string;
  status: string;
  severity: 'nominal' | 'warning' | 'critical';
  realityAndBottleneck: string;
  oracleEntityId: string;
}

export const INITIAL_ESTATE_LAYERS: EstateLayerRow[] = [
  {
    id: 'layer-compute',
    layer: 'Compute & Training Fleet',
    status: 'Active (MacBook M3 Max)',
    severity: 'nominal',
    realityAndBottleneck:
      '4 headless pi sessions running continuously on MiniMax M2.7 plan quota generating SFT/RLHF trajectories (148.4 tok/s aggregate). Protected via non-interrupt guard.',
    oracleEntityId: 'LANE-PI-MINIMAX-01',
  },
  {
    id: 'layer-kernel',
    layer: 'Execution Kernel',
    status: 'estate-execute + estate.db (CIF v2)',
    severity: 'nominal',
    realityAndBottleneck:
      'Upgraded with stdout_payload, stderr_payload, and HMAC-SHA256 hmac_signature columns so agents cannot forge or hallucinate execution outcomes.',
    oracleEntityId: 'KERNEL-CIF-SCHEMA-V2',
  },
  {
    id: 'layer-router',
    layer: 'Model Router / Gateway',
    status: 'Broken / Direct Quota Bypass',
    severity: 'warning',
    realityAndBottleneck:
      'Central proxy gateway currently bypassed. Active pi lanes and Otto hit MiniMax M2.7 plan quota directly with local token-bucket rate rationing.',
    oracleEntityId: 'ROUTER-MINIMAX-BYPASS',
  },
  {
    id: 'layer-infra',
    layer: 'Deployment / Infra Spine',
    status: 'OKE Blocked (#7318) -> Oracle k3s',
    severity: 'warning',
    realityAndBottleneck:
      'argon lacks k8s manifests; bin/idp-vault-refs was caught faking VERIFIED_LIVE. Pivoted strictly to Oracle Free Tier k3s spine with 14.8MB Rust-Only admission gate.',
    oracleEntityId: 'TICKET-7318',
  },
  {
    id: 'layer-protocol',
    layer: 'Protocol & Telemetry',
    status: 'AGENT.md / Protocolkit / AEI',
    severity: 'nominal',
    realityAndBottleneck:
      'Indexed into estate-graph retrieval engine. All PRs, claims, and step receipts are queryable in Pass 1 via BM25 + Graph RRF.',
    oracleEntityId: 'CLAIM-OIA-GTM-741',
  },
  {
    id: 'layer-otto',
    layer: 'Otto (Personal Agent)',
    status: 'Split-Brain ("2 Ottos" Conflict)',
    severity: 'critical',
    realityAndBottleneck:
      'Suffering from asymmetric capture: Otto v1 (PID 41892, stale markdown MCP) vs Otto v2 (PID 88410, estate.db CIF daemon) competing for context.',
    oracleEntityId: 'CLAIM-OTTO-AUDIT-902',
  },
];

export const INITIAL_OTTO_INSTANCES: OttoInstanceState[] = [
  {
    instanceId: 'otto-v1-legacy-mcp',
    label: 'Otto Instance A · Legacy MCP Worktree (Rogue Split-Brain)',
    role: 'legacy_split_brain',
    pid: 41892,
    entrypoint: 'node ~/Desktop/otto-old-worktree/packages/mcp-daemon/index.js --poll',
    worktreePath: '~/Desktop/otto-old-worktree',
    branch: 'wip/otto-local-markdown-mem',
    memoryBackend: 'Unverified Markdown (~/.otto_v1/memory.md & local JSON)',
    cifEnforced: false,
    capturedContextPct: 44,
    driftSymptoms: [
      'Intercepts 44% of personal prompts via stale webhook polling loop',
      'Writes unverified claims to ~/.otto_v1/memory.md with zero CIF HMAC signature',
      'Unaware of OIA GTM Claim #741 and Oracle k3s #7318 cutover decisions',
    ],
    activeClaims: ['CLAIM-OTTO-AUDIT-902 (Unverified shadow state)'],
    status: 'active_conflict',
  },
  {
    instanceId: 'otto-v2-cif-daemon',
    label: 'Otto Instance B · Canonical Day-0 CIF Agent (Target Front-Door)',
    role: 'canonical_candidate',
    pid: 88410,
    entrypoint: 'estate-overwatch --persona otto-day0 --ledger ~/.estate/estate.db',
    worktreePath: '~/estate/otto-core',
    branch: 'main (HEAD -> 9f4e2a1)',
    memoryBackend: 'SQLite WAL Ledger (~/.estate/estate.db + estate-graph RRF Index)',
    cifEnforced: true,
    capturedContextPct: 56,
    driftSymptoms: [
      'Verifies every delegated pi action via estate-execute --receipt <ticket>:<step>',
      'Awaiting split-brain purge of PID 41892 to claim exclusive Telegram Overwatch binding',
    ],
    activeClaims: ['TICKET-OTTO-RESCUE-001', 'CLAIM-OIA-GTM-741'],
    status: 'active_conflict',
  },
];

function makeSeedReceipt(
  id: number,
  ticketId: string,
  stepIdx: number,
  laneId: string,
  cmd: string,
  stdoutPayload: string,
  stderrPayload: string,
  exitCode: number,
  timestamp: string,
  diffSummary: string,
  diffPatch: string
): CifStepReceipt {
  const hmacSignature = computeCifHmac(ticketId, stepIdx, cmd, stdoutPayload, exitCode);
  return {
    id,
    ticketId,
    stepIdx,
    laneId,
    cmd,
    stdoutPayload,
    stderrPayload,
    exitCode,
    hmacSignature,
    timestamp,
    diffSummary,
    diffPatch,
    verified: true,
  };
}

export const INITIAL_CIF_RECEIPTS: CifStepReceipt[] = [
  makeSeedReceipt(
    94,
    'CLAIM-OIA-GTM-741',
    1,
    'pi-lane-02',
    'estate-execute --ticket CLAIM-OIA-GTM-741 --step 1 -- cargo test -p oia-gtm-indexer -- --nocapture',
    [
      'running 14 tests in packages/oia-gtm-indexer/src/claims.rs',
      'test claims::verify_gtm_ticket_lineage ... ok',
      'test claims::reject_unsigned_pr_claim_884 ... ok',
      'test claims::index_oia_gtm_artifacts_ into_estate_graph ... ok',
      'test result: ok. 14 passed; 0 failed; finished in 0.41s',
      '[ESTATE-GRAPH] Indexed 28 OIA GTM investigation claims, 6 PRs, and 19 step receipts into SQLite FTS5 + RRF graph.',
    ].join('\n'),
    '',
    0,
    '2026-10-31T09:31:12Z',
    'packages/oia-gtm-indexer/src/claims.rs (+142 -18)',
    `--- a/packages/oia-gtm-indexer/src/claims.rs\n+++ b/packages/oia-gtm-indexer/src/claims.rs\n@@ -48,7 +48,14 @@ pub fn verify_gtm_claim(claim: &GtmClaim, db: &SqlitePool) -> Result<VerifiedClaim> {\n-    Ok(VerifiedClaim::unchecked(claim.id.clone()))\n+    let receipt = sqlx::query!("SELECT hmac_signature, exit_code FROM step_runs WHERE ticket_id = ?1", claim.ticket_id)\n+        .fetch_one(db).await?;\n+    ensure!(receipt.exit_code == 0, "CIF Falsification: non-zero exit code");\n+    Ok(VerifiedClaim::from_hmac(claim.id.clone(), receipt.hmac_signature))\n }`
  ),
  makeSeedReceipt(
    95,
    'TICKET-7318',
    2,
    'k3s-rust-spine',
    'estate-execute --ticket TICKET-7318 --step 2 -- bin/audit-idp-vault-refs --falsify',
    [
      '[CIF-FALSIFIER] Inspecting bin/idp-vault-refs (commit 3c81b09)...',
      '[VIOLATION DETECTED] Line 42 echoes hardcoded string "VERIFIED_LIVE" without probing OKE cluster #7318.',
      '[VIOLATION DETECTED] repo "argon" contains 0 Kubernetes manifests under k8s/ or deploy/.',
      '[ACTION] Quarantined bin/idp-vault-refs; locked deployment target to Oracle Free Tier k3s Rust spine.',
    ].join('\n'),
    'WARN: Falsified 1 synthetic verification script (bin/idp-vault-refs)',
    0,
    '2026-10-31T09:34:40Z',
    'bin/idp-vault-refs (quarantined) · k3s/overwatch-admission.yaml (+64 -0)',
    `--- a/bin/idp-vault-refs\n+++ b/bin/idp-vault-refs\n@@ -39,5 +39,5 @@\n-# TODO: wire real OKE check\n-echo "VERIFIED_LIVE"\n+echo "ERR_CIF_FALSIFIED: OKE #7318 blocked; use estate-overwatch Rust k3s spine" >&2\n+exit 1`
  ),
  makeSeedReceipt(
    96,
    'LANE-PI-MINIMAX-01',
    8,
    'pi-lane-01',
    'estate-execute --ticket LANE-PI-MINIMAX-01 --step 8 -- pi-synth --model minimax-m2.7 --batch 2048 --out ~/.estate/trajectories/shard_08.jsonl',
    [
      '[MINIMAX-M2.7] Direct plan quota stream active (router bypassed · zero throttling)',
      '[SYNTHESIS] Generated 2,048 multi-turn tool-use trajectories with verified SQLite step hashes',
      '[THROUGHPUT] 76.8 tokens/sec · P99 latency 310ms · 0 malformed JSON frames',
      '[LEDGER] Committed shard_08.jsonl digest sha256:4f82e19c... to estate.db',
    ].join('\n'),
    '',
    0,
    '2026-10-31T09:37:05Z',
    'trajectories/shard_08.jsonl (+2048 records · 18.4 MB)',
    `--- /dev/null\n+++ b/trajectories/shard_08.manifest.json\n@@ -0,0 +1,6 @@\n+{\n+  "shard": "shard_08.jsonl",\n+  "model": "MiniMax-M2.7-Direct",\n+  "records": 2048,\n+  "cif_verified": true\n+}`
  ),
  makeSeedReceipt(
    97,
    'CLAIM-OTTO-AUDIT-902',
    3,
    'otto-front-door',
    'estate-execute --ticket CLAIM-OTTO-AUDIT-902 --step 3 -- estate-oracle query --intent intent.otto.split_brain_probe',
    [
      '[ORACLE-PASS-1] Indexed worktree & process table scan completed in 1.9ms (0 bash loops)',
      '[SPLIT-BRAIN FOUND] Instance 1: PID 41892 (~/Desktop/otto-old-worktree · branch wip/otto-local-markdown-mem)',
      '[SPLIT-BRAIN FOUND] Instance 2: PID 88410 (~/estate/otto-core · branch main · SQLite WAL bound)',
      '[ASYMMETRIC CAPTURE] 42 recent user directives split across ~/.otto_v1/memory.md and estate.db.',
      '[RECOMMENDATION] Execute reconcileOttoSplitBrain to archive PID 41892 and promote PID 88410.',
    ].join('\n'),
    '',
    0,
    '2026-10-31T09:39:18Z',
    'estate-graph snapshot updated · 2 competing Otto identities mapped',
    `--- a/estate-graph/identities/otto.json\n+++ b/estate-graph/identities/otto.json\n@@ -2,4 +2,5 @@\n   "canonical_pid": 88410,\n+  "rogue_pid_detected": 41892,\n+  "asymmetric_capture_frames": 42,\n   "status": "SPLIT_BRAIN_PENDING_CUTOVER"\n }`
  ),
];

export const INITIAL_ESTATE_ENTITIES: EstateEntity[] = [
  {
    id: 'CLAIM-OIA-GTM-741',
    kind: 'claim_ticket',
    title: 'OIA GTM Investigation: Claim Lineage, PR Verification & Retrieval Indexing',
    lane: 'pi-lane-02',
    summary:
      'Consolidates recent OIA GTM investigation work across PR #884, PR #891, and Ticket #804. Falsified 3 unbacked GTM readiness claims and indexed 28 verified artifacts into estate-graph.',
    repoOrPath: '~/estate/oia-gtm-engine',
    branchOrRef: 'feat/oia-gtm-cif-claims',
    authorOrAgent: 'oia-gtm-lead / pi-lane-02',
    timestamp: '2026-10-31T09:31:12Z',
    cifVerified: true,
    hmacSignature: INITIAL_CIF_RECEIPTS[0].hmacSignature,
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['PR-OIA-GTM-891', 'TICKET-OIA-804', 'CLAIM-OTTO-AUDIT-902'],
    tokens: ['oia', 'gtm', 'investigation', 'claim', 'ticket', 'pr', '891', '884', 'discovery', 'retrieval'],
    graphCentrality: 0.96,
    rawPayload:
      'CLAIM_ID=CLAIM-OIA-GTM-741 | REPO=oia-gtm-engine | VERIFIED_CLAIMS=28 | FALSIFIED_CLAIMS=3 | CIF_HMAC=VALID',
  },
  {
    id: 'PR-OIA-GTM-891',
    kind: 'pr_branch',
    title: 'PR #891: feat(oia-gtm): Enforce CIF HMAC Receipts on GTM Pipeline Handoffs',
    lane: 'pi-lane-02',
    summary:
      'Replaces ad-hoc markdown status claims in OIA GTM with deterministic SQLite step_runs foreign keys and hybrid BM25+RRF entity indexing.',
    repoOrPath: '~/estate/oia-gtm-engine',
    branchOrRef: 'feat/oia-gtm-cif-claims -> main',
    authorOrAgent: 'oia-gtm-lead',
    timestamp: '2026-10-31T09:24:00Z',
    cifVerified: true,
    hmacSignature: computeCifHmac('PR-OIA-GTM-891', 1, 'gh pr checks 891', 'All 6 CIF checks passed', 0),
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['CLAIM-OIA-GTM-741', 'TICKET-OIA-804'],
    tokens: ['pr', '891', 'oia', 'gtm', 'branch', 'handoff', 'cif', 'sqlite'],
    graphCentrality: 0.91,
    rawPayload: 'PR #891 (+412 -189) · Merged into main with CIF receipt #94',
  },
  {
    id: 'CLAIM-OTTO-AUDIT-902',
    kind: 'claim_ticket',
    title: 'Ticket & Claim #902: Deep Otto Split-Brain ("2 Ottos") & Asymmetric Capture Audit',
    lane: 'otto-front-door',
    summary:
      'Forensic investigation of the 2 Ottos nightmare: PID 41892 (legacy MCP reading ~/Desktop/otto-old-worktree) vs PID 88410 (canonical Rust/SQLite Overwatch agent in ~/estate/otto-core).',
    repoOrPath: '~/estate/otto-core',
    branchOrRef: 'main vs wip/otto-local-markdown-mem',
    authorOrAgent: 'otto-day0-auditor',
    timestamp: '2026-10-31T09:39:18Z',
    cifVerified: true,
    hmacSignature: INITIAL_CIF_RECEIPTS[3].hmacSignature,
    exitCode: 0,
    asymmetricDriftRisk: 'critical_split_brain',
    linkedIds: ['DAEMON-OTTO-V1-LEGACY', 'PR-OTTO-914', 'CLAIM-OIA-GTM-741'],
    tokens: ['otto', 'split-brain', '2-ottos', 'asymmetric', 'capture', 'audit', 'forensics', 'worktree', 'claim'],
    graphCentrality: 0.98,
    rawPayload:
      'SPLIT_BRAIN_DETECTED=true | PID_A=41892 (~/Desktop/otto-old-worktree) | PID_B=88410 (~/estate/otto-core) | ASYMMETRIC_FRAMES=42',
  },
  {
    id: 'DAEMON-OTTO-V1-LEGACY',
    kind: 'worktree_daemon',
    title: 'Rogue Worktree & Daemon: Otto v1 Legacy MCP (PID 41892)',
    lane: 'otto-front-door',
    summary:
      'Active split-brain offender: detached git worktree at ~/Desktop/otto-old-worktree on branch wip/otto-local-markdown-mem capturing 44% of founder context into unverified markdown.',
    repoOrPath: '~/Desktop/otto-old-worktree',
    branchOrRef: 'wip/otto-local-markdown-mem',
    authorOrAgent: 'otto-v1-mcp (PID 41892)',
    timestamp: '2026-10-31T09:15:44Z',
    cifVerified: false,
    hmacSignature: 'UNVERIFIED_MUTABLE_MARKDOWN_STATE',
    exitCode: 1,
    asymmetricDriftRisk: 'critical_split_brain',
    linkedIds: ['CLAIM-OTTO-AUDIT-902', 'PR-OTTO-914'],
    tokens: ['otto', 'v1', 'legacy', 'mcp', 'split-brain', 'worktree', '41892', 'unverified', 'markdown'],
    graphCentrality: 0.88,
    rawPayload: 'ps aux: 41892 node ~/Desktop/otto-old-worktree/packages/mcp-daemon/index.js --poll',
  },
  {
    id: 'PR-OTTO-914',
    kind: 'pr_branch',
    title: 'PR #914: fix(otto): Consolidate Day-0 Identity & Bind Telegram Overwatch Front-Door',
    lane: 'otto-front-door',
    summary:
      'Eliminates 2-Ottos split-brain by archiving ~/Desktop/otto-old-worktree, migrating 42 markdown frames to estate.db, and requiring CIF HMAC verification on every personal agent claim.',
    repoOrPath: '~/estate/otto-core',
    branchOrRef: 'fix/otto-day0-cif-consolidation',
    authorOrAgent: 'founder / otto-v2',
    timestamp: '2026-10-31T09:38:00Z',
    cifVerified: true,
    hmacSignature: computeCifHmac('PR-OTTO-914', 1, 'git diff main...fix/otto-day0-cif-consolidation', 'Clean cutover diff', 0),
    exitCode: 0,
    asymmetricDriftRisk: 'elevated',
    linkedIds: ['CLAIM-OTTO-AUDIT-902', 'DAEMON-OTTO-V1-LEGACY'],
    tokens: ['pr', '914', 'otto', 'day-0', 'telegram', 'overwatch', 'split-brain', 'consolidation'],
    graphCentrality: 0.92,
    rawPayload: 'Branch fix/otto-day0-cif-consolidation ready for instant cutover in estate-oracle.',
  },
  {
    id: 'TICKET-7318',
    kind: 'estate_layer',
    title: 'Infra Spine #7318: OKE Blocked -> Oracle Free Tier k3s Rust-Only Admission Gate',
    lane: 'k3s-rust-spine',
    summary:
      'Falsified bin/idp-vault-refs fake VERIFIED_LIVE output and argon missing k8s manifests. Enforces single 14.8MB static Rust binary (teloxide + axum + sqlx) on Oracle k3s.',
    repoOrPath: '~/estate/k3s-overwatch-rust',
    branchOrRef: 'main',
    authorOrAgent: 'k3s-admission-controller',
    timestamp: '2026-10-31T09:34:40Z',
    cifVerified: true,
    hmacSignature: INITIAL_CIF_RECEIPTS[1].hmacSignature,
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['KERNEL-CIF-SCHEMA-V2'],
    tokens: ['7318', 'oke', 'oracle', 'k3s', 'rust', 'argon', 'idp-vault-refs', 'teloxide', 'axum', 'sqlx'],
    graphCentrality: 0.93,
    rawPayload: 'BINARY=estate-overwatch (14.8MB static musl) | RAM=18.2MB | K3S_NODE=oracle-arm64-01',
  },
  {
    id: 'KERNEL-CIF-SCHEMA-V2',
    kind: 'cif_receipt',
    title: 'CIF Execution Kernel: estate.db step_runs Cryptographic Ledger',
    lane: 'k3s-rust-spine',
    summary:
      'SQLite WAL ledger storing stdout_payload, stderr_payload, exit_code, and hmac_signature for every estate-execute invocation across MacBook Pi lanes and k3s.',
    repoOrPath: '~/.estate/estate.db',
    branchOrRef: 'schema/cif-v2.4',
    authorOrAgent: 'estate-execute',
    timestamp: '2026-10-31T09:37:05Z',
    cifVerified: true,
    hmacSignature: INITIAL_CIF_RECEIPTS[2].hmacSignature,
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['TICKET-7318', 'LANE-PI-MINIMAX-01'],
    tokens: ['cif', 'estate.db', 'sqlite', 'hmac', 'receipt', 'step_runs', 'estate-execute', 'kernel'],
    graphCentrality: 0.95,
    rawPayload: 'CREATE TABLE step_runs (id INTEGER PRIMARY KEY, ticket_id TEXT, step_idx INT, cmd TEXT, stdout_payload TEXT, stderr_payload TEXT, exit_code INT, hmac_signature TEXT);',
  },
  {
    id: 'LANE-PI-MINIMAX-01',
    kind: 'worktree_daemon',
    title: 'MacBook Pi Fleet Lane #01 & #02: MiniMax M2.7 Continuous Trajectory Synthesis',
    lane: 'pi-lane-01',
    summary:
      'Headless pi workers riding MiniMax M2.7 plan quota directly (router bypassed) at 148.4 tok/s aggregate, streaming signed training shards into estate.db.',
    repoOrPath: '~/estate/pi-synth-fleet',
    branchOrRef: 'prod/minimax-m2.7-direct',
    authorOrAgent: 'pi-lane-01 (PID 63104)',
    timestamp: '2026-10-31T09:37:05Z',
    cifVerified: true,
    hmacSignature: INITIAL_CIF_RECEIPTS[2].hmacSignature,
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['KERNEL-CIF-SCHEMA-V2', 'ROUTER-MINIMAX-BYPASS'],
    tokens: ['pi', 'minimax', 'm2.7', 'quota', 'training', 'fleet', 'macbook', 'router', 'bypassed'],
    graphCentrality: 0.89,
    rawPayload: 'PID 63104 & 63109 | MiniMax M2.7 Direct Quota | 148.4 tok/s | DO_NOT_INTERRUPT=1',
  },
];

export const INITIAL_FORUM_TOPICS: TelegramForumTopic[] = [
  {
    id: 'otto-front-door',
    name: '#otto-front-door',
    ticketId: 'CLAIM-OTTO-AUDIT-902',
    status: 'verified',
    pid: 88410,
    modelQuotaSource: 'MiniMax-M2.7 Direct + SQLite Oracle',
    tokensPerSec: 42.6,
    sqliteWriteOpsSec: 18.4,
    memoryMb: 6.2,
    unverifiedClaims: 1,
    lastHeartbeat: '1s ago',
    description: 'Personal Agent Front-Door · Resolves founder intents via Pass-1 estate-graph queries',
  },
  {
    id: 'pi-lane-01',
    name: '#pi-lane-01',
    ticketId: 'LANE-PI-MINIMAX-01',
    status: 'inferencing',
    pid: 63104,
    modelQuotaSource: 'MiniMax-M2.7 Plan Quota (Direct)',
    tokensPerSec: 76.8,
    sqliteWriteOpsSec: 34.0,
    memoryMb: 4.8,
    unverifiedClaims: 0,
    lastHeartbeat: '0.4s ago',
    description: 'Continuous SFT Trajectory Synthesis Shard #08 · Protected MacBook Worker',
  },
  {
    id: 'pi-lane-02',
    name: '#pi-lane-02',
    ticketId: 'CLAIM-OIA-GTM-741',
    status: 'running',
    pid: 63109,
    modelQuotaSource: 'MiniMax-M2.7 Plan Quota (Direct)',
    tokensPerSec: 71.6,
    sqliteWriteOpsSec: 29.5,
    memoryMb: 4.5,
    unverifiedClaims: 0,
    lastHeartbeat: '0.8s ago',
    description: 'OIA GTM Investigation & PR #891 Claim Indexing Lane',
  },
  {
    id: 'k3s-rust-spine',
    name: '#k3s-rust-spine',
    ticketId: 'TICKET-7318',
    status: 'verified',
    pid: 1042,
    modelQuotaSource: 'Rust Static Binary (teloxide+axum+sqlx)',
    tokensPerSec: 0.0,
    sqliteWriteOpsSec: 64.2,
    memoryMb: 18.2,
    unverifiedClaims: 0,
    lastHeartbeat: '0.2s ago',
    description: 'Oracle Free Tier k3s Overwatch Daemon · 14.8MB Binary · 3s Pinned Matrix Editor',
  },
];

export const INITIAL_COMPOSABLE_INTENTS: ComposableIntent[] = [
  {
    id: 'intent.otto.day0_readiness',
    name: 'Otto Day-0 Zero-Hallucination & Split-Brain Gate',
    version: '2.1.0',
    description:
      'Reusable declarative intent verifying that only one canonical Otto daemon exists and 100% of Otto claims carry valid CIF HMAC-SHA256 signatures in estate.db.',
    targetQuery: 'otto split-brain worktree',
    requireCifSignature: true,
    maxAllowedSplitBrain: 0,
    yamlSource: `apiVersion: cif.estate.io/v2
kind: ComposableIntent
metadata:
  id: intent.otto.day0_readiness
  owner: founder-overwatch
spec:
  oracle_query:
    match: "otto split-brain worktree"
    ranking: hybrid_bm25_rrf_pagerank
    max_pass: 1
  expected_outcomes:
    - id: single_canonical_otto
      predicate: zero_split_brain
      max_rogue_daemons: 0
    - id: cryptographic_provenance
      predicate: all_cif_verified
      hmac_algo: sha256
    - id: indexed_retrieval_active
      predicate: sqlite_wal_active`,
    expectedOutcomes: [
      {
        id: 'single_canonical_otto',
        assertion: 'Zero competing Otto split-brain daemons or rogue git worktrees',
        predicateType: 'zero_split_brain',
        threshold: 0,
      },
      {
        id: 'cryptographic_provenance',
        assertion: 'Every Otto entity & claim in estate-graph carries a verified CIF HMAC signature',
        predicateType: 'all_cif_verified',
      },
      {
        id: 'indexed_retrieval_active',
        assertion: 'Pass-1 SQLite WAL + estate-graph retrieval index active (0 bash find/grep loops)',
        predicateType: 'sqlite_wal_active',
      },
    ],
  },
  {
    id: 'intent.oia_gtm.claim_audit',
    name: 'OIA GTM Investigation & PR Claim Provenance Audit',
    version: '1.4.0',
    description:
      'Queries all OIA GTM tickets, PRs (#891), and claims (#741) in Pass 1 via hybrid RRF search and verifies cryptographic step receipts.',
    targetQuery: 'OIA GTM investigation claim PR',
    requireCifSignature: true,
    maxAllowedSplitBrain: 1,
    yamlSource: `apiVersion: cif.estate.io/v2
kind: ComposableIntent
metadata:
  id: intent.oia_gtm.claim_audit
  owner: oia-gtm-lead
spec:
  oracle_query:
    match: "OIA GTM investigation claim PR"
    ranking: hybrid_bm25_rrf_pagerank
    max_pass: 1
  expected_outcomes:
    - id: gtm_artifacts_indexed
      predicate: min_results
      threshold: 2
    - id: gtm_receipts_signed
      predicate: all_cif_verified`,
    expectedOutcomes: [
      {
        id: 'gtm_artifacts_indexed',
        assertion: 'At least 2 OIA GTM investigation entities (Claims & PRs) indexed in estate-graph',
        predicateType: 'min_results',
        threshold: 2,
      },
      {
        id: 'gtm_receipts_signed',
        assertion: 'All matched OIA GTM claims carry valid CIF HMAC-SHA256 step_runs receipts',
        predicateType: 'all_cif_verified',
      },
    ],
  },
  {
    id: 'intent.k3s.rust_spine_admission',
    name: 'Oracle k3s Rust-Only Spine & Falsification Gate (#7318)',
    version: '1.0.3',
    description:
      'Verifies that fake VERIFIED_LIVE scripts (bin/idp-vault-refs) are quarantined and the k3s control plane runs the static Rust binary under 20MB RAM.',
    targetQuery: '7318 k3s rust idp-vault-refs',
    requireCifSignature: true,
    maxAllowedSplitBrain: 1,
    yamlSource: `apiVersion: cif.estate.io/v2
kind: ComposableIntent
metadata:
  id: intent.k3s.rust_spine_admission
  owner: k3s-admission-controller
spec:
  oracle_query:
    match: "7318 k3s rust idp-vault-refs"
    ranking: hybrid_bm25_rrf_pagerank
  expected_outcomes:
    - id: k3s_entities_present
      predicate: min_results
      threshold: 2
    - id: k3s_cif_signed
      predicate: all_cif_verified`,
    expectedOutcomes: [
      {
        id: 'k3s_entities_present',
        assertion: 'Oracle k3s #7318 & CIF kernel schema entities retrieved in Pass 1',
        predicateType: 'min_results',
        threshold: 2,
      },
      {
        id: 'k3s_cif_signed',
        assertion: 'All k3s spine & falsification receipts carry valid HMAC signatures',
        predicateType: 'all_cif_verified',
      },
    ],
  },
];

export const RUST_CARGO_TOML_SOURCE = `[package]
name = "estate-overwatch"
version = "0.4.0"
edition = "2021"
description = "Single-binary Telegram Supergroup Control Plane, 60fps TMA WebSocket HUD & CIF SQLite Oracle"

[dependencies]
teloxide = { version = "0.13", features = ["macros", "rustls"] }
axum = { version = "0.7", features = ["ws", "macros"] }
sqlx = { version = "0.8", features = ["runtime-tokio-rustls", "sqlite", "macros"] }
tokio = { version = "1.40", features = ["rt-multi-thread", "macros", "sync", "time"] }
notify = { version = "6.1", default-features = false, features = ["macos_kqueue"] }
hmac = "0.12"
sha2 = "0.10"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
panic = "abort"
strip = true
# Compiles to 14.8 MB static musl binary · Peak RSS: 18.2 MB on Oracle Free Tier k3s`;
