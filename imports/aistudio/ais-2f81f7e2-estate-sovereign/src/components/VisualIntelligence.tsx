import React, { useState } from 'react';
import { EstateNode, EstateArtifact, FinancialHealthMetrics } from '../types/estate';
import { ArrowRight, Compass, ShieldAlert, CheckCircle2, RefreshCw, Eye, AlertTriangle } from 'lucide-react';

interface VisualIntelligenceProps {
  nodes: EstateNode[];
  artifacts: EstateArtifact[];
  metrics: FinancialHealthMetrics;
  onInspectArtifact: (artifact: EstateArtifact) => void;
  onOpenNewMotion: () => void;
  onNavigateToView: (view: string) => void;
}

export const VisualIntelligence: React.FC<VisualIntelligenceProps> = ({
  nodes,
  artifacts,
  metrics,
  onInspectArtifact,
  onOpenNewMotion,
  onNavigateToView,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('NODE-01');
  const [visualMode, setVisualMode] = useState<'topology' | 'phase-space' | 'feedback-loop'>('topology');

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || nodes[0];
  const recoveredMockup = artifacts.find((a) => a.id === 'ART-001');

  return (
    <div className="space-y-6">
      {/* Founder Red-Line Anchor Kicker & Status Banner */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-amber-400">
              <Compass className="w-4 h-4 text-amber-400" />
              <span>Estate Sovereign Orientation Matrix</span>
              <span className="text-neutral-600">/</span>
              <span className="text-neutral-400">Zero Blindness Directive</span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              Real-Time Visual Intelligence &amp; Algorithmic Topology
            </h1>
            <p className="text-xs md:text-sm text-neutral-400 max-w-3xl">
              Deterministic modeling of estate state space. Every agent action is anchored to a governing decree, 
              cryptographic artifact, and closed feedback loop to protect founder health and treasury runway.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {recoveredMockup && (
              <button
                onClick={() => onInspectArtifact(recoveredMockup)}
                className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-emerald-300 bg-emerald-950/60 border border-emerald-800/80 rounded-lg hover:bg-emerald-900/60 transition-colors cursor-pointer"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Inspect Recovered Mockup (ART-001)</span>
              </button>
            )}
            <button
              onClick={() => onNavigateToView('failure-model')}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-neutral-300 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg transition-colors cursor-pointer"
            >
              <span>Model Chaos Shape</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Essential Anchor Metrics Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 pt-4 border-t border-neutral-800/80">
          <div>
            <div className="text-xs text-neutral-400">Active Orientation</div>
            <div className="text-base font-semibold text-white mt-0.5">Anchored Algorithmically</div>
            <div className="text-xs text-emerald-400 font-mono mt-0.5">100% Proven Vectors</div>
          </div>
          <div>
            <div className="text-xs text-neutral-400">Feedback Loop Closure</div>
            <div className="text-base font-semibold text-white font-mono tabular-nums mt-0.5">
              {metrics.closedFeedbackLoopsCount} / {metrics.closedFeedbackLoopsCount + metrics.openFeedbackLoopsCount} Loops
            </div>
            <div className="text-xs text-amber-400 font-mono mt-0.5">
              {metrics.openFeedbackLoopsCount} Open (Requires Gate)
            </div>
          </div>
          <div>
            <div className="text-xs text-neutral-400">Treasury Runway</div>
            <div className="text-base font-semibold text-white font-mono tabular-nums mt-0.5">
              {metrics.runwayMonths.toFixed(1)} Months
            </div>
            <div className="text-xs text-neutral-400 font-mono mt-0.5">
              ${metrics.dailyBurnUSD.toFixed(0)}/day burn
            </div>
          </div>
          <div>
            <div className="text-xs text-neutral-400">Founder Cognitive Load</div>
            <div className="text-base font-semibold text-amber-400 font-mono tabular-nums mt-0.5">
              {metrics.founderCognitiveLoadIndex} / 100
            </div>
            <div className="text-xs text-red-400 font-mono mt-0.5">Red-Line Warning Zone</div>
          </div>
        </div>
      </div>

      {/* Main Visual Intelligence Canvas Container */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        {/* Sub-header with Segmented Interactive Filter Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-3.5 border-b border-neutral-800 bg-neutral-900/60">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-neutral-300">Visual Mode:</span>
            <div className="flex items-center gap-1 p-1 bg-neutral-950 rounded-lg border border-neutral-800">
              <button
                onClick={() => setVisualMode('topology')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  visualMode === 'topology'
                    ? 'bg-neutral-800 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Estate Topology Map
              </button>
              <button
                onClick={() => setVisualMode('phase-space')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  visualMode === 'phase-space'
                    ? 'bg-neutral-800 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Chaos vs Destination
              </button>
              <button
                onClick={() => setVisualMode('feedback-loop')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  visualMode === 'feedback-loop'
                    ? 'bg-neutral-800 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Closed-Loop Telemetry
              </button>
            </div>
          </div>

          <div className="text-xs text-neutral-400 font-mono flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>Live Node Telemetry Active</span>
            <span className="text-neutral-600">·</span>
            <span>Refresh rate 250ms</span>
          </div>
        </div>

        {/* Canvas Render Area */}
        <div className="p-6">
          {visualMode === 'topology' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Interactive Vector Topology Canvas */}
              <div className="lg:col-span-8 bg-neutral-950 rounded-xl border border-neutral-800 p-4 relative overflow-hidden min-h-[460px] flex flex-col justify-between">
                {/* Background Grid Pattern */}
                <div 
                  className="absolute inset-0 opacity-15 pointer-events-none"
                  style={{
                    backgroundImage: 'radial-gradient(circle, #f59e0b 1px, transparent 1px)',
                    backgroundSize: '24px 24px'
                  }}
                />

                {/* SVG Conduit Paths */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  <defs>
                    <linearGradient id="activeBeam" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.8" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.2" />
                    </linearGradient>
                    <linearGradient id="driftBeam" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity="0.7" />
                      <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.1" />
                    </linearGradient>
                  </defs>

                  {/* Lines connecting nodes */}
                  <line x1="20%" y1="45%" x2="50%" y2="25%" stroke="#3b82f6" strokeWidth="2" strokeDasharray="4 4" opacity="0.6" />
                  <line x1="50%" y1="25%" x2="80%" y2="35%" stroke="#10b981" strokeWidth="2.5" opacity="0.7" />
                  <line x1="20%" y1="45%" x2="48%" y2="70%" stroke="#ef4444" strokeWidth="2" opacity="0.8" />
                  <line x1="48%" y1="70%" x2="78%" y2="78%" stroke="#f59e0b" strokeWidth="2" strokeDasharray="3 3" opacity="0.6" />
                  <line x1="80%" y1="35%" x2="78%" y2="78%" stroke="#10b981" strokeWidth="2" opacity="0.5" />
                  
                  {/* Closed loop feedback arc returning to founder */}
                  <path
                    d="M 640 340 C 500 440, 260 400, 180 240"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2"
                    strokeDasharray="6 4"
                    opacity="0.8"
                  />
                </svg>

                {/* Legend Header */}
                <div className="relative z-10 flex items-center justify-between text-xs text-neutral-400 font-mono">
                  <span>AUTONOMOUS ESTATE MESH [v2.4.1]</span>
                  <span className="text-emerald-400">Closed Feedback Loop: Active</span>
                </div>

                {/* Node Interactive Buttons positioned across the topology */}
                <div className="relative z-10 my-auto grid grid-cols-1 md:grid-cols-3 gap-6 py-8">
                  {/* Founder Core Node */}
                  <div className="flex flex-col items-start">
                    <button
                      onClick={() => setSelectedNodeId('NODE-01')}
                      className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer w-full max-w-[220px] ${
                        selectedNodeId === 'NODE-01'
                          ? 'bg-amber-950/40 border-amber-500 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500'
                          : 'bg-neutral-900/90 border-neutral-700 hover:border-neutral-500'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-amber-400">
                        <span>FOUNDER_CORE</span>
                        <span className="text-neutral-400">NODE-01</span>
                      </div>
                      <div className="text-sm font-bold text-white mt-1">Founder Anchor</div>
                      <div className="text-xs text-neutral-400 mt-1">Chief Arbiter &amp; Edicts</div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-neutral-800 text-xs font-mono">
                        <span className="text-neutral-400">Cognitive:</span>
                        <span className="text-amber-400">{metrics.founderCognitiveLoadIndex}%</span>
                      </div>
                    </button>
                  </div>

                  {/* Middle Column: Gate & Agents */}
                  <div className="flex flex-col gap-6 justify-center">
                    <button
                      onClick={() => setSelectedNodeId('NODE-02')}
                      className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer w-full max-w-[220px] ${
                        selectedNodeId === 'NODE-02'
                          ? 'bg-blue-950/40 border-blue-500 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500'
                          : 'bg-neutral-900/90 border-neutral-700 hover:border-neutral-500'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-blue-400">
                        <span>PROTOCOL_GATE</span>
                        <span className="text-neutral-400">NODE-02</span>
                      </div>
                      <div className="text-sm font-bold text-white mt-1">Algorithmic Gate</div>
                      <div className="text-xs text-neutral-400 mt-1">Convergence Prover</div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-neutral-800 text-xs font-mono">
                        <span className="text-neutral-400">Open Loops:</span>
                        <span className="text-emerald-400">0 Quarantined</span>
                      </div>
                    </button>

                    <button
                      onClick={() => setSelectedNodeId('NODE-04')}
                      className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer w-full max-w-[220px] ${
                        selectedNodeId === 'NODE-04'
                          ? 'bg-red-950/40 border-red-500 shadow-lg shadow-red-500/10 ring-1 ring-red-500'
                          : 'bg-neutral-900/90 border-neutral-700 hover:border-neutral-500'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-red-400">
                        <span>AGENT_FLEET</span>
                        <span className="text-neutral-400">NODE-04</span>
                      </div>
                      <div className="text-sm font-bold text-white mt-1">Agent Processors</div>
                      <div className="text-xs text-neutral-400 mt-1">7 Autonomous Workers</div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-neutral-800 text-xs font-mono">
                        <span className="text-neutral-400">Drift Risk:</span>
                        <span className="text-red-400 font-bold">CONTAINED</span>
                      </div>
                    </button>
                  </div>

                  {/* Right Column: Artifact Vault & Capital Treasury */}
                  <div className="flex flex-col gap-6 justify-center items-end">
                    <button
                      onClick={() => setSelectedNodeId('NODE-03')}
                      className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer w-full max-w-[220px] ${
                        selectedNodeId === 'NODE-03'
                          ? 'bg-emerald-950/40 border-emerald-500 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500'
                          : 'bg-neutral-900/90 border-neutral-700 hover:border-neutral-500'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-emerald-400">
                        <span>ARTIFACT_VAULT</span>
                        <span className="text-neutral-400">NODE-03</span>
                      </div>
                      <div className="text-sm font-bold text-white mt-1">Artifact Vault</div>
                      <div className="text-xs text-neutral-400 mt-1">5 Verified Outputs</div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-neutral-800 text-xs font-mono">
                        <span className="text-neutral-400">Zero Lost:</span>
                        <span className="text-emerald-400 font-bold">100% Traceable</span>
                      </div>
                    </button>

                    <button
                      onClick={() => setSelectedNodeId('NODE-05')}
                      className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer w-full max-w-[220px] ${
                        selectedNodeId === 'NODE-05'
                          ? 'bg-purple-950/40 border-purple-500 shadow-lg shadow-purple-500/10 ring-1 ring-purple-500'
                          : 'bg-neutral-900/90 border-neutral-700 hover:border-neutral-500'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono text-purple-400">
                        <span>CAPITAL_TREASURY</span>
                        <span className="text-neutral-400">NODE-05</span>
                      </div>
                      <div className="text-sm font-bold text-white mt-1">Treasury Runway</div>
                      <div className="text-xs text-neutral-400 mt-1">${metrics.totalTreasuryUSD.toLocaleString()} Reserve</div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-neutral-800 text-xs font-mono">
                        <span className="text-neutral-400">Runway:</span>
                        <span className="text-purple-300">{metrics.runwayMonths.toFixed(1)} mo</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Footer telemetry tracker on canvas */}
                <div className="relative z-10 flex items-center justify-between pt-3 border-t border-neutral-900 text-xs font-mono text-neutral-500">
                  <span>Conduit Bandwidth: 1.4 GB/s</span>
                  <span>Loop Stability: Lyapunov Negative Definite (Converging)</span>
                </div>
              </div>

              {/* Node Inspector Panel */}
              <div className="lg:col-span-4 bg-neutral-950 rounded-xl border border-neutral-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-mono text-amber-400 uppercase tracking-wider">Node Telemetry</div>
                  <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                    selectedNode.status === 'ACTIVE' 
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' 
                      : 'bg-amber-950 text-amber-400 border border-amber-800'
                  }`}>
                    {selectedNode.status}
                  </span>
                </div>

                <div>
                  <h3 className="text-base font-bold text-white">{selectedNode.name}</h3>
                  <p className="text-xs text-neutral-400 mt-1">
                    System identifier <span className="font-mono text-neutral-300">{selectedNode.id}</span> category <span className="font-mono text-neutral-300">{selectedNode.category}</span>
                  </p>
                </div>

                <div className="space-y-2.5 pt-2 border-t border-neutral-800 text-xs">
                  <div className="flex justify-between py-1 border-b border-neutral-900">
                    <span className="text-neutral-400">Governing Decree:</span>
                    <span className="font-medium text-neutral-200">{selectedNode.assignedDecree || 'None'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-neutral-900">
                    <span className="text-neutral-400">Active Load:</span>
                    <span className="font-mono font-medium text-neutral-200">{selectedNode.loadPercent}%</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-neutral-900">
                    <span className="text-neutral-400">Open Loops Count:</span>
                    <span className={`font-mono font-medium ${selectedNode.openLoopsCount > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {selectedNode.openLoopsCount}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-neutral-900">
                    <span className="text-neutral-400">Heartbeat Latency:</span>
                    <span className="font-mono text-neutral-400">{selectedNode.lastPing}</span>
                  </div>
                </div>

                {/* Node Actions */}
                <div className="pt-2 space-y-2">
                  <button
                    onClick={onOpenNewMotion}
                    className="w-full py-2 px-3 text-xs font-semibold text-neutral-950 bg-amber-500 hover:bg-amber-400 rounded-lg transition-colors cursor-pointer text-center"
                  >
                    Bind New Algorithmic Motion
                  </button>
                  <button
                    onClick={() => onNavigateToView('artifacts')}
                    className="w-full py-2 px-3 text-xs font-medium text-neutral-300 bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 rounded-lg transition-colors cursor-pointer text-center"
                  >
                    View Associated Artifacts
                  </button>
                </div>
              </div>
            </div>
          )}

          {visualMode === 'phase-space' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Chaos Phase State (The Past Failure Mode) */}
                <div className="bg-neutral-950 rounded-xl border border-red-950/80 p-5 space-y-4">
                  <div className="flex items-center justify-between text-xs font-mono text-red-400">
                    <span className="flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      UNANCHORED CHAOS PATTERN (THE VOID)
                    </span>
                    <span>DIVERGENT</span>
                  </div>

                  <h3 className="text-base font-bold text-white">The Known Failure Signature</h3>
                  <p className="text-xs text-neutral-400 leading-relaxed">
                    Reacting to anxiety by building new things without a mathematical anchor. Mindless agents generate agenda text in a void, leaving artifacts lost, treasury bleeding, and founder cognitive health at critical strain.
                  </p>

                  <div className="bg-red-950/20 border border-red-900/40 rounded-lg p-3 space-y-2 text-xs font-mono">
                    <div className="flex justify-between text-neutral-400">
                      <span>Entropy Drift:</span>
                      <span className="text-red-400 font-bold">+84.2% / week</span>
                    </div>
                    <div className="flex justify-between text-neutral-400">
                      <span>Artifact Orphaning:</span>
                      <span className="text-red-400 font-bold">High (Founder Blind)</span>
                    </div>
                    <div className="flex justify-between text-neutral-400">
                      <span>Burn Trajectory:</span>
                      <span className="text-red-400 font-bold">Runway Exhaustion &lt; 90 days</span>
                    </div>
                    <div className="flex justify-between text-neutral-400">
                      <span>Founder Strain:</span>
                      <span className="text-red-400 font-bold">Chronic Burnout (Red-Line)</span>
                    </div>
                  </div>
                </div>

                {/* Target Destination State (The Algorithmic Sovereign Mode) */}
                <div className="bg-neutral-950 rounded-xl border border-emerald-950/80 p-5 space-y-4">
                  <div className="flex items-center justify-between text-xs font-mono text-emerald-400">
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      TARGET SOVEREIGN DESTINATION
                    </span>
                    <span>CONVERGENT</span>
                  </div>

                  <h3 className="text-base font-bold text-white">Algorithmically First Estate</h3>
                  <p className="text-xs text-neutral-400 leading-relaxed">
                    Closed-loop delivery protocol where every decree requires a state transition model, every motion produces a cryptographically verified artifact, and founder health and treasury runway are shielded by automated invariants.
                  </p>

                  <div className="bg-emerald-950/20 border border-emerald-900/40 rounded-lg p-3 space-y-2 text-xs font-mono">
                    <div className="flex justify-between text-neutral-400">
                      <span>Entropy Bound:</span>
                      <span className="text-emerald-400 font-bold">Stable (Lyapunov Invariant)</span>
                    </div>
                    <div className="flex justify-between text-neutral-400">
                      <span>Artifact Provenance:</span>
                      <span className="text-emerald-400 font-bold">100% Indexed &amp; Recovered</span>
                    </div>
                    <div className="flex justify-between text-neutral-400">
                      <span>Runway Extension:</span>
                      <span className="text-emerald-400 font-bold">&gt; 180 Days Target</span>
                    </div>
                    <div className="flex justify-between text-neutral-400">
                      <span>Founder Orientation:</span>
                      <span className="text-emerald-400 font-bold">Calm, Deterministic Command</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Button to launch mathematical simulation */}
              <div className="text-center pt-2">
                <button
                  onClick={() => onNavigateToView('failure-model')}
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-neutral-950 bg-amber-500 hover:bg-amber-400 rounded-lg transition-colors cursor-pointer shadow"
                >
                  <span>Open Mathematical Failure Simulator</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {visualMode === 'feedback-loop' && (
            <div className="bg-neutral-950 rounded-xl border border-neutral-800 p-6 space-y-6">
              <div>
                <h3 className="text-base font-bold text-white">Closed-Loop Delivery Protocol Architecture</h3>
                <p className="text-xs text-neutral-400 mt-1 max-w-3xl">
                  How the estate prevents tasks from wandering into a void. Every agenda must traverse these 5 gates and close the feedback loop before any capital or agent thread is released.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <div className="p-3.5 rounded-lg border border-neutral-800 bg-neutral-900/40 space-y-2">
                  <div className="text-xs font-mono text-amber-400">GATE 01</div>
                  <div className="text-xs font-bold text-white">Algorithmic Model</div>
                  <div className="text-xs text-neutral-400 leading-snug">State transitions &amp; convergence proof defined upfront.</div>
                </div>

                <div className="p-3.5 rounded-lg border border-neutral-800 bg-neutral-900/40 space-y-2">
                  <div className="text-xs font-mono text-amber-400">GATE 02</div>
                  <div className="text-xs font-bold text-white">Closed-Loop Metric</div>
                  <div className="text-xs text-neutral-400 leading-snug">Empirical value metric specified (e.g. burn delta, blind spot = 0).</div>
                </div>

                <div className="p-3.5 rounded-lg border border-neutral-800 bg-neutral-900/40 space-y-2">
                  <div className="text-xs font-mono text-amber-400">GATE 03</div>
                  <div className="text-xs font-bold text-white">Risk Clearance</div>
                  <div className="text-xs text-neutral-400 leading-snug">Founder cognitive load and capital burn bounded before launch.</div>
                </div>

                <div className="p-3.5 rounded-lg border border-neutral-800 bg-neutral-900/40 space-y-2">
                  <div className="text-xs font-mono text-amber-400">GATE 04</div>
                  <div className="text-xs font-bold text-white">Artifact Deposit</div>
                  <div className="text-xs text-neutral-400 leading-snug">Deliverable code/asset registered in vault with sha256 checksum.</div>
                </div>

                <div className="p-3.5 rounded-lg border border-emerald-800 bg-emerald-950/20 space-y-2">
                  <div className="text-xs font-mono text-emerald-400">GATE 05</div>
                  <div className="text-xs font-bold text-white">Value Attestation</div>
                  <div className="text-xs text-neutral-400 leading-snug">Feedback loop closed. Founder inspects and signs off on value.</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
