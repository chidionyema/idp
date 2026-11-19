/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeDeterministicHash,
  evaluateSingleInvariant,
  evaluateGate,
  calculateMerkleRoot,
  verifyMerkleChainIntegrity,
  DEFAULT_INVARIANT_RULES,
  generateTimeSeriesTelemetry,
  detectEstateAnomalies,
  generateLatencyHeatmapData,
  generateDayZeroSecurityAlerts,
  DEFAULT_SURFACE_LATENCY_CAPS,
  syncLatencyCapsToRules,
  evaluateSurfaceLatencyViolation,
} from './optimus-engine';
import { InvariantRule, MetricPayload, MerkleLedgerBlock, LatencyHeatmapCell, DayZeroSecurityAlert, SurfaceLatencyCapConfig } from '../types/optimus';

test('deterministic hash generates standard 64-char hex string', () => {
  const hash1 = computeDeterministicHash('optimus-test-payload');
  const hash2 = computeDeterministicHash('optimus-test-payload');
  const hash3 = computeDeterministicHash('different-payload');

  assert.equal(hash1.length, 64);
  assert.equal(hash1, hash2, 'Identical inputs must yield identical hashes');
  assert.notEqual(hash1, hash3, 'Distinct inputs must yield distinct hashes');
});

test('evaluateSingleInvariant correctly validates >= floor constraints', () => {
  const coverageRule: InvariantRule = {
    id: 'INV-TEST-COV',
    name: 'Coverage',
    metricKey: 'coverage_percent',
    operator: '>=',
    threshold: 90,
    unit: '%',
    description: 'Minimum coverage test',
    applicableSurfaces: ['git_commit_push'],
    isHardGate: true,
  };

  const passing = evaluateSingleInvariant(coverageRule, { coverage_percent: 94.2 });
  assert.equal(passing.passed, true);
  assert.equal(passing.deviation, '+4.20%');

  const failing = evaluateSingleInvariant(coverageRule, { coverage_percent: 88.5 });
  assert.equal(failing.passed, false);
  assert.equal(failing.deviation, '-1.50%');

  const missing = evaluateSingleInvariant(coverageRule, {});
  assert.equal(missing.passed, false);
  assert.equal(missing.actualValue, 'MISSING_UNMETERED');
});

test('evaluateSingleInvariant correctly validates <= ceiling constraints', () => {
  const latencyRule: InvariantRule = {
    id: 'INV-TEST-LAT',
    name: 'P99 Latency',
    metricKey: 'p99_latency_ms',
    operator: '<=',
    threshold: 100,
    unit: 'ms',
    description: 'Max latency test',
    applicableSurfaces: ['microservice_engine'],
    isHardGate: true,
  };

  const passing = evaluateSingleInvariant(latencyRule, { p99_latency_ms: 78 });
  assert.equal(passing.passed, true);

  const failing = evaluateSingleInvariant(latencyRule, { p99_latency_ms: 145 });
  assert.equal(failing.passed, false);
  assert.match(failing.deviation, /EXCEEDED/);
});

test('evaluateGate strictly intercepts and blocks circumvention attempts', () => {
  const bypassPayload: MetricPayload = {
    surface: 'git_commit_push',
    entityId: 'commit-sneaky-101',
    actor: 'rogue-dev@company.com',
    bypassFlagsDetected: ['--no-verify'],
    metrics: {
      coverage_percent: 95,
      cyclomatic_complexity_max: 8,
      critical_cve_count: 0,
      metric_signature_valid: true,
    },
  };

  const outcome = evaluateGate(bypassPayload, DEFAULT_INVARIANT_RULES);
  assert.equal(outcome.allowed, false);
  assert.equal(outcome.status, 'REJECTED_BLOCKED');
  assert.equal(outcome.isCircumventionAttempt, true);
  assert.ok(outcome.rejectionReasons.some((r) => r.includes('--no-verify')));
});

test('evaluateGate signs and issues push token for fully compliant payload', () => {
  const validPayload: MetricPayload = {
    surface: 'git_commit_push',
    entityId: 'commit-feat-auth-042',
    actor: 'lead-dev@company.com',
    metrics: {
      coverage_percent: 94.8,
      cyclomatic_complexity_max: 9,
      critical_cve_count: 0,
      metric_signature_valid: true,
      circumvention_flags_detected: 0,
    },
  };

  const outcome = evaluateGate(validPayload, DEFAULT_INVARIANT_RULES);
  assert.equal(outcome.allowed, true);
  assert.equal(outcome.status, 'RATIFIED_AND_SIGNED');
  assert.ok(outcome.signedPushToken?.startsWith('opt_token_v3_'));
  assert.ok(outcome.cryptographicSignature?.startsWith('ECDSA-P256-SHA256:'));
});

test('calculateMerkleRoot combines leaves into single deterministic root', () => {
  const leaves = [
    computeDeterministicHash('leaf-1'),
    computeDeterministicHash('leaf-2'),
    computeDeterministicHash('leaf-3'),
  ];

  const root = calculateMerkleRoot(leaves);
  assert.equal(root.length, 64);
  assert.equal(root, calculateMerkleRoot(leaves));
});

test('verifyMerkleChainIntegrity detects tampering', () => {
  const block0: MerkleLedgerBlock = {
    index: 0,
    timestamp: '2026-11-06T00:00:00Z',
    surface: 'git_commit_push',
    entityId: 'genesis-block',
    actor: 'system',
    blockHash: computeDeterministicHash('block0'),
    previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
    merkleRoot: computeDeterministicHash('root0'),
    status: 'RATIFIED_AND_SIGNED',
    signature: 'SIG_0',
    metricsSnapshot: {},
    violationCount: 0,
    attestationSummary: 'Genesis block',
  };

  const block1: MerkleLedgerBlock = {
    index: 1,
    timestamp: '2026-11-06T00:05:00Z',
    surface: 'microservice_engine',
    entityId: 'engine-payment-v1',
    actor: 'ci-runner',
    blockHash: computeDeterministicHash('block1'),
    previousHash: block0.blockHash,
    merkleRoot: computeDeterministicHash('root1'),
    status: 'RATIFIED_AND_SIGNED',
    signature: 'SIG_1',
    metricsSnapshot: {},
    violationCount: 0,
    attestationSummary: 'Payment engine deployment',
  };

  const validLedger = [block0, block1];
  const validCheck = verifyMerkleChainIntegrity(validLedger);
  assert.equal(validCheck.isValid, true);

  // Corrupt block1's previousHash
  const corruptedLedger = [
    block0,
    { ...block1, previousHash: 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef' },
  ];
  const corruptCheck = verifyMerkleChainIntegrity(corruptedLedger);
  assert.equal(corruptCheck.isValid, false);
  assert.equal(corruptCheck.brokenIndex, 1);
});

test('generateTimeSeriesTelemetry yields valid chronological telemetry points', () => {
  const points = generateTimeSeriesTelemetry();
  assert.equal(points.length, 16);
  assert.ok(points[0].ratified > 0);
  assert.ok(points.some((p: any) => p.circumventions > 0));
});

test('detectEstateAnomalies flags circumvention clusters and latency cliffs', () => {
  const points = generateTimeSeriesTelemetry();
  const anomalies = detectEstateAnomalies(points, []);
  assert.ok(anomalies.length >= 2);
  assert.ok(anomalies.some((a: any) => a.id === 'ANOM-BYPASS-CLUSTER'));
  assert.ok(anomalies.some((a: any) => a.id === 'ANOM-LATENCY-CLIFF'));
});

test('generateLatencyHeatmapData yields comprehensive 8-surface matrix with bottleneck clusters', () => {
  const heatmap = generateLatencyHeatmapData();
  // 8 surfaces * 12 time slices = 96 cells
  assert.equal(heatmap.length, 96);

  // Validate math invariants: p50 <= p95 <= p99
  for (const cell of heatmap) {
    assert.ok(cell.p50Ms <= cell.p95Ms, `p50 (${cell.p50Ms}) should be <= p95 (${cell.p95Ms})`);
    assert.ok(cell.p95Ms <= cell.p99Ms, `p95 (${cell.p95Ms}) should be <= p99 (${cell.p99Ms})`);
  }

  // Detect identified bottleneck clusters
  const bottleneckClusters = heatmap.filter((c) => c.isBottleneckCluster);
  assert.ok(bottleneckClusters.length > 0, 'Must identify bottleneck clusters');
  assert.ok(bottleneckClusters.some((c) => c.clusterSeverity === 'CRITICAL'));
  assert.ok(bottleneckClusters.every((c) => Boolean(c.bottleneckRootCause)));
});

test('generateDayZeroSecurityAlerts yields real-time baseline deviations with color-coded severity', () => {
  const alerts = generateDayZeroSecurityAlerts();
  assert.ok(alerts.length >= 6, 'Should generate multiple comprehensive security alerts');

  const severities = alerts.map((a) => a.severity);
  assert.ok(severities.includes('CRITICAL'), 'Must include CRITICAL severity alerts');
  assert.ok(severities.includes('HIGH'), 'Must include HIGH severity alerts');
  assert.ok(severities.includes('MEDIUM'), 'Must include MEDIUM severity alerts');
  assert.ok(severities.includes('LOW'), 'Must include LOW severity alerts');

  // Verify all alerts contain baseline, observed, threat vector, and mitigation
  for (const alert of alerts) {
    assert.ok(alert.id.startsWith('SEC-ALERT-'));
    assert.ok(alert.dayZeroBaselineMetric.length > 0);
    assert.ok(alert.realTimeObservedMetric.length > 0);
    assert.ok(alert.threatVector.length > 0);
    assert.ok(alert.mitigationEnforced.length > 0);
  }
});

test('syncLatencyCapsToRules generates surface-specific latency invariant rules', () => {
  const syncedRules = syncLatencyCapsToRules(DEFAULT_INVARIANT_RULES, DEFAULT_SURFACE_LATENCY_CAPS);
  const latencyRules = syncedRules.filter((r) => r.id.startsWith('INV-LAT-SURF-'));

  assert.equal(latencyRules.length, 8, 'Must generate exactly 8 surface-specific latency cap rules');

  const agentRule = latencyRules.find((r) => r.id === 'INV-LAT-SURF-autonomous_agent');
  assert.ok(agentRule);
  assert.equal(agentRule.threshold, 110);
  assert.equal(agentRule.operator, '<=');
  assert.equal(agentRule.isHardGate, true);
});

test('evaluateSurfaceLatencyViolation triggers automated violation when latency cap is exceeded', () => {
  const agentCap = DEFAULT_SURFACE_LATENCY_CAPS.autonomous_agent;

  // Passing test: 85ms <= 110ms cap
  const passing = evaluateSurfaceLatencyViolation('autonomous_agent', 85, agentCap);
  assert.equal(passing.isViolation, false);
  assert.equal(passing.severity, 'NOMINAL');

  // Failing test: 142ms > 110ms cap
  const violation = evaluateSurfaceLatencyViolation('autonomous_agent', 142, agentCap);
  assert.equal(violation.isViolation, true);
  assert.equal(violation.deviationMs, 32);
  assert.equal(violation.severity, 'CRITICAL');
  assert.ok(violation.enforcementAction.includes('HARD_KILL_SWITCH'));
});


