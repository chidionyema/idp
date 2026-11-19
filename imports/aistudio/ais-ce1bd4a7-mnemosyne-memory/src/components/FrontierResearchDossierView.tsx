import React, { useState } from 'react';
import {
  FRONTIER_ARCHITECTURES,
  SOVEREIGN_MODULES,
  FrontierArchitecture,
} from '../data/frontierResearch';
import { Search, CheckSquare, Square, ArrowUpRight } from 'lucide-react';

interface FrontierResearchDossierViewProps {
  activeModuleKeys: string[];
  onToggleModule: (moduleKey: string) => void;
  onEnableAllModules: () => void;
}

export const FrontierResearchDossierView: React.FC<FrontierResearchDossierViewProps> = ({
  activeModuleKeys,
  onToggleModule,
  onEnableAllModules,
}) => {
  const [selectedOrg, setSelectedOrg] = useState<'ALL' | FrontierArchitecture['organization']>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const organizations: ('ALL' | FrontierArchitecture['organization'])[] = [
    'ALL',
    'Anthropic',
    'OpenAI',
    'Meta FAIR',
    'Google DeepMind',
    'Letta (MemGPT)',
    'Zep (Graphiti)',
  ];

  const filteredArchitectures = FRONTIER_ARCHITECTURES.filter((arch) => {
    const matchesOrg = selectedOrg === 'ALL' || arch.organization === selectedOrg;
    const q = searchQuery.trim().toLowerCase();
    const matchesSearch =
      !q ||
      arch.organization.toLowerCase().includes(q) ||
      arch.systemName.toLowerCase().includes(q) ||
      arch.coreMechanism.toLowerCase().includes(q) ||
      arch.howTheyHandledMemory.toLowerCase().includes(q) ||
      arch.bestOfBreedFeatureAdopted.toLowerCase().includes(q);
    return matchesOrg && matchesSearch;
  });

  return (
    <div className="space-y-10">
      {/* Section 1: Best-of-Breed Synthesized Architecture Configurator */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="max-w-3xl space-y-1.5">
            <div className="text-xs text-slate-500">
              Best-of-Breed Synthesis · Live Architectural Ablation Controls
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Synthesized Sovereign Memory Modules ({activeModuleKeys.length}/{SOVEREIGN_MODULES.length} Enabled)
            </h1>
            <p className="text-sm text-slate-600">
              Toggle any frontier mechanism below to perform a live ablation study. Disabling a module immediately recalculates our system’s Recall, Context Rot Index, and Invariant Proofs across the entire platform.
            </p>
          </div>

          {activeModuleKeys.length < SOVEREIGN_MODULES.length && (
            <button
              type="button"
              onClick={onEnableAllModules}
              className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer whitespace-nowrap"
            >
              Restore All 6 Best-of-Breed Modules
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {SOVEREIGN_MODULES.map((mod) => {
            const isEnabled = activeModuleKeys.includes(mod.key);
            return (
              <div
                key={mod.key}
                className={`border rounded-xl p-5 flex flex-col justify-between transition-colors ${
                  isEnabled
                    ? 'bg-white border-slate-300'
                    : 'bg-slate-50 border-slate-200 opacity-75'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-xs text-slate-500">
                      <span>{mod.pillar}</span>
                      <span aria-hidden="true"> · </span>
                      <span>Origin: {mod.originLab}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => onToggleModule(mod.key)}
                      aria-label={`Toggle ${mod.name}`}
                      className="text-slate-900 hover:text-slate-700 cursor-pointer shrink-0 inline-flex items-center gap-1 text-xs font-semibold"
                    >
                      {isEnabled ? (
                        <CheckSquare className="w-4 h-4 text-slate-900" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-400" />
                      )}
                      <span>{isEnabled ? 'Enabled' : 'Disabled'}</span>
                    </button>
                  </div>

                  <h2 className="text-base font-bold text-slate-900">{mod.name}</h2>
                  <p className="text-xs text-slate-600 leading-relaxed">{mod.specification}</p>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-200 space-y-2 text-xs">
                  <div className="font-mono text-[11px] text-slate-700">{mod.verificationInvariant}</div>
                  <div className="flex items-center justify-between font-mono tabular-nums text-slate-600">
                    <span>Recall: +{mod.recallDeltaPct}%</span>
                    <span>Rot Reduction: -{mod.rotReductionPct}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section 2: Exhaustive Frontier Lab Architectural Research Dossier */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Deep Architectural Research Dossier: How Frontier Labs Solved &amp; Struggled With Memory
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Comparative breakdown of Anthropic, OpenAI, Meta FAIR, Google DeepMind, Letta (MemGPT), and Zep (Graphiti) across Memory, Active Focus, Multitasking, and Context Rot.
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search frontier lab architectures"
              placeholder="Filter mechanisms, math, or labs…"
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
        </div>

        {/* Organization Filter Bar */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-100 rounded-lg w-fit">
          {organizations.map((org) => (
            <button
              key={org}
              type="button"
              onClick={() => setSelectedOrg(org)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                selectedOrg === org
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {org === 'ALL' ? 'All Frontier Labs (6)' : org}
            </button>
          ))}
        </div>

        {/* Detailed Lab Dossier Cards */}
        <div className="space-y-6">
          {filteredArchitectures.map((arch, index) => {
            const moduleAdopted = activeModuleKeys.includes(arch.adoptionModuleKey);
            return (
              <article
                key={arch.id}
                className="border border-slate-200 rounded-xl p-6 space-y-5 hover:border-slate-300 transition-colors"
              >
                <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
                  <div>
                    <div className="text-xs text-slate-500">
                      <span>0{index + 1}. {arch.organization}</span>
                      <span aria-hidden="true"> · </span>
                      <span>{arch.releaseEra}</span>
                      <span aria-hidden="true"> · </span>
                      <span>Primary Pillar: {arch.primaryPillar}</span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 mt-1">{arch.systemName}</h3>
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono tabular-nums text-slate-700">
                    <span>LoCoMo: {arch.metrics.locomoRecallPct}%</span>
                    <span>·</span>
                    <span>RULER-128K: {arch.metrics.ruler128kNeedlePct}%</span>
                    <span>·</span>
                    <span>Contradiction Fix: {arch.metrics.contradictionResolutionPct}%</span>
                  </div>
                </div>

                {/* Mathematical & Core Mechanism Bar */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-xs space-y-1">
                  <div className="font-semibold text-slate-800">
                    Core Mechanism: <span className="font-normal text-slate-700">{arch.coreMechanism}</span>
                  </div>
                  <div className="font-mono text-slate-600">
                    Mathematical Formulation: {arch.mathematicalBasis}
                  </div>
                </div>

                {/* 4-Column Deep Technical Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 text-xs leading-relaxed">
                  <div className="space-y-1">
                    <div className="font-bold text-slate-900">1. How They Handled Memory</div>
                    <p className="text-slate-600">{arch.howTheyHandledMemory}</p>
                  </div>

                  <div className="space-y-1">
                    <div className="font-bold text-slate-900">2. Active Focus Strategy</div>
                    <p className="text-slate-600">{arch.activeFocusStrategy}</p>
                  </div>

                  <div className="space-y-1">
                    <div className="font-bold text-slate-900">3. Active Multitasking Model</div>
                    <p className="text-slate-600">{arch.multitaskingModel}</p>
                  </div>

                  <div className="space-y-1">
                    <div className="font-bold text-amber-900">4. Context Rot Vulnerability</div>
                    <p className="text-slate-600">{arch.contextRotWeakness}</p>
                  </div>
                </div>

                {/* Best-of-Breed Feature Synthesized Footer */}
                <div className="pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs">
                  <div>
                    <span className="font-semibold text-slate-900">Best-of-Breed Feature Adopted in Mnemosyne: </span>
                    <span className="text-slate-700">{arch.bestOfBreedFeatureAdopted}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onToggleModule(arch.adoptionModuleKey)}
                    className="font-semibold text-slate-900 hover:underline inline-flex items-center gap-1 cursor-pointer"
                  >
                    <span>
                      {moduleAdopted ? 'Active in Sovereign Engine (Click to Ablate)' : 'Disabled (Click to Re-Enable)'}
                    </span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
};
