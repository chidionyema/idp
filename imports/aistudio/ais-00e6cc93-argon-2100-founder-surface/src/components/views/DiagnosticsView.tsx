import React, { useState } from 'react';
import { Activity, ShieldCheck, AlertTriangle, CheckCircle2, RefreshCw, Cpu, HardDrive, Clock } from 'lucide-react';
import { SubsystemHealth, EstateState } from '../../utils/estateLogic';

interface DiagnosticsViewProps {
  estateState: EstateState;
  onVerifyGreenlane: () => void;
}

export const DiagnosticsView: React.FC<DiagnosticsViewProps> = ({
  estateState,
  onVerifyGreenlane,
}) => {
  const [isRunningCheck, setIsRunningCheck] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>('all');

  const filteredSubsystems = estateState.subsystems.filter((sub) => {
    if (filterCategory === 'all') return true;
    return sub.category === filterCategory;
  });

  const handleRunVerification = () => {
    setIsRunningCheck(true);
    setTimeout(() => {
      onVerifyGreenlane();
      setIsRunningCheck(false);
    }, 1200);
  };

  const invariants = [
    {
      id: 'inv-1',
      title: 'Invariant 1: Zero Synaptic Packet Loss',
      description: 'Genesis spine packets must traverse nodes with 0.00% dropped buffers.',
      status: 'nominal',
      measuredValue: '0.000% dropped',
    },
    {
      id: 'inv-2',
      title: 'Invariant 2: One-Brain Working Context Integrity',
      description: 'Episodic memory recall vectors must preserve 128k token context fidelity.',
      status: 'nominal',
      measuredValue: '100% fidelity',
    },
    {
      id: 'inv-3',
      title: 'Invariant 3: Clean ASCII & Trusted Push Gate',
      description: 'Source code and gateway artifacts must pass strict ASCII range <= 127 checks.',
      status: estateState.asciiFirewallViolations > 0 ? 'warning' : 'nominal',
      measuredValue: estateState.asciiFirewallViolations > 0 ? '1 Flagged File (Legion #42412348112)' : '0 Violations',
    },
    {
      id: 'inv-4',
      title: 'Invariant 4: Cross-Agent Authority & Non-Destructive Parity',
      description: 'No background agent may deprecate or conceal an estate capability without signed review.',
      status: 'nominal',
      measuredValue: '100% Parity Verified',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Operations</span>
            <span>/</span>
            <span className="text-sky-400">Diagnostics &amp; Greenlane Invariants</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Estate Diagnostics &amp; Telemetry Matrix
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time subsystem health, latency percentiles, memory pressure, and Greenlane invariant verification.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono border ${
            estateState.greenlaneStatus === 'verified'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              estateState.greenlaneStatus === 'verified' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'
            }`} />
            <span>Greenlane: {estateState.greenlaneStatus.toUpperCase()}</span>
          </div>

          <button
            onClick={handleRunVerification}
            disabled={isRunningCheck}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRunningCheck ? 'animate-spin' : ''}`} />
            <span>{isRunningCheck ? 'Evaluating Invariants...' : 'Verify Greenlane Estate Status'}</span>
          </button>
        </div>
      </div>

      {/* Latency Percentiles & Key Vitals Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Latency p50</span>
            <Clock className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">8.4 ms</div>
          <span className="text-xs text-emerald-400 font-mono">Target &lt; 15ms</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Latency p95</span>
            <Clock className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">16.2 ms</div>
          <span className="text-xs text-emerald-400 font-mono">Target &lt; 25ms</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Total Memory In-Use</span>
            <HardDrive className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">24.5 GB</div>
          <span className="text-xs text-slate-400 font-mono">of 64 GB provisioned</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Throughput Rate</span>
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">
            {estateState.totalInferenceThroughput.toLocaleString()} /s
          </div>
          <span className="text-xs text-emerald-400 font-mono">Inference &amp; Synapse IO</span>
        </div>
      </div>

      {/* Greenlane Invariant Audit Panel */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 spatial-grid">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Assurance Gate</span>
            <h3 className="text-sm font-semibold text-white mt-0.5">Greenlane Invariant Audit Suite</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">4 Active Continuous Invariants</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {invariants.map((inv) => (
            <div
              key={inv.id}
              className={`p-4 rounded-xl border ${
                inv.status === 'nominal'
                  ? 'bg-slate-900/40 border-slate-800'
                  : 'bg-amber-950/20 border-amber-500/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-white">{inv.title}</h4>
                <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                  inv.status === 'nominal'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                }`}>
                  {inv.status.toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{inv.description}</p>
              <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between items-center text-xs font-mono">
                <span className="text-slate-500">Live Reading:</span>
                <span className={inv.status === 'nominal' ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                  {inv.measuredValue}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Subsystems Health Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Inventory Health</span>
            <h3 className="text-sm font-semibold text-white mt-0.5">Subsystem Diagnostics ({filteredSubsystems.length})</h3>
          </div>

          {/* Segmented Filter Control */}
          <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-lg border border-slate-800">
            {['all', 'spine', 'compute', 'memory', 'agents', 'governance'].map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`px-3 py-1 text-xs font-medium rounded-md capitalize transition-colors ${
                  filterCategory === cat
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-medium">Subsystem Name</th>
                <th className="pb-3 font-medium">Category</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium text-right">Latency</th>
                <th className="pb-3 font-medium text-right">Throughput</th>
                <th className="pb-3 font-medium text-right">Memory</th>
                <th className="pb-3 font-medium text-right">Uptime</th>
                <th className="pb-3 font-medium text-center">Greenlane</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredSubsystems.map((sub) => (
                <tr key={sub.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 font-semibold text-white">{sub.name}</td>
                  <td className="py-3 text-slate-400 capitalize">{sub.category}</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-xs border ${
                      sub.status === 'nominal'
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        : sub.status === 'recovering'
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                        : 'bg-red-500/10 border-red-500/30 text-red-400'
                    }`}>
                      {sub.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 text-right text-slate-200 tabular-nums">{sub.latencyMs} ms</td>
                  <td className="py-3 text-right text-slate-200 tabular-nums">{sub.throughputPerSec.toLocaleString()} /s</td>
                  <td className="py-3 text-right text-slate-200 tabular-nums">{sub.memoryUsageMb} MB</td>
                  <td className="py-3 text-right text-emerald-400 tabular-nums">{sub.uptimePct.toFixed(2)}%</td>
                  <td className="py-3 text-center">
                    {sub.greenlaneVerified ? (
                      <span className="text-emerald-400 font-bold">✓ Verified</span>
                    ) : (
                      <span className="text-amber-400 font-bold">Pending</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
