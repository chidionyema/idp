import React, { useState } from 'react';
import { Sliders, Shield, AlertTriangle, Power, Zap, CheckCircle2, RotateCw } from 'lucide-react';
import { EstateState } from '../../utils/estateLogic';

interface OmegaControlViewProps {
  estateState: EstateState;
  onApplyParameterTuning: (params: {
    maxConcurrency: number;
    spatialProjectionRateHz: number;
    transcriptFirewallStrictness: 'strict' | 'standard' | 'bypass';
  }) => void;
  onRemediateLegion: () => void;
  onVerifyGreenlane: () => void;
}

export const OmegaControlView: React.FC<OmegaControlViewProps> = ({
  estateState,
  onApplyParameterTuning,
  onRemediateLegion,
  onVerifyGreenlane,
}) => {
  const [concurrency, setConcurrency] = useState(estateState.operationalParameters.maxConcurrency);
  const [spatialRate, setSpatialRate] = useState(estateState.operationalParameters.spatialProjectionRateHz);
  const [firewallStrictness, setFirewallStrictness] = useState(estateState.operationalParameters.transcriptFirewallStrictness);
  const [appliedSuccess, setAppliedSuccess] = useState(false);

  const handleApply = () => {
    onApplyParameterTuning({
      maxConcurrency: concurrency,
      spatialProjectionRateHz: spatialRate,
      transcriptFirewallStrictness: firewallStrictness,
    });
    setAppliedSuccess(true);
    setTimeout(() => setAppliedSuccess(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Executive Authority</span>
            <span>/</span>
            <span className="text-sky-400">Omega Deep Operational Control</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Founder Direct Intervention &amp; Parameter Overrides
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            High-privilege orchestration switches: fleet concurrency calibration, firewall enforcement, and emergency subsystem recovery.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleApply}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors shadow-md"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Apply Operational Overrides</span>
          </button>
        </div>
      </div>

      {appliedSuccess && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>Operational parameters applied across all active clusters. Live estate updated.</span>
        </div>
      )}

      {/* Main Grid: Parameters + Emergency Protocol Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sliders and Operational Parameter Controls */}
        <div className="lg:col-span-7 rounded-2xl border border-slate-800 bg-slate-950/80 p-5 space-y-5">
          <div className="pb-3 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-sky-400" />
              Runtime Tuning Parameters
            </h3>
            <span className="text-xs font-mono text-slate-400">Dynamic Live Calibration</span>
          </div>

          {/* Max Concurrency Slider */}
          <div>
            <div className="flex justify-between items-center text-xs font-mono mb-2">
              <span className="text-slate-300">Global Fleet Concurrency Cap</span>
              <span className="text-sky-400 font-bold">{concurrency} Threads</span>
            </div>
            <input
              type="range"
              min="8"
              max="64"
              step="4"
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              className="w-full accent-sky-400 bg-slate-800 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-500 font-mono mt-1">
              <span>8 (Conservative)</span>
              <span>32 (Nominal)</span>
              <span>64 (Hyper-Parallel)</span>
            </div>
          </div>

          {/* Spatial Projection Rate Slider */}
          <div>
            <div className="flex justify-between items-center text-xs font-mono mb-2">
              <span className="text-slate-300">2100 Spatial Projection Refresh Rate</span>
              <span className="text-sky-400 font-bold">{spatialRate} Hz</span>
            </div>
            <input
              type="range"
              min="30"
              max="120"
              step="15"
              value={spatialRate}
              onChange={(e) => setSpatialRate(Number(e.target.value))}
              className="w-full accent-sky-400 bg-slate-800 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-500 font-mono mt-1">
              <span>30 Hz (Eco)</span>
              <span>60 Hz (Standard)</span>
              <span>120 Hz (Ultra-Fluid)</span>
            </div>
          </div>

          {/* Transcript Firewall Strictness */}
          <div>
            <div className="text-xs font-mono text-slate-300 mb-2">
              Transcript Firewall Boundary Strictness
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(['strict', 'standard', 'bypass'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setFirewallStrictness(mode)}
                  className={`py-2 px-3 text-xs font-mono rounded-lg border uppercase transition-colors ${
                    firewallStrictness === mode
                      ? 'bg-sky-600/30 border-sky-400 text-sky-200 font-bold'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Founder Direct Overrides & Emergency Triggers */}
        <div className="lg:col-span-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <div className="pb-3 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              Direct Founder Actions
            </h3>
            <span className="text-xs font-mono text-slate-400">Immediate Execution</span>
          </div>

          {/* Quick Action: Legion Recovery Run #42412348112 */}
          <div className="p-3.5 rounded-xl border border-sky-500/30 bg-slate-950/60">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">Legion Recovery #42412348112</span>
              <span className="text-xs font-mono text-amber-400">Queued</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Remediate non-ASCII encoding violation and clear trusted push firewall.
            </p>
            <button
              onClick={onRemediateLegion}
              className="mt-3 w-full py-2 px-3 text-xs font-semibold rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition-colors"
            >
              Force Execute Legion Recovery Run
            </button>
          </div>

          {/* Quick Action: Greenlane Invariant Verification */}
          <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-slate-950/60">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">Greenlane Invariant Sweep</span>
              <span className="text-xs font-mono text-emerald-400">
                {estateState.greenlaneStatus.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Force synchronous verification of all 4 continuous invariants across Genesis nodes.
            </p>
            <button
              onClick={onVerifyGreenlane}
              className="mt-3 w-full py-2 px-3 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
            >
              Verify Greenlane Synchronization
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
