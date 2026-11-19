import React, { useState } from 'react';
import {
  PlatformWorkloadUnit,
  ResearchDagStageNode,
  AgentsMdPointerEntry,
  PredictiveEarlyWarning,
  ProcessOpenLoopGap,
  computeResourceAllocationAndEviction,
  runAutonomousSelfReviewAndGapAnalysis,
} from '../lib/protocolEngine';

interface ResearchMlYieldGovernanceViewProps {
  workloads: PlatformWorkloadUnit[];
  dagNodes: ResearchDagStageNode[];
  pointers: AgentsMdPointerEntry[];
  earlyWarnings: PredictiveEarlyWarning[];
  openLoops: ProcessOpenLoopGap[];
  onRemediateWorkloadProof: (workloadId: string) => void;
  onEvictWorkloadNow: (workloadId: string) => void;
  onMitigateEarlyWarning: (warningId: string) => void;
  onCloseOpenLoop: (loopId: string) => void;
  onCloseAllLoopsAndWarnings: () => void;
  onRunResearchDagPass: () => void;
}

export const ResearchMlYieldGovernanceView: React.FC<
  ResearchMlYieldGovernanceViewProps
> = ({
  workloads,
  dagNodes,
  pointers,
  earlyWarnings,
  openLoops,
  onRemediateWorkloadProof,
  onEvictWorkloadNow,
  onMitigateEarlyWarning,
  onCloseOpenLoop,
  onCloseAllLoopsAndWarnings,
  onRunResearchDagPass,
}) => {
  const [selectedPointerId, setSelectedPointerId] = useState<string>(
    pointers[0]?.pointerId || 'PTR-ROOT-01'
  );

  const allocations = computeResourceAllocationAndEviction(workloads);
  const reviewReport = runAutonomousSelfReviewAndGapAnalysis(
    workloads,
    pointers,
    earlyWarnings,
    openLoops
  );

  const selectedPointer =
    pointers.find((p) => p.pointerId === selectedPointerId) || pointers[0];

  return (
    <div className="space-y-8">
      {/* Section 01: Executive BLUF Super-View & Autonomous Self-Review Header */}
      <section className="bg-slate-900 dark:bg-slate-900 text-white rounded-xl border border-slate-800 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 pb-6 border-b border-slate-800">
          <div className="space-y-2 max-w-3xl">
            <div className="text-[11px] font-mono uppercase tracking-widest text-emerald-400">
              FOUNDER SUPER-VIEW · REAL-TIME RESEARCH, ML & PROOF-OF-YIELD GOVERNANCE
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight font-display text-white">
              Done Means Proof of Yield — Else Zero Resources & Platform Eviction
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed">
              {reviewReport.executiveBlufSummary}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={onRunResearchDagPass}
              className="px-4 py-2.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 transition-colors cursor-pointer whitespace-nowrap"
            >
              Execute GPT-Researcher + ML Pass
            </button>
            <button
              type="button"
              onClick={onCloseAllLoopsAndWarnings}
              className="px-4 py-2.5 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition-colors cursor-pointer whitespace-nowrap"
            >
              Close All Open Loops & Mitigate Risks
            </button>
          </div>
        </div>

        {/* 4 Key KPI Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-6">
          <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">
              Platform Congruence & Loop Hygiene
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-emerald-400">
              {reviewReport.overallPlatformCongruencePercent.toFixed(1)}%
            </div>
            <div className="mt-1 text-xs text-slate-400 font-mono tabular-nums">
              {reviewReport.closedLoopsCount}/{ openLoops.length } Loops Closed ·{' '}
              {earlyWarnings.filter((w) => w.mitigated).length}/{earlyWarnings.length} Risks Mitigated
            </div>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">
              Compute Reclaimed from Evictions
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-white">
              {reviewReport.reclaimedCpuMillicores}m CPU
            </div>
            <div className="mt-1 text-xs text-emerald-400 font-mono tabular-nums">
              +{reviewReport.reclaimedMemoryMb} MB RAM shifted to Prime ML
            </div>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">
              AGENTS.md Context Bloat Cut
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-sky-400">
              -{reviewReport.agentsMdTokenReductionPercent.toFixed(1)}%
            </div>
            <div className="mt-1 text-xs text-slate-400 font-mono tabular-nums">
              {reviewReport.activeRootAgentsMdLines} Lines Root Index · Private GitHub Synced
            </div>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">
              Active vs. Evicted Workloads
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-amber-400">
              {reviewReport.activePlatformWorkloadsCount} Active /{' '}
              {reviewReport.evictedOrDrainingWorkloadsCount} Evicted
            </div>
            <div className="mt-1 text-xs text-slate-400 font-mono tabular-nums">
              Zero Proof = 0% Compute Allocation
            </div>
          </div>
        </div>

        {/* Autonomous Self-Review Recommendations Strip */}
        <div className="mt-6 pt-5 border-t border-slate-800">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2.5">
            AUTONOMOUS SELF-REVIEW · PROACTIVE SUGGESTIONS TO FOUNDER (TONE CONTRACT: INSTITUTIONAL BLUF)
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {reviewReport.founderRecommendations.map((rec, idx) => (
              <div
                key={idx}
                className="bg-slate-950/60 border border-slate-800/90 rounded-lg p-3.5 text-xs text-slate-200 leading-relaxed"
              >
                <span className="font-mono font-semibold text-emerald-400 mr-1.5">
                  0{idx + 1}.
                </span>
                {rec}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 02: World-Class Visual Telemetry Canvas (2-Column Grid) */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Left Visual Card: Upgraded GPT-Researcher + Conformal ML Multi-Agent DAG */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col justify-start space-y-5">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
                01. DAY-0 RESEARCH, ML & DATA SCIENCE ARCHITECTURE
              </span>
              <span className="text-xs font-mono text-emerald-700 dark:text-emerald-400 tabular-nums shrink-0">
                PRT-RES-DAG-901 · 965ms
              </span>
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white font-display">
              Protocol-Bound GPT-Researcher & Conformal ML DAG
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Upgrades standard GPT Researcher (Planner → Parallel Executor → Publisher) by inserting a mandatory Rust Conformal Proof & Citation Verifier gate and binding every sub-query to an explicit Expected Yield target.
            </p>
          </div>

          {/* Bespoke SVG DAG Diagram */}
          <div className="rounded-lg bg-slate-950 border border-slate-800 p-4">
            <svg
              viewBox="0 0 600 185"
              className="w-full h-auto"
              role="img"
              aria-label="GPT-Researcher and Conformal ML Directed Acyclic Graph"
            >
              {/* Connecting DAG Flow Lines */}
              <path
                d="M 115 92 L 175 45 M 115 92 L 175 92 M 115 92 L 175 139"
                stroke="#38bdf8"
                strokeWidth="1.75"
                fill="none"
              />
              <path
                d="M 305 45 L 360 92 M 305 92 L 360 92 M 305 139 L 360 92"
                stroke="#10b981"
                strokeWidth="1.75"
                fill="none"
              />
              <path
                d="M 465 92 L 500 92"
                stroke="#f59e0b"
                strokeWidth="2"
                fill="none"
              />

              {/* Stage 1: Planner Node */}
              <rect
                x="12"
                y="56"
                width="103"
                height="72"
                rx="6"
                fill="#0f172a"
                stroke="#38bdf8"
                strokeWidth="1.5"
              />
              <text x="22" y="76" fill="#38bdf8" fontSize="9" fontFamily="monospace">
                01. PLANNER
              </text>
              <text x="22" y="93" fill="#f8fafc" fontSize="10" fontWeight="bold">
                Hypothesis
              </text>
              <text x="22" y="107" fill="#94a3b8" fontSize="8.5" fontFamily="monospace">
                1 → 8 Queries
              </text>
              <text x="22" y="120" fill="#34d399" fontSize="8.5" fontFamily="monospace">
                Yield Target Set
              </text>

              {/* Stage 2: Parallel Executor Swarm (3 Parallel Lanes) */}
              <rect
                x="175"
                y="20"
                width="130"
                height="46"
                rx="5"
                fill="#0f172a"
                stroke="#64748b"
                strokeWidth="1.2"
              />
              <text x="184" y="37" fill="#e2e8f0" fontSize="9.5" fontWeight="bold">
                Tokio Web & Registry
              </text>
              <text x="184" y="53" fill="#94a3b8" fontSize="8.5" fontFamily="monospace">
                County Title & Plat Diffs
              </text>

              <rect
                x="175"
                y="70"
                width="130"
                height="46"
                rx="5"
                fill="#0f172a"
                stroke="#38bdf8"
                strokeWidth="1.5"
              />
              <text x="184" y="87" fill="#e2e8f0" fontSize="9.5" fontWeight="bold">
                Polars + Burn ML
              </text>
              <text x="184" y="103" fill="#38bdf8" fontSize="8.5" fontFamily="monospace">
                Conformal Quantile NOI
              </text>

              <rect
                x="175"
                y="120"
                width="130"
                height="46"
                rx="5"
                fill="#0f172a"
                stroke="#64748b"
                strokeWidth="1.2"
              />
              <text x="184" y="137" fill="#e2e8f0" fontSize="9.5" fontWeight="bold">
                Survival Hazard DS
              </text>
              <text x="184" y="153" fill="#94a3b8" fontSize="8.5" fontFamily="monospace">
                14d Default Forecaster
              </text>

              {/* Stage 3: Conformal Proof Verifier */}
              <rect
                x="360"
                y="52"
                width="105"
                height="80"
                rx="6"
                fill="#022c22"
                stroke="#10b981"
                strokeWidth="1.5"
              />
              <text x="370" y="72" fill="#34d399" fontSize="9" fontFamily="monospace">
                03. VERIFIER
              </text>
              <text x="370" y="89" fill="#ffffff" fontSize="10" fontWeight="bold">
                Conformal Gate
              </text>
              <text x="370" y="104" fill="#a7f3d0" fontSize="8.5" fontFamily="monospace">
                sha256 Provenance
              </text>
              <text x="370" y="119" fill="#34d399" fontSize="8.5" fontFamily="monospace">
                0 Hallucinations
              </text>

              {/* Stage 4: Publisher Outbox */}
              <rect
                x="500"
                y="56"
                width="88"
                height="72"
                rx="6"
                fill="#0f172a"
                stroke="#f59e0b"
                strokeWidth="1.5"
              />
              <text x="508" y="76" fill="#fbbf24" fontSize="9" fontFamily="monospace">
                04. OUTBOX
              </text>
              <text x="508" y="93" fill="#ffffff" fontSize="10" fontWeight="bold">
                BLUF Brief
              </text>
              <text x="508" y="108" fill="#cbd5e1" fontSize="8.5" fontFamily="monospace">
                105.6% Yield
              </text>
              <text x="508" y="121" fill="#fbbf24" fontSize="8.5" fontFamily="monospace">
                Atomic Flush
              </text>
            </svg>
          </div>

          {/* 4 DAG Stage Detail Rows */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {dagNodes.map((node) => (
              <div
                key={node.nodeId}
                className="rounded-lg border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/70 dark:bg-slate-950/50"
              >
                <div className="flex items-center justify-between gap-2 text-xs font-mono">
                  <span className="font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                    0{node.stageOrder}. {node.nodeId}
                  </span>
                  <span className="text-emerald-700 dark:text-emerald-400 tabular-nums whitespace-nowrap">
                    {node.verifiedYieldPercent.toFixed(1)}% · {node.latencyMs}ms
                  </span>
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
                  {node.role}
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {node.gptResearcherEvolution}
                </p>
                <div className="mt-2 pt-2 border-t border-slate-200/80 dark:border-slate-800 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  Mistake Avoided: {node.legacyMistakeAvoided}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Visual Card: Proof-of-Yield Resource Eviction & Reallocation Telemetry */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col justify-start space-y-5">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
                02. MANDATORY FIRST-CLASS PRINCIPLE · RESOURCE SCHEDULER
              </span>
              <span className="text-xs font-mono text-amber-700 dark:text-amber-400 tabular-nums shrink-0">
                Zero Proof = 0% Quota
              </span>
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white font-display">
              Proof-of-Yield Compute Allocation & Graduated Eviction
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Every workload must continuously prove economic yield (Actual ÷ Expected Outcome) with a sha256 artifact. Unverified or sub-target workloads are throttled and gradually shifted off the platform.
            </p>
          </div>

          {/* Bespoke SVG Resource Eviction vs Expansion Telemetry */}
          <div className="rounded-lg bg-slate-950 border border-slate-800 p-4">
            <svg
              viewBox="0 0 600 185"
              className="w-full h-auto"
              role="img"
              aria-label="Proof-of-Yield Resource Allocation and Eviction Bars"
            >
              <text x="16" y="22" fill="#94a3b8" fontSize="9.5" fontFamily="monospace">
                WORKLOAD ID · PROOF-OF-YIELD STANDING vs. ALLOCATED COMPUTE QUOTA
              </text>

              {allocations.map((dec, idx) => {
                const y = 38 + idx * 29;
                const barWidth = Math.max(6, Math.round((dec.allocationMultiplierPercent / 140) * 260));
                const barColor =
                  dec.status === 'PRIME_EXPANSION'
                    ? '#10b981'
                    : dec.status === 'SUSTAINED_BASELINE'
                    ? '#38bdf8'
                    : dec.status === 'THROTTLED_PROBATION'
                    ? '#f59e0b'
                    : '#ef4444';

                return (
                  <g key={dec.workloadId}>
                    <text
                      x="16"
                      y={y + 13}
                      fill="#e2e8f0"
                      fontSize="9.5"
                      fontFamily="monospace"
                    >
                      {dec.workloadId} ({dec.yieldPercent.toFixed(1)}%)
                    </text>
                    <rect
                      x="165"
                      y={y + 2}
                      width="265"
                      height="14"
                      rx="3"
                      fill="#1e293b"
                    />
                    <rect
                      x="165"
                      y={y + 2}
                      width={barWidth}
                      height="14"
                      rx="3"
                      fill={barColor}
                    />
                    <text
                      x="440"
                      y={y + 13}
                      fill={barColor}
                      fontSize="9"
                      fontFamily="monospace"
                    >
                      {dec.allocationMultiplierPercent}% ({dec.allocatedCpuMillicores}m)
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* 4-Stage Graduated Eviction Policy Ladder (Balanced 2x2 Grid) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/70 dark:bg-slate-950/50">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                  01. PRIME_EXPANSION
                </span>
                <span className="text-emerald-700 dark:text-emerald-400 tabular-nums">
                  135% Quota
                </span>
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
                Surplus Yield + sha256 Proof
              </div>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Granted automatically when Yield ≥ 102% with verified sha256 proof. Absorbs CPU and memory reclaimed from evicted workloads.
              </p>
              <div className="mt-2 pt-2 border-t border-slate-200/80 dark:border-slate-800 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                Standing: Priority Tokio Compute Pool
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/70 dark:bg-slate-950/50">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-sky-700 dark:text-sky-400">
                  02. SUSTAINED_BASELINE
                </span>
                <span className="text-sky-700 dark:text-sky-400 tabular-nums">
                  100% Quota
                </span>
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
                On-Target Yield (95%–101.9%)
              </div>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Retains full baseline compute allocation as long as cryptographic proof tokens are attached on every state transition.
              </p>
              <div className="mt-2 pt-2 border-t border-slate-200/80 dark:border-slate-800 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                Standing: Standard Headless Worker Slot
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/70 dark:bg-slate-950/50">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-amber-700 dark:text-amber-400">
                  03. THROTTLED_PROBATION
                </span>
                <span className="text-amber-700 dark:text-amber-400 tabular-nums">
                  45% → 15% Quota
                </span>
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
                Sub-95% Yield or Deficit Epoch
              </div>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                1 deficit epoch throttles compute to 45%; 2 epochs initiates Graduated Drain (15% quota) and checkpoints state to cold storage.
              </p>
              <div className="mt-2 pt-2 border-t border-slate-200/80 dark:border-slate-800 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                Standing: Capped Pending Remediation Proof
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/70 dark:bg-slate-950/50">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-rose-700 dark:text-rose-400">
                  04. EVICTED_OFF_PLATFORM
                </span>
                <span className="text-rose-700 dark:text-rose-400 tabular-nums">
                  0% Quota
                </span>
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
                Missing Proof or Persistent Deficit
              </div>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Workloads that emit prose without a cryptographic Proof of Yield or fail 3 epochs are evicted off the platform (0m CPU / 0MB RAM).
              </p>
              <div className="mt-2 pt-2 border-t border-slate-200/80 dark:border-slate-800 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                Standing: Shifted Off Platform · Compute Reclaimed
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 03: Interactive Platform Resource Standing & Eviction Ledger Table */}
      <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
              03. REAL-TIME WORKLOAD STANDING · DONE MEANS PROOF OF YIELD
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white font-display">
              Platform Resource Allocation & Graduated Eviction Ledger
            </h2>
          </div>
          <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
            Total Reclaimed: {reviewReport.reclaimedCpuMillicores}m CPU · {reviewReport.reclaimedMemoryMb} MB RAM
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400">
                <th className="py-3 pr-4">Workload & Category</th>
                <th className="py-3 px-4">Expected vs. Actual</th>
                <th className="py-3 px-4">Proof of Yield</th>
                <th className="py-3 px-4">Platform Standing & Quota</th>
                <th className="py-3 pl-4 text-right">Founder Override</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {workloads.map((w) => {
                const dec = allocations.find((a) => a.workloadId === w.id)!;
                return (
                  <tr key={w.id} className="align-top">
                    <td className="py-4 pr-4">
                      <div className="font-mono font-semibold text-slate-900 dark:text-white">
                        {w.id} · {w.protocolId}
                      </div>
                      <div className="font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                        {w.name}
                      </div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        {w.category}
                      </div>
                    </td>

                    <td className="py-4 px-4 font-mono tabular-nums">
                      <div className="font-semibold text-slate-900 dark:text-white">
                        {dec.yieldPercent.toFixed(1)}% Yield
                      </div>
                      <div className="text-slate-600 dark:text-slate-400 mt-0.5">
                        Actual: {w.actualOutcome} {w.unit} / Expected: {w.expectedOutcome} {w.unit}
                      </div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        Deficit Epochs: {w.consecutiveDeficitEpochs}
                      </div>
                    </td>

                    <td className="py-4 px-4">
                      <div
                        className={`font-mono font-semibold ${
                          w.proofVerified
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : 'text-rose-700 dark:text-rose-400'
                        }`}
                      >
                        {w.proofVerified ? 'PROOF VERIFIED' : 'MISSING PROOF TOKEN'}
                      </div>
                      <div className="font-mono text-[11px] text-slate-600 dark:text-slate-400 mt-0.5 max-w-xs break-words">
                        {w.proofOfYieldToken}
                      </div>
                    </td>

                    <td className="py-4 px-4">
                      <div
                        className={`font-mono font-semibold ${
                          dec.status === 'PRIME_EXPANSION'
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : dec.status === 'SUSTAINED_BASELINE'
                            ? 'text-sky-700 dark:text-sky-400'
                            : dec.status === 'THROTTLED_PROBATION'
                            ? 'text-amber-700 dark:text-amber-400'
                            : 'text-rose-700 dark:text-rose-400'
                        }`}
                      >
                        {dec.status} ({dec.allocationMultiplierPercent}% Quota)
                      </div>
                      <div className="font-mono tabular-nums text-slate-700 dark:text-slate-300 mt-0.5">
                        {dec.allocatedCpuMillicores}m CPU · {dec.allocatedMemoryMb} MB RAM
                      </div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5 max-w-xs">
                        {dec.platformStandingRationale}
                      </div>
                    </td>

                    <td className="py-4 pl-4 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-2">
                        {dec.allocationMultiplierPercent < 100 && (
                          <button
                            type="button"
                            onClick={() => onRemediateWorkloadProof(w.id)}
                            className="px-2.5 py-1.5 rounded text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors cursor-pointer"
                          >
                            Seal Proof & Restore
                          </button>
                        )}
                        {dec.status !== 'EVICTED_OFF_PLATFORM' && (
                          <button
                            type="button"
                            onClick={() => onEvictWorkloadNow(w.id)}
                            className="px-2.5 py-1.5 rounded text-xs font-medium border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
                          >
                            Evict (0%)
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 04: Predictive Early-Warning Engine & Open-Loop Process Gap Detector */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Left: Predictive Early-Warning Insights (Seeing Problems Before They Happen) */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col justify-start space-y-5">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
                04. PREDICTIVE EARLY-WARNING INTELLIGENCE
              </span>
              <span className="text-xs font-mono text-slate-600 dark:text-slate-400 tabular-nums">
                Continuous Multi-Stream Fusion
              </span>
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white font-display">
              See Problems Before They Happen
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Continuously fuses county registries, BLS inflation feeds, Polars lease tensors, and state-machine logs to forecast yield bottlenecks hours or days before they occur.
            </p>
          </div>

          <div className="space-y-3">
            {earlyWarnings.map((warn) => (
              <div
                key={warn.id}
                className="rounded-lg border border-slate-200 dark:border-slate-800 p-4 bg-slate-50/70 dark:bg-slate-950/50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {warn.id} · Horizon: T-{warn.horizonHours}h
                  </span>
                  <span
                    className={`font-semibold tabular-nums ${
                      warn.mitigated
                        ? 'text-emerald-700 dark:text-emerald-400'
                        : 'text-amber-700 dark:text-amber-400'
                    }`}
                  >
                    {warn.mitigated
                      ? 'MITIGATED PROACTIVELY'
                      : `Predicted Yield Risk: ${warn.expectedYieldRiskPercent}% (${warn.confidencePercent}% Conf)`}
                  </span>
                </div>

                <div className="mt-1.5 text-sm font-semibold text-slate-900 dark:text-white">
                  {warn.title}
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {warn.predictedFailureIfIgnored}
                </p>
                <div className="mt-2 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  Fused Telemetry: {warn.dataSourceFused}
                </div>

                <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs font-mono text-slate-700 dark:text-slate-300">
                    Action: {warn.preventiveProtocolAction}
                  </span>
                  {!warn.mitigated && (
                    <button
                      type="button"
                      onClick={() => onMitigateEarlyWarning(warn.id)}
                      className="px-3 py-1.5 rounded text-xs font-semibold bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-white transition-colors cursor-pointer shrink-0"
                    >
                      Execute Preventive Protocol
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: End-to-End Open-Loop & Process Gap Detector */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col justify-start space-y-5">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
                05. END-TO-END PROCESS GAP & OPEN-LOOP DETECTOR
              </span>
              <span className="text-xs font-mono text-emerald-700 dark:text-emerald-400 tabular-nums">
                {reviewReport.openLoopsCount} Open · {reviewReport.closedLoopsCount} Closed
              </span>
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white font-display">
              Identify & Close Open Loops Across the Spine
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Automatically audits every stage of the 7-Stage Spine (`SPINE-INBOX` through `SPINE-YIELD`) to surface unsealed proofs, unconsumed inbox events, and unreviewed yield surpluses.
            </p>
          </div>

          <div className="space-y-3">
            {openLoops.map((loop) => (
              <div
                key={loop.id}
                className="rounded-lg border border-slate-200 dark:border-slate-800 p-4 bg-slate-50/70 dark:bg-slate-950/50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {loop.id} · {loop.spineStageId} · {loop.loopType}
                  </span>
                  <span
                    className={`font-semibold tabular-nums ${
                      loop.status === 'CLOSED_VERIFIED'
                        ? 'text-emerald-700 dark:text-emerald-400'
                        : 'text-rose-700 dark:text-rose-400'
                    }`}
                  >
                    {loop.status === 'CLOSED_VERIFIED'
                      ? 'CLOSED & VERIFIED'
                      : `OPEN LOOP (-${loop.yieldDragPercent}% Yield Drag)`}
                  </span>
                </div>

                <div className="mt-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Target: {loop.sourceEntityId}
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {loop.gapDescription}
                </p>

                <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs font-mono text-slate-700 dark:text-slate-300">
                    Resolution: {loop.resolutionProtocolAction}
                  </span>
                  {loop.status === 'OPEN_LOOP' && (
                    <button
                      type="button"
                      onClick={() => onCloseOpenLoop(loop.id)}
                      className="px-3 py-1.5 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors cursor-pointer shrink-0"
                    >
                      Close Open Loop
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 05: AGENTS.md Context Bloat Eradication & Private GitHub Memory Ledger */}
      <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
              06. AGENTS.MD CONTEXT BLOAT CLEANUP & PRIVATE GITHUB HIERARCHICAL MEMORY
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white font-display">
              Mandatory Root Pointer Index (`AGENTS.md` v4.0) & Private GitHub Memory Sync
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
              Replaced the chaotic 1,840-line monolithic `AGENTS.md` (24,200 tokens of stale stack traces and conflicting rules) with a 64-line Root Pointer Index synced to `git@github.com:olat-estate/private-memory-ledger.git`. Every specialist agent loads only the exact scoped memory pointer needed for its active protocol.
            </p>
          </div>
          <div className="text-xs font-mono text-emerald-700 dark:text-emerald-400 tabular-nums shrink-0">
            24,200 Legacy Tokens → 1,045 Pointer Tokens (-95.7% Bloat)
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Pointer Table */}
          <div className="space-y-3">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">
              CLICK A POINTER URI TO INSPECT MANDATORY AGENT CONSTITUTION RULE
            </div>
            {pointers.map((ptr) => {
              const isSelected = ptr.pointerId === selectedPointer.pointerId;
              return (
                <button
                  key={ptr.pointerId}
                  type="button"
                  onClick={() => setSelectedPointerId(ptr.pointerId)}
                  className={`w-full text-left rounded-lg border p-3.5 transition-colors cursor-pointer ${
                    isSelected
                      ? 'border-slate-900 dark:border-slate-100 bg-slate-50 dark:bg-slate-800/80'
                      : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50/60 dark:hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {ptr.pointerId} · {ptr.uri}
                    </span>
                    <span className="text-emerald-700 dark:text-emerald-400 tabular-nums">
                      {ptr.lineCount} lines ({ptr.tokenFootprint} tok vs {ptr.legacyBloatedTokens} legacy)
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                    {ptr.mandatoryRuleSummary}
                  </div>
                  <div className="mt-1.5 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                    Domain: {ptr.domain} · Private GitHub Commit: {ptr.gitCommitSha}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right: Clean Root AGENTS.md v4.0 File Preview */}
          <div className="rounded-lg bg-slate-950 border border-slate-800 p-5 text-slate-100 font-mono text-xs flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-[11px] text-slate-400">
                <span>/AGENTS.md (v4.0 Root Pointer Index · 64 Lines Max)</span>
                <span className="text-emerald-400">SYNCED: olat-estate/private-memory-ledger</span>
              </div>
              <pre className="mt-4 text-[11px] leading-relaxed text-slate-200 whitespace-pre-wrap break-words">
{`# OLAT ESTATE — MANDATORY AGENT CONSTITUTION (ROOT POINTER INDEX)
# Zero Monolithic Context Bloat. Progressive Disclosure via Private GitHub Memory.

[01. CONGRUENT 7-STAGE SPINE]
-> Pointer: mem://constitution/spine-invariants.md (git@olat-memory:94a8e1c)
Rule: All work traverses SPINE-INBOX -> SPINE-REPLAY -> SPINE-CLAIM -> SPINE-INTENT -> SPINE-PROOF -> SPINE-OUTBOX -> SPINE-YIELD.

[02. FIRST-CLASS PRINCIPLE: DONE MEANS PROOF OF YIELD]
-> Pointer: mem://protocols/done-means-proof-of-yield.md (git@olat-memory:3f02b7d)
Rule: Every output requires a sha256 Proof Token + Actual/Expected Yield >= Gate. Unverified workloads are throttled and evicted to 0% compute.

[03. WORLD-CLASS RESEARCH & CONFORMAL ML DAG]
-> Pointer: mem://research/gpt-researcher-conformal-dag.md (git@olat-memory:8c19d4a)
Rule: Execute Planner -> Parallel Tokio/Polars Swarm -> Conformal Verifier -> BLUF Outbox.

[04. PRIVATE GITHUB EPISODIC & SEMANTIC MEMORY]
-> Pointer: mem://github-private/episodic-checkpoint-index.bin (git@olat-memory:7b44e90)
Rule: Hydrate state via Fold(State_0, EventLog). Zero local laptop state.

[05. EXECUTIVE TONE & SELF-REVIEW PRESENTATION CONTRACT]
-> Pointer: mem://tone/founder-bluf-communication-contract.md (git@olat-memory:1e88c3f)
Rule: Lead with BLUF metric delta, verified sha256 proof, predictive horizon risk, and single recommended Founder action.`}
              </pre>
            </div>

            <div className="pt-3 border-t border-slate-800 text-[11px] text-emerald-400">
              Active Inspector ({selectedPointer.uri}): {selectedPointer.mandatoryRuleSummary}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
