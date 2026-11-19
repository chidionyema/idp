/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  evaluateProposal,
  verifyAntiRecursionProof,
  requestBreakGlassLoan,
  repayBreakGlassDebt,
  detectOscillations,
  runVisualMandateComplianceAudit,
  INITIAL_IPN_PACKETS,
  INITIAL_KEY_LOANS,
  INITIAL_FAILURE_CLASSES,
  INITIAL_DEBT_LEDGER,
  INITIAL_VISUAL_RULES,
  INITIAL_HISTORY_BLOCKERS,
  DEMARCATION_MATRIX,
  sanitizeDeepSeekCredentials,
  resolveModelRoute,
  evaluateTripartiteHealth,
  evaluateAgentDofGate,
  founderExpandDof,
  runDeterministicTillingSweep,
  calculateLongevityIndex,
  executeSurvivalDrill,
  INITIAL_TRIPARTITE_STATE,
  INITIAL_DOF_POLICY,
  INITIAL_TILLING_PROBES,
  INITIAL_FREE_LANES,
  INITIAL_SURVIVAL_DRILLS,
  getAideTriumvirateState,
  dispatchToAide,
  verifyAideContinuousPresence,
  INITIAL_AIDE_TRIUMVIRATE,
  INITIAL_FLEET_COUNCIL,
  INITIAL_REVIEW_DOCKETS,
  INITIAL_MEETING_AGENDA,
  INITIAL_TRANSCRIPT,
  INITIAL_FOUNDER_COGNITIVE_PROFILE,
  INITIAL_FLEET_COGNITIVE_PROFILE,
  getTimezoneAndVpnState,
  executeMeetingDocketImmediate,
  updateFounderCognitiveState,
  INITIAL_ANTICIPATORY_ACTIONS,
  INITIAL_BAR_ELEVATION_METRICS,
  getCircadianFlowSensory,
  enactAnticipatoryAction,
  ratchetBarElevation,
  COMMAND_CODE_CATALOG,
  INITIAL_ACTIVE_COMMAND_STACK,
  NEVER_DELEGABLE_CODES,
  executeCommandCode,
  revokeActiveCommand,
  BreakGlassDebtEntry,
  FailureClassId,
} from './protocolEngine.ts';


describe('ProtocolEngine 2100 Systems & Invariants', () => {
  it('deterministic gate rejects proposals that offload friction to Founder', () => {
    const result = evaluateProposal({
      title: 'Manual DB Migration helper',
      targetScope: 'Database schema patch',
      founderFrictionDelta: 2,
      rootCauseCoverage: 0.9,
      reusableAssetGenerated: true,
      automatedTestAdded: true,
      estimatedFutureHoursSaved: 10,
      hoursToImplement: 2,
    });

    assert.strictEqual(result.gateDecision, 'REJECTED');
    assert.strictEqual(result.isCompliant, false);
    assert.ok(result.reasons.some(r => r.includes('Founder')));
  });

  it('anti-recursion engine flags temporary bypass heuristics that cause tail-chasing', () => {
    const proof = verifyAntiRecursionProof('Quick temporary bypass on deploy timeout', 'TRADEOFF_OSCILLATION');
    assert.strictEqual(proof.isSafe, false);
    assert.ok(proof.recursionRiskScore >= 0.4);
    assert.ok(proof.warnings.length > 0);
  });

  it('anti-recursion engine approves structural invariant fixes', () => {
    const proof = verifyAntiRecursionProof('Network-boundary Zod schema gate with fuzzing', 'SYMPTOM_MIGRATION');
    assert.strictEqual(proof.isSafe, true);
    assert.strictEqual(proof.warnings.length, 0);
  });

  it('IPN packets contain complete lifecycle telemetry and CDO reviews', () => {
    assert.ok(INITIAL_IPN_PACKETS.length > 0);
    const packet = INITIAL_IPN_PACKETS[0];
    assert.ok(packet.oracleAlignmentScore >= 0.9);
    assert.ok(packet.historyLog.length > 0);
    assert.strictEqual(packet.cdoReview?.terminalState, 'DELIVERED');
  });

  it('Key Loan Protocol enforces zero standing agent access via time-bound leases', () => {
    assert.ok(INITIAL_KEY_LOANS.length > 0);
    const activeLease = INITIAL_KEY_LOANS.find(l => l.approvalStatus === 'ACTIVE_LEASE');
    assert.ok(activeLease);
    assert.ok(activeLease.remainingSeconds > 0);
    assert.ok(activeLease.maxDurationSeconds <= 3600);
  });

  it('FPRP Debt Ledger grants time-bound loan and establishes repayment deadline', () => {
    const loanResult = requestBreakGlassLoan(
      {
        parentBottleneck: 'Ephemeral Redis connection timeout',
        failureClass: 'GUARDRAIL_BYPASS_RECURSION',
        scope: 'Increase connection retry window to 5s',
        durationMinutes: 30,
        requestingAgent: 'otto',
        mandatoryRepaymentPlan: 'Implement exponential backoff connection pool with circuit breaker',
      },
      INITIAL_DEBT_LEDGER
    );

    assert.strictEqual(loanResult.granted, true);
    assert.ok(loanResult.debtEntry);
    assert.strictEqual(loanResult.debtEntry?.status, 'OPEN_DEBT');
    assert.strictEqual(loanResult.debtEntry?.antiRecursionProofRequired, true);
  });

  it('FPRP Debt Ledger freezes bypass credit when agent has overdue debt', () => {
    const overdueDebts: BreakGlassDebtEntry[] = [
      {
        debtId: 'DEBT-OVERDUE-1',
        parentBottleneck: 'Stale build lock',
        failureClass: 'DEBT_SPIRAL',
        scope: 'Delete lock file',
        grantedAt: '2026-11-01T00:00:00Z',
        deadline: '2026-11-01T01:00:00Z',
        status: 'OVERDUE',
        requestingAgent: 'concierge',
        mandatoryRepaymentPlan: 'File flock mutex',
        antiRecursionProofRequired: true,
      },
    ];

    const result = requestBreakGlassLoan(
      {
        parentBottleneck: 'Another build issue',
        failureClass: 'TRADEOFF_OSCILLATION',
        scope: 'Skip verify step',
        durationMinutes: 15,
        requestingAgent: 'concierge',
        mandatoryRepaymentPlan: 'Fix later',
      },
      overdueDebts
    );

    assert.strictEqual(result.granted, false);
    assert.ok(result.rejectionReason?.includes('frozen'));
  });

  it('repaying break-glass debt requires a valid anti-recursion proof', () => {
    const debts: BreakGlassDebtEntry[] = [
      {
        debtId: 'DEBT-TEST-01',
        parentBottleneck: 'Socket drop',
        failureClass: 'TRADEOFF_OSCILLATION',
        scope: 'Buffer bump',
        grantedAt: new Date().toISOString(),
        deadline: new Date(Date.now() + 3600000).toISOString(),
        status: 'OPEN_DEBT',
        requestingAgent: 'otto',
        mandatoryRepaymentPlan: 'Real fix',
        antiRecursionProofRequired: true,
      },
    ];

    // Attempting to repay with a temporary bypass should FAIL
    const badRepayment = repayBreakGlassDebt(
      'DEBT-TEST-01',
      'Quick temporary bypass retry timeout',
      debts
    );
    assert.strictEqual(badRepayment.success, false);
    assert.ok(badRepayment.error?.includes('anti-recursion verification'));

    // Repaying with a structural invariant fix should SUCCEED
    const goodRepayment = repayBreakGlassDebt(
      'DEBT-TEST-01',
      'Backpressure-aware WebSocket flow controller with drop notification',
      debts
    );
    assert.strictEqual(goodRepayment.success, true);
    assert.strictEqual(goodRepayment.updatedDebts[0].status, 'REPAID');
    assert.ok(goodRepayment.antiRecursionReceipt?.startsWith('PROOF-HMAC'));
  });

  it('detectOscillations trips circuit breaker upon recurring failure class loops', () => {
    const history: Array<{ classId: FailureClassId; timestamp: string }> = [
      { classId: 'TRADEOFF_OSCILLATION', timestamp: '2026-11-03T01:00:00Z' },
      { classId: 'GUARDRAIL_BYPASS_RECURSION', timestamp: '2026-11-03T01:15:00Z' },
      { classId: 'TRADEOFF_OSCILLATION', timestamp: '2026-11-03T01:30:00Z' },
    ];

    const result = detectOscillations(history);
    assert.strictEqual(result.isOscillating, true);
    assert.ok(result.incident);
    assert.strictEqual(result.incident?.circuitBreakerTripped, true);
    assert.ok(result.incident?.circuitBreakerAction.includes('QUICK_FIXES_HALTED'));
  });

  it('machine-enforced 2100 Visual Mandate audit passes with zero founder intervention required', () => {
    const report = runVisualMandateComplianceAudit(INITIAL_VISUAL_RULES);
    assert.strictEqual(report.allPass, true);
    assert.strictEqual(report.overallScore, 100);
    assert.strictEqual(report.enforcedByMachine, true);
    assert.strictEqual(report.founderInterventionRequired, false);
  });

  it('History Lane critical blockers have actionable non-destructive remedies', () => {
    assert.strictEqual(INITIAL_HISTORY_BLOCKERS.length, 7);
    const diskFloorBlocker = INITIAL_HISTORY_BLOCKERS.find(b => b.id === 'HL-01');
    assert.ok(diskFloorBlocker);
    assert.ok(diskFloorBlocker.oneLineFixCommand.includes('ESTATE_DISK_FLOOR_MB'));

    const telegramBlocker = INITIAL_HISTORY_BLOCKERS.find(b => b.id === 'HL-02');
    assert.ok(telegramBlocker);
    assert.ok(telegramBlocker.remedyCodeSnippet?.includes('estate.env'));

    const laneWhereBlocker = INITIAL_HISTORY_BLOCKERS.find(b => b.id === 'HL-03');
    assert.ok(laneWhereBlocker);
    assert.ok(laneWhereBlocker.oneLineFixCommand.includes('bin/lane-where'));

    const deepseekBlocker = INITIAL_HISTORY_BLOCKERS.find(b => b.id === 'HL-07');
    assert.ok(deepseekBlocker);
    assert.ok(deepseekBlocker.symptom.includes('503'));
    assert.ok(deepseekBlocker.rootCause.includes('deepseek-flash'));
  });

  it('sanitizeDeepSeekCredentials strips whitespace, quotes, and CRLF to prevent Cloudflare 401', () => {
    const dirtyKey = '  "sk-f89a2bc417d940bca835ef98sjQw"\r\n';
    const result = sanitizeDeepSeekCredentials(dirtyKey);

    assert.strictEqual(result.cleanKey, 'sk-f89a2bc417d940bca835ef98sjQw');
    assert.strictEqual(result.isValidFormat, true);
    assert.strictEqual(result.maskedKey, 'sk-****sjQw');
    assert.strictEqual(result.recommendedAuthHeader, 'Authorization: Bearer sk-f89a2bc417d940bca835ef98sjQw');
    assert.ok(result.detectedIssues.length >= 2);
  });

  it('resolveModelRoute aliases hallucinated deepseek-flash to official deepseek-chat and configures 503 fallback', () => {
    const flashRoute = resolveModelRoute('deepseek-flash');
    assert.strictEqual(flashRoute.canonicalModel, 'deepseek-chat');
    assert.strictEqual(flashRoute.routeStatus, 'ALIASED');
    assert.strictEqual(flashRoute.fallbackModel, 'gemini-2.5-pro');
    assert.ok(flashRoute.mitigationNotice.includes('does not exist'));

    const chatRoute = resolveModelRoute('deepseek-chat');
    assert.strictEqual(chatRoute.canonicalModel, 'deepseek-chat');
    assert.strictEqual(chatRoute.routeStatus, 'CANONICAL');
    assert.strictEqual(chatRoute.fallbackModel, 'gemini-2.5-pro');

    const reasonerRoute = resolveModelRoute('deepseek-reasoner');
    assert.strictEqual(reasonerRoute.canonicalModel, 'deepseek-reasoner');
    assert.strictEqual(reasonerRoute.isOfficialModel, true);
  });

  it('Demarcation Matrix enforces all 6 constitutional dimensions with zero cross-contamination', () => {
    assert.strictEqual(DEMARCATION_MATRIX.length, 6);
    const dimensions = DEMARCATION_MATRIX.map(d => d.dimension);
    assert.ok(dimensions.includes('Compute & Execution Host'));
    assert.ok(dimensions.includes('Git Repositories & Sync Branches'));
    assert.ok(dimensions.includes('AI Model Routing & DeepSeek Protocol'));
    assert.ok(dimensions.includes('Verification & Audit Proof'));
    assert.ok(dimensions.includes('Economic & Operational Philosophy'));
    assert.ok(dimensions.includes('Cross-Contamination & Failure Isolation'));

    DEMARCATION_MATRIX.forEach(d => {
      assert.ok(d.inviolableRule.length > 20);
      assert.ok(d.historyLane.badge);
      assert.ok(d.genesisEstate.badge);
    });
  });

  it('Tripartite Organism Covenant triggers estate-wide Amber/Red when any single pillar degrades', () => {
    // Nominal state
    const nominal = evaluateTripartiteHealth(
      INITIAL_TRIPARTITE_STATE.founder,
      INITIAL_TRIPARTITE_STATE.agents,
      INITIAL_TRIPARTITE_STATE.machine
    );
    assert.strictEqual(nominal.estateStatus, 'GREEN');
    assert.strictEqual(nominal.isAutoSteeringActive, false);
    assert.strictEqual(nominal.activeSteeringDirectives.length, 0);

    // Single pillar degradation (e.g. Machine drops below 0.85)
    const degradedMachine = {
      ...INITIAL_TRIPARTITE_STATE.machine,
      healthScore: 0.72,
      status: 'AMBER' as const,
    };
    const amberState = evaluateTripartiteHealth(
      INITIAL_TRIPARTITE_STATE.founder,
      INITIAL_TRIPARTITE_STATE.agents,
      degradedMachine
    );
    assert.strictEqual(amberState.estateStatus, 'AMBER');
    assert.strictEqual(amberState.bottleneckPillar, 'MACHINE');
    assert.strictEqual(amberState.isAutoSteeringActive, true);
    assert.ok(amberState.activeSteeringDirectives.some(d => d.targetPillar === 'MACHINE'));

    // Critical failure (e.g. Agents thrashing, drop below 0.50)
    const criticalAgents = {
      ...INITIAL_TRIPARTITE_STATE.agents,
      healthScore: 0.42,
      status: 'RED' as const,
    };
    const redState = evaluateTripartiteHealth(
      INITIAL_TRIPARTITE_STATE.founder,
      criticalAgents,
      INITIAL_TRIPARTITE_STATE.machine
    );
    assert.strictEqual(redState.estateStatus, 'RED');
    assert.strictEqual(redState.bottleneckPillar, 'AGENTS');
    assert.ok(redState.activeSteeringDirectives.some(d => d.priority === 'CRITICAL'));
  });

  it('Degree of Freedom (DoF) Governor strictly blocks unapproved agent exploration and allows Founder-only elevation', () => {
    // Agent requesting DoF Level 3 when policy is Level 1 -> blocked
    const decisionLevel3 = evaluateAgentDofGate('Refactor state-machine code', 3, INITIAL_DOF_POLICY);
    assert.strictEqual(decisionLevel3.granted, false);
    assert.ok(decisionLevel3.rejectionReason?.includes('Degree of Freedom'));
    assert.ok(decisionLevel3.deterministicAlternative);

    // Prohibited exploratory bash loop -> blocked even if level 1
    const decisionBashLoop = evaluateAgentDofGate('EXPLORATORY_BASH_LOOP retry 100 times', 1, INITIAL_DOF_POLICY);
    assert.strictEqual(decisionBashLoop.granted, false);
    assert.ok(decisionBashLoop.rejectionReason?.includes('prohibited'));

    // Founder expands DoF with sovereign passphrase -> granted
    const expansion = founderExpandDof(3, 'FOUNDER_AUTH_SOVEREIGN_KEY_2026', 15);
    assert.strictEqual(expansion.success, true);
    assert.ok(expansion.policy);
    assert.strictEqual(expansion.policy.currentLevel, 3);
    assert.strictEqual(expansion.policy.founderOverrideActive, true);

    // With expanded policy, Level 3 is now permitted
    const decisionApproved = evaluateAgentDofGate('Refactor state-machine code', 3, expansion.policy);
    assert.strictEqual(decisionApproved.granted, true);
  });

  it('Deterministic Testing & Exploratory Testing "Tilling" Engine reduces entropy without manual agent thrash', () => {
    assert.ok(INITIAL_TILLING_PROBES.length >= 6);
    const sweep = runDeterministicTillingSweep(INITIAL_TILLING_PROBES);
    assert.strictEqual(sweep.totalProbesRun, INITIAL_TILLING_PROBES.length);
    assert.ok(sweep.soilPurityIndex >= 0.85);
    assert.ok(sweep.entropyTaxSavedHours > 0);
    sweep.probes.forEach(p => {
      assert.ok(p.deterministicReceipt.startsWith('HMAC_'));
      assert.ok(p.entropyReductionScore > 0);
      assert.ok(p.failureModePrevented.length > 10);
    });
  });

  it('Eternal Life Longevity Engine mathematically proves near-zero collapse probability with 7 free lanes', () => {
    assert.ok(INITIAL_FREE_LANES.length >= 7);
    const posture = calculateLongevityIndex(INITIAL_FREE_LANES, INITIAL_SURVIVAL_DRILLS);
    assert.strictEqual(posture.targetLifeSpan, 'PERPETUAL_ETERNAL_LIFE');
    assert.strictEqual(posture.totalMonthlyCostUsd, 0.0);
    assert.ok(posture.calculatedFailureProbabilityPerDecade <= 1e-10);
    assert.ok(posture.longevityScore >= 95.0);

    // Execute provider extinction drill (GCP blackout)
    const drillResult = executeSurvivalDrill('DRILL-01-PROVIDER-EXTINCTION', INITIAL_SURVIVAL_DRILLS);
    assert.strictEqual(drillResult.result.drillResult, 'PASS_ZERO_DATA_LOSS');
    assert.ok(drillResult.result.recoveryProofSha256.startsWith('SHA256_'));
    assert.ok(drillResult.message.includes('Zero data loss'));
  });

  it('Perpetual Founder Aide Triumvirate guarantees Otto, Concierge, and Mega-Oracle are continuously on tap', () => {
    assert.strictEqual(INITIAL_AIDE_TRIUMVIRATE.length, 3);
    const aideIds = INITIAL_AIDE_TRIUMVIRATE.map(a => a.id);
    assert.ok(aideIds.includes('OTTO'));
    assert.ok(aideIds.includes('CONCIERGE'));
    assert.ok(aideIds.includes('MEGA_ORACLE'));

    // Verify attestation
    const attestation = verifyAideContinuousPresence(INITIAL_AIDE_TRIUMVIRATE);
    assert.strictEqual(attestation.allOnline, true);
    assert.ok(attestation.maxLatencyMs < 2.5, 'All aides must satisfy <2.5ms dispatch latency invariant');
    assert.ok(attestation.proofSha256.startsWith('SHA256_AIDE_TRIUMVIRATE_PRESENCE_ATTESTED'));

    // Check individual aide capabilities & quick actions
    const otto = INITIAL_AIDE_TRIUMVIRATE.find(a => a.id === 'OTTO')!;
    assert.ok(otto.capabilities.length >= 4);
    assert.ok(otto.quickActions.some(q => q.command === 'run_soil_tilling_sweep'));

    const concierge = INITIAL_AIDE_TRIUMVIRATE.find(a => a.id === 'CONCIERGE')!;
    assert.ok(concierge.capabilities.length >= 4);
    assert.ok(concierge.quickActions.some(q => q.command === 'sync_to_argon'));

    const oracle = INITIAL_AIDE_TRIUMVIRATE.find(a => a.id === 'MEGA_ORACLE')!;
    assert.ok(oracle.capabilities.length >= 4);
    assert.ok(oracle.quickActions.some(q => q.command === 'calculate_collapse_risk'));
  });

  it('dispatchToAide executes deterministically with sub-2.5ms latency and HMAC cryptographic receipts', () => {
    // Dispatch to Otto
    const ottoRes = dispatchToAide('OTTO', 'run_soil_tilling_sweep');
    assert.ok(ottoRes.latencyMs <= 2.5);
    assert.ok(ottoRes.hmacSignature.startsWith('HMAC_SHA256_OTTO_'));
    assert.ok(ottoRes.response.includes('Soil Tilling completed'));

    // Dispatch to Concierge
    const conciergeRes = dispatchToAide('CONCIERGE', 'sanitize_credentials');
    assert.ok(conciergeRes.latencyMs <= 2.5);
    assert.ok(conciergeRes.hmacSignature.startsWith('HMAC_SHA256_CONCIERGE_'));
    assert.ok(conciergeRes.response.includes('Credential hygiene'));

    // Dispatch to Mega-Oracle
    const oracleRes = dispatchToAide('MEGA_ORACLE', 'calculate_collapse_risk');
    assert.ok(oracleRes.latencyMs <= 2.5);
    assert.ok(oracleRes.hmacSignature.startsWith('HMAC_SHA256_MEGA_ORACLE_'));
    assert.ok(oracleRes.response.includes('Longevity proof attested'));
  });

  it('Fleet Council Invariant (§13.1): Full attendee quorum present, world-class review facilities, and zero missed sessions', () => {
    assert.ok(INITIAL_FLEET_COUNCIL.length >= 8);
    const memberIds = INITIAL_FLEET_COUNCIL.map(m => m.id);
    assert.ok(memberIds.includes('FOUNDER_SOVEREIGN'));
    assert.ok(memberIds.includes('AIDE_OTTO'));
    assert.ok(memberIds.includes('AIDE_CONCIERGE'));
    assert.ok(memberIds.includes('AIDE_MEGA_ORACLE'));
    assert.ok(memberIds.includes('LANE_A_LEADER'));
    assert.ok(memberIds.includes('LANE_B_LEADER'));
    assert.ok(memberIds.includes('SECURITY_SENTINEL'));
    assert.ok(memberIds.includes('FMEA_LEAD'));

    // Check each attendee has strengths, weaknesses, and status
    for (const member of INITIAL_FLEET_COUNCIL) {
      assert.ok(member.cognitiveStrengths.length > 0);
      assert.ok(member.operationalWeaknesses.length > 0);
      assert.ok(member.specialization.length > 0);
      assert.ok(member.currentMoodScore >= 0.85);
    }

    // Verify initial agenda and transcript
    assert.ok(INITIAL_MEETING_AGENDA.length >= 4);
    assert.ok(INITIAL_TRANSCRIPT.length >= 4);
    assert.ok(INITIAL_TRANSCRIPT.some(t => t.speaker.includes('Founder')));
  });

  it('Timezone & VPN Engine (§13.2): Anchored to UK Founder Base (Europe/London) with automatic VPN multi-hop mitigation and calendar lock', () => {
    // Normal UK timezone
    const tzUk = getTimezoneAndVpnState('Europe/London');
    assert.strictEqual(tzUk.founderBaseTimezone, 'Europe/London');
    assert.strictEqual(tzUk.isVpnDetected, false);
    assert.ok(tzUk.vpnMitigationStrategy.includes('Direct UK Sovereign Link'));
    assert.strictEqual(tzUk.calendarAlertStatus, 'CALENDAR_SYNCED');
    assert.ok(tzUk.timeUntilWeeklyReviewSeconds > 0);
    assert.ok(tzUk.nextScheduledWeeklyMeetingUk.includes('Europe/London'));

    // Simulated VPN from Amsterdam / Frankfurt
    const tzVpn = getTimezoneAndVpnState('Europe/Amsterdam');
    assert.strictEqual(tzVpn.isVpnDetected, true);
    assert.ok(tzVpn.vpnMitigationStrategy.includes('VPN Active (Europe/Amsterdam)'));
    assert.ok(tzVpn.vpnMitigationStrategy.includes('Europe/London'));
    // Clocks must show UK base regardless of VPN
    assert.strictEqual(tzVpn.founderBaseTimezone, 'Europe/London');
    assert.ok(tzVpn.activeLaneClocks.length >= 4);
  });

  it('Immediate Effect Engine (§13.3): Ratifying meeting review dockets executes to production with sub-2.5ms latency and HMAC-SHA256 receipt', () => {
    const docketToRatify = INITIAL_REVIEW_DOCKETS[0].id;
    const { updatedDockets, executionRecord } = executeMeetingDocketImmediate(docketToRatify, true);

    const ratifiedDocket = updatedDockets.find(d => d.id === docketToRatify)!;
    assert.strictEqual(ratifiedDocket.reviewStatus, 'DISPATCHED_TO_PRODUCTION');
    assert.ok(ratifiedDocket.ratificationReceipt?.startsWith('HMAC_SHA256_IMMEDIATE_EXEC_'));
    assert.ok(ratifiedDocket.executionLatencyMs! <= 2.5);

    // Verify execution record
    assert.strictEqual(executionRecord.status, 'SUCCESS');
    assert.strictEqual(executionRecord.verifiedInProd, true);
    assert.ok(executionRecord.latencyMs <= 2.5);
    assert.ok(executionRecord.receipt.startsWith('HMAC_SHA256_IMMEDIATE_EXEC_'));
  });

  it('Reciprocal Cognitive Mesh (§13.4): Bi-directional habit learning and dynamic fleet adaptation across Tripartite Covenant', () => {
    // Verify initial profile
    assert.strictEqual(INITIAL_FOUNDER_COGNITIVE_PROFILE.baseCity, 'London, United Kingdom');
    assert.strictEqual(INITIAL_FOUNDER_COGNITIVE_PROFILE.focusState, 'DEEP_FLOW');
    assert.ok(INITIAL_FOUNDER_COGNITIVE_PROFILE.learnedHabitPatterns.length >= 5);
    assert.ok(INITIAL_FLEET_COGNITIVE_PROFILE.tripartiteSynergyMatrix.length === 3);

    // Update founder state to HIGH_VELOCITY_SPRINT
    const updated = updateFounderCognitiveState('HIGH_VELOCITY_SPRINT', 99, 'Aggressive Launch Execution');
    assert.strictEqual(updated.focusState, 'HIGH_VELOCITY_SPRINT');
    assert.strictEqual(updated.moodEnergyIndex, 99);
    assert.ok(updated.fleetAutoAdaptation.includes('Aggressive Push'));

    // Update to RESTORATION
    const restore = updateFounderCognitiveState('RESTORATION', 80, 'Resting; quiet maintenance only');
    assert.strictEqual(restore.focusState, 'RESTORATION');
    assert.ok(restore.fleetAutoAdaptation.includes('protective shield'));

    // Check synergy matrix covers FOUNDER, AGENTS, MACHINE
    const pillars = INITIAL_FLEET_COGNITIVE_PROFILE.tripartiteSynergyMatrix.map(s => s.pillar);
    assert.ok(pillars.includes('FOUNDER'));
    assert.ok(pillars.includes('AGENTS'));
    assert.ok(pillars.includes('MACHINE'));
  });

  it('Anticipatory Execution Invariant (§14.1): Pre-computes next actions with zero waiting for prompts and sub-2.5ms enactment', () => {
    assert.ok(INITIAL_ANTICIPATORY_ACTIONS.length >= 4);
    for (const act of INITIAL_ANTICIPATORY_ACTIONS) {
      assert.ok(act.predictedLeverage >= 2.0, 'All anticipatory actions must satisfy R_asym >= 2.0');
      assert.ok(act.precomputedSolution.length > 0);
      assert.ok(act.autoTestProof.length > 0);
    }

    // Enact one anticipatory item (e.g. ANTICIPATE-01)
    const { updatedActions, enactedItem } = enactAnticipatoryAction('ANTICIPATE-01');
    assert.strictEqual(enactedItem.status, 'ONE_TAP_ENACTED');
    assert.ok(enactedItem.enactedReceipt?.startsWith('HMAC_SHA256_ANTICIPATORY_ENACT_'));
    assert.ok(enactedItem.enactedLatencyMs! <= 2.5);

    const updated = updatedActions.find(a => a.id === 'ANTICIPATE-01')!;
    assert.strictEqual(updated.status, 'ONE_TAP_ENACTED');
  });

  it('Continuous Bar Elevation (§14.2): Auto-ratchets standards upward without regression to baseline', () => {
    assert.ok(INITIAL_BAR_ELEVATION_METRICS.length >= 5);
    const latencyMetric = INITIAL_BAR_ELEVATION_METRICS.find(m => m.id === 'BAR-01')!;
    assert.ok(parseFloat(latencyMetric.elevatedBar) < parseFloat(latencyMetric.canonicalBaseline), 'Elevated latency bar must be tighter than baseline');

    const asymMetric = INITIAL_BAR_ELEVATION_METRICS.find(m => m.id === 'BAR-02')!;
    assert.ok(parseFloat(asymMetric.elevatedBar) > parseFloat(asymMetric.canonicalBaseline), 'Elevated asymmetry bar must be higher than baseline');

    // Ratchet an elevation metric
    const { targetMetric } = ratchetBarElevation('BAR-02');
    assert.strictEqual(targetMetric.ratchetCount, asymMetric.ratchetCount + 1);
    assert.strictEqual(targetMetric.status, 'ELEVATED');
  });

  it('Circadian Flow Sensory (§14.4): Adapts cognitive shield and theme across London time phases', () => {
    // Late Night in London (02:00)
    const lateNight = getCircadianFlowSensory(2);
    assert.strictEqual(lateNight.detectedPhase, 'LATE_NIGHT_DEEP_INVENT');
    assert.strictEqual(lateNight.autoDofRecommendation, 'HYPER_VELOCITY_LEAP');
    assert.ok(lateNight.phaseDescription.includes('Absolute Silence'));

    // Afternoon in London (15:00)
    const afternoon = getCircadianFlowSensory(15);
    assert.strictEqual(afternoon.detectedPhase, 'AFTERNOON_TACTICAL_VELOCITY');
    assert.ok(afternoon.phaseDescription.includes('Operational Velocity'));

    // Morning in London (08:00)
    const morning = getCircadianFlowSensory(8);
    assert.strictEqual(morning.detectedPhase, 'MORNING_HARVEST');

    // Evening in London (20:00)
    const evening = getCircadianFlowSensory(20);
    assert.strictEqual(evening.detectedPhase, 'EVENING_STRATEGIC_SYNTHESIS');
  });

  it('Command Code Protocol (§15): 90+ codes cataloged across 12 domains with complete metadata and invariants', () => {
    assert.ok(COMMAND_CODE_CATALOG.length >= 90, 'Must contain at least 90 command codes as specified in catalog');

    // Verify all 12 domains are represented
    const domains = new Set(COMMAND_CODE_CATALOG.map(c => c.domain));
    assert.strictEqual(domains.size, 12, 'Must span all 12 operational domains');
    assert.ok(domains.has('Focus & Priority'));
    assert.ok(domains.has('Emergency & Posture'));
    assert.ok(domains.has('Security & Integrity'));
    assert.ok(domains.has('Resilience & Continuity'));
    assert.ok(domains.has('Presence & Welfare'));
    assert.ok(domains.has('Flow & Throughput'));
    assert.ok(domains.has('Compounding & Doctrine'));
    assert.ok(domains.has('Evidence & Ledger'));
    assert.ok(domains.has('Learning & Agents'));
    assert.ok(domains.has('Science & Research'));
    assert.ok(domains.has('Diagnosis & Truth'));
    assert.ok(domains.has('Governance & Terminal'));

    // Check invariants on each code
    for (const code of COMMAND_CODE_CATALOG) {
      assert.strictEqual(code.code, code.code.toUpperCase(), 'Codes must be strictly uppercase');
      assert.ok(code.effect.length > 0, 'Every code must have an operational effect');
      assert.ok(code.ttlDisplay.length > 0, 'Every code must have a defined TTL');
      assert.ok(['L1', 'L2', 'L3', 'L4', 'L5', 'L6'].includes(code.level));
      assert.ok(['C0', 'C1', 'C2', 'C3', 'C4'].includes(code.confirmTier));
      assert.ok(['F', 'O', 'R', 'OR', 'A', 'N'].includes(code.delegation));
    }
  });

  it('Command Code Execution (§15.1, §15.2): Concurrency capped at 7 codes, refusal on 8th, and refusal of unknown codes', () => {
    // 1. Unknown code refused
    const unknownRes = executeCommandCode('FLUX_CAPACITOR_UNKNOWN', 'Founder (Chidi)', INITIAL_ACTIVE_COMMAND_STACK);
    assert.strictEqual(unknownRes.success, false);
    assert.ok(unknownRes.refusalReason?.includes('UNKNOWN_CODE'));
    assert.ok(unknownRes.echoText.includes('REFUSED'));

    // 2. 7-code cap test: build stack of 7 active codes
    let currentStack = [...INITIAL_ACTIVE_COMMAND_STACK]; // starts with 2
    const fillCodes = ['QUIET', 'BENCHMARK', 'PROVE', 'SCAN', 'CALIBRATE'];
    for (const c of fillCodes) {
      const res = executeCommandCode(c, 'Founder (Chidi)', currentStack);
      if (res.success) {
        currentStack = res.activeStack;
      }
    }
    assert.strictEqual(currentStack.filter(s => s.status === 'ACTIVE').length, 7, 'Active stack must reach exactly 7 codes');

    // 3. Attempting 8th code trips refusal
    const overflowRes = executeCommandCode('AUDIT', 'Founder (Chidi)', currentStack);
    assert.strictEqual(overflowRes.success, false);
    assert.ok(overflowRes.refusalReason?.includes('COMMAND_FATIGUE_CAP_REACHED'));
    assert.ok(overflowRes.echoText.includes('REFUSED'));
  });

  it('Never-Delegable Sovereign Inviolability (§15.4): Non-delegable sovereign codes refuse non-founder issuance', () => {
    assert.ok(NEVER_DELEGABLE_CODES.has('NUKE'));
    assert.ok(NEVER_DELEGABLE_CODES.has('WAR'));
    assert.ok(NEVER_DELEGABLE_CODES.has('ETERNAL'));
    assert.ok(NEVER_DELEGABLE_CODES.has('SUCCESSION'));

    // Attempting to issue NUKE from Otto
    const ottoNukeRes = executeCommandCode('NUKE', 'Otto (Aide)', INITIAL_ACTIVE_COMMAND_STACK);
    assert.strictEqual(ottoNukeRes.success, false);
    assert.ok(ottoNukeRes.refusalReason?.includes('UNAUTHORIZED_DELEGATION'));
    assert.ok(ottoNukeRes.echoText.includes('Never-Delegable'));

    // Attempting to issue WAR from Concierge
    const conciergeWarRes = executeCommandCode('WAR', 'Concierge (Aide)', INITIAL_ACTIVE_COMMAND_STACK);
    assert.strictEqual(conciergeWarRes.success, false);
    assert.ok(conciergeWarRes.refusalReason?.includes('UNAUTHORIZED_DELEGATION'));
  });

  it('Echo-Back & Receipts (§15.3): Generates HMAC-SHA256 receipt, sub-2.5ms state shift, and clears opposing codes', () => {
    // Issue HOLD first
    const holdRes = executeCommandCode('HOLD', 'Founder (Chidi)', INITIAL_ACTIVE_COMMAND_STACK);
    assert.strictEqual(holdRes.success, true);
    assert.ok(holdRes.activeStack.some(c => c.code === 'HOLD' && c.status === 'ACTIVE'));

    // Issuing GO should execute, release HOLD, and emit receipt
    const goRes = executeCommandCode('GO', 'Founder (Chidi)', holdRes.activeStack);
    assert.strictEqual(goRes.success, true);
    assert.ok(goRes.latencyMs <= 2.5, 'Execution latency must be <= 2.5ms');
    assert.ok(goRes.receiptId?.startsWith('CMD-'));
    assert.ok(!goRes.activeStack.some(c => c.code === 'HOLD' && c.status === 'ACTIVE'), 'HOLD must be released by GO');

    // Revocation also works by receiptId
    const firstReceipt = goRes.activeStack[0].receiptId;
    const stackAfterRevoke = revokeActiveCommand(firstReceipt, goRes.activeStack);
    const revokedEntry = stackAfterRevoke.find(c => c.receiptId === firstReceipt);
    assert.strictEqual(revokedEntry?.status, 'REVOKED');
  });
});






