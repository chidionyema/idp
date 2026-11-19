/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { ShieldCheck, GitBranch, AlertTriangle, Eye, Infinity as InfinityIcon, Users } from 'lucide-react';

export type ActiveTab =
  | 'alien-ceo'
  | 'ccp'
  | 'fleet-review'
  | 'tripartite'
  | 'flow-fprp'
  | 'ipn'
  | 'cdo'
  | 'klp'
  | 'science'
  | 'compounding'
  | 'cockpit'
  | 'audit';

interface TopNavProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  onOpenSync: () => void;
  onOpenWelcome?: () => void;
  isEmergencyHalt: boolean;
  unpushedCount: number;
}

export const TopNav: React.FC<TopNavProps> = ({
  activeTab,
  onTabChange,
  onOpenSync,
  onOpenWelcome,
  isEmergencyHalt,
  unpushedCount,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/80 px-6 py-3.5 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-8">
        
        {/* Zone 1: Single text element wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <span className="font-mono font-bold text-slate-950 text-base">G</span>
          </div>
          <span className="text-base font-bold tracking-tight text-white whitespace-nowrap">
            GENESIS ESTATE
          </span>
          <span className="hidden sm:inline-block text-xs font-mono text-cyan-400/90 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/60">
            2100 ALIEN
          </span>
        </div>

        {/* Zone 2: Navigation tabs with single-line whitespace-nowrap controls */}
        <nav className="hidden lg:flex items-center gap-1 text-xs font-medium text-slate-300">
          <button
            onClick={() => onTabChange('alien-ceo')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
              activeTab === 'alien-ceo'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>2100 Alien View</span>
          </button>

          <button
            onClick={() => onTabChange('ccp')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
              activeTab === 'ccp'
                ? 'bg-slate-800 text-purple-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span>Voice CCP (§15)</span>
          </button>

          <button
            onClick={() => onTabChange('fleet-review')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
              activeTab === 'fleet-review'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            <Users className="w-3.5 h-3.5 text-cyan-400" />
            <span>Fleet Council (§13)</span>
          </button>


          <button
            onClick={() => onTabChange('tripartite')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
              activeTab === 'tripartite'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            <InfinityIcon className="w-3.5 h-3.5 text-cyan-400" />
            <span>Tripartite & Longevity</span>
          </button>

          <button
            onClick={() => onTabChange('flow-fprp')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
              activeTab === 'flow-fprp'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Flow & Anti-Recursion (FPRP)</span>
          </button>

          <button
            onClick={() => onTabChange('ipn')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'ipn'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            Instruction Mesh (IPN)
          </button>


          <button
            onClick={() => onTabChange('cdo')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'cdo'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            CDO & Flow
          </button>

          <button
            onClick={() => onTabChange('klp')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'klp'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            Key Loan (KLP)
          </button>

          <button
            onClick={() => onTabChange('science')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'science'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            Science & History
          </button>

          <button
            onClick={() => onTabChange('compounding')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'compounding'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            Compounding
          </button>

          <button
            onClick={() => onTabChange('cockpit')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'cockpit'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            Cockpit
          </button>

          <button
            onClick={() => onTabChange('audit')}
            className={`px-3 py-1.5 rounded-md transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'audit'
                ? 'bg-slate-800 text-cyan-300 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60'
            }`}
          >
            Audit
          </button>
        </nav>

        {/* Zone 3: 1 primary action button */}
        <div className="flex items-center gap-3 shrink-0">
          {isEmergencyHalt ? (
            <div className="flex items-center gap-1.5 text-xs font-mono font-medium text-rose-300 bg-rose-950/80 px-2.5 py-1 rounded border border-rose-800">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>HALTED</span>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded border border-emerald-800/60">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>INVARIANTS SEALED</span>
            </div>
          )}

          {/* Founder Guide Quick Launch */}
          {onOpenWelcome && (
            <button
              onClick={onOpenWelcome}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-semibold text-cyan-300 hover:text-white bg-slate-900 hover:bg-slate-800 rounded-lg border border-cyan-800/60 transition-all cursor-pointer shadow-sm active:scale-95"
              title="Open Genesis Executive Welcome & Operations Guide"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>Founder Guide</span>
            </button>
          )}

          <button
            onClick={onOpenSync}
            className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:from-cyan-300 hover:to-teal-200 rounded-lg shadow-sm transition-all whitespace-nowrap shrink-0 cursor-pointer active:scale-95"
          >
            <GitBranch className="w-3.5 h-3.5 text-slate-950" />
            <span>Argon Sync</span>
            {unpushedCount > 0 && (
              <span className="px-1.5 py-0.2 bg-slate-900 text-cyan-300 rounded text-[10px] font-mono font-bold">
                +{unpushedCount}
              </span>
            )}
          </button>
        </div>

      </div>

      {/* Mobile nav bar */}
      <div className="flex lg:hidden overflow-x-auto gap-1.5 pt-3 pb-1 text-xs border-t border-slate-900 mt-2">
        {(['alien-ceo', 'flow-fprp', 'ipn', 'cdo', 'klp', 'science', 'compounding', 'cockpit', 'audit'] as ActiveTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`px-2.5 py-1 rounded whitespace-nowrap uppercase font-mono text-[10px] ${
              activeTab === tab ? 'bg-slate-800 text-cyan-300 font-bold' : 'text-slate-400'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
    </header>
  );
};
