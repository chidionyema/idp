/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import {
  ArchitecturalPlane,
  ArchitectureProposalRfc,
  ConsultantQuestion,
  IncidentRecord,
  INITIAL_CONSULTANT_QUESTIONS,
  INITIAL_INCIDENTS,
  INITIAL_MILESTONES,
  INITIAL_RFCS,
  MilestoneStatus,
  RoadmapMilestone,
} from './data/idpDomainData';
import { CRITICAL_ENGINEERING_LANES } from './data/singleEngineerSpecData';
import {
  simulateArchitectureMetrics,
  SimulationConfig,
} from './utils/roadmapLogic';
import { VisionAndSpecsView } from './components/VisionAndSpecsView';
import { RoadmapMatrixView } from './components/RoadmapMatrixView';
import { IncidentsAndWorkView } from './components/IncidentsAndWorkView';
import { ProposalsAndSimulatorView } from './components/ProposalsAndSimulatorView';
import { ConsultantBriefView } from './components/ConsultantBriefView';
import { SingleEngineerSpecView } from './components/SingleEngineerSpecView';
import { EstateMultiplierPlanView } from './components/EstateMultiplierPlanView';

type ActiveTab =
  | 'multiplier'
  | 'spec'
  | 'vision'
  | 'roadmap'
  | 'incidents'
  | 'proposals'
  | 'consultant';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('multiplier');
  const [milestones, setMilestones] = useState<RoadmapMilestone[]>(INITIAL_MILESTONES);
  const [incidents, setIncidents] = useState<IncidentRecord[]>(INITIAL_INCIDENTS);
  const [rfcs, setRfcs] = useState<ArchitectureProposalRfc[]>(INITIAL_RFCS);
  const [questions, setQuestions] = useState<ConsultantQuestion[]>(INITIAL_CONSULTANT_QUESTIONS);

  // Contextual navigation filters
  const [selectedRfcId, setSelectedRfcId] = useState<string>('RFC-01');
  const [selectedLaneId, setSelectedLaneId] = useState<string>('LANE-01');
  const [roadmapPlaneFilter, setRoadmapPlaneFilter] = useState<ArchitecturalPlane | 'ALL'>('ALL');
  const [incidentModuleFilter, setIncidentModuleFilter] = useState<string>('');

  // Architecture simulator state
  const [simConfig, setSimConfig] = useState<SimulationConfig>({
    streamingWindowSec: 2,
    bitemporalAuditStrictness: 98,
    falsificationGatesCount: 5,
    entityResolutionConcurrency: 25000,
  });

  const simResult = simulateArchitectureMetrics(rfcs, simConfig);

  const handleUpdateMilestoneStatus = (milestoneId: string, newStatus: MilestoneStatus) => {
    setMilestones((prev) =>
      prev.map((m) => (m.id === milestoneId ? { ...m, status: newStatus } : m))
    );
  };

  const handleSelectRfcOption = (rfcId: string, optionId: 'A' | 'B' | 'C') => {
    setRfcs((prev) =>
      prev.map((r) => (r.id === rfcId ? { ...r, selectedOptionId: optionId } : r))
    );
  };

  const handleAddIncident = (newInc: IncidentRecord) => {
    setIncidents((prev) => [newInc, ...prev]);
  };

  const handleToggleQuestion = (id: string) => {
    setQuestions((prev) =>
      prev.map((q) => (q.id === id ? { ...q, includedInBrief: !q.includedInBrief } : q))
    );
  };

  const handleAddQuestion = (newQ: ConsultantQuestion) => {
    setQuestions((prev) => [...prev, newQ]);
  };

  const navigateToRfc = (rfcId: string) => {
    setSelectedRfcId(rfcId);
    setActiveTab('proposals');
  };

  const navigateToIncidents = (modulePath?: string) => {
    setIncidentModuleFilter(modulePath || '');
    setActiveTab('incidents');
  };

  const navigateToRoadmapPlane = (plane: ArchitecturalPlane) => {
    setRoadmapPlaneFilter(plane);
    setActiveTab('roadmap');
  };

  const navigateToLane = (laneId: string) => {
    setSelectedLaneId(laneId);
    setActiveTab('spec');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FBF9F5] text-stone-900">
      {/* Top Bar Contract: 3 zones separated by gap-8 on desktop, responsive wrap on mobile */}
      <header className="flex flex-wrap md:flex-nowrap items-center justify-between gap-y-3 gap-x-4 md:gap-8 px-4 sm:px-6 lg:px-10 py-3.5 bg-white border-b border-stone-200 sticky top-0 z-30">
        {/* Zone 1: Single text element wordmark */}
        <a
          href="#top"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab('multiplier');
          }}
          className="text-base sm:text-lg font-display font-semibold tracking-tight text-stone-900 whitespace-nowrap shrink-0"
        >
          IDP Estate & Reality Research
        </a>

        {/* Zone 2: 5 concise single-line text navigation links */}
        <nav
          aria-label="Primary Architecture Navigation"
          className="order-3 md:order-2 w-full md:w-auto flex items-center gap-5 sm:gap-6 overflow-x-auto text-xs sm:text-sm font-medium text-stone-600 pt-2 md:pt-0 border-t md:border-t-0 border-stone-100"
        >
          <button
            type="button"
            onClick={() => setActiveTab('multiplier')}
            className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeTab === 'multiplier'
                ? 'text-stone-900 underline underline-offset-8 decoration-2 decoration-stone-900 font-semibold'
                : 'hover:text-stone-900'
            }`}
          >
            Estate Multiplier & PRs
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('spec')}
            className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeTab === 'spec'
                ? 'text-stone-900 underline underline-offset-8 decoration-2 decoration-stone-900 font-semibold'
                : 'hover:text-stone-900'
            }`}
          >
            5 Critical Lanes & Code
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('vision')}
            className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeTab === 'vision'
                ? 'text-stone-900 underline underline-offset-8 decoration-2 decoration-stone-900 font-semibold'
                : 'hover:text-stone-900'
            }`}
          >
            Vision & Specs
          </button>
          <button
            type="button"
            onClick={() => {
              setRoadmapPlaneFilter('ALL');
              setActiveTab('roadmap');
            }}
            className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeTab === 'roadmap'
                ? 'text-stone-900 underline underline-offset-8 decoration-2 decoration-stone-900 font-semibold'
                : 'hover:text-stone-900'
            }`}
          >
            Roadmap Matrix
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('proposals')}
            className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeTab === 'proposals'
                ? 'text-stone-900 underline underline-offset-8 decoration-2 decoration-stone-900 font-semibold'
                : 'hover:text-stone-900'
            }`}
          >
            Proposals & Lab
          </button>
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="order-2 md:order-3 flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => {
              setIncidentModuleFilter('');
              setActiveTab('incidents');
            }}
            className={`px-2.5 py-2 text-xs font-medium border transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeTab === 'incidents'
                ? 'bg-stone-200 border-stone-400 text-stone-900 font-semibold'
                : 'border-stone-300 text-stone-700 hover:bg-stone-100'
            }`}
          >
            Incidents
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('consultant')}
            className="px-3 sm:px-4 py-2 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            Consultant & PR
          </button>
        </div>
      </header>

      {/* Global Critical Agent Lanes & Saved Spec Routing Bar — Immediately Visible to All Agents & Engineers */}
      <div className="bg-stone-900 text-stone-200 border-b border-stone-800 px-4 sm:px-6 lg:px-10 py-2.5 text-xs">
        <div className="max-w-[1360px] mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
            <span className="text-amber-300 font-semibold">SAVED REPO SPECS:</span>
            <span>/AGENTS.md</span>
            <span aria-hidden="true">·</span>
            <span>/docs/ESTATE_EXPONENTIAL_MULTIPLIER_PLAN.md</span>
            <span aria-hidden="true">·</span>
            <span>/docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md</span>
            <span aria-hidden="true">·</span>
            <span>/src/lanes/operationalKernels.ts</span>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto">
            {CRITICAL_ENGINEERING_LANES.map((lane) => {
              const isCurrent =
                activeTab === 'spec' && selectedLaneId === lane.laneId;
              return (
                <button
                  key={lane.laneId}
                  type="button"
                  onClick={() => navigateToLane(lane.laneId)}
                  className={`px-2.5 py-1 font-mono text-[11px] transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    isCurrent
                      ? 'bg-white text-stone-950 font-semibold'
                      : 'bg-stone-800 text-stone-200 hover:bg-stone-700'
                  }`}
                >
                  {lane.shortLabel}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Content Container */}
      <main className="flex-1 w-full max-w-[1360px] mx-auto px-6 lg:px-10 py-10">
        {activeTab === 'multiplier' && <EstateMultiplierPlanView />}

        {activeTab === 'spec' && (
          <SingleEngineerSpecView
            selectedLaneId={selectedLaneId}
            onSelectLaneId={setSelectedLaneId}
            onNavigateToRfc={navigateToRfc}
            onNavigateToIncident={() => navigateToIncidents()}
          />
        )}

        {activeTab === 'vision' && (
          <VisionAndSpecsView
            onNavigateToRfc={navigateToRfc}
            onNavigateToIncidents={navigateToIncidents}
            onNavigateToRoadmapPlane={navigateToRoadmapPlane}
            onNavigateToLane={navigateToLane}
          />
        )}

        {activeTab === 'roadmap' && (
          <RoadmapMatrixView
            milestones={milestones}
            initialPlaneFilter={roadmapPlaneFilter}
            onUpdateMilestoneStatus={handleUpdateMilestoneStatus}
            onSelectRfc={navigateToRfc}
            onSelectIncident={() => navigateToIncidents()}
            onSelectLane={navigateToLane}
          />
        )}

        {activeTab === 'incidents' && (
          <IncidentsAndWorkView
            incidents={incidents}
            initialModuleFilter={incidentModuleFilter}
            onAddIncident={handleAddIncident}
            onSelectRfc={navigateToRfc}
            onSelectLane={navigateToLane}
          />
        )}

        {activeTab === 'proposals' && (
          <ProposalsAndSimulatorView
            rfcs={rfcs}
            selectedRfcId={selectedRfcId}
            onSelectRfcId={setSelectedRfcId}
            onSelectRfcOption={handleSelectRfcOption}
            simConfig={simConfig}
            onUpdateSimConfig={setSimConfig}
            simResult={simResult}
            onNavigateToBrief={() => setActiveTab('consultant')}
          />
        )}

        {activeTab === 'consultant' && (
          <ConsultantBriefView
            rfcs={rfcs}
            incidents={incidents}
            milestones={milestones}
            questions={questions}
            simResult={simResult}
            onToggleQuestion={handleToggleQuestion}
            onAddQuestion={handleAddQuestion}
          />
        )}
      </main>

      {/* Quiet Institutional Footer */}
      <footer className="border-t border-stone-200 bg-white px-6 lg:px-10 py-6 text-xs text-stone-500">
        <div className="max-w-[1360px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            IDP Reality Research Platform · Canonical Spec: /AGENTS.md &
            /docs/SINGLE_ENGINEER_OPERATIONAL_SPEC.md
          </div>
          <div className="font-mono">
            Master Spec v3.4 · Bitemporal Fidelity: {simResult.bitemporalFidelityPct}% · P99
            Target: {simResult.endToEndLatencyMs}ms
          </div>
        </div>
      </footer>
    </div>
  );
}
