import React, { useState } from 'react';
import {
  STANDARD_WORKLOAD_REQUESTS,
  HOST_HARDWARE_PROFILES,
  WorkloadRequest,
  HostProfileId,
  ModelFamily,
  routeWorkload
} from '../engine/genesisAirLlmEngine';
import { GitBranch, ShieldCheck, AlertTriangle, Clock, Coins, CheckCircle2 } from 'lucide-react';

export const InferenceRouterView: React.FC = () => {
  const [selectedHostId, setSelectedHostId] = useState<HostProfileId>('genesis-linux-nvme-worker');
  const [selectedWorkloadId, setSelectedWorkloadId] = useState<string>('wl-overnight-arch');
  const [customLatencySeconds, setCustomLatencySeconds] = useState<number>(3600);
  const [customOutputTokens, setCustomOutputTokens] = useState<number>(850);
  const [customImplementerFamily, setCustomImplementerFamily] = useState<ModelFamily>('gemini-external');
  const [requireCrossFamily, setRequireCrossFamily] = useState<boolean>(true);

  const activeHost =
    HOST_HARDWARE_PROFILES.find((h) => h.id === selectedHostId) ?? HOST_HARDWARE_PROFILES[0];

  const baseWorkload =
    STANDARD_WORKLOAD_REQUESTS.find((w) => w.id === selectedWorkloadId) ??
    STANDARD_WORKLOAD_REQUESTS[3];

  const handleSelectPresetWorkload = (wl: WorkloadRequest) => {
    setSelectedWorkloadId(wl.id);
    setCustomLatencySeconds(wl.maxLatencySeconds);
    setCustomOutputTokens(wl.estimatedOutputTokens);
    setCustomImplementerFamily(wl.implementingAgentFamily ?? 'gemini-external');
    setRequireCrossFamily(wl.requiresEpistemicIndependence);
  };

  const liveWorkload: WorkloadRequest = {
    ...baseWorkload,
    maxLatencySeconds: customLatencySeconds,
    estimatedOutputTokens: customOutputTokens,
    implementingAgentFamily: customImplementerFamily,
    requiresEpistemicIndependence: requireCrossFamily
  };

  const activeDecision = routeWorkload(liveWorkload, activeHost);

  const allDecisions = STANDARD_WORKLOAD_REQUESTS.map((wl) => ({
    workload: wl,
    decision: routeWorkload(wl, activeHost)
  }));

  return (
    <div className="space-y-10">
      {/* Header & Runtime Architecture Explanation */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 lg:p-8 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <div className="text-xs font-medium text-slate-500">
              Section 03 · Runtime Integration & Dynamic Resource Allocation
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">
              IDP Context Compiler & Multi-Lane Inference Router
            </h1>
            <p className="text-sm text-slate-600 mt-1 max-w-3xl">
              AirLLM is never the default interactive inference engine. Instead, the IDP Context Compiler evaluates workload SLOs, latency tolerance, hardware quotas, and cross-family epistemic independence before dispatching to one of five execution lanes.
            </p>
          </div>

          <div className="shrink-0">
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Target Genesis Worker / Host Profile
            </label>
            <select
              aria-label="Target Genesis Worker / Host Profile"
              value={selectedHostId}
              onChange={(e) => setSelectedHostId(e.target.value as HostProfileId)}
              className="bg-slate-50 border border-slate-300 text-slate-900 text-xs font-medium rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
            >
              {HOST_HARDWARE_PROFILES.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 5-Stage Architectural Flow Diagram */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div className="font-mono text-slate-500">Stage 01</div>
            <div className="font-semibold text-slate-900 mt-1">IDP Agent / Supervisor</div>
            <p className="text-slate-600 mt-1">
              Submits capability, quality, latency SLO, budget, and implementing model family metadata.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div className="font-mono text-slate-500">Stage 02</div>
            <div className="font-semibold text-slate-900 mt-1">Context Compiler</div>
            <p className="text-slate-600 mt-1">
              Shapes deterministic evidence, evaluates blast radius, and flags correlated-failure risk.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900 text-white">
            <div className="font-mono text-amber-300">Stage 03</div>
            <div className="font-semibold mt-1">Inference Router</div>
            <p className="text-slate-300 mt-1">
              Optimises across SLOs · Cost per verified result · Hardware quotas · Cross-family independence.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div className="font-mono text-slate-500">Stage 04</div>
            <div className="font-semibold text-slate-900 mt-1">Execution Fabric</div>
            <p className="text-slate-600 mt-1">
              Dispatches to Deterministic Code, Fast Local 8B, AirLLM Streamed 27B–235B, or External API.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div className="font-mono text-slate-500">Stage 05</div>
            <div className="font-semibold text-slate-900 mt-1">Evidence & Telemetry</div>
            <p className="text-slate-600 mt-1">
              Records verified outcome accuracy and updates routing weights for subsequent dispatches.
            </p>
          </div>
        </div>
      </section>

      {/* Interactive Routing Simulator */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Workload Configurator */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 space-y-5">
          <div>
            <div className="text-xs font-medium text-slate-500">Interactive Routing Simulator</div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Configure IDP Workload & Constraints
            </h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">
                Select Workload Archetype
              </label>
              <select
                aria-label="Select Workload Archetype"
                value={selectedWorkloadId}
                onChange={(e) => {
                  const found = STANDARD_WORKLOAD_REQUESTS.find((w) => w.id === e.target.value);
                  if (found) handleSelectPresetWorkload(found);
                }}
                className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                {STANDARD_WORKLOAD_REQUESTS.map((wl) => (
                  <option key={wl.id} value={wl.id}>
                    {wl.name} ({wl.department})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="router-latency-input" className="block text-xs font-medium text-slate-700 mb-1">
                  Latency SLO Ceiling (sec)
                </label>
                <input
                  id="router-latency-input"
                  type="number"
                  min={1}
                  max={14400}
                  value={customLatencySeconds}
                  onChange={(e) => setCustomLatencySeconds(Math.max(1, Number(e.target.value)))}
                  className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm font-mono tabular-nums rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label htmlFor="router-tokens-input" className="block text-xs font-medium text-slate-700 mb-1">
                  Required Output Tokens
                </label>
                <input
                  id="router-tokens-input"
                  type="number"
                  min={50}
                  max={4000}
                  step={50}
                  value={customOutputTokens}
                  onChange={(e) => setCustomOutputTokens(Math.max(50, Number(e.target.value)))}
                  className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm font-mono tabular-nums rounded-lg px-3 py-2"
                />
              </div>
            </div>

            <div>
              <label htmlFor="implementer-family-select" className="block text-xs font-medium text-slate-700 mb-1">
                Implementing Agent Model Family (For Independence Check)
              </label>
              <select
                id="implementer-family-select"
                value={customImplementerFamily}
                onChange={(e) => setCustomImplementerFamily(e.target.value as ModelFamily)}
                className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg px-3 py-2"
              >
                <option value="gemini-external">Gemini Family (External Cloud Implementer)</option>
                <option value="claude-external">Claude Family (External Cloud Implementer)</option>
                <option value="llama-meta">Llama Family (Meta Open-Weight Implementer)</option>
                <option value="qwen-alibaba">Qwen Family (Alibaba Open-Weight Implementer)</option>
              </select>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2.5 text-sm text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requireCrossFamily}
                  onChange={(e) => setRequireCrossFamily(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                <span>Enforce Cross-Family Epistemic Independence Gate</span>
              </label>
              <p className="text-xs text-slate-500 mt-1 pl-6">
                Prevents a model family from verifying or approving its own architectural or code changes.
              </p>
            </div>
          </div>
        </div>

        {/* Right: Live Decision Output */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-4">
              <div>
                <div className="text-xs font-medium text-slate-500">
                  Compiled Routing Verdict · {liveWorkload.department}
                </div>
                <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                  {activeDecision.selectedLaneLabel}
                </h3>
              </div>
              <div className="text-right font-mono tabular-nums">
                <div className="text-xs text-slate-500">Selected Backend ID</div>
                <div className="text-sm font-semibold text-slate-900">{activeDecision.selectedModelId}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-500">Estimated Execution Time</div>
                <div className="text-lg font-bold text-slate-900 font-mono tabular-nums mt-1">
                  {activeDecision.estimatedDurationSeconds}s
                  {activeDecision.estimatedDurationSeconds >= 60
                    ? ` (${(activeDecision.estimatedDurationSeconds / 60).toFixed(1)}m)`
                    : ''}
                </div>
                <div className="text-xs text-slate-500 mt-0.5 font-mono tabular-nums">
                  SLO Ceiling: {liveWorkload.maxLatencySeconds}s
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-500">Estimated Run Cost</div>
                <div className="text-lg font-bold text-slate-900 font-mono tabular-nums mt-1">
                  £{activeDecision.estimatedCostGbp.toFixed(4)}
                </div>
                <div className="text-xs text-slate-500 mt-0.5 font-mono tabular-nums">
                  Budget Cap: £{liveWorkload.budgetCapGbp.toFixed(3)}
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-500">Epistemic Independence</div>
                <div className="text-sm font-bold text-slate-900 mt-1 flex items-center gap-1.5">
                  {activeDecision.epistemicIndependenceVerified ? (
                    <>
                      <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span className="text-emerald-800">Decorrelated Family</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span className="text-amber-800">Single-Family Fast Path</span>
                    </>
                  )}
                </div>
                <div className="text-xs text-slate-500 mt-0.5 font-mono">
                  Verifier: {activeDecision.selectedModelFamily}
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2 text-sm">
              <div>
                <span className="font-semibold text-slate-900">Router Decision Rationale: </span>
                <span className="text-slate-700">{activeDecision.rationale}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-900">Epistemic Audit Note: </span>
                <span className="text-slate-700">{activeDecision.epistemicIndependenceReason}</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <span>Host Guardrail Profile: {activeHost.name}</span>
            <span className="font-mono">Fallback Lane: {activeDecision.fallbackLane}</span>
          </div>
        </div>
      </section>

      {/* Complete Estate Workload Routing Policy Matrix */}
      <section className="space-y-4">
        <div>
          <div className="text-xs font-medium text-slate-500">
            Estate-Wide Routing Policy Table
          </div>
          <h2 className="text-lg font-bold text-slate-900 mt-0.5">
            Active Routing Matrix Across All IDP Workloads
          </h2>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-xs font-semibold text-slate-600">
                  <th className="py-3 px-4">IDP Workload</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4 text-right">SLO Ceiling</th>
                  <th className="py-3 px-4">Preferred Execution Lane</th>
                  <th className="py-3 px-4">Selected Model / Engine</th>
                  <th className="py-3 px-4 text-right">Est. Duration</th>
                  <th className="py-3 px-4 text-right">Est. Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-sm">
                {allDecisions.map(({ workload, decision }) => (
                  <tr
                    key={workload.id}
                    onClick={() => handleSelectPresetWorkload(workload)}
                    className={`cursor-pointer transition-colors ${
                      workload.id === selectedWorkloadId ? 'bg-slate-100/90' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="py-3 px-4 font-semibold text-slate-900">{workload.name}</td>
                    <td className="py-3 px-4 text-xs text-slate-600">{workload.department}</td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-xs text-slate-600">
                      {workload.maxLatencySeconds}s
                    </td>
                    <td className="py-3 px-4 text-xs font-medium">
                      <span
                        className={
                          decision.selectedLane === 'airllm-streamed'
                            ? 'text-emerald-800 font-semibold'
                            : decision.selectedLane === 'policy-gate'
                            ? 'text-amber-800 font-semibold'
                            : 'text-slate-700'
                        }
                      >
                        {decision.selectedLaneLabel}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-700">
                      {decision.selectedModelId}
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-xs text-slate-800">
                      {decision.estimatedDurationSeconds}s
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-xs text-slate-800">
                      £{decision.estimatedCostGbp.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
};
