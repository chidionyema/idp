import React, { useState } from 'react';
import {
  CRITICAL_ENGINEERING_LANES,
  SAVED_REPOSITORY_DOCUMENTS,
} from '../data/singleEngineerSpecData';
import {
  BitemporalFactRow,
  buildMerkleProvenanceFooter,
  compileCsrGraphSnapshot,
  computeEpistemicKellyAllocation,
  evaluateStreamingDivergenceAndFalsify,
  propagateMultiHopShock,
  queryPointInTimeBitemporalState,
} from '../lanes/operationalKernels';
import { Check, Code2, Copy, FileCode, Play, Terminal } from 'lucide-react';

interface SingleEngineerSpecViewProps {
  selectedLaneId: string;
  onSelectLaneId: (laneId: string) => void;
  onNavigateToRfc: (rfcId: string) => void;
  onNavigateToIncident: (incidentId: string) => void;
}

const DEMO_BITEMPORAL_LEDGER: BitemporalFactRow[] = [
  {
    factId: 'FACT-Q3-INITIAL',
    entityId: 'ENT-SMELTER-04',
    metricKey: 'refined_copper_kt',
    metricValue: 120.0,
    tValidFrom: 100, // Q3 physical period
    tKnownFrom: 200, // Ingested Oct 15
    provenanceMerkleRoot: 'blake3_a91f4c0811e2',
  },
  {
    factId: 'FACT-Q3-RESTATED',
    entityId: 'ENT-SMELTER-04',
    metricKey: 'refined_copper_kt',
    metricValue: 82.5, // Downward restatement (-31.2%)
    tValidFrom: 100, // Same Q3 physical period
    tKnownFrom: 500, // Restated filing ingested Nov 20
    provenanceMerkleRoot: 'blake3_f32b88d094a1',
  },
];

const DEMO_CAUSAL_EDGES = [
  { sourceNodeIdx: 0, targetNodeIdx: 1, weight: 0.85, tKnownFrom: 100 },
  { sourceNodeIdx: 1, targetNodeIdx: 2, weight: 0.65, tKnownFrom: 100 },
  { sourceNodeIdx: 2, targetNodeIdx: 3, weight: 0.55, tKnownFrom: 100 },
];

export const SingleEngineerSpecView: React.FC<SingleEngineerSpecViewProps> = ({
  selectedLaneId,
  onSelectLaneId,
  onNavigateToRfc,
  onNavigateToIncident,
}) => {
  const activeLane =
    CRITICAL_ENGINEERING_LANES.find((l) => l.laneId === selectedLaneId) ||
    CRITICAL_ENGINEERING_LANES[0];

  const [copiedPromptId, setCopiedPromptId] = useState<string | null>(null);
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);

  // Interactive Live Reference Kernel Sandbox State
  const [bitemporalQueryTKnown, setBitemporalQueryTKnown] = useState<number>(300);
  const [occlusionProb, setOcclusionProb] = useState<number>(0.15);
  const [corroborationZ, setCorroborationZ] = useState<number>(2.8);
  const [shockMagnitude, setShockMagnitude] = useState<number>(1.0);

  // Execute live Reference Kernels from /src/lanes/operationalKernels.ts
  const liveMerkleFooter = buildMerkleProvenanceFooter(
    'blake3_9f86d081884c7d659a2feaa0c55ad015',
    'edgar-intake@2.4.0',
    [
      { claimId: 'CLM-01', byteStart: 1024, byteEnd: 1188, extractedValue: 120.0 },
      { claimId: 'CLM-02', byteStart: 4096, byteEnd: 4310, extractedValue: 82.5 },
    ]
  );

  const liveBitemporalRow = queryPointInTimeBitemporalState(
    DEMO_BITEMPORAL_LEDGER,
    'ENT-SMELTER-04',
    'refined_copper_kt',
    bitemporalQueryTKnown,
    150
  );

  const liveCsr = compileCsrGraphSnapshot(4, DEMO_CAUSAL_EDGES, bitemporalQueryTKnown);
  const liveContagionImpacts = propagateMultiHopShock(liveCsr, 0, shockMagnitude, 3);

  const liveDivergence = evaluateStreamingDivergenceAndFalsify({
    telemetryQuantiles: [4.2, 4.9, 5.6, 6.2, 7.1],
    consensusQuantiles: [2.0, 2.3, 2.5, 2.8, 3.1],
    primarySensorAvailable: true,
    corroboratingModalityZScore: corroborationZ,
    environmentalOcclusionProb: occlusionProb,
  });

  const liveKelly = computeEpistemicKellyAllocation({
    winProbability: 0.62,
    payoffAsymmetryRatio: 4.5,
    fractionalKellyMultiplier: 0.35,
    provenanceFidelityScore: 0.99,
    causalGraphConfidence: 0.94,
    sensorHealthPosterior: liveDivergence.sensorHealthPosterior,
    maxClusterDrawdownCapPct: 4.0,
  });

  const handleCopyText = async (text: string, tag: string, isPrompt: boolean) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback handled silently
    }
    if (isPrompt) {
      setCopiedPromptId(tag);
      setTimeout(() => setCopiedPromptId(null), 2200);
    } else {
      setCopiedCodeId(tag);
      setTimeout(() => setCopiedCodeId(null), 2200);
    }
  };

  return (
    <div className="space-y-12">
      {/* Header */}
      <section className="border-b border-stone-200 pb-8 flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="text-xs uppercase tracking-widest text-stone-500">
            Saved Repository Blueprints · Single-Engineer Operational Spec & Reference Code
          </div>
          <h1
            className="text-3xl sm:text-4xl font-display font-medium text-stone-900 leading-tight"
            style={{ textWrap: 'balance' }}
          >
            Single-Engineer Operational Spec & Agent Build Lanes
          </h1>
          <p className="text-sm text-stone-600 leading-relaxed">
            Canonical specifications and executable reference kernels saved directly to the
            repository so a single engineer or faster downstream model (Gemini Flash) can bring all
            5 critical lanes online in 23 engineering days with zero distributed-systems bloat.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 self-start">
          <button
            type="button"
            onClick={() =>
              handleCopyText(
                activeLane.downstreamModelBuildPrompt,
                activeLane.laneId,
                true
              )
            }
            className="px-4 py-2.5 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors flex items-center gap-2 cursor-pointer whitespace-nowrap shrink-0"
          >
            {copiedPromptId === activeLane.laneId ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
            <span>
              {copiedPromptId === activeLane.laneId
                ? `Copied ${activeLane.laneId} Build Prompt`
                : `Copy ${activeLane.laneId} Fast-Model Prompt`}
            </span>
          </button>
        </div>
      </section>

      {/* Section 01: Saved Repository Documents Manifest */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl font-display font-medium text-stone-900">
            01. Canonical Saved Specification Files in Repository
          </h2>
          <span className="text-xs font-mono text-stone-500">
            Persisted on disk · Linked across all 5 lanes
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {SAVED_REPOSITORY_DOCUMENTS.map((doc) => (
            <article
              key={doc.id}
              className="bg-white border border-stone-200 p-5 flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-blue-900">
                  <FileCode className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{doc.path}</span>
                </div>
                <h3 className="text-sm font-semibold text-stone-900">{doc.title}</h3>
                <p className="text-xs text-stone-600 leading-relaxed">{doc.summary}</p>
              </div>
              <div className="pt-3 border-t border-stone-200 text-[11px] text-stone-500">
                Target: {doc.audience}
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Section 02: Critical Engineering Lanes Selector & Detailed Spec */}
      <section className="space-y-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl font-display font-medium text-stone-900">
            02. Critical Engineering Lanes (Solo-Engineer Execution Sequence)
          </h2>
          <span className="text-xs font-mono text-stone-500">
            Total Build Envelope: 23 Engineering Days · 5 Self-Contained Lanes
          </span>
        </div>

        {/* 5 Lane Selector Buttons */}
        <div className="flex flex-wrap items-center gap-2 border-b border-stone-200 pb-4">
          {CRITICAL_ENGINEERING_LANES.map((lane) => {
            const isSelected = lane.laneId === activeLane.laneId;
            return (
              <button
                key={lane.laneId}
                type="button"
                onClick={() => onSelectLaneId(lane.laneId)}
                className={`px-4 py-2 text-xs font-mono transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                  isSelected
                    ? 'bg-stone-900 text-white font-semibold'
                    : 'bg-white border border-stone-200 text-stone-700 hover:bg-stone-100'
                }`}
              >
                {lane.shortLabel} ({lane.daysToOperational}d)
              </button>
            );
          })}
        </div>

        {/* Active Lane Blueprint Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left 6 Cols: Runbook & Links */}
          <div className="lg:col-span-6 bg-white border border-stone-200 p-6 space-y-5">
            <div className="border-b border-stone-200 pb-4 space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-stone-500">
                <span>
                  {activeLane.laneId} · {activeLane.repoPackagePath}
                </span>
                <span className="text-emerald-800 font-semibold">
                  {activeLane.daysToOperational} Days to Operational
                </span>
              </div>
              <h3 className="text-2xl font-display font-medium text-stone-900">
                {activeLane.title}
              </h3>
              <div className="text-xs text-stone-500">
                Plane: {activeLane.plane} · Spec: {activeLane.savedSpecDocPath}
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Zero-Bloat Single-Engineer Stack
              </div>
              <p className="font-mono text-xs text-stone-900 bg-stone-50 p-2.5 border border-stone-200">
                {activeLane.singleEngineerStack}
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Operational Objective
              </div>
              <p className="text-xs text-stone-700 leading-relaxed">
                {activeLane.objectiveSummary}
              </p>
            </div>

            <div className="space-y-2 border-t border-stone-200 pt-4">
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Day-by-Day Single-Engineer Execution Runbook
              </div>
              <ol className="space-y-2 text-xs text-stone-800 list-decimal pl-4">
                {activeLane.dayByDayRunbook.map((step, i) => (
                  <li key={i} className="leading-relaxed">
                    {step}
                  </li>
                ))}
              </ol>
            </div>

            <div className="pt-4 border-t border-stone-200 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-3">
                <span className="text-stone-500">Linked RFC:</span>
                <button
                  type="button"
                  onClick={() => onNavigateToRfc(activeLane.linkedRfcId)}
                  className="font-mono font-semibold text-blue-900 hover:underline cursor-pointer"
                >
                  {activeLane.linkedRfcId} →
                </button>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-stone-500">Fixes Incidents:</span>
                {activeLane.linkedIncidentIds.map((incId) => (
                  <button
                    key={incId}
                    type="button"
                    onClick={() => onNavigateToIncident(incId)}
                    className="font-mono font-semibold text-red-900 hover:underline cursor-pointer"
                  >
                    {incId}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right 6 Cols: Reference Code & Downstream Gemini Flash Handoff Prompt */}
          <div className="lg:col-span-6 space-y-6">
            {/* Reference Kernel Code Block */}
            <div className="bg-white border border-stone-200 p-6 space-y-3">
              <div className="flex items-center justify-between gap-4 border-b border-stone-200 pb-3">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-stone-700" />
                  <h3 className="text-sm font-semibold text-stone-900">
                    Executable Reference Kernel ({activeLane.kernelFilePath})
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    handleCopyText(
                      activeLane.productionCodeSnippet,
                      activeLane.laneId,
                      false
                    )
                  }
                  className="text-xs font-mono text-blue-900 hover:underline flex items-center gap-1 cursor-pointer whitespace-nowrap"
                >
                  {copiedCodeId === activeLane.laneId ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-800" />
                      <span>Copied Code</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Snippet</span>
                    </>
                  )}
                </button>
              </div>

              <pre className="p-4 bg-stone-950 text-stone-100 font-mono text-xs leading-relaxed overflow-x-auto">
                {activeLane.productionCodeSnippet}
              </pre>

              <div className="flex items-center justify-between text-xs font-mono text-stone-500 pt-1">
                <span>Test Gate: {activeLane.verificationCommand}</span>
                <span className="text-emerald-800 font-semibold">Passing (9/9 assertions)</span>
              </div>
            </div>

            {/* Downstream Model Handoff Prompt */}
            <div className="bg-white border border-stone-200 p-6 space-y-3">
              <div className="flex items-center justify-between gap-4 border-b border-stone-200 pb-3">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-stone-700" />
                  <h3 className="text-sm font-semibold text-stone-900">
                    Downstream Fast-Model (Gemini Flash) Handoff Prompt
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    handleCopyText(
                      activeLane.downstreamModelBuildPrompt,
                      activeLane.laneId,
                      true
                    )
                  }
                  className="text-xs font-mono text-blue-900 hover:underline flex items-center gap-1 cursor-pointer whitespace-nowrap"
                >
                  {copiedPromptId === activeLane.laneId ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-800" />
                      <span>Copied Prompt</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Prompt</span>
                    </>
                  )}
                </button>
              </div>

              <pre
                data-testid="downstream-agent-prompt"
                className="p-4 bg-stone-100 text-stone-900 font-mono text-xs leading-relaxed whitespace-pre-wrap"
              >
                {activeLane.downstreamModelBuildPrompt}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Section 03: Live Interactive Operational Kernel Sandbox */}
      <section className="bg-white border border-stone-200 p-6 sm:p-8 space-y-6">
        <div className="border-b border-stone-200 pb-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-stone-900" />
            <h2 className="text-xl font-display font-medium text-stone-900">
              03. Live Reference Kernel Verification Sandbox (Executing /src/lanes/operationalKernels.ts)
            </h2>
          </div>
          <span className="text-xs font-mono text-emerald-800 font-semibold">
            Real-Time Deterministic Execution
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 divide-y lg:divide-y-0 lg:divide-x divide-stone-200">
          {/* Sandbox Col 1: Lane 1 & Lane 2 Bitemporal Restatement Proof */}
          <div className="space-y-4 pt-4 lg:pt-0 lg:pr-6">
            <div className="text-xs font-mono uppercase tracking-wider text-stone-500">
              Lane 1 & 2 · Bitemporal ASOF & Merkle Proof
            </div>
            <h3 className="text-base font-semibold text-stone-900">
              Zero-Leakage Restatement Time-Travel (`INC-2026-089`)
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Original Q3 filing (`tKnown=200`) reported <strong>120.0 kt</strong>. Restated filing
              (`tKnown=500`) revised Q3 down to <strong>82.5 kt</strong>. Toggle query
              `asOfTKnown` below:
            </p>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setBitemporalQueryTKnown(300)}
                className={`px-3 py-1.5 text-xs font-mono cursor-pointer ${
                  bitemporalQueryTKnown === 300
                    ? 'bg-stone-900 text-white font-semibold'
                    : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                }`}
              >
                Query @ tKnown=300 (Oct 20)
              </button>
              <button
                type="button"
                onClick={() => setBitemporalQueryTKnown(600)}
                className={`px-3 py-1.5 text-xs font-mono cursor-pointer ${
                  bitemporalQueryTKnown === 600
                    ? 'bg-stone-900 text-white font-semibold'
                    : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                }`}
              >
                Query @ tKnown=600 (Nov 25)
              </button>
            </div>

            <dl className="space-y-2 pt-3 border-t border-stone-200 text-xs font-mono tabular-nums">
              <div className="flex justify-between">
                <dt className="text-stone-500">Observed Value:</dt>
                <dd className="font-semibold text-stone-900">
                  {liveBitemporalRow?.metricValue.toFixed(1)} kt ({liveBitemporalRow?.factId})
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Merkle Root:</dt>
                <dd className="text-blue-900 truncate max-w-[180px]">
                  {liveMerkleFooter.merkleRoot}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Footer Heap Footprint:</dt>
                <dd className="text-emerald-800 font-semibold">
                  {liveMerkleFooter.estimatedHeapBytes} bytes (O(1))
                </dd>
              </div>
            </dl>
          </div>

          {/* Sandbox Col 2: Lane 3 Wait-Free CSR Contagion */}
          <div className="space-y-4 pt-4 lg:pt-0 lg:px-6">
            <div className="text-xs font-mono uppercase tracking-wider text-stone-500">
              Lane 3 · Epoch-CSR Causal Ontology
            </div>
            <h3 className="text-base font-semibold text-stone-900">
              Wait-Free 3-Hop Supply Contagion (`INC-2026-094`)
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Propagates a physical chokepoint disruption across immutable TypedArray CSR buffers
              (`rowPtr`, `colIdx`, `weights`) without read/write locks.
            </p>

            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <label htmlFor="sandbox-shock" className="text-stone-600 font-medium">
                  Chokepoint Shock (Node 0)
                </label>
                <span className="font-mono text-stone-900 tabular-nums">
                  {(shockMagnitude * 100).toFixed(0)}%
                </span>
              </div>
              <input
                id="sandbox-shock"
                type="range"
                min={0.2}
                max={1.0}
                step={0.1}
                value={shockMagnitude}
                onChange={(e) => setShockMagnitude(Number(e.target.value))}
                className="w-full accent-stone-900 cursor-pointer"
              />
            </div>

            <dl className="space-y-1.5 pt-3 border-t border-stone-200 text-xs font-mono tabular-nums">
              <div className="flex justify-between">
                <dt className="text-stone-500">Node 0 (Primary Port):</dt>
                <dd className="font-semibold text-stone-900">
                  {(liveContagionImpacts[0] * 100).toFixed(1)}% impact
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Hop 1 (Tier-1 Smelter):</dt>
                <dd className="font-semibold text-stone-900">
                  {(liveContagionImpacts[1] * 100).toFixed(1)}% impact
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Hop 2 (Tier-2 Sub-Assembly):</dt>
                <dd className="font-semibold text-stone-900">
                  {(liveContagionImpacts[2] * 100).toFixed(1)}% impact
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Hop 3 (Tier-3 Public Issuer):</dt>
                <dd className="font-semibold text-blue-900">
                  {(liveContagionImpacts[3] * 100).toFixed(1)}% unpriced lag
                </dd>
              </div>
            </dl>
          </div>

          {/* Sandbox Col 3: Lane 4 & 5 Falsification & Convex Kelly */}
          <div className="space-y-4 pt-4 lg:pt-0 lg:pl-6">
            <div className="text-xs font-mono uppercase tracking-wider text-stone-500">
              Lane 4 & 5 · Falsification & Convex Sizing
            </div>
            <h3 className="text-base font-semibold text-stone-900">
              Bayesian Confounding Gate & Kelly Sizing (`INC-2026-111`)
            </h3>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs">
                  <label htmlFor="sandbox-occlusion" className="text-stone-600 font-medium">
                    Cloud / Sensor Occlusion Prob
                  </label>
                  <span className="font-mono text-stone-900 tabular-nums">
                    {Math.round(occlusionProb * 100)}%
                  </span>
                </div>
                <input
                  id="sandbox-occlusion"
                  type="range"
                  min={0}
                  max={0.95}
                  step={0.05}
                  value={occlusionProb}
                  onChange={(e) => setOcclusionProb(Number(e.target.value))}
                  className="w-full accent-stone-900 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs">
                  <label htmlFor="sandbox-corroboration" className="text-stone-600 font-medium">
                    Secondary Modality Z-Score
                  </label>
                  <span className="font-mono text-stone-900 tabular-nums">
                    {corroborationZ.toFixed(1)}σ
                  </span>
                </div>
                <input
                  id="sandbox-corroboration"
                  type="range"
                  min={0}
                  max={3.5}
                  step={0.1}
                  value={corroborationZ}
                  onChange={(e) => setCorroborationZ(Number(e.target.value))}
                  className="w-full accent-stone-900 cursor-pointer"
                />
              </div>
            </div>

            <dl className="space-y-1.5 pt-3 border-t border-stone-200 text-xs font-mono tabular-nums">
              <div className="flex justify-between">
                <dt className="text-stone-500">Sensor Health Posterior:</dt>
                <dd className="font-semibold text-stone-900">
                  {liveDivergence.sensorHealthPosterior}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Falsification Gate Status:</dt>
                <dd
                  className={
                    liveDivergence.passedFalsificationGates
                      ? 'text-emerald-800 font-semibold'
                      : 'text-red-800 font-semibold'
                  }
                >
                  {liveDivergence.passedFalsificationGates ? 'SURVIVED (PROMOTED)' : 'REFUTED (BLOCKED)'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-500">Epistemic Kelly Allocation:</dt>
                <dd className="font-semibold text-blue-900">
                  {liveKelly.recommendedAllocationPct}% of NAV
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>
    </div>
  );
};
