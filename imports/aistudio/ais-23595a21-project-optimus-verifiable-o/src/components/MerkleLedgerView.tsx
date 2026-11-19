/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Database,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  ArrowRight,
  Lock,
} from 'lucide-react';
import { MerkleLedgerBlock } from '../types/optimus';
import { verifyMerkleChainIntegrity } from '../utils/optimus-engine';

interface MerkleLedgerViewProps {
  ledger: MerkleLedgerBlock[];
  onSelectBlock: (block: MerkleLedgerBlock) => void;
  onAuditChain: () => void;
  isAuditing: boolean;
  auditOutcome: string | null;
}

export const MerkleLedgerView: React.FC<MerkleLedgerViewProps> = ({
  ledger,
  onSelectBlock,
  onAuditChain,
  isAuditing,
  auditOutcome,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'RATIFIED' | 'BLOCKED'>('ALL');

  const filteredBlocks = ledger.filter((block) => {
    const matchesQuery =
      block.entityId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      block.actor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      block.blockHash.toLowerCase().includes(searchQuery.toLowerCase()) ||
      block.surface.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesQuery) return false;

    if (statusFilter === 'RATIFIED') return block.status === 'RATIFIED_AND_SIGNED';
    if (statusFilter === 'BLOCKED') return block.status === 'REJECTED_BLOCKED';
    return true;
  });

  return (
    <div className="space-y-5">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            <span>Verifiable Merkle Audit Ledger (Zero-Circumvention Chain)</span>
          </h2>
          <p className="text-xs text-slate-400">
            Cryptographic ledger tracking every push, commit, agent dispatch, and deployment. Tamper-evident and mathematically chained.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={onAuditChain}
            disabled={isAuditing}
            className="px-4 py-2 text-xs font-semibold text-white bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors whitespace-nowrap flex items-center gap-2 shadow-sm"
          >
            <Lock className="w-3.5 h-3.5 text-indigo-400" />
            <span>{isAuditing ? 'Recalculating SHA-256 Roots...' : 'Audit Merkle Integrity'}</span>
          </button>
        </div>
      </div>

      {auditOutcome && (
        <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800 text-xs text-emerald-300 font-mono flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{auditOutcome}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by entity, commit hash, author, or surface..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Interactive Segmented Filter Controls */}
        <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-lg border border-slate-800">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap ${
              statusFilter === 'ALL'
                ? 'bg-slate-800 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All Blocks ({ledger.length})
          </button>
          <button
            onClick={() => setStatusFilter('RATIFIED')}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap ${
              statusFilter === 'RATIFIED'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/80'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Ratified & Signed
          </button>
          <button
            onClick={() => setStatusFilter('BLOCKED')}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap ${
              statusFilter === 'BLOCKED'
                ? 'bg-red-950 text-red-300 border border-red-800/80'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Blocked Circumventions
          </button>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 font-mono text-[11px] text-slate-400">
              <tr>
                <th className="py-2.5 px-4 font-semibold">Height</th>
                <th className="py-2.5 px-4 font-semibold">Surface / Target</th>
                <th className="py-2.5 px-4 font-semibold">Status / Invariants</th>
                <th className="py-2.5 px-4 font-semibold">Committer / Actor</th>
                <th className="py-2.5 px-4 font-semibold">Block Hash</th>
                <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                <th className="py-2.5 px-4 text-right font-semibold">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredBlocks.map((block) => {
                const isRatified = block.status === 'RATIFIED_AND_SIGNED';
                return (
                  <tr
                    key={block.index}
                    onClick={() => onSelectBlock(block)}
                    className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-slate-200 tabular-nums">
                      #{block.index}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{block.entityId}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{block.surface}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {isRatified ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950/70 text-emerald-400 border border-emerald-800/80">
                            <ShieldCheck className="w-3 h-3 text-emerald-400" />
                            <span>RATIFIED</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-red-950/70 text-red-400 border border-red-800/80">
                            <ShieldAlert className="w-3 h-3 text-red-400" />
                            <span>BLOCKED</span>
                          </span>
                        )}
                        {block.violationCount > 0 && (
                          <span className="text-[10px] font-mono text-red-400">
                            {block.violationCount} violation{block.violationCount > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-300">
                      {block.actor}
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      <span className="text-indigo-400 font-semibold">{block.blockHash.substring(0, 8)}</span>
                      <span>...</span>
                      <span className="text-slate-500">{block.blockHash.substring(56)}</span>
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400 tabular-nums">
                      {new Date(block.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectBlock(block);
                        }}
                        className="text-xs font-medium text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}

              {filteredBlocks.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    No blocks matched the filter or search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
