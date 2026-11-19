/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { ShieldAlert } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onSimulateClick: () => void;
  blockedCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onSimulateClick,
  blockedCount,
}) => {
  return (
    <header className="flex items-center justify-between gap-8 px-6 py-3.5 border-b border-slate-800 bg-[#090d16] sticky top-0 z-40">
      {/* Zone 1: Single text element wordmark */}
      <div className="flex items-center gap-3 shrink-0">
        <a
          href="#dashboard"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab('estate');
          }}
          className="text-lg font-bold tracking-tight text-white whitespace-nowrap hover:text-indigo-400 transition-colors"
        >
          Project Optimus
        </a>
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 text-[11px] font-mono font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 rounded">
          ZERO-CIRCUMVENTION ACTIVE
        </span>
      </div>

      {/* Zone 2: clean single-line text navigation links */}
      <nav className="hidden lg:flex items-center gap-5 text-sm font-medium text-slate-400">
        <button
          onClick={() => setActiveTab('estate')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'estate' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          Estate Topology
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'analytics' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          Telemetry Analytics
        </button>
        <button
          onClick={() => setActiveTab('interceptor')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'interceptor' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          Push Gate Interceptor
        </button>
        <button
          onClick={() => setActiveTab('ledger')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 flex items-center gap-1.5 ${
            activeTab === 'ledger' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          <span>Merkle Ledger</span>
          {blockedCount > 0 && (
            <span className="text-[10px] font-mono bg-red-950/80 text-red-400 px-1.5 py-0.2 rounded border border-red-800/70">
              {blockedCount} blocked
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('aei_analysis')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'aei_analysis' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          Genesis & Lineage
        </button>
        <button
          onClick={() => setActiveTab('policy')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'policy' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          Policy Studio
        </button>
        <button
          onClick={() => setActiveTab('evidence')}
          className={`hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 flex items-center gap-1.5 ${
            activeTab === 'evidence' ? 'border-indigo-500 text-white font-semibold' : 'border-transparent'
          }`}
        >
          <span className="text-emerald-400 font-bold">●</span>
          <span>Execution Evidence & Git</span>
        </button>
      </nav>

      {/* Zone 3: 1 primary action */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onSimulateClick}
          className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors whitespace-nowrap shrink-0 shadow-sm shadow-indigo-900/40 flex items-center gap-2"
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Simulate Push Gate</span>
        </button>
      </div>
    </header>
  );
};
