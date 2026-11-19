import React, { useState } from 'react';
import { Header } from './components/Header';
import { ResolutionConsole } from './components/ResolutionConsole';
import { BaselineTable } from './components/BaselineTable';
import { AdversarialProof } from './components/AdversarialProof';
import { ReuseTraces } from './components/ReuseTraces';
import { ExecutiveReport } from './components/ExecutiveReport';
import { CapabilityCatalog } from './components/CapabilityCatalog';
import { ArgoSyncView } from './components/ArgoSyncView';
import { GreenlaneEliminationView } from './components/GreenlaneEliminationView';
import { AutonomousScienceView } from './components/AutonomousScienceView';
import { FounderCollaborationView } from './components/FounderCollaborationView';
import { computeBaselineMetrics } from './core/baselineData';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('console');
  const baselineMetrics = computeBaselineMetrics();

  const metrics = {
    totalAvoidedHours: baselineMetrics.totalAvoidedHoursPostChange,
    costSavedUsd: baselineMetrics.postChangeCostSavedUsd,
    reuseRate: baselineMetrics.postChangeReuseYieldRate
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-500 selection:text-white">
      {/* Top Header & Navigation */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} metrics={metrics} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 pb-16">
        {activeTab === 'console' && <ResolutionConsole />}
        {activeTab === 'collab' && <FounderCollaborationView />}
        {activeTab === 'science' && <AutonomousScienceView />}
        {activeTab === 'greenlane' && <GreenlaneEliminationView />}
        {activeTab === 'baseline' && <BaselineTable />}
        {activeTab === 'adversarial' && <AdversarialProof />}
        {activeTab === 'traces' && <ReuseTraces />}
        {activeTab === 'report' && <ExecutiveReport />}
        {activeTab === 'argosync' && <ArgoSyncView />}
        {activeTab === 'catalog' && <CapabilityCatalog />}
      </main>

      {/* Sticky Bottom Status Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/90 py-2.5 px-4 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 font-mono text-[11px]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Kimi Capability-First Resolution Engine</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-500">Estate Scope: IDP + Argon Genesis</span>
          </div>

          <div className="flex items-center gap-4 text-slate-500">
            <span>Issue #47 (FLOW)</span>
            <span>PR #50 (Lifecycle)</span>
            <span>Issue #7771 (Ownership)</span>
            <span className="text-emerald-400 font-bold">SHA: e4f901c</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
