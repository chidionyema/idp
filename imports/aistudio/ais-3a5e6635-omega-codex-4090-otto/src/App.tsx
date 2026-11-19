/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  EstateState,
  DefectStatus,
  DefectRegistryMode,
  PillarId,
  BacklogMission,
  ForgedTool,
  createInitialEstateState,
  computeFivePillarsStatus,
  pruneEstateWorktreesAndCaches,
  resolveDefectControl,
  unblockAllArgonGates,
  drainBacklogMission,
  createFounderMissionContract,
  forgeAutoTool,
  evaluateEstateSweep,
  evaluateArgonPrePushGate,
  triggerRealTimeSweep,
  executeArgonSyncGuarantee,
} from './engine/ottoEngine';
import { ExecutiveBriefingView } from './components/ExecutiveBriefingView';
import { ArgonGateView } from './components/ArgonGateView';
import { SwarmBacklogView } from './components/SwarmBacklogView';
import { ToolForgeCatechismView } from './components/ToolForgeCatechismView';
import { SovereignActuationView } from './components/SovereignActuationView';

type ActiveTab =
  | 'briefing'
  | 'argon-gate'
  | 'swarm-backlog'
  | 'tool-forge'
  | 'sovereign-actuation';

export default function App() {
  const [state, setState] = useState<EstateState>(() => createInitialEstateState());
  const [activeTab, setActiveTab] = useState<ActiveTab>('briefing');
  const [actionReceiptBanner, setActionReceiptBanner] = useState<string | null>(null);

  const pillars = computeFivePillarsStatus(state);
  const sweepEval = evaluateEstateSweep(state);
  const gateEval = evaluateArgonPrePushGate(state.argonGate);

  const handleUnblockAllGates = (mode: DefectRegistryMode = 'TRACKED_COMMITTED') => {
    setState((prev) => unblockAllArgonGates(prev, mode));
    setActionReceiptBanner(
      `Argon Pre-Push Gate VERIFIED (${mode}) · Reclaimed 14.62 GiB (18.64 GiB free, admit=GRANTED) · 3 controls transitioned to CONTROL_VERIFIED.`
    );
  };

  const handlePruneWorktrees = () => {
    setState((prev) => pruneEstateWorktreesAndCaches(prev));
    setActionReceiptBanner(
      'Pruned 28 stale worktrees and Cargo build caches (+14.62 GiB) without touching dirty working files · disk-sentinel admit=GRANTED.'
    );
  };

  const handleResolveDefect = (defectId: string, status: DefectStatus) => {
    setState((prev) => resolveDefectControl(prev, defectId, status));
    setActionReceiptBanner(`Updated ${defectId} status to ${status} in genesis-defect-controls.json.`);
  };

  const handleUpdateTrailers = (trailers: EstateState['argonGate']['commitTrailers']) => {
    setState((prev) => ({
      ...prev,
      argonGate: {
        ...prev.argonGate,
        commitTrailers: trailers,
      },
    }));
    setActionReceiptBanner(
      `Updated Genesis commit trailers (${trailers.instructionId} · class=${trailers.changeClass}).`
    );
  };

  const handleDrainMission = (missionId: string) => {
    setState((prev) => drainBacklogMission(prev, missionId));
    setActionReceiptBanner(
      missionId === 'DROP-2026-1082'
        ? 'DROP-2026-1082 executed via npm run sync:github · Bundle c3d3ce2c pushed to genesis-live with zero external login.'
        : `Drained ${missionId} through 3/3 Byzantine Sieve quorum and staged to origin/propose/*.`
    );
  };

  const handleCreateContract = (input: {
    title: string;
    targetRepo: string;
    bddSpec: string;
    pillar: PillarId;
    priority: BacklogMission['priority'];
  }) => {
    setState((prev) => createFounderMissionContract(prev, input));
    setActionReceiptBanner(
      `Dispatched new Founder Intent Contract ("${input.title}") across Claude, Codex, and Pi.`
    );
  };

  const handleForgeTool = (input: {
    name: string;
    language: ForgedTool['language'];
    bottleneckSolved: string;
    targetRepo: string;
  }) => {
    setState((prev) => forgeAutoTool(prev, input));
    setActionReceiptBanner(
      `Forged autonomous CLI tool ${input.name} (${input.language}) and committed to propose/auto-tool.`
    );
  };

  const handleExecuteArgonSync = () => {
    const res = executeArgonSyncGuarantee(state);
    setState(res.nextState);
    setActionReceiptBanner(
      `Argon-Sync Autonomous Push Guaranteed: Propagated ${res.pushedCommits} commits to origin/estate/recovery-durable-sessions · Receipt: ${res.receiptHash}`
    );
  };

  const handleTriggerSweep = () => {
    // If argonSyncAutoPropagate is true, sweep automatically guarantees push to argon-sync
    setState((prev) => {
      const swept = triggerRealTimeSweep(prev);
      if (swept.argonSyncAutoPropagate) {
        return executeArgonSyncGuarantee(swept).nextState;
      }
      return swept;
    });
    setActionReceiptBanner(
      'Executed ~/.estate/bin/otto-background-sweep.py sweep · Changes auto-pushed to argon-sync without reminder.'
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* Strict 3-Zone Top Bar Contract */}
      <header className="flex items-center justify-between gap-8 px-6 py-4 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        {/* Zone 1: Single text element wordmark */}
        <a
          href="#briefing"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab('briefing');
          }}
          className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-50 whitespace-nowrap shrink-0 font-display"
        >
          Omega Codex :4090
        </a>

        {/* Zone 2: 5 concise single-line text navigation links */}
        <nav
          aria-label="Primary Workspace Navigation"
          className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-300"
        >
          <a
            href="#briefing"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('briefing');
            }}
            className={`hover:text-slate-900 dark:hover:text-white transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'briefing'
                ? 'text-slate-900 dark:text-white underline underline-offset-8 decoration-amber-400 decoration-2'
                : ''
            }`}
          >
            Executive Briefing
          </a>
          <a
            href="#argon-gate"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('argon-gate');
            }}
            className={`hover:text-slate-900 dark:hover:text-white transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'argon-gate'
                ? 'text-slate-900 dark:text-white underline underline-offset-8 decoration-amber-400 decoration-2'
                : ''
            }`}
          >
            Argon Gate
          </a>
          <a
            href="#swarm-backlog"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('swarm-backlog');
            }}
            className={`hover:text-slate-900 dark:hover:text-white transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'swarm-backlog'
                ? 'text-slate-900 dark:text-white underline underline-offset-8 decoration-amber-400 decoration-2'
                : ''
            }`}
          >
            Swarm & Backlog
          </a>
          <a
            href="#tool-forge"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('tool-forge');
            }}
            className={`hover:text-slate-900 dark:hover:text-white transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'tool-forge'
                ? 'text-slate-900 dark:text-white underline underline-offset-8 decoration-amber-400 decoration-2'
                : ''
            }`}
          >
            Tool Forge & Catechism
          </a>
          <a
            href="#sovereign-actuation"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('sovereign-actuation');
            }}
            className={`hover:text-slate-900 dark:hover:text-white transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'sovereign-actuation'
                ? 'text-slate-900 dark:text-white underline underline-offset-8 decoration-amber-400 decoration-2'
                : ''
            }`}
          >
            Sovereign Actuation
          </a>
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => handleUnblockAllGates('TRACKED_COMMITTED')}
            className="px-4 py-2 text-xs font-semibold text-slate-100 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {gateEval.verdict === 'PASS' && sweepEval.diskAdmit === 'GRANTED'
              ? 'Estate Gate Verified'
              : 'Unblock Estate Gate'}
          </button>
        </div>
      </header>

      {/* Mobile Navigation Bar (visible only on small screens) */}
      <div className="md:hidden flex items-center gap-2 overflow-x-auto px-4 py-2.5 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        {(
          [
            { id: 'briefing', label: 'Briefing' },
            { id: 'argon-gate', label: 'Argon Gate' },
            { id: 'swarm-backlog', label: 'Swarm Backlog' },
            { id: 'tool-forge', label: 'Tool Forge' },
            { id: 'sovereign-actuation', label: 'Sovereign Engine' },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setActiveTab(item.id)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap shrink-0 ${
              activeTab === item.id
                ? 'bg-amber-400 text-slate-950 font-semibold'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Main Content Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {actionReceiptBanner ? (
          <div
            role="status"
            className="flex items-center justify-between gap-4 px-4 py-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400 tabular-nums"
          >
            <span>Receipt: {actionReceiptBanner}</span>
            <button
              type="button"
              onClick={() => setActionReceiptBanner(null)}
              className="text-slate-400 hover:text-slate-200 whitespace-nowrap shrink-0 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        ) : null}

        {activeTab === 'briefing' && (
          <ExecutiveBriefingView
            state={state}
            pillars={pillars}
            onUnblockAllGates={() => handleUnblockAllGates('TRACKED_COMMITTED')}
            onPruneWorktrees={handlePruneWorktrees}
            onDrainMission={handleDrainMission}
            onNavigateTab={setActiveTab}
            onTriggerSweep={handleTriggerSweep}
            onExecuteArgonSync={handleExecuteArgonSync}
          />
        )}

        {activeTab === 'argon-gate' && (
          <ArgonGateView
            state={state}
            onResolveDefect={handleResolveDefect}
            onUnblockAllGates={handleUnblockAllGates}
            onUpdateTrailers={handleUpdateTrailers}
          />
        )}

        {activeTab === 'swarm-backlog' && (
          <SwarmBacklogView
            state={state}
            onDrainMission={handleDrainMission}
            onCreateContract={handleCreateContract}
          />
        )}

        {activeTab === 'tool-forge' && (
          <ToolForgeCatechismView state={state} onForgeTool={handleForgeTool} />
        )}

        {activeTab === 'sovereign-actuation' && (
          <SovereignActuationView
            state={state}
            onExecuteDrop1082={() => handleDrainMission('DROP-2026-1082')}
          />
        )}
      </main>

      {/* Quiet Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <span>Omega Codex :4090 · Otto Digital Twin Estate Architecture</span>
          <div className="flex items-center gap-4 font-mono tabular-nums">
            <span>Sweep: ~/.estate/bin/otto-background-sweep.py</span>
            <span aria-hidden="true">·</span>
            <span>Sync: DROP-2026-1082 (c3d3ce2c)</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
