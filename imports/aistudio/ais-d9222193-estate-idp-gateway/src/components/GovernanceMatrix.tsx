import React, { useState } from 'react';
import { Scale, CheckCircle2, AlertCircle, Info, HelpCircle } from 'lucide-react';
import { GOVERNANCE_CLAUSES } from '../protocol/rules';

export const GovernanceMatrix: React.FC = () => {
  const [filterMode, setFilterMode] = useState<string>('all');

  const filteredClauses = GOVERNANCE_CLAUSES.filter((c) => {
    if (filterMode === 'all') return true;
    return c.enforcementMode === filterMode;
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <Scale className="h-5 w-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">
              Governance Clauses Decidability & Contract Loader Matrix
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Machine-decidable analysis of the 9 governance clauses: 1 fully enforceable, 6 partly decidable, 2 policy advice.
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center space-x-1.5 text-xs font-mono">
          <button
            onClick={() => setFilterMode('all')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filterMode === 'all'
                ? 'bg-cyan-600 text-white font-semibold'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            All (9)
          </button>
          <button
            onClick={() => setFilterMode('enforced')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filterMode === 'enforced'
                ? 'bg-emerald-600 text-white font-semibold'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Enforced Gates
          </button>
          <button
            onClick={() => setFilterMode('linted')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filterMode === 'linted'
                ? 'bg-amber-600 text-white font-semibold'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Linted Rules
          </button>
          <button
            onClick={() => setFilterMode('advice')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filterMode === 'advice'
                ? 'bg-indigo-600 text-white font-semibold'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Advice / Policy
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
            <tr>
              <th className="py-2.5 px-4 font-medium w-12 text-center">#</th>
              <th className="py-2.5 px-4 font-medium">Clause Name</th>
              <th className="py-2.5 px-4 font-medium">Machine Decidable?</th>
              <th className="py-2.5 px-4 font-medium">Enforcement Tier</th>
              <th className="py-2.5 px-4 font-medium hidden md:table-cell">Required Declarations for Exact Gate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70 bg-slate-950/40">
            {filteredClauses.map((clause) => (
              <tr key={clause.clauseNumber} className="hover:bg-slate-900/40 transition-colors">
                <td className="py-3 px-4 text-center font-mono text-slate-400 font-semibold">
                  {clause.clauseNumber}
                </td>
                <td className="py-3 px-4">
                  <div className="font-semibold text-white">{clause.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                    {clause.details}
                  </div>
                </td>
                <td className="py-3 px-4 font-mono text-[11px]">
                  {clause.decidableByMachine === 'Yes' && (
                    <span className="inline-flex items-center space-x-1 text-emerald-400 font-semibold">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Yes (Direct)</span>
                    </span>
                  )}
                  {clause.decidableByMachine === 'Partly' && (
                    <span className="inline-flex items-center space-x-1 text-amber-400 font-semibold">
                      <AlertCircle className="h-3.5 w-3.5" />
                      <span>Partly (Missing Inputs)</span>
                    </span>
                  )}
                  {clause.decidableByMachine === 'Mostly' && (
                    <span className="inline-flex items-center space-x-1 text-cyan-400 font-semibold">
                      <Info className="h-3.5 w-3.5" />
                      <span>Mostly (Countable)</span>
                    </span>
                  )}
                  {clause.decidableByMachine === 'Measure only' && (
                    <span className="inline-flex items-center space-x-1 text-indigo-400 font-semibold">
                      <Scale className="h-3.5 w-3.5" />
                      <span>Measure Only</span>
                    </span>
                  )}
                  {clause.decidableByMachine === 'No' && (
                    <span className="inline-flex items-center space-x-1 text-slate-400 font-semibold">
                      <HelpCircle className="h-3.5 w-3.5 text-slate-500" />
                      <span>No (Intent/Advice)</span>
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 font-mono text-[11px]">
                  {clause.enforcementMode === 'enforced' && (
                    <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                      ENFORCED
                    </span>
                  )}
                  {clause.enforcementMode === 'linted' && (
                    <span className="px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-bold">
                      LINTED
                    </span>
                  )}
                  {clause.enforcementMode === 'advice' && (
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                      ADVICE
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 text-slate-300 hidden md:table-cell font-mono text-[11px]">
                  {clause.requiredDeclaration}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
