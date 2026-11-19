import React from 'react';
import { ShieldCheck, Activity, Terminal } from 'lucide-react';
import { EstateState } from '../utils/estateLogic';

interface HeaderProps {
  currentTab: string;
  onSelectTab: (tabId: string) => void;
  estateState: EstateState;
  onOpenCommandPalette: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onSelectTab,
  estateState,
  onOpenCommandPalette,
}) => {
  const navItems = [
    { id: 'overview', label: '2100 Concierge' },
    { id: 'genesis_spine', label: 'Genesis Spine' },
    { id: 'fleet', label: 'Fleet & Agents' },
    { id: 'diagnostics', label: 'Diagnostics & Greenlane' },
    { id: 'evaluations', label: 'Parity Regression Gate' },
    { id: 'research', label: 'Research & ML' },
    { id: 'omega', label: 'Omega Control' },
  ];

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between gap-8 px-6 py-4 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
      {/* Zone 1: Brand wordmark */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={() => onSelectTab('overview')}
          className="text-lg font-bold tracking-tight text-white font-display whitespace-nowrap shrink-0 hover:text-sky-400 transition-colors"
        >
          ARGON 2100
        </button>
        <span className="hidden sm:inline-block text-xs font-mono text-sky-400/80 bg-sky-950/40 px-2 py-0.5 rounded border border-sky-500/20">
          Founder Surface
        </span>
      </div>

      {/* Zone 2: 4-5 clean single-line navigation links */}
      <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`whitespace-nowrap shrink-0 transition-colors pb-0.5 border-b-2 ${
                isActive
                  ? 'text-white border-sky-400 font-semibold'
                  : 'text-slate-400 border-transparent hover:text-slate-200'
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Zone 3: 1 primary action or status badge */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onOpenCommandPalette}
          className="hidden lg:flex items-center gap-2 px-2.5 py-1.5 text-xs text-slate-400 bg-slate-900 border border-slate-700/80 rounded-lg hover:text-white hover:border-slate-600 transition-colors"
          title="Command Palette (Cmd+K)"
        >
          <Terminal className="w-3.5 h-3.5 text-sky-400" />
          <span>Cmd+K</span>
        </button>

        <button
          onClick={() => onSelectTab('evaluations')}
          className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-850 border border-sky-500/30 rounded-lg transition-colors whitespace-nowrap shrink-0 shadow-sm"
        >
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>Estate Health {estateState.healthScore}%</span>
        </button>
      </div>
    </header>
  );
};
