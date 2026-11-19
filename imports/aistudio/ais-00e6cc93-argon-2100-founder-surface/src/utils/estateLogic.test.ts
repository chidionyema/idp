import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateEstateHealth,
  evaluateParityRegressionGate,
  validateAsciiFirewall,
  executeFounderInterrogation,
  applyOperationalAction,
  SubsystemHealth,
  CapabilityInventoryItem,
  EstateState,
} from './estateLogic';

test('calculateEstateHealth calculates overall health and aggregates counts', () => {
  const subsystems: SubsystemHealth[] = [
    {
      id: 'sub-1',
      name: 'Spine Core',
      category: 'spine',
      status: 'nominal',
      latencyMs: 12,
      throughputPerSec: 1400,
      memoryUsageMb: 512,
      uptimePct: 99.99,
      greenlaneVerified: true,
    },
    {
      id: 'sub-2',
      name: 'Inference Mesh',
      category: 'compute',
      status: 'nominal',
      latencyMs: 18,
      throughputPerSec: 3200,
      memoryUsageMb: 2048,
      uptimePct: 99.95,
      greenlaneVerified: true,
    },
    {
      id: 'sub-3',
      name: 'Legion Worker',
      category: 'agents',
      status: 'recovering',
      latencyMs: 45,
      throughputPerSec: 200,
      memoryUsageMb: 800,
      uptimePct: 98.5,
      greenlaneVerified: false,
    },
  ];

  const result = calculateEstateHealth(subsystems);
  assert.equal(result.allNominal, false);
  assert.equal(result.degradedCount, 1);
  assert.equal(result.criticalCount, 0);
  assert.ok(result.overallHealthScore >= 90 && result.overallHealthScore <= 95);
  assert.equal(result.averageLatencyMs, 25);
});

test('evaluateParityRegressionGate validates 100% preservation across 2100 surface and deep views', () => {
  const inventory: CapabilityInventoryItem[] = [
    {
      id: 'cap-1',
      code: 'EST-RES-01',
      name: 'Continuous Checkpoint Weights',
      pillar: 'Research & ML',
      status: 'active',
      exposedIn2100Surface: true,
      deepSpecialistViewAvailable: true,
      dataSource: 'neural_spine',
      lastAuditTimestamp: '2026-11-07',
    },
    {
      id: 'cap-2',
      code: 'EST-FLEET-02',
      name: 'Legion Recovery Controller',
      pillar: 'Fleet Management',
      status: 'active',
      exposedIn2100Surface: true,
      deepSpecialistViewAvailable: true,
      dataSource: 'operational_store',
      lastAuditTimestamp: '2026-11-07',
    },
  ];

  const passResult = evaluateParityRegressionGate(inventory);
  assert.equal(passResult.passed, true);
  assert.equal(passResult.scorePct, 100);
  assert.equal(passResult.missingInSurface.length, 0);

  const flawedInventory: CapabilityInventoryItem[] = [
    ...inventory,
    {
      id: 'cap-3',
      code: 'EST-OMEGA-03',
      name: 'Omega Direct Override',
      pillar: 'Omega Control',
      status: 'active',
      exposedIn2100Surface: false,
      deepSpecialistViewAvailable: true,
      dataSource: 'live_telemetry',
      lastAuditTimestamp: '2026-11-07',
    },
  ];

  const failResult = evaluateParityRegressionGate(flawedInventory);
  assert.equal(failResult.passed, false);
  assert.equal(failResult.missingInSurface.length, 1);
});

test('validateAsciiFirewall catches non-ASCII characters that caused Legion trusted push failure', () => {
  const cleanSource = 'const founderGateway = "legion-recovery-v2";\nconsole.log(founderGateway);\n';
  const cleanResult = validateAsciiFirewall(cleanSource);
  assert.equal(cleanResult.valid, true);
  assert.equal(cleanResult.violations.length, 0);

  const corruptedSource = 'const title = "Estate Intelligence \u2014 Genesis Spine \u2013 Live";\n';
  const corruptedResult = validateAsciiFirewall(corruptedSource);
  assert.equal(corruptedResult.valid, false);
  assert.ok(corruptedResult.violations.length >= 2);
  assert.equal(corruptedResult.violations[0].line, 1);
});

test('executeFounderInterrogation answers Legion recovery inquiries specifically', () => {
  const mockState: EstateState = {
    healthScore: 94,
    activeAgents: 6,
    totalInferenceThroughput: 8420,
    greenlaneStatus: 'verified',
    parityGatePass: true,
    asciiFirewallViolations: 1,
    subsystems: [],
    capabilities: [],
    agents: [
      {
        id: 'agent-1',
        name: 'Legion Orchestrator',
        role: 'Gateway Deployment & Build',
        cluster: 'Orchestration-01',
        status: 'recovering',
        currentTask: 'Queued for Recovery Run #42412348112',
        concurrency: 8,
        yieldRatio: 0.94,
        lastRunId: '42412348112',
      },
    ],
    recentLogs: [],
    operationalParameters: {
      maxConcurrency: 16,
      inferenceTemperature: 0.2,
      transcriptFirewallStrictness: 'strict',
      trustedPushEncodingCheck: true,
      voiceConciergeSynthesis: true,
      spatialProjectionRateHz: 60,
    },
  };

  const response = executeFounderInterrogation('What happened with Legion recovery run #42412348112?', mockState);
  assert.equal(response.category, 'legion_recovery');
  assert.ok(response.synthesis.includes('42412348112'));
  assert.ok(response.synthesis.includes('non-ASCII'));
});

test('applyOperationalAction updates Legion recovery state and restores health', () => {
  const mockState: EstateState = {
    healthScore: 82,
    activeAgents: 5,
    totalInferenceThroughput: 5200,
    greenlaneStatus: 'warning',
    parityGatePass: true,
    asciiFirewallViolations: 1,
    subsystems: [
      {
        id: 'sub-legion',
        name: 'Legion Gateway',
        category: 'agents',
        status: 'recovering',
        latencyMs: 38,
        throughputPerSec: 400,
        memoryUsageMb: 850,
        uptimePct: 98.1,
        greenlaneVerified: false,
      },
    ],
    capabilities: [],
    agents: [
      {
        id: 'agent-1',
        name: 'Legion Orchestrator',
        role: 'Gateway Deployment',
        cluster: 'Orchestration-01',
        status: 'recovering',
        currentTask: 'Queued for run #42412348112',
        concurrency: 4,
        yieldRatio: 0.82,
      },
    ],
    recentLogs: [],
    operationalParameters: {
      maxConcurrency: 12,
      inferenceTemperature: 0.2,
      transcriptFirewallStrictness: 'strict',
      trustedPushEncodingCheck: true,
      voiceConciergeSynthesis: true,
      spatialProjectionRateHz: 60,
    },
  };

  const remediated = applyOperationalAction(mockState, { type: 'remediate_legion' });
  assert.equal(remediated.agents[0].status, 'active');
  assert.equal(remediated.asciiFirewallViolations, 0);
  assert.equal(remediated.recentLogs.length, 1);
  assert.equal(remediated.recentLogs[0].status, 'passed');
});
