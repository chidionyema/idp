import React from 'react';

interface TopBarProps {
  currentView: string;
  onSelectView: (view: string) => void;
  onOpenNewMotion: () => void;
  isEmergencyFrozen: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentView,
  onSelectView,
  onOpenNewMotion,
  isEmergencyFrozen
}) => {
  return (
    <header className="flex items-center justify-between gap-8 px-6 py-3.5 border-b border-neutral-800 bg-neutral-950 sticky top-0 z-40">
      {/* Zone 1: Single text element wordmark */}
      <a 
        href="#top" 
        onClick={(e) => { e.preventDefault(); onSelectView('topology'); }} 
        className="text-lg font-bold tracking-tight text-white whitespace-nowrap shrink-0 flex items-center gap-2.5"
      >
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 ring-4 ring-amber-500/20"></span>
        <span>Estate Sovereign</span>
      </a>

      {/* Zone 2: 4-5 clean single-line text navigation links */}
      <nav className="hidden md:flex items-center gap-7 text-xs font-semibold text-neutral-400">
        <button
          onClick={() => onSelectView('topology')}
          className={`cursor-pointer pb-1 transition-colors whitespace-nowrap shrink-0 ${
            currentView === 'topology'
              ? 'text-white border-b-2 border-amber-500'
              : 'hover:text-neutral-200'
          }`}
        >
          Visual Intelligence
        </button>
        <button
          onClick={() => onSelectView('artifacts')}
          className={`cursor-pointer pb-1 transition-colors whitespace-nowrap shrink-0 ${
            currentView === 'artifacts'
              ? 'text-white border-b-2 border-amber-500'
              : 'hover:text-neutral-200'
          }`}
        >
          Artifact Vault &amp; Sync
        </button>
        <button
          onClick={() => onSelectView('motions')}
          className={`cursor-pointer pb-1 transition-colors whitespace-nowrap shrink-0 ${
            currentView === 'motions'
              ? 'text-white border-b-2 border-amber-500'
              : 'hover:text-neutral-200'
          }`}
        >
          Motions &amp; Decrees
        </button>
        <button
          onClick={() => onSelectView('agents')}
          className={`cursor-pointer pb-1 transition-colors whitespace-nowrap shrink-0 ${
            currentView === 'agents'
              ? 'text-white border-b-2 border-amber-500'
              : 'hover:text-neutral-200'
          }`}
        >
          Agent Dispatcher
        </button>
        <button
          onClick={() => onSelectView('telemetry')}
          className={`cursor-pointer pb-1 transition-colors whitespace-nowrap shrink-0 ${
            currentView === 'telemetry' || currentView === 'failure-model'
              ? 'text-white border-b-2 border-amber-500'
              : 'hover:text-neutral-200'
          }`}
        >
          Risk &amp; Action Board
        </button>
      </nav>

      {/* Zone 3: 1 primary action */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onOpenNewMotion}
          disabled={isEmergencyFrozen}
          className={`px-4 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
            isEmergencyFrozen
              ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed'
              : 'bg-amber-500 text-neutral-950 font-semibold hover:bg-amber-400 active:scale-95 shadow-sm'
          }`}
        >
          {isEmergencyFrozen ? 'Estate Standby Active' : 'New Algorithmic Motion'}
        </button>
      </div>
    </header>
  );
};
