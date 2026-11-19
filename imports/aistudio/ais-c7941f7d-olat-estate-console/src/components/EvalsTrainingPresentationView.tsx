import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Play,
  GraduationCap,
  Presentation,
  Download,
  Plus,
  ArrowLeft,
  ArrowRight,
} from 'lucide-react';
import {
  EvalScenario,
  TrainingModule,
  FleetSummaryMetrics,
  SpecialistAgent,
} from '../lib/protocolEngine';

interface EvalsTrainingPresentationViewProps {
  evals: EvalScenario[];
  trainingModules: TrainingModule[];
  metrics: FleetSummaryMetrics;
  agents: SpecialistAgent[];
  onRunEvalSuite: () => void;
  onExecuteTrainingBatch: (moduleId: string) => void;
  onAddTrainingModule: (
    title: string,
    targetSquad: string,
    protocolFocus: string,
    yieldLiftPercent: number
  ) => void;
}

export const EvalsTrainingPresentationView: React.FC<
  EvalsTrainingPresentationViewProps
> = ({
  evals,
  trainingModules,
  metrics,
  agents,
  onRunEvalSuite,
  onExecuteTrainingBatch,
  onAddTrainingModule,
}) => {
  const [activeSubView, setActiveSubView] = useState<'evals' | 'presentation'>('evals');
  const [slideIndex, setSlideIndex] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>('');

  const [newTrainTitle, setNewTrainTitle] = useState<string>('');
  const [newTrainSquad, setNewTrainSquad] = useState<string>('Commercial Lease Fleet');
  const [newTrainFocus, setNewTrainFocus] = useState<string>('');
  const [newTrainLift, setNewTrainLift] = useState<string>('5.5');
  const [trainFormError, setTrainFormError] = useState<string>('');

  const slides = [
    {
      index: '01',
      kicker: 'Strategic Realignment Brief',
      title: 'Why Olat Pivoted From Heavy Infrastructure to Autonomous Estate Protocols',
      problem:
        'Heavy infrastructure investments and laptop-dependent agent prototypes created high operational fragility. When infrastructure failed, delivery stalled completely with zero verifiable customer yield.',
      resolution:
        'We redirected 100% of engineering focus toward Protocol Engineering: autonomous specialist squads built on the Quad-Layer and Agent Kit, executing Estate workflows headlessly without human intervention.',
      metricLabel: 'Laptop & Manual Loop Dependency',
      metricValue: '0.0% (100% Headless Fleet)',
    },
    {
      index: '02',
      kicker: 'Quad-Layer & Agent Kit Stack',
      title: 'Event-Driven State Machines, Persistent Memory & Private Inbox/Outbox',
      problem:
        'Ad-hoc conversational agents lose context across long-running property workflows and cannot prove compliance with statutory or lease covenants.',
      resolution:
        'Every specialist operates as an event-driven finite state machine (IDLE → CLAIMED → EXECUTING_PROTOCOL → PROOF_ATTACHED → OUTBOX_DISPATCHED) backed by Persistent Estate Memory and isolated Private Inbox/Outbox queues.',
      metricLabel: 'Verified Proof Bundles Dispatched to Outbox',
      metricValue: `${metrics.totalOutboxDispatched} Signed Bundles`,
    },
    {
      index: '03',
      kicker: 'Outcome vs. Expected Outcome',
      title: 'End-to-End Instruction, Claim, Proof & Yield Accounting',
      problem:
        'Activity metrics (tokens generated, tasks started) mask delivery failure. Founders require hard proof that instructions produce expected economic outcomes.',
      resolution:
        'Every instruction mandates a structured Specialist Claim, a cryptographic Proof token, and a strict Yield calculation (Actual Outcome ÷ Expected Outcome) audited directly in the Founder Review queue.',
      metricLabel: 'Current Fleet Average Yield',
      metricValue: `${metrics.averageYieldPercent.toFixed(1)}% (${metrics.founderApprovedCount}/${metrics.totalInstructions} Founder Approved)`,
    },
    {
      index: '04',
      kicker: 'Continuous Fleet Calibration',
      title: 'Protocol Evals & Specialist Curriculum Training',
      problem:
        'Edge cases in statutory cure timelines or multi-rider CPI leases require systematic calibration rather than manual hotfixes.',
      resolution:
        'Failed or sub-target instructions automatically feed deterministic Eval benchmarks and targeted Training Curricula—lifting specialist yield and protocol compliance before deployment.',
      metricLabel: 'Fleet Protocol Eval Pass Rate',
      metricValue: `${metrics.evalPassRate.toFixed(1)}% Across ${evals.length} Benchmarks`,
    },
  ];

  const currentSlide = slides[slideIndex];

  const handleCreateTraining = (e: React.FormEvent) => {
    e.preventDefault();
    const parsedLift = Number(newTrainLift);
    if (!newTrainTitle.trim() || newTrainTitle.trim().length < 8) {
      setTrainFormError('Training curriculum title must be at least 8 characters.');
      return;
    }
    if (!newTrainFocus.trim() || newTrainFocus.trim().length < 8) {
      setTrainFormError('Protocol focus description must be at least 8 characters.');
      return;
    }
    if (Number.isNaN(parsedLift) || parsedLift <= 0) {
      setTrainFormError('Expected yield lift % must be a positive number.');
      return;
    }
    setTrainFormError('');
    onAddTrainingModule(
      newTrainTitle.trim(),
      newTrainSquad,
      newTrainFocus.trim(),
      parsedLift
    );
    setNewTrainTitle('');
    setNewTrainFocus('');
    setStatusMessage(`Added new specialist training curriculum: ${newTrainTitle.trim()}.`);
  };

  const handleExportBrief = () => {
    const content = [
      '# OLAT ESTATE — FOUNDER STRATEGIC PIVOT & FLEET YIELD BRIEF',
      `Generated: 2026-11-01 | Fleet Average Yield: ${metrics.averageYieldPercent.toFixed(1)}% | Eval Pass Rate: ${metrics.evalPassRate.toFixed(1)}%`,
      '',
      '## 1. Strategic Shift',
      'Eliminated heavy infrastructure and laptop dependency in favor of Quad-Layer + Agent Kit headless specialists governed by strict Estate protocols.',
      '',
      '## 2. Live Fleet Metrics',
      `- Total Instructions Audited: ${metrics.totalInstructions}`,
      `- Average Yield (Outcome vs Expected): ${metrics.averageYieldPercent.toFixed(1)}%`,
      `- Founder Approved Outcomes: ${metrics.founderApprovedCount}`,
      `- Pending Founder Review: ${metrics.pendingFounderReviewCount}`,
      `- Headless Autonomy Rate: ${metrics.headlessAutonomyRate}%`,
    ].join('\n');

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'olat-estate-founder-pivot-brief.md';
    a.click();
    URL.revokeObjectURL(url);
    setStatusMessage(
      'Exported Founder Strategic Pivot & Yield Brief (olat-estate-founder-pivot-brief.md).'
    );
  };

  return (
    <div className="space-y-8">
      {/* Header & Mode Switcher */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Fleet Calibration · Protocol Evals & Training · Executive Communication
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">
            Fleet Evals, Specialist Training & Founder Presentation Studio
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 max-w-3xl">
            Benchmark specialist squads against strict Estate protocol invariants, execute training episodes to close yield deficits, and present the strategic pivot brief.
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveSubView('evals')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeSubView === 'evals'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            Evals & Training Workbench
          </button>
          <button
            type="button"
            onClick={() => setActiveSubView('presentation')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              activeSubView === 'presentation'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            Founder Pivot Presentation Deck
          </button>
        </div>
      </div>

      {statusMessage && (
        <div
          role="status"
          className="p-3.5 rounded-lg bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-xs font-medium flex items-center justify-between"
        >
          <span>{statusMessage}</span>
          <button
            type="button"
            onClick={() => setStatusMessage('')}
            className="text-xs underline opacity-80 hover:opacity-100 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {activeSubView === 'evals' ? (
        <div className="space-y-8">
          {/* Section 1: Protocol & Yield Evaluation Suite */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  01. Deterministic Protocol & Yield Evaluation Suite
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Current Fleet Pass Rate: {metrics.evalPassRate.toFixed(1)}% ({evals.filter((e) => e.passed).length} of {evals.length} passing threshold)
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  onRunEvalSuite();
                  setStatusMessage(
                    'Executed full deterministic Eval Suite across all 4 specialist squads.'
                  );
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 transition-colors inline-flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Run Full Fleet Eval Suite</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    <th className="py-2.5 px-3">Eval Benchmark</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Specialist & Protocol</th>
                    <th className="py-2.5 px-3 text-right">Threshold</th>
                    <th className="py-2.5 px-3 text-right">Measured Score</th>
                    <th className="py-2.5 px-3">Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {evals.map((ev) => (
                    <tr key={ev.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {ev.title}
                        </div>
                        <div className="font-mono text-slate-500 dark:text-slate-400">
                          {ev.id} · Last run {ev.lastRunAt}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-600 dark:text-slate-400">
                        {ev.category}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-700 dark:text-slate-300">
                        {ev.specialistId} · {ev.protocolId}
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-400">
                        {ev.passThresholdPercent.toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-bold text-slate-900 dark:text-slate-100">
                        {ev.scorePercent.toFixed(1)}%
                      </td>
                      <td className="py-3 px-3">
                        {ev.passed ? (
                          <span className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Passed</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-medium text-rose-700 dark:text-rose-400">
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Below Threshold</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 2: Specialist Training Curricula */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-6">
            <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-slate-500" />
                <span>02. Specialist Fleet Training Curricula ({trainingModules.length})</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Execute targeted protocol training episodes to calibrate specialist state machines and lift outcome yield.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {trainingModules.map((mod) => (
                <div
                  key={mod.id}
                  className="border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col justify-between space-y-4 bg-slate-50/50 dark:bg-slate-950/50"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400">
                      <span>{mod.id}</span>
                      <span>{mod.status}</span>
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {mod.title}
                    </h3>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      Squad: {mod.targetSquad}
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 pt-1">
                      {mod.protocolFocus}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-2.5">
                    <div className="flex items-center justify-between text-xs font-mono tabular-nums">
                      <span className="text-slate-500 dark:text-slate-400">
                        Episodes: {mod.episodesCompleted}
                      </span>
                      <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                        +{mod.yieldLiftPercent.toFixed(1)}% Yield Lift
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        onExecuteTrainingBatch(mod.id);
                        setStatusMessage(
                          `Completed +100 replay training episodes for ${mod.id} (${mod.title}); updated specialist eval calibration.`
                        );
                      }}
                      className="w-full py-2 px-3 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                    >
                      Run +100 Training Episodes
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Add New Training Curriculum Form */}
            <form
              onSubmit={handleCreateTraining}
              className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3"
            >
              <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                Launch New Protocol Training Curriculum
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                <div className="sm:col-span-4">
                  <label
                    htmlFor="train-title-input"
                    className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
                  >
                    Curriculum Title
                  </label>
                  <input
                    id="train-title-input"
                    type="text"
                    placeholder="Sub-Clause Holdback Proof Calibration"
                    value={newTrainTitle}
                    onChange={(e) => setNewTrainTitle(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div className="sm:col-span-3">
                  <label
                    htmlFor="train-squad-select"
                    className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
                  >
                    Target Specialist Squad
                  </label>
                  <select
                    id="train-squad-select"
                    value={newTrainSquad}
                    onChange={(e) => setNewTrainSquad(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  >
                    <option value="Commercial Lease Fleet">Commercial Lease Fleet</option>
                    <option value="Title & Registry Integrity">Title & Registry Integrity</option>
                    <option value="NOI & Yield Treasury Fleet">NOI & Yield Treasury Fleet</option>
                    <option value="Receivables & Compliance">Receivables & Compliance</option>
                  </select>
                </div>
                <div className="sm:col-span-3">
                  <label
                    htmlFor="train-focus-input"
                    className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
                  >
                    Protocol Invariant Focus
                  </label>
                  <input
                    id="train-focus-input"
                    type="text"
                    placeholder="Zero unverified rider schedules"
                    value={newTrainFocus}
                    onChange={(e) => setNewTrainFocus(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label
                    htmlFor="train-lift-input"
                    className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
                  >
                    Target Lift (%)
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="train-lift-input"
                      type="number"
                      step="0.1"
                      value={newTrainLift}
                      onChange={(e) => setNewTrainLift(e.target.value)}
                      className="w-full px-2.5 py-2 text-xs font-mono tabular-nums rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                    />
                    <button
                      type="submit"
                      className="px-3 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-md hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      Add
                    </button>
                  </div>
                </div>
              </div>
              {trainFormError && (
                <p
                  role="alert"
                  className="text-xs text-rose-600 dark:text-rose-400 font-medium"
                >
                  {trainFormError}
                </p>
              )}
            </form>
          </section>
        </div>
      ) : (
        /* Founder Strategic Pivot Presentation Studio */
        <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 lg:p-10 space-y-8">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
              <Presentation className="w-4 h-4" />
              <span>
                FOUNDER & BOARD COMMUNICATION DECK · SLIDE {currentSlide.index} OF 04
              </span>
            </div>

            <button
              type="button"
              onClick={handleExportBrief}
              className="px-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Executive Brief (.md)</span>
            </button>
          </div>

          <div className="space-y-6 max-w-4xl">
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              {currentSlide.index}. {currentSlide.kicker}
            </div>
            <h2
              className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-50"
              style={{ textWrap: 'balance' }}
            >
              {currentSlide.title}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div className="p-5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-rose-700 dark:text-rose-400">
                  Previous Bottleneck (Heavy Infra & Laptop Dependency)
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {currentSlide.problem}
                </p>
              </div>

              <div className="p-5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  New Protocol-First Architecture (Quad-Layer + Agent Kit)
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {currentSlide.resolution}
                </p>
              </div>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white dark:bg-slate-900">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                {currentSlide.metricLabel}
              </span>
              <span className="text-base font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
                {currentSlide.metricValue}
              </span>
            </div>
          </div>

          <div className="pt-6 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {slides.map((s, idx) => (
                <button
                  key={s.index}
                  type="button"
                  onClick={() => setSlideIndex(idx)}
                  className={`px-3 py-1.5 text-xs font-mono rounded-md transition-colors cursor-pointer ${
                    idx === slideIndex
                      ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-bold'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  Slide {s.index}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() =>
                  setSlideIndex((prev) => (prev - 1 + slides.length) % slides.length)
                }
                className="px-3 py-1.5 text-xs font-medium border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 inline-flex items-center gap-1 cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
              <button
                type="button"
                onClick={() => setSlideIndex((prev) => (prev + 1) % slides.length)}
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-md hover:bg-slate-800 inline-flex items-center gap-1 cursor-pointer"
              >
                <span>Next Slide</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
