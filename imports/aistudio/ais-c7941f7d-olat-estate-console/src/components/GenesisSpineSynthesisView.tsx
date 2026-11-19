import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  GitMerge,
  ShieldCheck,
  Terminal,
  BookOpen,
  Plus,
} from 'lucide-react';
import {
  GENESIS_SPINE_STAGES,
  BuildHistoryIncident,
  EngineerTransitionStep,
  SuperSynthesisReport,
  SpecialistAgent,
} from '../lib/protocolEngine';

interface GenesisSpineSynthesisViewProps {
  synthesisReport: SuperSynthesisReport;
  incidents: BuildHistoryIncident[];
  transitionSteps: EngineerTransitionStep[];
  agents: SpecialistAgent[];
  onToggleTransitionStep: (stepId: string) => void;
  onExecuteSuperSynthesis: () => void;
  onAddBuildIncident: (
    failureTitle: string,
    legacySymptom: string,
    rootCause: string,
    protocolMachineFix: string,
    spineStageId: string
  ) => void;
  onNavigate: (tab: 'spine' | 'overview' | 'fleet' | 'protocols' | 'yield' | 'evals') => void;
}

export const GenesisSpineSynthesisView: React.FC<GenesisSpineSynthesisViewProps> = ({
  synthesisReport,
  incidents,
  transitionSteps,
  agents,
  onToggleTransitionStep,
  onExecuteSuperSynthesis,
  onAddBuildIncident,
  onNavigate,
}) => {
  const [selectedStageIdx, setSelectedStageIdx] = useState<number>(0);
  const [synthesisBanner, setSynthesisBanner] = useState<string>('');

  const [newFailureTitle, setNewFailureTitle] = useState<string>('');
  const [newSymptom, setNewSymptom] = useState<string>('');
  const [newRootCause, setNewRootCause] = useState<string>('');
  const [newProtocolFix, setNewProtocolFix] = useState<string>('');
  const [newSpineStageId, setNewSpineStageId] = useState<string>('SPINE-INBOX');
  const [incidentError, setIncidentError] = useState<string>('');

  const activeStage = GENESIS_SPINE_STAGES[selectedStageIdx] || GENESIS_SPINE_STAGES[0];

  const allInboxStream = agents.flatMap((agent) =>
    agent.inbox.map((msg) => ({
      ...msg,
      agentId: agent.id,
      protocolId: agent.protocolId,
      machineState: agent.machineState,
    }))
  );

  const handleAddIncidentSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFailureTitle.trim() || newFailureTitle.trim().length < 6) {
      setIncidentError('Failure title must be at least 6 characters.');
      return;
    }
    if (!newRootCause.trim() || newRootCause.trim().length < 8) {
      setIncidentError('Root cause analysis must be at least 8 characters.');
      return;
    }
    if (!newProtocolFix.trim() || newProtocolFix.trim().length < 8) {
      setIncidentError('Protocol machine guard fix must be at least 8 characters.');
      return;
    }
    setIncidentError('');
    onAddBuildIncident(
      newFailureTitle.trim(),
      newSymptom.trim() || 'Legacy unverified state mutation detected during cutover.',
      newRootCause.trim(),
      newProtocolFix.trim(),
      newSpineStageId
    );
    setNewFailureTitle('');
    setNewSymptom('');
    setNewRootCause('');
    setNewProtocolFix('');
    setSynthesisBanner(
      `Synthesized legacy failure "${newFailureTitle.trim()}" into ${newSpineStageId} invariant guard.`
    );
  };

  return (
    <div className="space-y-10">
      {/* Top Hero: The Genesis Spine & Super-Synthesis Command */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 lg:p-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          <div className="lg:col-span-7 flex flex-col justify-between space-y-5">
            <div className="space-y-2.5">
              <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                <span>New Genesis Architecture</span>
                <span aria-hidden="true">·</span>
                <span>Private Inbox + Build History Synthesis</span>
                <span aria-hidden="true">·</span>
                <span>Real-World Durable Execution</span>
              </div>
              <h1
                className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50"
                style={{ textWrap: 'balance' }}
              >
                The Congruent Genesis Spine: Turning Infrastructure Chaos Into Deterministic Protocol Execution
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl">
                Engineers do not need to juggle ten disconnected systems. Grounded in real-world distributed systems research—<strong>Transactional Inbox/Outbox</strong>, <strong>Event-Sourced State Replay (Temporal/Restate pattern)</strong>, and <strong>ESAA Cognitive-Execution Separation</strong>—every Estate workflow follows one linear 7-stage spine that makes our past infrastructure and laptop failures mathematically impossible to repeat.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => {
                  onExecuteSuperSynthesis();
                  setSynthesisBanner(
                    'Executed Full Super-Synthesis: drained all pending Private Inbox events through deterministic FSM guards, verified Outbox proof tokens, and locked 100.0% Genesis Spine Congruence.'
                  );
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-white transition-colors whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 cursor-pointer"
              >
                <GitMerge className="w-3.5 h-3.5" />
                <span>Run Super-Synthesis & Lock 100% Congruence</span>
              </button>

              <button
                type="button"
                onClick={() => onNavigate('fleet')}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 cursor-pointer"
              >
                <span>Inspect Private Inboxes ({synthesisReport.unconsumedInboxEvents} Unconsumed)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={() => onNavigate('yield')}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                Open Yield & Founder Gate
              </button>
            </div>
          </div>

          {/* Right 5 Cols: Live Congruence & Replay State Box */}
          <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 rounded-lg p-5 bg-slate-50/70 dark:bg-slate-950/60 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  Spine Congruence & Replay Audit
                </div>
                <div className="text-base font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                  {synthesisReport.spineHealthStatus}
                </div>
              </div>
              <div className="text-2xl font-bold font-mono tabular-nums text-emerald-700 dark:text-emerald-400">
                {synthesisReport.congruencePercent.toFixed(1)}%
              </div>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              {synthesisReport.synthesisSummary}
            </p>

            <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs font-mono">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400">Replay Fold Hash:</span>
                <span className="text-slate-900 dark:text-slate-100 font-semibold">
                  {synthesisReport.replayDeterminismHash}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400">Legacy Chaos Neutralized:</span>
                <span className="text-emerald-700 dark:text-emerald-400 font-semibold tabular-nums">
                  {synthesisReport.neutralizedIncidents} / {synthesisReport.totalIncidents} Failure Modes
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400">Engineer Cutover Progress:</span>
                <span className="text-slate-900 dark:text-slate-100 font-semibold tabular-nums">
                  {synthesisReport.completedTransitionSteps} / {synthesisReport.totalTransitionSteps} Phases Complete
                </span>
              </div>
            </div>
          </div>
        </div>

        {synthesisBanner && (
          <div
            role="status"
            className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-900 dark:text-emerald-200 font-medium flex items-center justify-between gap-4"
          >
            <span>{synthesisBanner}</span>
            <button
              type="button"
              onClick={() => setSynthesisBanner('')}
              className="underline shrink-0 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}
      </section>

      {/* Section 01: The 7-Stage Congruent Genesis Spine */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            01. The 7-Stage Congruent Genesis Spine (One Mental Model for All Engineers)
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            Every instruction on the Estate moves strictly from left to right along this spine. Select any stage to inspect the real-world distributed systems pattern and mandatory engineer rule.
          </p>
        </div>

        {/* 7-Step Horizontal Spine Selector */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
          {GENESIS_SPINE_STAGES.map((stage, idx) => {
            const isSelected = idx === selectedStageIdx;
            return (
              <button
                key={stage.id}
                type="button"
                onClick={() => setSelectedStageIdx(idx)}
                className={`text-left p-3.5 rounded-lg border transition-colors flex flex-col justify-between cursor-pointer ${
                  isSelected
                    ? 'bg-slate-900 text-white border-slate-900 dark:bg-slate-100 dark:text-slate-900 dark:border-slate-100'
                    : 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                }`}
              >
                <div className="text-[11px] font-mono opacity-75">
                  Stage {stage.stepNumber}
                </div>
                <div className="font-semibold text-xs mt-1.5 leading-snug">
                  {stage.name}
                </div>
                <div className="text-[10px] font-mono opacity-70 mt-2 truncate">
                  {stage.id}
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Spine Stage Deep-Dive Card */}
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            <div className="lg:col-span-7 space-y-4">
              <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
                <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  STAGE {activeStage.stepNumber} · {activeStage.id} · {activeStage.layerBinding}
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                  {activeStage.name}
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
                  <div className="font-semibold text-slate-500 dark:text-slate-400">
                    Real-World Research Pattern
                  </div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100">
                    {activeStage.realWorldPattern}
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
                  <div className="font-semibold text-slate-500 dark:text-slate-400">
                    Historical Chaos Eliminated
                  </div>
                  <div className="text-emerald-700 dark:text-emerald-400 font-medium">
                    {activeStage.chaosEliminated}
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-5 p-5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4 text-xs">
              <div className="space-y-1.5">
                <div className="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-slate-500" />
                  <span>Mandatory Engineer Implementation Law</span>
                </div>
                <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                  {activeStage.engineerRule}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-1">
                <div className="text-slate-500 dark:text-slate-400">
                  Formal Protocol Machine Invariant
                </div>
                <div className="font-mono text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900 p-2.5 rounded border border-slate-200 dark:border-slate-800">
                  {activeStage.invariantExpression}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 02: Private Inbox + Build History Super-Synthesis Matrix */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left 7 Cols: Build History Post-Mortem -> Protocol Guard Matrix */}
        <div className="lg:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 flex flex-col justify-between space-y-5">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              02. Build History Post-Mortem → Protocol Machine Guards
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Every failure that caused our infrastructure crisis is mapped to a hard protocol invariant so it can never recur.
            </p>
          </div>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
            {incidents.map((inc) => (
              <div key={inc.id} className="py-3.5 space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                  <span className="text-slate-500 dark:text-slate-400">
                    <strong className="text-slate-900 dark:text-slate-100">{inc.id}</strong> · {inc.era} · Guard: {inc.spineStageId}
                  </span>
                  <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{inc.status}</span>
                  </span>
                </div>
                <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                  {inc.failureTitle}
                </div>
                <div className="text-slate-600 dark:text-slate-400">
                  <strong>Root Cause:</strong> {inc.rootCause}
                </div>
                <div className="text-emerald-800 dark:text-emerald-300 font-medium">
                  <strong>Protocol Machine Guard:</strong> {inc.protocolMachineFix}
                </div>
              </div>
            ))}
          </div>

          {/* Add Build Incident Synthesis Form */}
          <form
            onSubmit={handleAddIncidentSubmit}
            className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3 text-xs"
          >
            <div className="font-semibold text-slate-900 dark:text-slate-100">
              Synthesize Legacy Failure Mode Into a Protocol Machine Guard
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label
                  htmlFor="inc-title-input"
                  className="block text-slate-600 dark:text-slate-400 mb-1"
                >
                  Legacy Failure Mode Title
                </label>
                <input
                  id="inc-title-input"
                  type="text"
                  placeholder="e.g., Concurrent Lease Amendment Overwrite"
                  value={newFailureTitle}
                  onChange={(e) => setNewFailureTitle(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label
                  htmlFor="inc-spine-select"
                  className="block text-slate-600 dark:text-slate-400 mb-1"
                >
                  Enforcing Genesis Spine Stage
                </label>
                <select
                  id="inc-spine-select"
                  value={newSpineStageId}
                  onChange={(e) => setNewSpineStageId(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                >
                  {GENESIS_SPINE_STAGES.map((st) => (
                    <option key={st.id} value={st.id}>
                      {st.stepNumber} · {st.id} ({st.name})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label
                  htmlFor="inc-cause-input"
                  className="block text-slate-600 dark:text-slate-400 mb-1"
                >
                  Historical Root Cause
                </label>
                <input
                  id="inc-cause-input"
                  type="text"
                  placeholder="e.g., Uncoordinated parallel writes without claim lock"
                  value={newRootCause}
                  onChange={(e) => setNewRootCause(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label
                  htmlFor="inc-fix-input"
                  className="block text-slate-600 dark:text-slate-400 mb-1"
                >
                  Protocol Machine Guard Fix
                </label>
                <div className="flex gap-2">
                  <input
                    id="inc-fix-input"
                    type="text"
                    placeholder="e.g., Mandatory ACQUIRE_CLAIM lease lock in FSM"
                    value={newProtocolFix}
                    onChange={(e) => setNewProtocolFix(e.target.value)}
                    className="flex-1 px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer"
                  >
                    Bind Guard
                  </button>
                </div>
              </div>
            </div>
            {incidentError && (
              <p role="alert" className="text-rose-600 dark:text-rose-400 font-medium">
                {incidentError}
              </p>
            )}
          </form>
        </div>

        {/* Right 5 Cols: Unified Fleet Private Inbox Synthesis Stream */}
        <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 flex flex-col justify-between space-y-4">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Unified Private Inbox & Event Replay Stream
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Synthesizes all specialist Private Inboxes into a single deterministic replay order
            </p>
          </div>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs flex-1">
            {allInboxStream.map((item) => (
              <div key={`${item.agentId}-${item.id}`} className="py-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-slate-500 dark:text-slate-400">
                  <span>
                    <strong className="text-slate-900 dark:text-slate-100">{item.id}</strong> → {item.agentId} ({item.protocolId})
                  </span>
                  <span
                    className={
                      item.processed
                        ? 'text-emerald-700 dark:text-emerald-400 font-semibold'
                        : 'text-amber-700 dark:text-amber-400 font-semibold'
                    }
                  >
                    {item.processed ? 'Replayed & Folded' : 'Queued in Inbox'}
                  </span>
                </div>
                <div className="text-slate-800 dark:text-slate-200 font-medium">
                  {item.payloadSummary}
                </div>
                <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                  Event: {item.eventType} · Machine State: {item.machineState}
                </div>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-500 dark:text-slate-400">
              Pending Inbox Events: {synthesisReport.unconsumedInboxEvents}
            </span>
            <button
              type="button"
              onClick={onExecuteSuperSynthesis}
              className="font-semibold text-slate-900 dark:text-slate-100 hover:underline cursor-pointer"
            >
              Drain & Replay All Inbox Events →
            </button>
          </div>
        </div>
      </section>

      {/* Section 03: Engineer Cutover & Transition Playbook */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-slate-500" />
              <span>03. Engineer Cutover & Transition Playbook (From Legacy Infra to Protocol Spine)</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Clear, unambiguous checklist showing every engineer what legacy habit to retire and what protocol action replaces it.
            </p>
          </div>
          <div className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-300">
            {synthesisReport.completedTransitionSteps} / {synthesisReport.totalTransitionSteps} Cutover Gates Verified
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {transitionSteps.map((step) => (
            <div
              key={step.id}
              className="border border-slate-200 dark:border-slate-800 rounded-lg p-5 flex flex-col justify-between space-y-4 bg-slate-50/40 dark:bg-slate-950/40"
            >
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between font-mono text-slate-500 dark:text-slate-400">
                  <span>
                    {step.id} · {step.phase}
                  </span>
                  <span
                    className={
                      step.completed
                        ? 'text-emerald-700 dark:text-emerald-400 font-semibold'
                        : 'text-amber-700 dark:text-amber-400 font-semibold'
                    }
                  >
                    {step.completed ? 'Verified' : 'Action Required'}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {step.title}
                </h3>

                <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="font-semibold text-rose-700 dark:text-rose-400">
                    Retire Legacy Habit:
                  </div>
                  <div className="text-slate-600 dark:text-slate-400">
                    {step.oldHabitToDrop}
                  </div>
                </div>

                <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="font-semibold text-emerald-700 dark:text-emerald-400">
                    Enforce Genesis Protocol Action:
                  </div>
                  <div className="text-slate-700 dark:text-slate-300">
                    {step.newProtocolAction}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 text-xs">
                <span className="font-mono text-slate-500 dark:text-slate-400 truncate">
                  Check: {step.verificationCommand}
                </span>
                <button
                  type="button"
                  onClick={() => onToggleTransitionStep(step.id)}
                  className={`px-3 py-1.5 rounded font-semibold whitespace-nowrap shrink-0 transition-colors cursor-pointer ${
                    step.completed
                      ? 'bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200'
                      : 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                  }`}
                >
                  {step.completed ? 'Completed ✓' : 'Mark Cutover Complete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
