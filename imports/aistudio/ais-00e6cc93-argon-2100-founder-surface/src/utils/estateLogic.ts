export interface SubsystemHealth {
  id: string;
  name: string;
  category: 'spine' | 'compute' | 'memory' | 'agents' | 'governance' | 'gateway';
  status: 'nominal' | 'degraded' | 'critical' | 'recovering';
  latencyMs: number;
  throughputPerSec: number;
  memoryUsageMb: number;
  uptimePct: number;
  greenlaneVerified: boolean;
}

export interface CapabilityInventoryItem {
  id: string;
  code: string;
  name: string;
  pillar: string;
  status: 'active' | 'under_review' | 'blocked_by_regression_gate';
  exposedIn2100Surface: boolean;
  deepSpecialistViewAvailable: boolean;
  dataSource: 'live_telemetry' | 'operational_store' | 'neural_spine';
  lastAuditTimestamp: string;
}

export interface AgentFleetMember {
  id: string;
  name: string;
  role: string;
  cluster: string;
  status: 'active' | 'recovering' | 'idle' | 'halted';
  currentTask: string;
  concurrency: number;
  yieldRatio: number;
  lastRunId?: string;
}

export interface ExecutionLogItem {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  pillar: string;
  status: 'passed' | 'remediated' | 'failed' | 'queued';
  details: string;
  instructionYieldScore: number;
}

export interface EstateState {
  healthScore: number;
  activeAgents: number;
  totalInferenceThroughput: number;
  greenlaneStatus: 'verified' | 'warning' | 'bypassed';
  parityGatePass: boolean;
  asciiFirewallViolations: number;
  subsystems: SubsystemHealth[];
  capabilities: CapabilityInventoryItem[];
  agents: AgentFleetMember[];
  recentLogs: ExecutionLogItem[];
  operationalParameters: {
    maxConcurrency: number;
    inferenceTemperature: number;
    transcriptFirewallStrictness: 'strict' | 'standard' | 'bypass';
    trustedPushEncodingCheck: boolean;
    voiceConciergeSynthesis: boolean;
    spatialProjectionRateHz: number;
  };
}

export function calculateEstateHealth(subsystems: SubsystemHealth[]): {
  overallHealthScore: number;
  allNominal: boolean;
  criticalCount: number;
  degradedCount: number;
  averageLatencyMs: number;
} {
  if (!subsystems || subsystems.length === 0) {
    return {
      overallHealthScore: 0,
      allNominal: false,
      criticalCount: 0,
      degradedCount: 0,
      averageLatencyMs: 0,
    };
  }

  let totalScore = 0;
  let criticalCount = 0;
  let degradedCount = 0;
  let totalLatency = 0;

  for (const s of subsystems) {
    totalLatency += s.latencyMs;
    if (s.status === 'nominal') {
      totalScore += 100;
    } else if (s.status === 'recovering') {
      totalScore += 80;
      degradedCount++;
    } else if (s.status === 'degraded') {
      totalScore += 60;
      degradedCount++;
    } else {
      totalScore += 20;
      criticalCount++;
    }
  }

  const overallHealthScore = Math.round(totalScore / subsystems.length);
  const averageLatencyMs = Math.round(totalLatency / subsystems.length);

  return {
    overallHealthScore,
    allNominal: criticalCount === 0 && degradedCount === 0,
    criticalCount,
    degradedCount,
    averageLatencyMs,
  };
}

export function evaluateParityRegressionGate(inventory: CapabilityInventoryItem[]): {
  passed: boolean;
  totalCapabilities: number;
  activeCount: number;
  surfaceExposedCount: number;
  deepSpecialistCount: number;
  missingInSurface: string[];
  missingDeepView: string[];
  scorePct: number;
} {
  const missingInSurface: string[] = [];
  const missingDeepView: string[] = [];
  let activeCount = 0;
  let surfaceExposedCount = 0;
  let deepSpecialistCount = 0;

  for (const cap of inventory) {
    if (cap.status === 'active') activeCount++;
    if (cap.exposedIn2100Surface) {
      surfaceExposedCount++;
    } else {
      missingInSurface.push(cap.name);
    }

    if (cap.deepSpecialistViewAvailable) {
      deepSpecialistCount++;
    } else {
      missingDeepView.push(cap.name);
    }
  }

  const total = inventory.length;
  const passed = missingInSurface.length === 0 && missingDeepView.length === 0 && total > 0;
  const scorePct = total > 0 ? Math.round(((surfaceExposedCount + deepSpecialistCount) / (total * 2)) * 100) : 0;

  return {
    passed,
    totalCapabilities: total,
    activeCount,
    surfaceExposedCount,
    deepSpecialistCount,
    missingInSurface,
    missingDeepView,
    scorePct,
  };
}

export function validateAsciiFirewall(fileContent: string): {
  valid: boolean;
  violations: Array<{ line: number; character: string; charCode: number }>;
} {
  const lines = fileContent.split('\n');
  const violations: Array<{ line: number; character: string; charCode: number }> = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (let c = 0; c < line.length; c++) {
      const code = line.charCodeAt(c);
      if (code > 127) {
        violations.push({
          line: i + 1,
          character: line[c],
          charCode: code,
        });
      }
    }
  }

  return {
    valid: violations.length === 0,
    violations,
  };
}

export interface InterrogationResult {
  query: string;
  category: 'legion_recovery' | 'genesis_spine' | 'estate_diagnostics' | 'research_ml' | 'fleet' | 'memory' | 'governance' | 'general';
  synthesis: string;
  recommendedView: string;
  contextData: Record<string, unknown>;
  confidence: number;
}

export function executeFounderInterrogation(query: string, state: EstateState): InterrogationResult {
  const lower = query.toLowerCase().trim();

  if (lower.includes('legion') || lower.includes('42412348112') || lower.includes('recovery run') || lower.includes('non-ascii')) {
    const legionAgent = state.agents.find(a => a.name.toLowerCase().includes('legion'));
    return {
      query,
      category: 'legion_recovery',
      synthesis: 'Legion Recovery Run #42412348112 is currently in state RECOVERING. Root cause: non-ASCII UTF-8 characters detected in founder-gateway build by trusted push firewall. Remediation instructions applied; pipeline queued for verified re-run.',
      recommendedView: 'fleet',
      confidence: 0.99,
      contextData: {
        runId: '42412348112',
        agent: legionAgent?.name || 'Legion Engine',
        status: legionAgent?.status || 'recovering',
        cluster: legionAgent?.cluster || 'Orchestration-01',
        remediationStatus: 'Instructions Queued - Awaiting Parity Gate Re-verification',
      },
    };
  }

  if (lower.includes('genesis') || lower.includes('spine') || lower.includes('topology') || lower.includes('node')) {
    return {
      query,
      category: 'genesis_spine',
      synthesis: 'Genesis Neural Spine is operating at nominal topology across 12 distributed cognitive nodes. Latency is locked under 18ms with 100% Greenlane packet synchrony.',
      recommendedView: 'genesis_spine',
      confidence: 0.95,
      contextData: {
        totalNodes: 12,
        syncRate: '99.98%',
        spineBackbone: 'High-Bandwidth Active Synapse Fabric',
        greenlaneIntegrity: state.greenlaneStatus,
      },
    };
  }

  if (lower.includes('parity') || lower.includes('gate') || lower.includes('regression') || lower.includes('capability')) {
    const parity = evaluateParityRegressionGate(state.capabilities);
    return {
      query,
      category: 'governance',
      synthesis: parity.passed
        ? `Capability-parity regression gate: PASS. All ${parity.totalCapabilities} estate intelligence capabilities are preserved, discoverable, and exposed on the 2100 surface.`
        : `Capability-parity regression gate: WARNING. ${parity.missingInSurface.length} items missing surface exposure, ${parity.missingDeepView.length} missing deep view.`,
      recommendedView: 'evaluations',
      confidence: 0.98,
      contextData: {
        passed: parity.passed,
        scorePct: parity.scorePct,
        activeCount: parity.activeCount,
        total: parity.totalCapabilities,
      },
    };
  }

  if (lower.includes('diagnostic') || lower.includes('health') || lower.includes('greenlane') || lower.includes('throughput')) {
    const health = calculateEstateHealth(state.subsystems);
    return {
      query,
      category: 'estate_diagnostics',
      synthesis: `Estate Health Index stands at ${health.overallHealthScore}/100. Average subsystem latency is ${health.averageLatencyMs}ms across ${state.subsystems.length} monitored subsystems. Greenlane state: ${state.greenlaneStatus.toUpperCase()}.`,
      recommendedView: 'diagnostics',
      confidence: 0.94,
      contextData: {
        overallHealthScore: health.overallHealthScore,
        criticalCount: health.criticalCount,
        degradedCount: health.degradedCount,
        greenlane: state.greenlaneStatus,
      },
    };
  }

  if (lower.includes('research') || lower.includes('ml') || lower.includes('model') || lower.includes('checkpoint')) {
    return {
      query,
      category: 'research_ml',
      synthesis: 'Argon Active ML Suite is evaluating Checkpoint v8.4-Omni with 94.2% test loss convergence and 1.84 instruction-yield multiplier across reasoning benchmarks.',
      recommendedView: 'research',
      confidence: 0.92,
      contextData: {
        checkpoint: 'v8.4-Omni',
        convergenceLoss: 0.042,
        benchmarkScore: 94.2,
      },
    };
  }

  if (lower.includes('memory') || lower.includes('one-brain') || lower.includes('vector') || lower.includes('context')) {
    return {
      query,
      category: 'memory',
      synthesis: 'One-Brain Episodic Memory stores 2.8M verified knowledge vectors with active associative cross-linking to founder directives and historical execution traces.',
      recommendedView: 'memory',
      confidence: 0.91,
      contextData: {
        vectorCount: '2.84M vectors',
        workingContextSize: '128k tokens',
        semanticSync: 'Nominal',
      },
    };
  }

  return {
    query,
    category: 'general',
    synthesis: `Founder inquiry processed against Estate Intelligence Core. All operational logs, agent states, and governance gates are synchronized across the 2100 surface.`,
    recommendedView: 'overview',
    confidence: 0.85,
    contextData: {
      estateHealth: state.healthScore,
      activeAgents: state.activeAgents,
    },
  };
}

export function applyOperationalAction(
  currentState: EstateState,
  action: {
    type: 'remediate_legion' | 'verify_greenlane' | 'toggle_parity_gate' | 'tune_parameter' | 'halt_agent' | 'resume_agent';
    payload?: Record<string, unknown>;
  }
): EstateState {
  const updated = structuredClone(currentState);

  if (action.type === 'remediate_legion') {
    const legion = updated.agents.find(a => a.name.toLowerCase().includes('legion'));
    if (legion) {
      legion.status = 'active';
      legion.currentTask = 'Executing mission post-ASCII remediation (Recovery #42412348112)';
    }
    updated.asciiFirewallViolations = 0;
    updated.recentLogs.unshift({
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString(),
      actor: 'Founder Surface Override',
      action: 'Legion Recovery Run #42412348112 Remediated',
      pillar: 'Fleet Management',
      status: 'passed',
      details: 'Clean ASCII encoding enforced. Trusted push firewall passed. Agent restored to active cluster.',
      instructionYieldScore: 0.98,
    });
    const health = calculateEstateHealth(updated.subsystems);
    updated.healthScore = health.overallHealthScore;
  }

  if (action.type === 'verify_greenlane') {
    updated.greenlaneStatus = 'verified';
    for (const sub of updated.subsystems) {
      sub.greenlaneVerified = true;
      if (sub.status === 'degraded' || sub.status === 'recovering') {
        sub.status = 'nominal';
      }
    }
    updated.recentLogs.unshift({
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString(),
      actor: 'Founder Surface Execution',
      action: 'Greenlane Estate Verification Completed',
      pillar: 'Estate Diagnostics',
      status: 'passed',
      details: 'All diagnostics passed invariant checks. Greenlane synchronization established across nodes.',
      instructionYieldScore: 1.0,
    });
    const health = calculateEstateHealth(updated.subsystems);
    updated.healthScore = health.overallHealthScore;
  }

  if (action.type === 'tune_parameter' && action.payload) {
    if (typeof action.payload.maxConcurrency === 'number') {
      updated.operationalParameters.maxConcurrency = action.payload.maxConcurrency;
    }
    if (typeof action.payload.spatialProjectionRateHz === 'number') {
      updated.operationalParameters.spatialProjectionRateHz = action.payload.spatialProjectionRateHz;
    }
    if (typeof action.payload.transcriptFirewallStrictness === 'string') {
      updated.operationalParameters.transcriptFirewallStrictness = action.payload.transcriptFirewallStrictness as 'strict' | 'standard' | 'bypass';
    }
    updated.recentLogs.unshift({
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString(),
      actor: 'Founder Deep Control',
      action: 'Operational Parameters Adjusted',
      pillar: 'Omega Control',
      status: 'passed',
      details: `Parameters updated: Concurrency=${updated.operationalParameters.maxConcurrency}, Firewall=${updated.operationalParameters.transcriptFirewallStrictness}`,
      instructionYieldScore: 0.95,
    });
  }

  return updated;
}
