import React from 'react';
import {
  ShieldCheck,
  GitBranch,
  Cpu,
  Terminal,
  Sparkles,
  Layers,
  DollarSign,
  Clock,
  Server,
  Flame,
  FlaskConical,
  Users
} from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  metrics: {
    totalAvoidedHours: number;
    costSavedUsd: number;
    reuseRate: string;
  };
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, metrics }) => {
  const tabs = [
    { id: 'console', label: 'Resolution Console', icon: Terminal, badge: 'FLOW #47' },
    { id: 'collab', label: 'Universal Collaboration', icon: Users, badge: 'P0 Gemini' },
    { id: 'science', label: 'Autonomous Science Lane', icon: FlaskConical, badge: 'P0 Science' },
    { id: 'greenlane', label: 'Greenlane Failure Elimination', icon: Flame, badge: 'GL-FAIL-042' },
    { id: 'baseline', label: 'Phase B: Baseline (20)', icon: Layers, badge: 'Audit' },
    { id: 'adversarial', label: 'Phase D: Adversarial Proof', icon: ShieldCheck, badge: '7 Tests' },
    { id: 'traces', label: '3 E2E Reuse Traces', icon: Cpu, badge: 'Verified' },
    { id: 'report', label: 'Phase E: Contract Report', icon: Sparkles, badge: 'P0 Report' },
    { id: 'argosync', label: 'Argo GitOps Sync', icon: Server, badge: 'Private Repo' },
    { id: 'catalog', label: 'Estate Catalog', icon: GitBranch, badge: 'IDP + Argon' }
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-50">
      {/* Top Banner */}
      <div className="border-b border-slate-800/80 px-4 py-2 bg-gradient-to-r from-blue-950/40 via-slate-900 to-indigo-950/40 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            PRIORITY: P0 ASYMMETRIC LEVERAGE
          </span>
          <span className="text-slate-400 hidden sm:inline">|</span>
          <span className="text-slate-300 font-mono">
            Contract Owner: <strong className="text-white">Kimi</strong>
          </span>
          <span className="text-slate-400 hidden sm:inline">|</span>
          <span className="text-slate-300 font-mono">
            Scope: <strong className="text-indigo-300">IDP + Argon Genesis</strong>
          </span>
        </div>

        <div className="flex items-center gap-3 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/60">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Greenlane: PASSING (SHA: e4f901c)</span>
          </div>
          <div className="flex items-center gap-1 text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/60">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span>Yield: <strong className="text-emerald-300">{metrics.totalAvoidedHours}h</strong></span>
          </div>
          <div className="flex items-center gap-1 text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/60">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            <span>Avoided: <strong className="text-emerald-300">${metrics.costSavedUsd.toLocaleString()}</strong></span>
          </div>
        </div>
      </div>

      {/* Main Header Nav */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 via-blue-600 to-cyan-500 p-0.5 shadow-lg shadow-blue-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[7px] flex items-center justify-center font-mono font-black text-blue-400 text-lg">
              K
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">
                Kimi Capability-First Resolution Engine
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                v3.2.0-PROD
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Verified reuse of existing estate capabilities before commissioning new implementation (Issue #47 / PR #50 / #7771)
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <nav className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none" aria-label="Engine Navigation">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                    isActive ? 'bg-blue-800 text-blue-100' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {tab.badge}
                </span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
