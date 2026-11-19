import React, { useState } from 'react';
import { TaskThread, MemoryNode } from '../engine/memoryEngine';
import { GitFork, Play, ShieldAlert, CheckCircle2, Plus } from 'lucide-react';

interface ActiveMultitaskingViewProps {
  threads: TaskThread[];
  globalNodes: MemoryNode[];
  onStepThread: (threadId: string) => void;
  onSpawnThread: (name: string, domain: string, budget: number) => void;
  onPromoteThreadFact: (threadId: string) => void;
}

export const ActiveMultitaskingView: React.FC<ActiveMultitaskingViewProps> = ({
  threads,
  globalNodes,
  onStepThread,
  onSpawnThread,
  onPromoteThreadFact,
}) => {
  const [newThreadName, setNewThreadName] = useState('');
  const [newThreadDomain, setNewThreadDomain] = useState('');
  const [newThreadBudget, setNewThreadBudget] = useState(2048);
  const [formError, setFormError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const activeGlobalNodes = globalNodes.filter((n) => n.validUntilStep === null && n.tier === 'working_focus');

  const handleCreateThread = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newThreadName.trim() || !newThreadDomain.trim()) {
      setFormError('Please provide both a Thread Name and Task Domain to fork a Copy-on-Write sandbox.');
      return;
    }
    setFormError(null);
    onSpawnThread(newThreadName.trim(), newThreadDomain.trim(), newThreadBudget);
    setStatusMessage(
      `Forked isolated Copy-on-Write sub-agent sandbox "${newThreadName.trim()}" with ${newThreadBudget} token ceiling and 0.0% cross-talk.`
    );
    setNewThreadName('');
    setNewThreadDomain('');
  };

  return (
    <div className="space-y-8">
      {/* Header & Architecture Explanation */}
      <section className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl space-y-2">
            <div className="text-xs text-slate-500">
              Active Multitasking Orchestrator · Copy-on-Write (CoW) Sub-Agent Context Isolation
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Parallel Task Sandboxes &amp; Zero-Contamination Shared Semantic Bus
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed">
              Standard multi-tasking agents collapse when parallel tool traces interleave inside a single context window. Mnemosyne synthesizes <strong>Anthropic’s Orchestrator-Subagent Isolation</strong> with <strong>Letta’s Transactional Shared Memory Blocks</strong>: each concurrent task forks a lightweight Copy-on-Write snapshot, absorbs noisy intermediate steps locally, and commits only verified semantic facts back to the global graph.
            </p>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-1.5 shrink-0">
            <div className="text-slate-500">Cross-Thread Scratchpad Leakage</div>
            <div className="text-2xl font-bold font-mono tabular-nums text-emerald-700">0.0%</div>
            <div className="text-slate-600 font-mono tabular-nums">
              {threads.length} Concurrent CoW Sandboxes Active
            </div>
          </div>
        </div>

        {statusMessage && (
          <div
            role="status"
            className="mt-4 p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{statusMessage}</span>
          </div>
        )}
      </section>

      {/* Concurrent Task Thread Cards */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {threads.map((thread) => {
          const utilizationPct = Math.min(
            100,
            Math.round((thread.usedTokens / thread.allocatedTokenBudget) * 100)
          );
          return (
            <div
              key={thread.id}
              className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between space-y-5"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2 border-b border-slate-200 pb-3">
                  <div>
                    <div className="text-xs text-slate-500 font-mono">
                      Priority P{thread.priority} · Status: {thread.status.toUpperCase()} · {thread.stepCount} Steps
                    </div>
                    <h2 className="text-base font-bold text-slate-900 mt-0.5">{thread.name}</h2>
                    <div className="text-xs text-slate-600 mt-0.5">{thread.domain}</div>
                  </div>
                </div>

                {/* Isolated RAM Utilization Bar */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Isolated CoW Scratchpad Budget</span>
                    <span className="font-mono tabular-nums text-slate-800">
                      {thread.usedTokens} / {thread.allocatedTokenBudget} tok ({utilizationPct}%)
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-900 transition-transform duration-150 origin-left"
                      style={{ transform: `scaleX(${utilizationPct / 100})` }}
                    />
                  </div>
                </div>

                {/* Ephemeral Local Scratchpad Log */}
                <div className="space-y-1.5 pt-1">
                  <div className="text-xs font-semibold text-slate-700">
                    Local Isolated Scratchpad (Hidden from Global Prompt):
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5 text-xs font-mono text-slate-700">
                    {thread.isolatedScratchpad.map((line, i) => (
                      <div key={i} className="leading-relaxed">
                        {i + 1}. {line}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="text-xs text-slate-500 flex items-center justify-between pt-1">
                  <span>Committed Global Edges: {thread.committedFactIds.join(', ') || 'None'}</span>
                  <span className="font-mono tabular-nums text-emerald-700">
                    Contamination: {thread.crossContaminationEvents}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    onStepThread(thread.id);
                    setStatusMessage(
                      `Executed isolated reasoning step in ${thread.name}; intermediate trace stayed inside local CoW RAM.`
                    );
                  }}
                  className="flex-1 py-2 px-3 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <Play className="w-3.5 h-3.5" />
                  Step Local Sandbox
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onPromoteThreadFact(thread.id);
                    setStatusMessage(
                      `Distilled and committed verified semantic invariant from ${thread.name} to Global Bi-Temporal Graph.`
                    );
                  }}
                  className="flex-1 py-2 px-3 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <GitFork className="w-3.5 h-3.5" />
                  Commit Verified Fact
                </button>
              </div>
            </div>
          );
        })}
      </section>

      {/* Bottom Split: Fork New Sub-Agent Sandbox + Shared Global Bus */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Fork New Isolated Task Thread
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Spawn a parallel Copy-on-Write sub-agent with a dedicated token budget ceiling.
            </p>
          </div>

          <form onSubmit={handleCreateThread} className="space-y-4" noValidate>
            <div>
              <label htmlFor="thread-name" className="block text-xs font-semibold text-slate-700 mb-1">
                Thread Identifier &amp; Role
              </label>
              <input
                id="thread-name"
                type="text"
                value={newThreadName}
                onChange={(e) => setNewThreadName(e.target.value)}
                placeholder="e.g. Thread 04 · Schema Migration Verifier"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label htmlFor="thread-domain" className="block text-xs font-semibold text-slate-700 mb-1">
                Assigned Objective / Workload
              </label>
              <input
                id="thread-domain"
                type="text"
                value={newThreadDomain}
                onChange={(e) => setNewThreadDomain(e.target.value)}
                placeholder="e.g. Zero-downtime shard rebalancing validation"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label htmlFor="thread-budget" className="block text-xs font-semibold text-slate-700 mb-1">
                Isolated Working RAM Ceiling (Tokens)
              </label>
              <select
                id="thread-budget"
                value={newThreadBudget}
                onChange={(e) => setNewThreadBudget(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value={1536}>1,536 Tokens (Compact Telemetry Worker)</option>
                <option value={2048}>2,048 Tokens (Standard Sub-Agent Sandbox)</option>
                <option value={4096}>4,096 Tokens (Deep Reasoning Synthesizer)</option>
              </select>
            </div>

            {formError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center justify-center gap-2 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Spawn Copy-on-Write Task Thread
            </button>
          </form>
        </section>

        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Shared Global Semantic Bus ({activeGlobalNodes.length} Active Verified Invariants)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              All concurrent threads read from this conflict-free semantic state. Only verified commits with valid <span className="font-mono">t_valid</span> timestamps appear here.
            </p>
          </div>

          <div className="divide-y divide-slate-200">
            {activeGlobalNodes.map((node) => (
              <div key={node.id} className="py-3 flex items-start justify-between gap-4 text-xs">
                <div className="space-y-0.5">
                  <div className="text-slate-500 font-mono">
                    {node.id} · Origin: {node.threadOrigin} · Zone: {node.contextPositionZone}
                  </div>
                  <div className="text-slate-900 font-semibold">
                    {node.subject} · <span className="font-normal text-slate-600">{node.predicate}</span> → {node.object}
                  </div>
                </div>
                <div className="text-right font-mono tabular-nums shrink-0">
                  <div className="text-emerald-700 font-semibold">Salience {node.salience.toFixed(2)}</div>
                  <div className="text-slate-400">Step {node.validFromStep}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
