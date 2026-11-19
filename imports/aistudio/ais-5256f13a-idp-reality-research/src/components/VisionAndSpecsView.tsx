import React, { useState } from 'react';
import {
  FOUNDER_VISION_INVARIANTS,
  REPO_MODULE_SPECS,
  RepoModuleSpec,
} from '../data/idpDomainData';
import { ArrowUpRight, Layers, ShieldCheck, Terminal } from 'lucide-react';

interface VisionAndSpecsViewProps {
  onNavigateToRfc: (rfcId: string) => void;
  onNavigateToIncidents: (modulePath?: string) => void;
  onNavigateToRoadmapPlane: (plane: RepoModuleSpec['plane']) => void;
  onNavigateToLane: (laneId: string) => void;
}

const MODULE_TO_LANE: Record<string, string> = {
  'MOD-INTAKE': 'LANE-01',
  'MOD-BITEMPORAL': 'LANE-02',
  'MOD-ONTOLOGY': 'LANE-03',
  'MOD-ASYMMETRY': 'LANE-04',
  'MOD-FALSIFY': 'LANE-04',
  'MOD-CONVEX': 'LANE-05',
};

export const VisionAndSpecsView: React.FC<VisionAndSpecsViewProps> = ({
  onNavigateToRfc,
  onNavigateToIncidents,
  onNavigateToRoadmapPlane,
  onNavigateToLane,
}) => {
  const [selectedModuleId, setSelectedModuleId] = useState<string>(REPO_MODULE_SPECS[0].id);
  const selectedModule =
    REPO_MODULE_SPECS.find((m) => m.id === selectedModuleId) || REPO_MODULE_SPECS[0];

  return (
    <div className="space-y-12">
      {/* Section 01: Founder Vision & Reality Research Monograph Header */}
      <section className="border-b border-stone-200 pb-10">
        <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500 uppercase tracking-widest mb-3">
          <span>Master Specification v3.4</span>
          <span aria-hidden="true">·</span>
          <span>Architectural Synthesis</span>
          <span aria-hidden="true">·</span>
          <span>Systemic Asymmetry Exploitation</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-8 space-y-4">
            <h1
              className="text-3xl sm:text-4xl lg:text-[2.75rem] font-display font-medium tracking-tight text-stone-900 leading-[1.12]"
              style={{ textWrap: 'balance' }}
            >
              Exploiting Structural Lags Between Physical Reality and Consensus Narrative
            </h1>
            <p className="text-base sm:text-lg text-stone-700 leading-relaxed max-w-3xl">
              The IDP platform is engineered around a single foundational premise: institutional markets
              and policy apparatus price secondary narratives rather than primary physical state. By pairing
              sub-second multi-modal sensorium intake with a strictly bitemporal causal ontology and
              mandatory adversarial falsification, IDP systematically isolates and captures asymmetric
              convexity before consensus aggregation occurs.
            </p>
          </div>

          <div className="lg:col-span-4 bg-white border border-stone-200 p-6 space-y-4">
            <div className="text-xs font-medium uppercase tracking-wider text-stone-500">
              Programme Executive Posture
            </div>
            <dl className="space-y-3 text-sm border-t border-stone-200 pt-3">
              <div className="flex items-baseline justify-between">
                <dt className="text-stone-600">Core Repository Packages</dt>
                <dd className="font-mono font-semibold text-stone-900 tabular-nums">6 Modules</dd>
              </div>
              <div className="flex items-baseline justify-between">
                <dt className="text-stone-600">Mean Spec v3.4 Compliance</dt>
                <dd className="font-mono font-semibold text-stone-900 tabular-nums">70.3%</dd>
              </div>
              <div className="flex items-baseline justify-between">
                <dt className="text-stone-600">Active Post-Mortem Remediations</dt>
                <dd className="font-mono font-semibold text-amber-800 tabular-nums">5 Incidents</dd>
              </div>
              <div className="flex items-baseline justify-between">
                <dt className="text-stone-600">Pending Consultant RFC Decisions</dt>
                <dd className="font-mono font-semibold text-blue-900 tabular-nums">5 Proposals</dd>
              </div>
            </dl>
            <div className="pt-2 border-t border-stone-200">
              <button
                type="button"
                onClick={() => onNavigateToRfc('RFC-01')}
                className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors cursor-pointer whitespace-nowrap"
              >
                <span>Review Priority Architecture RFCs</span>
                <ArrowUpRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Section 02: The Four Non-Negotiable Epistemic Invariants */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-stone-500 mb-1">
              01. Constitutional Axioms
            </div>
            <h2 className="text-2xl font-display font-medium text-stone-900">
              Founder Vision & Non-Negotiable Epistemic Invariants
            </h2>
          </div>
          <p className="text-sm text-stone-600 max-w-md">
            Every architectural proposal and external consultant recommendation is evaluated against
            these four hard system invariants.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {FOUNDER_VISION_INVARIANTS.map((inv, idx) => (
            <article
              key={inv.id}
              className="bg-white border border-stone-200 p-6 flex flex-col justify-between space-y-5"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-stone-500 font-mono">
                  <span>
                    0{idx + 1} · {inv.id}
                  </span>
                  <span className="text-blue-900 font-medium">{inv.formula}</span>
                </div>
                <h3 className="text-lg font-semibold text-stone-900">{inv.title}</h3>
                <p className="text-sm text-stone-600 leading-relaxed">{inv.mandate}</p>
              </div>

              <div className="pt-4 border-t border-stone-200 text-xs text-stone-600">
                <span className="font-semibold text-red-900">Observed Violation Penalty: </span>
                <span>{inv.violationCost}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Section 03: Systemic Asymmetry Exploitation Mechanics */}
      <section className="bg-white border border-stone-200 p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-stone-200 pb-5">
          <div>
            <div className="text-xs uppercase tracking-widest text-stone-500 mb-1">
              02. Exploitation Taxonomy
            </div>
            <h2 className="text-2xl font-display font-medium text-stone-900">
              How IDP Converts Epistemic Asymmetry into Convex Payoffs
            </h2>
          </div>
          <div className="text-xs font-mono text-stone-500">
            Mechanism-to-Outcome Pipeline · 4 Structural Vectors
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 divide-y md:divide-y-0 md:divide-x divide-stone-200">
          <div className="pt-4 md:pt-0 md:pr-4 space-y-2">
            <div className="text-xs font-mono text-stone-500">Vector I · Latency Gap</div>
            <h3 className="text-base font-semibold text-stone-900">
              Information Latency Arbitrage
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Captures the 180ms–6hr window between raw physical/regulatory state change (grid load
              harmonics, port draught anomalies) and secondary wire aggregation.
            </p>
            <div className="pt-2 text-xs font-mono text-blue-900">
              Target P99: &lt; 500ms intake
            </div>
          </div>

          <div className="pt-4 md:pt-0 md:px-4 space-y-2">
            <div className="text-xs font-mono text-stone-500">Vector II · Topology Gap</div>
            <h3 className="text-base font-semibold text-stone-900">
              Cross-Silo Structural Blindspot
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Links multi-hop corporate ownership, customs bills of lading, and regional permits to
              expose tier-3 supply bottlenecks invisible to sector-siloed analysts.
            </p>
            <div className="pt-2 text-xs font-mono text-blue-900">
              Target: 5-hop CSR traversal &lt; 15ms
            </div>
          </div>

          <div className="pt-4 md:pt-0 md:px-4 space-y-2">
            <div className="text-xs font-mono text-stone-500">Vector III · Epistemic Gap</div>
            <h3 className="text-base font-semibold text-stone-900">
              Narrative-vs-Telemetry Divergence
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Quantifies Kullback-Leibler and Wasserstein divergence between consensus implied
              probability distributions and empirical sensorium ground truth.
            </p>
            <div className="pt-2 text-xs font-mono text-blue-900">
              Target: 5 Bayesian refutation gates
            </div>
          </div>

          <div className="pt-4 md:pt-0 md:pl-4 space-y-2">
            <div className="text-xs font-mono text-stone-500">Vector IV · Payoff Structure</div>
            <h3 className="text-base font-semibold text-stone-900">
              Tail-Risk Convexity Structuring
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Weights fractional-Kelly allocation by cryptographic provenance depth and
              counterfactual survival score to maximize upside skew under bounded drawdown.
            </p>
            <div className="pt-2 text-xs font-mono text-blue-900">
              Target: Max cluster drawdown &le; 4.0%
            </div>
          </div>
        </div>
      </section>

      {/* Section 04: Interactive IDP Repository & Master Spec Audit Matrix */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-stone-500 mb-1">
              03. Repository & Master Spec Audit
            </div>
            <h2 className="text-2xl font-display font-medium text-stone-900">
              Monorepo Package Topology & Active Bottleneck Inspector
            </h2>
          </div>
          <div className="text-xs text-stone-600">
            Select any repository package below to inspect its Master Spec mandate and active engineering bottleneck.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left: High-Density Repository Table */}
          <div className="lg:col-span-7 bg-white border border-stone-200 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-stone-200 text-xs text-stone-500 uppercase tracking-wider bg-stone-50">
                  <th className="py-3 px-4 font-medium">Repo Path</th>
                  <th className="py-3 px-4 font-medium">Architectural Plane</th>
                  <th className="py-3 px-4 font-medium text-right">Spec Score</th>
                  <th className="py-3 px-4 font-medium text-right">P99 Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 text-sm">
                {REPO_MODULE_SPECS.map((mod) => {
                  const isSelected = mod.id === selectedModule.id;
                  return (
                    <tr
                      key={mod.id}
                      onClick={() => setSelectedModuleId(mod.id)}
                      className={`transition-colors cursor-pointer ${
                        isSelected ? 'bg-blue-50/70' : 'hover:bg-stone-50'
                      }`}
                    >
                      <td className="py-3.5 px-4 font-mono text-xs font-medium text-stone-900">
                        <button
                          type="button"
                          onClick={() => setSelectedModuleId(mod.id)}
                          className="text-left hover:underline focus:outline-none cursor-pointer"
                        >
                          {mod.path}
                        </button>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-stone-600">{mod.plane}</td>
                      <td className="py-3.5 px-4 text-right font-mono text-xs tabular-nums">
                        <span
                          className={
                            mod.complianceScore >= 75
                              ? 'text-emerald-800 font-semibold'
                              : mod.complianceScore >= 65
                              ? 'text-amber-800 font-semibold'
                              : 'text-red-800 font-semibold'
                          }
                        >
                          {mod.complianceScore}%
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-xs text-stone-700 tabular-nums">
                        {mod.p99LatencyMs} ms
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Right: Selected Package Deep-Dive Inspector */}
          <div className="lg:col-span-5 bg-white border border-stone-200 p-6 space-y-5">
            <div className="border-b border-stone-200 pb-4 space-y-1">
              <div className="flex items-center justify-between text-xs font-mono text-stone-500">
                <span>{selectedModule.path}</span>
                <span>{selectedModule.specVersion}</span>
              </div>
              <h3 className="text-lg font-semibold text-stone-900">{selectedModule.title}</h3>
              <div className="text-xs text-stone-500">
                Plane: {selectedModule.plane} · Compliance: {selectedModule.complianceScore}%
              </div>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs font-medium uppercase tracking-wider text-stone-500 mb-1 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5" />
                  <span>Production Stack</span>
                </div>
                <p className="font-mono text-xs text-stone-800">{selectedModule.stack}</p>
              </div>

              <div>
                <div className="text-xs font-medium uppercase tracking-wider text-stone-500 mb-1 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  <span>Subsystem Responsibility</span>
                </div>
                <p className="text-stone-700 text-xs leading-relaxed">{selectedModule.summary}</p>
              </div>

              <div>
                <div className="text-xs font-medium uppercase tracking-wider text-stone-500 mb-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Founder Master Spec Mandate</span>
                </div>
                <p className="text-stone-800 text-xs font-medium leading-relaxed">
                  {selectedModule.founderMandate}
                </p>
              </div>

              <div className="pt-3 border-t border-stone-200">
                <div className="text-xs font-semibold text-red-900 mb-1">
                  Active Architectural Bottleneck / Recent Incident Trigger
                </div>
                <p className="text-xs text-stone-700 leading-relaxed">
                  {selectedModule.bottleneck}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-stone-200 flex flex-wrap items-center gap-2.5">
              <button
                type="button"
                onClick={() =>
                  onNavigateToLane(MODULE_TO_LANE[selectedModule.id] || 'LANE-01')
                }
                className="px-3.5 py-2 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors cursor-pointer whitespace-nowrap"
              >
                Open {MODULE_TO_LANE[selectedModule.id] || 'LANE-01'} Spec & Code →
              </button>
              <button
                type="button"
                onClick={() => onNavigateToRoadmapPlane(selectedModule.plane)}
                className="px-3.5 py-2 text-xs font-medium text-stone-800 bg-stone-100 hover:bg-stone-200 transition-colors cursor-pointer whitespace-nowrap"
              >
                Inspect Plane Roadmap
              </button>
              <button
                type="button"
                onClick={() => onNavigateToIncidents(selectedModule.path)}
                className="px-3.5 py-2 text-xs font-medium text-stone-800 bg-stone-100 hover:bg-stone-200 transition-colors cursor-pointer whitespace-nowrap"
              >
                View Module Incidents
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
