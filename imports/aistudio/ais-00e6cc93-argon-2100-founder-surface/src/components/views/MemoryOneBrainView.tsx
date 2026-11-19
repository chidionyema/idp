import React, { useState } from 'react';
import { Database, Search, Network, Brain, Sparkles, Compass } from 'lucide-react';

export const MemoryOneBrainView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCluster, setSelectedCluster] = useState<string>('cluster-core');

  const clusters = [
    {
      id: 'cluster-core',
      name: 'Founder Directives & Core Intent',
      vectorCount: '482,100',
      description: 'Preservation of complete estate intelligence, non-destructive integration, and zero-deprecation mandate.',
      similarity: 0.99,
      tags: ['founder-surface', 'estate-preservation', 'zero-deprecation', '2100-concierge'],
    },
    {
      id: 'cluster-spine',
      name: 'Genesis Spine Topology & Invariants',
      vectorCount: '891,400',
      description: 'Zero-drop packet routing, synapse mesh synchrony, and Greenlane operational invariants.',
      similarity: 0.95,
      tags: ['synaptic-mesh', 'low-latency', 'packet-routing', 'greenlane'],
    },
    {
      id: 'cluster-agents',
      name: 'Agent Fleet & Gateway Protocols',
      vectorCount: '745,200',
      description: 'Legion orchestrator state, transcript firewall rules, Ruff compliance, and trusted push ASCII gate.',
      similarity: 0.92,
      tags: ['legion-recovery', '42412348112', 'ascii-gate', 'ruff-lint'],
    },
    {
      id: 'cluster-ml',
      name: 'Argon Active ML & Checkpoints',
      vectorCount: '721,300',
      description: 'MoE weights, test loss convergence curves, instruction-yield optimization, and benchmark evals.',
      similarity: 0.88,
      tags: ['loss-convergence', 'moe-checkpoint', 'yield-multiplier', 'benchmarks'],
    },
  ];

  const filteredClusters = clusters.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.description.toLowerCase().includes(q) ||
      c.tags.some((t) => t.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Architecture</span>
            <span>/</span>
            <span className="text-sky-400">Memory &amp; One-Brain Synapse</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            One-Brain Episodic Memory &amp; Semantic Vector Store
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            2.84M verified knowledge vectors indexed across associative memory clusters, preserving founder directives and continuous learning.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-lg bg-sky-950/40 border border-sky-500/20 text-xs font-mono text-sky-400">
            Working Context: 128k Tokens Nominal
          </div>
        </div>
      </div>

      {/* Semantic Search Bar */}
      <div className="relative">
        <div className="flex items-center gap-3 bg-slate-950 border border-slate-800 rounded-xl p-3 shadow-lg focus-within:border-sky-500">
          <Search className="w-5 h-5 text-sky-400 shrink-0 ml-1" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search episodic memory vectors by concept, directive, or agent run..."
            className="w-full bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none font-sans"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="text-xs text-slate-400 hover:text-white px-2"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Memory Clusters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredClusters.map((cluster) => {
          const isSelected = selectedCluster === cluster.id;
          return (
            <div
              key={cluster.id}
              onClick={() => setSelectedCluster(cluster.id)}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                isSelected
                  ? 'border-sky-500/50 bg-slate-900/80 shadow-lg'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
                    <Brain className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{cluster.name}</h3>
                    <span className="text-xs font-mono text-slate-400">{cluster.vectorCount} vectors</span>
                  </div>
                </div>
                <span className="text-xs font-mono text-emerald-400 font-bold">
                  {(cluster.similarity * 100).toFixed(0)}% Match
                </span>
              </div>

              <p className="text-xs text-slate-300 mt-3 leading-relaxed">
                {cluster.description}
              </p>

              <div className="mt-4 pt-3 border-t border-slate-800 flex flex-wrap gap-1.5">
                {cluster.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-400 border border-slate-700/60"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
