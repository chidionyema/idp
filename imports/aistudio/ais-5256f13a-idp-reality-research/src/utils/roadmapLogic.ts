import {
  ArchitecturalPlane,
  ArchitectureProposalRfc,
  AsymmetryVector,
  ConsultantQuestion,
  HorizonId,
  IncidentRecord,
  RoadmapMilestone,
} from '../data/idpDomainData';

export interface RoadmapFilterState {
  horizon: HorizonId | 'ALL';
  plane: ArchitecturalPlane | 'ALL';
  vector: AsymmetryVector | 'ALL';
  searchQuery: string;
}

export interface SimulationConfig {
  streamingWindowSec: number; // 1 to 3600
  bitemporalAuditStrictness: number; // 50 to 100
  falsificationGatesCount: number; // 1 to 8
  entityResolutionConcurrency: number; // 1000 to 50000 updates/sec
}

export interface ArchitectureSimulationResult {
  endToEndLatencyMs: number;
  bitemporalFidelityPct: number;
  falsePositiveRatePct: number;
  monthlyInfraBurnUsd: number;
  expectedAsymmetryCapturePct: number;
  totalImplementationWeeks: number;
  criticalPathScore: 'Optimal' | 'Balanced' | 'High Latency Risk' | 'Leakage Risk';
}

export function filterMilestones(
  milestones: RoadmapMilestone[],
  filters: RoadmapFilterState
): RoadmapMilestone[] {
  return milestones.filter((ms) => {
    if (filters.horizon !== 'ALL' && ms.horizon !== filters.horizon) {
      return false;
    }
    if (filters.plane !== 'ALL' && ms.plane !== filters.plane) {
      return false;
    }
    if (filters.vector !== 'ALL' && ms.asymmetryVector !== filters.vector) {
      return false;
    }
    if (filters.searchQuery.trim() !== '') {
      const q = filters.searchQuery.toLowerCase().trim();
      const matchTitle = ms.title.toLowerCase().includes(q);
      const matchId = ms.id.toLowerCase().includes(q);
      const matchThesis = ms.thesisImpact.toLowerCase().includes(q);
      const matchIncident = ms.linkedIncidentIds.some((id) => id.toLowerCase().includes(q));
      const matchRfc = ms.linkedRfcId.toLowerCase().includes(q);
      if (!matchTitle && !matchId && !matchThesis && !matchIncident && !matchRfc) {
        return false;
      }
    }
    return true;
  });
}

export function computeRoadmapSummary(milestones: RoadmapMilestone[]) {
  const total = milestones.length;
  const completed = milestones.filter((m) => m.status === 'Completed').length;
  const inProgress = milestones.filter((m) => m.status === 'In Progress').length;
  const blocked = milestones.filter((m) => m.status === 'Blocked by RFC').length;
  const planned = milestones.filter((m) => m.status === 'Planned').length;
  const totalEffortWeeks = milestones.reduce((acc, m) => acc + m.effortWeeks, 0);

  const byHorizon: Record<HorizonId, { count: number; weeks: number }> = {
    H1: { count: 0, weeks: 0 },
    H2: { count: 0, weeks: 0 },
    H3: { count: 0, weeks: 0 },
  };

  for (const m of milestones) {
    byHorizon[m.horizon].count += 1;
    byHorizon[m.horizon].weeks += m.effortWeeks;
  }

  return {
    total,
    completed,
    inProgress,
    blocked,
    planned,
    totalEffortWeeks,
    byHorizon,
  };
}

export function simulateArchitectureMetrics(
  rfcs: ArchitectureProposalRfc[],
  config: SimulationConfig
): ArchitectureSimulationResult {
  let baseLatencyMs = 0;
  let baseCostUsd = 0;
  let fidelitySum = 0;
  let captureLiftSum = 0;
  let totalWeeks = 0;

  for (const rfc of rfcs) {
    const selected =
      rfc.options.find((o) => o.id === rfc.selectedOptionId) || rfc.options[0];
    baseLatencyMs += selected.latencyImpactMs;
    baseCostUsd += selected.monthlyInfraCostUsd;
    fidelitySum += selected.bitemporalFidelityScore;
    captureLiftSum += selected.asymmetryCaptureLiftPct;
    totalWeeks += selected.implementationWeeks;
  }

  const avgRfcFidelity = rfcs.length > 0 ? fidelitySum / rfcs.length : 90;

  // Factor in streaming window vs micro-batch lag
  const windowPenaltyMs = Math.round(Math.sqrt(config.streamingWindowSec) * 110);
  const gateLatencyMs = config.falsificationGatesCount * 65;
  const concurrencyDiscountMs = Math.round((50000 - config.entityResolutionConcurrency) / 250);

  const endToEndLatencyMs = Math.max(
    180,
    baseLatencyMs + windowPenaltyMs + gateLatencyMs + concurrencyDiscountMs
  );

  const bitemporalFidelityPct = Math.min(
    100,
    Number(((avgRfcFidelity * 0.7 + config.bitemporalAuditStrictness * 0.3)).toFixed(1))
  );

  // False positive rate drops exponentially with falsification gates
  const rawFalsePositive = 24 * Math.exp(-0.32 * config.falsificationGatesCount);
  const falsePositiveRatePct = Number(Math.max(0.8, rawFalsePositive).toFixed(1));

  const computeMultiplier =
    1 +
    (config.falsificationGatesCount - 3) * 0.06 +
    (config.entityResolutionConcurrency / 25000) * 0.12;
  const monthlyInfraBurnUsd = Math.round(baseCostUsd * Math.max(0.75, computeMultiplier));

  // Asymmetry capture improves with low latency, high fidelity, and low false positives
  const latencyPenaltyPct = Math.min(35, endToEndLatencyMs / 180);
  const rawCapture =
    32 + captureLiftSum * 0.52 - latencyPenaltyPct * 0.45 + (bitemporalFidelityPct - 85) * 0.4;
  const expectedAsymmetryCapturePct = Number(
    Math.max(15, Math.min(96, rawCapture)).toFixed(1)
  );

  let criticalPathScore: ArchitectureSimulationResult['criticalPathScore'] = 'Balanced';
  if (bitemporalFidelityPct < 88) {
    criticalPathScore = 'Leakage Risk';
  } else if (endToEndLatencyMs > 2200) {
    criticalPathScore = 'High Latency Risk';
  } else if (expectedAsymmetryCapturePct >= 68 && bitemporalFidelityPct >= 94) {
    criticalPathScore = 'Optimal';
  }

  return {
    endToEndLatencyMs,
    bitemporalFidelityPct,
    falsePositiveRatePct,
    monthlyInfraBurnUsd,
    expectedAsymmetryCapturePct,
    totalImplementationWeeks: totalWeeks,
    criticalPathScore,
  };
}

export function validateNewIncidentInput(input: {
  title: string;
  affectedModule: string;
  rootCause: string;
  blastRadiusMetric: string;
}): { valid: boolean; error?: string } {
  if (!input.title || input.title.trim().length < 6) {
    return { valid: false, error: 'Incident title must be at least 6 characters.' };
  }
  if (!input.affectedModule || input.affectedModule.trim().length === 0) {
    return { valid: false, error: 'Please specify the affected repository module.' };
  }
  if (!input.blastRadiusMetric || input.blastRadiusMetric.trim().length < 4) {
    return { valid: false, error: 'Please provide a concrete blast radius metric.' };
  }
  if (!input.rootCause || input.rootCause.trim().length < 10) {
    return { valid: false, error: 'Root cause analysis must be at least 10 characters.' };
  }
  return { valid: true };
}

export function generateConsultantBriefMarkdown(params: {
  rfcs: ArchitectureProposalRfc[];
  incidents: IncidentRecord[];
  milestones: RoadmapMilestone[];
  questions: ConsultantQuestion[];
  simResult: ArchitectureSimulationResult;
  consultantRoleTitle: string;
  engagementWeeks: number;
  founderNotes: string;
}): string {
  const {
    rfcs,
    incidents,
    milestones,
    questions,
    simResult,
    consultantRoleTitle,
    engagementWeeks,
    founderNotes,
  } = params;

  const includedQuestions = questions.filter((q) => q.includedInBrief);
  const h1Milestones = milestones.filter((m) => m.horizon === 'H1');
  const h2Milestones = milestones.filter((m) => m.horizon === 'H2');
  const h3Milestones = milestones.filter((m) => m.horizon === 'H3');

  const lines: string[] = [
    `# IDP PLATFORM — EXTERNAL ARCHITECTURE CONSULTANT BRIEFING DOSSIER`,
    `Target Role: ${consultantRoleTitle}`,
    `Engagement Horizon: ${engagementWeeks} Weeks · Status: Decision-Ready Technical Package`,
    ``,
    `## 1. Executive Mission & Core Asymmetry Thesis`,
    `IDP is an empirical Reality Research Platform engineered to detect, falsify, and exploit systemic asymmetries — structural divergences between primary physical/regulatory reality and lagging consensus narratives. Unlike descriptive analytics pipelines, IDP enforces four non-negotiable architectural invariants:`,
    `- **INV-01 (Strict Bitemporal Isolation)**: Every state assertion is indexed on both \`t_valid\` (physical occurrence) and \`t_known\` (IDP ingestion timestamp) to guarantee zero look-ahead leakage.`,
    `- **INV-02 (Primary Telemetry Over Consensus)**: Direct ingestion of AIS maritime draughts, grid harmonics, customs manifests, and regulatory dockets before secondary aggregation.`,
    `- **INV-03 (Automated Adversarial Falsification)**: Candidate divergences must survive Bayesian sensor-confounding and null-hypothesis stress gates before promotion.`,
    `- **INV-04 (Cryptographic Byte Provenance)**: Every signal weight resolves deterministically to content-addressed BLAKE3 raw captures.`,
    ``,
    `## 2. Target Architecture Baseline & Simulated Performance Envelope`,
    `- **Projected End-to-End Signal Latency (P99)**: ${simResult.endToEndLatencyMs} ms`,
    `- **Bitemporal Audit Fidelity Score**: ${simResult.bitemporalFidelityPct}%`,
    `- **Post-Falsification False-Positive Rate**: ${simResult.falsePositiveRatePct}%`,
    `- **Expected Asymmetry Capture Ratio**: ${simResult.expectedAsymmetryCapturePct}%`,
    `- **Estimated Core Infra Burn**: $${simResult.monthlyInfraBurnUsd.toLocaleString()}/month`,
    `- **Architecture Posture**: ${simResult.criticalPathScore}`,
    ``,
    `## 3. Recent Production Incidents Driving Architectural Overhaul`,
    ...incidents.map(
      (inc) =>
        `- **${inc.id} (${inc.severity} · ${inc.affectedModule}) — ${inc.title}**\n  - *Blast Radius*: ${inc.blastRadiusMetric}\n  - *Root Cause*: ${inc.rootCause}\n  - *Linked Proposal*: ${inc.linkedRfcId}`
    ),
    ``,
    `## 4. Active Architecture Proposals (RFC Decisions for Consultant Sign-Off)`,
    ...rfcs.map((rfc) => {
      const sel = rfc.options.find((o) => o.id === rfc.selectedOptionId) || rfc.options[0];
      return [
        `### ${rfc.id}: ${rfc.title} [${rfc.status}]`,
        `- **Plane**: ${rfc.plane} (${rfc.horizon}) · **Linked Incidents**: ${rfc.linkedIncidents.join(', ')}`,
        `- **Selected Baseline**: ${sel.label} (${sel.latencyImpactMs}ms latency impact, $${sel.monthlyInfraCostUsd}/mo, ${sel.bitemporalFidelityScore}% fidelity)`,
        `- **Architecture Summary**: ${sel.architectureSummary}`,
        `- **Specific Question for Consultant**: ${rfc.consultantPromptQuestion}`,
      ].join('\n');
    }),
    ``,
    `## 5. Multi-Dimensional Roadmap Summary`,
    `### Horizon 1 (Days 0–90: Stabilization, Bitemporal Spine & Zero-Leakage Provenance)`,
    ...h1Milestones.map(
      (m) => `- **${m.id}**: ${m.title} (${m.effortWeeks}w · ${m.status}) — *Target*: ${m.acceptanceMetric}`
    ),
    `### Horizon 2 (Days 90–180: Streaming Divergence Kernel & Falsification Lab)`,
    ...h2Milestones.map(
      (m) => `- **${m.id}**: ${m.title} (${m.effortWeeks}w · ${m.status}) — *Target*: ${m.acceptanceMetric}`
    ),
    `### Horizon 3 (Days 180–365: Autonomous Red-Teaming & Second-Order Contagion)`,
    ...h3Milestones.map(
      (m) => `- **${m.id}**: ${m.title} (${m.effortWeeks}w · ${m.status}) — *Target*: ${m.acceptanceMetric}`
    ),
    ``,
    `## 6. Prioritized Technical Questions & Deliverables for External Consultant`,
    ...includedQuestions.map(
      (q) =>
        `- **[${q.id} · ${q.priority}] ${q.domain}**\n  - *Inquiry*: ${q.question}\n  - *Expected Deliverable*: ${q.expectedDeliverable}`
    ),
  ];

  if (founderNotes.trim().length > 0) {
    lines.push(``, `## 7. Founder & Programme Director Context Notes`, founderNotes.trim());
  }

  return lines.join('\n');
}
