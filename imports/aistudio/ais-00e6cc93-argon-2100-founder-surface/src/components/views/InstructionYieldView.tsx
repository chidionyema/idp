import React, { useState } from 'react';
import { History, Search, Filter, TrendingUp, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { ExecutionLogItem, EstateState } from '../../utils/estateLogic';

interface InstructionYieldViewProps {
  estateState: EstateState;
}

export const InstructionYieldView: React.FC<InstructionYieldViewProps> = ({ estateState }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedLog, setSelectedLog] = useState<ExecutionLogItem | null>(null);

  const filteredLogs = estateState.recentLogs.filter((log) => {
    const matchesSearch =
      log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.actor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.details.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || log.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Operations</span>
            <span>/</span>
            <span className="text-sky-400">Instruction &amp; Yield History</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Execution Traces &amp; Yield Multipliers
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete audit trail of agent executions, instruction-yield ratios, and recovery workflows across releases.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="p-2 px-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <span className="text-slate-400">Average Instruction Yield:</span>{' '}
            <strong className="text-emerald-400">1.84x Output/Token</strong>
          </div>
        </div>
      </div>

      {/* Yield Efficiency Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs font-mono text-slate-400">Net Instruction Cost</span>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">$0.18 / 1k Instructions</div>
          <span className="text-xs text-emerald-400 font-mono">-24% optimization via Vulcan</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs font-mono text-slate-400">Pass Rate In-Flight</span>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">98.4% Nominal</div>
          <span className="text-xs text-slate-400 font-mono">1 Recovery Run in Queue</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs font-mono text-slate-400">Continuous Audits Completed</span>
          <div className="text-xl font-bold font-mono text-white tabular-nums mt-1">42,810 Runs</div>
          <span className="text-xs text-sky-400 font-mono">Zero Silent Rollbacks</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-slate-950/80">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search execution traces, actors, or recovery runs..."
            className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none font-mono"
          >
            <option value="all">All Execution Statuses</option>
            <option value="passed">Passed</option>
            <option value="queued">Queued</option>
            <option value="remediated">Remediated</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Execution Logs Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-medium">Timestamp</th>
                <th className="pb-3 font-medium">Actor / Origin</th>
                <th className="pb-3 font-medium">Action Directive</th>
                <th className="pb-3 font-medium">Pillar</th>
                <th className="pb-3 font-medium text-center">Status</th>
                <th className="pb-3 font-medium text-right">Instruction Yield</th>
                <th className="pb-3 font-medium text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 text-slate-400 whitespace-nowrap">{log.timestamp}</td>
                  <td className="py-3 font-semibold text-white">{log.actor}</td>
                  <td className="py-3 text-slate-200 max-w-xs truncate">{log.action}</td>
                  <td className="py-3 text-slate-400">{log.pillar}</td>
                  <td className="py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs border uppercase ${
                      log.status === 'passed'
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        : log.status === 'queued'
                        ? 'bg-sky-500/10 border-sky-500/30 text-sky-400'
                        : log.status === 'remediated'
                        ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                        : 'bg-red-500/10 border-red-500/30 text-red-400'
                    }`}>
                      {log.status}
                    </span>
                  </td>
                  <td className="py-3 text-right text-emerald-400 font-bold tabular-nums">
                    {(log.instructionYieldScore * 100).toFixed(0)}%
                  </td>
                  <td className="py-3 text-right">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="text-sky-400 hover:text-sky-300 hover:underline"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Log Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-4 font-mono">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs text-sky-400 uppercase tracking-wider">Trace Inspection</span>
                <h3 className="text-base font-bold text-white mt-1">{selectedLog.action}</h3>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-white">{selectedLog.timestamp}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Origin Actor:</span>
                <span className="text-white">{selectedLog.actor}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Estate Pillar:</span>
                <span className="text-white">{selectedLog.pillar}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Execution Status:</span>
                <span className="text-white uppercase font-bold">{selectedLog.status}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Instruction Yield Score:</span>
                <span className="text-emerald-400 font-bold">{(selectedLog.instructionYieldScore * 100).toFixed(0)}%</span>
              </div>

              <div className="mt-4 pt-2">
                <span className="text-slate-400 block mb-1">Execution Trace Details:</span>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs leading-relaxed">
                  {selectedLog.details}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white"
              >
                Close Trace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
