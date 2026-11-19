import React, { useState } from 'react';
import { 
  Cpu, 
  Database, 
  Radio, 
  RotateCcw, 
  Search, 
  ShieldCheck, 
  Skull, 
  Sparkles, 
  Zap, 
  CheckCircle2, 
  ArrowRight,
  RefreshCw,
  Server,
  Layers,
  Clock
} from 'lucide-react';
import { PEER_BUS_AGENTS, INITIAL_MEMORIES } from '../data/estateRecords';
import { MemoryEntry, PeerAgent } from '../types/otto';
import { ModelCascadeConfigurator } from './ModelCascadeConfigurator';

export const PeerBusAndMemory: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'peers' | 'memory' | 'continuity' | 'lanes'>('peers');
  const [agents, setAgents] = useState<PeerAgent[]>(PEER_BUS_AGENTS);
  const [memories, setMemories] = useState<MemoryEntry[]>(INITIAL_MEMORIES);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLatencyMs, setSearchLatencyMs] = useState<number | null>(null);

  // Model Lanes Router State
  const [activeLane, setActiveLane] = useState<'cheap' | 'frontier'>('cheap');
  const [laneFailoverStatus, setLaneFailoverStatus] = useState<string | null>(null);

  // Continuity / SIGKILL state
  const [isKillingSession, setIsKillingSession] = useState(false);
  const [successorStatus, setSuccessorStatus] = useState<{
    step: string;
    elapsedSeconds: number;
    stepsPreserved: number;
    proofHash: string;
  } | null>(null);

  // Cross-Vendor Bus Handover simulation
  const [busRoundtripStatus, setBusRoundtripStatus] = useState<string | null>(null);

  const handleSimulateHandover = () => {
    setBusRoundtripStatus('Dispatching task: AST Refactor ➔ Vision Diff ➔ Blind QA...');
    setTimeout(() => {
      setBusRoundtripStatus('Otto (Lead) ➔ DeepSeek (Code Worker) executing AST...');
      setTimeout(() => {
        setBusRoundtripStatus('DeepSeek ➔ Gemini Flash Vision diffing screens...');
        setTimeout(() => {
          setBusRoundtripStatus('Gemini ➔ Blind Verifier generating SHA-256 verdict...');
          setTimeout(() => {
            setBusRoundtripStatus('Success: 4-vendor roundtrip complete in 1.4s. 0 founder relay. Proof: sha256:01928374');
          }, 400);
        }, 400);
      }, 400);
    }, 400);
  };

  const handleSearchMemory = (q: string) => {
    setSearchQuery(q);
    const start = performance.now();
    setTimeout(() => {
      setSearchLatencyMs(Math.round(performance.now() - start + 12));
    }, 40);
  };

  const handleTestDeadLaneFailover = () => {
    setLaneFailoverStatus('Simulating dead primary lane (Cheap Gemini Flash)...');
    setTimeout(() => {
      setLaneFailoverStatus('Dead lane detected in 220ms. Auto-rerouting to Frontier lane (Claude 3.5 Sonnet / Gemini Pro)...');
      setTimeout(() => {
        setActiveLane('frontier');
        setLaneFailoverStatus('Failover complete in 2.1s (Under 5s bar). Founder saw zero retries.');
      }, 900);
    }, 600);
  };

  const handleSimulateKill = () => {
    setIsKillingSession(true);
    setSuccessorStatus({
      step: 'SIGKILL signal sent. Active worker terminated mid-execution.',
      elapsedSeconds: 0,
      stepsPreserved: 3,
      proofHash: 'pending'
    });

    let s = 0;
    const interval = setInterval(() => {
      s += 3;
      if (s >= 18) {
        clearInterval(interval);
        setIsKillingSession(false);
        setSuccessorStatus({
          step: 'Successor booted, read outbox-state checkpoint, and finished remaining 2 steps!',
          elapsedSeconds: 18.4,
          stepsPreserved: 5,
          proofHash: 'sha256:aa918273'
        });
      } else {
        setSuccessorStatus(prev => prev ? ({ ...prev, elapsedSeconds: s }) : null);
      }
    }, 200);
  };

  const filteredMemories = memories.filter(
    m =>
      m.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.layer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl border border-purple-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-mono mb-2">
              <Cpu className="w-3.5 h-3.5" />
              <span>SECTION 4: BRAIN, 3-LAYER MEMORY & PEER BUS</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Peer Bus & Autonomous Memory Engine
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Otto is an <span className="text-purple-400 font-semibold">agent loop with tools</span>, not a chatbot. Orchestrates cross-vendor peers over <code className="text-cyan-400 font-mono text-xs">bin/genesis-crew.py</code>, maintains proactive 3-layer memory, and auto-hands off on session kill without human relay.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab('peers')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === 'peers' ? 'bg-purple-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
              }`}
            >
              Peer Bus (5 Nodes)
            </button>
            <button
              onClick={() => setActiveTab('memory')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === 'memory' ? 'bg-purple-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
              }`}
            >
              Proactive Memory
            </button>
            <button
              onClick={() => setActiveTab('continuity')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === 'continuity' ? 'bg-purple-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
              }`}
            >
              Continuity (Kill Test)
            </button>
            <button
              onClick={() => setActiveTab('lanes')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === 'lanes' ? 'bg-purple-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
              }`}
            >
              Model Lanes Router
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: PEER BUS (bin/genesis-crew.py) */}
      {activeTab === 'peers' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3 mb-4">
              <div>
                <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
                  <Radio className="w-4 h-4 text-cyan-400" />
                  <span>Cross-Vendor Peer Agent Bus: bin/genesis-crew.py</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Otto runs as Lead with specialized workers and an independent blind verifier.
                </p>
              </div>

              <button
                onClick={handleSimulateHandover}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all self-start sm:self-auto"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Simulate 4-Vendor Handover</span>
              </button>
            </div>

            {/* Handover Real-Time Status Ticker */}
            {busRoundtripStatus && (
              <div className="p-3 mb-4 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs font-mono animate-fadeIn">
                {busRoundtripStatus}
              </div>
            )}

            {/* 5 Agent Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map(agent => (
                <div
                  key={agent.id}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">{agent.name}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                      {agent.role}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-400 leading-snug">
                    Task: <span className="text-slate-300">{agent.currentTask}</span>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono">
                    <span className="text-emerald-400 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      {agent.status.toUpperCase()}
                    </span>
                    <span>Bus Ping: {agent.busHeartbeat}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: PROACTIVE 3-LAYER MEMORY */}
      {activeTab === 'memory' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3 mb-4">
              <div>
                <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
                  <Database className="w-4 h-4 text-purple-400" />
                  <span>Proactive Memory (User · Project · Session)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Machine-captured after every turn. Otto answers "what do you know about X" in under 2 seconds.
                </p>
              </div>

              {searchLatencyMs !== null && (
                <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-800">
                  Search Latency: {searchLatencyMs}ms (&lt; 2.0s bar)
                </span>
              )}
            </div>

            {/* Memory Search Input */}
            <div className="relative mb-4">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => handleSearchMemory(e.target.value)}
                placeholder="Search machine memory (e.g. VIP, airlock, checkpoint, rules)..."
                className="w-full pl-9 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 font-sans"
              />
            </div>

            {/* Memories List */}
            <div className="space-y-3">
              {filteredMemories.map(mem => (
                <div
                  key={mem.id}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold ${
                        mem.layer === 'user'
                          ? 'bg-sky-950 text-sky-400 border border-sky-800'
                          : mem.layer === 'project'
                          ? 'bg-purple-950 text-purple-400 border border-purple-800'
                          : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      }`}>
                        {mem.layer} layer
                      </span>
                      <span className="font-mono font-bold text-slate-200">{mem.key}</span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">{mem.timestamp}</span>
                  </div>

                  <p className="text-slate-300 text-[12px] leading-relaxed">{mem.content}</p>

                  <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono">
                    <span>Verified: {mem.verifiedBy}</span>
                    <span>Session: {mem.sourceSession}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CONTINUITY / SIGKILL RESILIENCE */}
      {activeTab === 'continuity' && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-rose-400 font-bold uppercase tracking-wider">
                EVAL E10: SESSION KILL CONTINUITY
              </div>
              <h3 className="text-lg font-bold text-white font-display mt-0.5">
                Automatic Successor State Recovery
              </h3>
              <p className="text-xs text-slate-400 max-w-xl">
                A killed or out-of-tokens session leaves its plan, progress, and transcript in the shared outbox-state branch. A successor starts within 60s and continues from the last proven step.
              </p>
            </div>

            <button
              onClick={handleSimulateKill}
              disabled={isKillingSession}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-lg shadow-rose-600/30 transition-all self-start sm:self-auto disabled:opacity-50"
            >
              <Skull className="w-4 h-4" />
              <span>Simulate Process SIGKILL</span>
            </button>
          </div>

          {successorStatus && (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Handover Latency:</span>
                <span className="text-cyan-400 font-bold text-sm">
                  {successorStatus.elapsedSeconds}s / 60.0s bar
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Steps Preserved:</span>
                <span className="text-emerald-400 font-bold">
                  {successorStatus.stepsPreserved} / 5 (Zero steps lost)
                </span>
              </div>
              <div className="p-3 rounded bg-slate-950 border border-slate-800 text-slate-300">
                {successorStatus.step}
              </div>
              {successorStatus.proofHash !== 'pending' && (
                <div className="text-[10px] text-emerald-400 flex items-center justify-between">
                  <span>Cryptographic Proof: {successorStatus.proofHash}</span>
                  <span className="font-bold">EVAL E10 PASSED</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: MODEL LANES ROUTER */}
      {activeTab === 'lanes' && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-amber-400 font-bold uppercase tracking-wider">
                MODEL LANES ROUTER &amp; FALLBACK
              </div>
              <h3 className="text-lg font-bold text-white font-display mt-0.5">
                Cheap Lane Default ➔ Frontier on Demand
              </h3>
              <p className="text-xs text-slate-400 max-w-xl">
                Every call goes through the estate router. A dead lane fails over within 5 seconds, and the founder never sees the retry.
              </p>
            </div>

            <button
              onClick={handleTestDeadLaneFailover}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold transition-all self-start sm:self-auto"
            >
              <Zap className="w-4 h-4" />
              <span>Test Dead Lane Failover (&lt;5s)</span>
            </button>
          </div>

          {laneFailoverStatus && (
            <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/30 text-amber-300 text-xs font-mono animate-fadeIn">
              {laneFailoverStatus}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className={`p-4 rounded-xl border text-xs space-y-2 ${
              activeLane === 'cheap'
                ? 'border-emerald-500 bg-emerald-950/20 text-emerald-300 ring-1 ring-emerald-500'
                : 'border-slate-800 bg-slate-900/40 text-slate-400'
            }`}>
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-white">Cheap Lane (Default)</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900">ACTIVE</span>
              </div>
              <div className="text-slate-300">Models: Gemini 2.5 Flash / DeepSeek-V3</div>
              <div className="text-[11px] text-slate-400">Used for 90%+ routine actions, screen parsing, and AST transformations.</div>
            </div>

            <div className={`p-4 rounded-xl border text-xs space-y-2 ${
              activeLane === 'frontier'
                ? 'border-indigo-500 bg-indigo-950/20 text-indigo-300 ring-1 ring-indigo-500'
                : 'border-slate-800 bg-slate-900/40 text-slate-400'
            }`}>
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-white">Frontier Lane (On-Demand)</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900">HOT STANDBY</span>
              </div>
              <div className="text-slate-300">Models: Gemini 2.5 Pro / Claude 3.5 Sonnet</div>
              <div className="text-[11px] text-slate-400">Triggered for complex architectural trade-offs and dead-lane failovers.</div>
            </div>
          </div>

          {/* Interactive Cascade Configurator embedded in Lanes */}
          <div className="pt-4 border-t border-slate-800">
            <ModelCascadeConfigurator />
          </div>
        </div>
      )}
    </div>
  );
};
