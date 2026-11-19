/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  SlidersHorizontal,
  ShieldAlert,
  Zap,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Play,
  Lock,
  Flame,
  Check,
  Server,
  Workflow,
  Cpu,
  Layers,
  Clock,
  Bot,
  Globe,
  Terminal,
} from 'lucide-react';
import {
  SurfaceType,
  SurfaceLatencyCapConfig,
  InvariantRule,
} from '../types/optimus';
import {
  DEFAULT_SURFACE_LATENCY_CAPS,
  evaluateSurfaceLatencyViolation,
} from '../utils/optimus-engine';

interface AlertThresholdConfigProps {
  latencyCaps: Record<SurfaceType, SurfaceLatencyCapConfig>;
  onUpdateLatencyCap: (
    surfaceId: SurfaceType,
    updatedCap: Partial<SurfaceLatencyCapConfig>
  ) => void;
  onResetToBaselines: () => void;
  onSimulateViolationTest?: (surfaceId: SurfaceType, simulatedLatency: number) => void;
}

const SURFACE_ICONS: Record<SurfaceType, React.ComponentType<{ className?: string }>> = {
  git_commit_push: Terminal,
  ci_cd_pipeline: Workflow,
  microservice_engine: Cpu,
  infra_as_code: Layers,
  scheduled_job: Clock,
  autonomous_agent: Bot,
  network_ingress_egress: Globe,
  runnable_script: Server,
};

export const AlertThresholdConfig: React.FC<AlertThresholdConfigProps> = ({
  latencyCaps,
  onUpdateLatencyCap,
  onResetToBaselines,
  onSimulateViolationTest,
}) => {
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<'ALL' | 'SOURCE' | 'RUNTIME' | 'INFRA' | 'AI'>('ALL');
  const [testResultNotice, setTestResultNotice] = useState<{
    surfaceId: SurfaceType;
    message: string;
    isViolation: boolean;
    severity: 'CRITICAL' | 'WARNING' | 'NOMINAL';
  } | null>(null);
  const [savedNotice, setSavedNotice] = useState<string | null>(null);

  const surfaceList = Object.values(latencyCaps);

  const filteredSurfaces = surfaceList.filter((s) => {
    if (selectedCategoryFilter === 'ALL') return true;
    if (selectedCategoryFilter === 'SOURCE') return s.surfaceId === 'git_commit_push' || s.surfaceId === 'ci_cd_pipeline';
    if (selectedCategoryFilter === 'RUNTIME') return s.surfaceId === 'microservice_engine' || s.surfaceId === 'scheduled_job' || s.surfaceId === 'runnable_script';
    if (selectedCategoryFilter === 'INFRA') return s.surfaceId === 'infra_as_code' || s.surfaceId === 'network_ingress_egress';
    if (selectedCategoryFilter === 'AI') return s.surfaceId === 'autonomous_agent';
    return true;
  });

  const averageCap = Math.round(
    surfaceList.reduce((acc, curr) => acc + curr.maxLatencyCapMs, 0) / surfaceList.length
  );

  const strictestCap = Math.min(...surfaceList.map((s) => s.maxLatencyCapMs));
  const strictestSurface = surfaceList.find((s) => s.maxLatencyCapMs === strictestCap)?.surfaceName || 'Network';

  const handleSliderChange = (surfaceId: SurfaceType, value: number) => {
    onUpdateLatencyCap(surfaceId, { maxLatencyCapMs: value });
    setSavedNotice(`Updated latency cap for ${surfaceId} to ${value}ms.`);
    setTimeout(() => setSavedNotice(null), 3000);
  };

  const handleModeChange = (
    surfaceId: SurfaceType,
    mode: 'HARD_KILL_SWITCH' | 'AUTO_QUARANTINE' | 'WARN_AUDIT_LOG'
  ) => {
    onUpdateLatencyCap(surfaceId, { enforcementMode: mode });
    setSavedNotice(`Enforcement mode for ${surfaceId} updated to ${mode}.`);
    setTimeout(() => setSavedNotice(null), 3000);
  };

  const handleRunSimulationTest = (surfaceId: SurfaceType) => {
    const cap = latencyCaps[surfaceId];
    // Simulate latency that exceeds cap by 35% to test violation trigger
    const simulatedLatency = Math.round(cap.maxLatencyCapMs * 1.35);

    const evaluation = evaluateSurfaceLatencyViolation(surfaceId, simulatedLatency, cap);

    setTestResultNotice({
      surfaceId,
      message: `Simulated ${simulatedLatency}ms probe against ${cap.maxLatencyCapMs}ms cap. ${evaluation.enforcementAction}`,
      isViolation: evaluation.isViolation,
      severity: evaluation.severity,
    });

    if (onSimulateViolationTest) {
      onSimulateViolationTest(surfaceId, simulatedLatency);
    }

    setTimeout(() => {
      setTestResultNotice(null);
    }, 6000);
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5">
      {/* Notifications */}
      {savedNotice && (
        <div className="p-3 bg-emerald-950/80 border border-emerald-700/80 rounded-lg text-emerald-300 text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{savedNotice}</span>
        </div>
      )}

      {testResultNotice && (
        <div
          className={`p-3.5 rounded-lg text-xs font-mono flex items-start gap-2.5 border ${
            testResultNotice.isViolation
              ? 'bg-red-950/80 border-red-700/80 text-red-200'
              : 'bg-emerald-950/80 border-emerald-700/80 text-emerald-200'
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-bold uppercase tracking-wider text-[11px] text-red-300">
              Automated Violation Gate Response Triggered ({testResultNotice.surfaceId})
            </div>
            <p className="text-[11px] leading-relaxed text-slate-300">
              {testResultNotice.message}
            </p>
          </div>
        </div>
      )}

      {/* Header and Baseline Reset */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="text-amber-400 font-semibold flex items-center gap-1">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>ALERT THRESHOLD CONFIGURATION</span>
            </span>
            <span aria-hidden="true">·</span>
            <span>PER-SURFACE LATENCY CAPS</span>
            <span aria-hidden="true">·</span>
            <span className="text-indigo-400 font-mono">AUTOMATED VIOLATIONS</span>
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight mt-1">
            Surface Latency Caps & Automated Violation Triggers
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-snug mt-1">
            Configure specific maximum latency boundaries for every execution surface across the estate. If observed P99 tail latency breaches the threshold, Project Optimus triggers an automated violation gate (Hard Kill-Switch or Sandbox Quarantine).
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onResetToBaselines}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
            <span>Reset Day 0 Baselines</span>
          </button>
        </div>
      </div>

      {/* Governance Strip: 4 KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Configured Surfaces</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white tabular-nums">
            8 / 8 Armed
          </div>
          <div className="text-[11px] text-slate-500">100% surface coverage</div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Average Latency Cap</span>
            <Zap className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-sky-400 tabular-nums">
            {averageCap}ms
          </div>
          <div className="text-[11px] text-slate-500">Estate-wide SLA bound</div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Strictest Boundary</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400 tabular-nums">
            {strictestCap}ms
          </div>
          <div className="text-[11px] text-slate-500">{strictestSurface}</div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Enforcement Mode</span>
            <Lock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 tabular-nums">
            Zero Bypass
          </div>
          <div className="text-[11px] text-slate-500">Cryptographic push lock</div>
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className="flex items-center gap-1.5 border-b border-slate-800 pb-2 text-xs font-mono overflow-x-auto">
        <span className="text-slate-500 text-[11px] uppercase mr-1">Surface Filter:</span>
        <button
          onClick={() => setSelectedCategoryFilter('ALL')}
          className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
            selectedCategoryFilter === 'ALL'
              ? 'bg-slate-800 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          All Surfaces (8)
        </button>
        <button
          onClick={() => setSelectedCategoryFilter('SOURCE')}
          className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
            selectedCategoryFilter === 'SOURCE'
              ? 'bg-slate-800 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Source & CI/CD (2)
        </button>
        <button
          onClick={() => setSelectedCategoryFilter('RUNTIME')}
          className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
            selectedCategoryFilter === 'RUNTIME'
              ? 'bg-slate-800 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Runtime & Compute (3)
        </button>
        <button
          onClick={() => setSelectedCategoryFilter('INFRA')}
          className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
            selectedCategoryFilter === 'INFRA'
              ? 'bg-slate-800 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Infra & Mesh (2)
        </button>
        <button
          onClick={() => setSelectedCategoryFilter('AI')}
          className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
            selectedCategoryFilter === 'AI'
              ? 'bg-slate-800 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          AI Agents (1)
        </button>
      </div>

      {/* Surface Threshold Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredSurfaces.map((config) => {
          const IconComponent = SURFACE_ICONS[config.surfaceId] || Terminal;
          const isHardGate = config.enforcementMode === 'HARD_KILL_SWITCH';

          return (
            <div
              key={config.surfaceId}
              className={`p-4 rounded-xl bg-slate-950 border transition-all space-y-3.5 ${
                isHardGate
                  ? 'border-slate-800 hover:border-slate-700'
                  : 'border-purple-900/50 hover:border-purple-700/60'
              }`}
            >
              {/* Card Top: Surface Info & Enforcement Mode Badge */}
              <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-indigo-400 shrink-0">
                    <IconComponent className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">
                      {config.surfaceName}
                    </h4>
                    <span className="text-[11px] font-mono text-slate-500">
                      {config.category}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded shrink-0 ${
                    config.enforcementMode === 'HARD_KILL_SWITCH'
                      ? 'bg-red-950 text-red-300 border border-red-800'
                      : config.enforcementMode === 'AUTO_QUARANTINE'
                      ? 'bg-purple-950 text-purple-300 border border-purple-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}
                >
                  {config.enforcementMode === 'HARD_KILL_SWITCH'
                    ? 'HARD KILL-SWITCH'
                    : config.enforcementMode === 'AUTO_QUARANTINE'
                    ? 'AUTO-QUARANTINE'
                    : 'AUDIT LOG'}
                </span>
              </div>

              {/* Baseline vs Current Cap Comparison */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                <div className="p-2 rounded bg-slate-900/90 border border-slate-800/80">
                  <span className="text-[10px] text-slate-500 block uppercase">Day 0 Baseline</span>
                  <span className="font-bold text-emerald-400">{config.baselineLatencyMs}ms</span>
                </div>
                <div className="p-2 rounded bg-slate-900/90 border border-slate-800/80">
                  <span className="text-[10px] text-slate-500 block uppercase">Configured Cap</span>
                  <span className="font-bold text-amber-300 text-sm">{config.maxLatencyCapMs}ms</span>
                </div>
                <div className="p-2 rounded bg-slate-900/90 border border-slate-800/80">
                  <span className="text-[10px] text-slate-500 block uppercase">Violation Risk</span>
                  <span
                    className={`font-bold ${
                      config.maxLatencyCapMs <= config.baselineLatencyMs * 1.5
                        ? 'text-red-400'
                        : 'text-sky-400'
                    }`}
                  >
                    {Math.round((config.maxLatencyCapMs / config.baselineLatencyMs) * 100)}%
                  </span>
                </div>
              </div>

              {/* Slider Control for Specific Latency Cap */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-400 text-[11px]">Maximum Latency Cap:</span>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      min={5}
                      max={300}
                      value={config.maxLatencyCapMs}
                      onChange={(e) =>
                        handleSliderChange(
                          config.surfaceId,
                          Math.max(5, Math.min(300, Number(e.target.value) || 5))
                        )
                      }
                      className="w-16 px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-white font-mono text-xs text-right focus:outline-none focus:border-indigo-500"
                    />
                    <span className="text-slate-400 text-xs">ms</span>
                  </div>
                </div>

                <input
                  type="range"
                  min={5}
                  max={200}
                  step={1}
                  value={config.maxLatencyCapMs}
                  onChange={(e) =>
                    handleSliderChange(config.surfaceId, Number(e.target.value))
                  }
                  className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />

                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>5ms (eBPF ultra-fast)</span>
                  <span>100ms (SLA bound)</span>
                  <span>200ms (Hard ceiling)</span>
                </div>
              </div>

              {/* Enforcement Action Triggered When Exceeded */}
              <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800/80 text-[11px] space-y-1">
                <span className="text-slate-500 font-mono uppercase text-[10px] flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-red-400" />
                  <span>Automated Violation Action (If Exceeded)</span>
                </span>
                <p className="text-slate-300 leading-snug">
                  {config.autoRemediationAction}
                </p>
              </div>

              {/* Enforcement Mode Selector & Live Test Trigger */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 border-t border-slate-800/80">
                <div className="flex items-center gap-1 text-[11px] font-mono">
                  <span className="text-slate-500 text-[10px]">Action:</span>
                  <select
                    value={config.enforcementMode}
                    onChange={(e) =>
                      handleModeChange(
                        config.surfaceId,
                        e.target.value as 'HARD_KILL_SWITCH' | 'AUTO_QUARANTINE' | 'WARN_AUDIT_LOG'
                      )
                    }
                    className="bg-slate-900 text-slate-200 border border-slate-800 rounded px-2 py-1 text-[11px] focus:outline-none focus:border-indigo-500"
                  >
                    <option value="HARD_KILL_SWITCH">Hard Kill-Switch (Block)</option>
                    <option value="AUTO_QUARANTINE">Auto-Quarantine (Sandbox)</option>
                    <option value="WARN_AUDIT_LOG">Audit Warning (Log Only)</option>
                  </select>
                </div>

                <button
                  onClick={() => handleRunSimulationTest(config.surfaceId)}
                  className="px-2.5 py-1 text-[11px] font-semibold rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1 shadow-sm whitespace-nowrap self-end sm:self-auto"
                >
                  <Play className="w-3 h-3" />
                  <span>Test Trigger (+35%)</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
