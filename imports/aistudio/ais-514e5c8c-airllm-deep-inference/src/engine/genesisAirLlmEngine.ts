/**
 * Genesis Facility · AirLLM Deep Inference & Autonomous Estate Core Engine
 * Pure, deterministic domain logic for:
 * 1. AirLLM Streamed Inference vs Conventional Residency Models & Checkpoint Catalog
 * 2. Six IDP Strategic Opportunities & Asymmetric Leverage Scoring
 * 3. Dynamic Inference Router & Context Compiler Decision Layer (with Cross-Family Independence Gates)
 * 4. Cost-Per-Verified-Result Economics Model
 * 5. Hardware & Apple Silicon / NVMe Disk Quota Enforcer
 * 6. Deep Inference Evaluation Lane (3-Way Comparative Benchmark & 8 Production Acceptance Criteria)
 */

export type ArchitectureStyle = 'llama-style' | 'qwen-dense' | 'qwen-moe' | 'kimi-ultra-moe';
export type ModelFamily = 'llama-meta' | 'mistral-europe' | 'qwen-alibaba' | 'kimi-moonshot' | 'claude-external' | 'gemini-external';
export type HostProfileId = 'macos-m3-max-dev' | 'genesis-linux-nvme-worker' | 'sovereign-gpu-node';
export type ExecutionLaneId = 'deterministic' | 'fast-local' | 'airllm-streamed' | 'external-api' | 'policy-gate';

export interface AirLlmModelSpec {
  id: string;
  name: string;
  parameterCountLabel: string;
  parametersBillions: number;
  reportedVramGb: number;
  conventionalVramGb: number;
  rawCheckpointGb: number;
  shardedDiskFootprintGb: number;
  estimatedSecPerTokenNvme: number;
  architectureStyle: ArchitectureStyle;
  modelFamily: ModelFamily;
  macOsAppleSiliconSupported: boolean;
  supportsStreamedLora: boolean;
  recommendedTier: 'tier-1-pilot' | 'tier-2-overnight' | 'tier-3-extreme-demo';
  notes: string;
}

export interface HostHardwareProfile {
  id: HostProfileId;
  name: string;
  os: 'macos-apple-silicon' | 'linux-x86-nvme';
  availableVramGb: number;
  systemRamGb: number;
  freeDiskGb: number;
  enforcedDiskQuotaGb: number;
  nvmeReadBandwidthGbPerSec: number;
  maxWallClockMinutes: number;
  hourlyOperatingCostGbp: number;
  isSunkOvernightHardware: boolean;
  isolatedFromEstateServices: boolean;
}

export interface StrategicOpportunity {
  id: string;
  index: string;
  title: string;
  department: string;
  priority: 'Very high' | 'High' | 'Medium';
  fitSummary: string;
  description: string;
  asymmetricMechanism: string;
  guardrailRequirement: string;
  genesisFacilityModule: string;
  enabledInGenesis: boolean;
  targetMetricDelta: string;
}

export interface WorkloadRequest {
  id: string;
  name: string;
  department: string;
  category:
    | 'health-check'
    | 'triage-classification'
    | 'interactive-coding'
    | 'overnight-architecture-review'
    | 'scientific-model-comparison'
    | 'failure-to-intelligence'
    | 'independent-verification'
    | 'urgent-service-recovery'
    | 'critical-production-auth';
  maxLatencySeconds: number;
  isOvernightBatch: boolean;
  impactLevel: 'low' | 'medium' | 'high' | 'critical';
  implementingAgentFamily?: ModelFamily;
  requiresEpistemicIndependence: boolean;
  budgetCapGbp: number;
  estimatedOutputTokens: number;
}

export interface RoutingDecision {
  workloadId: string;
  selectedLane: ExecutionLaneId;
  selectedLaneLabel: string;
  selectedModelId: string;
  selectedModelFamily: ModelFamily;
  epistemicIndependenceVerified: boolean;
  epistemicIndependenceReason: string;
  estimatedDurationSeconds: number;
  estimatedCostGbp: number;
  rationale: string;
  fallbackLane: ExecutionLaneId;
}

export interface EconomicsScenarioInput {
  taskName: string;
  runsPerBatch: number;
  standardHourlyCostGbp: number;
  standardExecutionMinutes: number;
  standardVerifiedSuccessRate: number; // 0 to 1
  airllmHourlyCostGbp: number;
  airllmExecutionMinutes: number;
  airllmVerifiedSuccessRate: number; // 0 to 1
  airllmNvmeWearCostPerRunGbp: number;
  useSunkOvernightCapacity: boolean;
  sunkElectricityOverheadPerHourGbp: number;
}

export interface EconomicsComparisonResult {
  standardComputeCostPerRunGbp: number;
  standardTotalBatchCostGbp: number;
  standardVerifiedOutcomesCount: number;
  standardCostPerVerifiedResultGbp: number;
  airllmEffectiveHourlyRateGbp: number;
  airllmComputeCostPerRunGbp: number;
  airllmTotalCostPerRunGbp: number;
  airllmTotalBatchCostGbp: number;
  airllmVerifiedOutcomesCount: number;
  airllmCostPerVerifiedResultGbp: number;
  costDeltaPerVerifiedResultGbp: number;
  isAirllmEconomicallySuperior: boolean;
  breakEvenExecutionMinutes: number;
  verdictSummary: string;
}

export interface QuotaValidationResult {
  allowed: boolean;
  modelId: string;
  hostId: HostProfileId;
  totalRequiredDiskGb: number;
  projectedWallClockMinutes: number;
  checks: {
    osArchitectureCompatible: boolean;
    vramWithinLimit: boolean;
    diskWithinQuota: boolean;
    wallClockWithinLimit: boolean;
    workerIsolated: boolean;
  };
  blockingReasons: string[];
  cleanupPolicyCommand: string;
}

export interface EvaluationTaskBenchmark {
  id: string;
  title: string;
  incidentReference: string;
  department: string;
  complexity: 'High' | 'Critical';
  description: string;
  expectedRootCause: string;
  outputTokensRequired: number;
  implementingModelFamily: ModelFamily;
}

export interface LaneRunMetrics {
  laneId: 'fast-local' | 'airllm-streamed' | 'external-api';
  laneLabel: string;
  modelName: string;
  modelFamily: ModelFamily;
  epistemicIndependenceFromImplementer: boolean;
  latencySeconds: number;
  throughputTokensPerSec: number;
  vramPeakGb: number;
  diskShardPeakGb: number;
  executionCostGbp: number;
  verifiedCorrectnessScore: number; // 0 - 100
  passedDeterministicVerification: boolean;
  costPerVerifiedOutcomeGbp: number;
  reproducibleEvidenceHash: string;
  diagnosticFinding: string;
}

export interface EvaluationLaneExperimentReport {
  experimentId: string;
  timestampIso: string;
  task: EvaluationTaskBenchmark;
  hostProfile: HostHardwareProfile;
  airllmModel: AirLlmModelSpec;
  quotaValidation: QuotaValidationResult;
  lanes: LaneRunMetrics[];
  shardCleanupVerified: boolean;
  cancellationRecoveryProven: boolean;
  reclaimedDiskGb: number;
  acceptanceCriteriaStatus: {
    id: string;
    label: string;
    passed: boolean;
    evidenceNote: string;
  }[];
  overallRecommendation: 'ADOPT_FOR_OVERNIGHT_LANE' | 'HOLD_QUOTA_OR_ARCH_BLOCKED' | 'PREFER_FAST_BASELINE';
}

export const AIRLLM_MODEL_CATALOG: AirLlmModelSpec[] = [
  {
    id: 'llama-3.1-8b-instruct',
    name: 'Llama 3.1 8B Instruct (Pilot Baseline)',
    parameterCountLabel: '8B',
    parametersBillions: 8,
    reportedVramGb: 1.4,
    conventionalVramGb: 16.5,
    rawCheckpointGb: 16.0,
    shardedDiskFootprintGb: 34.0,
    estimatedSecPerTokenNvme: 0.35,
    architectureStyle: 'llama-style',
    modelFamily: 'llama-meta',
    macOsAppleSiliconSupported: true,
    supportsStreamedLora: true,
    recommendedTier: 'tier-1-pilot',
    notes: 'Ideal initial Deep Inference Evaluation Lane pilot; compatible with both Apple Silicon and Linux NVMe workers.'
  },
  {
    id: 'qwen3-8b',
    name: 'Qwen3 ~8B',
    parameterCountLabel: '~8B',
    parametersBillions: 8,
    reportedVramGb: 1.5,
    conventionalVramGb: 16.8,
    rawCheckpointGb: 16.2,
    shardedDiskFootprintGb: 35.0,
    estimatedSecPerTokenNvme: 0.38,
    architectureStyle: 'qwen-dense',
    modelFamily: 'qwen-alibaba',
    macOsAppleSiliconSupported: false,
    supportsStreamedLora: true,
    recommendedTier: 'tier-1-pilot',
    notes: 'Reported 1–2 GB VRAM in AirLLM benchmarks. Requires Linux CUDA worker; not supported on macOS Apple Silicon.'
  },
  {
    id: 'qwen3.8-27b',
    name: 'Qwen3.8-27B',
    parameterCountLabel: '27B',
    parametersBillions: 27,
    reportedVramGb: 3.33,
    conventionalVramGb: 56.0,
    rawCheckpointGb: 54.0,
    shardedDiskFootprintGb: 114.0,
    estimatedSecPerTokenNvme: 1.15,
    architectureStyle: 'qwen-dense',
    modelFamily: 'qwen-alibaba',
    macOsAppleSiliconSupported: false,
    supportsStreamedLora: true,
    recommendedTier: 'tier-1-pilot',
    notes: 'Practical 8B–32B sweet spot for Science Department laboratory evaluation on dedicated Linux NVMe workers.'
  },
  {
    id: 'llama-3.3-70b',
    name: 'Llama 3.3 70B',
    parameterCountLabel: '70B',
    parametersBillions: 70,
    reportedVramGb: 4.0,
    conventionalVramGb: 144.0,
    rawCheckpointGb: 140.0,
    shardedDiskFootprintGb: 295.0,
    estimatedSecPerTokenNvme: 2.85,
    architectureStyle: 'llama-style',
    modelFamily: 'llama-meta',
    macOsAppleSiliconSupported: true,
    supportsStreamedLora: true,
    recommendedTier: 'tier-2-overnight',
    notes: 'Reported ~4 GB GPU memory. Strong cross-family independent verification & overnight architectural review engine.'
  },
  {
    id: 'qwen3.8-flash-next',
    name: 'Qwen3.8-Flash-Next',
    parameterCountLabel: 'MoE Hybrid',
    parametersBillions: 80,
    reportedVramGb: 5.95,
    conventionalVramGb: 160.0,
    rawCheckpointGb: 155.0,
    shardedDiskFootprintGb: 320.0,
    estimatedSecPerTokenNvme: 1.9,
    architectureStyle: 'qwen-moe',
    modelFamily: 'qwen-alibaba',
    macOsAppleSiliconSupported: false,
    supportsStreamedLora: false,
    recommendedTier: 'tier-2-overnight',
    notes: 'Streams active experts selectively. Reported 5.95 GB VRAM working set.'
  },
  {
    id: 'qwen3-235b',
    name: 'Qwen3-235B MoE',
    parameterCountLabel: '235B',
    parametersBillions: 235,
    reportedVramGb: 3.1,
    conventionalVramGb: 480.0,
    rawCheckpointGb: 470.0,
    shardedDiskFootprintGb: 960.0,
    estimatedSecPerTokenNvme: 8.4,
    architectureStyle: 'qwen-moe',
    modelFamily: 'qwen-alibaba',
    macOsAppleSiliconSupported: false,
    supportsStreamedLora: false,
    recommendedTier: 'tier-2-overnight',
    notes: 'Reported ~3 GB VRAM via sparse expert streaming. Demands high-endurance NVMe storage quota (~1 TB).'
  },
  {
    id: 'kimi-k3-2.8t',
    name: 'Kimi K3 2.8T',
    parameterCountLabel: '2.8T',
    parametersBillions: 2800,
    reportedVramGb: 3.72,
    conventionalVramGb: 5600.0,
    rawCheckpointGb: 1560.0,
    shardedDiskFootprintGb: 3180.0,
    estimatedSecPerTokenNvme: 292.0,
    architectureStyle: 'kimi-ultra-moe',
    modelFamily: 'kimi-moonshot',
    macOsAppleSiliconSupported: false,
    supportsStreamedLora: false,
    recommendedTier: 'tier-3-extreme-demo',
    notes: 'Reported 3.72 GB VRAM at ~292s/token and ~1.56 TB checkpoint. Extreme memory demonstration; blocked by standard Genesis disk & wall-clock quotas.'
  }
];

export const HOST_HARDWARE_PROFILES: HostHardwareProfile[] = [
  {
    id: 'genesis-linux-nvme-worker',
    name: 'Genesis Isolated Worker · Linux PCIe 5.0 NVMe + RTX 4060 8GB',
    os: 'linux-x86-nvme',
    availableVramGb: 8.0,
    systemRamGb: 64.0,
    freeDiskGb: 1800.0,
    enforcedDiskQuotaGb: 500.0,
    nvmeReadBandwidthGbPerSec: 12.4,
    maxWallClockMinutes: 90,
    hourlyOperatingCostGbp: 0.2,
    isSunkOvernightHardware: true,
    isolatedFromEstateServices: true
  },
  {
    id: 'macos-m3-max-dev',
    name: 'Development MacBook Pro · Apple Silicon (Restricted Guardrail Mode)',
    os: 'macos-apple-silicon',
    availableVramGb: 12.0,
    systemRamGb: 36.0,
    freeDiskGb: 140.0,
    enforcedDiskQuotaGb: 60.0,
    nvmeReadBandwidthGbPerSec: 6.8,
    maxWallClockMinutes: 30,
    hourlyOperatingCostGbp: 0.08,
    isSunkOvernightHardware: true,
    isolatedFromEstateServices: false
  },
  {
    id: 'sovereign-gpu-node',
    name: 'Sovereign Estate Vault · Dual NVMe RAID-0 + 16GB Ada L40S Slice',
    os: 'linux-x86-nvme',
    availableVramGb: 16.0,
    systemRamGb: 128.0,
    freeDiskGb: 4000.0,
    enforcedDiskQuotaGb: 1200.0,
    nvmeReadBandwidthGbPerSec: 22.0,
    maxWallClockMinutes: 180,
    hourlyOperatingCostGbp: 0.35,
    isSunkOvernightHardware: false,
    isolatedFromEstateServices: true
  }
];

export const INITIAL_STRATEGIC_OPPORTUNITIES: StrategicOpportunity[] = [
  {
    id: 'opp-sovereign-inference',
    index: '01',
    title: 'Sovereign Inference Infrastructure',
    department: 'Core Platform & Resilience',
    priority: 'High',
    fitSummary: 'Best for asynchronous workloads · Model-provider independence',
    description:
      'Operates an additional inference lane on hardware IDP directly controls without requiring a multi-GPU cluster, insulating critical asynchronous pipelines from external API outages or rate-limit shocks.',
    asymmetricMechanism:
      'Converts spare single-GPU nodes with fast NVMe arrays into high-capacity fallback reasoning engines when external APIs degrade.',
    guardrailRequirement: 'Route strictly asynchronous/non-interactive queues; enforce wall-clock timeouts.',
    genesisFacilityModule: 'Sovereign Asynchronous Queue Escalator',
    enabledInGenesis: true,
    targetMetricDelta: '100% API outage survivability for batch pipelines'
  },
  {
    id: 'opp-science-lab',
    index: '02',
    title: 'Science Department Model Laboratory',
    department: 'Science Department',
    priority: 'Very high',
    fitSummary: 'Strong research fit · Open-weight evaluation & streamed LoRA',
    description:
      'Evaluates 27B–235B open-weight models and runs AirLLM 4 streamed LoRA training experiments on modest GPU hardware to test reasoning, failure diagnosis, and epistemic self-correction before committing to cluster rentals.',
    asymmetricMechanism:
      'Decouples hypothesis testing on frontier open weights from expensive multi-A100 hourly reservations.',
    guardrailRequirement: 'Mandatory pre-flight disk shard budget registration and post-run shard purge.',
    genesisFacilityModule: 'Deep Inference Evaluation Lane & LoRA Bench',
    enabledInGenesis: true,
    targetMetricDelta: '-78% exploratory GPU rental expenditure'
  },
  {
    id: 'opp-independent-verification',
    index: '03',
    title: 'Independent Verification Agents',
    department: 'Verification & Safety',
    priority: 'High',
    fitSummary: 'Non-urgent deep verification · Cross-family decorrelation',
    description:
      'Reviews an implementing agent’s proposed code changes, test evidence, incident hypotheses, and architectural decisions using a distinct model family to reduce correlated blind spots.',
    asymmetricMechanism:
      'Enforces measured epistemic independence: if a Claude/Gemini agent authored the patch, a local Llama-70B or Qwen-27B verifier audits the causal chain.',
    guardrailRequirement: 'Router blocks same-family verification and tracks empirical error decorrelation.',
    genesisFacilityModule: 'Cross-Family Epistemic Auditor Gate',
    enabledInGenesis: true,
    targetMetricDelta: '-42% correlated verification escapes on high-impact PRs'
  },
  {
    id: 'opp-architectural-intelligence',
    index: '04',
    title: 'Estate-Wide Architectural Intelligence',
    department: 'Architecture & Governance',
    priority: 'High',
    fitSummary: 'Latency-tolerant · Scheduled overnight batch sweeps',
    description:
      'Executes scheduled overnight investigations into cross-repo dependency drift, duplicated capabilities, boundary violations, and unresolved failure patterns.',
    asymmetricMechanism:
      'Exploits zero-marginal-cost idle overnight compute cycles where 45–60 minute execution times carry zero human waiting cost.',
    guardrailRequirement: 'Scheduled strictly during off-peak window (01:00–05:30 UTC) with automatic preemption.',
    genesisFacilityModule: 'Nocturnal Architectural Drift Scanner',
    enabledInGenesis: true,
    targetMetricDelta: 'Zero human latency cost · Full-estate nightly synthesis'
  },
  {
    id: 'opp-failure-to-intelligence',
    index: '05',
    title: 'Failure-to-Intelligence Pipeline',
    department: 'Reliability & Epistemics',
    priority: 'Very high',
    fitSummary: 'Directly aligned with IDP objectives · Root-cause escalation',
    description:
      'Examines recurring failure clusters, generates alternative causal hypotheses, and proposes class-wide deterministic remedies and invariants that complement existing unit/integration suites.',
    asymmetricMechanism:
      'Turns single production anomalies into permanent class-wide regression tests via deep multi-hour offline reasoning.',
    guardrailRequirement: 'Every proposed remedy must compile into a deterministic test artifact before acceptance.',
    genesisFacilityModule: 'Causal Cluster Escalation Synthesizer',
    enabledInGenesis: true,
    targetMetricDelta: '3.4x recurring incident elimination per verified remedy'
  },
  {
    id: 'opp-model-adaptation',
    index: '06',
    title: 'Estate-Specific Model Adaptation',
    department: 'Science & Training',
    priority: 'Medium',
    fitSummary: 'Streamed LoRA · Evidence-backed trace curation',
    description:
      'Trains compact LoRA adapters using AirLLM 4 streamed backpropagation strictly on verified execution traces and held-out deterministic tests rather than raw agent narratives.',
    asymmetricMechanism:
      'Prevents epistemic inbreeding (learning agent misconceptions) by gating training samples on objective test pass proofs.',
    guardrailRequirement: 'Rejects unverified narrative transcripts; requires held-out deterministic benchmark lift.',
    genesisFacilityModule: 'Verified-Trace Streamed LoRA Trainer',
    enabledInGenesis: false,
    targetMetricDelta: '+19% domain remediation accuracy on held-out incidents'
  }
];

export const STANDARD_WORKLOAD_REQUESTS: WorkloadRequest[] = [
  {
    id: 'wl-health-check',
    name: 'Estate Service Health Checks & SLO Alerts',
    department: 'Core Platform',
    category: 'health-check',
    maxLatencySeconds: 1,
    isOvernightBatch: false,
    impactLevel: 'low',
    requiresEpistemicIndependence: false,
    budgetCapGbp: 0.001,
    estimatedOutputTokens: 50
  },
  {
    id: 'wl-triage',
    name: 'Log Anomaly Classification & Incident Triage',
    department: 'Operations Supervisor',
    category: 'triage-classification',
    maxLatencySeconds: 5,
    isOvernightBatch: false,
    impactLevel: 'low',
    requiresEpistemicIndependence: false,
    budgetCapGbp: 0.01,
    estimatedOutputTokens: 180
  },
  {
    id: 'wl-interactive-coding',
    name: 'Interactive Feature Implementation & Refactoring',
    department: 'Engineering Agents',
    category: 'interactive-coding',
    maxLatencySeconds: 25,
    isOvernightBatch: false,
    impactLevel: 'medium',
    implementingAgentFamily: 'gemini-external',
    requiresEpistemicIndependence: false,
    budgetCapGbp: 0.15,
    estimatedOutputTokens: 1200
  },
  {
    id: 'wl-overnight-arch',
    name: 'Overnight Deep Architecture & Dependency Drift Review',
    department: 'Architecture & Governance',
    category: 'overnight-architecture-review',
    maxLatencySeconds: 3600,
    isOvernightBatch: true,
    impactLevel: 'high',
    implementingAgentFamily: 'gemini-external',
    requiresEpistemicIndependence: true,
    budgetCapGbp: 0.25,
    estimatedOutputTokens: 850
  },
  {
    id: 'wl-failure-intelligence',
    name: 'Failure-to-Intelligence Causal Cluster Escalation',
    department: 'Reliability & Science',
    category: 'failure-to-intelligence',
    maxLatencySeconds: 5400,
    isOvernightBatch: true,
    impactLevel: 'high',
    implementingAgentFamily: 'claude-external',
    requiresEpistemicIndependence: true,
    budgetCapGbp: 0.35,
    estimatedOutputTokens: 950
  },
  {
    id: 'wl-science-comparison',
    name: 'Science Lab Cross-Model Epistemic Evaluation',
    department: 'Science Department',
    category: 'scientific-model-comparison',
    maxLatencySeconds: 4800,
    isOvernightBatch: true,
    impactLevel: 'medium',
    implementingAgentFamily: 'llama-meta',
    requiresEpistemicIndependence: true,
    budgetCapGbp: 0.3,
    estimatedOutputTokens: 700
  },
  {
    id: 'wl-urgent-recovery',
    name: 'Urgent Production Service Degradation Recovery',
    department: 'Incident Response',
    category: 'urgent-service-recovery',
    maxLatencySeconds: 12,
    isOvernightBatch: false,
    impactLevel: 'critical',
    implementingAgentFamily: 'gemini-external',
    requiresEpistemicIndependence: false,
    budgetCapGbp: 0.5,
    estimatedOutputTokens: 600
  },
  {
    id: 'wl-critical-auth',
    name: 'Critical Production Release Authorisation Gate',
    department: 'Verification & Governance',
    category: 'critical-production-auth',
    maxLatencySeconds: 1800,
    isOvernightBatch: false,
    impactLevel: 'critical',
    implementingAgentFamily: 'gemini-external',
    requiresEpistemicIndependence: true,
    budgetCapGbp: 0.4,
    estimatedOutputTokens: 650
  }
];

export const EVALUATION_BENCHMARK_TASKS: EvaluationTaskBenchmark[] = [
  {
    id: 'eval-inc-409',
    title: 'INC-409 · Distributed Lock Starvation Under Retry Storm',
    incidentReference: 'IDP-INC-2026-409',
    department: 'Failure-to-Intelligence Pipeline',
    complexity: 'Critical',
    description:
      'Three supervisor workers entered livelock during transient Redis lease expiry. Standard fast triage patched the timeout constant, masking the non-idempotent fencing token progression.',
    expectedRootCause:
      'Missing monotonic fencing token validation on storage write path combined with synchronized exponential backoff jitter omission.',
    outputTokensRequired: 620,
    implementingModelFamily: 'gemini-external'
  },
  {
    id: 'eval-arch-112',
    title: 'ARCH-112 · Cross-Department Schema & Capability Duplication',
    incidentReference: 'IDP-ARCH-2026-112',
    department: 'Estate-Wide Architectural Intelligence',
    complexity: 'High',
    description:
      'Audit 14 autonomous microservice manifests to detect divergent telemetry envelope parsers and hidden circular state transitions between Science and Operations supervisors.',
    expectedRootCause:
      'Cyclic event emission between Supervisor-Retry-Queue and Telemetry-Normalizer when dead-letter payloads exceed 64 KB.',
    outputTokensRequired: 780,
    implementingModelFamily: 'claude-external'
  },
  {
    id: 'eval-ver-884',
    title: 'VER-884 · Independent Verification of Migration Rollback Patch',
    incidentReference: 'IDP-VER-2026-884',
    department: 'Independent Verification Agents',
    complexity: 'Critical',
    description:
      'Verify whether a proposed zero-downtime column drop migration preserves backward compatibility if a canary worker crashes mid-transaction.',
    expectedRootCause:
      'Dual-write trigger drops NOT NULL constraint too late in phase 2, causing old read replicas to reject rollback writes.',
    outputTokensRequired: 540,
    implementingModelFamily: 'qwen-alibaba'
  }
];

/**
 * Pure Hardware & Quota Guardrail Evaluator
 * Enforces macOS Apple Silicon architecture limits, VRAM ceilings, disk shard budgets, and wall-clock caps.
 */
export function evaluateHardwareGuardrails(
  model: AirLlmModelSpec,
  host: HostHardwareProfile,
  outputTokensToGenerate: number = 600
): QuotaValidationResult {
  const blockingReasons: string[] = [];

  // 1. OS & Architecture Check (macOS supports only Apple Silicon + Llama/Mistral architectures)
  const osArchitectureCompatible =
    host.os === 'linux-x86-nvme' || (host.os === 'macos-apple-silicon' && model.macOsAppleSiliconSupported);

  if (!osArchitectureCompatible) {
    blockingReasons.push(
      `Architecture '${model.architectureStyle}' (${model.name}) is unsupported on ${host.name}. macOS support is strictly limited to Apple Silicon with Llama/Mistral architectures.`
    );
  }

  // 2. VRAM Working Set Check
  const vramWithinLimit = model.reportedVramGb <= host.availableVramGb;
  if (!vramWithinLimit) {
    blockingReasons.push(
      `Model working set (${model.reportedVramGb.toFixed(2)} GB VRAM) exceeds host GPU limit (${host.availableVramGb.toFixed(1)} GB).`
    );
  }

  // 3. Disk Budget & Shard Footprint Check (raw checkpoint + converted layer shards)
  const totalRequiredDiskGb = Number((model.rawCheckpointGb + model.shardedDiskFootprintGb).toFixed(1));
  const diskWithinQuota =
    totalRequiredDiskGb <= host.enforcedDiskQuotaGb && totalRequiredDiskGb <= host.freeDiskGb;

  if (!diskWithinQuota) {
    blockingReasons.push(
      `Total checkpoint + layer-shard footprint (${totalRequiredDiskGb} GB) exceeds enforced Genesis disk quota (${host.enforcedDiskQuotaGb} GB) or free storage (${host.freeDiskGb} GB).`
    );
  }

  // 4. Wall-Clock Execution Time Limit Check
  // Adjust token latency proportionally to host NVMe bandwidth relative to baseline 12.4 GB/s
  const bandwidthFactor = 12.4 / Math.max(1, host.nvmeReadBandwidthGbPerSec);
  const effectiveSecPerToken = model.estimatedSecPerTokenNvme * bandwidthFactor;
  const projectedWallClockMinutes = Number(((effectiveSecPerToken * outputTokensToGenerate) / 60).toFixed(1));
  const wallClockWithinLimit = projectedWallClockMinutes <= host.maxWallClockMinutes;

  if (!wallClockWithinLimit) {
    blockingReasons.push(
      `Projected runtime (${projectedWallClockMinutes} min for ${outputTokensToGenerate} tokens at ${effectiveSecPerToken.toFixed(2)}s/tok) exceeds worker wall-clock limit (${host.maxWallClockMinutes} min).`
    );
  }

  // 5. Worker Isolation Check (production evaluation lane requires isolated worker)
  const workerIsolated = host.isolatedFromEstateServices;
  if (!workerIsolated && model.parametersBillions > 10) {
    blockingReasons.push(
      `Host '${host.name}' is not isolated from interactive estate services; models >10B (${model.parameterCountLabel}) are blocked to prevent disk/system-load thrashing.`
    );
  }

  const allowed =
    osArchitectureCompatible &&
    vramWithinLimit &&
    diskWithinQuota &&
    wallClockWithinLimit &&
    (workerIsolated || model.parametersBillions <= 10);

  return {
    allowed,
    modelId: model.id,
    hostId: host.id,
    totalRequiredDiskGb,
    projectedWallClockMinutes,
    checks: {
      osArchitectureCompatible,
      vramWithinLimit,
      diskWithinQuota,
      wallClockWithinLimit,
      workerIsolated
    },
    blockingReasons,
    cleanupPolicyCommand: `genesis-ctl shards purge --model=${model.id} --verify-hash --reclaim-gb=${totalRequiredDiskGb}`
  };
}

/**
 * Pure Cost-Per-Verified-Result Calculator
 * Implements: Cost per verified result = Total execution cost / Verified successful outcomes
 */
export function calculateCostPerVerifiedResult(
  input: EconomicsScenarioInput
): EconomicsComparisonResult {
  const safeRuns = Math.max(1, input.runsPerBatch);
  const standardHoursPerRun = input.standardExecutionMinutes / 60;
  const standardComputeCostPerRunGbp = standardHoursPerRun * input.standardHourlyCostGbp;
  const standardTotalBatchCostGbp = standardComputeCostPerRunGbp * safeRuns;
  const standardVerifiedOutcomesCount = Math.max(0.01, safeRuns * input.standardVerifiedSuccessRate);
  const standardCostPerVerifiedResultGbp = standardTotalBatchCostGbp / standardVerifiedOutcomesCount;

  const airllmEffectiveHourlyRateGbp = input.useSunkOvernightCapacity
    ? input.sunkElectricityOverheadPerHourGbp
    : input.airllmHourlyCostGbp;

  const airllmHoursPerRun = input.airllmExecutionMinutes / 60;
  const airllmComputeCostPerRunGbp = airllmHoursPerRun * airllmEffectiveHourlyRateGbp;
  const airllmTotalCostPerRunGbp = airllmComputeCostPerRunGbp + input.airllmNvmeWearCostPerRunGbp;
  const airllmTotalBatchCostGbp = airllmTotalCostPerRunGbp * safeRuns;
  const airllmVerifiedOutcomesCount = Math.max(0.01, safeRuns * input.airllmVerifiedSuccessRate);
  const airllmCostPerVerifiedResultGbp = airllmTotalBatchCostGbp / airllmVerifiedOutcomesCount;

  const costDeltaPerVerifiedResultGbp =
    airllmCostPerVerifiedResultGbp - standardCostPerVerifiedResultGbp;
  const isAirllmEconomicallySuperior =
    airllmCostPerVerifiedResultGbp < standardCostPerVerifiedResultGbp;

  // Break-even AirLLM execution minutes where AirLLM cost/verified equals Standard cost/verified
  const targetAirllmCostPerRun =
    standardCostPerVerifiedResultGbp * input.airllmVerifiedSuccessRate -
    input.airllmNvmeWearCostPerRunGbp;
  const breakEvenExecutionMinutes =
    airllmEffectiveHourlyRateGbp > 0
      ? Math.max(0, Number(((targetAirllmCostPerRun / airllmEffectiveHourlyRateGbp) * 60).toFixed(1)))
      : 999;

  let verdictSummary = '';
  if (isAirllmEconomicallySuperior) {
    const savingsPct = Math.round(
      ((standardCostPerVerifiedResultGbp - airllmCostPerVerifiedResultGbp) /
        standardCostPerVerifiedResultGbp) *
        100
    );
    verdictSummary = `AirLLM delivers ${savingsPct}% lower cost per verified result (£${airllmCostPerVerifiedResultGbp.toFixed(3)} vs £${standardCostPerVerifiedResultGbp.toFixed(3)}) by combining ${input.useSunkOvernightCapacity ? 'sunk overnight capacity' : 'low-VRAM worker rates'} with a ${(input.airllmVerifiedSuccessRate * 100).toFixed(0)}% verified resolution rate.`;
  } else {
    const premiumPct = Math.round(
      ((airllmCostPerVerifiedResultGbp - standardCostPerVerifiedResultGbp) /
        standardCostPerVerifiedResultGbp) *
        100
    );
    verdictSummary = `Standard inference is ${premiumPct}% more economical per verified result (£${standardCostPerVerifiedResultGbp.toFixed(3)} vs £${airllmCostPerVerifiedResultGbp.toFixed(3)}). Streamed execution time (${input.airllmExecutionMinutes}m) outweighs the lower hourly GPU rate unless run on spare overnight hardware or yielding higher verification accuracy.`;
  }

  return {
    standardComputeCostPerRunGbp: Number(standardComputeCostPerRunGbp.toFixed(4)),
    standardTotalBatchCostGbp: Number(standardTotalBatchCostGbp.toFixed(2)),
    standardVerifiedOutcomesCount: Number(standardVerifiedOutcomesCount.toFixed(2)),
    standardCostPerVerifiedResultGbp: Number(standardCostPerVerifiedResultGbp.toFixed(4)),
    airllmEffectiveHourlyRateGbp: Number(airllmEffectiveHourlyRateGbp.toFixed(4)),
    airllmComputeCostPerRunGbp: Number(airllmComputeCostPerRunGbp.toFixed(4)),
    airllmTotalCostPerRunGbp: Number(airllmTotalCostPerRunGbp.toFixed(4)),
    airllmTotalBatchCostGbp: Number(airllmTotalBatchCostGbp.toFixed(2)),
    airllmVerifiedOutcomesCount: Number(airllmVerifiedOutcomesCount.toFixed(2)),
    airllmCostPerVerifiedResultGbp: Number(airllmCostPerVerifiedResultGbp.toFixed(4)),
    costDeltaPerVerifiedResultGbp: Number(costDeltaPerVerifiedResultGbp.toFixed(4)),
    isAirllmEconomicallySuperior,
    breakEvenExecutionMinutes,
    verdictSummary
  };
}

/**
 * Dynamic Inference Router & Context Compiler Decision Layer
 * Selects the optimal execution lane based on workload SLOs, batch tolerance, hardware guardrails,
 * and cross-family epistemic independence requirements.
 */
export function routeWorkload(
  workload: WorkloadRequest,
  host: HostHardwareProfile
): RoutingDecision {
  // 1. Deterministic health checks -> Deterministic code
  if (workload.category === 'health-check') {
    return {
      workloadId: workload.id,
      selectedLane: 'deterministic',
      selectedLaneLabel: 'Deterministic Code & Invariant Probes',
      selectedModelId: 'deterministic-runtime-verifier',
      selectedModelFamily: 'llama-meta',
      epistemicIndependenceVerified: true,
      epistemicIndependenceReason: 'Deterministic state assertion (zero stochastic model correlation).',
      estimatedDurationSeconds: 0.15,
      estimatedCostGbp: 0.0001,
      rationale: 'Health checks and SLO probes must execute deterministically without LLM latency or cost.',
      fallbackLane: 'fast-local'
    };
  }

  // 2. Simple classification & triage -> Fast local small quantised model
  if (workload.category === 'triage-classification') {
    return {
      workloadId: workload.id,
      selectedLane: 'fast-local',
      selectedLaneLabel: 'Fast Local Quantised Model (Resident VRAM)',
      selectedModelId: 'llama-3.1-8b-q4-resident',
      selectedModelFamily: 'llama-meta',
      epistemicIndependenceVerified: true,
      epistemicIndependenceReason: 'Low-impact triage routed to resident 8B local classifier.',
      estimatedDurationSeconds: 1.8,
      estimatedCostGbp: 0.0008,
      rationale: 'Sub-5s latency SLO satisfied by resident 4-bit local 8B model without weight streaming overhead.',
      fallbackLane: 'external-api'
    };
  }

  // 3. Interactive coding or urgent service recovery -> Fast capable model / External API
  if (
    workload.category === 'interactive-coding' ||
    workload.category === 'urgent-service-recovery' ||
    workload.maxLatencySeconds < 120
  ) {
    return {
      workloadId: workload.id,
      selectedLane: 'external-api',
      selectedLaneLabel: 'Fast Capable Model / External API Lane',
      selectedModelId: 'frontier-fast-api',
      selectedModelFamily: 'gemini-external',
      epistemicIndependenceVerified: !workload.requiresEpistemicIndependence,
      epistemicIndependenceReason:
        workload.category === 'urgent-service-recovery'
          ? 'Fast recovery prioritized; post-incident verification escalated to AirLLM offline lane.'
          : 'Interactive latency SLO (<30s) precludes streamed weight transfer.',
      estimatedDurationSeconds: 8.5,
      estimatedCostGbp: 0.095,
      rationale:
        'AirLLM streamed inference is unsuitable for interactive coding or urgent recovery due to PCIe/NVMe layer transfer latency.',
      fallbackLane: 'fast-local'
    };
  }

  // 4. Critical production authorisation -> Policy Gate + Independent Cross-Family Evidence
  if (workload.category === 'critical-production-auth') {
    const candidateModels = AIRLLM_MODEL_CATALOG.filter(
      (m) =>
        m.modelFamily !== workload.implementingAgentFamily &&
        evaluateHardwareGuardrails(m, host, workload.estimatedOutputTokens).allowed
    );
    const chosen = candidateModels[0] ?? AIRLLM_MODEL_CATALOG[0];
    return {
      workloadId: workload.id,
      selectedLane: 'policy-gate',
      selectedLaneLabel: 'Independent Policy Gate + Cross-Family Verifier',
      selectedModelId: chosen.id,
      selectedModelFamily: chosen.modelFamily,
      epistemicIndependenceVerified: chosen.modelFamily !== workload.implementingAgentFamily,
      epistemicIndependenceReason: `Implementing family (${workload.implementingAgentFamily ?? 'none'}) audited by independent family (${chosen.modelFamily}) + deterministic policy gate.`,
      estimatedDurationSeconds: Number((chosen.estimatedSecPerTokenNvme * workload.estimatedOutputTokens).toFixed(0)),
      estimatedCostGbp: 0.065,
      rationale:
        'High-impact production release combines deterministic policy invariants with an independent model family audit.',
      fallbackLane: 'external-api'
    };
  }

  // 5. Latency-tolerant / Overnight batch / Science Lab / Failure-to-Intelligence -> AirLLM Candidate
  // Select largest compatible AirLLM model from a DIFFERENT family than implementingAgentFamily
  const compatibleAirLlmModels = AIRLLM_MODEL_CATALOG.filter((m) => {
    const quota = evaluateHardwareGuardrails(m, host, workload.estimatedOutputTokens);
    const familyIndependent =
      !workload.requiresEpistemicIndependence || m.modelFamily !== workload.implementingAgentFamily;
    return quota.allowed && familyIndependent;
  }).sort((a, b) => b.parametersBillions - a.parametersBillions);

  if (compatibleAirLlmModels.length > 0) {
    const selected = compatibleAirLlmModels[0];
    const durationSec = Number(
      (selected.estimatedSecPerTokenNvme * workload.estimatedOutputTokens * (12.4 / host.nvmeReadBandwidthGbPerSec)).toFixed(0)
    );
    const hours = durationSec / 3600;
    const costGbp = Number(((hours * host.hourlyOperatingCostGbp) + 0.015).toFixed(4));

    return {
      workloadId: workload.id,
      selectedLane: 'airllm-streamed',
      selectedLaneLabel: 'AirLLM Deep Streamed Inference Lane',
      selectedModelId: selected.id,
      selectedModelFamily: selected.modelFamily,
      epistemicIndependenceVerified: selected.modelFamily !== workload.implementingAgentFamily,
      epistemicIndependenceReason: `Cross-family audit enforced: ${selected.modelFamily} verifies ${workload.implementingAgentFamily ?? 'autonomous-agent'} output.`,
      estimatedDurationSeconds: durationSec,
      estimatedCostGbp: costGbp,
      rationale: `Selected ${selected.name} (${selected.reportedVramGb} GB VRAM working set) on ${host.name}. Latency-tolerant workload captures deep reasoning without GPU cluster rental.`,
      fallbackLane: 'external-api'
    };
  }

  // Fallback if host guardrails block all large models (e.g., restricted MacBook with Llama implementer)
  return {
    workloadId: workload.id,
    selectedLane: 'external-api',
    selectedLaneLabel: 'External API Baseline (Host Quota Fallback)',
    selectedModelId: 'claude-external-verifier',
    selectedModelFamily: 'claude-external',
    epistemicIndependenceVerified: workload.implementingAgentFamily !== 'claude-external',
    epistemicIndependenceReason: 'Host hardware guardrails blocked local streamed model; routed to cross-family external API.',
    estimatedDurationSeconds: 18,
    estimatedCostGbp: 0.14,
    rationale: `Host '${host.name}' guardrails blocked streamed models for this workload; safely escalated to External API baseline.`,
    fallbackLane: 'fast-local'
  };
}

/**
 * Simulates the First Experiment: Deep Inference Evaluation Lane
 * Compares Fast Local Quantised Model vs AirLLM Streamed Model vs External API Baseline
 * on real IDP incidents and checks all 8 acceptance criteria.
 */
export function simulateEvaluationLaneRun(
  task: EvaluationTaskBenchmark,
  host: HostHardwareProfile,
  airllmModel: AirLlmModelSpec
): EvaluationLaneExperimentReport {
  const quotaValidation = evaluateHardwareGuardrails(
    airllmModel,
    host,
    task.outputTokensRequired
  );

  // 1. Fast Local Quantised Baseline (8B Q4 resident in VRAM)
  const fastLocalLatencySec = Number((task.outputTokensRequired * 0.022).toFixed(1));
  const fastLocalScore = task.complexity === 'Critical' ? 61 : 72;
  const fastLocalPassed = fastLocalScore >= 80;
  const fastLocalCost = 0.004;

  // 2. AirLLM Streamed Model Candidate
  const bandwidthFactor = 12.4 / Math.max(1, host.nvmeReadBandwidthGbPerSec);
  const airllmLatencySec = Number(
    (task.outputTokensRequired * airllmModel.estimatedSecPerTokenNvme * bandwidthFactor).toFixed(1)
  );
  const airllmThroughput = Number((task.outputTokensRequired / Math.max(1, airllmLatencySec)).toFixed(2));
  const airllmScore =
    airllmModel.parametersBillions >= 70
      ? 94
      : airllmModel.parametersBillions >= 27
      ? 89
      : 76;
  const airllmEpistemicIndependent = airllmModel.modelFamily !== task.implementingModelFamily;
  const airllmPassed = quotaValidation.allowed && airllmScore >= 82 && airllmEpistemicIndependent;
  const airllmHours = airllmLatencySec / 3600;
  const airllmCost = Number(((airllmHours * host.hourlyOperatingCostGbp) + 0.012).toFixed(4));

  // 3. External Premium API Baseline
  const externalApiLatencySec = Number((task.outputTokensRequired * 0.035).toFixed(1));
  const externalApiScore = 92;
  const externalApiIndependent = 'claude-external' !== task.implementingModelFamily;
  const externalApiCost = 0.165;

  const lanes: LaneRunMetrics[] = [
    {
      laneId: 'fast-local',
      laneLabel: 'Fast Local Quantised (8B Q4 Resident)',
      modelName: 'Llama-3.1-8B-Q4_K_M',
      modelFamily: 'llama-meta',
      epistemicIndependenceFromImplementer: 'llama-meta' !== task.implementingModelFamily,
      latencySeconds: fastLocalLatencySec,
      throughputTokensPerSec: Number((task.outputTokensRequired / fastLocalLatencySec).toFixed(1)),
      vramPeakGb: 5.2,
      diskShardPeakGb: 4.8,
      executionCostGbp: fastLocalCost,
      verifiedCorrectnessScore: fastLocalScore,
      passedDeterministicVerification: fastLocalPassed,
      costPerVerifiedOutcomeGbp: fastLocalPassed ? fastLocalCost : Number((fastLocalCost / 0.35).toFixed(4)),
      reproducibleEvidenceHash: `sha256:fast-${task.id}-7a19c`,
      diagnosticFinding:
        'Identified surface timeout symptom but missed deeper multi-service state invariant violation.'
    },
    {
      laneId: 'airllm-streamed',
      laneLabel: `AirLLM Streamed (${airllmModel.name})`,
      modelName: airllmModel.name,
      modelFamily: airllmModel.modelFamily,
      epistemicIndependenceFromImplementer: airllmEpistemicIndependent,
      latencySeconds: airllmLatencySec,
      throughputTokensPerSec: airllmThroughput,
      vramPeakGb: airllmModel.reportedVramGb,
      diskShardPeakGb: quotaValidation.totalRequiredDiskGb,
      executionCostGbp: airllmCost,
      verifiedCorrectnessScore: quotaValidation.allowed ? airllmScore : 0,
      passedDeterministicVerification: airllmPassed,
      costPerVerifiedOutcomeGbp: airllmPassed
        ? Number((airllmCost / (airllmScore / 100)).toFixed(4))
        : 9.9999,
      reproducibleEvidenceHash: quotaValidation.allowed
        ? `sha256:airllm-${airllmModel.id}-${task.id}-9f4e2`
        : 'BLOCKED_BY_PREFLIGHT_QUOTA_GATE',
      diagnosticFinding: quotaValidation.allowed
        ? `Synthesized full causal chain (${task.expectedRootCause}) while keeping GPU working set at ${airllmModel.reportedVramGb} GB.`
        : `Execution prevented prior to shard creation: ${quotaValidation.blockingReasons[0]}`
    },
    {
      laneId: 'external-api',
      laneLabel: 'External Frontier API Baseline',
      modelName: 'Frontier Cloud Verifier API',
      modelFamily: 'claude-external',
      epistemicIndependenceFromImplementer: externalApiIndependent,
      latencySeconds: externalApiLatencySec,
      throughputTokensPerSec: Number((task.outputTokensRequired / externalApiLatencySec).toFixed(1)),
      vramPeakGb: 0,
      diskShardPeakGb: 0,
      executionCostGbp: externalApiCost,
      verifiedCorrectnessScore: externalApiScore,
      passedDeterministicVerification: true,
      costPerVerifiedOutcomeGbp: Number((externalApiCost / (externalApiScore / 100)).toFixed(4)),
      reproducibleEvidenceHash: `sha256:extapi-${task.id}-3b88d`,
      diagnosticFinding:
        'Accurate causal diagnosis, but relies on external provider availability and incurs per-token API spend.'
    }
  ];

  const acceptanceCriteriaStatus = [
    {
      id: 'ac-1-isolated-worker',
      label: 'Run on a separate worker without disrupting existing estate services',
      passed: host.isolatedFromEstateServices,
      evidenceNote: host.isolatedFromEstateServices
        ? `Verified isolated execution on ${host.name} (cgroups I/O & GPU namespace isolated).`
        : `Failed: ${host.name} shares resources with local development / interactive services.`
    },
    {
      id: 'ac-2-resource-limits',
      label: 'Enforce disk, RAM, GPU and wall-clock resource limits',
      passed:
        quotaValidation.checks.vramWithinLimit &&
        quotaValidation.checks.diskWithinQuota &&
        quotaValidation.checks.wallClockWithinLimit &&
        quotaValidation.checks.osArchitectureCompatible,
      evidenceNote: quotaValidation.allowed
        ? `VRAM ${airllmModel.reportedVramGb}/${host.availableVramGb} GB · Disk ${quotaValidation.totalRequiredDiskGb}/${host.enforcedDiskQuotaGb} GB · Time ${quotaValidation.projectedWallClockMinutes}/${host.maxWallClockMinutes}m.`
        : `Guardrail triggered: ${quotaValidation.blockingReasons.join(' ')}`
    },
    {
      id: 'ac-3-three-way-comparison',
      label: 'Compare against a fast local model and an external API baseline',
      passed: lanes.length === 3,
      evidenceNote: '3-way telemetry recorded across Fast Local Q4, AirLLM Streamed, and External API Baseline.'
    },
    {
      id: 'ac-4-real-idp-incidents',
      label: 'Evaluate on real IDP incidents and architectural review tasks',
      passed: Boolean(task.incidentReference),
      evidenceNote: `Evaluated against ${task.incidentReference} (${task.department}).`
    },
    {
      id: 'ac-5-telemetry-recorded',
      label: 'Record correctness, latency, throughput, cost and failure rate',
      passed: true,
      evidenceNote: `AirLLM: ${airllmScore}% correctness · ${airllmLatencySec}s latency · ${airllmThroughput} tok/s · £${airllmCost.toFixed(4)} cost.`
    },
    {
      id: 'ac-6-reproducible-evidence',
      label: 'Require reproducible evidence for every accepted conclusion',
      passed: quotaValidation.allowed && airllmEpistemicIndependent,
      evidenceNote: quotaValidation.allowed
        ? `Deterministic artifact hash ${lanes[1].reproducibleEvidenceHash} + cross-family independence (${airllmModel.modelFamily} vs ${task.implementingModelFamily}).`
        : 'Blocked run or correlated model family; conclusion not accepted without independent proof.'
    },
    {
      id: 'ac-7-cleanup-proven',
      label: 'Prove cancellation, recovery and complete model-shard cleanup',
      passed: true,
      evidenceNote: `100% of temporary layer shards (${quotaValidation.totalRequiredDiskGb} GB) purged via deterministic post-run hook.`
    },
    {
      id: 'ac-8-single-router',
      label: 'Integrate through the existing router, not a second control plane',
      passed: true,
      evidenceNote: 'Dispatched via unified IDP Context Compiler & Inference Router policy table.'
    }
  ];

  const allCriteriaPassed = acceptanceCriteriaStatus.every((c) => c.passed);
  const overallRecommendation = !quotaValidation.allowed
    ? 'HOLD_QUOTA_OR_ARCH_BLOCKED'
    : allCriteriaPassed && airllmScore >= 85
    ? 'ADOPT_FOR_OVERNIGHT_LANE'
    : 'PREFER_FAST_BASELINE';

  const cleanModelSlug = airllmModel.id.replace(/[^a-zA-Z0-9]/g, '').slice(0, 8).toUpperCase();
  return {
    experimentId: `EXP-${task.id.toUpperCase()}-${cleanModelSlug}`,
    timestampIso: '2026-11-05T03:24:00Z',
    task,
    hostProfile: host,
    airllmModel,
    quotaValidation,
    lanes,
    shardCleanupVerified: true,
    cancellationRecoveryProven: true,
    reclaimedDiskGb: quotaValidation.allowed ? quotaValidation.totalRequiredDiskGb : 0,
    acceptanceCriteriaStatus,
    overallRecommendation
  };
}
