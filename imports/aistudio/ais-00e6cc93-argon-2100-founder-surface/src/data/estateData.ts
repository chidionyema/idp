import { SubsystemHealth, CapabilityInventoryItem, AgentFleetMember, ExecutionLogItem, EstateState } from '../utils/estateLogic';

export interface SpineNode {
  id: string;
  name: string;
  type: 'core' | 'synapse' | 'buffer' | 'router' | 'gateway';
  x: number;
  y: number;
  status: 'nominal' | 'active' | 'syncing';
  latencyMs: number;
  loadPct: number;
  connections: string[];
}

export const INITIAL_SPINE_NODES: SpineNode[] = [
  { id: 'node-core', name: 'Spine Core Alpha', type: 'core', x: 50, y: 50, status: 'nominal', latencyMs: 4, loadPct: 68, connections: ['node-syn-1', 'node-syn-2', 'node-route-1', 'node-buf-1'] },
  { id: 'node-syn-1', name: 'Synapse Mesh North', type: 'synapse', x: 25, y: 30, status: 'nominal', latencyMs: 8, loadPct: 54, connections: ['node-core', 'node-gw-1'] },
  { id: 'node-syn-2', name: 'Synapse Mesh South', type: 'synapse', x: 75, y: 30, status: 'nominal', latencyMs: 7, loadPct: 62, connections: ['node-core', 'node-gw-2'] },
  { id: 'node-route-1', name: 'Neural Router East', type: 'router', x: 80, y: 70, status: 'nominal', latencyMs: 11, loadPct: 78, connections: ['node-core', 'node-buf-2'] },
  { id: 'node-buf-1', name: 'Cognitive Buffer West', type: 'buffer', x: 20, y: 70, status: 'nominal', latencyMs: 6, loadPct: 41, connections: ['node-core', 'node-syn-1'] },
  { id: 'node-buf-2', name: 'Context Memory Relay', type: 'buffer', x: 50, y: 85, status: 'nominal', latencyMs: 9, loadPct: 59, connections: ['node-core', 'node-route-1'] },
  { id: 'node-gw-1', name: 'Legion Dispatch Gateway', type: 'gateway', x: 12, y: 15, status: 'syncing', latencyMs: 24, loadPct: 83, connections: ['node-syn-1'] },
  { id: 'node-gw-2', name: 'Inference Stream Ingress', type: 'gateway', x: 88, y: 15, status: 'nominal', latencyMs: 14, loadPct: 65, connections: ['node-syn-2'] },
];

export const INITIAL_SUBSYSTEMS: SubsystemHealth[] = [
  { id: 'sub-genesis', name: 'Genesis Neural Spine', category: 'spine', status: 'nominal', latencyMs: 11, throughputPerSec: 14850, memoryUsageMb: 2450, uptimePct: 99.98, greenlaneVerified: true },
  { id: 'sub-compute', name: 'Inference Acceleration Cluster', category: 'compute', status: 'nominal', latencyMs: 16, throughputPerSec: 8920, memoryUsageMb: 6144, uptimePct: 99.94, greenlaneVerified: true },
  { id: 'sub-memory', name: 'One-Brain Episodic Memory Store', category: 'memory', status: 'nominal', latencyMs: 9, throughputPerSec: 11200, memoryUsageMb: 4096, uptimePct: 99.99, greenlaneVerified: true },
  { id: 'sub-legion', name: 'Legion Gateway Orchestrator', category: 'agents', status: 'recovering', latencyMs: 34, throughputPerSec: 1420, memoryUsageMb: 1280, uptimePct: 98.40, greenlaneVerified: false },
  { id: 'sub-omega', name: 'Omega Execution Controller', category: 'governance', status: 'nominal', latencyMs: 8, throughputPerSec: 4300, memoryUsageMb: 1024, uptimePct: 100.0, greenlaneVerified: true },
  { id: 'sub-firewall', name: 'Transcript & Encoding Firewall', category: 'governance', status: 'nominal', latencyMs: 4, throughputPerSec: 21500, memoryUsageMb: 512, uptimePct: 99.99, greenlaneVerified: true },
  { id: 'sub-research', name: 'Argon Active ML Engine', category: 'compute', status: 'nominal', latencyMs: 19, throughputPerSec: 3600, memoryUsageMb: 8192, uptimePct: 99.85, greenlaneVerified: true },
  { id: 'sub-concierge', name: '2100 Spatial Voice & HUD Gateway', category: 'gateway', status: 'nominal', latencyMs: 14, throughputPerSec: 5100, memoryUsageMb: 950, uptimePct: 99.95, greenlaneVerified: true },
];

export const INITIAL_AGENTS: AgentFleetMember[] = [
  {
    id: 'agent-legion',
    name: 'Legion Orchestrator',
    role: 'Gateway Deployment & Build Supervisor',
    cluster: 'Orchestration-Alpha',
    status: 'recovering',
    currentTask: 'Queued for Recovery Run #42412348112 (Remediation: clean non-ASCII chars in founder-gateway)',
    concurrency: 12,
    yieldRatio: 0.88,
    lastRunId: '42412348112',
  },
  {
    id: 'agent-argon-ml',
    name: 'Argon Research ML',
    role: 'Continuous Fine-Tuning & Weights Evaluation',
    cluster: 'GPU-Cluster-West',
    status: 'active',
    currentTask: 'Evaluating Checkpoint v8.4-Omni test loss convergence curve',
    concurrency: 24,
    yieldRatio: 0.96,
    lastRunId: '883921094',
  },
  {
    id: 'agent-omega',
    name: 'Omega Core Protocol',
    role: 'Operational Invariant & Greenlane Supervisor',
    cluster: 'Spine-Core-01',
    status: 'active',
    currentTask: 'Continuously polling Greenlane packet synchrony & invariants',
    concurrency: 8,
    yieldRatio: 1.0,
    lastRunId: '90023411',
  },
  {
    id: 'agent-hermes',
    name: 'Hermes Telemetry Relay',
    role: 'Estate Diagnostics & Latency Tracing',
    cluster: 'Telemetry-Mesh',
    status: 'active',
    currentTask: 'Aggregating subsystem p99 latency trees and memory pressure',
    concurrency: 16,
    yieldRatio: 0.94,
    lastRunId: '77291032',
  },
  {
    id: 'agent-athena',
    name: 'Athena QA Auditor',
    role: 'Automated Capability-Parity Regression Gatekeeper',
    cluster: 'Governance-Node',
    status: 'active',
    currentTask: 'Verifying all 38 estate capabilities preserved in deployed 2100 surface',
    concurrency: 6,
    yieldRatio: 0.99,
    lastRunId: '65412908',
  },
  {
    id: 'agent-vulcan',
    name: 'Vulcan Yield Optimizer',
    role: 'Token Yield & Instruction Cost Optimization',
    cluster: 'Yield-Cluster-02',
    status: 'active',
    currentTask: 'Calibrating reasoning tokens vs instruction completion yield',
    concurrency: 10,
    yieldRatio: 0.93,
    lastRunId: '54201984',
  },
];

export const INITIAL_CAPABILITIES: CapabilityInventoryItem[] = [
  { id: 'cap-1', code: 'EST-SPINE-01', pillar: 'Genesis Spine & Topology', name: 'Dynamic Neural Spine Topology Graph', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'neural_spine', lastAuditTimestamp: '2026-11-07 12:45' },
  { id: 'cap-2', code: 'EST-SPINE-02', pillar: 'Genesis Spine & Topology', name: 'Synapse Packet Flow & Latency Tracing', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'neural_spine', lastAuditTimestamp: '2026-11-07 12:45' },
  { id: 'cap-3', code: 'EST-RES-01', pillar: 'Research & ML', name: 'Continuous Checkpoint Weights & Loss Curves', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:42' },
  { id: 'cap-4', code: 'EST-RES-02', pillar: 'Research & ML', name: 'Active Inference Benchmark Yields', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'operational_store', lastAuditTimestamp: '2026-11-07 12:42' },
  { id: 'cap-5', code: 'EST-DIAG-01', pillar: 'Estate Diagnostics', name: 'Full Subsystem Health & Latency Matrix', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:50' },
  { id: 'cap-6', code: 'EST-DIAG-02', pillar: 'Estate Diagnostics', name: 'Greenlane Invariant Audit & Verification', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:50' },
  { id: 'cap-7', code: 'EST-FLEET-01', pillar: 'Fleet Management', name: 'Autonomous Agent Fleet Status & Task Queues', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'operational_store', lastAuditTimestamp: '2026-11-07 12:48' },
  { id: 'cap-8', code: 'EST-FLEET-02', pillar: 'Fleet Management', name: 'Legion Recovery Mission Controller (#42412348112)', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:48' },
  { id: 'cap-9', code: 'EST-YIELD-01', pillar: 'Instruction & Yield History', name: 'Granular Instruction Yield & Cost Ratios', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'operational_store', lastAuditTimestamp: '2026-11-07 12:40' },
  { id: 'cap-10', code: 'EST-YIELD-02', pillar: 'Instruction & Yield History', name: 'Execution Run Audit & Recovery Event Log', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'operational_store', lastAuditTimestamp: '2026-11-07 12:40' },
  { id: 'cap-11', code: 'EST-GOV-01', pillar: 'Protocols & Governance', name: 'Transcript Firewall & Ruff Compliance Engine', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:35' },
  { id: 'cap-12', code: 'EST-GOV-02', pillar: 'Protocols & Governance', name: 'Trusted Push Gate & ASCII/UTF-8 Firewall', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:35' },
  { id: 'cap-13', code: 'EST-MEM-01', pillar: 'Memory & One-Brain', name: '2.84M Semantic Vector Cluster Navigator', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'neural_spine', lastAuditTimestamp: '2026-11-07 12:44' },
  { id: 'cap-14', code: 'EST-MEM-02', pillar: 'Memory & One-Brain', name: 'Episodic Graph & Founder Directives Anchor', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'neural_spine', lastAuditTimestamp: '2026-11-07 12:44' },
  { id: 'cap-15', code: 'EST-EVAL-01', pillar: 'Evaluations & Regression Gate', name: 'Automated Feature-Parity Regression Gate', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'operational_store', lastAuditTimestamp: '2026-11-07 12:50' },
  { id: 'cap-16', code: 'EST-EVAL-02', pillar: 'Evaluations & Regression Gate', name: 'Non-Destructive Capability Verification Suite', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'operational_store', lastAuditTimestamp: '2026-11-07 12:50' },
  { id: 'cap-17', code: 'EST-OMEGA-01', pillar: 'Omega Operational Control', name: 'Founder Direct Parameter Override Console', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:49' },
  { id: 'cap-18', code: 'EST-OMEGA-02', pillar: 'Omega Operational Control', name: 'Emergency Subsystem Isolation & Kill Switches', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'live_telemetry', lastAuditTimestamp: '2026-11-07 12:49' },
  { id: 'cap-19', code: 'EST-VOICE-01', pillar: 'Voice & 2100 Concierge', name: 'Audio-Reactive Voice Concierge Orb Interface', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'neural_spine', lastAuditTimestamp: '2026-11-07 12:51' },
  { id: 'cap-20', code: 'EST-VOICE-02', pillar: 'Voice & 2100 Concierge', name: 'Contextual Spatial Intelligence Card Projection', status: 'active', exposedIn2100Surface: true, deepSpecialistViewAvailable: true, dataSource: 'neural_spine', lastAuditTimestamp: '2026-11-07 12:51' },
];

export const INITIAL_LOGS: ExecutionLogItem[] = [
  {
    id: 'log-01',
    timestamp: '2026-11-07 12:48:11',
    actor: 'Legion Recovery Watcher',
    action: 'Queued Legion recovery run #42412348112',
    pillar: 'Fleet Management',
    status: 'queued',
    details: 'Remediation instructions submitted for founder-gateway build. Clean ASCII encoding staged.',
    instructionYieldScore: 0.94,
  },
  {
    id: 'log-02',
    timestamp: '2026-11-07 12:44:02',
    actor: 'Trusted Push Gate',
    action: 'Push rejected: Non-ASCII bytes detected in founder-gateway/src/index.ts',
    pillar: 'Protocols & Governance',
    status: 'failed',
    details: 'Encountered em-dash (0x2014) in comment header. Ruff passed, transcript firewall passed, push blocked.',
    instructionYieldScore: 0.72,
  },
  {
    id: 'log-03',
    timestamp: '2026-11-07 12:39:15',
    actor: 'Athena Regression Suite',
    action: 'Automated capability-parity regression gate: PASS',
    pillar: 'Evaluations & Regression Gate',
    status: 'passed',
    details: '20 of 20 core capabilities verified exposed and operable on 2100 Founder Surface.',
    instructionYieldScore: 1.0,
  },
  {
    id: 'log-04',
    timestamp: '2026-11-07 12:30:20',
    actor: 'Argon Research ML',
    action: 'Checkpoint v8.4-Omni training epoch 48 completed',
    pillar: 'Research & ML',
    status: 'passed',
    details: 'Convergence loss settled to 0.0418. Reasoning benchmark yield increased to 1.84x.',
    instructionYieldScore: 0.98,
  },
  {
    id: 'log-05',
    timestamp: '2026-11-07 12:22:45',
    actor: 'Omega Controller',
    action: 'Greenlane state verified across all 12 Genesis nodes',
    pillar: 'Estate Diagnostics',
    status: 'passed',
    details: 'Invariant checks nominal. Average node sync latency 11ms.',
    instructionYieldScore: 1.0,
  },
];

export const INITIAL_ESTATE_STATE: EstateState = {
  healthScore: 94,
  activeAgents: 5,
  totalInferenceThroughput: 59340,
  greenlaneStatus: 'warning', // Warning because Legion is in recovery
  parityGatePass: true,
  asciiFirewallViolations: 1, // Reflects the Legion non-ASCII incident awaiting remediation confirmation
  subsystems: INITIAL_SUBSYSTEMS,
  capabilities: INITIAL_CAPABILITIES,
  agents: INITIAL_AGENTS,
  recentLogs: INITIAL_LOGS,
  operationalParameters: {
    maxConcurrency: 32,
    inferenceTemperature: 0.2,
    transcriptFirewallStrictness: 'strict',
    trustedPushEncodingCheck: true,
    voiceConciergeSynthesis: true,
    spatialProjectionRateHz: 60,
  },
};
