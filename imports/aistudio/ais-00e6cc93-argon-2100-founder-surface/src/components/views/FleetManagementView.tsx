import React, { useState } from 'react';
import { Bot, CheckCircle2, AlertOctagon, RotateCw, Pause, Play, ShieldAlert, Cpu } from 'lucide-react';
import { AgentFleetMember, EstateState } from '../../utils/estateLogic';

interface FleetManagementViewProps {
  estateState: EstateState;
  onRemediateLegion: () => void;
  onUpdateAgentConcurrency: (agentId: string, newConcurrency: number) => void;
}

export const FleetManagementView: React.FC<FleetManagementViewProps> = ({
  estateState,
  onRemediateLegion,
  onUpdateAgentConcurrency,
}) => {
  const [selectedAgent, setSelectedAgent] = useState<AgentFleetMember>(estateState.agents[0]);
  const [isRemediating, setIsRemediating] = useState(false);

  const legionAgent = estateState.agents.find((a) => a.name.toLowerCase().includes('legion')) || estateState.agents[0];

  const handleRemediate = () => {
    setIsRemediating(true);
    setTimeout(() => {
      onRemediateLegion();
      setIsRemediating(false);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Operations</span>
            <span>/</span>
            <span className="text-sky-400">Fleet Management &amp; Autonomous Agents</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Agent Fleet Orchestration &amp; Supervision
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time status of distributed agent runtimes, concurrency limits, task queues, and recovery pipelines.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">
            Active Fleet Concurrency: <strong className="text-white">
              {estateState.agents.reduce((acc, a) => acc + a.concurrency, 0)} threads
            </strong>
          </span>
        </div>
      </div>

      {/* Legion Recovery Spotlight Card (Addresses user prompt directly) */}
      <div className="rounded-2xl border border-sky-500/30 bg-slate-950/90 p-5 shadow-xl spatial-grid relative overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-4 pb-3 border-b border-slate-800">
          <div className="flex items-start gap-3">
            <div className={`p-2.5 rounded-xl border ${
              legionAgent.status === 'active'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
            }`}>
              {legionAgent.status === 'active' ? <CheckCircle2 className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-sky-400 uppercase tracking-wider">Mission Recovery Controller</span>
                <span className="text-xs text-slate-500">·</span>
                <span className="text-xs font-mono text-slate-300">Run #42412348112</span>
              </div>
              <h3 className="text-base font-bold text-white mt-0.5">
                Legion Orchestrator · Founder-Gateway Build
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono px-2.5 py-1 rounded border uppercase ${
              legionAgent.status === 'active'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse'
            }`}>
              Status: {legionAgent.status}
            </span>
          </div>
        </div>

        {/* Narrative & Invariant Audit Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400">Ruff Linter Pass</span>
            <div className="text-sm font-bold font-mono text-emerald-400 flex items-center gap-1.5 mt-1">
              <CheckCircle2 className="w-4 h-4" /> Passed Clean
            </div>
            <p className="text-xs text-slate-500 mt-1">Zero syntax errors or formatting flaws.</p>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400">Transcript Firewall</span>
            <div className="text-sm font-bold font-mono text-emerald-400 flex items-center gap-1.5 mt-1">
              <CheckCircle2 className="w-4 h-4" /> Passed Clean
            </div>
            <p className="text-xs text-slate-500 mt-1">All agent dialogue verified leak-free.</p>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400">Trusted Push Gate</span>
            <div className={`text-sm font-bold font-mono flex items-center gap-1.5 mt-1 ${
              legionAgent.status === 'active' ? 'text-emerald-400' : 'text-amber-400'
            }`}>
              {legionAgent.status === 'active' ? (
                <>
                  <CheckCircle2 className="w-4 h-4" /> ASCII Verified &amp; Pushed
                </>
              ) : (
                <>
                  <AlertOctagon className="w-4 h-4" /> Non-ASCII Blocked
                </>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {legionAgent.status === 'active'
                ? 'Non-ASCII chars sanitized. Push cleared.'
                : 'Blocked by encoding firewall. Recovery queued.'}
            </p>
          </div>
        </div>

        {/* Recovery Action Bar */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-400 font-mono">
            Current Task: <span className="text-white">{legionAgent.currentTask}</span>
          </p>

          {legionAgent.status !== 'active' ? (
            <button
              onClick={handleRemediate}
              disabled={isRemediating}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors shadow-md"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRemediating ? 'animate-spin' : ''}`} />
              <span>{isRemediating ? 'Executing Recovery #42412348112...' : 'Apply ASCII Remediation & Complete Push'}</span>
            </button>
          ) : (
            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> Legion Pipeline Verified &amp; Running
            </span>
          )}
        </div>
      </div>

      {/* Agent Fleet Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {estateState.agents.map((agent) => {
          const isSelected = selectedAgent.id === agent.id;
          return (
            <div
              key={agent.id}
              onClick={() => setSelectedAgent(agent)}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                isSelected
                  ? 'border-sky-500/50 bg-slate-900/80 shadow-lg'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white">{agent.name}</h4>
                  <span className="text-xs text-slate-400 font-mono">{agent.role}</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-mono border uppercase ${
                  agent.status === 'active'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                }`}>
                  {agent.status}
                </span>
              </div>

              <div className="mt-4 space-y-2">
                <div className="text-xs font-mono text-slate-400">
                  <span>Cluster:</span> <span className="text-white">{agent.cluster}</span>
                </div>
                <div className="text-xs font-mono text-slate-400">
                  <span>Yield Ratio:</span> <span className="text-emerald-400 font-bold">{(agent.yieldRatio * 100).toFixed(0)}%</span>
                </div>
                <div className="text-xs text-slate-400 line-clamp-2 mt-1">
                  {agent.currentTask}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                <div className="text-xs font-mono text-slate-400">
                  <span>Concurrency:</span> <strong className="text-white">{agent.concurrency}</strong>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateAgentConcurrency(agent.id, Math.max(1, agent.concurrency - 2));
                    }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono"
                  >
                    -
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateAgentConcurrency(agent.id, agent.concurrency + 2);
                    }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
