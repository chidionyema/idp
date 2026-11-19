import React, { useState, useEffect } from 'react';
import { Search, ArrowRight, ShieldCheck, Cpu, Activity, Bot, History, Brain, Sliders, X } from 'lucide-react';

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTab: (tabId: string) => void;
  onInterrogateQuery: (query: string) => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  onSelectTab,
  onInterrogateQuery,
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const commands = [
    { id: 'genesis_spine', title: 'Genesis Neural Spine & Node Topology', icon: Activity, category: 'Pillar View' },
    { id: 'fleet', title: 'Fleet Management & Legion Recovery #42412348112', icon: Bot, category: 'Pillar View' },
    { id: 'diagnostics', title: 'Estate Diagnostics & Greenlane Invariants', icon: Activity, category: 'Pillar View' },
    { id: 'evaluations', title: 'Automated Feature-Parity Regression Gate', icon: ShieldCheck, category: 'Assurance Gate' },
    { id: 'research', title: 'Argon Active Research & ML Checkpoints', icon: Cpu, category: 'Pillar View' },
    { id: 'instruction_yield', title: 'Instruction & Yield History Traces', icon: History, category: 'Pillar View' },
    { id: 'governance', title: 'Protocols, Transcript Firewall & ASCII Gate', icon: ShieldCheck, category: 'Governance' },
    { id: 'memory', title: 'One-Brain Episodic Memory Vector Store', icon: Brain, category: 'Pillar View' },
    { id: 'omega', title: 'Omega Founder Overrides & Parameter Tuning', icon: Sliders, category: 'Operational Control' },
  ];

  const filteredCommands = commands.filter((cmd) =>
    cmd.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden font-mono">
        <div className="flex items-center gap-3 p-4 border-b border-slate-800 bg-slate-950">
          <Search className="w-5 h-5 text-sky-400 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a pillar name or ask estate intelligence..."
            autoFocus
            className="w-full bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-96 overflow-y-auto p-2">
          {filteredCommands.length > 0 ? (
            <div className="space-y-1">
              {filteredCommands.map((cmd) => {
                const Icon = cmd.icon;
                return (
                  <button
                    key={cmd.id}
                    onClick={() => {
                      onSelectTab(cmd.id);
                      onClose();
                    }}
                    className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-slate-800 text-left transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-slate-800 group-hover:bg-slate-700 text-sky-400">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-white group-hover:text-sky-300">
                          {cmd.title}
                        </div>
                        <span className="text-[10px] text-slate-400">{cmd.category}</span>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-sky-400" />
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-6 text-center">
              <p className="text-xs text-slate-400">
                No matching view. Interrogate estate intelligence directly with "{query}"?
              </p>
              <button
                onClick={() => {
                  onInterrogateQuery(query);
                  onSelectTab('overview');
                  onClose();
                }}
                className="mt-3 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
              >
                Send to 2100 Voice Concierge
              </button>
            </div>
          )}
        </div>

        <div className="p-3 bg-slate-950 border-t border-slate-800 text-[11px] text-slate-500 flex justify-between">
          <span>Navigate with arrows or click</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
};
