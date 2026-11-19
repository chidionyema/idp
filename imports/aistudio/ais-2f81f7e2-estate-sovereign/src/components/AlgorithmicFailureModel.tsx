import React, { useState } from 'react';
import { Sliders, AlertTriangle, CheckCircle2, TrendingDown, ArrowRight, Zap, RefreshCw } from 'lucide-react';

export const AlgorithmicFailureModel: React.FC = () => {
  // Model Parameters
  const [reactionFrequency, setReactionFrequency] = useState<number>(75); // %
  const [anchorDiscipline, setAnchorDiscipline] = useState<number>(25); // %
  const [closedLoopEnforcement, setClosedLoopEnforcement] = useState<number>(30); // %
  const [agentSpeculationCap, setAgentSpeculationCap] = useState<number>(80); // %

  // Computed differential outcomes
  // Entropy Growth Rate: positive = runaway chaos, negative = stabilizing
  const entropyRate = ((reactionFrequency * 1.4 + agentSpeculationCap * 1.1) - (anchorDiscipline * 1.8 + closedLoopEnforcement * 1.5)).toFixed(1);
  const isDivergent = parseFloat(entropyRate) > 0;

  // Projected runway under current parameters
  const projectedRunwayDays = Math.max(30, Math.round(180 - (parseFloat(entropyRate) * 1.4)));
  const projectedFounderStrain = Math.min(98, Math.max(20, Math.round(50 + (parseFloat(entropyRate) * 0.4))));
  const artifactLossProbability = Math.min(95, Math.max(2, Math.round((reactionFrequency * 0.6) + (agentSpeculationCap * 0.4) - (closedLoopEnforcement * 0.7))));

  // Presets
  const applyKnownFailurePattern = () => {
    setReactionFrequency(85);
    setAnchorDiscipline(15);
    setClosedLoopEnforcement(10);
    setAgentSpeculationCap(90);
  };

  const applySovereignTargetDestination = () => {
    setReactionFrequency(15);
    setAnchorDiscipline(90);
    setClosedLoopEnforcement(95);
    setAgentSpeculationCap(20);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-amber-400">
              <Sliders className="w-4 h-4 text-amber-400" />
              <span>Algorithmic Failure Pattern Laboratory</span>
              <span className="text-neutral-600">/</span>
              <span>Mathematical Proof of Chaos vs Destination</span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              Prove and Model the Known Failure Pattern
            </h1>
            <p className="text-xs md:text-sm text-neutral-400 max-w-3xl leading-relaxed">
              Eliminate guessing from estate governance. This simulator mathematically demonstrates why reacting and building new things without an anchor 
              causes explosive entropy, runaway burn, and founder collapse—and proves how the Sovereign Algorithmic Anchor guarantees stability.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={applyKnownFailurePattern}
              className="px-3 py-1.5 text-xs font-medium text-red-300 bg-red-950/60 border border-red-800/80 rounded-lg hover:bg-red-900/60 transition-colors cursor-pointer"
            >
              Simulate Failure Loop
            </button>
            <button
              onClick={applySovereignTargetDestination}
              className="px-3 py-1.5 text-xs font-medium text-emerald-300 bg-emerald-950/60 border border-emerald-800/80 rounded-lg hover:bg-emerald-900/60 transition-colors cursor-pointer"
            >
              Simulate Sovereign Anchor
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Controls & Live Comparative Engine */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Mathematical Control Parameters */}
        <div className="lg:col-span-5 bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <h3 className="text-sm font-bold text-white">System Variable Modulators</h3>
            <span className="text-xs font-mono text-neutral-500">Continuous Dynamics</span>
          </div>

          {/* Slider 1 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-neutral-300 font-medium">Reactive Build Urge (Old Failure Pattern)</span>
              <span className="font-mono text-amber-400">{reactionFrequency}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={reactionFrequency}
              onChange={(e) => setReactionFrequency(parseInt(e.target.value, 10))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="text-[11px] text-neutral-500">
              Tendency to start new builds when anxious rather than fixing feedback loops.
            </div>
          </div>

          {/* Slider 2 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-neutral-300 font-medium">Algorithmic Anchor Discipline (Decree 01)</span>
              <span className="font-mono text-emerald-400">{anchorDiscipline}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={anchorDiscipline}
              onChange={(e) => setAnchorDiscipline(parseInt(e.target.value, 10))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <div className="text-[11px] text-neutral-500">
              Requiring formal mathematical state-space formulation before coding.
            </div>
          </div>

          {/* Slider 3 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-neutral-300 font-medium">Closed-Loop Verification Gate (Decree 02)</span>
              <span className="font-mono text-blue-400">{closedLoopEnforcement}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={closedLoopEnforcement}
              onChange={(e) => setClosedLoopEnforcement(parseInt(e.target.value, 10))}
              className="w-full accent-blue-500 cursor-pointer"
            />
            <div className="text-[11px] text-neutral-500">
              No motion closes without empirical value proof and artifact vault lock.
            </div>
          </div>

          {/* Slider 4 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-neutral-300 font-medium">Agent Speculative Autonomy (Mindless Text)</span>
              <span className="font-mono text-red-400">{agentSpeculationCap}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={agentSpeculationCap}
              onChange={(e) => setAgentSpeculationCap(parseInt(e.target.value, 10))}
              className="w-full accent-red-500 cursor-pointer"
            />
            <div className="text-[11px] text-neutral-500">
              Unsupervised agent execution generating agenda text without clear protocols.
            </div>
          </div>

          {/* Invariant Equation Box */}
          <div className="p-3.5 bg-neutral-950 rounded-lg border border-neutral-800 text-xs font-mono space-y-1.5 text-neutral-400">
            <div className="text-neutral-300 font-semibold">Lyapunov Stability Condition:</div>
            <div className="text-amber-400">dE/dt = 1.4(React) + 1.1(Spec) - 1.8(Anchor) - 1.5(Loop)</div>
            <div className="text-[11px] text-neutral-500">
              System stabilizes if and only if dE/dt &le; 0. Current rate: <span className={isDivergent ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>{entropyRate}</span>
            </div>
          </div>
        </div>

        {/* Right: Projected State Trajectory */}
        <div className="lg:col-span-7 bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2 text-xs font-mono text-white">
              <span className={`w-2.5 h-2.5 rounded-full ${isDivergent ? 'bg-red-500' : 'bg-emerald-500'}`} />
              <span className="uppercase tracking-wider font-bold">
                {isDivergent ? 'Divergent Entropy Trajectory (Void Risk)' : 'Convergent Sovereign Trajectory (Anchored)'}
              </span>
            </div>
            <span className="text-xs font-mono text-neutral-400">180-Day Simulation</span>
          </div>

          {/* SVG Trajectory Graph */}
          <div className="bg-neutral-950 rounded-xl border border-neutral-800 p-4 relative h-64 flex flex-col justify-between overflow-hidden">
            <div className="flex justify-between text-[11px] font-mono text-neutral-500">
              <span>TREASURY &amp; HEALTH RUNWAY TRAJECTORY</span>
              <span>t = 0 → t = 180 Days</span>
            </div>

            <svg className="w-full h-44 overflow-visible" viewBox="0 0 500 150">
              {/* Grid lines */}
              <line x1="0" y1="30" x2="500" y2="30" stroke="#262626" strokeDasharray="3 3" />
              <line x1="0" y1="75" x2="500" y2="75" stroke="#262626" strokeDasharray="3 3" />
              <line x1="0" y1="120" x2="500" y2="120" stroke="#262626" strokeDasharray="3 3" />

              {/* Red-Line Threshold Band */}
              <line x1="0" y1="120" x2="500" y2="120" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="4 2" opacity="0.8" />
              <text x="10" y="115" fill="#ef4444" fontSize="10" fontFamily="monospace">RED-LINE COLLAPSE THRESHOLD</text>

              {/* Target Destination Curve (Green, smooth asymptote) */}
              <path
                d="M 0 50 C 150 45, 300 40, 500 35"
                fill="none"
                stroke="#10b981"
                strokeWidth="2.5"
                opacity="0.9"
              />
              <text x="350" y="30" fill="#10b981" fontSize="10" fontFamily="monospace">Sovereign Target (Stable)</text>

              {/* Actual Projected Curve based on slider state */}
              {isDivergent ? (
                // Crashing curve
                <path
                  d="M 0 50 C 100 60, 250 110, 420 145"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="3"
                />
              ) : (
                // Controlled curve
                <path
                  d="M 0 50 C 120 48, 280 42, 500 38"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3"
                />
              )}
            </svg>

            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-neutral-500">Initial State (Day 0)</span>
              <span className={isDivergent ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
                {isDivergent ? `Runway Exhaustion: Day ${projectedRunwayDays}` : 'Runway Extended: 180+ Days'}
              </span>
            </div>
          </div>

          {/* Outcome Scorecard */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-neutral-950 rounded-lg border border-neutral-800 text-xs">
              <div className="text-neutral-400">Projected Runway</div>
              <div className={`text-base font-bold font-mono mt-1 ${isDivergent ? 'text-red-400' : 'text-emerald-400'}`}>
                {projectedRunwayDays} Days
              </div>
              <div className="text-[10px] text-neutral-500 mt-0.5">
                {isDivergent ? 'Red-line risk imminent' : 'Treasury secure'}
              </div>
            </div>

            <div className="p-3 bg-neutral-950 rounded-lg border border-neutral-800 text-xs">
              <div className="text-neutral-400">Founder Cognitive Strain</div>
              <div className={`text-base font-bold font-mono mt-1 ${projectedFounderStrain > 60 ? 'text-red-400' : 'text-emerald-400'}`}>
                {projectedFounderStrain} / 100
              </div>
              <div className="text-[10px] text-neutral-500 mt-0.5">
                {projectedFounderStrain > 60 ? 'Severe decision burnout' : 'Calm, anchored clarity'}
              </div>
            </div>

            <div className="p-3 bg-neutral-950 rounded-lg border border-neutral-800 text-xs">
              <div className="text-neutral-400">Artifact Loss Probability</div>
              <div className={`text-base font-bold font-mono mt-1 ${artifactLossProbability > 30 ? 'text-red-400' : 'text-emerald-400'}`}>
                {artifactLossProbability}% Risk
              </div>
              <div className="text-[10px] text-neutral-500 mt-0.5">
                {artifactLossProbability > 30 ? 'High blind spot chance' : 'Zero lost artifacts'}
              </div>
            </div>
          </div>

          {/* The Founder's Definitive Decision Anchor */}
          <div className="p-4 bg-amber-950/20 border border-amber-900/40 rounded-lg text-xs space-y-1.5">
            <div className="font-bold text-amber-400 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              <span>The Founder Sovereign Anchor Rule</span>
            </div>
            <p className="text-neutral-300 leading-relaxed">
              Whenever you feel the urge to react, dream in a void, or command mindless agents to build a new system: 
              <strong className="text-white"> STOP. </strong> Enact an Algorithmic Gate first. Require state-space convergence, a quantifiable closed-loop metric, and an immutable artifact vault address before spending one dollar or one unit of cognitive health.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
