/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  INITIAL_STRATEGIC_OPPORTUNITIES,
  StrategicOpportunity
} from './engine/genesisAirLlmEngine';
import { StrategicAssessmentView } from './components/StrategicAssessmentView';
import { InferenceRouterView } from './components/InferenceRouterView';
import { EconomicsLabView } from './components/EconomicsLabView';
import { EvaluationLaneView } from './components/EvaluationLaneView';

type ActiveTab = 'assessment' | 'router' | 'economics' | 'evaluation-lane';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('assessment');
  const [opportunities, setOpportunities] = useState<StrategicOpportunity[]>(
    INITIAL_STRATEGIC_OPPORTUNITIES
  );
  const [evalLaneModelId, setEvalLaneModelId] = useState<string>('llama-3.3-70b');

  const handleToggleOpportunity = (id: string) => {
    setOpportunities((prev) =>
      prev.map((opp) =>
        opp.id === id ? { ...opp, enabledInGenesis: !opp.enabledInGenesis } : opp
      )
    );
  };

  const handleInspectModelInEvalLane = (modelId: string) => {
    setEvalLaneModelId(modelId);
    setActiveTab('evaluation-lane');
  };

  const navItems: { id: ActiveTab; label: string }[] = [
    { id: 'assessment', label: 'Strategic Assessment' },
    { id: 'router', label: 'Inference Router' },
    { id: 'economics', label: 'Economics Lab' },
    { id: 'evaluation-lane', label: 'Evaluation Lane' }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Strict 3-Zone Top Bar Contract */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200">
        <div className="max-w-[1360px] mx-auto flex items-center justify-between gap-8 px-4 sm:px-6 lg:px-8 py-3.5">
          {/* Zone 1: Single text element wordmark */}
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('assessment');
            }}
            className="text-base sm:text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0"
          >
            Genesis · Autonomous AI Estate
          </a>

          {/* Zone 2: 4 single-line text navigation links */}
          <nav
            aria-label="Primary Workspace Navigation"
            className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600"
          >
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`py-1 transition-colors whitespace-nowrap shrink-0 border-b-2 ${
                    isActive
                      ? 'border-slate-900 text-slate-900 font-semibold'
                      : 'border-transparent text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Zone 3: 1 primary action */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => setActiveTab('evaluation-lane')}
              className="px-4 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
            >
              Launch Evaluation Lane
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Navigation Strip (visible only below md breakpoint) */}
      <div className="md:hidden bg-white border-b border-slate-200 px-4 py-2 overflow-x-auto">
        <div className="flex items-center gap-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap shrink-0 ${
                activeTab === item.id
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Container */}
      <main id="top" className="flex-1 max-w-[1360px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'assessment' && (
          <StrategicAssessmentView
            opportunities={opportunities}
            onToggleOpportunity={handleToggleOpportunity}
            onInspectModelInEvalLane={handleInspectModelInEvalLane}
          />
        )}

        {activeTab === 'router' && <InferenceRouterView />}

        {activeTab === 'economics' && <EconomicsLabView />}

        {activeTab === 'evaluation-lane' && (
          <EvaluationLaneView initialModelId={evalLaneModelId} />
        )}
      </main>

      {/* Quiet Footer */}
      <footer className="border-t border-slate-200 bg-white mt-16">
        <div className="max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            Genesis Autonomous AI Estate · AirLLM Deep Inference Architecture & Governance
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setActiveTab('assessment')}
              className="hover:text-slate-900 transition-colors"
            >
              Research Dossier
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => setActiveTab('router')}
              className="hover:text-slate-900 transition-colors"
            >
              Inference Router
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => setActiveTab('economics')}
              className="hover:text-slate-900 transition-colors"
            >
              Economics Model
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => setActiveTab('evaluation-lane')}
              className="hover:text-slate-900 transition-colors"
            >
              Deep Evaluation Lane
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
