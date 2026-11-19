import React, { useState } from 'react';
import {
  EconomicsScenarioInput,
  calculateCostPerVerifiedResult
} from '../engine/genesisAirLlmEngine';
import { Calculator, TrendingDown, TrendingUp, RotateCcw } from 'lucide-react';

const PRESET_SCENARIOS: { id: string; label: string; description: string; input: EconomicsScenarioInput }[] = [
  {
    id: 'research-baseline',
    label: '1. Research Dossier Illustration (£2.00/h vs £0.20/h)',
    description:
      'Exact baseline from Section 4: Standard inference at £2.00/hr taking 3 minutes (£0.10) vs AirLLM at £0.20/hr taking 60 minutes (£0.20) with equal accuracy.',
    input: {
      taskName: 'Architecture Review (On-Demand Cloud Comparison)',
      runsPerBatch: 10,
      standardHourlyCostGbp: 2.0,
      standardExecutionMinutes: 3,
      standardVerifiedSuccessRate: 0.8,
      airllmHourlyCostGbp: 0.2,
      airllmExecutionMinutes: 60,
      airllmVerifiedSuccessRate: 0.8,
      airllmNvmeWearCostPerRunGbp: 0.0,
      useSunkOvernightCapacity: false,
      sunkElectricityOverheadPerHourGbp: 0.03
    }
  },
  {
    id: 'sunk-overnight-advantage',
    label: '2. Overnight Spare Hardware + Deep Verification Lift',
    description:
      'Owned Genesis hardware running overnight (sunk capital, £0.03/hr electricity + £0.008 NVMe wear) where 70B deep reasoning improves verified resolution from 58% to 91%.',
    input: {
      taskName: 'Overnight Estate-Wide Architectural Drift Sweep',
      runsPerBatch: 15,
      standardHourlyCostGbp: 2.0,
      standardExecutionMinutes: 4,
      standardVerifiedSuccessRate: 0.58,
      airllmHourlyCostGbp: 0.2,
      airllmExecutionMinutes: 42,
      airllmVerifiedSuccessRate: 0.91,
      airllmNvmeWearCostPerRunGbp: 0.008,
      useSunkOvernightCapacity: true,
      sunkElectricityOverheadPerHourGbp: 0.03
    }
  },
  {
    id: 'failure-to-intelligence',
    label: '3. Failure-to-Intelligence Causal Cluster Escalation',
    description:
      'Recurring incident cluster where fast models repeatedly fail (35% verified fix rate) and AirLLM 70B offline analysis achieves 88% verified deterministic remediation.',
    input: {
      taskName: 'Failure-to-Intelligence Escalation Pipeline',
      runsPerBatch: 8,
      standardHourlyCostGbp: 2.4,
      standardExecutionMinutes: 6,
      standardVerifiedSuccessRate: 0.35,
      airllmHourlyCostGbp: 0.2,
      airllmExecutionMinutes: 55,
      airllmVerifiedSuccessRate: 0.88,
      airllmNvmeWearCostPerRunGbp: 0.012,
      useSunkOvernightCapacity: false,
      sunkElectricityOverheadPerHourGbp: 0.03
    }
  }
];

export const EconomicsLabView: React.FC = () => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>('research-baseline');
  const [scenario, setScenario] = useState<EconomicsScenarioInput>(PRESET_SCENARIOS[0].input);

  const handleSelectPreset = (presetId: string) => {
    const found = PRESET_SCENARIOS.find((p) => p.id === presetId);
    if (found) {
      setSelectedPresetId(found.id);
      setScenario({ ...found.input });
    }
  };

  const result = calculateCostPerVerifiedResult(scenario);

  return (
    <div className="space-y-10">
      {/* Header & Formula Banner */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 lg:p-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-7 space-y-2">
            <div className="text-xs font-medium text-slate-500">
              Section 04 · The Economics: When Does It Actually Save Money?
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Cost-Per-Verified-Result Economics Laboratory
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed">
              Small-VRAM marketing can obscure three major operational costs: storage footprint, PCIe/NVMe data transfer wear, and wall-clock execution time. For IDP, the true optimisation target is never cost per token or GPU memory alone—it is total execution cost divided by verified successful outcomes.
            </p>
          </div>

          <div className="lg:col-span-5 bg-slate-900 text-white rounded-lg p-5 font-mono text-xs space-y-3">
            <div className="text-slate-400">Governing IDP Economic Objective Function</div>
            <div className="text-sm sm:text-base font-semibold text-amber-300 py-2 border-y border-slate-800">
              Cost per Verified Result = Total Execution Cost ÷ Verified Successful Outcomes
            </div>
            <div className="text-slate-300 leading-relaxed font-sans text-xs">
              Cheaper hourly hardware (£0.20/hr) running 20× longer (60m vs 3m) doubles compute cost (£0.20 vs £0.10) unless executed on spare overnight capacity or yielding superior verified resolution accuracy.
            </div>
          </div>
        </div>

        {/* Scenario Selector Tabs */}
        <div className="pt-4 border-t border-slate-200 flex flex-wrap items-center gap-2">
          {PRESET_SCENARIOS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleSelectPreset(preset.id)}
              className={`px-3.5 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                selectedPresetId === preset.id
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </section>

      {/* Main Calculator Workbench */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Parameter Controls */}
        <div className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 pb-4">
            <div>
              <div className="text-xs font-medium text-slate-500">Interactive Parameters</div>
              <h2 className="text-lg font-bold text-slate-900 mt-0.5">{scenario.taskName}</h2>
            </div>
            <button
              type="button"
              onClick={() => handleSelectPreset(selectedPresetId)}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md inline-flex items-center gap-1.5 whitespace-nowrap shrink-0"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Preset</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Standard Inference Inputs */}
            <div className="space-y-4 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="font-semibold text-sm text-slate-900 border-b border-slate-200 pb-2">
                Standard Inference Baseline
              </div>

              <div>
                <label htmlFor="std-hourly-cost" className="block text-xs font-medium text-slate-700 mb-1">
                  Hourly Compute Cost (£/hr)
                </label>
                <input
                  id="std-hourly-cost"
                  type="number"
                  step="0.1"
                  min="0.05"
                  value={scenario.standardHourlyCostGbp}
                  onChange={(e) =>
                    setScenario({ ...scenario, standardHourlyCostGbp: Math.max(0.01, Number(e.target.value)) })
                  }
                  className="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-sm font-mono tabular-nums"
                />
              </div>

              <div>
                <label htmlFor="std-exec-min" className="block text-xs font-medium text-slate-700 mb-1">
                  Execution Time per Run (minutes)
                </label>
                <input
                  id="std-exec-min"
                  type="number"
                  step="1"
                  min="0.5"
                  value={scenario.standardExecutionMinutes}
                  onChange={(e) =>
                    setScenario({ ...scenario, standardExecutionMinutes: Math.max(0.5, Number(e.target.value)) })
                  }
                  className="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-sm font-mono tabular-nums"
                />
              </div>

              <div>
                <label htmlFor="std-success-rate" className="block text-xs font-medium text-slate-700 mb-1">
                  Verified Outcome Rate ({Math.round(scenario.standardVerifiedSuccessRate * 100)}%)
                </label>
                <input
                  id="std-success-rate"
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={scenario.standardVerifiedSuccessRate}
                  onChange={(e) =>
                    setScenario({ ...scenario, standardVerifiedSuccessRate: Number(e.target.value) })
                  }
                  className="w-full accent-slate-900"
                />
              </div>
            </div>

            {/* AirLLM Streamed Inputs */}
            <div className="space-y-4 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="font-semibold text-sm text-slate-900 border-b border-slate-200 pb-2">
                AirLLM Streamed Inference
              </div>

              <div>
                <label htmlFor="airllm-hourly-cost" className="block text-xs font-medium text-slate-700 mb-1">
                  Worker Hourly Cost (£/hr)
                </label>
                <input
                  id="airllm-hourly-cost"
                  type="number"
                  step="0.05"
                  min="0.01"
                  disabled={scenario.useSunkOvernightCapacity}
                  value={scenario.airllmHourlyCostGbp}
                  onChange={(e) =>
                    setScenario({ ...scenario, airllmHourlyCostGbp: Math.max(0.01, Number(e.target.value)) })
                  }
                  className="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-sm font-mono tabular-nums disabled:opacity-50"
                />
              </div>

              <div>
                <label htmlFor="airllm-exec-min" className="block text-xs font-medium text-slate-700 mb-1">
                  Streamed Execution Time (minutes)
                </label>
                <input
                  id="airllm-exec-min"
                  type="number"
                  step="1"
                  min="1"
                  value={scenario.airllmExecutionMinutes}
                  onChange={(e) =>
                    setScenario({ ...scenario, airllmExecutionMinutes: Math.max(1, Number(e.target.value)) })
                  }
                  className="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-sm font-mono tabular-nums"
                />
              </div>

              <div>
                <label htmlFor="airllm-success-rate" className="block text-xs font-medium text-slate-700 mb-1">
                  Verified Outcome Rate ({Math.round(scenario.airllmVerifiedSuccessRate * 100)}%)
                </label>
                <input
                  id="airllm-success-rate"
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={scenario.airllmVerifiedSuccessRate}
                  onChange={(e) =>
                    setScenario({ ...scenario, airllmVerifiedSuccessRate: Number(e.target.value) })
                  }
                  className="w-full accent-slate-900"
                />
              </div>
            </div>
          </div>

          {/* Sunk Overnight Capacity & NVMe Wear Controls */}
          <div className="pt-2 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
            <label className="flex items-start gap-2.5 text-xs text-slate-800 cursor-pointer">
              <input
                type="checkbox"
                checked={scenario.useSunkOvernightCapacity}
                onChange={(e) =>
                  setScenario({ ...scenario, useSunkOvernightCapacity: e.target.checked })
                }
                className="mt-0.5 w-4 h-4 rounded border-slate-300 text-slate-900"
              />
              <div>
                <span className="font-semibold block">Use Owned Overnight Spare Capacity</span>
                <span className="text-slate-500">
                  Bills only marginal electricity (£{scenario.sunkElectricityOverheadPerHourGbp.toFixed(2)}/hr) + NVMe wear.
                </span>
              </div>
            </label>

            <div>
              <label htmlFor="nvme-wear-input" className="block text-xs font-medium text-slate-700 mb-1">
                NVMe Storage Wear & I/O Overhead per Run (£)
              </label>
              <input
                id="nvme-wear-input"
                type="number"
                step="0.002"
                min="0"
                value={scenario.airllmNvmeWearCostPerRunGbp}
                onChange={(e) =>
                  setScenario({
                    ...scenario,
                    airllmNvmeWearCostPerRunGbp: Math.max(0, Number(e.target.value))
                  })
                }
                className="w-full bg-slate-50 border border-slate-300 rounded px-3 py-1.5 text-sm font-mono tabular-nums"
              />
            </div>
          </div>
        </div>

        {/* Right Column: Comparative Economic Output */}
        <div className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between space-y-6">
          <div className="space-y-5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <div className="text-xs font-medium text-slate-500">Comparative Economic Verdict</div>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                  {result.isAirllmEconomicallySuperior
                    ? 'AirLLM Streamed Lane is Economically Superior'
                    : 'Standard Fast Inference is More Economical'}
                </h3>
              </div>
              <div className="text-right font-mono tabular-nums">
                <div className="text-xs text-slate-500">Break-Even AirLLM Runtime</div>
                <div className="text-sm font-bold text-slate-900">{result.breakEvenExecutionMinutes} min</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <div className="text-xs text-slate-500">Standard Inference</div>
                <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
                  £{result.standardCostPerVerifiedResultGbp.toFixed(4)}
                </div>
                <div className="text-xs text-slate-500">Cost per Verified Result</div>
                <div className="pt-2 border-t border-slate-200 text-xs font-mono tabular-nums text-slate-600 space-y-1">
                  <div className="flex justify-between">
                    <span>Raw Compute / Run:</span>
                    <span>£{result.standardComputeCostPerRunGbp.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Verified Outcomes ({scenario.runsPerBatch} runs):</span>
                    <span>{result.standardVerifiedOutcomesCount}</span>
                  </div>
                </div>
              </div>

              <div
                className={`p-4 rounded-lg border space-y-2 ${
                  result.isAirllmEconomicallySuperior
                    ? 'bg-emerald-50/50 border-emerald-300'
                    : 'bg-amber-50/50 border-amber-300'
                }`}
              >
                <div className="text-xs text-slate-600">AirLLM Streamed Lane</div>
                <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
                  £{result.airllmCostPerVerifiedResultGbp.toFixed(4)}
                </div>
                <div className="text-xs text-slate-600">Cost per Verified Result</div>
                <div className="pt-2 border-t border-slate-200/80 text-xs font-mono tabular-nums text-slate-700 space-y-1">
                  <div className="flex justify-between">
                    <span>Compute + NVMe / Run:</span>
                    <span>£{result.airllmTotalCostPerRunGbp.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Verified Outcomes ({scenario.runsPerBatch} runs):</span>
                    <span>{result.airllmVerifiedOutcomesCount}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-700 leading-relaxed">
              <span className="font-semibold text-slate-900">Economic Synthesis: </span>
              {result.verdictSummary}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 font-mono tabular-nums">
            <span>Effective AirLLM Rate: £{result.airllmEffectiveHourlyRateGbp.toFixed(3)}/hr</span>
            <span>
              Net Delta: {result.costDeltaPerVerifiedResultGbp <= 0 ? '' : '+'}£
              {result.costDeltaPerVerifiedResultGbp.toFixed(4)} / verified outcome
            </span>
          </div>
        </div>
      </section>
    </div>
  );
};
