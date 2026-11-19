import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { VoiceConciergeOrb } from './components/VoiceConciergeOrb';
import { GenesisSpineView } from './components/views/GenesisSpineView';
import { ResearchMlView } from './components/views/ResearchMlView';
import { DiagnosticsView } from './components/views/DiagnosticsView';
import { FleetManagementView } from './components/views/FleetManagementView';
import { InstructionYieldView } from './components/views/InstructionYieldView';
import { GovernanceProtocolsView } from './components/views/GovernanceProtocolsView';
import { MemoryOneBrainView } from './components/views/MemoryOneBrainView';
import { ParityRegressionGateView } from './components/views/ParityRegressionGateView';
import { OmegaControlView } from './components/views/OmegaControlView';
import { CommandPaletteModal } from './components/CommandPaletteModal';
import { INITIAL_ESTATE_STATE } from './data/estateData';
import { applyOperationalAction, EstateState } from './utils/estateLogic';
import { ShieldCheck, Activity, Cpu, Bot, History, Brain, Sliders, Layers } from 'lucide-react';

export default function App() {
  const [estateState, setEstateState] = useState<EstateState>(INITIAL_ESTATE_STATE);
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Check URL parameters on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab') || params.get('pillar');
      if (tabParam) {
        setCurrentTab(tabParam);
      }
    }
  }, []);

  const handleExecuteRemediateLegion = () => {
    setEstateState((prev) => applyOperationalAction(prev, { type: 'remediate_legion' }));
  };

  const handleExecuteVerifyGreenlane = () => {
    setEstateState((prev) => applyOperationalAction(prev, { type: 'verify_greenlane' }));
  };

  const handleUpdateConcurrency = (agentId: string, newConcurrency: number) => {
    setEstateState((prev) => {
      const updated = structuredClone(prev);
      const agent = updated.agents.find((a) => a.id === agentId);
      if (agent) {
        agent.concurrency = newConcurrency;
      }
      return updated;
    });
  };

  const handleApplyParameters = (params: {
    maxConcurrency: number;
    spatialProjectionRateHz: number;
    transcriptFirewallStrictness: 'strict' | 'standard' | 'bypass';
  }) => {
    setEstateState((prev) =>
      applyOperationalAction(prev, {
        type: 'tune_parameter',
        payload: params,
      })
    );
  };

  const allPillars = [
    { id: 'overview', label: '2100 Concierge Hub', icon: Layers },
    { id: 'genesis_spine', label: 'Genesis Spine Topology', icon: Activity },
    { id: 'fleet', label: 'Fleet & Legion Recovery', icon: Bot },
    { id: 'diagnostics', label: 'Diagnostics & Greenlane', icon: Activity },
    { id: 'evaluations', label: 'Parity Regression Gate', icon: ShieldCheck },
    { id: 'research', label: 'Research & Active ML', icon: Cpu },
    { id: 'instruction_yield', label: 'Instruction & Yield History', icon: History },
    { id: 'governance', label: 'Protocols & ASCII Gate', icon: ShieldCheck },
    { id: 'memory', label: 'Memory & One-Brain', icon: Brain },
    { id: 'omega', label: 'Omega Deep Control', icon: Sliders },
  ];

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* Top Bar Contract compliant header */}
      <Header
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        estateState={estateState}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-8">
        {/* The 2100 Spatial Access Layer (Voice Concierge Orb) - Always active and unified */}
        <VoiceConciergeOrb
          estateState={estateState}
          onNavigateToPillar={setCurrentTab}
          onExecuteAction={(type) => {
            if (type === 'remediate_legion') handleExecuteRemediateLegion();
            if (type === 'verify_greenlane') handleExecuteVerifyGreenlane();
          }}
        />

        {/* Pillar Navigation Bar for Deep Specialist Interrogation */}
        <div className="border-b border-slate-800 pb-2">
          <div className="flex items-center justify-between pb-3">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Preserved Estate Capability Inventory
              </span>
              <h2 className="text-base font-bold text-white mt-0.5">
                Specialist Operational Views &amp; Deep Governance
              </h2>
            </div>
            <span className="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              10/10 Specialist Pillars Active
            </span>
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
            {allPillars.map((p) => {
              const Icon = p.icon;
              const isActive = currentTab === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setCurrentTab(p.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                    isActive
                      ? 'bg-sky-500/15 border border-sky-400/40 text-white font-semibold shadow-sm'
                      : 'bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-400' : 'text-slate-500'}`} />
                  <span>{p.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* View Switcher: Deep Specialist Views */}
        <div className="transition-all duration-200">
          {currentTab === 'overview' && (
            <div className="space-y-8">
              {/* Executive Surface Overview Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div
                  onClick={() => setCurrentTab('fleet')}
                  className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-sky-500/40 cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400">Fleet Operations</span>
                    <Bot className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white mt-2">
                    {estateState.agents.length} Agents
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Legion Recovery #42412348112 {estateState.agents[0].status === 'active' ? 'Remediated' : 'Queued'}
                  </p>
                </div>

                <div
                  onClick={() => setCurrentTab('genesis_spine')}
                  className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-sky-500/40 cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400">Genesis Spine</span>
                    <Activity className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white mt-2">
                    12 Distributed Nodes
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Latency 11ms · Synapse mesh synchronous
                  </p>
                </div>

                <div
                  onClick={() => setCurrentTab('evaluations')}
                  className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-sky-500/40 cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400">Parity Regression Gate</span>
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-2">
                    100% Pass Score
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Zero capabilities deprecated or hidden
                  </p>
                </div>

                <div
                  onClick={() => setCurrentTab('research')}
                  className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-sky-500/40 cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400">Argon Research ML</span>
                    <Cpu className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white mt-2">
                    v8.4-Omni Checkpoint
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    1.84x instruction yield · Loss 0.0418
                  </p>
                </div>
              </div>

              {/* Directly embed Genesis Spine & Diagnostics in Overview for immediate visual presence */}
              <GenesisSpineView />
            </div>
          )}

          {currentTab === 'genesis_spine' && <GenesisSpineView />}
          {currentTab === 'research' && <ResearchMlView />}
          {currentTab === 'diagnostics' && (
            <DiagnosticsView
              estateState={estateState}
              onVerifyGreenlane={handleExecuteVerifyGreenlane}
            />
          )}
          {currentTab === 'fleet' && (
            <FleetManagementView
              estateState={estateState}
              onRemediateLegion={handleExecuteRemediateLegion}
              onUpdateAgentConcurrency={handleUpdateConcurrency}
            />
          )}
          {currentTab === 'instruction_yield' && <InstructionYieldView estateState={estateState} />}
          {currentTab === 'governance' && (
            <GovernanceProtocolsView
              estateState={estateState}
              onRemediateLegion={handleExecuteRemediateLegion}
            />
          )}
          {currentTab === 'memory' && <MemoryOneBrainView />}
          {currentTab === 'evaluations' && (
            <ParityRegressionGateView
              estateState={estateState}
              onNavigateToPillar={setCurrentTab}
            />
          )}
          {currentTab === 'omega' && (
            <OmegaControlView
              estateState={estateState}
              onApplyParameterTuning={handleApplyParameters}
              onRemediateLegion={handleExecuteRemediateLegion}
              onVerifyGreenlane={handleExecuteVerifyGreenlane}
            />
          )}
        </div>
      </main>

      {/* Clean, Non-Slop Footer */}
      <footer className="border-t border-slate-800/80 py-6 px-6 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <span>Argon Estate Intelligence · Founder Surface Ownership Model</span>
          <span>Verified Non-Destructive Capability Parity &copy; 2026</span>
          <span>Greenlane Invariants Enforced</span>
        </div>
      </footer>

      {/* Global Command Palette */}
      <CommandPaletteModal
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={setCurrentTab}
        onInterrogateQuery={(q) => {
          // Pass query
        }}
      />
    </div>
  );
}
