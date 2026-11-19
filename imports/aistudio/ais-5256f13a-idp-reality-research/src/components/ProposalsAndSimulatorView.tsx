import React from 'react';
import { ArchitectureProposalRfc } from '../data/idpDomainData';
import {
  ArchitectureSimulationResult,
  SimulationConfig,
} from '../utils/roadmapLogic';
import { Check, Sliders } from 'lucide-react';

interface ProposalsAndSimulatorViewProps {
  rfcs: ArchitectureProposalRfc[];
  selectedRfcId: string;
  onSelectRfcId: (id: string) => void;
  onSelectRfcOption: (rfcId: string, optionId: 'A' | 'B' | 'C') => void;
  simConfig: SimulationConfig;
  onUpdateSimConfig: (next: SimulationConfig) => void;
  simResult: ArchitectureSimulationResult;
  onNavigateToBrief: () => void;
}

export const ProposalsAndSimulatorView: React.FC<ProposalsAndSimulatorViewProps> = ({
  rfcs,
  selectedRfcId,
  onSelectRfcId,
  onSelectRfcOption,
  simConfig,
  onUpdateSimConfig,
  simResult,
  onNavigateToBrief,
}) => {
  const activeRfc = rfcs.find((r) => r.id === selectedRfcId) || rfcs[0];

  return (
    <div className="space-y-12">
      {/* Header */}
      <section className="border-b border-stone-200 pb-8 flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="text-xs uppercase tracking-widest text-stone-500">
            Architectural Decision Records (RFCs) · Interactive Trade-Off Simulator
          </div>
          <h1
            className="text-3xl sm:text-4xl font-display font-medium text-stone-900 leading-tight"
            style={{ textWrap: 'balance' }}
          >
            Systemic Asymmetry Architecture Proposals & Trade-Off Lab
          </h1>
          <p className="text-sm text-stone-600 leading-relaxed">
            Compare candidate architectural options across RFC-01 through RFC-05 and stress-test
            their combined impact on point-in-time bitemporal fidelity, P99 signal latency, and
            asymmetry capture before locking the External Consultant SOW.
          </p>
        </div>

        <button
          type="button"
          onClick={onNavigateToBrief}
          className="px-4 py-2.5 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors cursor-pointer self-start whitespace-nowrap shrink-0"
        >
          Sync Selections to Consultant Dossier →
        </button>
      </section>

      {/* Interactive System-Wide Architecture & Asymmetry Payoff Simulator */}
      <section className="bg-white border border-stone-200 p-6 sm:p-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-stone-700" />
            <h2 className="text-xl font-display font-medium text-stone-900">
              Real-Time Architecture Envelope & Asymmetry Capture Simulator
            </h2>
          </div>
          <div className="text-xs font-mono text-stone-600 whitespace-nowrap">
            Posture Classification:{' '}
            <span
              className={
                simResult.criticalPathScore === 'Optimal'
                  ? 'text-emerald-800 font-semibold'
                  : simResult.criticalPathScore === 'Balanced'
                  ? 'text-blue-900 font-semibold'
                  : 'text-red-800 font-semibold'
              }
            >
              {simResult.criticalPathScore}
            </span>
          </div>
        </div>

        {/* Simulated Output KPI Strip — Hairline Divided (No Cards Within Cards) */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-6 border-y border-stone-200 py-5 divide-y sm:divide-y-0 sm:divide-x divide-stone-200">
          <div className="pt-3 sm:pt-0 sm:pr-4">
            <div className="text-xs text-stone-500">End-to-End Signal P99</div>
            <div className="text-2xl font-mono font-semibold text-stone-900 tabular-nums mt-1">
              {simResult.endToEndLatencyMs} ms
            </div>
            <div className="text-xs text-stone-500 mt-1">Intake to divergence</div>
          </div>

          <div className="pt-3 sm:pt-0 sm:px-4">
            <div className="text-xs text-stone-500">Bitemporal Audit Fidelity</div>
            <div className="text-2xl font-mono font-semibold text-blue-900 tabular-nums mt-1">
              {simResult.bitemporalFidelityPct}%
            </div>
            <div className="text-xs text-stone-500 mt-1">Zero-leakage index</div>
          </div>

          <div className="pt-3 sm:pt-0 sm:px-4">
            <div className="text-xs text-stone-500">False-Positive Promotion</div>
            <div className="text-2xl font-mono font-semibold text-emerald-800 tabular-nums mt-1">
              {simResult.falsePositiveRatePct}%
            </div>
            <div className="text-xs text-stone-500 mt-1">Post-falsification gate</div>
          </div>

          <div className="pt-3 sm:pt-0 sm:px-4">
            <div className="text-xs text-stone-500">Asymmetry Capture Ratio</div>
            <div className="text-2xl font-mono font-semibold text-stone-900 tabular-nums mt-1">
              {simResult.expectedAsymmetryCapturePct}%
            </div>
            <div className="text-xs text-stone-500 mt-1">Pre-consensus alpha</div>
          </div>

          <div className="pt-3 sm:pt-0 sm:pl-4 col-span-2 sm:col-span-1">
            <div className="text-xs text-stone-500">Projected Infra Burn</div>
            <div className="text-2xl font-mono font-semibold text-stone-900 tabular-nums mt-1">
              ${simResult.monthlyInfraBurnUsd.toLocaleString()}
            </div>
            <div className="text-xs text-stone-500 mt-1 font-mono tabular-nums">
              /mo · {simResult.totalImplementationWeeks}w build
            </div>
          </div>
        </div>

        {/* 4 Parameter Sliders */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <label htmlFor="sim-window" className="font-medium text-stone-700">
                Divergence Window
              </label>
              <span className="font-mono text-stone-900 tabular-nums">
                {simConfig.streamingWindowSec}s
              </span>
            </div>
            <input
              id="sim-window"
              type="range"
              min={1}
              max={600}
              step={1}
              value={simConfig.streamingWindowSec}
              onChange={(e) =>
                onUpdateSimConfig({
                  ...simConfig,
                  streamingWindowSec: Number(e.target.value),
                })
              }
              className="w-full accent-stone-900 cursor-pointer"
            />
            <div className="text-[11px] text-stone-500">
              1s streaming vs 600s micro-batch window
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <label htmlFor="sim-strictness" className="font-medium text-stone-700">
                Bitemporal Audit Strictness
              </label>
              <span className="font-mono text-stone-900 tabular-nums">
                {simConfig.bitemporalAuditStrictness}%
              </span>
            </div>
            <input
              id="sim-strictness"
              type="range"
              min={60}
              max={100}
              step={1}
              value={simConfig.bitemporalAuditStrictness}
              onChange={(e) =>
                onUpdateSimConfig({
                  ...simConfig,
                  bitemporalAuditStrictness: Number(e.target.value),
                })
              }
              className="w-full accent-stone-900 cursor-pointer"
            />
            <div className="text-[11px] text-stone-500">
              Point-in-time ASOF verification depth
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <label htmlFor="sim-gates" className="font-medium text-stone-700">
                Falsification Gates
              </label>
              <span className="font-mono text-stone-900 tabular-nums">
                {simConfig.falsificationGatesCount} gates
              </span>
            </div>
            <input
              id="sim-gates"
              type="range"
              min={1}
              max={8}
              step={1}
              value={simConfig.falsificationGatesCount}
              onChange={(e) =>
                onUpdateSimConfig({
                  ...simConfig,
                  falsificationGatesCount: Number(e.target.value),
                })
              }
              className="w-full accent-stone-900 cursor-pointer"
            />
            <div className="text-[11px] text-stone-500">
              Automated Bayesian null-hypothesis tests
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <label htmlFor="sim-concurrency" className="font-medium text-stone-700">
                Graph Merge Throughput
              </label>
              <span className="font-mono text-stone-900 tabular-nums">
                {(simConfig.entityResolutionConcurrency / 1000).toFixed(0)}k/s
              </span>
            </div>
            <input
              id="sim-concurrency"
              type="range"
              min={5000}
              max={50000}
              step={5000}
              value={simConfig.entityResolutionConcurrency}
              onChange={(e) =>
                onUpdateSimConfig({
                  ...simConfig,
                  entityResolutionConcurrency: Number(e.target.value),
                })
              }
              className="w-full accent-stone-900 cursor-pointer"
            />
            <div className="text-[11px] text-stone-500">
              Lock-free entity resolution capacity
            </div>
          </div>
        </div>
      </section>

      {/* RFC Selector Tabs & Detailed Option A/B/C Trade-Off Matrix */}
      <section className="space-y-6">
        <div className="flex flex-wrap items-center gap-2 border-b border-stone-200 pb-4">
          {rfcs.map((rfc) => {
            const isSelected = rfc.id === activeRfc.id;
            const shortNames: Record<string, string> = {
              'RFC-01': 'Bitemporal Spine',
              'RFC-02': 'Lock-Free Causal Graph',
              'RFC-03': 'Streaming Divergence',
              'RFC-04': 'Merkle Provenance',
              'RFC-05': 'Bayesian Falsification',
            };
            return (
              <button
                key={rfc.id}
                type="button"
                onClick={() => onSelectRfcId(rfc.id)}
                className={`px-4 py-2 text-xs font-mono transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                  isSelected
                    ? 'bg-stone-900 text-white font-semibold'
                    : 'bg-white border border-stone-200 text-stone-700 hover:bg-stone-100'
                }`}
              >
                {rfc.id} · {shortNames[rfc.id] || rfc.title} (Opt {rfc.selectedOptionId})
              </button>
            );
          })}
        </div>

        {/* Active RFC Specification Header */}
        <div className="bg-white border border-stone-200 p-6 sm:p-8 space-y-6">
          <div className="border-b border-stone-200 pb-5 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-stone-500">
              <span>
                {activeRfc.id} · {activeRfc.plane} · Horizon {activeRfc.horizon}
              </span>
              <span className="text-blue-900 font-semibold">{activeRfc.status}</span>
            </div>
            <h2 className="text-2xl font-display font-medium text-stone-900">
              {activeRfc.title}
            </h2>
            <div className="text-xs text-stone-500">
              Remediates Incidents: {activeRfc.linkedIncidents.join(', ')}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-sm">
            <div className="space-y-1.5">
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Architectural Problem Statement
              </div>
              <p className="text-xs text-stone-700 leading-relaxed">
                {activeRfc.problemStatement}
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Systemic Asymmetry Exploitation Rationale
              </div>
              <p className="text-xs text-stone-700 leading-relaxed">
                {activeRfc.asymmetryExploitationRationale}
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-stone-200 space-y-1">
            <div className="text-xs font-semibold uppercase tracking-wider text-blue-900">
              Specific Mandate / Question for External Consultant
            </div>
            <p className="text-xs text-stone-800 leading-relaxed font-medium">
              {activeRfc.consultantPromptQuestion}
            </p>
          </div>
        </div>

        {/* 3-Column Option Comparison — Direct Single-Elevation Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {activeRfc.options.map((opt) => {
              const isChosen = activeRfc.selectedOptionId === opt.id;
              return (
                <div
                  key={opt.id}
                  className={`border p-5 flex flex-col justify-between space-y-5 transition-colors ${
                    isChosen
                      ? 'border-stone-900 bg-stone-50/70'
                      : 'border-stone-200 bg-white'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-semibold text-stone-900">
                        OPTION {opt.id}
                        {opt.recommended ? ' · RECOMMENDED' : ''}
                      </span>
                      <span className="text-stone-500">{opt.implementationWeeks}w build</span>
                    </div>

                    <h3 className="text-base font-semibold text-stone-900 leading-snug">
                      {opt.label}
                    </h3>

                    <p className="text-xs text-stone-600 leading-relaxed">
                      {opt.architectureSummary}
                    </p>

                    <dl className="grid grid-cols-3 gap-2 pt-3 border-t border-stone-200 text-xs font-mono tabular-nums">
                      <div>
                        <dt className="text-[10px] text-stone-500 uppercase">Latency</dt>
                        <dd className="font-semibold text-stone-900">+{opt.latencyImpactMs}ms</dd>
                      </div>
                      <div>
                        <dt className="text-[10px] text-stone-500 uppercase">Fidelity</dt>
                        <dd className="font-semibold text-blue-900">
                          {opt.bitemporalFidelityScore}%
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[10px] text-stone-500 uppercase">Infra/Mo</dt>
                        <dd className="font-semibold text-stone-900">
                          ${opt.monthlyInfraCostUsd.toLocaleString()}
                        </dd>
                      </div>
                    </dl>

                    <div className="space-y-2 pt-3 border-t border-stone-200 text-xs">
                      <div className="font-semibold text-emerald-900">Advantages</div>
                      <ul className="space-y-1 text-stone-700 list-disc pl-4">
                        {opt.pros.map((pro, idx) => (
                          <li key={idx}>{pro}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="space-y-2 pt-2 text-xs">
                      <div className="font-semibold text-red-900">Trade-Offs / Risks</div>
                      <ul className="space-y-1 text-stone-600 list-disc pl-4">
                        {opt.cons.map((con, idx) => (
                          <li key={idx}>{con}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => onSelectRfcOption(activeRfc.id, opt.id)}
                    className={`w-full py-2.5 px-4 text-xs font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer whitespace-nowrap ${
                      isChosen
                        ? 'bg-stone-900 text-white'
                        : 'bg-stone-100 text-stone-800 hover:bg-stone-200'
                    }`}
                  >
                    {isChosen && <Check className="w-3.5 h-3.5" />}
                    <span>
                      {isChosen
                        ? `Selected Baseline (Option ${opt.id})`
                        : `Select Option ${opt.id} for Roadmap`}
                    </span>
                  </button>
                </div>
              );
            })}
        </div>
      </section>
    </div>
  );
};
