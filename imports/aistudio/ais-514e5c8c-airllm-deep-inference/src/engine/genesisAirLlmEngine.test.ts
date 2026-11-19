import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AIRLLM_MODEL_CATALOG,
  HOST_HARDWARE_PROFILES,
  STANDARD_WORKLOAD_REQUESTS,
  EVALUATION_BENCHMARK_TASKS,
  evaluateHardwareGuardrails,
  calculateCostPerVerifiedResult,
  routeWorkload,
  simulateEvaluationLaneRun
} from './genesisAirLlmEngine';

test('evaluateHardwareGuardrails blocks Qwen and Kimi 2.8T models on macOS Apple Silicon and enforces disk quotas', () => {
  const macHost = HOST_HARDWARE_PROFILES.find((h) => h.id === 'macos-m3-max-dev')!;
  const linuxWorker = HOST_HARDWARE_PROFILES.find((h) => h.id === 'genesis-linux-nvme-worker')!;

  const qwen8b = AIRLLM_MODEL_CATALOG.find((m) => m.id === 'qwen3-8b')!;
  const llama8b = AIRLLM_MODEL_CATALOG.find((m) => m.id === 'llama-3.1-8b-instruct')!;
  const kimi28t = AIRLLM_MODEL_CATALOG.find((m) => m.id === 'kimi-k3-2.8t')!;

  // Qwen3 ~8B on macOS should be blocked due to architecture restriction
  const qwenOnMac = evaluateHardwareGuardrails(qwen8b, macHost, 400);
  assert.equal(qwenOnMac.allowed, false);
  assert.equal(qwenOnMac.checks.osArchitectureCompatible, false);

  // Llama 3.1 8B on macOS should pass (Apple Silicon + Llama-style + 50GB total < 60GB quota)
  const llamaOnMac = evaluateHardwareGuardrails(llama8b, macHost, 400);
  assert.equal(llamaOnMac.allowed, true);
  assert.equal(llamaOnMac.checks.osArchitectureCompatible, true);
  assert.equal(llamaOnMac.checks.diskWithinQuota, true);

  // Kimi K3 2.8T on Linux Genesis Worker should be blocked by disk quota (4740 GB > 400 GB) and wall-clock time (292s/tok)
  const kimiOnLinux = evaluateHardwareGuardrails(kimi28t, linuxWorker, 600);
  assert.equal(kimiOnLinux.allowed, false);
  assert.equal(kimiOnLinux.checks.diskWithinQuota, false);
  assert.equal(kimiOnLinux.checks.wallClockWithinLimit, false);
});

test('calculateCostPerVerifiedResult accurately computes illustration from research assessment (£0.10 standard vs £0.20 AirLLM)', () => {
  // Research assessment section 4:
  // Standard: £2.00/hr, 3 minutes => £0.10 compute cost
  // AirLLM: £0.20/hr, 60 minutes => £0.20 compute cost
  const baselineComparison = calculateCostPerVerifiedResult({
    taskName: 'Architecture Review Baseline',
    runsPerBatch: 1,
    standardHourlyCostGbp: 2.0,
    standardExecutionMinutes: 3,
    standardVerifiedSuccessRate: 1.0,
    airllmHourlyCostGbp: 0.2,
    airllmExecutionMinutes: 60,
    airllmVerifiedSuccessRate: 1.0,
    airllmNvmeWearCostPerRunGbp: 0,
    useSunkOvernightCapacity: false,
    sunkElectricityOverheadPerHourGbp: 0.03
  });

  assert.equal(baselineComparison.standardComputeCostPerRunGbp, 0.1);
  assert.equal(baselineComparison.airllmComputeCostPerRunGbp, 0.2);
  assert.equal(baselineComparison.isAirllmEconomicallySuperior, false);

  // Now test sunk overnight capacity with higher verified resolution accuracy on complex clusters
  const overnightAdvantage = calculateCostPerVerifiedResult({
    taskName: 'Overnight Failure-to-Intelligence Escalation',
    runsPerBatch: 10,
    standardHourlyCostGbp: 2.0,
    standardExecutionMinutes: 5,
    standardVerifiedSuccessRate: 0.55,
    airllmHourlyCostGbp: 0.2,
    airllmExecutionMinutes: 45,
    airllmVerifiedSuccessRate: 0.9,
    airllmNvmeWearCostPerRunGbp: 0.01,
    useSunkOvernightCapacity: true,
    sunkElectricityOverheadPerHourGbp: 0.03
  });

  assert.equal(overnightAdvantage.isAirllmEconomicallySuperior, true);
  assert.ok(overnightAdvantage.airllmCostPerVerifiedResultGbp < overnightAdvantage.standardCostPerVerifiedResultGbp);
});

test('routeWorkload dispatches interactive coding to Fast API and overnight deep review to AirLLM with cross-family independence', () => {
  const linuxWorker = HOST_HARDWARE_PROFILES.find((h) => h.id === 'genesis-linux-nvme-worker')!;
  const interactiveCoding = STANDARD_WORKLOAD_REQUESTS.find((w) => w.id === 'wl-interactive-coding')!;
  const overnightArch = STANDARD_WORKLOAD_REQUESTS.find((w) => w.id === 'wl-overnight-arch')!;

  const interactiveRoute = routeWorkload(interactiveCoding, linuxWorker);
  assert.equal(interactiveRoute.selectedLane, 'external-api');

  const overnightRoute = routeWorkload(overnightArch, linuxWorker);
  assert.equal(overnightRoute.selectedLane, 'airllm-streamed');
  assert.equal(overnightRoute.epistemicIndependenceVerified, true);
  assert.notEqual(overnightRoute.selectedModelFamily, overnightArch.implementingAgentFamily);
});

test('simulateEvaluationLaneRun verifies 3-way comparison and 8 acceptance criteria on isolated Linux worker', () => {
  const linuxWorker = HOST_HARDWARE_PROFILES.find((h) => h.id === 'genesis-linux-nvme-worker')!;
  const llama70b = AIRLLM_MODEL_CATALOG.find((m) => m.id === 'llama-3.3-70b')!;
  const incidentTask = EVALUATION_BENCHMARK_TASKS[0];

  const report = simulateEvaluationLaneRun(incidentTask, linuxWorker, llama70b);
  assert.equal(report.lanes.length, 3);
  assert.equal(report.quotaValidation.allowed, true);
  assert.equal(report.shardCleanupVerified, true);
  assert.equal(report.overallRecommendation, 'ADOPT_FOR_OVERNIGHT_LANE');
  assert.ok(report.acceptanceCriteriaStatus.every((c) => c.passed));
});
