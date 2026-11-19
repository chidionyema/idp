import React, { useState } from 'react';
import {
  Layers,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Clock,
  DollarSign,
  TrendingUp,
  FileText
} from 'lucide-react';
import { BASELINE_20_INSTRUCTIONS, computeBaselineMetrics } from '../core/baselineData';
import { BaselineInstructionRecord } from '../core/types';

export const BaselineTable: React.FC = () => {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRecord, setSelectedRecord] = useState<BaselineInstructionRecord | null>(null);

  const metrics = computeBaselineMetrics();

  const filteredInstructions = BASELINE_20_INSTRUCTIONS.filter((item) => {
    const matchesFilter =
      filterType === 'ALL' ||
      item.postChangeResolution === filterType ||
      (filterType === 'DUPLICATES' && item.baselineActionTaken === 'DUPLICATE_IMPLEMENTATION') ||
      (filterType === 'GAPS' && !item.capabilityExisted);

    const matchesSearch =
      item.instruction.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.existingCapabilityId && item.existingCapabilityId.toLowerCase().includes(searchQuery.toLowerCase())) ||
      item.evidenceNotes.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Metric KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Sampled Instructions
          </div>
          <div className="text-2xl font-bold text-white font-mono">{metrics.totalInstructions}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Authoritative records</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Baseline Discovery Failure
          </div>
          <div className="text-2xl font-bold text-rose-400 font-mono">
            {metrics.baselineDiscoveryFailureRate}
          </div>
          <div className="text-[11px] text-rose-400/80 mt-0.5">11 duplicate builds</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Baseline Wasted Work
          </div>
          <div className="text-2xl font-bold text-amber-400 font-mono">
            {metrics.totalHoursWastedInBaseline}h
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            ${metrics.baselineCostWastedUsd.toLocaleString()} USD churn
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Post-Change Avoided Work
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {metrics.totalAvoidedHoursPostChange}h
          </div>
          <div className="text-[11px] text-emerald-400/80 mt-0.5">
            ${metrics.postChangeCostSavedUsd.toLocaleString()} USD yield
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Verified Reuse Yield
          </div>
          <div className="text-2xl font-bold text-blue-400 font-mono">
            {metrics.postChangeReuseYieldRate}
          </div>
          <div className="text-[11px] text-blue-400/80 mt-0.5">18 / 20 resolved</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-400 mr-2 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Filter:
          </span>
          {['ALL', 'REUSE', 'COMPOSE', 'ADAPT', 'IMPLEMENT_NEW', 'DUPLICATES', 'GAPS'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilterType(tab)}
              className={`text-xs px-2.5 py-1 rounded-md font-mono transition-all cursor-pointer ${
                filterType === tab
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search instructions or evidence..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-full md:w-64"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] text-slate-400 uppercase font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-3 w-12 text-center">#</th>
                <th className="py-3 px-4">Estate Instruction</th>
                <th className="py-3 px-3">Domain</th>
                <th className="py-3 px-3 text-center">Existed?</th>
                <th className="py-3 px-3">Baseline Action</th>
                <th className="py-3 px-3 text-right">Wasted</th>
                <th className="py-3 px-3">Capability-First Resolution</th>
                <th className="py-3 px-3 text-right">Avoided</th>
                <th className="py-3 px-3 text-center">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
              {filteredInstructions.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                  onClick={() => setSelectedRecord(item)}
                >
                  <td className="py-2.5 px-3 text-center text-slate-500 font-bold">{item.id}</td>
                  <td className="py-2.5 px-4 font-sans text-xs text-slate-200 max-w-xs md:max-w-md truncate">
                    {item.instruction}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {item.domain}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {item.capabilityExisted ? (
                      <span className="text-emerald-400 font-bold">YES</span>
                    ) : (
                      <span className="text-slate-500 font-bold">GAP</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                        item.baselineActionTaken === 'DUPLICATE_IMPLEMENTATION'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : item.baselineActionTaken === 'ACCIDENTAL_REUSE'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}
                    >
                      {item.baselineActionTaken.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-rose-400">
                    {item.baselineHoursWasted > 0 ? `${item.baselineHoursWasted}h` : '0h'}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                        item.postChangeResolution === 'REUSE'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : item.postChangeResolution === 'COMPOSE'
                          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                          : item.postChangeResolution === 'ADAPT'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {item.postChangeResolution}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                    {item.postChangeAvoidedHours > 0 ? `+${item.postChangeAvoidedHours}h` : '0h'}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedRecord(item);
                      }}
                      className="text-blue-400 hover:text-blue-300 underline text-[11px]"
                    >
                      Evidence
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Evidence Modal / Detail Panel */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-bold border border-blue-500/30">
                  Instruction #{selectedRecord.id} • {selectedRecord.domain}
                </span>
                <h3 className="text-base font-bold text-white mt-1">{selectedRecord.instruction}</h3>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="text-slate-400 hover:text-white text-sm font-mono p-1 rounded hover:bg-slate-800 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="text-slate-400 mb-1">Baseline State:</div>
                <div className="text-rose-400 font-bold">
                  {selectedRecord.baselineActionTaken} ({selectedRecord.baselineHoursWasted}h wasted)
                </div>
                <div className="text-slate-400 mt-1 text-[11px]">
                  Discovered: {selectedRecord.baselineDiscovered ? 'YES' : 'NO (Missed)'}
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="text-slate-400 mb-1">Capability-First Resolution:</div>
                <div className="text-emerald-400 font-bold">
                  {selectedRecord.postChangeResolution} (+{selectedRecord.postChangeAvoidedHours}h avoided)
                </div>
                <div className="text-slate-400 mt-1 text-[11px]">
                  Capability: {selectedRecord.postChangeCapabilityId || 'None (Clean Gap)'}
                </div>
              </div>
            </div>

            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                Explicit Authoritative Evidence Notes:
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-sans">{selectedRecord.evidenceNotes}</p>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedRecord(null)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold cursor-pointer"
              >
                Close Audit Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
