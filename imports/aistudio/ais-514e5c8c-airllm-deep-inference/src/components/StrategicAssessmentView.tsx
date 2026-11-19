import React, { useState } from 'react';
import {
  AIRLLM_MODEL_CATALOG,
  AirLlmModelSpec,
  StrategicOpportunity
} from '../engine/genesisAirLlmEngine';
import { Layers, HardDrive, Cpu, ShieldAlert, Check, ArrowRight } from 'lucide-react';

interface StrategicAssessmentViewProps {
  opportunities: StrategicOpportunity[];
  onToggleOpportunity: (id: string) => void;
  onInspectModelInEvalLane: (modelId: string) => void;
}

export const StrategicAssessmentView: React.FC<StrategicAssessmentViewProps> = ({
  opportunities,
  onToggleOpportunity,
  onInspectModelInEvalLane
}) => {
  const [tierFilter, setTierFilter] = useState<'all' | 'tier-1-pilot' | 'tier-2-overnight' | 'tier-3-extreme-demo' | 'macos-safe'>('all');
  const [activeLayerStep, setActiveLayerStep] = useState<number>(2);
  const [selectedStreamModelId, setSelectedStreamModelId] = useState<string>('llama-3.3-70b');

  const selectedStreamModel: AirLlmModelSpec =
    AIRLLM_MODEL_CATALOG.find((m) => m.id === selectedStreamModelId) ?? AIRLLM_MODEL_CATALOG[3];

  const filteredModels = AIRLLM_MODEL_CATALOG.filter((m) => {
    if (tierFilter === 'all') return true;
    if (tierFilter === 'macos-safe') return m.macOsAppleSiliconSupported;
    return m.recommendedTier === tierFilter;
  });

  const enabledCount = opportunities.filter((o) => o.enabledInGenesis).length;

  const streamLayers = [
    { index: 1, name: 'Embedding & Tokeniser Projection', sizeGb: 1.1, phase: 'Purged after forward pass' },
    { index: 2, name: 'Transformer Block Shard 01–20', sizeGb: selectedStreamModel.reportedVramGb * 0.85, phase: 'Active in GPU Working Set' },
    { index: 3, name: 'Transformer Block Shard 21–40', sizeGb: selectedStreamModel.reportedVramGb * 0.85, phase: 'Prefetching from NVMe Queue' },
    { index: 4, name: 'Transformer Block Shard 41–80', sizeGb: selectedStreamModel.reportedVramGb * 0.85, phase: 'Resident on PCIe NVMe Storage' },
    { index: 5, name: 'LM Head & Verification Logits', sizeGb: 1.2, phase: 'Resident on PCIe NVMe Storage' }
  ];

  return (
    <div className="space-y-12">
      {/* Executive Thesis & Core Distinction */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 lg:p-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          <div className="lg:col-span-7 flex flex-col justify-between space-y-6">
            <div className="space-y-3">
              <div className="text-xs font-medium text-slate-500">
                <span>Research Assessment · November 2026</span>
                <span className="mx-2" aria-hidden="true">·</span>
                <span>Science Department Governance</span>
                <span className="mx-2" aria-hidden="true">·</span>
                <span>High Strategic Potential</span>
              </div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-slate-900" style={{ textWrap: 'balance' }}>
                AirLLM: Decoupling Model Capability from Resident GPU Memory Across Your Autonomous AI Estate
              </h1>
              <p className="text-base text-slate-600 leading-relaxed max-w-2xl">
                AirLLM challenges a foundational constraint on autonomous infrastructure by streaming layer shards or active MoE experts from storage through a compact 1–6 GB GPU working set. For Genesis and IDP, the asymmetric advantage is not replacing interactive coding calls with slow giants—it is unlocking sovereign overnight architectural intelligence, cross-family independent verification, and deep failure-to-intelligence escalation on modest hardware.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                <div className="font-semibold text-slate-900">Conventional Residency</div>
                <p className="text-slate-600">
                  Requires full model weights resident in high-cost GPU VRAM; forces multi-GPU cluster rentals for 70B+ models.
                </p>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                <div className="font-semibold text-slate-900">AirLLM Streamed Execution</div>
                <p className="text-slate-600">
                  Streams layer shards or selected MoE experts from NVMe storage through a 1–6 GB GPU working set for latency-tolerant tasks.
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div>
                <div className="text-xs text-slate-500">Core Architectural Principle</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">Small VRAM ≠ Fast Compute</div>
                <p className="mt-0.5 text-xs text-slate-600">
                  Eliminates VRAM residency limits while shifting cost to NVMe I/O transfer and wall-clock time.
                </p>
              </div>
              <div>
                <div className="text-xs text-slate-500">Primary Optimisation Metric</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">Cost per Verified Result</div>
                <p className="mt-0.5 text-xs text-slate-600">
                  Total execution cost divided by verified deterministic outcomes—not raw cost per token.
                </p>
              </div>
              <div>
                <div className="text-xs text-slate-500">Genesis Enabled Facilities</div>
                <div className="mt-1 text-sm font-semibold text-slate-900 font-mono tabular-nums">
                  {enabledCount} of {opportunities.length} Active Lanes
                </div>
                <p className="mt-0.5 text-xs text-slate-600">
                  Routed via the unified IDP Context Compiler under strict disk and runtime quotas.
                </p>
              </div>
            </div>
          </div>

          {/* Interactive Streamed Inference vs Conventional Residency Visualizer */}
          <div className="lg:col-span-5 bg-slate-900 text-slate-100 rounded-lg p-6 flex flex-col justify-between space-y-5">
            <div className="space-y-3 border-b border-slate-800 pb-4">
              <div>
                <div className="text-xs text-slate-400">1. What the Technology Actually Achieves</div>
                <h2 className="text-base font-semibold text-white mt-0.5">
                  Layer-Streamed Working Set vs Full Residency
                </h2>
              </div>
              <label className="block text-xs text-slate-300">
                <span className="sr-only">Inspect Model Architecture</span>
                <select
                  aria-label="Inspect Model Architecture"
                  value={selectedStreamModelId}
                  onChange={(e) => setSelectedStreamModelId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 text-slate-100 text-xs rounded-md px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  {AIRLLM_MODEL_CATALOG.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.parameterCountLabel})
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 rounded bg-slate-800/80 border border-slate-700/80">
                <div className="text-slate-400">Conventional Inference</div>
                <div className="text-lg font-bold text-rose-300 font-mono tabular-nums mt-1">
                  {selectedStreamModel.conventionalVramGb.toFixed(1)} GB VRAM
                </div>
                <div className="text-slate-400 mt-1">
                  Full weights resident in GPU memory · Cluster required
                </div>
              </div>
              <div className="p-3.5 rounded bg-slate-800/80 border border-amber-500/40">
                <div className="text-amber-300">AirLLM Streamed Working Set</div>
                <div className="text-lg font-bold text-emerald-300 font-mono tabular-nums mt-1">
                  {selectedStreamModel.reportedVramGb.toFixed(2)} GB VRAM
                </div>
                <div className="text-slate-300 mt-1 font-mono tabular-nums">
                  {selectedStreamModel.shardedDiskFootprintGb} GB shards · ~{selectedStreamModel.estimatedSecPerTokenNvme}s/tok
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Interactive Layer Transfer Pipeline (Click shard to step)</span>
                <span className="font-mono tabular-nums text-amber-300">Step {activeLayerStep}/5</span>
              </div>
              <div className="space-y-1.5">
                {streamLayers.map((layer) => {
                  const isActive = layer.index === activeLayerStep;
                  const isCompleted = layer.index < activeLayerStep;
                  return (
                    <button
                      key={layer.index}
                      type="button"
                      onClick={() => setActiveLayerStep(layer.index)}
                      className={`w-full text-left px-3 py-2 rounded text-xs transition-colors flex items-center justify-between gap-2 border ${
                        isActive
                          ? 'bg-amber-500/20 border-amber-400 text-white'
                          : isCompleted
                          ? 'bg-slate-800/40 border-slate-800 text-slate-400'
                          : 'bg-slate-800/70 border-slate-700/70 text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <span className="font-medium truncate">
                        0{layer.index}. {layer.name}
                      </span>
                      <span className="font-mono tabular-nums shrink-0 text-[11px]">
                        {isActive
                          ? `GPU Active (${layer.sizeGb.toFixed(2)} GB)`
                          : isCompleted
                          ? 'Freed from VRAM'
                          : 'On NVMe Disk'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 1B: Project-Reported Model Configurations & Hardware Reality Table */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="text-xs font-medium text-slate-500">
              Section 01 · Benchmark Inventory & Storage Realities
            </div>
            <h2 className="text-xl font-bold text-slate-900 mt-0.5">
              Reported AirLLM Configurations vs Operational Footprint
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Project-reported memory figures demonstrate extreme VRAM compression, while checkpoint shard footprints and token transfer times govern where each model is operationally viable.
            </p>
          </div>

          {/* Interactive Filter Controls */}
          <div className="flex items-center gap-1 p-1 bg-slate-200/80 rounded-lg self-start">
            {[
              { id: 'all', label: 'All Models (7)' },
              { id: 'tier-1-pilot', label: 'Pilot 8B–27B' },
              { id: 'tier-2-overnight', label: 'Overnight 70B–235B' },
              { id: 'macos-safe', label: 'macOS Apple Silicon Safe' },
              { id: 'tier-3-extreme-demo', label: '2.8T Extreme Demo' }
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setTierFilter(tab.id as typeof tierFilter)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  tierFilter === tab.id
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-xs font-semibold text-slate-600">
                  <th className="py-3 px-4">Model Configuration</th>
                  <th className="py-3 px-4">Architecture</th>
                  <th className="py-3 px-4 text-right">Reported VRAM</th>
                  <th className="py-3 px-4 text-right">Conventional VRAM</th>
                  <th className="py-3 px-4 text-right">Raw + Shard Disk</th>
                  <th className="py-3 px-4 text-right">Est. Token Latency</th>
                  <th className="py-3 px-4">macOS Support</th>
                  <th className="py-3 px-4 text-right">Evaluation Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-sm">
                {filteredModels.map((model) => {
                  const totalDisk = (model.rawCheckpointGb + model.shardedDiskFootprintGb).toFixed(1);
                  return (
                    <tr key={model.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900">{model.name}</div>
                        <div className="text-xs text-slate-500 mt-0.5 max-w-md">{model.notes}</div>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-600 font-mono">
                        {model.architectureStyle}
                        {model.supportsStreamedLora ? ' · LoRA v4' : ''}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono tabular-nums font-semibold text-emerald-700">
                        {model.reportedVramGb.toFixed(2)} GB
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono tabular-nums text-slate-500">
                        {model.conventionalVramGb.toFixed(0)} GB
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono tabular-nums text-slate-800">
                        <div>{totalDisk} GB</div>
                        <div className="text-[11px] text-slate-500">
                          ({model.rawCheckpointGb}G raw + {model.shardedDiskFootprintGb}G shards)
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono tabular-nums">
                        <span
                          className={
                            model.estimatedSecPerTokenNvme > 30
                              ? 'text-rose-700 font-semibold'
                              : model.estimatedSecPerTokenNvme > 2
                              ? 'text-amber-700 font-medium'
                              : 'text-slate-800'
                          }
                        >
                          {model.estimatedSecPerTokenNvme}s / tok
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs">
                        {model.macOsAppleSiliconSupported ? (
                          <span className="text-emerald-700 font-medium">Supported (Apple Silicon)</span>
                        ) : (
                          <span className="text-rose-700 font-medium">Blocked on macOS (Linux Only)</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => onInspectModelInEvalLane(model.id)}
                          className="px-3 py-1.5 text-xs font-medium text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors whitespace-nowrap shrink-0 inline-flex items-center gap-1"
                        >
                          <span>Test in Lane</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Section 2: Six Strategic Opportunities Across IDP & Genesis Facilities */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="text-xs font-medium text-slate-500">
              Section 02 · Six Strategic Opportunities Across IDP
            </div>
            <h2 className="text-xl font-bold text-slate-900 mt-0.5">
              Genesis Facility Capabilities & Asymmetric Leverage Matrix
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Enable or stage Genesis facility lanes below to govern which IDP departments can dispatch workloads to AirLLM streamed backends.
            </p>
          </div>
          <div className="text-xs text-slate-600 font-mono tabular-nums">
            Active Genesis Modules: {enabledCount} / {opportunities.length}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {opportunities.map((opp) => (
            <article
              key={opp.id}
              className={`bg-white border rounded-xl p-6 flex flex-col justify-between transition-colors ${
                opp.enabledInGenesis ? 'border-slate-300' : 'border-slate-200 opacity-85'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                  <span>
                    {opp.index}. {opp.department}
                  </span>
                  <span className="font-medium text-slate-700">Priority: {opp.priority}</span>
                </div>

                <h3 className="text-lg font-bold text-slate-900">
                  {opp.title}
                </h3>

                <div className="text-xs text-slate-500">
                  {opp.fitSummary}
                </div>

                <p className="text-sm text-slate-600 leading-relaxed">
                  {opp.description}
                </p>

                <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
                  <div>
                    <span className="font-semibold text-slate-800">Asymmetric Leverage: </span>
                    <span className="text-slate-600">{opp.asymmetricMechanism}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-800">Safety Guardrail: </span>
                    <span className="text-slate-600">{opp.guardrailRequirement}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between gap-3">
                <div className="text-xs">
                  <div className="text-slate-500">Genesis Module</div>
                  <div className="font-medium text-slate-900">{opp.genesisFacilityModule}</div>
                </div>

                <button
                  type="button"
                  onClick={() => onToggleOpportunity(opp.id)}
                  aria-pressed={opp.enabledInGenesis}
                  className={`px-3.5 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
                    opp.enabledInGenesis
                      ? 'bg-slate-900 text-white hover:bg-slate-800'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <Check className={`w-3.5 h-3.5 ${opp.enabledInGenesis ? 'opacity-100' : 'opacity-0'}`} />
                  <span>{opp.enabledInGenesis ? 'Facility Enabled' : 'Enable Facility'}</span>
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};
