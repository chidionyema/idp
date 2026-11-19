/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Compass,
  Zap,
  TrendingUp,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
  Clock,
  Cpu,
  Layers,
  ChevronDown,
  ChevronUp,
  Flame,
  Fingerprint,
  Sliders,
  Play,
  ArrowUpRight,
  Sun,
  Moon,
  Radio
} from 'lucide-react';
import {
  INITIAL_ANTICIPATORY_ACTIONS,
  INITIAL_BAR_ELEVATION_METRICS,
  getCircadianFlowSensory,
  enactAnticipatoryAction,
  ratchetBarElevation,
  AnticipatoryActionItem,
  BarElevationMetric,
  CircadianFlowSensory
} from '../lib/protocolEngine.ts';

interface AnticipatoryMindReaderHudProps {
  onOpenFleetCouncil?: () => void;
  onOpenSync?: () => void;
}

export const AnticipatoryMindReaderHud: React.FC<AnticipatoryMindReaderHudProps> = ({
  onOpenFleetCouncil,
  onOpenSync
}) => {
  const [actions, setActions] = useState<AnticipatoryActionItem[]>(INITIAL_ANTICIPATORY_ACTIONS);
  const [metrics, setMetrics] = useState<BarElevationMetric[]>(INITIAL_BAR_ELEVATION_METRICS);
  const [sensory, setSensory] = useState<CircadianFlowSensory>(getCircadianFlowSensory());
  const [activeTab, setActiveTab] = useState<'anticipatory' | 'bar-elevation' | 'circadian'>('anticipatory');
  const [isEnacting, setIsEnacting] = useState<string | null>(null);

  // Update circadian sensory every 10 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setSensory(getCircadianFlowSensory());
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const handleEnact = (actionId: string) => {
    setIsEnacting(actionId);
    setTimeout(() => {
      const { updatedActions } = enactAnticipatoryAction(actionId, actions);
      setActions(updatedActions);
      setIsEnacting(null);
    }, 400);
  };

  const handleRatchet = (metricId: string) => {
    const { updatedMetrics } = ratchetBarElevation(metricId, metrics);
    setMetrics(updatedMetrics);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      
      {/* Background Ambient Aura modulated by London Circadian Rhythm */}
      <div className={`absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl ${sensory.ambientChromaModulation} blur-3xl pointer-events-none`} />

      {/* Header Bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 mb-6 relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800 flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 animate-pulse text-purple-400" />
              CONSTITUTIONAL CANON §14
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-cyan-400" />
              PREDICTIVE PROACTION ENGAGED
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
              ZERO-PROMPT DNA
            </span>
          </div>

          <h2 className="text-xl sm:text-2xl font-black tracking-tight text-white flex items-center gap-2.5">
            <span>Anticipatory Mind-Reader HUD &amp; Bar-Elevation Matrix</span>
            <Flame className="w-5 h-5 text-amber-400 animate-pulse" />
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-3xl">
            Pre-computing high-leverage sovereign decisions and auto-ratcheting quality standards without waiting for prompts.
            Adapting in real time to the Founder's circadian cadence in London.
          </p>
        </div>

        {/* Circadian Phase Pill */}
        <div className="bg-slate-950/80 border border-slate-800 px-4 py-2.5 rounded-xl font-mono text-xs flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-indigo-950/80 border border-indigo-800/80 flex items-center justify-center text-indigo-400">
            {sensory.londonHour >= 6 && sensory.londonHour < 18 ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
          </div>
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">London Circadian Phase</div>
            <div className="text-xs font-bold text-slate-200">{sensory.detectedPhase.replace(/_/g, ' ')}</div>
            <div className="text-[10px] text-cyan-400">{sensory.deflectedFrictionItemsCount} friction items deflected</div>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 mb-5">
        <button
          onClick={() => setActiveTab('anticipatory')}
          className={`px-3.5 py-1.5 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'anticipatory'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Zap className="w-4 h-4 text-cyan-400" />
          <span>Pre-Computed Actions ({actions.filter(a => a.status !== 'ONE_TAP_ENACTED').length} Ready)</span>
        </button>

        <button
          onClick={() => setActiveTab('bar-elevation')}
          className={`px-3.5 py-1.5 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'bar-elevation'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          <span>Continuous Bar Elevation Standards</span>
        </button>

        <button
          onClick={() => setActiveTab('circadian')}
          className={`px-3.5 py-1.5 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'circadian'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Clock className="w-4 h-4 text-purple-400" />
          <span>Circadian Resonance &amp; Friction Deflector</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: PRE-COMPUTED SOVEREIGN ACTIONS */}
      {/* ========================================================================= */}
      {activeTab === 'anticipatory' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {actions.map((act) => (
              <div
                key={act.id}
                className={`p-5 rounded-xl border transition-all ${
                  act.status === 'ONE_TAP_ENACTED'
                    ? 'bg-slate-950/40 border-emerald-800/60'
                    : 'bg-slate-950/80 border-slate-800 hover:border-cyan-800/70 shadow-md'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Sponsor: {act.agentSponsor}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                    act.status === 'ONE_TAP_ENACTED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold'
                      : 'bg-cyan-950 text-cyan-300 border border-cyan-800 animate-pulse'
                  }`}>
                    {act.status}
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white mb-1">{act.title}</h4>
                <p className="text-xs text-slate-300 mb-3">{act.rationale}</p>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 font-mono text-xs space-y-1.5 mb-4">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Predicted Leverage (R_asym):</span>
                    <span className="text-emerald-400 font-bold">{act.predictedLeverage}x</span>
                  </div>
                  <div className="text-[11px] text-slate-300">
                    <span className="text-slate-400">Solution:</span> {act.precomputedSolution}
                  </div>
                  <div className="text-[10px] text-slate-500 truncate">
                    <span className="text-slate-400">Test Proof:</span> {act.autoTestProof}
                  </div>
                  {act.enactedReceipt && (
                    <div className="text-[10px] text-indigo-300 truncate">
                      <span className="text-slate-400">Receipt:</span> {act.enactedReceipt} ({act.enactedLatencyMs}ms)
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                  <span className="text-[10px] font-mono text-slate-500">
                    Category: {act.category}
                  </span>

                  {act.status !== 'ONE_TAP_ENACTED' ? (
                    <button
                      onClick={() => handleEnact(act.id)}
                      disabled={isEnacting === act.id}
                      className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-md shadow-cyan-950 active:scale-95 disabled:opacity-50"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      <span>{isEnacting === act.id ? 'Enacting...' : '1-Tap Enact'}</span>
                    </button>
                  ) : (
                    <span className="text-xs font-mono text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Enacted &amp; Attested</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CONTINUOUS BAR ELEVATION STANDARDS */}
      {/* ========================================================================= */}
      {activeTab === 'bar-elevation' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 mb-4">
            <div className="text-xs font-mono font-bold text-white mb-1 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span>Machine-Enforced Upward Standard Ratchet (§14.2)</span>
            </div>
            <p className="text-xs text-slate-400">
              The estate automatically tightens latency ceilings, raises asymmetry ratios, and deepens aesthetic baselines.
              Once a higher bar is achieved, the system locks the new threshold permanently—regression to the historical median is strictly prohibited.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {metrics.map((m) => (
              <div
                key={m.id}
                className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                    <span>{m.invariantRule}</span>
                    <span className="text-cyan-400 font-bold">Ratchet #{m.ratchetCount}</span>
                  </div>
                  <h4 className="text-xs font-bold text-white mb-2">{m.dimension}</h4>

                  <div className="space-y-1.5 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Old Canonical:</span>
                      <span className="text-slate-400">{m.canonicalBaseline}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Elevated Standard:</span>
                      <span className="text-cyan-300 font-bold">{m.elevatedBar}</span>
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-slate-800">
                      <span className="text-slate-300">Live Attestation:</span>
                      <span className="text-emerald-400 font-bold">{m.currentAttestation}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleRatchet(m.id)}
                  className="w-full py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer hover:border-cyan-500"
                >
                  <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Elevate Standard Bar</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: CIRCADIAN RESONANCE & FRICTION DEFLECTOR */}
      {/* ========================================================================= */}
      {activeTab === 'circadian' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
          
          {/* Circadian Resonance Card */}
          <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-4 h-4 text-purple-400" />
                <span>London Circadian Tuning (§14.4)</span>
              </span>
              <span className="text-purple-300 text-[11px]">UK Prime</span>
            </div>

            <p className="text-slate-300 font-sans text-xs leading-relaxed">
              {sensory.phaseDescription}
            </p>

            <div className="space-y-2 text-[11px]">
              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Recommended DoF Containment:</span>
                <span className="text-cyan-300 font-bold">{sensory.autoDofRecommendation}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Cognitive Shielding Protocol:</span>
                <span className="text-emerald-400 font-bold">ACTIVE (100% Noise Muted)</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Ambient UI Palette:</span>
                <span className="text-indigo-300 font-bold">Dynamically Calibrated</span>
              </div>
            </div>
          </div>

          {/* Autonomous Friction Deflector Log */}
          <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Autonomous Friction Deflector (§1.4 / §14.3)</span>
              </span>
              <span className="text-emerald-400 text-[11px]">Delta_founder = 0</span>
            </div>

            <div className="space-y-2 text-[11px]">
              <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800/80 flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-slate-200 font-bold">Credential Header Hygiene:</span>
                  <div className="text-slate-400">Stripped trailing whitespace and quotes from DeepSeek keys automatically.</div>
                </div>
              </div>

              <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800/80 flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-slate-200 font-bold">503 Circuit Breaker Auto-Fallback:</span>
                  <div className="text-slate-400">Configured automatic exponential backoff to Gemini-2.5-Pro; 0 founder interventions.</div>
                </div>
              </div>

              <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800/80 flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-slate-200 font-bold">Release Bundle Staging:</span>
                  <div className="text-slate-400">Pre-compiled olat-estate-genesis-main.bundle ready for 1-click Argon delivery.</div>
                </div>
              </div>
            </div>

          </div>

        </div>
      )}

    </div>
  );
};
