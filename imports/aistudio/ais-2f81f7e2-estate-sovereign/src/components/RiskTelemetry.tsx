import React from 'react';
import { FinancialHealthMetrics } from '../types/estate';
import { AlertOctagon, Heart, DollarSign, ShieldAlert, Zap, PauseCircle, PlayCircle, Moon, Activity } from 'lucide-react';

interface RiskTelemetryProps {
  metrics: FinancialHealthMetrics;
  isEmergencyFrozen: boolean;
  isHealthShieldActive: boolean;
  onToggleEmergencyFreeze: () => void;
  onToggleHealthShield: () => void;
  onPurgeUnanchoredThreads: () => void;
}

export const RiskTelemetry: React.FC<RiskTelemetryProps> = ({
  metrics,
  isEmergencyFrozen,
  isHealthShieldActive,
  onToggleEmergencyFreeze,
  onToggleHealthShield,
  onPurgeUnanchoredThreads,
}) => {
  return (
    <div className="space-y-6">
      {/* Red-Line Territory Alert Header */}
      <div className={`rounded-xl p-5 border transition-all ${
        isEmergencyFrozen 
          ? 'bg-amber-950/30 border-amber-800/80' 
          : 'bg-red-950/40 border-red-800/80 shadow-lg shadow-red-950/20'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-red-400 font-bold">
              <AlertOctagon className="w-4 h-4 text-red-400" />
              <span>Red-Line Territory Alert</span>
              <span className="text-neutral-600">/</span>
              <span>Founder Sovereign Protection Act</span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              Treasury Runway &amp; Founder Health Telemetry
            </h1>
            <p className="text-xs md:text-sm text-neutral-300 max-w-3xl leading-relaxed">
              Addressing the critical reality: Mindless agent churn without capital and health risk management destroys estates. 
              Real-time telemetry anchors capital burn to delivered value and shields the Founder from continuous drift.
            </p>
          </div>

          {/* Emergency Sovereign Actions */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={onToggleEmergencyFreeze}
              className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center gap-2 ${
                isEmergencyFrozen
                  ? 'bg-emerald-500 hover:bg-emerald-400 text-neutral-950 shadow'
                  : 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/30 animate-pulse'
              }`}
            >
              {isEmergencyFrozen ? <PlayCircle className="w-4 h-4" /> : <PauseCircle className="w-4 h-4" />}
              <span>{isEmergencyFrozen ? 'Resume Controlled Operations' : 'Emergency Estate Freeze'}</span>
            </button>

            <button
              onClick={onToggleHealthShield}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors border cursor-pointer flex items-center gap-2 ${
                isHealthShieldActive
                  ? 'bg-blue-900/60 text-blue-200 border-blue-700'
                  : 'bg-neutral-900 text-neutral-300 border-neutral-700 hover:bg-neutral-800'
              }`}
            >
              <Moon className="w-4 h-4 text-blue-400" />
              <span>{isHealthShieldActive ? 'Health Shield: Active' : 'Engage Health Shield'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Two High-Priority Telemetry Hubs: Treasury & Founder Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hub 1: Financial Runway Defense */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-wider">
              <DollarSign className="w-4 h-4" />
              <span>Treasury Defense Telemetry</span>
            </div>
            <span className="font-mono text-xs text-neutral-400">
              Runway: <span className="text-white font-bold">{metrics.runwayMonths.toFixed(1)} Months</span>
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3.5 bg-neutral-950 rounded-lg border border-neutral-800">
              <div className="text-xs text-neutral-400">Total Treasury Balance</div>
              <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">
                ${metrics.totalTreasuryUSD.toLocaleString()}
              </div>
              <div className="text-[11px] text-neutral-500 mt-1">Sovereign liquid reserves</div>
            </div>

            <div className="p-3.5 bg-neutral-950 rounded-lg border border-neutral-800">
              <div className="text-xs text-neutral-400">Daily Burn Velocity</div>
              <div className="text-xl font-bold font-mono text-amber-400 tabular-nums mt-1">
                ${metrics.dailyBurnUSD.toFixed(0)} <span className="text-xs text-neutral-500 font-normal">/ day</span>
              </div>
              <div className="text-[11px] text-neutral-500 mt-1">${metrics.monthlyBurnUSD.toLocaleString()} / month</div>
            </div>
          </div>

          {/* Burn Allocation Vectors */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-neutral-300">Burn Vectors &amp; Allocations:</div>
            
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-neutral-400">
                <span>Autonomous Agent Inference &amp; Context:</span>
                <span className="text-white">$142 / day (45%)</span>
              </div>
              <div className="w-full h-1.5 bg-neutral-950 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full w-[45%]" />
              </div>

              <div className="flex justify-between text-neutral-400 pt-1">
                <span>Infrastructure &amp; Server Pipelines:</span>
                <span className="text-white">$98 / day (31%)</span>
              </div>
              <div className="w-full h-1.5 bg-neutral-950 rounded-full overflow-hidden">
                <div className="bg-blue-500 h-full w-[31%]" />
              </div>

              <div className="flex justify-between text-neutral-400 pt-1">
                <span>Legal, Filings &amp; Contingency:</span>
                <span className="text-white">$73 / day (24%)</span>
              </div>
              <div className="w-full h-1.5 bg-neutral-950 rounded-full overflow-hidden">
                <div className="bg-purple-500 h-full w-[24%]" />
              </div>
            </div>
          </div>

          {/* Burn Containment Quick Action */}
          <div className="pt-2 border-t border-neutral-800 flex items-center justify-between">
            <div className="text-xs text-neutral-400">
              <span>Unanchored Agent Threads: </span>
              <span className={`font-mono font-bold ${metrics.unanchoredAgentThreads > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                {metrics.unanchoredAgentThreads} Active
              </span>
            </div>

            <button
              onClick={onPurgeUnanchoredThreads}
              className="px-3 py-1.5 bg-red-950/60 hover:bg-red-900/60 text-red-300 border border-red-800/80 rounded-lg text-xs font-medium transition-colors cursor-pointer"
            >
              Purge Unanchored Threads
            </button>
          </div>
        </div>

        {/* Hub 2: Founder Health & Cognitive Shield */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2 text-xs font-mono text-red-400 uppercase tracking-wider">
              <Heart className="w-4 h-4 text-red-400" />
              <span>Founder Cognitive &amp; Health Shield</span>
            </div>
            <span className="font-mono text-xs text-neutral-400">
              Health Status: <span className="text-amber-400 font-bold">Strain Warning</span>
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3.5 bg-neutral-950 rounded-lg border border-neutral-800">
              <div className="text-xs text-neutral-400">Cognitive Load Index</div>
              <div className="text-xl font-bold font-mono text-amber-400 tabular-nums mt-1">
                {metrics.founderCognitiveLoadIndex} <span className="text-xs text-neutral-500 font-normal">/ 100</span>
              </div>
              <div className="text-[11px] text-red-400 mt-1">Exceeds ideal bound (&le; 55)</div>
            </div>

            <div className="p-3.5 bg-neutral-950 rounded-lg border border-neutral-800">
              <div className="text-xs text-neutral-400">Nightly Recovery Sleep</div>
              <div className="text-xl font-bold font-mono text-blue-400 tabular-nums mt-1">
                {metrics.founderRestHoursPerNight} <span className="text-xs text-neutral-500 font-normal">hrs</span>
              </div>
              <div className="text-[11px] text-neutral-500 mt-1">Target &ge; 7.5 hrs</div>
            </div>
          </div>

          {/* Biological Guardrails */}
          <div className="space-y-3">
            <div className="text-xs font-semibold text-neutral-300">Cognitive Stressor Decomposition:</div>
            
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-lg bg-neutral-950 border border-neutral-800 flex justify-between items-center">
                <div>
                  <div className="text-white font-medium">Continuous Operational Drift</div>
                  <div className="text-neutral-500 text-[11px]">{metrics.founderContinuousDriftHours} hrs without anchor reset</div>
                </div>
                <span className="text-red-400 font-mono text-[11px]">HIGH STRAIN</span>
              </div>

              <div className="p-2.5 rounded-lg bg-neutral-950 border border-neutral-800 flex justify-between items-center">
                <div>
                  <div className="text-white font-medium">Mindless Agent Text Noise</div>
                  <div className="text-neutral-500 text-[11px]">Filtered via Sovereign Edict 02</div>
                </div>
                <span className="text-emerald-400 font-mono text-[11px]">CONTAINED</span>
              </div>

              <div className="p-2.5 rounded-lg bg-neutral-950 border border-neutral-800 flex justify-between items-center">
                <div>
                  <div className="text-white font-medium">Missing Artifact Blind Spot</div>
                  <div className="text-neutral-500 text-[11px]">Eradicated via Vault Provenance</div>
                </div>
                <span className="text-emerald-400 font-mono text-[11px]">RESOLVED</span>
              </div>
            </div>
          </div>

          {/* Health Shield Status */}
          <div className="pt-2 border-t border-neutral-800 flex items-center justify-between">
            <div className="text-xs text-neutral-400">
              Shield Status: <span className="text-neutral-200 font-medium">{isHealthShieldActive ? 'Enforcing Rest Hours' : 'Standby'}</span>
            </div>
            <button
              onClick={onToggleHealthShield}
              className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-lg text-xs font-medium transition-colors cursor-pointer"
            >
              {isHealthShieldActive ? 'Adjust Thresholds' : 'Activate Biological Shield'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
