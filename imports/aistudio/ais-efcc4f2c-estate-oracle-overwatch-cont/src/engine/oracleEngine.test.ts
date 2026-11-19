import test from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import {
  computeCifHmac,
  verifyCifReceipt,
  queryEstateOracle,
  parseSearchQuery,
  parseAndIngestRawDump,
  evaluateComposableIntent,
  reconcileOttoSplitBrain,
  generateStandaloneOracleCliScript,
  generateMacOsDoubleClickInstaller,
  generateFounderNightWatchGift,
  type EstateEntity,
  type OttoInstanceState,
  type ComposableIntent,
} from './oracleEngine';
import {
  createInitialArgonMemoryPlaneState,
  remediateMemoryPlaneAndSignDecree,
  runDreamConsolidationCycle,
  buildBudgetedClaimOpenBrief,
} from './memoryPlaneEngine';
import {
  evaluatePlanFenceSequence,
  createInitialRouterAndProtocolState,
  pollConsultingInboxAndPromoteToOutbox,
  switchLaneProtocolInRealTime,
  executeInstructionPacketAndMeasureYieldAlpha,
} from '../../extensions/pi-plan-lock/plan';

const sampleEntities: EstateEntity[] = [
  {
    id: 'CLAIM-OIA-GTM-741',
    kind: 'claim_ticket',
    title: 'OIA GTM Investigation: Asymmetric Pipeline & Claim Verification Audit',
    lane: 'oia-gtm-audit',
    summary: 'Deep audit of OIA GTM recent investigation work, unverified PR claims, and ticket handoffs.',
    repoOrPath: '~/estate/oia-gtm-engine',
    branchOrRef: 'feat/oia-gtm-cif-claims',
    authorOrAgent: 'pi-lane-02',
    timestamp: '2026-10-31T08:55:00Z',
    cifVerified: true,
    hmacSignature: 'a1b2c3d4e5f60718293a4b5c6d7e8f90112233445566778899aabbccddeeff00',
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['PR-884', 'TICKET-7318'],
    tokens: ['oia', 'gtm', 'investigation', 'claim', 'ticket', 'pr'],
    graphCentrality: 0.94,
    rawPayload: 'SELECT * FROM step_runs WHERE ticket_id = "CLAIM-OIA-GTM-741";',
  },
  {
    id: 'DAEMON-OTTO-V1-LEGACY',
    kind: 'worktree_daemon',
    title: 'Otto v1 Legacy MCP Daemon (Split-Brain Duplicate)',
    lane: 'otto-front-door',
    summary: 'Competing Otto process reading stale ~/Desktop/otto-old-worktree markdown files without CIF HMAC.',
    repoOrPath: '~/Desktop/otto-old-worktree',
    branchOrRef: 'wip/otto-local-markdown',
    authorOrAgent: 'otto-v1-mcp',
    timestamp: '2026-10-31T09:10:00Z',
    cifVerified: false,
    hmacSignature: 'UNVERIFIED_MUTABLE_LOG',
    exitCode: 1,
    asymmetricDriftRisk: 'critical_split_brain',
    linkedIds: ['CLAIM-OTTO-AUDIT-902'],
    tokens: ['otto', 'split-brain', 'asymmetric', 'mcp', 'worktree'],
    graphCentrality: 0.89,
    rawPayload: 'PID 41892 node /Users/founder/Desktop/otto-old-worktree/mcp-server.js',
  },
  {
    id: 'TICKET-7318',
    kind: 'estate_layer',
    title: 'OKE Blocked (#7318) -> Pivot to Oracle Free Tier k3s Rust Spine',
    lane: 'k3s-overwatch-spine',
    summary: 'argon lacks k8s manifests and bin/idp-vault-refs faked VERIFIED_LIVE. Enforcing Rust-only k3s admission.',
    repoOrPath: '~/estate/k3s-overwatch-rust',
    branchOrRef: 'main',
    authorOrAgent: 'architect-kernel',
    timestamp: '2026-10-31T07:30:00Z',
    cifVerified: true,
    hmacSignature: '99887766554433221100ffeeddccbbaa99887766554433221100ffeeddccbbaa',
    exitCode: 0,
    asymmetricDriftRisk: 'none',
    linkedIds: ['CLAIM-OIA-GTM-741'],
    tokens: ['oke', '7318', 'oracle', 'k3s', 'rust', 'argon', 'idp-vault-refs'],
    graphCentrality: 0.91,
    rawPayload: 'Cargo.toml: teloxide + axum + sqlx static binary 14.8MB',
  },
];

test('CIF HMAC-SHA256 deterministic signature computation and verification', () => {
  const sig = computeCifHmac('TICKET-101', 1, 'cargo check --release', 'Finished release [optimized]', 0);
  assert.equal(sig.length, 64);

  const validReceipt = {
    ticketId: 'TICKET-101',
    stepIdx: 1,
    cmd: 'cargo check --release',
    stdoutPayload: 'Finished release [optimized]',
    exitCode: 0,
    hmacSignature: sig,
  };
  assert.equal(verifyCifReceipt(validReceipt), true);
  assert.equal(verifyCifReceipt({ ...validReceipt, exitCode: 1 }), false);
  assert.equal(verifyCifReceipt({ ...validReceipt, stdoutPayload: 'ForgedVERIFIED_LIVE' }), false);
});

test('Hybrid BM25F + Trigram Typo Tolerance + Structured Search Operators work accurately', () => {
  const oiaResults = queryEstateOracle(sampleEntities, 'OIA GTM investigation claim');
  assert.ok(oiaResults.length >= 1);
  assert.equal(oiaResults[0].entity.id, 'CLAIM-OIA-GTM-741');

  const typoResults = queryEstateOracle(sampleEntities, 'ottto worktre');
  assert.ok(typoResults.length >= 1);
  assert.equal(typoResults[0].entity.id, 'DAEMON-OTTO-V1-LEGACY');
  assert.ok(typoResults[0].fuzzyCorrections.length >= 1);

  const unverifiedOnly = queryEstateOracle(sampleEntities, 'verified:false');
  assert.equal(unverifiedOnly.length, 1);
  assert.equal(unverifiedOnly[0].entity.id, 'DAEMON-OTTO-V1-LEGACY');

  const parsed = parseSearchQuery('kind:claim lane:oia "unverified PR" -legacy');
  assert.equal(parsed.filters.kind, 'claim');
  assert.equal(parsed.filters.lane, 'oia');
  assert.deepEqual(parsed.exactPhrases, ['unverified pr']);
  assert.deepEqual(parsed.excludedTerms, ['legacy']);
});

test('Raw terminal dump ingestor extracts PIDs, step_runs, PRs, and detects 2-Ottos split-brain', () => {
  const rawDump = `
=== 1. LIVE OTTO & PI PROCESSES ===
founder 41892 1.2 0.8 node ~/Desktop/otto-old-worktree/mcp-server.js
founder 88410 0.4 0.3 estate-overwatch --agent otto-day0 --db ~/.estate/estate.db
=== 3. ESTATE.DB LEDGER ===
104|CLAIM-OIA-GTM-741|estate-execute --verify oia-gtm|0
105|TICKET-GREENLANE-99|bin/idp-vault-refs fake VERIFIED_LIVE greenlane|1
  `;
  const report = parseAndIngestRawDump(rawDump, 'test-macbook-probe');
  assert.equal(report.ingestedCount, 4);
  assert.ok(report.detectedAnomalies.some((a) => a.includes('Split-Brain')));
  assert.ok(report.detectedAnomalies.some((a) => a.includes('CIF Gate Violation')));
});

test('Dual installation generators and Founder Night-Watch Gift produce signed verifiable artifacts', () => {
  const cliScript = generateStandaloneOracleCliScript('https://estate.example.com', 'estate-private');
  assert.ok(cliScript.includes('CREATE VIRTUAL TABLE IF NOT EXISTS estate_fts USING fts5'));
  assert.ok(cliScript.includes('gh repo create'));

  const macApp = generateMacOsDoubleClickInstaller('https://estate.example.com', 'estate-private');
  assert.ok(macApp.includes('osascript'));

  const { updatedInstances, updatedEntities, newReceipt } = reconcileOttoSplitBrain(
    [],
    sampleEntities,
    []
  );
  const gift = generateFounderNightWatchGift(updatedEntities, [newReceipt], updatedInstances, []);
  assert.equal(gift.nightWatchActive, true);
  assert.equal(gift.dossierHmacSignature.length, 64);
  assert.ok(gift.funderProofMarkdown.includes('CRYPTOGRAPHIC FUNDER DOSSIER'));
});

test('Argon Memory Plane remediates 0/18 lanes to 18/18, locks D1..D9 ballots, distills Dreaming memories, and budgets Claim-Open Briefs', () => {
  const initial = createInitialArgonMemoryPlaneState();
  assert.equal(initial.auditSummary.operatingLanes, 0);
  assert.equal(initial.auditSummary.totalLanes, 18);
  assert.equal(initial.auditSummary.openFindingsCount, 27);
  assert.equal(initial.ballots.length, 9);

  // Remediate all 18 lanes and sign Argon decree
  const { nextState, hmacSignature } = remediateMemoryPlaneAndSignDecree(initial);
  assert.equal(nextState.auditSummary.operatingLanes, 18);
  assert.equal(nextState.auditSummary.openFindingsCount, 0);
  assert.equal(nextState.auditSummary.specScenariosPassing, 29);
  assert.equal(nextState.argonDecreeSigned, true);
  assert.equal(hmacSignature.length, 64);

  // Run Dreaming V3+ consolidation cycle
  const dreamRes = runDreamConsolidationCycle(nextState, {
    title: 'Enforce Cross-Runtime Memory Canary on Cline & Codex',
    rawFailureEpisode: 'Verify Cline and Codex inject Claim Briefs before any code edit.',
    sourceTicket: 'TICKET-42-CANARY',
    probeCmd: 'estate-audit --probe-runtime=cline,codex',
    kind: 'procedural',
  });
  assert.equal(dreamRes.nextState.distilledMemories.length, initial.distilledMemories.length + 1);
  assert.ok(dreamRes.diffReport.includes('+++ b/growmos/memories/index.md'));

  // Build budgeted Claim-Open Brief
  const briefRes = buildBudgetedClaimOpenBrief(dreamRes.nextState.distilledMemories, 150, 0.85);
  assert.ok(briefRes.totalTokensUsed <= 150);
  assert.ok(briefRes.includedFacts.length >= 2);
  assert.equal(briefRes.staleRejectedFacts.length, 0);
  assert.ok(briefRes.renderedBriefMarkdown.includes('CLAIM-OPEN MEMORY BRIEF'));
});

test('All 5 production CLI binaries in bin/ execute against register/memory-lanes-18.json with 18/18 lanes operating', () => {
  const auditJsonRaw = execSync('node bin/estate-memory-audit --json', { encoding: 'utf-8' });
  const auditParsed = JSON.parse(auditJsonRaw);
  assert.equal(auditParsed.operatingLanes, 18);
  assert.equal(auditParsed.totalLanes, 18);
  assert.equal(auditParsed.openFindingsCount, 0);

  const decideOut = execSync('node bin/estate-decide', { encoding: 'utf-8' });
  assert.ok(decideOut.includes('DECISION-ARGON-MEMORY-0021'));

  const briefOut = execSync('node bin/estate-claim-brief --ticket=TICKET-42 --budget=220', {
    encoding: 'utf-8',
  });
  assert.ok(briefOut.includes('Stale-Served: 0/'));

  const submitOut = execSync(
    'node bin/estate-lane-submit --ticket=TICKET-42 -- echo "PRODUCTION_READY"',
    { encoding: 'utf-8' }
  );
  assert.ok(submitOut.includes('Captured & Signed (TICKET-42)'));

  const dreamOut = execSync('node bin/memory-dream', { encoding: 'utf-8' });
  assert.ok(dreamOut.includes('MEMORY-DREAM BOUNDED CONSOLIDATION REPORT'));
});

test('Unified #7680 + #7692 Plan Contract Fence enforces 3-Tries Bound, Machine-Checkable BDD then, bin/estate-plan, and bin/idp-hypothesize', () => {
  const initialRouter = createInitialRouterAndProtocolState();
  assert.ok(initialRouter.protocolSessions.length >= 4);

  // 1. 4th identical call must be refused by 3-tries bound
  const fourTries = evaluatePlanFenceSequence(
    {
      given: 'extensions/pi-plan-lock/cases.json exists',
      when: 'agent invokes bash bin/idp-hypothesize --race-spec',
      then: 'exit_code == 0 && file_exists:extensions/pi-plan-lock/cases.json',
    },
    { tool: 'bash', input: { cmd: 'bin/idp-hypothesize --race-spec' } },
    4,
    3
  );
  assert.equal(fourTries.length, 4);
  assert.equal(fourTries[2].authorized, true);
  assert.equal(fourTries[3].authorized, false);
  assert.ok(fourTries[3].reason.includes('REFUSED_MAX_ATTEMPTS'));

  // 2. Uncheckable prose-only BDD then clause must be refused immediately
  const proseThen = evaluatePlanFenceSequence(
    {
      given: 'repo is clean',
      when: 'agent edits plan.py',
      then: 'everything works great and looks nice',
    },
    { tool: 'edit_file', input: { path: 'platform/estate/memory/plan.py' } },
    1,
    3
  );
  assert.equal(proseThen[0].authorized, false);
  assert.ok(proseThen[0].reason.includes('REFUSED_UNCHECKABLE_THEN'));

  // 3. Verify bin/estate-plan and bin/idp-hypothesize execute with exit code 0
  const planJson = JSON.parse(execSync('node bin/estate-plan --json', { encoding: 'utf-8' }));
  assert.equal(planJson.passedCases, 4);
  assert.equal(planJson.totalCases, 4);

  const hypJson = JSON.parse(execSync('node bin/idp-hypothesize --json', { encoding: 'utf-8' }));
  assert.equal(hypJson.governanceStatus, 'PASS');
  assert.equal(hypJson.subgoals[0].exitCode, 0);
});

test('Agent Service Resuscitator, Rust Router v2.4.0, Consulting Inbox/Outbox Poller, Spec Enforcer (ESTATE-SPEC-STD-V2) & Machine Catalog pass end-to-end', () => {
  const initialRouter = createInitialRouterAndProtocolState();
  assert.equal(initialRouter.activeAgentDaemonsCount, 4);
  assert.equal(initialRouter.rustRouterOptimizations.length, 6);

  // 1. Poll Consulting Lane Inbox with a new MiniMax M2.7 Big-Ticket dispatch
  const pollRes = pollConsultingInboxAndPromoteToOutbox(initialRouter, {
    senderAgent: 'minimax-fenced-worker-01 (MiniMax-M2.7)',
    ticketId: 'TICKET-MINIMAX-BIG-7799',
    ticketScope: 'BIG_TICKET_FENCED',
    subject: 'MiniMax Big-Ticket #7799: Audited via Consulting Lane Inbox',
    payloadSummary: 'Strict protocol envelope verified on Consulting Lane.',
    bddThenClause: 'exit_code == 0 && test_pass:minimax_consulting_inbox_gate',
  });
  assert.ok(pollRes.newEnvelope);
  assert.equal(pollRes.newEnvelope?.status, 'AUDITED_AND_PROMOTED_TO_OUTBOX');
  assert.ok(pollRes.newReceipt);
  assert.equal(pollRes.newReceipt?.exitCode, 0);

  // 2. Verify all 5 new CLI tools exit 0 with valid JSON reports
  const svcJson = JSON.parse(execSync('node bin/estate-service-up --json', { encoding: 'utf-8' }));
  assert.equal(svcJson.activeAgentsCount, 4);
  assert.equal(svcJson.exitCode, 0);

  const rustJson = JSON.parse(execSync('node bin/estate-rust-router --json', { encoding: 'utf-8' }));
  assert.equal(rustJson.allOptimizationsVerified, true);
  assert.equal(rustJson.optimizationsPassed, '6/6');

  const inboxJson = JSON.parse(execSync('node bin/estate-inbox-poll --json', { encoding: 'utf-8' }));
  assert.equal(inboxJson.allEnvelopesVerified, true);
  assert.ok(inboxJson.outboxCount >= 3);

  const specJson = JSON.parse(execSync('node bin/estate-spec-enforce --json', { encoding: 'utf-8' }));
  assert.equal(specJson.standardId, 'ESTATE-SPEC-STD-V2');
  assert.equal(specJson.allPassed, true);
  assert.equal(specJson.claudeRepoItemsReRefined, '4/4');

  const catalogJson = JSON.parse(
    execSync('node bin/estate-catalog-export --json', { encoding: 'utf-8' })
  );
  assert.equal(catalogJson.status, 'WHOLE_REPO_EXPORT_READY');
  assert.equal(catalogJson.exitCode, 0);

  const instJson = JSON.parse(
    execSync('node bin/estate-push-instructions --json', { encoding: 'utf-8' })
  );
  assert.equal(instJson.status, 'ALL_PROJECTS_DOCUMENTED_AND_PUSH_READY');
  assert.equal(instJson.projectsVerified, '5/5');
  assert.equal(instJson.exitCode, 0);
});

test('Red-Line Failure Classes (FC-01..FC-03) eradicated: bin/estate-router, bin/deepseek-direct (non-router), and bin/estate-eval (16/16 cases + Claude Inbox next work) pass side-by-side', () => {
  const routedJson = JSON.parse(execSync('node bin/estate-router --json', { encoding: 'utf-8' }));
  assert.equal(routedJson.status, 'OPERATIONAL_DUAL_ENGINE_ACTIVE');
  assert.equal(routedJson.normalizedEndpoint, '/v1/chat/completions');
  assert.equal(routedJson.directNonRouterShadow.parityMatch, true);
  assert.equal(routedJson.exitCode, 0);

  const directJson = JSON.parse(execSync('node bin/deepseek-direct --json', { encoding: 'utf-8' }));
  assert.equal(directJson.mode, 'DIRECT_NON_ROUTER_BYPASS');
  assert.equal(directJson.status, 'OPERATIONAL_DIRECT_SOCKET');
  assert.ok(directJson.strippedR1Traps.includes('messages[*].reasoning_content'));
  assert.equal(directJson.exitCode, 0);

  const evalJson = JSON.parse(execSync('node bin/estate-eval --json', { encoding: 'utf-8' }));
  assert.equal(evalJson.overallStatus, 'ALL_RED_LINES_ERADICATED_AND_EVAL_PASS');
  assert.equal(evalJson.failureClassesEradicated, '3/3');
  assert.equal(evalJson.evalScore, '16/16 (100%)');
  assert.equal(evalJson.exitCode, 0);
});

test('Claude Inbox Core (INBOX-007..009): Declarative Protocol Engineering, Real-Time Per-Lane Protocol Switching (War Games / Training), Instruction Packet Yield Alpha, and Quad/DNA/Generations pass end-to-end', () => {
  const initialRouter = createInitialRouterAndProtocolState();
  assert.equal(initialRouter.hardcodedTimeoutsInCode, 0);
  assert.equal(initialRouter.timeoutStrategy, 'PROGRESSIVE_PARTIAL_VALUE_YIELD');
  assert.equal(initialRouter.nonFunctionalContracts.length, 4);
  assert.equal(initialRouter.hotSwappableProtocols.length, 4);

  // 1. Real-time per-lane protocol switch to War Games Adversarial protocol
  const switched = switchLaneProtocolInRealTime(
    initialRouter,
    'deepseek-protocol-01',
    'PROTO-WAR-GAMES-ADVERSARIAL-V1'
  );
  assert.equal(
    switched.nextState.laneProtocolAssignments['deepseek-protocol-01'],
    'PROTO-WAR-GAMES-ADVERSARIAL-V1'
  );
  assert.equal(switched.switchedProtocol.mode, 'WAR_GAMES_EVAL');

  // 2. Execute Instruction Packet with soft-timeout progressive partial-value yield
  const pktRes = executeInstructionPacketAndMeasureYieldAlpha(
    switched.nextState,
    'Run War Games chaos drill and verify progressive partial value on soft timeout',
    'deepseek-protocol-01',
    true
  );
  assert.equal(pktRes.packetOutcome.firstPassFounderApproved, true);
  assert.equal(pktRes.packetOutcome.progressivePartialValueDelivered, true);
  assert.ok(pktRes.packetOutcome.yieldAlpha >= 0.85);
  assert.equal(pktRes.packetOutcome.lateCiCdGatesHit, 0);

  // 3. Verify bin/estate-protocol-engine CLI reads Claude Inbox Core docs (3/3) and couples with 18/18 Memory Plane
  const protoEngineJson = JSON.parse(
    execSync('node bin/estate-protocol-engine --json', { encoding: 'utf-8' })
  );
  assert.equal(protoEngineJson.status, 'PROTOCOL_ENGINEERING_AND_YIELD_ALPHA_VERIFIED');
  assert.equal(protoEngineJson.hardcodedTimeoutsInCode, 0);
  assert.equal(protoEngineJson.claudeInboxCoreDocsRead.length, 3);
  assert.equal(protoEngineJson.memoryPlaneIntegration.operatingLanes, '18/18');
  assert.ok(protoEngineJson.sampleInstructionPacketOutcome.yieldAlpha >= 0.9);
  assert.equal(
    protoEngineJson.quadIdentityDna.sovereignIdentityId,
    'ESTATE-SOVEREIGN-QUAD-ID-001'
  );
});






